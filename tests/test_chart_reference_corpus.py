"""Reference preflight uses synthetic corpora copied only from public sample charts."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
import paydirt.chart_source_bundle as sources
from paydirt.chart_engine_audit import validate_engine_report
from tests import test_chart_readiness_freeze as support

freeze_files = support.freeze_files

REAL_VALIDATE = validate_engine_report
RULES = """season: 1983
two_point_conversion: false
overtime:
  enabled: true
  format: sudden_death
  period_length_minutes: 15
  max_periods_regular: 1
  max_periods_playoff: 0
  can_end_in_tie_regular: true
  can_end_in_tie_playoff: false
  coin_toss_winner_receives: true
"""


def bind(root: Path, path: Path, value: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def files(directory: Path) -> dict:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def partitions(names: list[str]) -> dict[str, str]:
    ordered = sorted(
        names,
        key=lambda name: (
            hashlib.sha256(("paydirt-reference-partition-v1:" + name).encode()).hexdigest(),
            name,
        ),
    )
    return {
        name: "development" if index % 2 == 0 else "withheld" for index, name in enumerate(ordered)
    }


@pytest.fixture
def reference_files(freeze_files: tuple, monkeypatch: pytest.MonkeyPatch) -> tuple:
    root, freeze = freeze_files
    candidate = root / freeze["cohorts"]["1983-generated"]["season_dir"]
    reference = root / "private-fixture/1983-reference"
    reference.mkdir(parents=True)
    (candidate / "1983.yaml").write_text(RULES)
    (reference / "1983.yaml").write_text(RULES)
    names = [f"Synthetic{index}" for index in range(28)]
    split = partitions(names)
    teams = {}
    for name in names:
        shutil.copytree(Path("seasons/2026/Ironclads"), candidate / name)
        shutil.copytree(Path("seasons/2026/Ironclads"), reference / ("Ref" + name))
        teams[name] = {
            "reference_folder": "Ref" + name,
            "partition": split[name],
            "inspected_before_freeze": True,
            "prior_use": "Synthetic public-fixture comparison; no private history asserted.",
        }
    # The original freeze fixture's root offense.csv is not a team.
    (candidate / "offense.csv").unlink()
    freeze["cohorts"]["1983-generated"]["chart_fingerprint"] = gate.chart_fingerprint(candidate)
    freeze["files"] = gate.readiness_file_inventory(root)
    evidence = {
        "schema_version": 1,
        "freeze_sha256": gate.readiness_freeze_fingerprint(freeze),
        "source_receipts": {},
        "training": {},
        "corpus": {
            "directory": reference.relative_to(root).as_posix(),
            "files": files(reference),
            "teams": teams,
            "partition_method": "sha256-folder-order-alternating-v1",
        },
    }
    calls = {"source": [], "component": [], "training": []}
    reports = {}
    for cohort in freeze["cohorts"]:
        folder = root / ".ai-audits/reference-fixture" / cohort
        evidence["source_receipts"][cohort] = bind(root, folder / "source.json", {"valid": True})
        report = {
            "metadata": {"seed": 20261108, "policy": "chart-focused"},
            "valid": True,
            "component_valid": True,
        }
        reports[cohort] = report
        evidence["training"][cohort] = bind(root, folder / "training.json", report)

    def prepared(path: Path, candidate_dir: Path, contract_path: Path) -> dict:
        calls["source"].append((path, candidate_dir, contract_path))
        if not json.loads(path.read_text()).get("valid"):
            raise ValueError("Synthetic prepared-source failure")
        return {
            "stats_dir": path.parent / "stats",
            "reproduced_dir": path.parent / "reproduced",
            "input_files": {"synthetic": path},
        }

    def component(directory: Path, contract: dict, report: dict, **options: object) -> dict:
        calls["component"].append((directory, contract, report, options))
        if report.get("raise"):
            raise ValueError("Synthetic component exception")
        return {
            "passed": report["component_valid"],
            "errors": [] if report["component_valid"] else ["Source/mechanics failed"],
            "components": {
                name: {"passed": True, "errors": []}
                for name in ("source", "tactics", "allocation", "engine")
            },
            "engine_evidence": report,
        }

    def validate(report: dict, contract: dict, directory: Path, **requirements: object) -> dict:
        calls["training"].append((report, contract, directory, requirements))
        return {
            "passed": report["valid"],
            "errors": [] if report["valid"] else ["Training fit failed"],
        }

    monkeypatch.setattr(sources, "prepared_source_options", prepared)
    monkeypatch.setattr(gate, "audit_release", component)
    monkeypatch.setattr(gate, "validate_engine_report", validate)
    return root, freeze, evidence, reference, reports, calls


def audit(data: tuple) -> dict:
    function = getattr(gate, "audit_reference_corpus_evidence", None)
    assert callable(function), (
        "Existing gate must validate stable-candidate reference census and prior-use partitions"
    )
    return function(*data[:3])


def rebind(data: tuple, cohort: str) -> None:
    root, _freeze, evidence, _reference, reports, _calls = data
    evidence["training"][cohort] = bind(
        root, root / evidence["training"][cohort]["path"], reports[cohort]
    )


def test_complete_corpus_is_independently_decoded_and_noncertifying(reference_files: tuple) -> None:
    result = audit(reference_files)
    assert result["passed"], result["errors"]
    assert result["corpus_validated"] is True
    assert result["reference_bytes_read"] is True
    assert result["benchmark_complete"] is False
    assert result["source_accepted"] is False
    assert result["ready_for_owner_review"] is False and result["release_certified"] is False
    corpus = result["corpus"]
    assert len(corpus["teams"]) == 28
    assert corpus["validation_class"] == "retrospective-cross-validation"
    assert corpus["partition_counts"] == {"development": 14, "withheld": 14}
    assert corpus["files"] == reference_files[2]["corpus"]["files"]
    assert corpus["rules_match"] is True
    assert all(
        team["decoder"]["passed"] and len(team["decoder"]["columns"]) == 73
        for team in corpus["teams"].values()
    )
    calls = reference_files[-1]
    assert all(len(values) == 4 for values in calls.values()), (
        "Recheck actual dependencies after the census"
    )
    assert all(
        call[-1] == {"minimum_repetitions": 64, "minimum_team_games": 1000, "require_fit": True}
        for call in calls["training"]
    )
    assert all(
        set(call[-1]) == {"stats_dir", "reproduced_dir", "input_files"}
        for call in calls["component"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "schema-bool",
        "extra",
        "freeze",
        "missing-cohort",
        "extra-cohort",
        "bad-reference",
        "changed-report",
        "missing-report",
        "duplicate-json",
        "nonfinite-json",
        "report-symlink",
        "training-seed",
        "seed-bool",
        "policy",
        "source-failed",
        "training-failed",
        "component-failed",
        "raised",
        "changed-code",
        "changed-candidate",
    ],
)
def test_invalid_dependencies_do_not_read_reference_bytes(
    reference_files: tuple,
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, freeze, evidence, reference, reports, calls = reference_files
    cohort = "1983-generated"
    report_path = root / evidence["training"][cohort]["path"]
    if mutation == "schema":
        evidence["schema_version"] = 2
    elif mutation == "schema-bool":
        evidence["schema_version"] = True
    elif mutation == "extra":
        evidence["passed"] = True
    elif mutation == "freeze":
        evidence["freeze_sha256"] = "0" * 64
    elif mutation == "missing-cohort":
        evidence["source_receipts"].pop("2024")
    elif mutation == "extra-cohort":
        evidence["training"]["2023"] = deepcopy(evidence["training"][cohort])
    elif mutation == "bad-reference":
        evidence["training"][cohort]["sha256"] = "PASS"
    elif mutation == "changed-report":
        report_path.write_text("{}")
    elif mutation == "missing-report":
        report_path.unlink()
    elif mutation in {"duplicate-json", "nonfinite-json"}:
        report_path.write_text(
            '{"valid":true,"valid":false}' if mutation == "duplicate-json" else '{"valid":1e999}'
        )
        evidence["training"][cohort]["sha256"] = hashlib.sha256(
            report_path.read_bytes()
        ).hexdigest()
    elif mutation == "report-symlink":
        target = report_path.with_suffix(".copy")
        report_path.rename(target)
        report_path.symlink_to(target)
    elif mutation == "training-seed":
        reports[cohort]["metadata"]["seed"] = 20361108
    elif mutation == "seed-bool":
        reports[cohort]["metadata"]["seed"] = True
    elif mutation == "policy":
        reports[cohort]["metadata"]["policy"] = "balanced"
    elif mutation == "source-failed":
        path = root / evidence["source_receipts"][cohort]["path"]
        evidence["source_receipts"][cohort] = bind(root, path, {"valid": False})
    elif mutation == "training-failed":
        reports[cohort]["valid"] = False
    elif mutation == "component-failed":
        reports[cohort]["component_valid"] = False
    elif mutation == "raised":
        reports[cohort]["raise"] = True
    elif mutation == "changed-code":
        (root / "paydirt/game_engine.py").write_text("Changed")
    elif mutation == "changed-candidate":
        (root / freeze["cohorts"][cohort]["season_dir"] / "Synthetic0/offense.csv").write_text(
            "Changed"
        )
    if mutation in {
        "training-seed",
        "seed-bool",
        "policy",
        "training-failed",
        "component-failed",
        "raised",
    }:
        rebind(reference_files, cohort)
    original = Path.read_bytes
    reference_reads = []

    def read(path: Path) -> bytes:
        if path.is_relative_to(reference):
            reference_reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"]
    assert result["reference_bytes_read"] is False and result["corpus_validated"] is False
    assert reference_reads == []
    if mutation in {"source-failed", "training-failed", "component-failed", "raised"}:
        assert {call[1].parent.name for call in calls["source"]} == {"candidates"}
        assert len(result["dependencies"]) == 2
        assert result["dependencies"]["2024"]["passed"]


@pytest.mark.parametrize(
    "mutation",
    [
        "directory-absolute",
        "directory-parent",
        "directory-symlink",
        "candidate-as-reference",
        "omitted-file",
        "extra-declared-file",
        "changed-file",
        "added-file",
        "missing-file",
        "file-symlink",
        "parent-symlink",
        "empty-extra-team",
        "extra-team",
        "missing-team",
        "omitted-mapping",
        "extra-mapping",
        "duplicate-mapping",
        "folder-traversal",
        "partition",
        "partition-method",
        "prior-use-bool",
        "prior-use-empty",
        "missing-metadata",
        "rules",
        "unsupported-token",
    ],
)
def test_reference_corpus_omissions_and_substitutions_fail(
    reference_files: tuple, mutation: str
) -> None:
    root, freeze, evidence, reference, _reports, _calls = reference_files
    corpus = evidence["corpus"]
    team = corpus["teams"]["Synthetic0"]
    path = reference / team["reference_folder"] / "offense.csv"
    if mutation == "directory-absolute":
        corpus["directory"] = str(reference)
    elif mutation == "directory-parent":
        corpus["directory"] = "private-fixture/../private-fixture/1983-reference"
    elif mutation == "directory-symlink":
        alias = root / "reference-alias"
        alias.symlink_to(reference)
        corpus["directory"] = "reference-alias"
    elif mutation == "candidate-as-reference":
        corpus["directory"] = freeze["cohorts"]["1983-generated"]["season_dir"]
        corpus["files"] = files(root / corpus["directory"])
    elif mutation == "omitted-file":
        corpus["files"].pop("1983.yaml")
    elif mutation == "extra-declared-file":
        corpus["files"]["not-present"] = "0" * 64
    elif mutation == "changed-file":
        path.write_text(path.read_text() + "\n")
    elif mutation == "added-file":
        (reference / "unbound.txt").write_text("Unbound")
    elif mutation == "missing-file":
        path.unlink()
    elif mutation == "file-symlink":
        target = root / "copy.csv"
        shutil.copyfile(path, target)
        path.unlink()
        path.symlink_to(target)
    elif mutation == "parent-symlink":
        folder = path.parent
        moved = root / "moved"
        folder.rename(moved)
        folder.symlink_to(moved)
    elif mutation == "empty-extra-team":
        (reference / "Unmapped").mkdir()
    elif mutation == "extra-team":
        shutil.copytree(path.parent, reference / "Unmapped")
    elif mutation == "missing-team":
        shutil.rmtree(path.parent)
    elif mutation == "omitted-mapping":
        corpus["teams"].pop("Synthetic0")
    elif mutation == "extra-mapping":
        corpus["teams"]["Invented"] = deepcopy(team)
    elif mutation == "duplicate-mapping":
        corpus["teams"]["Synthetic1"]["reference_folder"] = team["reference_folder"]
    elif mutation == "folder-traversal":
        team["reference_folder"] = "../RefSynthetic0"
    elif mutation == "partition":
        team["partition"] = "withheld" if team["partition"] == "development" else "development"
    elif mutation == "partition-method":
        corpus["partition_method"] = "manually-selected"
    elif mutation == "prior-use-bool":
        team["inspected_before_freeze"] = "false"
    elif mutation == "prior-use-empty":
        team["prior_use"] = " "
    elif mutation == "missing-metadata":
        (path.parent / "team.yaml").unlink()
        corpus["files"] = files(reference)
    elif mutation == "rules":
        (reference / "1983.yaml").write_text(
            RULES.replace("two_point_conversion: false", "two_point_conversion: true")
        )
        corpus["files"] = files(reference)
    elif mutation == "unsupported-token":
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream))
        rows[1][1] = "BOGUS"
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
        corpus["files"] = files(reference)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"]
    assert result["corpus_validated"] is False and result["benchmark_complete"] is False
    assert result["release_certified"] is False


def test_uninspected_partitions_are_declarations_not_unseen_proof(reference_files: tuple) -> None:
    for entry in reference_files[2]["corpus"]["teams"].values():
        entry["inspected_before_freeze"] = False
        entry["prior_use"] = "Declared uninspected synthetic fixture."
    result = audit(reference_files)
    assert result["passed"], result["errors"]
    assert result["corpus"]["validation_class"] == "declared-withheld-team-validation"
    assert result["corpus"]["non_observation_proven"] is False


def test_known_decoder_defaults_are_retained_as_limitations(reference_files: tuple) -> None:
    _root, _freeze, evidence, reference, _reports, _calls = reference_files
    path = reference / "RefSynthetic0/offense.csv"
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    rows[1][11] = "OFF 5"
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    evidence["corpus"]["files"] = files(reference)
    result = audit(reference_files)
    assert result["passed"], result["errors"]
    decoder = result["corpus"]["teams"]["Synthetic0"]["decoder"]
    assert decoder["passed"] and not decoder["fully_supported"] and decoder["limitations"]
    assert not result["benchmark_complete"]


def test_one_decoder_failure_does_not_hide_other_teams(
    reference_files: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    import paydirt.chart_audit as decoder

    function = decoder.audit_chart_decoder
    calls = []

    def check(path: Path) -> dict:
        calls.append(path.name)
        if path.name == "RefSynthetic0":
            raise ValueError("Synthetic decoder exception")
        return function(path)

    monkeypatch.setattr(decoder, "audit_chart_decoder", check)
    result = audit(reference_files)
    assert not result["passed"] and any(
        "Synthetic decoder exception" in reason for reason in result["errors"]
    )
    assert len(calls) == 28 and len(result["corpus"]["teams"]) == 28


@pytest.mark.parametrize(
    "nested",
    [
        None,
        [],
        {},
        {"passed": True},
        {"passed": True, "errors": None},
        {"passed": "true", "errors": []},
        {"passed": True, "errors": ["Contradiction"]},
    ],
)
def test_malformed_nested_dependencies_fail_closed(
    reference_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    nested: object,
) -> None:
    monkeypatch.setattr(gate, "validate_engine_report", lambda *args, **kwargs: nested)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"]
    assert result["reference_bytes_read"] is False


def test_minimal_synthetic_report_cannot_replace_real_campaign_evidence(
    reference_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gate, "validate_engine_report", REAL_VALIDATE)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"] and not result["reference_bytes_read"]


@pytest.mark.parametrize(
    "mutation",
    ["reference-file", "added-reference-directory", "freeze", "manifest", "training", "source"],
)
def test_late_changes_invalidate_the_entire_census(
    reference_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    import paydirt.chart_audit as decoder

    root, freeze, evidence, reference, _reports, _calls = reference_files
    original = decoder.audit_chart_decoder
    changed = False

    def check(path: Path) -> dict:
        nonlocal changed
        result = original(path)
        if not changed:
            changed = True
            if mutation == "reference-file":
                (reference / "RefSynthetic0/offense.csv").write_text("Late change")
            elif mutation == "added-reference-directory":
                (reference / "LateExtra").mkdir()
            elif mutation == "freeze":
                freeze["engine_fingerprint"] = "0" * 64
            elif mutation == "manifest":
                evidence["corpus"]["teams"]["Synthetic0"]["prior_use"] = "Late declaration"
            elif mutation == "training":
                (root / evidence["training"]["2024"]["path"]).write_text("{}")
            elif mutation == "source":
                (root / evidence["source_receipts"]["2024"]["path"]).write_text("{}")
        return result

    monkeypatch.setattr(decoder, "audit_chart_decoder", check)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"]
    assert result["corpus_validated"] is False and result["release_certified"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "reference-file",
        "empty-directory",
        "manifest",
        "source",
        "training",
        "source-symlink",
        "freeze",
    ],
)
def test_inputs_are_rechecked_after_dependency_revalidation(
    reference_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root, freeze, evidence, reference, _reports, calls = reference_files
    original = gate.validate_engine_report

    def validate(*args: object, **kwargs: object) -> dict:
        result = original(*args, **kwargs)
        if len(calls["training"]) == 4:
            if mutation == "reference-file":
                (reference / "RefSynthetic0/offense.csv").write_text("Late after census")
            elif mutation == "empty-directory":
                (reference / "LaterExtra").mkdir()
            elif mutation == "manifest":
                evidence["corpus"]["teams"]["Synthetic0"]["prior_use"] = "Late"
            elif mutation == "freeze":
                freeze["reserved_families"]["reference"]["opened"] = True
            else:
                field = "training" if mutation == "training" else "source_receipts"
                path = root / evidence[field]["2024"]["path"]
                if mutation == "source-symlink":
                    moved = path.with_suffix(".moved")
                    path.rename(moved)
                    path.symlink_to(moved)
                else:
                    path.write_text("{}")
        return result

    monkeypatch.setattr(gate, "validate_engine_report", validate)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"]
    assert result["corpus_validated"] is False


@pytest.mark.parametrize(
    "nested",
    [
        None,
        [],
        {},
        {"passed": True},
        {"passed": True, "errors": None},
        {"passed": "true", "errors": []},
        {"passed": True, "errors": ["Contradiction"]},
    ],
)
def test_malformed_decoder_results_cannot_pass(
    reference_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    nested: object,
) -> None:
    import paydirt.chart_audit as decoder

    monkeypatch.setattr(decoder, "audit_chart_decoder", lambda *_: nested)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"] and not result["corpus_validated"]
    assert len(result["corpus"]["teams"]) == 28


def test_both_cohort_dependency_failures_are_retained(reference_files: tuple) -> None:
    reference_files[-2]["1983-generated"]["component_valid"] = False
    reference_files[-2]["2024"]["valid"] = False
    for name in ("1983-generated", "2024"):
        rebind(reference_files, name)
    result = audit(reference_files)
    assert not result["passed"] and not result["reference_bytes_read"]
    assert all(not value["passed"] for value in result["dependencies"].values())
    assert any("1983-generated" in reason for reason in result["errors"])
    assert any("2024" in reason for reason in result["errors"])


@pytest.mark.parametrize(
    "mode",
    [
        "valid",
        "bad-binding",
        "missing-freeze",
        "existing-output",
        "public-output",
        "mixed-cohort",
        "mixed-visual",
        "declaration-changed",
        "freeze-changed",
        "output-parent-symlink",
    ],
)
def test_reference_cli_keeps_private_evidence_local_and_preserves_inputs(
    reference_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    from scripts import audit_generated_charts as cli

    root, freeze, evidence, _reference, *_ = reference_files
    monkeypatch.setattr(cli, "ROOT", root)
    folder = root / ".ai-audits/reference-fixture/cli"
    freeze_path, declaration_path = folder / "freeze.json", folder / "reference.json"
    bind(root, freeze_path, freeze)
    bind(root, declaration_path, evidence)
    output = root / ".ai-audits/chart-reference-comparison/synthetic-cli-result.json"
    argv = [
        "--reference-corpus",
        str(declaration_path),
        "--freeze",
        str(freeze_path),
        "--output",
        str(output),
    ]
    if mode == "bad-binding":
        evidence["freeze_sha256"] = "0" * 64
        bind(root, declaration_path, evidence)
    elif mode == "missing-freeze":
        argv = ["--reference-corpus", str(declaration_path), "--output", str(output)]
    elif mode == "existing-output":
        output.parent.mkdir(parents=True)
        output.write_text("Preserve")
    elif mode == "public-output":
        output = root / ".ai-audits/public-result.json"
        argv[-1] = str(output)
    elif mode == "mixed-cohort":
        argv += ["--season-dir", freeze["cohorts"]["1983-generated"]["season_dir"]]
    elif mode == "mixed-visual":
        argv += ["--visual-capture", str(declaration_path)]
    elif mode == "output-parent-symlink":
        actual = root / "outside"
        actual.mkdir()
        output.parent.symlink_to(actual, target_is_directory=True)
    elif mode in {"declaration-changed", "freeze-changed"}:
        original = gate.audit_reference_corpus_evidence

        def changed(*args: object) -> dict:
            result = original(*args)
            (declaration_path if mode == "declaration-changed" else freeze_path).write_text("{}")
            return result

        monkeypatch.setattr(gate, "audit_reference_corpus_evidence", changed)
    before = declaration_path.read_bytes()
    code = cli.main(argv)
    if mode == "valid":
        assert code == 0
        result = json.loads(output.read_text())
        assert result["passed"] and result["corpus_validated"] and not result["benchmark_complete"]
        assert result["input_files"]["declaration"]["sha256"] == hashlib.sha256(before).hexdigest()
    elif mode in {"bad-binding", "declaration-changed", "freeze-changed"}:
        assert code == 1
        result = json.loads(output.read_text())
        assert not result["passed"] and not result["corpus_validated"]
    else:
        assert code == 1
        if mode == "existing-output":
            assert output.read_text() == "Preserve"
        else:
            assert not output.exists()
    if mode != "declaration-changed":
        assert declaration_path.read_bytes() == before


def test_bound_reports_are_not_duplicated_in_the_preflight_result(reference_files: tuple) -> None:
    result = audit(reference_files)
    assert result["passed"], result["errors"]
    assert all(
        "engine_evidence" not in value["component"] for value in result["dependencies"].values()
    )
    assert result["dependency_artifacts_verified"] == 4


@pytest.mark.parametrize(
    "metadata", ["", "[]", "team_name: [", "short_name: SYN", "team_name: true"]
)
def test_unreadable_or_unidentified_metadata_cannot_silently_fall_back(
    reference_files: tuple,
    metadata: str,
) -> None:
    _root, _freeze, evidence, reference, *_ = reference_files
    path = reference / "RefSynthetic0/team.yaml"
    path.write_text(metadata)
    evidence["corpus"]["files"] = files(reference)
    result = audit(reference_files)
    assert not result["passed"] and result["errors"]
    assert len(result["corpus"]["teams"]) == 28
    assert result["corpus"]["teams"]["Synthetic0"]["decoder"]["passed"] is False
    assert result["corpus"]["teams"]["Synthetic1"]["decoder"]["passed"] is True

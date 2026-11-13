"""Paired gate boundaries use explicit public stubs, never private campaign evidence."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

import paydirt.chart_reference_audit as reference
import paydirt.chart_release_gate as gate
from paydirt.chart_engine_audit import _schedule_hash
from tests import test_chart_reference_corpus as support
from tests import test_chart_reference_pairs as pair_support

bind = support.bind
freeze_files = support.freeze_files
reference_files = support.reference_files
rebind = support.rebind
paired_reports = pair_support.paired_reports


@pytest.fixture(scope="module")
def real_pair_summary(paired_reports: tuple) -> dict:
    result = pair_support.compare(paired_reports)
    assert result["passed"], result["errors"]
    return result


@pytest.fixture
def pair_evidence(
    reference_files: tuple, real_pair_summary: dict, monkeypatch: pytest.MonkeyPatch
) -> tuple:
    """Scale only a public boundary stub; these are not actual 28-team games."""
    root, freeze, evidence, corpus, reports, calls = reference_files
    entry = freeze["cohorts"]["1983-generated"]
    path = root / entry["contract"]["path"]
    contract = json.loads(path.read_text())
    names = sorted(contract["teams"])
    contract["schedule"] = [
        {"away": names[2 * index], "home": names[2 * index + 1]}
        for _week in range(16)
        for index in range(14)
    ]
    entry["contract"] = bind(root, path, contract)
    freeze["files"] = gate.readiness_file_inventory(root)
    evidence["freeze_sha256"] = gate.readiness_freeze_fingerprint(freeze)
    directory = root / ".ai-audits/chart-reference-comparison/paired-fixture"
    paired = {
        "schema_version": 1,
        "freeze_sha256": gate.readiness_freeze_fingerprint(freeze),
        "reference_declaration_sha256": gate.readiness_freeze_fingerprint(evidence),
    }
    for side in ("generated", "reference"):
        paired[side] = bind(root, directory / (side + ".json"), {"side": side, "valid": True})

    def collect(
        generated: dict,
        original: dict,
        source: dict,
        candidate: object,
        reference_dir: object,
        mapping: dict,
    ) -> dict:
        assert len(mapping) == 28 and len(source["schedule"]) == 224
        assert candidate == root / entry["season_dir"] and reference_dir == corpus
        result = deepcopy(real_pair_summary)
        result["exposure_complete"] = True
        result["coverage"] = {
            "repetitions": 64,
            "games_per_set": 14336,
            "paired_games": 14336,
            "team_games": dict.fromkeys(names, 1024),
        }
        result["metadata"].update(
            master=20461108,
            schedule_hash=_schedule_hash(
                [(row["away"], row["home"]) for row in contract["schedule"]]
            ),
        )
        result["teams"] = {
            name: {
                **deepcopy(real_pair_summary["teams"]["Ironclads"]),
                "reference_folder": mapping[name],
            }
            for name in names
        }
        result["paired"] = {
            name: deepcopy(real_pair_summary["paired"]["Ironclads"]) for name in names
        }
        result["paired"]["league"] = deepcopy(real_pair_summary["paired"]["league"])
        for metrics in result["paired"].values():
            for summary in metrics.values():
                summary["replications"] = 64
        result["rankings"] = {
            label: {metric: names for metric in values}
            for label, values in real_pair_summary["rankings"].items()
        }
        result["game_pairs"] = [
            {
                "repetition": repetition,
                "game_index": index,
                "seed": 20461108 + repetition * 1000003 + index * 1009,
                "away": row["away"],
                "home": row["home"],
                "reference_away": mapping[row["away"]],
                "reference_home": mapping[row["home"]],
                "score_delta": {"away": 0, "home": 0},
            }
            for repetition in range(64)
            for index, row in enumerate(contract["schedule"])
        ]
        if not generated["valid"] or not original["valid"]:
            result["passed"] = False
            result["errors"].append("Synthetic raw campaign failure")
        return result

    monkeypatch.setattr(reference, "compare_reference_campaigns", collect)
    return root, freeze, evidence, paired, corpus, reports, calls, collect


def audit(data: tuple) -> dict:
    function = getattr(gate, "audit_reference_paired_evidence", None)
    assert callable(function), (
        "Existing gate must guard actual paired reports and complete exposure"
    )
    return function(*data[:4])


def test_complete_paired_gate_rechecks_dependencies_and_remains_noncertifying(
    pair_evidence: tuple,
) -> None:
    result = audit(pair_evidence)
    assert result["passed"], result["errors"]
    assert (
        result["paired_validated"] and result["corpus_validated"] and result["reference_bytes_read"]
    )
    assert set(result["preflights"]) == {"before", "after"}
    assert result["paired"]["coverage"]["paired_games"] == 14336
    assert not result["benchmark_complete"] and not result["source_accepted"]
    assert not result["ready_for_owner_review"] and not result["release_certified"]
    assert all(len(values) == 8 for values in pair_evidence[-2].values())


@pytest.mark.parametrize("mutation", ["source", "training", "freeze", "corpus"])
def test_failed_dependencies_prevent_reading_paired_outcomes(
    pair_evidence: tuple, mutation: str
) -> None:
    root, freeze, evidence, paired, corpus, reports, _calls, _collect = pair_evidence
    if mutation == "source":
        bind(root, root / evidence["source_receipts"]["2024"]["path"], {"valid": False})
    elif mutation == "training":
        reports["2024"]["valid"] = False
        rebind((root, freeze, evidence, corpus, reports, _calls), "2024")
    elif mutation == "freeze":
        freeze["schema_version"] = 0
    else:
        (corpus / "new-directory").mkdir()
    # A missing report would raise if read before the failed preflight.
    (root / paired["generated"]["path"]).unlink()
    result = audit(pair_evidence)
    assert not result["passed"] and result["errors"] and not result["paired_validated"]
    assert not result["paired"] and not result["paired_artifacts_read"]


@pytest.mark.parametrize(
    "mutation",
    ["schema", "extra", "freeze", "declaration", "digest", "public", "symlink", "both-raw"],
)
def test_paired_declaration_and_raw_artifacts_are_strict(
    pair_evidence: tuple, mutation: str
) -> None:
    root, _freeze, _evidence, paired, _corpus, _reports, _calls, _collect = pair_evidence
    if mutation == "schema":
        paired["schema_version"] = True
    elif mutation == "extra":
        paired["asserted_pass"] = True
    elif mutation == "freeze":
        paired["freeze_sha256"] = "0" * 64
    elif mutation == "declaration":
        paired["reference_declaration_sha256"] = "0" * 64
    elif mutation == "digest":
        paired["generated"]["sha256"] = "0" * 64
    elif mutation == "public":
        paired["generated"] = bind(root, root / "public-paired.json", {"valid": True})
    elif mutation == "symlink":
        target = root / paired["generated"]["path"]
        alias = target.with_name("alias.json")
        alias.symlink_to(target.name)
        paired["generated"]["path"] = alias.relative_to(root).as_posix()
    else:
        for side in ("generated", "reference"):
            path = root / paired[side]["path"]
            path.write_text("{malformed")
            paired[side]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = audit(pair_evidence)
    assert not result["passed"] and result["errors"] and not result["paired_validated"]
    assert "after" in result["preflights"]
    if mutation == "both-raw":
        assert any("generated" in error for error in result["errors"]) and any(
            "reference" in error for error in result["errors"]
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "corpus",
        "source",
        "training",
        "code",
        "declaration",
        "pair-declaration",
        "pair-file",
        "exception",
        "malformed",
        "failed",
        "short",
        "team",
        "pair",
        "seed",
        "score",
    ],
)
def test_paired_gate_rechecks_after_failure_or_late_change(
    pair_evidence: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root, freeze, evidence, paired, corpus, _reports, _calls, collect = pair_evidence

    def changed(*args: object) -> dict:
        if mutation == "exception":
            raise RuntimeError("Synthetic paired comparison exception")
        result = collect(*args)
        if mutation == "malformed":
            return []
        if mutation == "failed":
            result["errors"].append("Synthetic comparison failure")
        elif mutation == "short":
            result["coverage"]["repetitions"] = 63
        elif mutation == "team":
            result["teams"].pop("Synthetic0")
        elif mutation == "pair":
            result["game_pairs"].pop()
        elif mutation == "seed":
            result["game_pairs"][0]["seed"] += 1
        elif mutation == "score":
            result["game_pairs"][0]["score_delta"]["home"] = True
        elif mutation == "candidate":
            path = (
                root / freeze["cohorts"]["1983-generated"]["season_dir"] / "Synthetic0/offense.csv"
            )
            path.write_text(path.read_text() + "\n")
        elif mutation == "corpus":
            (corpus / "new-directory").mkdir()
        elif mutation in {"source", "training", "pair-file"}:
            binding = (
                paired["generated"]
                if mutation == "pair-file"
                else evidence["source_receipts" if mutation == "source" else "training"]["2024"]
            )
            path = root / binding["path"]
            path.write_text(path.read_text() + "\n")
        elif mutation == "code":
            (root / "paydirt/game_engine.py").write_text("# changed\n")
        elif mutation == "pair-declaration":
            paired["freeze_sha256"] = "0" * 64
        else:
            evidence["corpus"]["teams"]["Synthetic0"]["prior_use"] = "changed"
        return result

    monkeypatch.setattr(reference, "compare_reference_campaigns", changed)
    result = audit(pair_evidence)
    assert not result["passed"] and result["errors"] and not result["paired_validated"]
    assert (
        not result["benchmark_complete"]
        and not result["source_accepted"]
        and not result["release_certified"]
    )
    assert "after" in result["preflights"]


def test_paired_report_changed_during_final_dependency_revalidation_is_rejected(
    pair_evidence: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = gate.audit_reference_corpus_evidence
    calls = 0

    def changed(*args: object) -> dict:
        nonlocal calls
        result = actual(*args)
        calls += 1
        if calls == 2:
            path = pair_evidence[0] / pair_evidence[3]["reference"]["path"]
            path.write_text(path.read_text() + "\n")
        return result

    monkeypatch.setattr(gate, "audit_reference_corpus_evidence", changed)
    result = audit(pair_evidence)
    assert not result["passed"] and result["errors"] and not result["paired_validated"]


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "no-corpus",
        "no-freeze",
        "weighted",
        "contexts",
        "public-output",
        "overwrite",
        "pair-output",
        "changed-paired",
        "changed-declaration",
    ],
)
def test_paired_cli_protects_private_inputs_and_rechecks_original_files(
    pair_evidence: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    from scripts import audit_generated_charts as cli

    root, freeze, evidence, paired, _corpus, _reports, _calls, _collect = pair_evidence
    monkeypatch.setattr(cli, "ROOT", root)
    freeze_path, declaration_path = (
        root / ".ai-audits/freeze.json",
        root / ".ai-audits/declaration.json",
    )
    paired_path = root / ".ai-audits/chart-reference-comparison/paired.json"
    bind(root, freeze_path, freeze)
    bind(root, declaration_path, evidence)
    bind(root, paired_path, paired)
    output = root / ".ai-audits/chart-reference-comparison/result.json"
    if mutation == "public-output":
        output = root / "public-result.json"
    elif mutation == "pair-output":
        output = paired_path
    elif mutation == "overwrite":
        output.write_text("owner sentinel")
    function = getattr(gate, "audit_reference_paired_evidence", None)
    assert callable(function), "Paired CLI must call the maintained gate"

    def checked(*args: object) -> dict:
        result = function(*args)
        if mutation in {"changed-paired", "changed-declaration"}:
            path = paired_path if mutation == "changed-paired" else declaration_path
            path.write_text(path.read_text() + "\n")
        return result

    monkeypatch.setattr(gate, "audit_reference_paired_evidence", checked)
    args = ["--reference-paired", str(paired_path), "--output", str(output)]
    if mutation != "no-corpus":
        args += ["--reference-corpus", str(declaration_path)]
    if mutation != "no-freeze":
        args += ["--freeze", str(freeze_path)]
    if mutation in {"weighted", "contexts"}:
        args += ["--reference-" + mutation]
    assert cli.main(args) == (0 if mutation == "none" else 1)
    if mutation in {"none", "changed-paired", "changed-declaration"}:
        result = json.loads(output.read_text())
        assert result["paired_validated"] is (mutation == "none")
        assert not result["benchmark_complete"] and not result["release_certified"]
    elif mutation == "overwrite":
        assert output.read_text() == "owner sentinel"
    elif mutation == "pair-output":
        assert json.loads(output.read_text()) == paired
    else:
        assert not output.exists()

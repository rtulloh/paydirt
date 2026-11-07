"""Charter preview selection must be derived from bound complete campaign evidence."""
from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
from paydirt.chart_engine_audit import TEAM_TOLERANCES, validate_engine_report
from tests import test_chart_visual_content as support

freeze_files = support.freeze_files
capture_files = support.capture_files
content_files = support.content_files
REAL_VALIDATE = validate_engine_report


@pytest.fixture
def selected_files(content_files: tuple, monkeypatch: pytest.MonkeyPatch) -> tuple:
    root, freeze, original_captures, original_content = content_files
    captures = {"schema_version": 1, "contexts": []}
    content = {"schema_version": 1, "contexts": []}
    reports, calls = {}, []
    for cohort, entry in freeze["cohorts"].items():
        first = "Dolphins" if cohort == "1983-generated" else "Synthetic0"
        names = [first, *[f"Synthetic{i}" for i in range(1, 28 if cohort == "1983-generated" else 32)]]
        contract_path = root / entry["contract"]["path"]
        contract = json.loads(contract_path.read_text())
        contract["teams"] = {}
        for index, name in enumerate(names):
            passing, rushing = ((6.0, 3.0) if index == 0 else (8.0, 5.0) if index == 1 else (7.0, 4.0))
            contract["teams"][name] = {"rates": {"completion_rate": .5, "interception_rate": .02,
                "sack_rate": .06, "yards_per_pass_attempt": passing, "rushing_yards_per_attempt": rushing}}
        entry["contract"] = support.bound(root, contract_path, contract)
        directory = root / entry["season_dir"]
        for name in names[:3]:
            if name != "Synthetic0":
                shutil.copytree(directory / "Synthetic0", directory / name)
        entry["chart_fingerprint"] = gate.chart_fingerprint(directory)
        reports[cohort] = {}
        for phase, seed in (("training", 20261108), ("held_out", 20361108)):
            report = {"valid": True, "metadata": {"seed": seed, "policy": "chart-focused", "repetitions": 64,
                      "team_names": {name: "Engine " + name for name in names}}, "teams": {}}
            for index, name in enumerate(names):
                values = deepcopy(contract["teams"][name]["rates"])
                values["completion_rate"] += .0294 if index == 2 and phase == "training" else .003
                report["teams"]["Engine " + name] = values
            reports[cohort][phase] = report
        old_capture = next(item for item in original_captures["contexts"] if item["cohort"] == cohort)
        receipt_original = json.loads((root / old_capture["capture"]["path"]).read_text())
        old_content = next(item for item in original_content["contexts"] if item["cohort"] == cohort)
        book_original = json.loads((root / old_content["api_book"]["path"]).read_text())
        for name in names[:3]:
            folder = root / ".ai-audits" / "selection" / cohort / name
            receipt = deepcopy(receipt_original)
            receipt["team"] = name
            receipt["chart_fingerprint"] = entry["chart_fingerprint"]
            state = {"game_id": cohort + "-" + name, "quarter": 1,
                     "home_team": {"id": name, "name": name},
                     "away_team": {"id": names[1] if name != names[1] else first, "name": "Opponent"}}
            receipt["state_before"] = support.bound(root, folder / "before.json", state)
            receipt["state_after"] = support.bound(root, folder / "after.json", state)
            book = deepcopy(book_original)
            book["team"] = state["home_team"]
            observed = {"cohort": cohort, "team": name, "api_book": support.bound(root, folder / "api.json", book), "views": {}}
            for view, section in receipt["sections"].items():
                section["url"] = f"http://127.0.0.1:5176/?charts={state['game_id']}&side=home&view={view}"
                observed["views"][view] = support.bound(root, folder / (view + "-dom.json"),
                                                       support.dom_view(book, view, section["url"]))
            captures["contexts"].append({"cohort": cohort, "team": name,
                                         "capture": support.bound(root, folder / "capture.json", receipt)})
            content["contexts"].append(observed)
    freeze_sha = gate.readiness_freeze_fingerprint(freeze)
    captures["freeze_sha256"] = content["freeze_sha256"] = freeze_sha
    for item in captures["contexts"]:
        path = root / item["capture"]["path"]
        receipt = json.loads(path.read_text())
        receipt["freeze_sha256"] = freeze_sha
        item["capture"] = support.bound(root, path, receipt)
    content["captures_sha256"] = gate.readiness_freeze_fingerprint(captures)
    evidence = {"schema_version": 1, "freeze_sha256": freeze_sha,
                "captures_sha256": gate.readiness_freeze_fingerprint(captures),
                "content_sha256": gate.readiness_freeze_fingerprint(content), "cohorts": {}}
    for cohort, phases in reports.items():
        evidence["cohorts"][cohort] = {
            phase: support.bound(root, root / ".ai-audits/selection" / cohort / (phase + ".json"), report)
            for phase, report in phases.items()}

    def validate(report: dict, contract: dict, directory: Path, **requirements: object) -> dict:
        calls.append((report, contract, directory, requirements))
        if report.get("raise"):
            raise ValueError("Synthetic campaign validation exception")
        team_metrics = {folder: {metric: {"observed": report["teams"][engine][metric],
            "target": contract["teams"][folder]["rates"][metric],
            "absolute_error": abs(report["teams"][engine][metric] - contract["teams"][folder]["rates"][metric]),
            "tolerance": tolerance, "passed": True} for metric, tolerance in TEAM_TOLERANCES.items()}
            for folder, engine in report["metadata"]["team_names"].items()}
        return {"passed": report.get("valid", True), "errors": report.get("errors", []), "team_metrics": team_metrics}
    monkeypatch.setattr(gate, "validate_engine_report", validate)
    return root, freeze, captures, content, evidence, reports, calls


def audit(files: tuple) -> dict:
    function = getattr(gate, "audit_visual_selection_evidence", None)
    assert callable(function), "Readiness must derive charter preview representatives from actual bound campaigns"
    return function(*files[:5])


def rewrite(files: tuple, cohort: str, phase: str) -> None:
    root, _freeze, _captures, _content, evidence, reports, _calls = files
    reference = evidence["cohorts"][cohort][phase]
    evidence["cohorts"][cohort][phase] = support.bound(root, root / reference["path"], reports[cohort][phase])


def test_source_and_campaign_roles_are_derived_and_noncertifying(selected_files: tuple) -> None:
    result = audit(selected_files)
    assert result["passed"], result["errors"]
    assert result["selection_validated"] is True
    assert result["release_certified"] is False and result["ready_for_owner_review"] is False
    assert result["source_accepted"] is False
    for cohort, details in result["cohorts"].items():
        first = "Dolphins" if cohort == "1983-generated" else "Synthetic0"
        assert details["worst_outlier"]["team"] == "Synthetic2"
        assert details["worst_outlier"]["phase"] == "training"
        assert details["strong_source_offense"]["team"] == "Synthetic1"
        assert details["weak_source_offense"]["team"] == first
    assert len(selected_files[-1]) == 4
    assert all(call[-1] == {"minimum_repetitions": 64, "minimum_team_games": 1000, "require_fit": True}
               for call in selected_files[-1])


@pytest.mark.parametrize("mutation", [
    "version", "version-bool", "extra", "freeze", "captures-binding", "content-binding",
    "missing-cohort", "extra-cohort", "missing-phase", "extra-phase", "bad-digest", "missing-file",
    "symlink", "duplicate-json", "nonfinite-json", "training-seed", "heldout-seed", "seed-bool",
    "wrong-policy", "nested-failed", "nested-errors", "nested-string-pass", "raised",
    "missing-team", "unknown-engine-team", "bool-metric", "missing-metric", "no-source-contrast",
    "changed-chart", "changed-dom",
])
def test_bad_or_substituted_selection_inputs_fail(selected_files: tuple, mutation: str) -> None:
    root, freeze, _captures, content, evidence, reports, _calls = selected_files
    cohort, phase = "1983-generated", "training"
    reference = evidence["cohorts"][cohort][phase]
    path = root / reference["path"]
    report = reports[cohort][phase]
    if mutation == "version": evidence["schema_version"] = 2
    elif mutation == "version-bool": evidence["schema_version"] = True
    elif mutation == "extra": evidence["passed"] = True
    elif mutation == "freeze": evidence["freeze_sha256"] = "0" * 64
    elif mutation == "captures-binding": evidence["captures_sha256"] = "0" * 64
    elif mutation == "content-binding": evidence["content_sha256"] = "0" * 64
    elif mutation == "missing-cohort": del evidence["cohorts"]["2024"]
    elif mutation == "extra-cohort": evidence["cohorts"]["2026"] = deepcopy(evidence["cohorts"]["2024"])
    elif mutation == "missing-phase": del evidence["cohorts"][cohort]["held_out"]
    elif mutation == "extra-phase": evidence["cohorts"][cohort]["hard"] = deepcopy(reference)
    elif mutation == "bad-digest": reference["sha256"] = "0" * 64
    elif mutation == "missing-file": path.unlink()
    elif mutation == "symlink":
        other = path.with_suffix(".backup")
        path.rename(other)
        path.symlink_to(other)
    elif mutation == "duplicate-json":
        reference.update(support.bound(root, path, b'{"metadata":{},"metadata":{}}'))
    elif mutation == "nonfinite-json":
        reference.update(support.bound(root, path, b'{"metadata":{"seed":NaN}}'))
    elif mutation == "training-seed": report["metadata"]["seed"] = 20361108; rewrite(selected_files, cohort, phase)
    elif mutation == "heldout-seed":
        reports[cohort]["held_out"]["metadata"]["seed"] = 20261108
        rewrite(selected_files, cohort, "held_out")
    elif mutation == "seed-bool": report["metadata"]["seed"] = True; rewrite(selected_files, cohort, phase)
    elif mutation == "wrong-policy": report["metadata"]["policy"] = "balanced"; rewrite(selected_files, cohort, phase)
    elif mutation == "nested-failed": report["valid"] = False; rewrite(selected_files, cohort, phase)
    elif mutation == "nested-errors": report["errors"] = ["Bad individual team"]; rewrite(selected_files, cohort, phase)
    elif mutation == "nested-string-pass": report["valid"] = "yes"; rewrite(selected_files, cohort, phase)
    elif mutation == "raised": report["raise"] = True; rewrite(selected_files, cohort, phase)
    elif mutation == "missing-team": report["metadata"]["team_names"].pop("Synthetic2"); rewrite(selected_files, cohort, phase)
    elif mutation == "unknown-engine-team": report["metadata"]["team_names"]["Synthetic2"] = "Unknown"; rewrite(selected_files, cohort, phase)
    elif mutation == "bool-metric": report["teams"]["Engine Synthetic2"]["completion_rate"] = True; rewrite(selected_files, cohort, phase)
    elif mutation == "missing-metric": del report["teams"]["Engine Synthetic2"]["completion_rate"]; rewrite(selected_files, cohort, phase)
    elif mutation == "no-source-contrast":
        contract_path = root / freeze["cohorts"][cohort]["contract"]["path"]
        contract = json.loads(contract_path.read_text())
        for team in contract["teams"].values():
            team["rates"].update(yards_per_pass_attempt=7, rushing_yards_per_attempt=4)
        freeze["cohorts"][cohort]["contract"] = support.bound(root, contract_path, contract)
        for report_phase, values in reports[cohort].items():
            for team in values["teams"].values():
                team.update(yards_per_pass_attempt=7, rushing_yards_per_attempt=4)
            rewrite(selected_files, cohort, report_phase)
        refresh_bindings(selected_files)
    elif mutation == "changed-chart":
        (root / freeze["cohorts"][cohort]["season_dir"] / "Synthetic2/offense.csv").write_text("Changed")
    elif mutation == "changed-dom":
        (root / content["contexts"][0]["views"]["offense"]["path"]).write_text("{}")
    result = audit(selected_files)
    assert result["passed"] is False and result["selection_validated"] is False
    assert result["errors"]
    assert result["release_certified"] is False


@pytest.mark.parametrize("cohort", ["1983-generated", "2024"])
@pytest.mark.parametrize("team_index", [0, 1, 2])
def test_every_required_context_must_be_present(selected_files: tuple, cohort: str, team_index: int) -> None:
    _root, _freeze, captures, content, evidence, *_ = selected_files
    selected = [entry for entry in captures["contexts"] if entry["cohort"] == cohort][team_index]
    captures["contexts"].remove(selected)
    content["contexts"] = [entry for entry in content["contexts"] if (entry["cohort"], entry["team"]) != (cohort, selected["team"])]
    content["captures_sha256"] = evidence["captures_sha256"] = gate.readiness_freeze_fingerprint(captures)
    evidence["content_sha256"] = gate.readiness_freeze_fingerprint(content)
    assert gate.audit_visual_content_evidence(*selected_files[:4])["passed"]
    result = audit(selected_files)
    assert not result["passed"] and not result["selection_validated"]


def test_actual_campaign_validator_rejects_short_synthetic_reports(selected_files: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "validate_engine_report", REAL_VALIDATE)
    result = audit(selected_files)
    assert not result["passed"] and not result["selection_validated"]
    assert any("runtime" in error.lower() or "evidence" in error.lower() for error in result["errors"])


def test_heldout_can_supply_the_worst_outlier(selected_files: tuple) -> None:
    reports = selected_files[-2]
    report = reports["2024"]["held_out"]
    report["teams"]["Engine Synthetic0"]["completion_rate"] = .5297
    rewrite(selected_files, "2024", "held_out")
    result = audit(selected_files)
    assert result["passed"], result["errors"]
    assert result["cohorts"]["2024"]["worst_outlier"]["team"] == "Synthetic0"
    assert result["cohorts"]["2024"]["worst_outlier"]["phase"] == "held_out"


def refresh_bindings(files: tuple) -> None:
    root, freeze, captures, content, evidence, *_ = files
    freeze_sha = gate.readiness_freeze_fingerprint(freeze)
    captures["freeze_sha256"] = content["freeze_sha256"] = evidence["freeze_sha256"] = freeze_sha
    for item in captures["contexts"]:
        path = root / item["capture"]["path"]
        receipt = json.loads(path.read_text())
        receipt["freeze_sha256"] = freeze_sha
        item["capture"] = support.bound(root, path, receipt)
    content["captures_sha256"] = evidence["captures_sha256"] = gate.readiness_freeze_fingerprint(captures)
    evidence["content_sha256"] = gate.readiness_freeze_fingerprint(content)


def test_synthetic_selected_captures_pass_existing_content_control(selected_files: tuple) -> None:
    result = gate.audit_visual_content_evidence(*selected_files[:4])
    assert result["passed"], result["errors"]
    assert result["tables_checked"] == 24 and result["cells_checked"] == 5220


def test_outlier_uses_fixed_tolerance_units(selected_files: tuple) -> None:
    reports = selected_files[-2]
    for phase in ("training", "held_out"):
        for team in reports["2024"][phase]["teams"].values():
            team["completion_rate"] = .503
    reports["2024"]["training"]["teams"]["Engine Synthetic0"]["interception_rate"] = .0299
    reports["2024"]["training"]["teams"]["Engine Synthetic2"]["yards_per_pass_attempt"] = 7.6
    for phase in ("training", "held_out"):
        rewrite(selected_files, "2024", phase)
    result = audit(selected_files)
    assert result["passed"], result["errors"]
    worst = result["cohorts"]["2024"]["worst_outlier"]
    assert worst["team"] == "Synthetic0" and worst["metric"] == "interception_rate"
    assert worst["normalized_error"] == pytest.approx(.99)


def test_exact_outlier_ties_use_folder_then_phase(selected_files: tuple) -> None:
    for phase in ("training", "held_out"):
        selected_files[-2]["2024"][phase]["teams"]["Engine Synthetic0"]["completion_rate"] = .5294
        rewrite(selected_files, "2024", phase)
    result = audit(selected_files)
    assert result["passed"], result["errors"]
    assert result["cohorts"]["2024"]["worst_outlier"]["team"] == "Synthetic0"
    assert result["cohorts"]["2024"]["worst_outlier"]["phase"] == "training"


@pytest.mark.parametrize("target", ["campaign", "content", "freeze", "campaign-symlink"])
def test_inputs_are_rechecked_after_all_campaigns(selected_files: tuple, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    original = gate.validate_engine_report
    def validate(*args: object, **kwargs: object) -> dict:
        result = original(*args, **kwargs)
        if len(selected_files[-1]) == 4:
            if target == "campaign":
                (selected_files[0] / selected_files[4]["cohorts"]["1983-generated"]["training"]["path"]).write_text("{}")
            elif target == "campaign-symlink":
                path = selected_files[0] / selected_files[4]["cohorts"]["1983-generated"]["training"]["path"]
                backup = path.with_suffix(".backup")
                path.rename(backup)
                path.symlink_to(backup)
            elif target == "content":
                selected_files[3]["contexts"][0]["api_book"]["sha256"] = "0" * 64
            else:
                selected_files[1]["files"]["AGENTS.md"] = "0" * 64
        return result
    monkeypatch.setattr(gate, "validate_engine_report", validate)
    result = audit(selected_files)
    assert not result["passed"] and not result["selection_validated"]


def test_first_cohort_exception_does_not_hide_the_other_cohort(selected_files: tuple) -> None:
    selected_files[-2]["1983-generated"]["training"]["raise"] = True
    rewrite(selected_files, "1983-generated", "training")
    result = audit(selected_files)
    assert not result["passed"]
    assert result["cohorts"]["2024"]["worst_outlier"]["team"] == "Synthetic2"
    assert len(selected_files[-1]) == 4


@pytest.mark.parametrize("mode", ["valid", "bad-binding", "missing-content", "missing-capture",
                                  "missing-freeze", "existing-output", "selection-changed"])
def test_existing_visual_cli_accepts_and_binds_selection_evidence(
    selected_files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    from scripts import audit_generated_charts as cli
    root, freeze, captures, content, evidence, *_ = selected_files
    monkeypatch.setattr(cli, "ROOT", root)
    folder = root / ".ai-audits/selection-cli"
    folder.mkdir()
    for name, value in (("freeze", freeze), ("captures", captures), ("content", content), ("selection", evidence)):
        support.bound(root, folder / (name + ".json"), value)
    if mode == "bad-binding":
        evidence["content_sha256"] = "0" * 64
        (folder / "selection.json").write_text(json.dumps(evidence))
    output = root / ".ai-audits/selection-result.json"
    if mode == "existing-output": output.write_text("Preserve\n")
    if mode == "selection-changed":
        original = gate.audit_visual_selection_evidence
        def validate(*args: object) -> dict:
            result = original(*args)
            (folder / "selection.json").write_text("{}")
            return result
        monkeypatch.setattr(gate, "audit_visual_selection_evidence", validate)
    arguments = ["--output", str(output), "--visual-selection", str(folder / "selection.json")]
    for mode_name, flag, filename in (("missing-freeze", "--freeze", "freeze"),
                                      ("missing-capture", "--visual-capture", "captures"),
                                      ("missing-content", "--visual-content", "content")):
        if mode != mode_name:
            arguments.extend((flag, str(folder / (filename + ".json"))))
    assert cli.main(arguments) == (0 if mode == "valid" else 1)
    if mode in {"missing-content", "missing-capture", "missing-freeze"}:
        assert not output.exists()
    elif mode == "existing-output":
        assert output.read_text() == "Preserve\n"
    else:
        result = json.loads(output.read_text())
        assert result["passed"] is (mode == "valid")
        assert result["selection_validated"] is (mode == "valid")
        assert result["release_certified"] is False
        assert "selection" in result["input_files"]


@pytest.mark.parametrize("bad", [None, [], {"passed": True}, {"passed": True, "errors": None}])
def test_malformed_nested_campaign_results_fail_without_hiding_other_cohort(
    selected_files: tuple, monkeypatch: pytest.MonkeyPatch, bad: object,
) -> None:
    original = gate.validate_engine_report
    def validate(*args: object, **kwargs: object) -> object:
        result = original(*args, **kwargs)
        return deepcopy(bad) if len(selected_files[-1]) == 1 else result
    monkeypatch.setattr(gate, "validate_engine_report", validate)
    result = audit(selected_files)
    assert not result["passed"] and not result["selection_validated"]
    assert result["cohorts"]["2024"]["worst_outlier"]["team"] == "Synthetic2"
    assert len(selected_files[-1]) == 4


def test_average_source_ties_and_alphabetical_strength_tie_break() -> None:
    from paydirt.chart_preview_selection_audit import preview_selection_roles
    rates = {name: {"completion_rate": .5, "interception_rate": .02, "sack_rate": .06,
                    "yards_per_pass_attempt": passing, "rushing_yards_per_attempt": rushing}
             for name, passing, rushing in (("A", 6, 5), ("B", 6, 3), ("C", 8, 3))}
    contract = {"teams": {name: {"rates": values} for name, values in rates.items()}}
    reports = {phase: {"metadata": {"team_names": {name: name for name in rates}}, "teams": deepcopy(rates)}
               for phase in ("training", "held_out")}
    result = preview_selection_roles(contract, reports)
    assert result["strong_source_offense"]["team"] == "A"
    assert result["strong_source_offense"]["source_ranks"] == {
        "yards_per_pass_attempt": 1.5, "rushing_yards_per_attempt": 3.0}
    assert result["weak_source_offense"]["team"] == "B"
    assert result["weak_source_offense"]["rank_sum"] == 3.0


@pytest.mark.parametrize("observed,target", [(1e308, -1e308), (1e308, .02)])
def test_finite_metric_arithmetic_cannot_emit_nonfinite_errors(observed: float, target: float) -> None:
    from paydirt.chart_preview_selection_audit import preview_selection_roles
    rates = {name: {"completion_rate": .5, "interception_rate": target, "sack_rate": .06,
                    "yards_per_pass_attempt": 6 + index, "rushing_yards_per_attempt": 3 + index}
             for index, name in enumerate(("A", "B"))}
    contract = {"teams": {name: {"rates": values} for name, values in rates.items()}}
    reports = {phase: {"metadata": {"team_names": {name: name for name in rates}}, "teams": deepcopy(rates)}
               for phase in ("training", "held_out")}
    reports["training"]["teams"]["A"]["interception_rate"] = observed
    with pytest.raises(ValueError, match="finite"):
        preview_selection_roles(contract, reports)

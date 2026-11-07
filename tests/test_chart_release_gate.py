"""A release must fail closed if any independent chart check rejects it."""
import json
from pathlib import Path

import pytest
import yaml

from paydirt.chart_release_gate import audit_release


@pytest.mark.parametrize("failed", ("source", "tactics", "allocation", "engine"))
def test_any_failed_component_blocks_release(monkeypatch: pytest.MonkeyPatch, failed: str) -> None:
    import paydirt.chart_release_gate as gate
    results = {name: {"passed": name != failed, "errors": ["defect"] if name == failed else []}
               for name in ("source", "tactics", "allocation", "engine")}
    monkeypatch.setattr(gate, "_components", lambda *_: results)
    result = audit_release(Path("synthetic"), {}, {})
    assert not result["passed"]
    assert any(failed in error for error in result["errors"])


def test_no_components_or_missing_evidence_cannot_certify_release(monkeypatch: pytest.MonkeyPatch) -> None:
    import paydirt.chart_release_gate as gate
    monkeypatch.setattr(gate, "_components", lambda *_: {})
    assert not audit_release(Path("synthetic"), {}, {})["passed"]


def test_contradictory_success_with_reported_errors_blocks_release(monkeypatch: pytest.MonkeyPatch) -> None:
    import paydirt.chart_release_gate as gate
    monkeypatch.setattr(gate, "_components", lambda *_: {
        name: {"passed": True, "errors": ["unresolved"] if name == "source" else []}
        for name in ("source", "tactics", "allocation", "engine")
    })
    assert not audit_release(Path("synthetic"), {}, {})["passed"]


def test_all_declared_components_required_to_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    import paydirt.chart_release_gate as gate
    monkeypatch.setattr(gate, "_components", lambda *_: {
        name: {"passed": True, "errors": [], "checks": dict.fromkeys(
            ("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"), True,
        )}
        for name in ("source", "tactics", "allocation", "engine")
    })
    assert audit_release(Path("synthetic"), {}, {})["passed"]


def test_component_pass_does_not_certify_entire_charter(monkeypatch):
    import paydirt.chart_release_gate as gate

    monkeypatch.setattr(gate, "_components", lambda *_: {
        name: {"passed": True, "errors": [], "checks": dict.fromkeys(
            ("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"), True,
        )} for name in ("source", "tactics", "allocation", "engine")
    })
    report = gate.audit_release(Path("synthetic"), {}, {})
    assert report["passed"]
    assert report["release_certified"] is False
    assert "component" in report["scope"].casefold()


def test_source_success_without_decoder_evidence_blocks_release(monkeypatch):
    import paydirt.chart_release_gate as gate

    components = {
        name: {"passed": True, "errors": []}
        for name in ("source", "tactics", "allocation", "engine")
    }
    components["source"]["checks"] = dict.fromkeys(
        ("raw_inputs", "normalized_stats", "source_hashes", "reproduction"), True,
    )
    monkeypatch.setattr(gate, "_components", lambda *_: components)
    report = gate.audit_release(Path("synthetic"), {}, {})
    assert not report["passed"]
    assert any("decoder" in error for error in report["errors"])


@pytest.mark.parametrize("missing", ("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"))
def test_component_success_cannot_hide_unverified_source_evidence(monkeypatch, missing):
    import paydirt.chart_release_gate as gate

    checks = dict.fromkeys(("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"), True)
    checks[missing] = False
    components = {name: {"passed": True, "errors": []}
                  for name in ("source", "tactics", "allocation", "engine")}
    components["source"]["checks"] = checks
    monkeypatch.setattr(gate, "_components", lambda *_: components)
    report = gate.audit_release(Path("synthetic"), {}, {})
    assert not report["passed"]
    assert any(missing in error for error in report["errors"])


def test_combined_gate_passes_actual_source_inputs_to_source_validator(tmp_path, monkeypatch):
    import paydirt.chart_release_gate as gate

    captured = {}

    def source(*_args, **kwargs):
        captured.update(kwargs)
        return {"passed": False, "errors": ["sentinel"]}

    monkeypatch.setattr(gate, "audit_generated_source", source)
    monkeypatch.setattr(gate, "audit_observer_conformance", lambda: {"passed": True, "errors": []})
    monkeypatch.setattr(gate, "validate_engine_report", lambda *_a, **_k: {"passed": True, "errors": []})
    files = {"play_by_play/public.csv": tmp_path / "source.csv"}
    gate.audit_release(tmp_path, {}, {}, stats_dir=tmp_path / "stats",
                       reproduced_dir=tmp_path / "reproduced", input_files=files)
    assert captured["stats_dir"] == tmp_path / "stats"
    assert captured["reproduced_dir"] == tmp_path / "reproduced"
    assert captured["input_files"] == files


def test_cli_forwards_source_verification_paths(tmp_path, monkeypatch):
    import paydirt.chart_release_gate as gate
    import scripts.audit_generated_charts as cli

    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"schedule": [{"away": "A", "home": "B"}]}))
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps({"play_by_play/public.csv": "source.csv"}))
    captured = {}

    def audit(*_args, **kwargs):
        captured.update(kwargs)
        return {"passed": True}

    monkeypatch.setattr(gate, "audit_release", audit)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *_a, **_k: {
        "metadata": {"attempt_end_zone_interception_returns": False},
    })
    assert cli.main([
        "--season-dir", str(tmp_path), "--contract", str(contract),
        "--output", str(tmp_path / "output.json"), "--source-inputs", str(inputs),
        "--source-stats-dir", str(tmp_path / "stats"), "--reproduced-dir", str(tmp_path / "reproduced"),
    ]) == 0
    assert captured["input_files"] == {"play_by_play/public.csv": tmp_path / "source.csv"}
    assert captured["stats_dir"] == tmp_path / "stats"
    assert captured["reproduced_dir"] == tmp_path / "reproduced"


def test_cli_rejects_missing_source_evidence_before_starting_campaign(tmp_path, monkeypatch):
    import scripts.audit_generated_charts as cli

    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"schedule": [{"away": "A", "home": "B"}]}))
    output = tmp_path / "failure.json"

    def unexpected_campaign(*_args, **_kwargs):
        pytest.fail("A missing source inventory must be rejected before a long campaign")

    monkeypatch.setattr(cli, "run_engine_audit", unexpected_campaign)
    assert cli.main(["--season-dir", str(tmp_path), "--contract", str(contract),
                     "--output", str(output)]) == 1
    assert "source" in json.loads(output.read_text())["errors"][0].casefold()


@pytest.mark.parametrize("policy", ["repeat-line-plunge", "repeat-te-short-long"])
def test_cli_collects_repeat_policy_as_mechanics_stress(tmp_path, monkeypatch, policy):
    import scripts.audit_generated_charts as cli

    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"schedule": [{"away": "A", "home": "B"}]}))
    monkeypatch.setattr(cli, "run_engine_audit", lambda *_a, **_k: {
        "metadata": {"policy": policy, "attempt_end_zone_interception_returns": False},
    })
    requirements = {}

    def validate(*_args, **kwargs):
        requirements.update(kwargs)
        return {"passed": True, "errors": []}

    monkeypatch.setattr(cli, "validate_engine_report", validate)
    output = tmp_path / "repeat.json"
    assert cli.main(["--season-dir", str(tmp_path), "--contract", str(contract),
                     "--output", str(output), "--policy", policy, "--repetitions", "1",
                     "--engine-only"]) == 0
    assert requirements == {"minimum_team_games": 16, "minimum_repetitions": 1,
                            "require_fit": False}
    assert json.loads(output.read_text())["release_certified"] is False


@pytest.mark.parametrize("workflow", ("test.yml", "release.yml"))
def test_workflows_enforce_both_public_generated_cohorts(workflow: str) -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github" / "workflows" / workflow).read_text()
    assert "scripts/audit_generated_charts.py" in text
    assert "1983-generated" in text and "2024" in text
    assert "--repetitions 64" in text
    assert "continue-on-error" not in text[text.index("  chart-quality:"):].split("\n  build:")[0]


def test_release_builds_wait_for_chart_quality_success() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/release.yml").read_text())
    assert "chart-quality" in workflow["jobs"]["build"]["needs"]


def test_combined_gate_catches_reintroduced_selected_priority_bug(monkeypatch: pytest.MonkeyPatch) -> None:
    import paydirt.chart_release_gate as gate
    from paydirt import play_resolver

    original = play_resolver.resolve_play

    def discard_selected_semantics(*args, **kwargs):
        result = original(*args, **kwargs)
        if "INT" in result.defense_modifier:
            result.result_type = play_resolver.ResultType.INTERCEPTION
        return result

    monkeypatch.setattr(play_resolver, "resolve_play", discard_selected_semantics)
    public = Path(__file__).resolve().parents[1] / "seasons/2026"
    monkeypatch.setattr(gate, "audit_generated_source", lambda *_a, **_k: {"passed": True})
    monkeypatch.setattr(gate, "audit_allocations", lambda: {"passed": True})
    monkeypatch.setattr(gate, "validate_engine_report", lambda *_a, **_k: {"passed": True})
    result = audit_release(public, {}, {})
    assert not result["passed"]
    assert any("fumble" in error for error in result["errors"])


def test_cli_preserves_failure_evidence_for_invalid_inputs(tmp_path: Path) -> None:
    from scripts.audit_generated_charts import main
    output = tmp_path / "failure.json"
    status = main([
        "--season-dir", str(tmp_path), "--contract", str(tmp_path / "missing.json"),
        "--output", str(output),
    ])
    assert status == 1
    evidence = json.loads(output.read_text())
    assert evidence["passed"] is False
    assert evidence["errors"]


def test_combined_gate_retains_exact_mechanics_and_blocks_lost_mass(monkeypatch):
    import paydirt.chart_release_gate as gate

    public = Path(__file__).resolve().parents[1] / "seasons/2026"
    monkeypatch.setattr(gate, "audit_generated_source", lambda *_a, **_k: {"passed": True})
    monkeypatch.setattr(gate, "audit_allocations", lambda: {"passed": True})
    monkeypatch.setattr(gate, "validate_engine_report", lambda *_a, **_k: {"passed": True})
    control = audit_release(public, {}, {})
    exact = control["components"]["tactics"].get("exact_mechanics", {})
    assert set(exact) == {"Ironclads", "Thunderhawks"}
    original = gate.audit_season

    def corrupted(*args, **kwargs):
        result = original(*args, **kwargs)
        result["exact_mechanics"]["Ironclads"]["plays"]["short_pass/A"]["exact_total_mass"] = [1, 2]
        return result

    monkeypatch.setattr(gate, "audit_season", corrupted)
    result = audit_release(public, {}, {})
    assert not result["passed"]
    assert any("mass" in error for error in result["errors"])


def test_cli_declares_training_seed_and_separates_policy_mechanics(tmp_path, monkeypatch):
    import scripts.audit_generated_charts as cli

    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"schedule": [{"away": "A", "home": "B"}]}))
    captured = {}

    def run(*args, **kwargs):
        captured.update(kwargs)
        return {"metadata": {"attempt_end_zone_interception_returns": False}}

    def validate(*args, **kwargs):
        captured["validation"] = kwargs
        return {"passed": True}

    monkeypatch.setattr(cli, "run_engine_audit", run)
    monkeypatch.setattr(cli, "validate_engine_report", validate)
    status = cli.main(["--season-dir", str(tmp_path), "--contract", str(contract),
                       "--output", str(tmp_path / "report.json"), "--engine-only", "--policy", "hard"])
    assert status == 0
    assert captured["seed"] == 20261108
    assert captured["validation"]["require_fit"] is False
    assert captured["validation"]["minimum_team_games"] == 128
    assert captured["validation"].get("minimum_repetitions") == 8


def test_full_component_gate_requires_sixty_four_independent_schedules(monkeypatch):
    import paydirt.chart_release_gate as gate

    captured = {}

    def validate(*args, **kwargs):
        captured.update(kwargs)
        return {"passed": True, "errors": []}

    monkeypatch.setattr(gate, "validate_engine_report", validate)
    public = Path(__file__).resolve().parents[1] / "seasons" / "2026"
    gate._components(public, {}, {})
    assert captured.get("minimum_repetitions") == 64

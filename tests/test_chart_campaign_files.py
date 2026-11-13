"""Actual campaign files are bound before their semantic validator sees them."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
from paydirt.chart_engine_audit import chart_fingerprint

CampaignFiles = tuple[Path, dict, list]

POLICIES = (
    "hard",
    "balanced",
    "run-heavy",
    "pass-heavy",
    "repeat-line-plunge",
    "repeat-off-tackle",
    "repeat-end-run",
    "repeat-draw",
    "repeat-screen",
    "repeat-short-pass",
    "repeat-medium-pass",
    "repeat-long-pass",
    "repeat-te-short-long",
)


@pytest.fixture
def campaign_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict, list]:
    calls = []

    def validate(report: dict, contract: dict, directory: Path, **options: object) -> dict:
        calls.append((report, contract, directory, options))
        return {"passed": True, "errors": []}

    monkeypatch.setattr(gate, "validate_engine_report", validate)

    def artifact(name: str, data: dict) -> dict:
        path = tmp_path / name
        path.write_text(json.dumps(data) + "\n")
        return {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    cohorts = {}
    for name, season, count in (("1983-generated", 1983, 28), ("2024", 2024, 32)):
        charts = tmp_path / name
        charts.mkdir()
        (charts / "offense.csv").write_text("Synthetic chart bytes\n")
        cohorts[name] = {
            "season_dir": name,
            "chart_fingerprint": chart_fingerprint(charts),
            "contract": artifact(
                name + "-contract.json",
                {"season": season, "teams": {f"Synthetic{i}": {} for i in range(count)}},
            ),
            "training": artifact(
                name + "-training.json", {"metadata": {"policy": "chart-focused", "seed": 20261108}}
            ),
            "held_out": artifact(
                name + "-held-out.json", {"metadata": {"policy": "chart-focused", "seed": 20361108}}
            ),
            "policies": {
                policy: artifact(
                    name + "-" + policy + ".json",
                    {"metadata": {"policy": policy, "seed": 20261108}},
                )
                for policy in POLICIES
            },
        }
    return tmp_path / "bundle.json", {"schema_version": 1, "cohorts": cohorts}, calls


def audit(path: Path, data: dict) -> dict:
    path.write_text(json.dumps(data) + "\n")
    function = getattr(gate, "audit_campaign_bundle_file", None)
    assert callable(function), "Campaign census must verify actual bound files"
    return function(path)


def test_bound_campaign_file_loads_all_reports_and_keeps_component_scope(
    campaign_files: CampaignFiles,
) -> None:
    path, data, calls = campaign_files
    result = audit(path, data)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert len(calls) == 30
    assert all(call[2].is_absolute() for call in calls)
    assert result["binding"]["artifacts_verified"] == 32


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-file",
        "changed-file",
        "wrong-digest",
        "unbound",
        "missing-contract",
        "changed-charts",
        "wrong-chart-digest",
        "missing-cohort",
        "extra-cohort",
        "missing-policy",
        "extra-policy",
        "wrong-version",
        "wrong-inventory",
        "extra-field",
        "scalar-json",
        "duplicate-json",
        "nonfinite-json",
    ],
)
def test_campaign_file_mutants_fail_before_any_unbound_success(
    campaign_files: CampaignFiles, mutation: str
) -> None:
    path, original, _calls = campaign_files
    data = deepcopy(original)
    cohort = data["cohorts"]["2024"]
    target = path.parent / cohort["training"]["path"]
    if mutation == "missing-file":
        target.unlink()
    elif mutation == "changed-file":
        target.write_text(target.read_text() + " ")
    elif mutation == "wrong-digest":
        cohort["training"]["sha256"] = "0" * 64
    elif mutation == "unbound":
        cohort["training"] = cohort["training"]["path"]
    elif mutation == "missing-contract":
        (path.parent / cohort["contract"]["path"]).unlink()
    elif mutation == "changed-charts":
        (path.parent / cohort["season_dir"] / "offense.csv").write_text("Changed\n")
    elif mutation == "wrong-chart-digest":
        cohort["chart_fingerprint"] = "0" * 64
    elif mutation == "missing-cohort":
        data["cohorts"].pop("2024")
    elif mutation == "extra-cohort":
        data["cohorts"]["2023"] = deepcopy(cohort)
    elif mutation == "missing-policy":
        cohort["policies"].pop("repeat-screen")
    elif mutation == "extra-policy":
        cohort["policies"]["undeclared"] = deepcopy(cohort["policies"]["hard"])
    elif mutation == "wrong-version":
        data["schema_version"] = 2
    elif mutation == "wrong-inventory":
        data["cohorts"] = []
    elif mutation == "extra-field":
        cohort["passed"] = True
    elif mutation in {"scalar-json", "duplicate-json", "nonfinite-json"}:
        text = {
            "scalar-json": "true",
            "duplicate-json": '{"metadata":{},"metadata":{}}',
            "nonfinite-json": '{"metadata":{"seed":NaN}}',
        }[mutation]
        target.write_text(text)
        cohort["training"]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    result = audit(path, data)
    assert not result["passed"]
    assert result["errors"]
    assert result["release_certified"] is False


def test_missing_bundle_is_a_structured_failure(tmp_path: Path) -> None:
    function = getattr(gate, "audit_campaign_bundle_file", None)
    assert callable(function), "Campaign file entry point must fail closed"
    result = function(tmp_path / "absent.json")
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False


def test_bound_files_do_not_hide_a_semantic_failure(
    campaign_files: CampaignFiles,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, data, _calls = campaign_files
    monkeypatch.setattr(
        gate,
        "validate_engine_report",
        lambda *args, **kwargs: {
            "passed": False,
            "errors": ["Independent fit failure"],
        },
    )
    result = audit(path, data)
    assert not result["passed"]
    assert result["binding"]["passed"] is True
    assert not result["census"]["passed"]
    assert any("Independent fit failure" in reason for reason in result["errors"])


@pytest.mark.parametrize("valid", [True, False])
def test_campaign_bundle_cli_validates_saved_files_without_running_games(
    campaign_files: CampaignFiles,
    monkeypatch: pytest.MonkeyPatch,
    valid: bool,
) -> None:
    from scripts import audit_generated_charts as cli

    path, data, _calls = campaign_files
    if not valid:
        data["cohorts"]["2024"]["training"]["sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    monkeypatch.setattr(
        cli,
        "run_engine_audit",
        lambda *args, **kwargs: pytest.fail("Bundle validation must not start games"),
    )
    output = path.parent / "result.json"
    assert cli.main(["--campaign-bundle", str(path), "--output", str(output)]) == (
        0 if valid else 1
    )
    result = json.loads(output.read_text())
    assert result["passed"] is valid
    assert result["release_certified"] is False


@pytest.mark.parametrize(
    "extra",
    [
        ["--engine-only"],
        ["--season-dir", "other"],
        ["--engine-report", "other.json"],
        ["--policy", "hard"],
        ["--seed", "1"],
        ["--repetitions", "1"],
    ],
)
def test_campaign_bundle_cli_rejects_conflicting_campaign_options(
    campaign_files: CampaignFiles,
    extra: list[str],
) -> None:
    from scripts import audit_generated_charts as cli

    path, data, _calls = campaign_files
    path.write_text(json.dumps(data))
    output = path.parent / "result.json"
    assert cli.main(["--campaign-bundle", str(path), "--output", str(output), *extra]) == 1
    result = json.loads(output.read_text())
    assert not result["passed"] and result["errors"]


@pytest.mark.parametrize("target", ["bundle", "report", "chart", "failed-report"])
def test_campaign_cli_never_overwrites_its_evidence(
    campaign_files: CampaignFiles, target: str
) -> None:
    from scripts import audit_generated_charts as cli

    path, data, _calls = campaign_files
    entry = data["cohorts"]["2024"]
    if target == "failed-report":
        entry["training"]["sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    output = (
        path
        if target == "bundle"
        else path.parent / entry["season_dir"] / "offense.csv"
        if target == "chart"
        else path.parent / entry["training"]["path"]
    )
    before = output.read_bytes()
    assert cli.main(["--campaign-bundle", str(path), "--output", str(output)]) == 1
    assert output.read_bytes() == before


def test_campaign_file_rejects_float_overflow_even_with_matching_digest(
    campaign_files: CampaignFiles,
) -> None:
    path, data, _calls = campaign_files
    reference = data["cohorts"]["2024"]["training"]
    target = path.parent / reference["path"]
    target.write_text('{"metadata":{"policy":"chart-focused","seed":20261108},"unused":1e999}')
    reference["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    result = audit(path, data)
    assert not result["passed"]
    assert result["binding"]["passed"] is False


@pytest.mark.parametrize(
    "invalid", ["conflicting-report", "conflicting-bundle", "extra-entry-field"]
)
def test_invalid_campaign_options_still_preserve_named_inputs(
    campaign_files: CampaignFiles,
    invalid: str,
) -> None:
    from scripts import audit_generated_charts as cli

    path, data, _calls = campaign_files
    entry = data["cohorts"]["2024"]
    if invalid == "extra-entry-field":
        entry["passed"] = True
    path.write_text(json.dumps(data))
    output = path if invalid == "conflicting-bundle" else path.parent / entry["training"]["path"]
    before = output.read_bytes()
    extra = ["--engine-only"] if invalid.startswith("conflicting") else []
    assert cli.main(["--campaign-bundle", str(path), "--output", str(output), *extra]) == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize("target", ["bundle", "report", "chart"])
def test_invalid_loaded_runtime_still_preserves_campaign_inputs(
    campaign_files: CampaignFiles,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    from scripts import audit_generated_charts as cli

    path, data, _calls = campaign_files
    entry = data["cohorts"]["2024"]
    path.write_text(json.dumps(data))
    output = (
        path
        if target == "bundle"
        else path.parent / entry["season_dir"] / "offense.csv"
        if target == "chart"
        else path.parent / entry["training"]["path"]
    )
    before = output.read_bytes()

    def invalid_runtime() -> str:
        raise RuntimeError("Invalid loaded runtime: stale implementation")

    monkeypatch.setattr(gate, "engine_fingerprint", invalid_runtime)
    assert cli.main(["--campaign-bundle", str(path), "--output", str(output)]) == 1
    assert output.read_bytes() == before


def test_campaign_file_returns_structured_invalid_runtime_failure(
    campaign_files: CampaignFiles,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, data, _calls = campaign_files

    def invalid_runtime() -> str:
        raise RuntimeError("Invalid loaded runtime: stale implementation")

    monkeypatch.setattr(gate, "engine_fingerprint", invalid_runtime)
    result = audit(path, data)
    assert not result["passed"] and result["errors"]
    assert (
        str(path.parent / data["cohorts"]["2024"]["training"]["path"])
        in result["binding"]["input_paths"]
    )

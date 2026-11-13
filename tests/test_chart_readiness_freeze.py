"""A declared freeze must bind the complete implementation and generation inputs."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
from paydirt.chart_engine_audit import chart_fingerprint

FreezeFiles = tuple[Path, dict]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    function = getattr(gate, "readiness_file_inventory", None)
    assert callable(function), "Freeze needs an independently discovered implementation inventory"
    return function(root)


def audit(root: Path, data: dict) -> dict:
    function = getattr(gate, "audit_readiness_freeze", None)
    assert callable(function), "Readiness must validate frozen implementation and input bytes"
    return function(root, data)


@pytest.fixture
def freeze_files(tmp_path: Path) -> FreezeFiles:
    paths = (
        "AGENTS.md",
        "pyproject.toml",
        "generate_nflverse_charts.py",
        "generate_pfr_charts.py",
        "tune_charts.py",
        "paydirt/game_engine.py",
        "paydirt/chart_engine_audit.py",
        "paydirt/chart_runtime_identity.py",
        "paydirt/chart_release_gate.py",
        "paydirt/chart_generator.py",
        "paydirt/auto_game.py",
        "tests/test_synthetic.py",
        "scripts/audit_generated_charts.py",
        "paydirt-web/backend/main.py",
        "paydirt-web/backend/requirements.txt",
        "paydirt-web/frontend/package.json",
        "paydirt-web/frontend/package-lock.json",
        "paydirt-web/frontend/vite.config.js",
        "paydirt-web/frontend/playwright.config.js",
        "paydirt-web/frontend/src/App.jsx",
        "paydirt-web/frontend/e2e/synthetic.spec.js",
        ".github/workflows/test.yml",
        ".github/workflows/release.yml",
        "config/chart-validation/1983.json",
        "config/chart-validation/2024.json",
        "docs/dev-notes/chart-confidence-agent-charter.md",
        "docs/dev-notes/chart-reference-comparison-protocol.md",
    )
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic public implementation fixture\n")
    cohorts = {}
    for name, season, count in (("1983-generated", 1983, 28), ("2024", 2024, 32)):
        directory = tmp_path / "candidates" / name
        directory.mkdir(parents=True)
        (directory / "offense.csv").write_text("Synthetic chart\n")
        sources = {}
        for label in ("normalized_stats/Synthetic.json", "play_by_play/source.csv"):
            path = tmp_path / "inputs" / name / label
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic public source\n")
            sources[label] = {"path": str(path.relative_to(tmp_path)), "sha256": digest(path)}
        (directory / "generation-manifest.json").write_text(
            json.dumps(
                {
                    "season": season,
                    "calibration_profile": {"pass_yard_multiplier": 1},
                    "input_hashes": {label: ref["sha256"] for label, ref in sources.items()},
                }
            )
        )
        contract = tmp_path / "inputs" / name / "contract.json"
        contract.write_text(
            json.dumps({"season": season, "teams": {f"Synthetic{i}": {} for i in range(count)}})
        )
        cohorts[name] = {
            "season_dir": str(directory.relative_to(tmp_path)),
            "chart_fingerprint": chart_fingerprint(directory),
            "contract": {"path": str(contract.relative_to(tmp_path)), "sha256": digest(contract)},
            "source_inputs": sources,
        }
    return tmp_path, {
        "schema_version": 1,
        "engine_fingerprint": gate.engine_fingerprint(),
        "files": {name: digest(tmp_path / name) for name in paths},
        "cohorts": cohorts,
        "reserved_families": {
            "held_out": {"master": 20361108, "opened": False},
            "reference": {"master": 20461108, "opened": False},
            "transfer": {"master": 20561108, "opened": False},
        },
    }


def test_freeze_binds_actual_complete_files_and_remains_a_component(
    freeze_files: FreezeFiles,
) -> None:
    root, data = freeze_files
    assert inventory(root) == data["files"]
    result = audit(root, data)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert set(result["cohorts"]) == {"1983-generated", "2024"}


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-code",
        "changed-code",
        "added-code",
        "omitted-code",
        "extra-code",
        "bad-digest",
        "missing-anchor",
        "missing-cohort",
        "extra-cohort",
        "changed-chart",
        "changed-profile",
        "changed-contract",
        "missing-contract",
        "substituted-contract",
        "unbound-source",
        "changed-source",
        "missing-source",
        "omitted-source",
        "extra-source",
        "manifest-source",
        "wrong-engine",
        "wrong-version",
        "extra-field",
        "wrong-seed",
        "opened-seed",
        "missing-seed",
    ],
)
def test_freeze_mutants_cannot_pass_on_a_self_declared_success(
    freeze_files: FreezeFiles,
    mutation: str,
) -> None:
    root, original = freeze_files
    data = deepcopy(original)
    entry = data["cohorts"]["2024"]
    source = entry["source_inputs"]["play_by_play/source.csv"]
    directory = root / entry["season_dir"]
    if mutation == "missing-code":
        (root / "tests/test_synthetic.py").unlink()
    elif mutation == "changed-code":
        (root / "paydirt/game_engine.py").write_text("Changed\n")
    elif mutation == "added-code":
        (root / "paydirt/new_observer.py").write_text("Added\n")
    elif mutation == "omitted-code":
        data["files"].pop("paydirt/auto_game.py")
    elif mutation == "extra-code":
        data["files"]["unknown.py"] = "0" * 64
    elif mutation == "bad-digest":
        data["files"]["paydirt/auto_game.py"] = "false"
    elif mutation == "missing-anchor":
        (root / "paydirt/chart_runtime_identity.py").unlink()
        data["files"].pop("paydirt/chart_runtime_identity.py")
    elif mutation == "missing-cohort":
        data["cohorts"].pop("2024")
    elif mutation == "extra-cohort":
        data["cohorts"]["2023"] = deepcopy(entry)
    elif mutation == "changed-chart":
        (directory / "offense.csv").write_text("Changed\n")
    elif mutation == "changed-profile":
        path = directory / "generation-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["calibration_profile"]["pass_yard_multiplier"] = 2
        path.write_text(json.dumps(manifest))
    elif mutation == "changed-contract":
        (root / entry["contract"]["path"]).write_text("{}")
    elif mutation == "missing-contract":
        (root / entry["contract"]["path"]).unlink()
    elif mutation == "substituted-contract":
        path = root / entry["contract"]["path"]
        path.write_text(json.dumps({"season": 2023, "teams": {}}))
        entry["contract"]["sha256"] = digest(path)
    elif mutation == "unbound-source":
        entry["source_inputs"]["play_by_play/source.csv"] = source["path"]
    elif mutation == "changed-source":
        (root / source["path"]).write_text("Changed\n")
    elif mutation == "missing-source":
        (root / source["path"]).unlink()
    elif mutation == "omitted-source":
        entry["source_inputs"].pop("play_by_play/source.csv")
    elif mutation == "extra-source":
        entry["source_inputs"]["undeclared/source.csv"] = deepcopy(source)
    elif mutation == "manifest-source":
        path = directory / "generation-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["input_hashes"]["play_by_play/source.csv"] = "0" * 64
        path.write_text(json.dumps(manifest))
        entry["chart_fingerprint"] = chart_fingerprint(directory)
    elif mutation == "wrong-engine":
        data["engine_fingerprint"] = "0" * 64
    elif mutation == "wrong-version":
        data["schema_version"] = True
    elif mutation == "extra-field":
        data["passed"] = True
    elif mutation == "wrong-seed":
        data["reserved_families"]["transfer"]["master"] = 20261108
    elif mutation == "opened-seed":
        data["reserved_families"]["held_out"]["opened"] = True
    elif mutation == "missing-seed":
        data["reserved_families"].pop("reference")
    result = audit(root, data)
    assert not result["passed"]
    assert result["errors"] and result["release_certified"] is False


def test_inventory_ignores_caches_dependencies_and_local_historical_data(
    freeze_files: FreezeFiles,
) -> None:
    root, data = freeze_files
    for name in (
        "paydirt/__pycache__/cached.pyc",
        "paydirt-web/frontend/node_modules/library/index.js",
        ".ai-audits/ignored.log",
        "seasons/1983/Synthetic/offense.csv",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic ignored data\n")
    assert inventory(root) == data["files"]


def test_changed_implementation_during_freeze_validation_fails(
    freeze_files: FreezeFiles,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, data = freeze_files
    original = gate.chart_fingerprint

    def change(path: Path) -> str:
        result = original(path)
        (root / "paydirt/auto_game.py").write_text("Changed during validation\n")
        return result

    monkeypatch.setattr(gate, "chart_fingerprint", change)
    result = audit(root, data)
    assert not result["passed"] and any("changed" in reason.lower() for reason in result["errors"])


def test_changed_loaded_runtime_during_freeze_validation_fails(
    freeze_files: FreezeFiles,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, data = freeze_files
    values = iter((data["engine_fingerprint"], "0" * 64))
    monkeypatch.setattr(gate, "engine_fingerprint", lambda: next(values))
    result = audit(root, data)
    assert not result["passed"] and result["errors"]


@pytest.mark.parametrize("target", ["source", "contract"])
def test_frozen_input_changed_after_its_first_read_fails(
    freeze_files: FreezeFiles,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    root, data = freeze_files
    entry = data["cohorts"]["1983-generated"]
    reference = (
        entry["contract"]
        if target == "contract"
        else entry["source_inputs"]["play_by_play/source.csv"]
    )
    original = gate.chart_fingerprint

    def change(path: Path) -> str:
        result = original(path)
        if path.name == "2024":
            (root / reference["path"]).write_text("Changed after initial binding\n")
        return result

    monkeypatch.setattr(gate, "chart_fingerprint", change)
    result = audit(root, data)
    assert not result["passed"] and any("changed" in reason.lower() for reason in result["errors"])


def test_frozen_manifest_cannot_substitute_another_source_season(freeze_files: FreezeFiles) -> None:
    root, data = freeze_files
    entry = data["cohorts"]["2024"]
    directory = root / entry["season_dir"]
    path = directory / "generation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["season"] = 2023
    path.write_text(json.dumps(manifest))
    entry["chart_fingerprint"] = chart_fingerprint(directory)
    result = audit(root, data)
    assert not result["passed"] and result["errors"]


def test_implementation_inventory_includes_core_runtime_resources(
    freeze_files: FreezeFiles,
) -> None:
    root, data = freeze_files
    path = root / "paydirt/data/probabilities.json"
    path.parent.mkdir()
    path.write_text('{"synthetic":true}\n')
    data["files"]["paydirt/data/probabilities.json"] = digest(path)
    assert inventory(root) == data["files"]
    result = audit(root, data)
    assert result["passed"], result["errors"]


def test_freeze_returns_structured_failure_for_an_invalid_loaded_runtime(
    freeze_files: FreezeFiles,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, data = freeze_files

    def invalid_runtime() -> str:
        raise RuntimeError("Invalid loaded runtime: stale implementation")

    monkeypatch.setattr(gate, "engine_fingerprint", invalid_runtime)
    result = audit(root, data)
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False

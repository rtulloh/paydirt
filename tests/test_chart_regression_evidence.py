"""Readiness requires actual bound execution records for every regression command."""
from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
from tests import test_chart_readiness_freeze as freeze_support

FreezeFiles = freeze_support.FreezeFiles
freeze_files = freeze_support.freeze_files


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def freeze_digest(data: dict) -> str:
    return digest(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def commands() -> dict[str, tuple[str, list[str]]]:
    python = sys.executable
    return {
        "core": (".", [python, "-m", "pytest", "tests/", "-q", "-o", "addopts=", "--tb=short", "-rs", "--cov=paydirt", "--cov-report=term"]),
        "backend": ("paydirt-web/backend", [python, "-m", "pytest", "tests/", "-q", "-o", "addopts=", "--tb=short"]),
        "frontend": ("paydirt-web/frontend", ["npm", "test", "--", "--run"]),
        "build": ("paydirt-web/frontend", ["npm", "run", "build"]),
        "browser": ("paydirt-web/frontend", ["npm", "run", "test:e2e"]),
        "lint": (".", ["ruff", "check", "paydirt/", "tests/", "paydirt-web/backend/"]),
        "all_games": (".", [python, "tests/run_all_games.py"]),
        "full_season": (".", [python, "tests/run_full_season.py"]),
        "public_ai": (".", [python, "tests/run_ai_audit.py", "--season", "2026", "--weeks", "16", "--seed", "8306", "--compare-balanced", "--output", ".ai-audits/public-season.json"]),
        "local_ai": (".", [python, "tests/run_ai_audit.py", "--season", "1983", "--weeks", "16", "--seed", "8306", "--compare-balanced", "--output", ".ai-audits/local-season.json", "--csv", ".ai-audits/local-season.csv"]),
        "chart_1983": (".", [python, "scripts/audit_generated_charts.py", "--season-dir", "seasons/1983", "--contract", "config/chart-validation/1983.json", "--output", ".ai-audits/chart-quality-1983.json", "--repetitions", "64", "--workers", "4"]),
        "chart_2024": (".", [python, "scripts/audit_generated_charts.py", "--season-dir", "seasons/2024", "--contract", "config/chart-validation/2024.json", "--output", ".ai-audits/chart-quality-2024.json", "--repetitions", "64", "--workers", "4"]),
    }


@pytest.fixture
def regression_files(freeze_files: FreezeFiles) -> tuple[Path, dict, dict]:
    root, freeze = freeze_files
    entries = {}
    for name, (cwd, argv) in commands().items():
        path = root / ".ai-audits/regression" / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        execution = {"argv": argv, "cwd": str((root / cwd).resolve()), "returncode": 0,
                     "stdout": "Synthetic successful execution\n", "stderr": ""}
        path.write_text(json.dumps(execution))
        entries[name] = {"path": str(path.relative_to(root)), "sha256": digest(path.read_bytes())}
    return root, freeze, {"schema_version": 1, "freeze_sha256": freeze_digest(freeze), "commands": entries}


def audit(files: tuple[Path, dict, dict]) -> dict:
    function = getattr(gate, "audit_regression_evidence", None)
    assert callable(function), "The readiness gate must validate the complete actual regression evidence"
    return function(*files)


def test_complete_current_regression_receipts_are_a_noncertifying_component(regression_files: tuple) -> None:
    result = audit(regression_files)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert set(result["commands"]) == set(commands())


def test_regression_command_inventory_matches_agents_without_omitting_required_runners() -> None:
    assert gate.required_regression_commands() == commands()
    root = Path(__file__).resolve().parents[1]
    section = (root / "AGENTS.md").read_text().split("### Required Full Regression Before Any Push", 1)[1]
    checklist = section.split("```bash\n", 1)[1].split("```", 1)[0].strip().splitlines()
    actual = []
    for cwd, argv in gate.required_regression_commands(released_charts=True).values():
        command = " ".join(["python3" if part == sys.executable else part for part in argv])
        actual.append(command if cwd == "." else f"(cd {cwd} && {command})")
    assert actual == checklist


@pytest.mark.parametrize("mutation", [
    "omitted-command", "extra-command", "wrong-version", "wrong-freeze", "self-declared-pass",
    "missing-log", "changed-log", "bad-digest", "bare-path", "failed-execution", "bool-exit",
    "wrong-command", "partial-campaign", "wrong-cwd", "missing-stdout", "invalid-stderr",
    "empty-execution", "duplicate-json", "nonfinite-json", "changed-code", "changed-candidate",
])
def test_incomplete_stale_or_failed_regression_cannot_become_readiness(
    regression_files: tuple, mutation: str,
) -> None:
    root, freeze, original = regression_files
    data = deepcopy(original)
    reference = data["commands"]["browser"]
    path = root / reference["path"]
    execution = json.loads(path.read_text())
    rewrite = False
    if mutation == "omitted-command": data["commands"].pop("full_season")
    elif mutation == "extra-command": data["commands"]["pytest_only"] = deepcopy(reference)
    elif mutation == "wrong-version": data["schema_version"] = True
    elif mutation == "wrong-freeze": data["freeze_sha256"] = "0" * 64
    elif mutation == "self-declared-pass": data["passed"] = True
    elif mutation == "missing-log": path.unlink()
    elif mutation == "changed-log": path.write_text("Changed\n")
    elif mutation == "bad-digest": reference["sha256"] = "invalid"
    elif mutation == "bare-path": data["commands"]["browser"] = reference["path"]
    elif mutation == "failed-execution": execution["returncode"] = 1; rewrite = True
    elif mutation == "bool-exit": execution["returncode"] = False; rewrite = True
    elif mutation == "wrong-command": execution["argv"] = ["npm", "run", "build"]; rewrite = True
    elif mutation == "partial-campaign":
        reference = data["commands"]["chart_2024"]; path = root / reference["path"]
        execution = json.loads(path.read_text()); execution["argv"][execution["argv"].index("64")] = "1"; rewrite = True
    elif mutation == "wrong-cwd": execution["cwd"] = str(root); rewrite = True
    elif mutation == "missing-stdout": execution.pop("stdout"); rewrite = True
    elif mutation == "invalid-stderr": execution["stderr"] = []; rewrite = True
    elif mutation == "empty-execution": execution["stdout"] = ""; rewrite = True
    elif mutation == "duplicate-json": path.write_text('{"returncode":0,"returncode":1}'); reference["sha256"] = digest(path.read_bytes())
    elif mutation == "nonfinite-json": path.write_text('{"returncode":NaN}'); reference["sha256"] = digest(path.read_bytes())
    elif mutation == "changed-code": (root / "paydirt/game_engine.py").write_text("Changed\n")
    elif mutation == "changed-candidate": (root / freeze["cohorts"]["2024"]["season_dir"] / "offense.csv").write_text("Changed\n")
    if rewrite:
        path.write_text(json.dumps(execution)); reference["sha256"] = digest(path.read_bytes())
    result = audit((root, freeze, data))
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False


def test_regression_discloses_existing_skips_and_warnings_without_suppressing_them(regression_files: tuple) -> None:
    root, freeze, data = regression_files
    reference = data["commands"]["core"]
    path = root / reference["path"]
    execution = json.loads(path.read_text())
    execution["stdout"] = "100 passed, 2 skipped\nSKIPPED [2] existing synthetic optional capability\n"
    execution["stderr"] = "WARNING: existing synthetic deprecation\n"
    path.write_text(json.dumps(execution)); reference["sha256"] = digest(path.read_bytes())
    result = audit((root, freeze, data))
    assert result["passed"], result["errors"]
    assert result["commands"]["core"]["diagnostics"] == (execution["stdout"] + execution["stderr"]).splitlines()


def test_regression_preserves_npm_warn_and_dependency_audit_summary(regression_files: tuple) -> None:
    root, freeze, data = regression_files
    reference = data["commands"]["frontend"]; path = root / reference["path"]
    execution = json.loads(path.read_text())
    execution.update({"stdout": "17 vulnerabilities (synthetic public fixture)\n", "stderr": "npm warn deprecated synthetic package\n"})
    path.write_text(json.dumps(execution)); reference["sha256"] = digest(path.read_bytes())
    result = audit((root, freeze, data))
    assert result["passed"], result["errors"]
    assert result["commands"]["frontend"]["diagnostics"] == [
        "17 vulnerabilities (synthetic public fixture)", "npm warn deprecated synthetic package",
    ]

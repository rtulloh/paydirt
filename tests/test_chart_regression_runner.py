"""The maintained collector executes actual commands and retains failures."""
from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from tests import test_chart_readiness_freeze as freeze_support
from tests.test_chart_regression_evidence import commands
from tests.test_chart_regression_outputs import install_output_fixtures

freeze_files = freeze_support.freeze_files


def runner(files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str = "normal") -> tuple:
    assert importlib.util.find_spec("scripts.run_chart_regression") is not None, "Readiness needs a maintained actual regression collector"
    module = importlib.import_module("scripts.run_chart_regression")
    root, freeze = files
    contents = install_output_fixtures(root, freeze, monkeypatch)
    freeze_path = root / ".ai-audits/freeze.json"
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_path.write_text(json.dumps(freeze))
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "occupied_review_ports", lambda: [8000] if mode == "ports" else [])
    calls = []
    def execute(argv: list[str], **options: object) -> subprocess.CompletedProcess:
        calls.append((argv, options))
        if mode == "missing-tool" and len(calls) == 1:
            raise OSError("Synthetic missing executable")
        if mode not in {"missing-artifact", "stale-artifact"}:
            for flag in ("--output", "--csv"):
                if flag in argv:
                    path = root / argv[argv.index(flag) + 1]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    name = next(name for name, (_cwd, command) in commands().items() if command == argv)
                    label = name + ("_json" if flag == "--output" else "_csv")
                    path.write_text("{}\n" if mode == "corrupt-artifact" and name == "public_ai" else contents[label])
        return subprocess.CompletedProcess(argv, 1 if mode == "failed" and len(calls) == 1 else 0,
                                           stdout="Synthetic completed command\n", stderr="WARNING: synthetic retained warning\n")
    monkeypatch.setattr(module.subprocess, "run", execute)
    return module, root, freeze, freeze_path, calls


@pytest.mark.parametrize("mode", ["normal", "failed", "missing-artifact", "stale-artifact", "missing-tool", "corrupt-artifact"])
def test_collector_runs_every_command_and_preserves_real_status_logs_and_artifacts(
    freeze_files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    module, root, _freeze, freeze_path, calls = runner(freeze_files, monkeypatch, mode)
    if mode == "stale-artifact":
        for _cwd, argv in commands().values():
            for flag in ("--output", "--csv"):
                if flag in argv:
                    path = root / argv[argv.index(flag) + 1]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("Old synthetic evidence\n")
    output = root / ".ai-audits/regression-01"
    assert module.main(["--freeze", str(freeze_path), "--output", str(output)]) == (0 if mode == "normal" else 1)
    assert len(calls) == 12
    evidence = json.loads((output / "evidence.json").read_text())
    result = json.loads((output / "result.json").read_text())
    assert result["passed"] is (mode == "normal") and result["release_certified"] is False
    assert len(evidence["commands"]) == 12
    if mode == "normal":
        assert len(result["produced_artifacts"]) == 5
        assert result["outputs"]["passed"] is True
        outputs = json.loads((output / "outputs.json").read_text())
        assert outputs["artifacts"] == result["produced_artifacts"]
    expected = commands()
    assert [call[0] for call in calls] == [argv for _cwd, argv in expected.values()]
    for name, reference in evidence["commands"].items():
        log = json.loads((root / reference["path"]).read_text())
        assert log["argv"] == expected[name][1]
        assert log["cwd"] == str((root / expected[name][0]).resolve())
        if mode == "missing-tool" and name == "core":
            assert log["returncode"] is None and "missing executable" in log["stderr"]
        else:
            assert log["returncode"] == (1 if mode == "failed" and name == "core" else 0)
            assert log["stdout"] and "WARNING" in log["stderr"]
    assert freeze_path.exists()


@pytest.mark.parametrize("mode", ["ports", "stale-freeze", "wrong-promoted", "existing-output", "inside-candidate", "inside-source", "inside-code"])
def test_collector_rejects_preflight_failures_without_running_or_overwriting_inputs(
    freeze_files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    module, root, freeze, freeze_path, calls = runner(freeze_files, monkeypatch, mode)
    output = root / ".ai-audits/regression-01"
    if mode == "stale-freeze": (root / "paydirt/game_engine.py").write_text("Changed\n")
    elif mode == "wrong-promoted": (root / "seasons/2024/offense.csv").write_text("Different candidate\n")
    elif mode == "existing-output": output.mkdir(); (output / "keep.txt").write_text("Preserve\n")
    elif mode == "inside-candidate": output = root / freeze["cohorts"]["2024"]["season_dir"] / "new-output"
    elif mode == "inside-source": output = root / "inputs/2024/normalized_stats/new-output"
    elif mode == "inside-code": output = root / "paydirt/new-output"
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert module.main(["--freeze", str(freeze_path), "--output", str(output)]) == 1
    assert not calls
    assert all(path.read_bytes() == data for path, data in before.items())

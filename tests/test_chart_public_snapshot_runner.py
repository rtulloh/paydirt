"""The clean collector copies public working-tree bytes and runs isolated suites."""

from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from tests import test_chart_public_snapshot as snapshot_support
from tests.test_chart_regression_evidence import commands

snapshot_files = snapshot_support.snapshot_files
freeze_files = snapshot_support.freeze_files


def runner(files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str = "normal") -> tuple:
    assert importlib.util.find_spec("scripts.run_chart_public_snapshot") is not None, (
        "Readiness needs a maintained clean public unit collector"
    )
    module = importlib.import_module("scripts.run_chart_public_snapshot")
    root, freeze, _evidence = files
    freeze_path = root / ".ai-audits/freeze.json"
    freeze_path.write_text(json.dumps(freeze))
    monkeypatch.setattr(module, "ROOT", root)
    real_run = subprocess.run
    calls = []

    def execute(argv: list[str], **options: object) -> subprocess.CompletedProcess:
        if argv[0] == "git":
            return real_run(argv, **options)
        calls.append((argv, options))
        if mode == "missing-tool" and len(calls) == 1:
            raise OSError("Synthetic missing executable")
        if mode == "source-changed" and len(calls) == 1:
            (root / "README.md").write_text("Changed during execution\n")
        if mode == "snapshot-changed" and len(calls) == 1:
            (Path(options["env"]["PYTHONPATH"]) / "README.md").write_text(
                "Changed during execution\n"
            )
        if mode == "freeze-changed" and len(calls) == 1:
            freeze_path.write_text("{}\n")
        return subprocess.CompletedProcess(
            argv,
            1 if mode == "failed" and len(calls) == 1 else 0,
            stdout="Synthetic completed isolated command\n",
            stderr="WARNING: synthetic retained warning\n",
        )

    monkeypatch.setattr(module.subprocess, "run", execute)
    return module, root, freeze, freeze_path, calls


@pytest.mark.parametrize(
    "mode",
    ["normal", "failed", "missing-tool", "source-changed", "snapshot-changed", "freeze-changed"],
)
def test_clean_collector_copies_public_bytes_and_retains_every_actual_execution(
    snapshot_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    module, root, _freeze, freeze_path, calls = runner(snapshot_files, monkeypatch, mode)
    private = root / "seasons/1972/Synthetic/offense.csv"
    private.parent.mkdir(parents=True)
    private.write_text("Ignored synthetic stand-in; never copy\n")
    output = root / ".ai-audits/clean-01"
    assert module.main(["--freeze", str(freeze_path), "--output", str(output)]) == (
        0 if mode == "normal" else 1
    )
    snapshot = output / "source"
    evidence = json.loads((output / "evidence.json").read_text())
    result = json.loads((output / "result.json").read_text())
    assert result["passed"] is (mode == "normal") and result["release_certified"] is False
    assert not (snapshot / "seasons/1972").exists()
    assert not (snapshot / ".git").exists()
    assert (snapshot / "AGENTS.md").read_text() == "Synthetic changed tracked public file\n"
    assert (snapshot / "README.md").is_file()
    expected = {"setup": ("paydirt-web/frontend", ["npm", "ci"])}
    expected.update({name: commands()[name] for name in ("core", "backend", "frontend")})
    assert [call[0] for call in calls] == [argv for _cwd, argv in expected.values()]
    for name, reference in evidence["commands"].items():
        execution = json.loads((root / reference["path"]).read_text())
        assert execution["argv"] == expected[name][1]
        assert execution["cwd"] == str((snapshot / expected[name][0]).resolve())
        assert execution["pythonpath"] == str(snapshot)
        assert execution["stderr"]
        if mode == "missing-tool" and name == "setup":
            assert execution["returncode"] is None
        else:
            assert execution["returncode"] == (1 if mode == "failed" and name == "setup" else 0)
    for _argv, options in calls:
        assert options["env"]["PYTHONPATH"] == str(snapshot)
        assert options["env"]["PYTHONNOUSERSITE"] == "1"


@pytest.mark.parametrize(
    "mode",
    [
        "stale-freeze",
        "wrong-promoted",
        "existing-output",
        "inside-source",
        "inside-code",
        "source-symlink",
    ],
)
def test_clean_collector_rejects_invalid_inputs_without_executing_or_overwriting_files(
    snapshot_files: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    module, root, _freeze, freeze_path, calls = runner(snapshot_files, monkeypatch, mode)
    output = root / ".ai-audits/clean-01"
    if mode == "stale-freeze":
        (root / "paydirt/game_engine.py").write_text("Changed\n")
    elif mode == "wrong-promoted":
        (root / "seasons/2024/offense.csv").write_text("Different candidate\n")
    elif mode == "existing-output":
        output.mkdir()
        (output / "keep.txt").write_text("Preserve\n")
    elif mode == "inside-source":
        output = root / "inputs/2024/normalized_stats/new-output"
    elif mode == "inside-code":
        output = root / "paydirt/new-output"
    elif mode == "source-symlink":
        path = root / "README.md"
        path.unlink()
        path.symlink_to(root / "AGENTS.md")
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert module.main(["--freeze", str(freeze_path), "--output", str(output)]) == 1
    assert not calls
    assert all(path.read_bytes() == data for path, data in before.items())

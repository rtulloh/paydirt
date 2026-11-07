"""The maintained preview collector owns isolated services and retains real evidence."""
from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
from tests import test_chart_visual_content as support

freeze_files = support.freeze_files
capture_files = support.capture_files
content_files = support.content_files


def runner(files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str) -> tuple:
    assert importlib.util.find_spec("scripts.run_chart_preview") is not None, "Readiness needs a maintained isolated browser-preview collector"
    module = importlib.import_module("scripts.run_chart_preview")
    root, freeze, captures, content = files
    for name in ("scripts/run_chart_preview_backend.py", "paydirt-web/frontend/e2e/collect-chart-preview.cjs"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic collector implementation\n")
    (root / "README.md").write_text("Synthetic public source\n")
    (root / ".gitignore").write_text(".ai-audits/\ncandidates/\ninputs/\nseasons/1983/\n")
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    for entry in freeze["cohorts"].values():
        folder = root / entry["season_dir"]
        shutil.copytree(folder / "Synthetic0", folder / "Synthetic1")
        entry["chart_fingerprint"] = gate.chart_fingerprint(folder)
    freeze["files"] = gate.readiness_file_inventory(root)
    freeze_path = root / ".ai-audits" / "preview-freeze.json"
    freeze_path.write_text(json.dumps(freeze))
    selection = {"schema_version": 1, "freeze_sha256": gate.readiness_freeze_fingerprint(freeze),
                 "contexts": [{"cohort": cohort, "team": "Synthetic0", "opponent": "Synthetic1", "side": "home"}
                              for cohort in freeze["cohorts"]]}
    selection_path = root / ".ai-audits" / "preview-selection.json"
    selection_path.write_text(json.dumps(selection))
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "_check_port", lambda port: (_ for _ in ()).throw(ValueError("Port occupied")) if mode == "occupied" else None)
    calls, processes = [], []

    class Process:
        def __init__(self, argv: list[str], **options: object) -> None:
            self.argv, self.pid, self.returncode = argv, 9000 + len(processes), None
            self.stopped = False
            processes.append(self)
        def poll(self) -> int | None:
            return self.returncode
        def terminate(self) -> None:
            self.stopped = True
            self.returncode = 0
            if "--receipt" in self.argv:
                path = Path(self.argv[self.argv.index("--receipt") + 1])
                data = json.loads(path.read_text())
                path.with_name("runtime-after.json").write_text(json.dumps(data))
                if mode == "late-manifest": (path.parent / "content.json").write_text("{}")
                if mode == "late-artifact": next((path.parent / "captures").rglob("*.png")).write_bytes(b"Changed")
        def wait(self, timeout: float | None = None) -> int:
            return self.returncode or 0
        def kill(self) -> None:
            self.stopped = True
            self.returncode = -9

    def wait_service(process: object, url: str) -> None:
        if mode == "service-failed": raise RuntimeError("Synthetic service failed")
        if "--receipt" in process.argv:
            path = Path(process.argv[process.argv.index("--receipt") + 1])
            path.write_text(json.dumps({"schema_version": 1, "freeze_sha256": gate.readiness_freeze_fingerprint(freeze),
                "engine_fingerprint": "0" * 64 if mode == "wrong-runtime" else freeze["engine_fingerprint"],
                "source_root": str(path.parent / "source"), "process_id": process.pid,
                "implementation_files": freeze["files"],
                "loaded_runtime": {"scheme": "compiled-loaded-definitions-v1", "definitions_sha256": "a" * 64,
                                   "constants_sha256": "b" * 64, "module_files": ["game_engine.py"],
                                   "python": "cpython-311", "optimization": 0}}))

    real_run = subprocess.run
    real_popen = subprocess.Popen
    def execute(argv: list[str], **options: object) -> subprocess.CompletedProcess:
        if argv[0] == "git": return real_run(argv, **options)
        calls.append((argv, options))
        if mode == "missing-tool" and argv[0] == "npm": raise OSError("Synthetic missing npm")
        if argv[0] == "node":
            output = Path(argv[argv.index("--output") + 1])
            plan = json.loads(Path(argv[argv.index("--plan") + 1]).read_text())
            fresh_captures = deepcopy(captures)
            fresh_captures["freeze_sha256"] = plan["freeze_sha256"]
            memo = {}
            def rebind(value: object) -> object:
                if isinstance(value, str): return value.replace(":5176/", ":5177/")
                if isinstance(value, list): return [rebind(item) for item in value]
                if not isinstance(value, dict): return value
                if set(value) == {"path", "sha256"}:
                    old = value["path"]
                    if old in memo: return memo[old]
                    source = root / old
                    target = output / "captures" / Path(old).relative_to(".ai-audits/visual")
                    if source.suffix == ".json":
                        data = rebind(json.loads(source.read_text()))
                        if isinstance(data, dict) and "chart_fingerprint" in data:
                            data.update(freeze_sha256=plan["freeze_sha256"],
                                        chart_fingerprint=freeze["cohorts"][data["cohort"]]["chart_fingerprint"])
                    else: data = source.read_bytes()
                    memo[old] = support.bound(root, target, data)
                    return memo[old]
                result = {key: rebind(item) for key, item in value.items()}
                if mode == "wrong-opponent" and "game_id" in result and "away_team" in result:
                    result["away_team"]["id"] = "Synthetic0"
                return result
            fresh_captures = rebind(fresh_captures)
            fresh_content = rebind(deepcopy(content))
            fresh_content.update(freeze_sha256=plan["freeze_sha256"], captures_sha256=gate.readiness_freeze_fingerprint(fresh_captures))
            if mode == "bad-content": fresh_content["contexts"][0]["api_book"]["sha256"] = "0" * 64
            (output / "captures.json").write_text(json.dumps(fresh_captures))
            (output / "content.json").write_text(json.dumps(fresh_content))
            if mode == "root-changed": (root / "README.md").write_text("Changed\n")
            if mode == "snapshot-changed": (output / "source" / "README.md").write_text("Changed\n")
            if mode == "candidate-changed": (output / "source" / "seasons" / "2024" / "Synthetic0" / "offense.csv").write_text("Changed\n")
            if mode == "freeze-changed": freeze_path.write_text("{}")
            if mode == "frontend-exit": processes[-1].returncode = 1; processes[-1].stopped = True
            if mode == "extra-season": (output / "source/seasons/1972").mkdir()
        return subprocess.CompletedProcess(argv, 1 if mode == "command-failed" else 0,
                                           stdout="Synthetic retained execution\n", stderr="WARNING: retained synthetic warning\n")

    monkeypatch.setattr(module.subprocess, "run", execute)
    monkeypatch.setattr(module.subprocess, "Popen", lambda argv, **options: real_popen(argv, **options) if argv[0] == "git" else Process(argv, **options))
    monkeypatch.setattr(module, "_wait_service", wait_service)
    if mode == "copy-failed":
        monkeypatch.setattr(module.shutil, "copy2", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Synthetic copy failure")))
    return module, root, freeze, freeze_path, selection_path, calls, processes


@pytest.mark.parametrize("mode", ["normal", "missing-tool", "command-failed", "service-failed", "wrong-runtime",
                                  "bad-content", "root-changed", "snapshot-changed", "candidate-changed", "freeze-changed",
                                  "late-manifest", "late-artifact", "wrong-opponent", "frontend-exit", "extra-season", "copy-failed"])
def test_collector_binds_evidence_and_always_stops_only_its_services(
    content_files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    module, root, freeze, freeze_path, selection, calls, processes = runner(content_files, monkeypatch, mode)
    private = root / "seasons/1983/PrivateStandIn/offense.csv"
    private.parent.mkdir(parents=True)
    private.write_text("Synthetic ignored stand-in; never read or copy\n")
    output = root / ".ai-audits" / "preview-01"
    assert module.main(["--freeze", str(freeze_path), "--selection", str(selection), "--output", str(output)]) == (0 if mode == "normal" else 1)
    result = json.loads((output / "result.json").read_text())
    assert result["passed"] is (mode == "normal")
    assert result["release_certified"] is False
    assert result["selection_validated"] is False
    assert all(process.stopped for process in processes)
    assert all(":8000" not in str(process.argv) and "5173" not in process.argv for process in processes)
    assert not (output / "source/seasons/1983/PrivateStandIn").exists()
    if mode == "normal":
        assert result["candidate_content_validated"] is True
        assert result["content"]["cells_checked"] == 1740
        assert [argv[0] for argv, _options in calls] == ["npm", "node"]
        for cohort, entry in freeze["cohorts"].items():
            season = "1983" if cohort == "1983-generated" else "2024"
            assert gate.chart_fingerprint(output / "source/seasons" / season) == entry["chart_fingerprint"]
        assert (output / "runtime-after.json").is_file()


@pytest.mark.parametrize("mode", ["occupied", "stale", "missing-cohort", "duplicate", "wrong-side",
                                  "unknown-team", "same-opponent", "existing-output", "inside-source", "inside-code"])
def test_invalid_preview_preflight_preserves_files_and_starts_nothing(
    content_files: tuple, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    module, root, _freeze, freeze_path, selection_path, calls, processes = runner(content_files, monkeypatch, mode)
    selection = json.loads(selection_path.read_text())
    output = root / ".ai-audits" / "preview-01"
    if mode == "stale": (root / "paydirt/game_engine.py").write_text("Changed")
    elif mode == "missing-cohort": selection["contexts"].pop()
    elif mode == "duplicate": selection["contexts"].append(deepcopy(selection["contexts"][0]))
    elif mode == "wrong-side": selection["contexts"][0]["side"] = "other"
    elif mode == "unknown-team": selection["contexts"][0]["team"] = "Other"
    elif mode == "same-opponent": selection["contexts"][0]["opponent"] = "Synthetic0"
    elif mode == "existing-output": output.mkdir(); (output / "keep.txt").write_text("Preserve")
    elif mode == "inside-source": output = root / "inputs/2024/new-output"
    elif mode == "inside-code": output = root / "paydirt/new-output"
    selection_path.write_text(json.dumps(selection))
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert module.main(["--freeze", str(freeze_path), "--selection", str(selection_path), "--output", str(output)]) == 1
    assert not calls and not processes
    assert all(path.read_bytes() == data for path, data in before.items())


def test_backend_probe_uses_the_real_health_route(content_files: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    module, root, _freeze, freeze_path, selection, _calls, _processes = runner(content_files, monkeypatch, "normal")
    real_wait = module._wait_service
    probes = []
    def observe(process: object, url: str) -> None:
        probes.append(url)
        real_wait(process, url)
    monkeypatch.setattr(module, "_wait_service", observe)
    assert module.main(["--freeze", str(freeze_path), "--selection", str(selection),
                        "--output", str(root / ".ai-audits/preview-01")]) == 0
    assert probes[0] == "http://127.0.0.1:8004/api/health"

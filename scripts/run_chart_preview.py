#!/usr/bin/env python3
"""Collect frozen chart previews using owned services in a fresh public source copy."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.chart_release_gate import (
    _strict_json_object,
    audit_readiness_freeze,
    audit_visual_content_evidence,
    chart_fingerprint,
    public_source_file_inventory,
    readiness_file_inventory,
    readiness_freeze_fingerprint,
)


def write_json(path: Path, value: object) -> None:
    """Retain evidence without replacing earlier output."""
    with path.open("x") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def _check_port(port: int) -> None:
    if port in {8000, 5173} or not 1024 <= port <= 65535:
        raise ValueError("Preview requires an unprivileged port outside owner services")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", port))


def _wait_service(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Preview service exited before readiness: {url}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Preview service readiness timed out: {url}")


def _files(directory: Path, *, implementation: bool = False) -> dict[str, str]:
    """Inventory regular files, excluding only generated implementation caches."""
    result = {}
    for base, folders, names in os.walk(directory, followlinks=False):
        parent = Path(base)
        for name in folders + names:
            if (parent / name).is_symlink():
                raise ValueError("Preview copies cannot contain symlinks")
        if implementation:
            folders[:] = [name for name in folders if name not in {
                "seasons", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
            }]
        for name in names:
            path = parent / name
            if not path.is_file():
                raise ValueError("Preview requires regular source files")
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _runtime(path: Path, freeze: dict, snapshot: Path, pid: int) -> dict:
    data = _strict_json_object(path.read_bytes())
    if (set(data) != {"schema_version", "freeze_sha256", "engine_fingerprint", "source_root",
                      "process_id", "implementation_files", "loaded_runtime"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["freeze_sha256"] != readiness_freeze_fingerprint(freeze)
            or data["engine_fingerprint"] != freeze["engine_fingerprint"]
            or data["source_root"] != str(snapshot) or data["process_id"] != pid
            or data["implementation_files"] != freeze["files"]):
        raise ValueError("Served runtime receipt differs from frozen snapshot")
    loaded = data["loaded_runtime"]
    if (not isinstance(loaded, dict)
            or set(loaded) != {"scheme", "python", "optimization", "module_files",
                              "definitions_sha256", "constants_sha256"}
            or loaded["scheme"] != "compiled-loaded-definitions-v1"
            or not isinstance(loaded["python"], str) or not loaded["python"]
            or type(loaded["optimization"]) is not int
            or not isinstance(loaded["module_files"], list) or not loaded["module_files"]
            or not all(isinstance(name, str) and name for name in loaded["module_files"])
            or not all(isinstance(loaded[key], str) and re.fullmatch(r"[0-9a-f]{64}", loaded[key])
                       for key in ("definitions_sha256", "constants_sha256"))):
        raise ValueError("Served runtime lacks loaded-definition and constant receipts")
    return data


def _selection(root: Path, freeze: dict, data: dict) -> list[dict]:
    if (set(data) != {"schema_version", "freeze_sha256", "contexts"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["freeze_sha256"] != readiness_freeze_fingerprint(freeze)
            or not isinstance(data["contexts"], list) or not data["contexts"]):
        raise ValueError("Preview selection requires schema 1 and the current freeze binding")
    seen = set()
    contexts = []
    for entry in data["contexts"]:
        if (not isinstance(entry, dict) or set(entry) != {"cohort", "team", "opponent", "side"}
                or not all(isinstance(value, str) and value for value in entry.values())
                or entry["cohort"] not in freeze["cohorts"] or entry["side"] not in {"home", "away"}
                or entry["team"] == entry["opponent"]):
            raise ValueError("Invalid selected preview context")
        cohort = freeze["cohorts"][entry["cohort"]]
        contract = _strict_json_object((root / cohort["contract"]["path"]).read_bytes())
        for key in ("team", "opponent"):
            if (entry[key] not in contract["teams"]
                    or not (root / cohort["season_dir"] / entry[key] / "offense.csv").is_file()):
                raise ValueError("Selected preview team is missing from frozen candidate")
        identity = entry["cohort"], entry["team"]
        if identity in seen:
            raise ValueError("Duplicate selected preview team")
        seen.add(identity)
        contexts.append({**entry, "season": str(contract["season"]),
                         "chart_fingerprint": cohort["chart_fingerprint"]})
    if {entry["cohort"] for entry in contexts} != set(freeze["cohorts"]):
        raise ValueError("Preview selection must include both frozen cohorts")
    return contexts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend-python", default=sys.executable)
    parser.add_argument("--backend-port", type=int, default=8004)
    parser.add_argument("--frontend-port", type=int, default=5177)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    result = {"passed": False, "release_certified": False, "selection_validated": False,
              "candidate_content_validated": False, "errors": [], "commands": {}}
    processes, logs = [], []
    created = False
    backend = None
    try:
        if (args.output.exists() or args.output.is_symlink()
                or not output.is_relative_to(ROOT / ".ai-audits")):
            raise ValueError("Preview output must be a new directory under ignored .ai-audits/")
        freeze_bytes, selection_bytes = args.freeze.read_bytes(), args.selection.read_bytes()
        freeze, selection = _strict_json_object(freeze_bytes), _strict_json_object(selection_bytes)
        before = audit_readiness_freeze(ROOT, freeze)
        if not before["passed"]:
            raise ValueError("Preview freeze preflight failed: " + "; ".join(before["errors"]))
        for entry in freeze["cohorts"].values():
            protected = [(ROOT / entry["season_dir"]).resolve(),
                         (ROOT / entry["contract"]["path"]).resolve().parent]
            protected.extend((ROOT / ref["path"]).resolve().parent for ref in entry["source_inputs"].values())
            if any(output.is_relative_to(path) for path in protected):
                raise ValueError("Preview cannot write inside candidate or source inputs")
        contexts = _selection(ROOT, freeze, selection)
        if args.backend_port == args.frontend_port:
            raise ValueError("Preview services require distinct ports")
        for port in (args.backend_port, args.frontend_port):
            _check_port(port)
        public = public_source_file_inventory(ROOT)
        intended = {name: sha for name, sha in public.items() if not name.startswith("seasons/")}
        output.mkdir(parents=True)
        created = True
        snapshot = output / "source"
        snapshot.mkdir()
        for name in intended:
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        candidates = {}
        for cohort, entry in freeze["cohorts"].items():
            source = ROOT / entry["season_dir"]
            candidates[cohort] = _files(source)
            season = "1983" if cohort == "1983-generated" else "2024"
            shutil.copytree(source, snapshot / "seasons" / season)
        if _files(snapshot, implementation=True) != intended or readiness_file_inventory(snapshot) != freeze["files"]:
            raise ValueError("Copied public implementation differs from freeze")
        environment = os.environ.copy()
        environment.update(PYTHONPATH=str(snapshot), PYTHONNOUSERSITE="1")
        frontend = snapshot / "paydirt-web/frontend"

        def execute(name: str, command: list[str]) -> None:
            execution = {"argv": command, "cwd": str(frontend), "pythonpath": str(snapshot)}
            try:
                done = subprocess.run(command, cwd=frontend, env=environment, text=True,
                                      capture_output=True, check=False, timeout=600)
                execution.update(returncode=done.returncode, stdout=done.stdout, stderr=done.stderr)
            except (OSError, subprocess.SubprocessError) as error:
                execution.update(returncode=None, stdout="", stderr=str(error))
            write_json(output / (name + ".json"), execution)
            result["commands"][name] = execution
            if execution["returncode"] != 0:
                raise RuntimeError(f"Preview {name} failed; see retained command log")

        execute("setup", ["npm", "ci"])
        backend_url = f"http://127.0.0.1:{args.backend_port}"
        frontend_url = f"http://127.0.0.1:{args.frontend_port}"
        plan = {"schema_version": 1, "freeze_sha256": readiness_freeze_fingerprint(freeze),
                "engine_fingerprint": freeze["engine_fingerprint"], "root": str(ROOT),
                "backend_url": backend_url, "frontend_url": frontend_url,
                "viewport": {"width": 1440, "height": 1100}, "contexts": contexts}
        write_json(output / "plan.json", plan)
        commands = [
            [args.backend_python, str(snapshot / "scripts/run_chart_preview_backend.py"),
             "--freeze", str(args.freeze.resolve()), "--receipt", str(output / "runtime-before.json"),
             "--port", str(args.backend_port)],
            ["node", str(frontend / "node_modules/vite/bin/vite.js"),
             "--host", "127.0.0.1", "--port", str(args.frontend_port), "--strictPort"],
        ]
        for index, command in enumerate(commands):
            log = (output / ("backend.log" if index == 0 else "frontend.log")).open("x")
            logs.append(log)
            process = subprocess.Popen(command, cwd=frontend, env=environment, stdout=log, stderr=subprocess.STDOUT)
            processes.append(process)
            if index == 0:
                backend = process
            _wait_service(process, backend_url + "/api/health" if index == 0 else frontend_url)
            if index == 0:
                result["runtime_before"] = _runtime(output / "runtime-before.json", freeze, snapshot, process.pid)
        execute("browser", ["node", str(frontend / "e2e/collect-chart-preview.cjs"),
                            "--plan", str(output / "plan.json"), "--output", str(output)])
        manifest_bytes = {name: (output / (name + ".json")).read_bytes() for name in ("captures", "content")}
        result["manifests"] = {name: {"path": (output / (name + ".json")).relative_to(ROOT).as_posix(),
                                     "sha256": hashlib.sha256(data).hexdigest()}
                               for name, data in manifest_bytes.items()}
        captures, content = (_strict_json_object(manifest_bytes[name]) for name in ("captures", "content"))
        result["content"] = audit_visual_content_evidence(ROOT, freeze, captures, content)
        if not result["content"]["passed"]:
            raise ValueError("Collected visual evidence failed: " + "; ".join(result["content"]["errors"]))
        selected = {(entry["cohort"], entry["team"]) for entry in contexts}
        if {(entry["cohort"], entry["team"]) for entry in captures["contexts"]} != selected:
            raise ValueError("Captured contexts differ from explicit selection")
        for entry in captures["contexts"]:
            receipt = _strict_json_object((ROOT / entry["capture"]["path"]).read_bytes())
            chosen = next(item for item in contexts if (item["cohort"], item["team"]) == (entry["cohort"], entry["team"]))
            state = _strict_json_object((ROOT / receipt["state_before"]["path"]).read_bytes())
            opponent_side = "away" if chosen["side"] == "home" else "home"
            if state.get(opponent_side + "_team", {}).get("id") != chosen["opponent"]:
                raise ValueError("Captured opponent differs from explicit selection")
            for section in receipt["sections"].values():
                url = urlparse(section["url"])
                if f"{url.scheme}://{url.netloc}" != frontend_url or parse_qs(url.query).get("side") != [chosen["side"]]:
                    raise ValueError("Capture used an unexpected preview origin or side")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        result["errors"].append(str(error))
    finally:
        for process in reversed(processes):
            try:
                if process.poll() is None:
                    process.terminate()
                else:
                    result["errors"].append("Preview service exited unexpectedly during capture")
                process.wait(timeout=5)
            except (OSError, subprocess.SubprocessError) as error:
                result["errors"].append(f"Service cleanup: {error}")
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()
    if created:
        try:
            if backend is not None and "runtime_before" in result:
                result["runtime_after"] = _runtime(output / "runtime-after.json", freeze, snapshot, backend.pid)
                if result["runtime_after"] != result["runtime_before"]:
                    raise ValueError("Served runtime changed during preview capture")
            if (args.freeze.read_bytes() != freeze_bytes or args.selection.read_bytes() != selection_bytes
                    or public_source_file_inventory(ROOT) != public):
                raise ValueError("Root implementation or original preview inputs changed during collection")
            after = audit_readiness_freeze(ROOT, freeze)
            if not after["passed"]:
                raise ValueError("Frozen input recheck failed: " + "; ".join(after["errors"]))
            if _files(snapshot, implementation=True) != intended or readiness_file_inventory(snapshot) != freeze["files"]:
                raise ValueError("Served public implementation changed during capture")
            if {path.name for path in (snapshot / "seasons").iterdir()} != {"1983", "2024"}:
                raise ValueError("Served preview contains an unexpected season directory")
            for cohort, entry in freeze["cohorts"].items():
                season = "1983" if cohort == "1983-generated" else "2024"
                served = snapshot / "seasons" / season
                if (_files(served) != candidates[cohort]
                        or chart_fingerprint(served) != entry["chart_fingerprint"]):
                    raise ValueError("Served candidate files changed during capture")
            if "manifests" in result:
                if any((output / (name + ".json")).read_bytes() != data for name, data in manifest_bytes.items()):
                    raise ValueError("Captured manifests changed during service shutdown")
                result["content"] = audit_visual_content_evidence(ROOT, freeze, captures, content)
                if not result["content"]["passed"]:
                    raise ValueError("Captured artifacts failed final recheck: " + "; ".join(result["content"]["errors"]))
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
            result["errors"].append(str(error))
        result["passed"] = not result["errors"]
        result["candidate_content_validated"] = result["passed"]
        write_json(output / "result.json", result)
    print(f"{'PASS' if result['passed'] else 'FAIL'}: {output}", flush=True)
    if result["errors"]:
        print("; ".join(result["errors"]), file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

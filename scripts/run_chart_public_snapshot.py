#!/usr/bin/env python3
"""Copy intended public files and collect complete unit suites in isolation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.chart_release_gate import (
    _strict_json_object,
    audit_public_snapshot,
    audit_readiness_freeze,
    chart_fingerprint,
    public_source_file_inventory,
    readiness_freeze_fingerprint,
    required_regression_commands,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory under ignored .ai-audits/")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output_allowed = False
    try:
        if args.output.exists() or args.output.is_symlink() or not output.is_relative_to(ROOT / ".ai-audits"):
            raise ValueError("Public unit collection requires a new directory under ignored .ai-audits/")
        freeze_bytes = args.freeze.read_bytes()
        freeze = _strict_json_object(freeze_bytes)
        for entry in freeze["cohorts"].values():
            protected = [(ROOT / entry["season_dir"]).resolve(), (ROOT / entry["contract"]["path"]).resolve().parent]
            protected.extend((ROOT / ref["path"]).resolve().parent for ref in entry["source_inputs"].values())
            if any(output.is_relative_to(path) for path in protected):
                raise ValueError("Public unit collection cannot write inside candidate or source inputs")
        output_allowed = True
        before = audit_readiness_freeze(ROOT, freeze)
        if not before["passed"]:
            raise ValueError("Public unit freeze preflight failed: " + "; ".join(before["errors"]))
        for name, entry in freeze["cohorts"].items():
            if chart_fingerprint(ROOT / "seasons" / name) != entry["chart_fingerprint"]:
                raise ValueError(f"Canonical seasons/{name} does not match the frozen candidate")
        files = public_source_file_inventory(ROOT)
        snapshot = output / "source"
        snapshot.mkdir(parents=True)
        for name in files:
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        evidence = {"schema_version": 1, "freeze_sha256": readiness_freeze_fingerprint(freeze),
                    "snapshot_dir": str(snapshot), "files": files, "commands": {}}
        environment = os.environ.copy()
        environment.update({"PYTHONPATH": str(snapshot), "PYTHONNOUSERSITE": "1"})
        required = {"setup": ("paydirt-web/frontend", ["npm", "ci"])}
        required.update({name: value for name, value in required_regression_commands().items()
                         if name in {"core", "backend", "frontend"}})
        for name, (cwd, command) in required.items():
            print(f"RUN {name}", flush=True)
            execution = {"argv": command, "cwd": str((snapshot / cwd).resolve()), "pythonpath": str(snapshot)}
            try:
                completed = subprocess.run(command, cwd=snapshot / cwd, env=environment,
                                           text=True, capture_output=True, check=False)
                execution.update({"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
            except OSError as error:
                execution.update({"returncode": None, "stdout": "", "stderr": str(error)})
            log = output / (name + ".json")
            write_json(log, execution)
            evidence["commands"][name] = {"path": str(log), "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
            print(f"EXIT {name} {execution['returncode']}", flush=True)
        write_json(output / "evidence.json", evidence)
        result = audit_public_snapshot(ROOT, freeze, evidence)
        result["freeze_file"] = {"path": str(args.freeze.resolve()), "sha256": hashlib.sha256(freeze_bytes).hexdigest()}
        if args.freeze.read_bytes() != freeze_bytes:
            result["errors"].append("Freeze file changed during public unit collection")
        result["passed"] = not result["errors"]
        write_json(output / "result.json", result)
        print(f"{'PASS' if result['passed'] else 'FAIL'}: {output / 'result.json'}", flush=True)
        return 0 if result["passed"] else 1
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        failure = {"passed": False, "release_certified": False, "errors": [str(error)]}
        if output_allowed and not (output / "result.json").exists():
            try:
                write_json(output / "result.json", failure)
            except OSError as output_error:
                print(f"Cannot retain public collection failure: {output_error}", file=sys.stderr)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

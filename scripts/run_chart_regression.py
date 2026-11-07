#!/usr/bin/env python3
"""Collect the complete AGENTS regression against a stable frozen local candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.chart_release_gate import (
    _strict_json_object,
    audit_readiness_freeze,
    audit_regression_evidence,
    audit_regression_outputs,
    chart_fingerprint,
    readiness_freeze_fingerprint,
    regression_ai_input_fingerprints,
    required_regression_commands,
)


def occupied_review_ports() -> list[int]:
    """Detect existing review services without stopping or changing them."""
    occupied = []
    for port in (8000, 5173):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                occupied.append(port)
        except OSError:
            pass
    return occupied


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
            raise ValueError("Regression collection requires a new directory under ignored .ai-audits/")
        freeze_bytes = args.freeze.read_bytes()
        freeze = _strict_json_object(freeze_bytes)
        for entry in freeze["cohorts"].values():
            protected = [(ROOT / entry["season_dir"]).resolve(), (ROOT / entry["contract"]["path"]).resolve().parent]
            protected.extend((ROOT / ref["path"]).resolve().parent for ref in entry["source_inputs"].values())
            if any(output.is_relative_to(path) for path in protected):
                raise ValueError("Regression collection cannot write inside candidate or source inputs")
        output_allowed = True
        before = audit_readiness_freeze(ROOT, freeze)
        if not before["passed"]:
            raise ValueError("Regression freeze preflight failed: " + "; ".join(before["errors"]))
        for name, entry in freeze["cohorts"].items():
            if chart_fingerprint(ROOT / "seasons" / name) != entry["chart_fingerprint"]:
                raise ValueError(f"Canonical seasons/{name} does not match the frozen candidate")
        from paydirt.chart_source_bundle import prepared_source_options
        source_receipts = {}
        for name, entry in freeze["cohorts"].items():
            year = "1983" if name == "1983-generated" else "2024"
            receipt = ROOT / f".ai-audits/chart-sources/{year}/source.json"
            contract_path = (ROOT / entry["contract"]["path"]).resolve()
            if (ROOT / f"config/chart-validation/{year}.json").read_bytes() != contract_path.read_bytes():
                raise ValueError(f"Canonical contract {year} differs from the frozen source contract")
            prepared_source_options(receipt, ROOT / "seasons" / name, contract_path)
            source_receipts[year] = {"path": str(receipt), "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()}
        ai_inputs = regression_ai_input_fingerprints(ROOT)
        ports = occupied_review_ports()
        if ports:
            raise ValueError(f"Review services still occupy {ports}; notify the parent and stop them before isolated browser regression")
        output.mkdir(parents=True)
        evidence = {"schema_version": 1, "freeze_sha256": readiness_freeze_fingerprint(freeze), "commands": {}}
        artifacts: dict[str, dict] = {}
        errors: list[str] = []
        for name, (cwd, command) in required_regression_commands().items():
            produced = {flag: ROOT / command[command.index(flag) + 1] for flag in ("--output", "--csv") if flag in command}
            previous = {flag: (path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else None
                        for flag, path in produced.items()}
            print(f"RUN {name}", flush=True)
            try:
                completed = subprocess.run(command, cwd=ROOT / cwd, text=True, capture_output=True, check=False)
                execution = {"argv": command, "cwd": str((ROOT / cwd).resolve()), "returncode": completed.returncode,
                             "stdout": completed.stdout, "stderr": completed.stderr}
            except OSError as error:
                execution = {"argv": command, "cwd": str((ROOT / cwd).resolve()), "returncode": None,
                             "stdout": "", "stderr": str(error)}
            log = output / (name + ".json")
            write_json(log, execution)
            evidence["commands"][name] = {"path": str(log), "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
            for flag, path in produced.items():
                try:
                    if previous[flag] == (path.stat().st_mtime_ns, path.stat().st_size):
                        raise ValueError("Produced artifact was not refreshed by its command")
                    data = path.read_bytes()
                    label = name + ("_csv" if flag == "--csv" else "_json")
                    captured = output / "artifacts" / (label + path.suffix)
                    captured.parent.mkdir(parents=True, exist_ok=True)
                    with captured.open("xb") as stream:
                        stream.write(data)
                    artifacts[label] = {"path": str(captured), "sha256": hashlib.sha256(data).hexdigest(), "original_path": str(path)}
                except (ValueError, OSError) as error:
                    errors.append(f"{name} {flag}: {error}")
            print(f"EXIT {name} {execution['returncode']}", flush=True)
        write_json(output / "evidence.json", evidence)
        output_evidence = {"schema_version": 1, "freeze_sha256": readiness_freeze_fingerprint(freeze),
                           "artifacts": artifacts, "ai_inputs": ai_inputs, "source_receipts": source_receipts}
        write_json(output / "outputs.json", output_evidence)
        result = audit_regression_evidence(ROOT, freeze, evidence)
        result["outputs"] = audit_regression_outputs(ROOT, freeze, output_evidence)
        errors.extend(f"Outputs: {reason}" for reason in result["outputs"]["errors"])
        result["produced_artifacts"] = artifacts
        result["freeze_file"] = {"path": str(args.freeze.resolve()), "sha256": hashlib.sha256(freeze_bytes).hexdigest()}
        if args.freeze.read_bytes() != freeze_bytes:
            errors.append("Freeze file changed during collection")
        for reference in artifacts.values():
            if hashlib.sha256(Path(reference["path"]).read_bytes()).hexdigest() != reference["sha256"]:
                errors.append("Captured regression artifact changed during collection")
        result["errors"].extend(errors)
        result["passed"] = not result["errors"]
        result["scope"] += " Actual AI/CSV/chart outputs receive independent semantic checks; full charter acceptance remains separate."
        write_json(output / "result.json", result)
        print(f"{'PASS' if result['passed'] else 'FAIL'}: {output / 'result.json'}", flush=True)
        return 0 if result["passed"] else 1
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        failure = {"passed": False, "release_certified": False, "errors": [str(error)]}
        if output_allowed and not (output / "result.json").exists():
            try:
                write_json(output / "result.json", failure)
            except OSError as output_error:
                print(f"Cannot retain collection failure: {output_error}", file=sys.stderr)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

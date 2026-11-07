#!/usr/bin/env python3
"""Prepare bound local public sources and reproduction paths for the chart gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.chart_source_bundle import prepare_chart_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--reproduced-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New preparation receipt; success also writes STEM-inputs.json for the gate")
    args = parser.parse_args(argv)
    receipt = args.output.resolve()
    inputs = receipt.with_name(receipt.stem + "-inputs.json")
    reproduced = args.reproduced_dir.resolve()
    protected = (args.bundle.resolve(), args.candidate_dir.resolve(), reproduced,
                 reproduced.with_name(reproduced.name + "-classified"))
    log = reproduced.with_suffix(".log")
    output_allowed = False
    try:
        for destination in (receipt, inputs):
            if (destination.exists() or destination.is_symlink() or destination == log
                    or any(destination.is_relative_to(path) for path in protected)):
                raise ValueError("Preparation receipts must use new paths outside inputs, candidate and producer outputs")
        output_allowed = True
        result = prepare_chart_sources(args.bundle, args.candidate_dir, args.reproduced_dir)
        passed = result.get("passed") is True and not result.get("errors")
        result["passed"], result["release_certified"] = passed, False
        if passed:
            paths = result["source_paths"]["input_files"]
            inputs.parent.mkdir(parents=True, exist_ok=True)
            with inputs.open("x") as stream:
                stream.write(json.dumps(paths, sort_keys=True, indent=2, allow_nan=False) + "\n")
            result["gate_input_inventory"] = str(inputs)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with receipt.open("x") as stream:
            stream.write(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
        print(f"{'PASS' if passed else 'FAIL'}: {receipt}", flush=True)
        return 0 if passed else 1
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        failure = {"passed": False, "release_certified": False, "errors": [str(error)]}
        if output_allowed and not receipt.exists():
            try:
                receipt.parent.mkdir(parents=True, exist_ok=True)
                with receipt.open("x") as stream:
                    stream.write(json.dumps(failure, indent=2) + "\n")
            except OSError as output_error:
                print(f"Cannot retain preparation failure: {output_error}", file=sys.stderr)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

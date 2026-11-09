#!/usr/bin/env python3
"""Compute the exact 1977 exception component; never certify a whole release.

Source-map values may be absolute or relative to --root. Reports are created
exclusively outside chart/source directories; existing evidence is never replaced.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paydirt.chart_release_gate import audit_statistical_release_exception


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate source-map key: {key}")
        result[key] = value
    return result


def _input_files(path: Path, root: Path) -> dict[str, Path]:
    values = json.loads(path.read_text(), object_pairs_hook=_unique_object)
    if (not isinstance(values, dict) or not values
            or any(not key.strip() or not isinstance(value, str) or not value.strip()
                   for key, value in values.items())):
        raise ValueError("Input-files JSON must map nonempty logical keys to nonempty path strings")
    return {key: (root / value).resolve() for key, value in values.items()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for option in ("root", "season-dir", "contract", "engine-report", "policy",
                   "public-season-dir", "stats-dir", "reproduced-dir", "input-files", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("Output already exists; preserve existing evidence")
        root = args.root.resolve()
        output = args.output.resolve()
        sources = _input_files(args.input_files, root)
        files = [args.contract, args.engine_report, args.policy, args.input_files, *sources.values()]
        if any(output.is_relative_to(path.resolve()) for path in files):
            raise ValueError("Output collides with an input file")
        directories = [args.season_dir, args.public_season_dir, args.stats_dir, args.reproduced_dir]
        if any(output.is_relative_to(path.resolve()) for path in directories):
            raise ValueError("Output must be outside all chart/source input directories")
        result = audit_statistical_release_exception(
            root, args.season_dir.resolve(), args.contract.resolve(), args.engine_report.resolve(),
            args.policy.resolve(), public_dir=args.public_season_dir.resolve(),
            stats_dir=args.stats_dir.resolve(), reproduced_dir=args.reproduced_dir.resolve(),
            input_files=sources,
        )
        if not isinstance(result, dict):
            raise TypeError("Audit returned a non-object result")
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        passed = result.get("passed") is True
        print(f"{'PASS' if passed else 'FAIL'}: statistical exception component only: {output}")
        return 0 if passed else 1
    except (OSError, ValueError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

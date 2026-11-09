#!/usr/bin/env python3
"""Audit only the two reviewed public-generated source/output sets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.generated_source_audit import audit_generated_source


def main() -> int:
    """Write a source consistency report and fail on unresolved discrepancies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", required=True, type=int, choices=(1983, 2024))
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--reproduced-dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    season_dir = ROOT / "seasons" / str(args.season)
    contract = json.loads(
        (ROOT / "config" / "chart-validation" / f"{args.season}.json").read_text()
    )
    report = audit_generated_source(
        season_dir,
        stats_dir=args.stats_dir,
        reproduced_dir=args.reproduced_dir,
        validation_contract=contract,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "season": args.season,
                "passed": report["passed"],
                "errors": report["errors"],
                "checks": report["checks"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

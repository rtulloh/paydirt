#!/usr/bin/env python3
"""Check committed charts without private source data or historical fit claims."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.chart_audit import audit_public_season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season-dir", type=Path, required=True)
    parser.add_argument("--expected-teams", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve().is_relative_to(args.season_dir.resolve()):
        parser.error("Audit output must be outside the committed chart inputs")
    try:
        result = audit_public_season(args.season_dir, expected_teams=args.expected_teams)
    except (OSError, ValueError) as error:
        result = {"passed": False, "errors": [str(error)], "release_certified": False,
                  "source_reproduction_checked": False, "historical_accuracy_checked": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("passed", "errors", "release_certified")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the synthetic chart event-allocation gate without installed team data.

Run from the repository root with Python 3.10 or newer. This audits generator
event preservation and finite-row probability fidelity, not historical fit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.chart_allocation_gate import audit_allocations


def main() -> int:
    """Write an aggregate audit report and fail when an allocation check fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, default=[8306, 9241, 11713])
    args = parser.parse_args()
    report = audit_allocations(seeds=args.seeds)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

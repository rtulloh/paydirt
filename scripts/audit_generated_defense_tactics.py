"""Audit generated defenses using exact resolver distributions and engine controls.

Only public2026 fixtures or explicitly public-provenance generation manifests are
accepted. This standalone runner never reads imported private historical charts.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.chart_loader import parse_defense_csv
from paydirt.chart_tactics_audit import (
    audit_defense_tactics,
    audit_engine_controls,
    audit_generated_strength_order,
    audit_priority_resolution,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--season-dir",
        type=Path,
        action="append",
        help="Public fixture/generated season; repeat for multiple sets",
    )
    parser.add_argument("--output", type=Path, help="Write aggregate JSON report here")
    parser.add_argument(
        "--engine-checks",
        choices=("all", "first", "none"),
        default="all",
        help="Stateful controls; release gating requires all (default)",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    roots = args.season_dir or [repo / "seasons" / "2026"]
    report = {
        "passed": True,
        "engine_checks": args.engine_checks,
        "teams": {},
        "scope": "Exact pre-state priority/B/QT plus controlled own40 stateful engine; "
        "historical accuracy, returns/recovery decisions and whole games are separate.",
    }
    priority = audit_priority_resolution()
    report["priority"] = {
        "passed": priority.passed,
        "findings": [asdict(f) for f in priority.findings],
    }
    report["passed"] &= priority.passed
    strength = audit_generated_strength_order()
    report["generated_strength"] = asdict(strength)
    report["generated_strength"]["passed"] = strength.passed
    report["passed"] &= strength.passed
    engine_checked = False
    for root in roots:
        root = root.resolve()
        if root != (repo / "seasons" / "2026").resolve():
            manifest = root / "generation-manifest.json"
            if not manifest.is_file():
                raise ValueError(f"Refusing nonpublic season without generation manifest: {root}")
            source = json.loads(manifest.read_text()).get("source", "")
            if not any(public in source for public in ("nflverse", "Pro Football Reference")):
                raise ValueError(f"Unrecognized public generation provenance in {manifest}")
        files = sorted(root.glob("*/defense.csv"))
        if not files:
            raise ValueError(f"No defense charts in {root}")
        for path in files:
            defense = parse_defense_csv(str(path))
            result = audit_defense_tactics(defense)
            row = asdict(result)
            row["passed"] = result.passed
            if args.engine_checks == "all" or (
                args.engine_checks == "first" and not engine_checked
            ):
                engine_result = audit_engine_controls(defense)
                row["engine"] = {
                    "passed": engine_result.passed,
                    "findings": [asdict(f) for f in engine_result.findings],
                }
                row["passed"] &= engine_result.passed
                engine_checked = True
            report["teams"][f"{root.name}/{path.parent.name}"] = row
            report["passed"] &= row["passed"]
            print(
                f"{'PASS' if row['passed'] else 'FAIL'} {root.name}/{path.parent.name}: "
                f"{len(result.findings)} blocking, {len(result.diagnostics)} exploratory",
                flush=True,
            )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {len(report['teams'])} defenses audited")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

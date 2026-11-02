#!/usr/bin/env python3
"""Tune generated Paydirt charts against engine calibration reports."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from paydirt.chart_tuning import load_tuning_config, run_tuning


def main(argv: Sequence[str] | None = None) -> int:
    """Run bounded chart tuning and held-out validation from a local JSON config."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Local tuning JSON file")
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="New empty directory for generated candidates and audit reports",
    )
    parser.add_argument(
        "--training-seasons",
        type=int,
        default=64,
        help="Full seasons per candidate profile (default 64)",
    )
    parser.add_argument(
        "--validation-seasons",
        type=int,
        default=256,
        help="Held-out seasons for the selected profile (default 256)",
    )
    args = parser.parse_args(argv)
    try:
        config = load_tuning_config(args.config)
        result = run_tuning(
            config,
            workspace=args.workspace,
            training_seasons=args.training_seasons,
            validation_seasons=args.validation_seasons,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Chart tuning failed: {error}", file=sys.stderr)
        return 1

    validation = result["validation"]
    status = "passed" if validation["within_tolerance"] else "failed"
    print(
        f"Chart tuning selected {json.dumps(result['selected_profile'], sort_keys=True)}; "
        f"held-out validation {status} with loss {validation['loss']:.4f}."
    )
    print(f"Audit report: {args.workspace / 'tuning-report.json'}")
    return int(not validation["within_tolerance"])


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify and stage a pinned local source archive; performs no download or publication."""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paydirt.chart_source_bundle import unpack_chart_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = unpack_chart_sources(args.archive, args.sha256, args.destination)
    except (ValueError, KeyError, TypeError, OSError, tarfile.TarError) as error:
        result = {"passed": False, "release_certified": False, "errors": [str(error)]}
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

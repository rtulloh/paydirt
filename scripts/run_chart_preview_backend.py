#!/usr/bin/env python3
"""Serve the isolated snapshot and attest loaded runtime before and after capture."""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "paydirt-web/backend"))

from paydirt.chart_engine_audit import engine_fingerprint
from paydirt.chart_release_gate import (
    _strict_json_object,
    readiness_file_inventory,
    readiness_freeze_fingerprint,
)
from paydirt.chart_runtime_identity import loaded_runtime_identity
from scripts.run_chart_preview import write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)
    freeze = _strict_json_object(args.freeze.read_bytes())
    modules = {name: importlib.import_module(name) for name in ("main", "routes", "chart_viewer")}
    for name, module in modules.items():
        if Path(module.__file__).resolve() != ROOT / "paydirt-web/backend" / (name + ".py"):
            raise ValueError("Preview backend imported outside isolated source")
    def receipt() -> dict:
        files = readiness_file_inventory(ROOT)
        fingerprint = engine_fingerprint()
        if files != freeze["files"] or fingerprint != freeze["engine_fingerprint"]:
            raise ValueError("Loaded preview source differs from freeze")
        return {"schema_version": 1, "freeze_sha256": readiness_freeze_fingerprint(freeze),
                "engine_fingerprint": fingerprint, "source_root": str(ROOT),
                "process_id": os.getpid(), "implementation_files": files,
                "loaded_runtime": loaded_runtime_identity()}
    write_json(args.receipt, receipt())
    import uvicorn
    try:
        uvicorn.run(modules["main"].app, host="127.0.0.1", port=args.port, reload=False)
    finally:
        write_json(args.receipt.with_name("runtime-after.json"), receipt())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

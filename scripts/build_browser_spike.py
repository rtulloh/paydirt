"""Stage public sample assets for the FLOW-033 browser feasibility spike.

This is a sample-only experiment, not the v1.11.0 release asset inventory.
No recursive source-directory copying or implicit asset discovery is permitted.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

# Reviewed import closure of routes/chart_viewer plus the browser transport.
# Additions require review; unrelated code, user data and other seasons stay out.
PUBLIC_FILES = (
    "paydirt/__init__.py",
    "paydirt/ai_analysis.py",
    "paydirt/chart_layout.py",
    "paydirt/chart_loader.py",
    "paydirt/commentary.py",
    "paydirt/computer_ai.py",
    "paydirt/game_engine.py",
    "paydirt/game_state.py",
    "paydirt/interception_policy.py",
    "paydirt/offense_strategy.py",
    "paydirt/overtime_rules.py",
    "paydirt/packaging.py",
    "paydirt/penalty_handler.py",
    "paydirt/play_events.py",
    "paydirt/play_resolver.py",
    "paydirt/priority_chart.py",
    "paydirt/season_rules.py",
    "paydirt/utils.py",
    "paydirt-web/backend/browser_bridge.py",
    "paydirt-web/backend/operations.py",
    "paydirt-web/backend/routes.py",
    "paydirt-web/backend/chart_viewer.py",
    "docs/installation.md",
    "docs/web-interface.md",
    "docs/playing.md",
    "docs/priority-chart.md",
    "docs/clock-management.md",
    "docs/ai-difficulty.md",
    "docs/seasons.md",
    "docs/chart-generator.md",
    "docs/saved-games-and-standings.md",
    "docs/images/defense.png",
    "docs/images/coin-toss.png",
    "docs/images/start-game-menu.png",
    "docs/images/menu.png",
    "docs/images/kickoff-and-scoreboard.png",
    "docs/images/offense.png",
    "docs/images/team-select.png",
    "seasons/2026/Ironclads/team.yaml",
    "seasons/2026/Ironclads/offense.csv",
    "seasons/2026/Ironclads/defense.csv",
    "seasons/2026/Ironclads/special.csv",
    "seasons/2026/Ironclads/roster.json",
    "seasons/2026/Thunderhawks/team.yaml",
    "seasons/2026/Thunderhawks/offense.csv",
    "seasons/2026/Thunderhawks/defense.csv",
    "seasons/2026/Thunderhawks/special.csv",
    "seasons/2026/Thunderhawks/roster.json",
    "seasons/2026/2026.yaml",
    "seasons/2026/ai_behavior.yaml",
    "LICENSE",
    "README.md",
    "CHART_ATTRIBUTION.md",
)
OUTPUT_FILES = {"python.zip", "manifest.json"}


def _reject_symlinks(path: Path, stop: Path | None = None) -> None:
    """Reject an asset or parent that redirects outside its declared location."""
    for component in (path, *path.parents):
        if component == stop:
            break
        if component.is_symlink():
            raise ValueError(f"Symlink is not permitted: {component}")


def _validate_output(root: Path, output: Path) -> Path:
    """Protect source files and unrelated existing output from replacement."""
    _reject_symlinks(output)
    output = output.resolve()
    if output == root or output in root.parents:
        raise ValueError(f"Unsafe output overlaps source root: {output}")
    if root in output.parents:
        relative = output.relative_to(root)
        if relative.parts[0] != ".ai-audits" or len(relative.parts) < 2:
            raise ValueError(f"Unsafe output inside source tree: {output}")
    if output.exists():
        if not output.is_dir():
            raise ValueError(f"Unsafe output is not a directory: {output}")
        for child in output.iterdir():
            _reject_symlinks(child, output)
            if child.name not in OUTPUT_FILES or not child.is_file():
                raise ValueError(f"Unexpected output file: {child}")
    return output


def build_bundle(source_root: Path, output: Path) -> dict[str, Any]:
    """Build deterministic sample assets and their SHA-256 inventory.

    Args:
        source_root: Repository or synthetic export containing the exact allowlist.
        output: Empty staging directory, or a previous two-file build directory.

    Returns:
        The manifest written beside python.zip for extraction into /app.
    """
    root = source_root.resolve()
    output = _validate_output(root, output.absolute())
    contents = []
    for relative in sorted(PUBLIC_FILES):
        asset = root / relative
        _reject_symlinks(asset, root)
        if not asset.is_file():
            raise ValueError(f"Missing public asset: {relative}")
        contents.append((relative, asset.read_bytes()))

    buffer = io.BytesIO()
    inventory = []
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, data in contents:
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
            inventory.append({
                "path": relative, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
    archive_bytes = buffer.getvalue()
    manifest = {
        "version": 1,
        "scope": "public-2026-spike",
        "files": [{
            "url": "python.zip", "mount": "/app", "bytes": len(archive_bytes),
            "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        }],
        "inventory": inventory,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "python.zip").write_bytes(archive_bytes)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Build the exact public sample bundle from this repository or an export."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path, default=Path(__file__).resolve().parents[1],
        help="Repository/export root containing the reviewed public assets",
    )
    parser.add_argument(
        "--output", type=Path,
        help="Empty staging directory (default: .ai-audits/browser-spike/staging)",
    )
    args = parser.parse_args(argv)
    output = args.output or args.source_root / ".ai-audits/browser-spike/staging"
    try:
        manifest = build_bundle(args.source_root, output)
    except ValueError as error:
        parser.error(str(error))
    print(f"Staged {len(manifest['inventory'])} public files in {output}")
    print(f"python.zip SHA-256: {manifest['files'][0]['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

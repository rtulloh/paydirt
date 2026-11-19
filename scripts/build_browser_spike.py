"""Stage the explicitly reviewed released public seasons for the browser build.

Chart bytes are preserved; only the reviewed asset inventory is staged.
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
PUBLIC_SEASONS = {
    "1977": (
        "49ers", "Bears", "Bengals", "Bills", "Broncos",
        "Browns", "Buccaneers", "Cardinals", "Chargers", "Chiefs",
        "Colts", "Cowboys", "Dolphins", "Eagles", "Falcons",
        "Giants", "Jets", "Lions", "Oilers", "Packers",
        "Patriots", "Raiders", "Rams", "Redskins", "Saints",
        "Seahawks", "Steelers", "Vikings",
    ),
    "1983": (
        "49ers", "Bears", "Bengals", "Bills", "Broncos",
        "Browns", "Buccaneers", "Cardinals", "Chargers", "Chiefs",
        "Colts", "Cowboys", "Dolphins", "Eagles", "Falcons",
        "Giants", "Jets", "Lions", "Oilers", "Packers",
        "Patriots", "Raiders", "Rams", "Redskins", "Saints",
        "Seahawks", "Steelers", "Vikings",
    ),
    "2024": (
        "49ers", "Bears", "Bengals", "Bills", "Broncos",
        "Browns", "Buccaneers", "Cardinals", "Chargers", "Chiefs",
        "Colts", "Commanders", "Cowboys", "Dolphins", "Eagles",
        "Falcons", "Giants", "Jaguars", "Jets", "Lions",
        "Packers", "Panthers", "Patriots", "Raiders", "Rams",
        "Ravens", "Saints", "Seahawks", "Steelers", "Texans",
        "Titans", "Vikings",
    ),
    "2026": (
        "Ironclads", "Thunderhawks",
    ),
}
TEAM_FILES = ("team.yaml", "offense.csv", "defense.csv", "special.csv", "roster.json")
SEASON_DOCUMENTS = (
    'seasons/1977/NOTES.md',
    'seasons/1977/generation-manifest.json',
    'seasons/1983/ATTRIBUTION.md',
    'seasons/1983/chart-audit.json',
    'seasons/1983/generation-manifest.json',
    'seasons/2024/ATTRIBUTION.md',
    'seasons/2024/chart-audit.json',
    'seasons/2024/generation-manifest.json',
    "seasons/2026/ai_behavior.yaml",
)

PUBLIC_FILES = (
    "paydirt/__init__.py",
    "paydirt/ai_analysis.py",
    "paydirt/auto_game.py",
    "paydirt/campaigns.py",
    "paydirt/campaign_simulation.py",
    "paydirt/chart_layout.py",
    "paydirt/chart_loader.py",
    "paydirt/commentary.py",
    "paydirt/computer_ai.py",
    "paydirt/game_engine.py",
    "paydirt/game_state.py",
    "paydirt/interception_policy.py",
    "paydirt/kicking_stats.py",
    "paydirt/offense_strategy.py",
    "paydirt/offense_stats.py",
    "paydirt/team_stats.py",
    "paydirt/overtime_rules.py",
    "paydirt/packaging.py",
    "paydirt/penalty_handler.py",
    "paydirt/play_events.py",
    "paydirt/play_resolver.py",
    "paydirt/priority_chart.py",
    "paydirt/season_rules.py",
    "paydirt/utils.py",
    "paydirt-web/backend/browser_bridge.py",
    "paydirt-web/backend/checkpoints.py",
    "paydirt-web/backend/campaign_operations.py",
    "paydirt-web/backend/native_library_operations.py",
    "config/season-schedules/1983.json",
    "config/season-schedules/2024.json",
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
    "LICENSE",
    "README.md",
    "CHART_ATTRIBUTION.md",
) + tuple(
    f"seasons/{year}/{team}/{name}"
    for year, teams in PUBLIC_SEASONS.items() for team in teams for name in TEAM_FILES
) + tuple(f"seasons/{year}/{year}.yaml" for year in PUBLIC_SEASONS) + SEASON_DOCUMENTS

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
    """Build deterministic public assets and their SHA-256 inventory.

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
        "scope": "public-released-seasons",
        "seasons": {year: list(teams) for year, teams in PUBLIC_SEASONS.items()},
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
    """Build the exact public released-season bundle from this repository or an export."""
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

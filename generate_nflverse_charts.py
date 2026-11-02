"""Generate Paydirt charts from nflverse regular-season play-by-play data."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from paydirt.chart_audit import audit_season
from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    generate_team_charts,
)
from paydirt.chart_source_coverage import source_feature_coverage
from paydirt.chart_tuning import apply_profile_overrides, load_calibration_profile
from paydirt.empirical_adjustment import (
    adjust_empirical_offense,
    calibrate_defense_stats,
    scale_empirical_run_yards,
)
from paydirt.nflverse_play_by_play import load_nflverse_play_by_play
from paydirt.pfr_play_by_play import EmpiricalPlay, calibrate_stats_from_pbp


def _load_team_map(path: Path) -> dict[str, str]:
    """Load and normalize an nflverse abbreviation to local team-name mapping."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Team map must be a nonempty JSON object")
    return {str(key).upper(): str(value) for key, value in data.items()}


def _select_empirical_plays(
    plays: Sequence[EmpiricalPlay],
) -> tuple[list[EmpiricalPlay], int]:
    """Keep chart columns with enough resolved outcomes for stable quantization."""
    grouped: dict[tuple[str, str], list[EmpiricalPlay]] = defaultdict(list)
    for play in plays:
        grouped[(play.unit, play.chart)].append(play)

    selected: list[EmpiricalPlay] = []
    fallback_columns = 0
    for (unit, chart), column_plays in grouped.items():
        resolved = [
            play
            for play in column_plays
            if not play.result.upper().startswith(("OFF ", "DEF ", "PI "))
        ]
        minimum = 12 if unit == "offense" else 8
        if unit == "special_teams" and chart == "interception_return":
            minimum = 3
        if len(resolved) < minimum:
            fallback_columns += 1
            continue
        selected.extend(column_plays)
    return selected, fallback_columns


def _write_empirical_csv(path: Path, plays: Sequence[EmpiricalPlay]) -> None:
    """Write classified outcomes with source provenance for local auditing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "team",
        "opponent",
        "unit",
        "chart",
        "result",
        "game_id",
        "play_number",
        "detail",
    )
    with path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(play.to_row() for play in plays)


def _copy_file_unless_same(source: Path, destination: Path) -> None:
    """Copy one metadata file unless generation is updating its source directory."""
    if source.resolve() == destination.resolve():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_season_metadata(template: Path, output: Path, season: int) -> None:
    """Copy the season rules file required by generated team directories."""
    source = template / f"{season}.yaml"
    if not source.exists():
        raise FileNotFoundError(f"Missing season rules file: {source}")
    output.mkdir(parents=True, exist_ok=True)
    _copy_file_unless_same(source, output / source.name)


def _copy_team_metadata(template: Path, output: Path, team_name: str) -> None:
    """Copy optional roster metadata used by commentary and local simulations."""
    roster = template / team_name / "roster.json"
    if roster.exists():
        _copy_file_unless_same(roster, output / team_name / "roster.json")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the nflverse play-by-play chart generation command."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate opponent-adjusted team charts from nflverse regular-season "
            "play-by-play and normalized aggregate statistics"
        )
    )
    parser.add_argument("--pbp", required=True, help="nflverse CSV or CSV.gz file")
    parser.add_argument("--stats-dir", required=True, help="Normalized team JSON directory")
    parser.add_argument(
        "--template-season",
        required=True,
        help="Season directory containing rules and optional roster metadata",
    )
    parser.add_argument("--team-map", required=True, help="Abbreviation-to-team JSON map")
    parser.add_argument("--output", required=True, help="Generated season directory")
    parser.add_argument("--audit-dir", required=True, help="Classified local audit CSV directory")
    parser.add_argument("--seed", type=int, default=8306, help="Stable generation seed")
    parser.add_argument(
        "--calibration-profile",
        type=Path,
        help="JSON generator profile; explicit adjustment flags override its values",
    )
    parser.add_argument(
        "--opponent-shrinkage",
        type=float,
        default=24.0,
        help="Ridge pseudo-count for separating offense and defense effects",
    )
    parser.add_argument(
        "--run-yard-multiplier",
        type=float,
        default=None,
        help="Engine-calibrated multiplier for resolved empirical run yards",
    )
    parser.add_argument(
        "--pass-completion-adjustment",
        type=float,
        default=None,
        help="Engine-calibrated change to empirical completion probability",
    )
    parser.add_argument(
        "--pass-interception-adjustment",
        type=float,
        default=None,
        help="Engine-calibrated change to empirical interception probability",
    )
    parser.add_argument(
        "--pass-pressure-adjustment",
        type=float,
        default=None,
        help="Engine-calibrated change to empirical pressure probability",
    )
    parser.add_argument(
        "--pass-yard-multiplier",
        type=float,
        default=None,
        help="Engine-calibrated multiplier for resolved empirical pass yards",
    )
    args = parser.parse_args(argv)
    profile = apply_profile_overrides(
        load_calibration_profile(args.calibration_profile),
        {
            "run_yard_multiplier": args.run_yard_multiplier,
            "pass_completion_adjustment": args.pass_completion_adjustment,
            "pass_interception_adjustment": args.pass_interception_adjustment,
            "pass_pressure_adjustment": args.pass_pressure_adjustment,
            "pass_yard_multiplier": args.pass_yard_multiplier,
        },
    )

    stats_dir = Path(args.stats_dir)
    template = Path(args.template_season)
    output = Path(args.output)
    audit_dir = Path(args.audit_dir)
    team_map = _load_team_map(Path(args.team_map))
    season_data = load_nflverse_play_by_play(args.pbp, seed=args.seed)

    coverage = source_feature_coverage(
        (play.to_row() for play in season_data.plays),
        field_goal_blocks=sum(attempt.blocked for attempt in season_data.field_goals),
    )

    adjusted = adjust_empirical_offense(
        season_data.plays,
        shrinkage=args.opponent_shrinkage,
    )
    plays_by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in season_data.plays:
        if play.unit != "offense":
            plays_by_team[play.team].append(play)
    for team, team_plays in adjusted.plays_by_team.items():
        plays_by_team[team].extend(
            scale_empirical_run_yards(team_plays, profile.run_yard_multiplier)
        )

    raw_plays_by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in season_data.plays:
        raw_plays_by_team[play.team].append(play)

    generated_teams: dict[str, dict[str, int | str]] = {}
    generated_season: int | None = None
    for abbreviation, team_name in sorted(team_map.items(), key=lambda item: item[1]):
        stats_path = stats_dir / f"{team_name}.json"
        if not stats_path.exists():
            raise FileNotFoundError(f"Missing normalized stats for {team_name}: {stats_path}")
        team_plays = plays_by_team.get(abbreviation, [])
        raw_team_plays = raw_plays_by_team.get(abbreviation, [])
        if not team_plays:
            raise ValueError(f"No empirical outcomes classified for {abbreviation} ({team_name})")

        stats = TeamSeasonStats.from_json(stats_path)
        generated_season = stats.season if generated_season is None else generated_season
        if stats.season != generated_season:
            raise ValueError("All input statistics must belong to the same season")
        calibrated = calibrate_stats_from_pbp(
            stats,
            team=abbreviation,
            field_goals=season_data.field_goals,
            fumbles=season_data.fumbles,
        )
        defense_profile = adjusted.defense_profiles.get(abbreviation)
        if defense_profile is not None:
            calibrated = calibrate_defense_stats(calibrated, defense_profile)

        generated_plays, fallback_columns = _select_empirical_plays(team_plays)
        empirical = EmpiricalChartData.from_rows(play.to_row() for play in generated_plays)
        generate_team_charts(
            calibrated,
            output / team_name,
            seed=args.seed,
            empirical=empirical,
            missing_source_features=coverage["modeled_missing_features"],
            calibrate_empirical_pass_events=True,
            empirical_pass_calibration=EmpiricalPassCalibration(
                completion_rate_adjustment=profile.pass_completion_adjustment,
                interception_rate_adjustment=profile.pass_interception_adjustment,
                pressure_rate_adjustment=profile.pass_pressure_adjustment,
                resolved_yard_multiplier=profile.pass_yard_multiplier,
            ),
        )
        _copy_team_metadata(template, output, team_name)
        _write_empirical_csv(audit_dir / f"{team_name}.csv", raw_team_plays)
        generated_teams[team_name] = {
            "nflverse_team": abbreviation,
            "empirical_outcomes": len(raw_team_plays),
            "opponent_adjusted_outcomes": len(team_plays),
            "generated_empirical_outcomes": len(generated_plays),
            "fallback_columns": fallback_columns,
            "field_goal_attempts": sum(
                attempt.team == abbreviation for attempt in season_data.field_goals
            ),
            "fumbles": sum(event.team == abbreviation for event in season_data.fumbles),
        }

    if generated_season is None:
        raise ValueError(f"No team statistics found in {stats_dir}")
    _copy_season_metadata(template, output, generated_season)
    manifest = {
        "season": generated_season,
        "seed": args.seed,
        "mode": "opponent-adjusted nflverse play-by-play",
        "calibration_profile": profile.to_dict(),
        "source_feature_coverage": coverage,
        "opponent_adjustment": {
            "model": "league additive offense plus defense effects",
            "pass_event_baseline": "aggregate engine calibration",
            "run_yard_multiplier": profile.run_yard_multiplier,
            "pass_completion_adjustment": profile.pass_completion_adjustment,
            "pass_interception_adjustment": profile.pass_interception_adjustment,
            "pass_pressure_adjustment": profile.pass_pressure_adjustment,
            "pass_yard_multiplier": profile.pass_yard_multiplier,
            "average_defense_effect": 0.0,
            "shrinkage": args.opponent_shrinkage,
        },
        "source": "nflverse regular-season play-by-play",
        "games": season_data.games,
        "source_rows": season_data.source_rows,
        "empirical_outcomes": len(season_data.plays),
        "field_goal_attempts": len(season_data.field_goals),
        "fumbles": len(season_data.fumbles),
        "diagnostics": dict(sorted(season_data.diagnostics.items())),
        "teams": generated_teams,
    }
    (output / "generation-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    chart_audit = audit_season(output)
    (output / "chart-audit.json").write_text(
        json.dumps(chart_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    if not chart_audit["passed"]:
        raise ValueError(f"Generated chart audit failed: {chart_audit['errors']}")
    print(
        f"Generated {len(generated_teams)} teams from {season_data.games} games and "
        f"{len(season_data.plays)} classified outcomes in {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

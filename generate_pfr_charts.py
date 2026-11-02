"""Generate Paydirt charts from archived PFR full play-by-play pages."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path

from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    generate_team_charts,
)
from paydirt.empirical_adjustment import adjust_empirical_offense, calibrate_defense_stats
from paydirt.pfr_play_by_play import (
    EmpiricalPlay,
    FieldGoalAttempt,
    FumbleEvent,
    calibrate_stats_from_pbp,
    classify_pfr_game,
    parse_pfr_boxscore,
)


def _source_date(path: Path) -> int | None:
    """Read a YYYYMMDD date prefix from a PFR boxscore filename."""
    prefix = path.stem[:8]
    return int(prefix) if prefix.isdigit() else None


def _load_team_map(path: Path) -> dict[str, str]:
    """Load and normalize a PFR-abbreviation to local-team-name mapping."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Team map must be a nonempty JSON object")
    return {str(key).upper(): str(value) for key, value in data.items()}


def _classify_directory(
    html_dir: Path,
    through_date: int | None,
    seed: int,
) -> tuple[
    list[EmpiricalPlay],
    list[FieldGoalAttempt],
    list[FumbleEvent],
    Counter[str],
    int,
    int,
]:
    """Parse and classify every selected PFR HTML file in a directory."""
    plays: list[EmpiricalPlay] = []
    field_goals: list[FieldGoalAttempt] = []
    fumbles: list[FumbleEvent] = []
    diagnostics: Counter[str] = Counter()
    games = 0
    source_rows = 0
    for path in sorted(html_dir.glob("*.htm*")):
        source_date = _source_date(path)
        if through_date is not None and source_date is not None and source_date > through_date:
            continue
        game = parse_pfr_boxscore(path.read_text(encoding="utf-8"), path.stem)
        classified = classify_pfr_game(game, seed=seed)
        source_rows += len(game.plays)
        plays.extend(classified.plays)
        field_goals.extend(classified.field_goals)
        fumbles.extend(classified.fumbles)
        diagnostics.update(classified.diagnostics)
        games += 1
    if games == 0:
        raise ValueError(f"No PFR boxscore HTML files found in {html_dir}")
    return plays, field_goals, fumbles, diagnostics, games, source_rows


def _select_empirical_plays(
    plays: Sequence[EmpiricalPlay],
) -> tuple[list[EmpiricalPlay], int]:
    """Keep only columns with enough resolved outcomes for stable quantization."""
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


def _copy_season_metadata(template: Path, output: Path, season: int) -> None:
    """Copy the season rules file required by generated team directories."""
    source = template / f"{season}.yaml"
    if not source.exists():
        raise FileNotFoundError(f"Missing season rules file: {source}")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output / source.name)


def _copy_team_metadata(template: Path, output: Path, team_name: str) -> None:
    """Copy optional roster metadata used by commentary and local simulations."""
    roster = template / team_name / "roster.json"
    if roster.exists():
        shutil.copy2(roster, output / team_name / "roster.json")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PFR play-by-play chart generation command."""
    parser = argparse.ArgumentParser(
        description="Generate team charts from aggregate stats plus archived PFR play-by-play."
    )
    parser.add_argument("--html-dir", required=True, help="Directory of local PFR boxscore HTML")
    parser.add_argument("--stats-dir", required=True, help="Directory of normalized team JSON stats")
    parser.add_argument(
        "--template-season",
        required=True,
        help="Existing season directory supplying season rules and optional rosters",
    )
    parser.add_argument(
        "--team-map",
        required=True,
        help="JSON object mapping PFR team abbreviations to stats filename stems",
    )
    parser.add_argument("--output", required=True, help="Destination season directory")
    parser.add_argument(
        "--audit-dir",
        required=True,
        help="Destination for classified per-team empirical CSV files",
    )
    parser.add_argument(
        "--through-date",
        type=int,
        help="Optional inclusive YYYYMMDD cutoff used to exclude postseason games",
    )
    parser.add_argument("--seed", type=int, default=8306, help="Stable classification seed")
    parser.add_argument(
        "--opponent-shrinkage",
        type=float,
        default=24.0,
        help="Ridge pseudo-count for separating offense and defense effects",
    )
    parser.add_argument(
        "--pass-completion-adjustment",
        type=float,
        default=0.0,
        help="Engine-calibrated change to empirical completion probability",
    )
    parser.add_argument(
        "--pass-interception-adjustment",
        type=float,
        default=0.0,
        help="Engine-calibrated change to empirical interception probability",
    )
    parser.add_argument(
        "--pass-pressure-adjustment",
        type=float,
        default=0.0,
        help="Engine-calibrated change to empirical pressure probability",
    )
    parser.add_argument(
        "--pass-yard-multiplier",
        type=float,
        default=1.0,
        help="Engine-calibrated multiplier for resolved empirical pass yards",
    )
    args = parser.parse_args(argv)

    html_dir = Path(args.html_dir)
    stats_dir = Path(args.stats_dir)
    template = Path(args.template_season)
    output = Path(args.output)
    audit_dir = Path(args.audit_dir)
    team_map = _load_team_map(Path(args.team_map))
    plays, field_goals, fumbles, diagnostics, games, source_rows = _classify_directory(
        html_dir, args.through_date, args.seed
    )

    adjusted = adjust_empirical_offense(plays, shrinkage=args.opponent_shrinkage)
    plays_by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in plays:
        if play.unit != "offense":
            plays_by_team[play.team].append(play)
    for team, team_plays in adjusted.plays_by_team.items():
        plays_by_team[team].extend(team_plays)

    raw_plays_by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in plays:
        raw_plays_by_team[play.team].append(play)

    generated_teams: dict[str, dict[str, int | str]] = {}
    season: int | None = None
    for abbreviation, team_name in sorted(team_map.items(), key=lambda item: item[1]):
        stats_path = stats_dir / f"{team_name}.json"
        if not stats_path.exists():
            raise FileNotFoundError(f"Missing normalized stats for {team_name}: {stats_path}")
        team_plays = plays_by_team.get(abbreviation, [])
        raw_team_plays = raw_plays_by_team.get(abbreviation, [])
        if not team_plays:
            raise ValueError(f"No empirical outcomes classified for {abbreviation} ({team_name})")
        stats = TeamSeasonStats.from_json(stats_path)
        season = stats.season if season is None else season
        if stats.season != season:
            raise ValueError("All input statistics must belong to the same season")
        calibrated = calibrate_stats_from_pbp(
            stats,
            team=abbreviation,
            field_goals=field_goals,
            fumbles=fumbles,
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
            calibrate_empirical_pass_events=True,
            empirical_pass_calibration=EmpiricalPassCalibration(
                completion_rate_adjustment=args.pass_completion_adjustment,
                interception_rate_adjustment=args.pass_interception_adjustment,
                pressure_rate_adjustment=args.pass_pressure_adjustment,
                resolved_yard_multiplier=args.pass_yard_multiplier,
            ),
        )
        _copy_team_metadata(template, output, team_name)
        _write_empirical_csv(audit_dir / f"{team_name}.csv", raw_team_plays)
        generated_teams[team_name] = {
            "pfr_team": abbreviation,
            "empirical_outcomes": len(raw_team_plays),
            "opponent_adjusted_outcomes": len(team_plays),
            "generated_empirical_outcomes": len(generated_plays),
            "fallback_columns": fallback_columns,
            "field_goal_attempts": sum(attempt.team == abbreviation for attempt in field_goals),
            "fumbles": sum(event.team == abbreviation for event in fumbles),
        }

    if season is None:
        raise ValueError(f"No team statistics found in {stats_dir}")
    _copy_season_metadata(template, output, season)
    manifest = {
        "season": season,
        "seed": args.seed,
        "opponent_adjustment": {
            "model": "league additive offense plus defense effects",
            "pass_event_baseline": "aggregate engine calibration",
            "pass_completion_adjustment": args.pass_completion_adjustment,
            "pass_interception_adjustment": args.pass_interception_adjustment,
            "pass_pressure_adjustment": args.pass_pressure_adjustment,
            "pass_yard_multiplier": args.pass_yard_multiplier,
            "average_defense_effect": 0.0,
            "shrinkage": args.opponent_shrinkage,
        },
        "source": "Pro Football Reference full play-by-play archived by the Wayback Machine",
        "games": games,
        "source_rows": source_rows,
        "through_date": args.through_date,
        "empirical_outcomes": len(plays),
        "field_goal_attempts": len(field_goals),
        "fumbles": len(fumbles),
        "diagnostics": dict(sorted(diagnostics.items())),
        "teams": generated_teams,
    }
    (output / "generation-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"Generated {len(generated_teams)} teams from {games} games and "
        f"{len(plays)} classified outcomes in {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

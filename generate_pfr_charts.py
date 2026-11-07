"""Generate Paydirt charts from archived PFR full play-by-play pages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from paydirt.chart_audit import audit_season
from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    generate_team_charts,
    resolve_cohort_pressure,
)
from paydirt.chart_source_coverage import source_feature_coverage
from paydirt.chart_tuning import apply_profile_overrides, load_calibration_profile
from paydirt.empirical_adjustment import (
    adjust_empirical_offense,
    calibrate_defense_stats,
    scale_empirical_run_yards,
)
from paydirt.fumble_source import FUMBLE_GAIN_POLICIES
from paydirt.gain_recipe import prepare_gain_recipe
from paydirt.generated_source_audit import generation_input_hashes
from paydirt.pfr_event_reconciliation import EventReconciliations, load_event_reconciliations
from paydirt.pfr_play_by_play import (
    EmpiricalPlay,
    FieldGoalAttempt,
    FumbleEvent,
    calibrate_stats_from_pbp,
    classify_pfr_game,
    parse_pfr_boxscore,
)
from paydirt.pfr_reconciliation_replay import ReconciliationReplay, reconciliation_input_hashes


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
    ledger_path: Path | None = None,
    event_counts: dict[str, Counter[str]] | None = None,
    event_reconciliations: EventReconciliations | None = None,
    fumble_gain_policy: str | None = None,
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
    ledger = []
    for path in sorted(html_dir.glob("*.htm*")):
        source_date = _source_date(path)
        if through_date is not None and source_date is not None and source_date > through_date:
            continue
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        game = parse_pfr_boxscore(path.read_text(encoding="utf-8"), path.stem)
        facts = event_reconciliations.for_game(game, raw_hash) if event_reconciliations else {}
        classified = classify_pfr_game(game, seed=seed, event_facts=facts,
                                       fumble_gain_policy=fumble_gain_policy)
        if event_counts is not None:
            for team, counts in classified.event_counts.items():
                event_counts.setdefault(team, Counter()).update(counts)
        ledger.append({
            "game_id": path.stem, "raw_filename": path.name,
            "raw_sha256": raw_hash,
            "event_reconciliations": [fact.to_dict() for fact in facts.values()],
            "fumble_events": [asdict(event) for event in classified.fumbles],
            "fumble_gain_projections": [event.to_dict() for event in classified.fumble_gain_projections],
            "fumble_box": game.fumble_box,
            "fumble_reconciliations": list(classified.fumble_reconciliations),
            "unsupported_required_fields": list(classified.unsupported_fields),
            "source_rows": len(game.plays), "field_goal_box": game.field_goal_box,
            "diagnostics": dict(classified.diagnostics),
            "source_conflicts": list(classified.source_conflicts),
            "event_counts": dict(classified.event_counts),
            "representations": [{"play_number": play.play_number, "team": play.team,
                                 "unit": play.unit, "chart": play.chart, "result": play.result}
                                for play in classified.plays],
        })
        source_rows += len(game.plays)
        plays.extend(classified.plays)
        field_goals.extend(classified.field_goals)
        fumbles.extend(classified.fumbles)
        diagnostics.update(classified.diagnostics)
        games += 1
    if games == 0:
        raise ValueError(f"No PFR boxscore HTML files found in {html_dir}")
    if event_reconciliations:
        event_reconciliations.assert_all_applied()
    if ledger_path is not None:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps({
            "classification_seed": seed, "games": ledger,
            "fumble_gain_policy": fumble_gain_policy,
            "interpretation": "Raw source hashes and event-to-chart representations; "
                              "multiple representations may condition one primary event. "
                              "Unobserved primary call families remain heuristic. "
                              "Field-goal conflicts retain unknown underlying mechanisms.",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    arguments = list(argv) if argv is not None else sys.argv[1:]
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
        "--gain-normalization-contract", type=Path,
        help="Source-only calendar/targets: regenerate baseline and derive one fixed gain adjustment",
    )
    parser.add_argument(
        "--fumble-gain-policy", choices=FUMBLE_GAIN_POLICIES,
        help="Explicit experimental separation of reviewed credit and modeled fumble gain",
    )
    parser.add_argument(
        "--event-reconciliations", type=Path,
        help="Reviewed primary-source sack facts with raw-event and evidence byte hashes",
    )
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

    html_dir = Path(args.html_dir)
    stats_dir = Path(args.stats_dir)
    template = Path(args.template_season)
    output = Path(args.output)
    audit_dir = Path(args.audit_dir)
    team_map = _load_team_map(Path(args.team_map))
    source_events: dict[str, Counter[str]] = {}
    reconciliations = (load_event_reconciliations(args.event_reconciliations)
                       if args.event_reconciliations else None)
    plays, field_goals, fumbles, diagnostics, games, source_rows = _classify_directory(
        html_dir, args.through_date, args.seed, audit_dir / "source-ledger.json", source_events,
        reconciliations, fumble_gain_policy=args.fumble_gain_policy,
    )

    if diagnostics.get("unreconciled_fumble_box", 0):
        raise ValueError("Unsupported source fields: inconsistent fumble box; see source-ledger.json")
    if any(event.lost is None for event in fumbles):
        raise ValueError("Unsupported source fields: unknown fumble recovery; see source-ledger.json")
    if diagnostics.get("missing_required_gains", 0):
        raise ValueError("Unsupported source fields: missing required gain; see source-ledger.json")

    coverage = source_feature_coverage(
        (play.to_row() for play in plays),
        field_goal_blocks=sum(attempt.blocked for attempt in field_goals),
    )

    adjusted = adjust_empirical_offense(plays, shrinkage=args.opponent_shrinkage)
    plays_by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in plays:
        if play.unit != "offense":
            plays_by_team[play.team].append(play)
    for team, team_plays in adjusted.plays_by_team.items():
        plays_by_team[team].extend(
            scale_empirical_run_yards(team_plays, profile.run_yard_multiplier)
        )

    raw_plays_by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in plays:
        raw_plays_by_team[play.team].append(play)

    generated_teams: dict[str, dict[str, int | str]] = {}
    prepared_teams = []
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
        prepared_teams.append((abbreviation, team_name, calibrated, empirical,
                               generated_plays, fallback_columns))

    normalization = (prepare_gain_recipe(
        main, arguments, audit_dir=audit_dir, contract_path=args.gain_normalization_contract,
        stats={name: stats for _, name, stats, _, _, _ in prepared_teams}, source_games=games,
    ) if args.gain_normalization_contract else None)
    pass_calibration = EmpiricalPassCalibration(
        completion_rate_adjustment=profile.pass_completion_adjustment,
        interception_rate_adjustment=profile.pass_interception_adjustment,
        pressure_rate_adjustment=profile.pass_pressure_adjustment,
        resolved_yard_multiplier=profile.pass_yard_multiplier,
    )
    neutral_pressure = resolve_cohort_pressure(
        [(stats, empirical) for _, _, stats, empirical, _, _ in prepared_teams],
        seed=args.seed, calibration=pass_calibration,
    )
    for abbreviation, team_name, calibrated, empirical, generated_plays, fallback_columns in prepared_teams:
        team_plays = plays_by_team[abbreviation]
        raw_team_plays = raw_plays_by_team[abbreviation]
        charts = generate_team_charts(
            calibrated,
            output / team_name,
            seed=args.seed,
            empirical=empirical,
            missing_source_features=coverage["modeled_missing_features"],
            calibrate_empirical_pass_events=True,
            empirical_pass_calibration=pass_calibration,
            neutral_pressure=neutral_pressure,
            **({"gain_multipliers": tuple(
                normalization["derivation"]["metrics"][metric]["teams"][team_name]["multiplier"]
                for metric in ("passing", "rushing"))} if normalization else {}),
        )
        _copy_team_metadata(template, output, team_name)
        _write_empirical_csv(audit_dir / f"{team_name}.csv", raw_team_plays)
        generated_teams[team_name] = {
            **({"gain_normalization": charts.gain_normalization} if normalization else {}),
            "primary_layout": charts.primary_layout,
            "empirical_allocation_diagnostics": charts.empirical_allocations,
            "opponent_sampling_diagnostics": adjusted.sampling_diagnostics.get(abbreviation, {}),
            "pfr_team": abbreviation,
            "source_event_counts": {key: source_events.get(abbreviation, {}).get(key, 0)
                                    for key in ("interceptions", "sacks", "field_goal_attempts")},
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
        "neutral_pressure_model": neutral_pressure.evidence,
        "fumble_gain_policy": args.fumble_gain_policy,
        "input_hashes": generation_input_hashes({
            "normalized_stats": sorted(stats_dir.glob("*.json")),
            "play_by_play": [path for path in html_dir.glob("*.htm*")
                             if args.through_date is None or _source_date(path) is None
                             or _source_date(path) <= args.through_date],
            "team_map": [Path(args.team_map)],
            "profile": [args.calibration_profile] if args.calibration_profile else [],
            "normalization_contract": [args.gain_normalization_contract] if args.gain_normalization_contract else [],
        }) | (reconciliation_input_hashes(reconciliations) if reconciliations else {}),
        "season": season,
        "seed": args.seed,
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
        "source": "Pro Football Reference full play-by-play archived by the Wayback Machine",
        "games": games,
        "source_rows": source_rows,
        "classification_ledger": {
            "sha256": hashlib.sha256((audit_dir / "source-ledger.json").read_bytes()).hexdigest(),
            "games": games,
        },
        "event_reconciliations": {
            "schema_version": (None if isinstance(reconciliations, ReconciliationReplay)
                               else reconciliations.schema_version if reconciliations else 1),
            "applied_events": len(reconciliations.facts) if reconciliations else 0,
            "review": "Reviewed source facts; hashes verify identity, not interpretation of scans",
        },
        **({"event_reconciliation_replay": {
            "schema_version": 1, "source_schema_versions": list(reconciliations.source_schema_versions),
            "replay_sha256": hashlib.sha256(reconciliations.replay_path.read_bytes()).hexdigest(),
        }} if isinstance(reconciliations, ReconciliationReplay) else {}),
        "through_date": args.through_date,
        "empirical_outcomes": len(plays),
        "field_goal_attempts": len(field_goals),
        "fumbles": len(fumbles),
        "diagnostics": dict(sorted(diagnostics.items())),
        "teams": generated_teams,
    }
    if normalization is not None:
        if normalization["baseline_input_hashes"] != {
                key: value for key, value in manifest["input_hashes"].items()
                if not key.startswith("normalization_contract/")}:
            raise ValueError("Source inputs changed between baseline and normalized generation")
        manifest["gain_normalization"] = normalization
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
        f"Generated {len(generated_teams)} teams from {games} games and "
        f"{len(plays)} classified outcomes in {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

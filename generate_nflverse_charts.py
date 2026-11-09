"""Generate Paydirt charts from nflverse regular-season play-by-play data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from paydirt.chart_audit import audit_season
from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    _fumble_ranges,
    _write_special,
    generate_team_charts,
    project_shared_return_column,
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
from paydirt.nflverse_fumble_ledger import FumbleLossReview
from paydirt.nflverse_play_by_play import FUMBLE_PROJECTION_MODES, load_nflverse_play_by_play
from paydirt.pfr_play_by_play import EmpiricalPlay, calibrate_stats_from_pbp


def _load_team_map(path: Path) -> dict[str, str]:
    """Load and normalize an nflverse abbreviation to local team-name mapping."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Team map must be a nonempty JSON object")
    return {str(key).upper(): str(value) for key, value in data.items()}


def _load_fumble_reviews(path: Path | None) -> tuple[tuple[FumbleLossReview, ...], list[Path]]:
    """Verify portable evidence bytes/pages before trusting typed review facts."""
    if path is None:
        return (), []
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise TypeError("Fumble review file requires a JSON list")
    reviews, evidence = [], []
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("Invalid typed fumble review record")
        values = dict(record)
        relative = values.pop("evidence_file", None)
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ValueError("Fumble review evidence_file must be relative to its review file")
        pdf = (path.parent / relative).resolve()
        try:
            data = pdf.read_bytes()
            review = FumbleLossReview(**values)
        except (OSError, TypeError) as exc:
            raise ValueError("Invalid fumble review evidence or typed fields") from exc
        if not data.startswith(b"%PDF-") or hashlib.sha256(data).hexdigest() != review.evidence_sha256:
            raise ValueError("Fumble review evidence PDF hash differs")
        page_nodes = re.findall(rb"<<[^<>]*?/Type\s*/Pages\b[^<>]*?>>", data, re.DOTALL)
        counts = [int(value) for node in page_nodes for value in re.findall(rb"/Count\s+(\d+)", node)]
        if type(review.evidence_page) is not int or not counts or not 1 <= review.evidence_page <= max(counts):
            raise ValueError("Fumble review evidence page is outside a verifiable PDF page tree")
        reviews.append(review)
        evidence.append(pdf)
    return tuple(reviews), sorted(set(evidence))


def _load_shared_exposures(
    path: Path, source: Path, teams: set[str], *, expected_games: int,
) -> tuple[dict[str, Fraction], list[Path]]:
    """Require complete, reconciled measurements bound to source/report bytes."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("source_sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError("Measured shared exposure source hash differs")
    relative = data.get("measurement_file")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Measured exposure receipt requires a relative measurement_file")
    measurement = (path.parent / relative).resolve()
    try:
        raw = measurement.read_bytes()
    except OSError as exc:
        raise ValueError("Missing shared exposure measurement") from exc
    if hashlib.sha256(raw).hexdigest() != data.get("measurement_sha256"):
        raise ValueError("Measured shared exposure receipt hash differs")
    receipt = json.loads(raw)
    seasons = receipt.get("source_schedules_completed")
    if (receipt.get("shared_final_retention_pending") != 0 or type(seasons) is not int or seasons <= 0
            or type(expected_games) is not int or expected_games <= 0
            or type(receipt.get("games_completed")) is not int
            or receipt["games_completed"] != seasons * expected_games):
        raise ValueError("Shared exposure measurement is incomplete or retention is pending")
    observed = Counter()
    for key, row in receipt.get("by_team_consumer", {}).items():
        count = row.get("retained_terminal_segments")
        if type(count) is not int or count < 0:
            raise ValueError("Invalid measured nonfoul terminal count")
        observed[key.split(":")[0]] += count
    supplied = data.get("terminal_exposures_by_team")
    if not isinstance(supplied, dict) or set(supplied) != teams or set(observed) != teams:
        raise ValueError("Measured shared exposure teams are incomplete")
    result = {}
    for team, value in supplied.items():
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or abs(value - observed[team] / seasons) > 1e-12):
            raise ValueError("Shared exposure count differs from its measurement")
        result[team] = Fraction(observed[team], seasons)
    return result, [measurement]


def _load_shared_ranges(
    path: Path, teams: set[str],
) -> dict[str, tuple[tuple[int, int], tuple[int, int]]]:
    """Keep the hash-bound measurement's peripheral pairs for this diagnostic."""
    data = json.loads(path.read_text(encoding="utf-8"))
    supplied = data.get("fumble_ranges_by_team")
    if not isinstance(supplied, dict) or set(supplied) != teams:
        raise ValueError("Diagnostic baseline fumble ranges are incomplete")
    receipt = json.loads((path.parent / data["measurement_file"]).read_text(encoding="utf-8"))
    result = {}
    for team, pair in supplied.items():
        if (not isinstance(pair, list) or len(pair) != 2
                or any(not isinstance(part, list) or len(part) != 2
                       or any(type(value) is not int for value in part) for part in pair)):
            raise ValueError("Invalid diagnostic fumble range pair")
        recovered, lost = (pair[0][0], pair[0][1]), (pair[1][0], pair[1][1])
        expected_lost = ((10, 39) if recovered == (0, 0) else (0, 0) if recovered == (10, 39)
                         else (recovered[1] + 1, 39))
        matching = [row.get("current_range") for key, row in receipt.get("by_team_consumer", {}).items()
                    if key.split(":")[0] == team]
        if (not matching or any(value != list(recovered) for value in matching) or lost != expected_lost
                or recovered != (0, 0) and not (recovered[0] == 10 and 10 <= recovered[1] <= 39)):
            raise ValueError("Diagnostic fumble ranges differ from measured baseline")
        result[team] = (recovered, lost)
    return result


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
    fieldnames: tuple[str, ...] = (
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
        writer: csv.DictWriter[str] = csv.DictWriter(destination, fieldnames=fieldnames)
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
    arguments = list(argv) if argv is not None else sys.argv[1:]
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
        "--gain-normalization-contract", type=Path,
        help="Source-only calendar/targets: regenerate baseline and derive one fixed gain adjustment",
    )
    parser.add_argument(
        "--fumble-gain-policy", choices=FUMBLE_GAIN_POLICIES,
        help="Explicit experimental separation of source credit and modeled fumble gain",
    )
    parser.add_argument("--fumble-projection-mode", choices=FUMBLE_PROJECTION_MODES,
                        help="Explicit experimental ordered-ledger source projection")
    parser.add_argument("--fumble-loss-reviews", type=Path,
                        help="Typed hash-bound event losses with relative evidence PDFs")
    parser.add_argument("--shared-return-exposures", type=Path,
                        help="Hash-bound reconciled measured terminal shared exposures")
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
    parser.add_argument(
        "--fumble-range-policy", choices=("measured_diagnostic_v1", "source_primary_v1"),
        help="Ordered projection recovery ranges: measured diagnostic prior (default) or corrected primary source counts",
    )
    args = parser.parse_args(argv)
    if args.fumble_range_policy is not None and not args.fumble_projection_mode:
        raise ValueError("Fumble range policy requires ordered projection mode")
    range_policy = args.fumble_range_policy or "measured_diagnostic_v1"
    if args.fumble_projection_mode and args.shared_return_exposures is None:
        raise ValueError("Ordered generation requires measured shared return exposure input")
    if (args.fumble_loss_reviews or args.shared_return_exposures) and not args.fumble_projection_mode:
        raise ValueError("Review/exposure inputs require an explicit fumble projection mode")
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
    reviews, review_evidence = _load_fumble_reviews(args.fumble_loss_reviews)
    season_data = load_nflverse_play_by_play(args.pbp, seed=args.seed,
                                             fumble_gain_policy=args.fumble_gain_policy,
                                             fumble_projection_mode=args.fumble_projection_mode,
                                             fumble_loss_reviews=reviews)
    exposures, measurement_evidence = (_load_shared_exposures(
        args.shared_return_exposures, Path(args.pbp), set(team_map), expected_games=season_data.games)
        if args.shared_return_exposures else ({}, []))
    frozen_ranges = _load_shared_ranges(args.shared_return_exposures, set(team_map)) if args.shared_return_exposures else {}
    audit_dir.mkdir(parents=True, exist_ok=True)
    gain_ledger = audit_dir / "fumble-gain-projections.json"
    gain_ledger.write_text(json.dumps({
        "schema_version": 1, "policy": args.fumble_gain_policy,
        "interpretation": "Separate modeled gains; null physical facts remain unknown. "
                          "No event-specific official-credit override enters the engine.",
        "events": [event.to_dict() for event in season_data.fumble_gain_projections],
    }, indent=2, sort_keys=True) + "\n")
    unsupported_ledger = audit_dir / "unsupported-source-fields.json"
    unsupported_ledger.write_text(json.dumps(list(season_data.unsupported_fields), indent=2, sort_keys=True) + "\n")
    if season_data.unsupported_fields:
        raise ValueError(f"Unsupported source fields: {len(season_data.unsupported_fields)}; see {unsupported_ledger}")
    joint_ledger = audit_dir / "joint-fumble-projections.json"
    if args.fumble_projection_mode:
        projected_source_ids = {projection.source_event_id for projection in season_data.joint_fumble_projections}
        joint_ledger.write_text(json.dumps({
            "mode": args.fumble_projection_mode, "fit_accepted": False,
            "range_policy": range_policy,
            "projections": [asdict(event) for event in season_data.joint_fumble_projections],
            "shared_fumble_ids": [event.source_event_id for event in season_data.shared_return_fumbles],
            "loss_reviews": [asdict(review) for review in reviews],
            "source_bindings": [{
                "source_event_id": ledger.source_event_id, "raw_play_sha256": ledger.raw_play_sha256,
                "origin": ledger.origin, "statistical_kind": ledger.statistical_kind,
                "statistical_yards": ledger.statistical_yards, "statistical_player_id": ledger.statistical_player_id,
                "events": [asdict(event) for event in ledger.events],
            } for ledger in season_data.fumble_ledgers if ledger.source_event_id in projected_source_ids],
            "physical_initial_truth_verified": False,
        }, indent=2, sort_keys=True) + "\n")

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

    generated_teams: dict[str, dict[str, object]] = {}
    prepared_teams = []
    range_inputs = {}
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
        if args.fumble_projection_mode:
            range_inputs[abbreviation] = {
                "before": {"rushing_F": stats.offense.rushing.fumbles, "rushing_lost": stats.offense.rushing.fumbles_lost,
                           "passing_F": stats.offense.passing.fumbles, "passing_lost": stats.offense.passing.fumbles_lost},
                "after": {"rushing_F": calibrated.offense.rushing.fumbles, "rushing_lost": calibrated.offense.rushing.fumbles_lost,
                          "passing_F": calibrated.offense.passing.fumbles, "passing_lost": calibrated.offense.passing.fumbles_lost},
                "before_range_cells": _fumble_ranges(stats), "after_range_cells": _fumble_ranges(calibrated),
                "punt_snap_origins_separate": sum(e.team == abbreviation and e.unit == "punt_snap" for e in season_data.fumbles),
                "shared_or_combined_loss_refit": False,
                "frozen_diagnostic_range_cells": frozen_ranges[abbreviation],
                "applied_range_cells": (frozen_ranges[abbreviation] if range_policy == "measured_diagnostic_v1"
                                        else _fumble_ranges(calibrated)),
            }
        defense_profile = adjusted.defense_profiles.get(abbreviation)
        if defense_profile is not None:
            calibrated = calibrate_defense_stats(calibrated, defense_profile)

        generated_plays, fallback_columns = _select_empirical_plays(team_plays)
        empirical = EmpiricalChartData.from_rows(play.to_row() for play in generated_plays)
        prepared_teams.append((abbreviation, team_name, calibrated, empirical,
                               generated_plays, fallback_columns))

    normalization = (prepare_gain_recipe(
        main, arguments, audit_dir=audit_dir, contract_path=args.gain_normalization_contract,
        stats={name: stats for _, name, stats, _, _, _ in prepared_teams},
        source_games=season_data.games,
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
    shared_allocations = {}
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
            fallback_run_yard_multiplier=profile.run_yard_multiplier,
            neutral_pressure=neutral_pressure,
            fumble_range_override=(frozen_ranges.get(abbreviation)
                                   if range_policy == "measured_diagnostic_v1" else None),
            **({"gain_multipliers": tuple(
                normalization["derivation"]["metrics"][metric]["teams"][team_name]["multiplier"]
                for metric in ("passing", "rushing"))} if normalization else {}),
        )
        if args.fumble_projection_mode:
            shared = [event for event in season_data.shared_return_fumbles if event.team == abbreviation]
            column, diagnostic = project_shared_return_column(
                interception_outcomes=season_data.interception_return_outcomes.get(abbreviation, {}),
                shared_fumble_outcomes={event.source_event_id: event.chart_result for event in shared},
                shared_fumble_losses={event.source_event_id: event.lost for event in shared},
                terminal_exposures=exposures[abbreviation],
                baseline_column=charts.special_teams["interception_return"],
                seed=args.seed + int.from_bytes(hashlib.sha256(abbreviation.encode()).digest()[:4], "big"),
            )
            charts.special_teams["interception_return"] = column
            _write_special(output / team_name / "special.csv", charts.special_teams, calibrated.special_teams.extra_point)
            shared_allocations[abbreviation] = diagnostic
        _copy_team_metadata(template, output, team_name)
        _write_empirical_csv(audit_dir / f"{team_name}.csv", raw_team_plays)
        generated_teams[team_name] = {
            **({"gain_normalization": charts.gain_normalization} if normalization else {}),
            "primary_layout": charts.primary_layout,
            "empirical_allocation_diagnostics": charts.empirical_allocations,
            "opponent_sampling_diagnostics": adjusted.sampling_diagnostics.get(abbreviation, {}),
            "nflverse_team": abbreviation,
            "source_event_counts": {key: season_data.event_counts.get(abbreviation, {}).get(key, 0)
                                    for key in ("interceptions", "sacks", "field_goal_attempts")},
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
    conversion_ledger = audit_dir / "excluded-conversions.json"
    conversion_ledger.write_text(
        json.dumps(list(season_data.excluded_conversions), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "neutral_pressure_model": neutral_pressure.evidence,
        "fumble_gain_model": {
            "policy": args.fumble_gain_policy,
            "projected_events": len(season_data.fumble_gain_projections),
            "basis_counts": dict(Counter(event.modeled_gain_basis
                                         for event in season_data.fumble_gain_projections)),
            "ledger_sha256": hashlib.sha256(gain_ledger.read_bytes()).hexdigest(),
            "physical_initial_truth_verified": False,
        },
        "ordered_fumble_projection": {
            "mode": args.fumble_projection_mode, "fit_accepted": False,
            "range_policy": range_policy if args.fumble_projection_mode else None,
            "joint_ledger_sha256": hashlib.sha256(joint_ledger.read_bytes()).hexdigest() if args.fumble_projection_mode else None,
            "primary_range_inputs": range_inputs, "shared_allocations": shared_allocations,
        },
        "required_source_fields": {
            "unsupported_count": len(season_data.unsupported_fields),
            "ledger_sha256": hashlib.sha256(unsupported_ledger.read_bytes()).hexdigest(),
        },
        "conversion_population": {
            "structured_flag_rows": season_data.diagnostics.get("structured_two_point_flags", 0),
            "unknown_flag_rows": season_data.diagnostics.get("missing_two_point_flags", 0),
            "not_applicable_flag_rows": season_data.diagnostics.get("not_applicable_two_point_flags", 0),
            "credited_offensive_attempts": season_data.diagnostics.get("excluded_two_point_attempts", 0),
            "excluded_count": len(season_data.excluded_conversions),
            "exclusion_ledger_sha256": hashlib.sha256(conversion_ledger.read_bytes()).hexdigest(),
        },
        "input_hashes": generation_input_hashes({
            "normalized_stats": sorted(stats_dir.glob("*.json")),
            "play_by_play": [Path(args.pbp)],
            "team_map": [Path(args.team_map)],
            "profile": [args.calibration_profile] if args.calibration_profile else [],
            "normalization_contract": [args.gain_normalization_contract] if args.gain_normalization_contract else [],
            "fumble_reviews": [args.fumble_loss_reviews] if args.fumble_loss_reviews else [],
            "fumble_review_evidence": review_evidence,
            "shared_exposures": [args.shared_return_exposures] if args.shared_return_exposures else [],
            "shared_measurement": measurement_evidence,
            "projection_code": [Path(__file__), *(Path(__file__).parent / "paydirt" / name for name in (
                "nflverse_play_by_play.py", "nflverse_fumble_ledger.py", "chart_generator.py", "fumble_source.py"))]
                if args.fumble_projection_mode else [],
        }),
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
        f"Generated {len(generated_teams)} teams from {season_data.games} games and "
        f"{len(season_data.plays)} classified outcomes in {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

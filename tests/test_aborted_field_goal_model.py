"""Synthetic/public regressions for explicitly owned no-kick snap outcomes."""

from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.chart_engine_audit import _decision_count_errors
from paydirt.chart_generator import TeamSeasonStats, generate_team_charts, supported_generated_cell
from paydirt.pfr_event_reconciliation import load_event_reconciliations
from paydirt.pfr_play_by_play import calibrate_stats_from_pbp, classify_pfr_game
from paydirt.play_resolver import (
    DefenseType,
    FieldGoalResult,
    PenaltyOption,
    PlayType,
    ResultType,
    parse_result_string,
)
from tests.game_fixtures import make_sample_game
from tests.test_aborted_field_goal_source import game as source_game
from tests.test_aborted_field_goal_source import sidecar


def resolved(cell: str, foul: str = "", offsetting: bool = False) -> FieldGoalResult:
    """Return a selected synthetic cell without consuming recovery dice."""
    penalties = [PenaltyOption(foul, f"{foul} 5", 5, "Synthetic foul")] if foul else []
    return FieldGoalResult(12, "synthetic selected roll", cell, 0,
                           penalty_options=penalties, offsetting=offsetting,
                           offended_team="defense" if foul == "OFF" else "offense")


@pytest.mark.parametrize("ownership", ["KEEP", "LOST"])
def test_selected_snap_has_explicit_owner_and_narrow_column_grammar(ownership: str) -> None:
    cell = f"F SNAP {ownership} 0"
    result = parse_result_string(cell)
    assert result.result_type == ResultType.FUMBLE
    assert getattr(result, "field_goal_snap_fumble", False)
    assert result.fumble_recovered is (ownership == "KEEP")
    assert result.yards == 0
    assert supported_generated_cell("special_teams", "field_goal", cell)
    for unit, column in [("offense", "line_plunge"), ("offense", "short_pass"),
                         ("special_teams", "punt"), ("special_teams", "kickoff_return")]:
        assert not supported_generated_cell(unit, column, cell)


@pytest.mark.parametrize("cell", ["F SNAP KEEP ?", "F SNAP MAYBE 0", "F SNAP KEEP -1"])
def test_snap_cannot_silently_invent_unknown_or_unsupported_gain(cell: str) -> None:
    assert not supported_generated_cell("special_teams", "field_goal", cell)
    with pytest.raises(ValueError, match="snap"):
        parse_result_string(cell)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("ownership", ["KEEP", "LOST"])
@pytest.mark.parametrize("position", [1, 50, 99])
@pytest.mark.parametrize("down", [2, 4])
def test_snap_ownership_downs_and_observer_without_kick_or_recovery_roll(
    home: bool, ownership: str, position: int, down: int,
) -> None:
    engine = make_sample_game()
    engine.state.is_home_possession = home
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = position, down, 1
    team = engine.state.possession_team.peripheral.short_name
    stats = engine.state.offense_stats
    observer = EngineCalibrationObserver()
    observer.on_decision(engine, None, PlayType.FIELD_GOAL, DefenseType.STANDARD)
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties",
               return_value=resolved(f"F SNAP {ownership} 0")), \
            patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("extra roll")):
        outcome = engine.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    observer.on_result(engine, outcome)
    changed = ownership == "LOST" or down == 4
    assert engine.state.is_home_possession is (home != changed)
    assert engine.state.ball_position == (100 - position if changed else position)
    assert engine.state.down == (1 if changed else 3)
    assert outcome.turnover is changed
    assert outcome.turnover_on_downs is (ownership == "KEEP" and down == 4)
    assert stats.fumbles_lost == int(ownership == "LOST")
    assert stats.total_yards == stats.rushing_yards == stats.passing_yards == stats.sacks == 0
    assert not outcome.field_goal_made and not outcome.touchdown and not outcome.safety
    assert getattr(outcome.result, "field_goal_snap_fumble", False)
    assert not outcome.result.fumble_recovery_roll and not outcome.result.fumble_return_dice
    assert len(engine.play_log) == 1
    totals = observer.team_totals(team)
    assert (totals.offensive_plays, totals.rushing_attempts, totals.field_goal_attempts,
            totals.field_goals_made, totals.pass_attempts, totals.sacks) == (1, 1, 0, 0, 0, 0)


@pytest.mark.parametrize("ownership", ["KEEP", "LOST"])
@pytest.mark.parametrize("foul", ["OFF", "DEF"])
@pytest.mark.parametrize("accept_play", [False, True])
def test_pending_snap_foul_defers_then_keeps_or_erases_occurrence(
    ownership: str, foul: str, accept_play: bool,
) -> None:
    engine = make_sample_game()
    engine.state.is_home_possession = True
    engine.state.ball_position, engine.state.down = 50, 2
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties",
               return_value=resolved(f"F SNAP {ownership} 0", foul)), \
            patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("extra roll")):
        pending = engine.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
        assert pending.pending_penalty_decision
        assert engine.state.is_home_possession and engine.state.ball_position == 50
        assert not engine.play_log and not engine.state.home_stats.fumbles_lost
        outcome = engine.apply_fg_penalty_decision(pending, accept_play)
    assert not outcome.pending_penalty_decision and len(engine.play_log) == 1
    assert not outcome.field_goal_made
    assert engine.state.home_stats.fumbles_lost == int(accept_play and ownership == "LOST")
    if accept_play:
        assert getattr(outcome.result, "field_goal_snap_fumble", False)
        assert engine.state.is_home_possession is (ownership == "KEEP")
    else:
        assert outcome.penalty_applied and not outcome.turnover
        assert not getattr(outcome.result, "field_goal_snap_fumble", False)
        assert engine.state.is_home_possession and engine.state.down == 2


@pytest.mark.parametrize("cell", ["25", "BK -8", "F - 5"])
def test_legacy_field_goal_cells_keep_existing_classification(cell: str) -> None:
    result = parse_result_string(cell)
    assert not getattr(result, "field_goal_snap_fumble", False)
    assert supported_generated_cell("special_teams", "field_goal", cell)


@pytest.mark.parametrize("lost", [False, True])
def test_reviewed_credit_zero_projects_owned_nonattempt_and_conditional_generator_mass(
    tmp_path: Path, lost: bool,
) -> None:
    path, record = sidecar(tmp_path, individual_lost=lost,
                           recovering_team="OWL" if lost else "FOX")
    inventory = load_event_reconciliations(path)
    facts = inventory.for_game(source_game(), record["raw_game_sha256"])
    result = classify_pfr_game(source_game(), event_facts=facts,
                               fumble_gain_policy="credited_fumble_proxy_v1")
    assert not result.unsupported_fields and not result.source_conflicts
    projection, = result.fumble_gain_projections
    assert projection.modeled_gain_basis == "credited_proxy"
    assert projection.modeled_initial_yards == 0
    assert projection.source_facts.physical_initial_yards is None
    assert projection.chart_result == f"F SNAP {'LOST' if lost else 'KEEP'} 0"
    assert len(result.field_goals) == 1 and result.event_counts["FOX"]["field_goal_attempts"] == 1
    stats = TeamSeasonStats.from_dict({"season": 2026, "team_name": "Foxes", "short_name": "FOX"})
    calibrated = calibrate_stats_from_pbp(stats, "FOX", result.field_goals, result.fumbles)
    assert getattr(calibrated.special_teams, "field_goal_snap_outcomes", ()) == (projection.chart_result,)
    charts = generate_team_charts(calibrated, tmp_path / "charts", seed=7)
    cells = charts.special_teams["field_goal"]
    assert projection.chart_result in cells.values()
    assert any(cell.lstrip("-").isdigit() for cell in cells.values())
    assert "F - 7" not in cells.values()


@pytest.mark.parametrize("policy,changes", [
    ("known_physical_v1", {"individual_lost": False}),
    ("credited_fumble_proxy_v1", {"individual_lost": False, "credited_player_id": None,
                                  "credited_rushing_yards": None}),
    ("credited_fumble_proxy_v1", {"individual_lost": None}),
])
def test_missing_credit_recovery_or_physical_fact_stays_unsupported(
    tmp_path: Path, policy: str, changes: dict,
) -> None:
    path, record = sidecar(tmp_path, **changes)
    facts = load_event_reconciliations(path).for_game(source_game(), record["raw_game_sha256"])
    result = classify_pfr_game(source_game(), event_facts=facts, fumble_gain_policy=policy)
    assert result.unsupported_fields and not result.fumble_gain_projections
    assert len(result.field_goals) == 1


@pytest.mark.parametrize("snap", [False, True])
def test_independent_decision_receipt_distinguishes_kick_from_snap(snap: bool) -> None:
    fields = ("offensive_plays", "rushing_attempts", "pass_attempts", "completions",
              "sacks", "field_goal_attempts", "field_goals_made")
    totals = dict.fromkeys(fields, 0)
    totals.update(offensive_plays=int(snap), rushing_attempts=int(snap),
                  field_goal_attempts=int(not snap))
    receipt = {"teams": {"FOX": totals}, "decision_results": [{
        "situation": ["FOX", "FIELD_GOAL"], "retained": True,
        "result": "FUMBLE" if snap else "YARDS", "initial_yards": 0,
        "qb_time": False, "punt_snap_fumble": False, "field_goal_snap_fumble": snap,
        "field_goal_made": False,
    }]}
    assert not _decision_count_errors(receipt)


@pytest.mark.parametrize("ownership", ["KEEP", "LOST"])
def test_offsetting_fouls_erase_snap_without_consuming_a_down(ownership: str) -> None:
    engine = make_sample_game()
    engine.state.is_home_possession = True
    engine.state.ball_position, engine.state.down = 50, 2
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties",
               return_value=resolved(f"F SNAP {ownership} 0", offsetting=True)):
        outcome = engine.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert engine.state.is_home_possession and engine.state.ball_position == 50
    assert engine.state.down == 2 and not engine.state.home_stats.turnovers
    assert not getattr(outcome.result, "field_goal_snap_fumble", False)
    assert outcome.result.replay_down and not outcome.turnover and not outcome.field_goal_made

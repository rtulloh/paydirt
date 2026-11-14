"""FLOW-023: decide own-end-zone interception returns after the catch.

The catch location, score and clock must be known before the choice, and no
return dice may be rolled until the decision is resolved. These tests use only
the public sample teams under ``seasons/2026`` with explicit synthetic cells.
"""
import json
import random
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.interception_policy import should_attempt_end_zone_return
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PlayResult,
    PlayType,
    ResultType,
)
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game

OWN_GOAL_LINE = 100
ONE_YARD_DEEP = 101
FOUR_YARDS_DEEP = 104
MAX_RECORDED_DEPTH = 109
PAST_END_LINE = 112


def interception_result(raw_spot: int) -> PlayResult:
    """Build a synthetic interception caught at ``raw_spot`` (offense perspective)."""
    return PlayResult(
        result_type=ResultType.INTERCEPTION,
        yards=raw_spot - 90,
        turnover=True,
        raw_result=f"INT {raw_spot - 90}",
        dice_roll=10,
    )


def throw_interception(game: PaydirtGameEngine, result: PlayResult):
    """Run a scrimmage pass that the patched resolver turns into an interception."""
    choice = PenaltyChoice(play_result=result)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        return game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD
        )


def decision_game(offense_home: bool = True, raw_spot: int = FOUR_YARDS_DEEP):
    """Sample game at the offense's own 10 with the intercepting team asking."""
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    game.state.ball_position = 90
    defense_home = not offense_home
    game.set_end_zone_interception_policy(defense_home, "ask")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    return game, interception_result(raw_spot)


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize(
    "raw_spot,depth",
    [
        (OWN_GOAL_LINE, 0),
        (ONE_YARD_DEEP, 1),
        (FOUR_YARDS_DEEP, 4),
        (MAX_RECORDED_DEPTH, 9),
        (PAST_END_LINE, 9),
    ],
)
def test_ask_defers_choice_until_catch_depth_is_known(
    offense_home: bool, raw_spot: int, depth: int
) -> None:
    game, result = decision_game(offense_home, raw_spot)
    before = (
        game.state.ball_position,
        game.state.is_home_possession,
        game.state.down,
        game.state.home_score,
        game.state.away_score,
    )
    with patch(
        "paydirt.game_engine.roll_chart_dice",
        side_effect=AssertionError("return dice rolled before the decision"),
    ) as dice:
        outcome = throw_interception(game, result)
    dice.assert_not_called()
    assert outcome.pending_end_zone_interception_return_decision is True
    assert outcome.int_catch_depth == depth
    assert outcome.turnover is False
    assert outcome.touchdown is False
    assert "end zone" in outcome.description.lower()
    # The catch depth is engine-provided, so the offense-derived LOS is untouched.
    assert before == (
        game.state.ball_position,
        game.state.is_home_possession,
        game.state.down,
        game.state.home_score,
        game.state.away_score,
    )
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0


@pytest.mark.parametrize("offense_home", [True, False])
def test_touchback_resolution_records_turnover_once_without_dice(offense_home: bool) -> None:
    game, result = decision_game(offense_home)
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        pending = throw_interception(game, result)
        dice.assert_not_called()
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=False
        )
    dice.assert_not_called()
    assert final.pending_end_zone_interception_return_decision is False
    assert final.turnover is True
    assert game.state.ball_position == 20
    assert game.state.is_home_possession is not offense_home
    assert game.state.away_stats.interceptions_thrown + game.state.home_stats.interceptions_thrown == 1
    with pytest.raises(ValueError):
        game.apply_end_zone_interception_return_decision(pending, attempt_return=False)


@pytest.mark.parametrize("offense_home", [True, False])
def test_return_resolution_rolls_once_and_matches_predeclared_policy(offense_home: bool) -> None:
    game, result = decision_game(offense_home)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice:
        pending = throw_interception(game, result)
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    dice.assert_called_once()
    assert final.turnover is True
    assert game.state.ball_position == 11
    assert result.int_spot == -4
    assert result.int_return_yards == 15
    assert final.description == result.description


def test_field_interception_is_unaffected_by_ask_policy() -> None:
    game, _ = decision_game(raw_spot=95)
    result = interception_result(95)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")) as dice:
        outcome = throw_interception(game, result)
    dice.assert_called_once()
    assert outcome.pending_end_zone_interception_return_decision is False


def test_explicit_touchback_policy_never_asks() -> None:
    game, result = decision_game()
    game.set_end_zone_interception_policy(False, "touchback")
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        outcome = throw_interception(game, result)
    dice.assert_not_called()
    assert outcome.pending_end_zone_interception_return_decision is False
    assert game.state.ball_position == 20


@pytest.mark.parametrize(
    "depth,differential,quarter,minutes,expected",
    [
        (0, 0, 4, 1.5, True),    # goal-line catch, tie game, late
        (0, 14, 4, 1.0, False),  # protect a two-score lead
        (1, -3, 4, 1.0, True),   # trailing, shallow catch
        (1, 14, 4, 1.0, False),  # leading, shallow catch still protects
        (3, -7, 3, 5.0, True),   # trailing by a score
        (3, 0, 1, 10.0, False),  # neutral early situation
        (6, -7, 4, 2.0, False),  # too deep to escape reliably
        (9, -7, 4, 0.5, False),
    ],
)
def test_cpu_policy_uses_depth_score_and_clock(
    depth: int, differential: int, quarter: int, minutes: float, expected: bool
) -> None:
    assert should_attempt_end_zone_return(
        catch_depth=depth,
        score_differential=differential,
        quarter=quarter,
        time_remaining=minutes,
    ) is expected


@pytest.mark.parametrize("depth,leading,should_roll", [
    (9, False, False),  # deep catch -> automatic touchback
    (0, False, True),   # goal-line catch trailing late -> return
    (1, True, False),   # shallow but protecting a lead -> touchback
])
def test_auto_policy_resolves_without_a_pending_decision(
    depth: int, leading: bool, should_roll: bool
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 90
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    if leading:  # away defense leads by 14
        game.state.away_score = 24
        game.state.home_score = 10
    else:  # home offense leads, away defense trails
        game.state.home_score = 24
        game.state.away_score = 10
    game.set_end_zone_interception_policy(False, "auto")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    result = interception_result(100 + depth)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")) as dice:
        outcome = throw_interception(game, result)
    assert outcome.pending_end_zone_interception_return_decision is False
    if should_roll:
        dice.assert_called_once()
        assert game.state.ball_position == 15
    else:
        dice.assert_not_called()
        assert game.state.ball_position == 20


def test_pending_decision_survives_save_and_load_with_random_state(tmp_path: Path) -> None:
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        pending = throw_interception(game, result)
    save_path = tmp_path / "pending-int.json"
    save_game(game, str(save_path))
    saved = json.loads(save_path.read_text())
    assert saved["pending_end_zone_interception"]["catch_depth"] == 4
    deferred_state = game._pending_end_zone_interception["random_state"]
    return_chart = dict(game.state.defense_team.special_teams.interception_return)

    # Resolving the live engine advances the global dice RNG after the save.
    live = game.apply_end_zone_interception_return_decision(
        pending, attempt_return=True
    )
    loaded = load_game(str(save_path))[0]
    assert loaded.has_pending_end_zone_interception is True
    assert random.getstate() == deferred_state
    loaded.state.defense_team.special_teams.interception_return = return_chart
    replay_pending = loaded._last_play_outcome
    replay = loaded.apply_end_zone_interception_return_decision(
        replay_pending, attempt_return=True
    )
    assert replay.result.int_return_dice == live.result.int_return_dice
    assert loaded.state.ball_position == game.state.ball_position
    assert loaded.state.is_home_possession == game.state.is_home_possession
    assert loaded.home_end_zone_interception_policy == game.home_end_zone_interception_policy
    assert loaded.away_end_zone_interception_policy == game.away_end_zone_interception_policy


def test_return_resolution_reports_yardage_and_spot_in_description() -> None:
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        pending = throw_interception(game, result)
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    assert "Return" in final.description
    assert "11" in final.description
    assert final.description.count("Return:") == 1


def test_return_touchdown_description_is_explicit() -> None:
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    game.state.defense_team.special_teams.interception_return = {26: "TD"}
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "TD")):
        pending = throw_interception(game, result)
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    assert final.touchdown is True
    assert "TOUCHDOWN" in final.description.upper()
    assert final.description.count("TOUCHDOWN") == 1


def test_pending_decision_preserves_requested_spike_until_resolution() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 90
    game.state.quarter = 4
    game.state.time_remaining = 0.5
    game.set_end_zone_interception_policy(False, "ask")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    result = interception_result(FOUR_YARDS_DEEP)
    choice = PenaltyChoice(play_result=result)
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15"))):
        pending = game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD, call_spike=True
        )
        assert pending.pending_end_zone_interception_return_decision is True
        assert pending.spike_used is False
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    assert final.result.int_return_dice == 26
    assert game.state.ball_position == 11


def test_pending_choice_blocks_a_new_snap_until_it_is_resolved() -> None:
    """FLOW-026: a snap cannot run while the return choice is unresolved."""
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        pending = throw_interception(game, result)
    assert pending.pending_end_zone_interception_return_decision is True
    state_before = deepcopy(game.state)
    with pytest.raises(ValueError, match="end-zone interception"):
        game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    with pytest.raises(ValueError, match="end-zone interception"):
        game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state == state_before
    assert not game.play_log
    assert game.has_pending_end_zone_interception
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        final = game.apply_end_zone_interception_return_decision(pending, attempt_return=False)
    assert not game.has_pending_end_zone_interception
    assert final.turnover is True
    assert game.state.ball_position == 20
    # The guard only covers the unresolved choice.
    game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)


@pytest.mark.parametrize(
    "action",
    [
        lambda game, pending: game.kickoff(),
        lambda game, pending: game.onside_kick(),
        lambda game, pending: game.safety_free_kick(),
        lambda game, pending: game.attempt_extra_point(),
        lambda game, pending: game.apply_defensive_timeout(
            pending,
            time_before_play=1.0,
            quarter_before_play=4,
            offense_was_home=True,
            two_minute_warning_before=True,
        ),
        lambda game, pending: game.apply_penalty_decision(
            pending, accept_play=True
        ),
        lambda game, pending: game.apply_punt_penalty_decision(
            pending, accept_penalty=True
        ),
        lambda game, pending: game.apply_kickoff_penalty_decision(
            pending, accept_penalty=True
        ),
        lambda game, pending: game.apply_fg_penalty_decision(
            pending, accept_play=True
        ),
        lambda game, pending: game.start_overtime(
            coin_toss_winner_is_home=True
        ),
    ],
    ids=[
        "kickoff",
        "onside-kick",
        "safety-free-kick",
        "extra-point",
        "defensive-timeout",
        "scrimmage-penalty",
        "punt-penalty",
        "kickoff-penalty",
        "field-goal-penalty",
        "overtime-start",
    ],
)
def test_pending_choice_blocks_other_game_changing_entry_points(action) -> None:
    """FLOW-026: every public game-changing action honors the pending choice."""
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(7, "10")):
        pending = throw_interception(game, result)
    assert pending.pending_end_zone_interception_return_decision is True
    state_before = deepcopy(game.state)
    log_before = list(game.play_log)
    history_before = list(game.offensive_call_history)
    start_quarter_before = game._last_play_start_quarter
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(7, "10")):
        with pytest.raises(ValueError, match="end-zone interception"):
            action(game, pending)
    assert game.state == state_before
    assert game.play_log == log_before
    assert game.offensive_call_history == history_before
    assert game._last_play_start_quarter == start_quarter_before
    assert game.has_pending_end_zone_interception


def test_pending_choice_blocks_two_point_before_conversion_setup() -> None:
    """FLOW-026: a try cannot enter its isolated conversion setup."""
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(7, "10")):
        pending = throw_interception(game, result)
    assert pending.pending_end_zone_interception_return_decision is True
    state_before = deepcopy(game.state)
    with patch.object(
        game,
        "get_two_point_situation",
        side_effect=AssertionError("two-point conversion setup started"),
    ):
        with pytest.raises(ValueError, match="end-zone interception"):
            game.attempt_two_point(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state == state_before
    assert game.has_pending_end_zone_interception

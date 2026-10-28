"""The S modifier pays a down after a finalized, eligible scrimmage play."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[False, True], ids=["away", "home"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 50
    engine.state.quarter = 4
    engine.state.time_remaining = 1
    engine.state.home_score, engine.state.away_score = 14, 7
    engine.state.two_minute_warning_called = True
    return engine


def play(game: PaydirtGameEngine, result: PlayResult, **kwargs: bool) -> PlayOutcome:
    with (
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)) as resolve,
        patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("spike rerolled a chart")),
        patch("paydirt.game_engine.random.uniform", return_value=40),
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True, **kwargs,
        )
    resolve.assert_called_once()
    return outcome


@pytest.mark.parametrize("yards,distance", [(4, 10), (10, 10), (15, 10), (2, 2)])
def test_first_down_completion_plus_spike_leaves_third_even_after_first_down_gain(
    game: PaydirtGameEngine, yards: int, distance: int,
) -> None:
    game.state.yards_to_go = distance
    home = game.state.is_home_possession
    outcome = play(game, PlayResult(ResultType.YARDS, yards=yards))
    assert outcome.spike_used
    assert game.state.down == outcome.down_after == 3
    assert game.state.is_home_possession is home
    assert game.state.ball_position == 50 + yards
    assert game.state.yards_to_go == (10 if yards >= distance else distance - yards)
    assert outcome.first_down is (yards >= distance)
    assert game.state.time_remaining == pytest.approx(1 - .333)
    assert outcome.transaction.final_down == 3
    assert outcome.transaction.final_ball_position == game.state.ball_position
    assert outcome.transaction.final_yards_to_go == game.state.yards_to_go
    assert outcome.transaction.possession_team == game.state.possession_team.peripheral.short_name
    assert "spike" in outcome.description.lower()
    assert len(game.play_log) == len(game.offensive_call_history) == 1
    assert game.state.offense_stats.first_downs == int(yards >= distance)


@pytest.mark.parametrize("down,expected_down,changes_possession", [(2, 4, False), (3, 1, True)])
def test_additional_down_can_turn_ball_over_without_fabricating_yardage(
    game: PaydirtGameEngine, down: int, expected_down: int, changes_possession: bool,
) -> None:
    game.state.down = down
    home = game.state.is_home_possession
    outcome = play(game, PlayResult(ResultType.YARDS, yards=4))
    assert outcome.spike_used
    assert game.state.down == outcome.down_after == expected_down
    assert game.state.is_home_possession is (not home if changes_possession else home)
    assert outcome.turnover_on_downs is changes_possession
    assert game.state.ball_position == (46 if changes_possession else 54)
    assert outcome.field_position_after == game.state.field_position_str()
    assert outcome.transaction.final_down == expected_down
    assert outcome.transaction.final_ball_position == game.state.ball_position
    assert outcome.transaction.possession_team == game.state.possession_team.peripheral.short_name
    assert outcome.yards_gained == 4
    assert len(game.play_log) == len(game.offensive_call_history) == 1


@pytest.mark.parametrize("case", ["incomplete", "oob", "designated-oob", "touchdown", "safety", "failed-fourth", "timeout"])
def test_ineligible_or_superseded_spike_does_not_charge_extra_down(game: PaydirtGameEngine, case: str) -> None:
    kwargs = {}
    result = PlayResult(ResultType.YARDS, yards=4)
    expected_down = 2
    if case == "incomplete":
        result = PlayResult(ResultType.INCOMPLETE)
    elif case == "oob":
        result.out_of_bounds = True
    elif case == "designated-oob":
        kwargs["out_of_bounds_designation"] = True
    elif case == "touchdown":
        result = PlayResult(ResultType.TOUCHDOWN, touchdown=True)
        expected_down = 1
    elif case == "safety":
        game.state.ball_position = 2
        result.yards = -3
        expected_down = 1
    elif case == "failed-fourth":
        game.state.down = 4
        expected_down = 1
    elif case == "timeout":
        kwargs["call_timeout"] = True
    outcome = play(game, result, **kwargs)
    assert not outcome.spike_used
    assert game.state.down == outcome.down_after == expected_down
    assert len(game.play_log) == 1


@pytest.mark.parametrize("kind", ["OFF", "DEF"])
@pytest.mark.parametrize("accept_play", [False, True])
@pytest.mark.parametrize("yards", [4, 12])
def test_spike_waits_for_penalty_decision_and_only_charges_retained_play(
    game: PaydirtGameEngine, kind: str, accept_play: bool, yards: int,
) -> None:
    home = game.state.is_home_possession
    choice = PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=yards, offense_yards=yards, defense_modifier=f"{kind} 5"),
        penalty_options=[PenaltyOption(kind, f"{kind} 5", 5, "synthetic foul")],
        offended_team="defense" if kind == "OFF" else "offense",
    )
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True)
    assert pending.pending_penalty_decision
    assert not pending.spike_used
    assert game.state.down == 1
    assert game.state.time_remaining == 1
    assert not game.play_log
    with patch("paydirt.game_engine.random.uniform", return_value=40):
        outcome = game.apply_penalty_decision(pending, accept_play)
    assert outcome.spike_used is accept_play
    assert game.state.down == outcome.down_after == (3 if accept_play else 1)
    assert game.state.is_home_possession is home
    assert game.state.time_remaining == pytest.approx(1 - (.333 if accept_play else 40 / 60))
    assert len(game.play_log) == len(game.offensive_call_history) == 1
    assert game.apply_penalty_decision(outcome, accept_play) is outcome
    assert game.state.down == outcome.down_after


def test_declined_foul_incompletion_needs_no_spike(game: PaydirtGameEngine) -> None:
    choice = PenaltyChoice(
        PlayResult(ResultType.INCOMPLETE),
        penalty_options=[PenaltyOption("OFF", "OFF 5", 5, "synthetic foul")],
        offended_team="defense",
    )
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True)
    with patch("paydirt.game_engine.random.uniform", return_value=40):
        outcome = game.apply_penalty_decision(pending, True)
    assert not outcome.spike_used
    assert game.state.down == outcome.down_after == 2


def test_offsetting_fouls_do_not_apply_spike(game: PaydirtGameEngine) -> None:
    choice = PenaltyChoice(PlayResult(ResultType.YARDS, yards=12), offsetting=True)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True)
    assert not outcome.spike_used
    assert game.state.down == 1
    assert game.state.time_remaining == pytest.approx(50 / 60)

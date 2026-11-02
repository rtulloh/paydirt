"""RULE-022 uses the supplied rulebook's action time, without dead time."""

from unittest.mock import Mock

import pytest

from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("accept_play", [False, True])
@pytest.mark.parametrize("kind,yards,seconds", [
    (ResultType.YARDS, 9, 5), (ResultType.YARDS, 26, 7),
    (ResultType.YARDS, -13, 6), (ResultType.INCOMPLETE, 0, 5),
    (ResultType.SACK, -12, 6), (ResultType.FUMBLE, 2, 7),
])
def test_flagged_action_uses_live_yardage_not_enforcement(
    monkeypatch, accept_play: bool, kind: ResultType, yards: int, seconds: int,
) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, 85 / 60
    game.state.ball_position = 35
    result = PlayResult(kind, yards=yards, fumble_resolved=True, fumble_recovered=True)
    choice = PenaltyChoice(result, penalty_options=[PenaltyOption("DEF", "DEF 15", 15, "Foul")])
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    timing = Mock(return_value=44)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)
    outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    game.apply_penalty_decision(outcome, accept_play=accept_play)
    assert game.state.time_remaining * 60 == pytest.approx(85 - seconds)
    timing.assert_not_called()


@pytest.mark.parametrize("oob", [False, True])
def test_flagged_completion_action_time_wins_over_sideline_timing(monkeypatch, oob: bool) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, 85 / 60
    result = PlayResult(ResultType.YARDS, yards=9, out_of_bounds=oob)
    choice = PenaltyChoice(result, penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Foul")])
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    game.apply_penalty_decision(outcome, accept_play=True)
    assert game.state.time_remaining * 60 == pytest.approx(80)


@pytest.mark.parametrize("kind,yards,return_yards,expected", [
    (ResultType.INTERCEPTION, 26, 18, 11),
    (ResultType.FUMBLE, 2, 18, 11),
])
def test_retained_turnover_includes_the_actual_return(
    kind: ResultType, yards: int, return_yards: int, expected: int,
) -> None:
    game = make_sample_game()
    result = PlayResult(kind, yards=yards, int_return_yards=return_yards,
                        int_return_dice=20, fumble_return_yards=return_yards, fumble_return_dice=20)
    assert game._flagged_scrimmage_seconds(PlayType.SHORT_PASS, result, 35, retained=True) == expected

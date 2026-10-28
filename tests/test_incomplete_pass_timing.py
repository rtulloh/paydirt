"""AI-007: agreed five-second incompletions, without running-clock dead time."""

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


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter,seconds", [(1, 600), (2, 28), (3, 600), (4, 120), (4, 28), (5, 28)])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined", "hail-mary"])
def test_incompletion_uses_five_seconds(
    monkeypatch: pytest.MonkeyPatch, home: bool, quarter: int, seconds: int, flow: str,
) -> None:
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home
    state.quarter, state.time_remaining = quarter, seconds / 60
    state.is_overtime = quarter == 5
    state.ot_period = int(quarter == 5)
    state.home_score, state.away_score = 14, 7
    state.ball_position, state.down, state.yards_to_go = 50, 1, 10
    state.two_minute_warning_called = seconds <= 120
    result = PlayResult(ResultType.INCOMPLETE, description="Incomplete pass")
    choice = PenaltyChoice(result)
    if flow == "declined":
        choice = PenaltyChoice(result, penalty_options=[
            PenaltyOption("OFF", "OFF 5", 5, "Synthetic foul")], offended_team="defense")
    timing = Mock(return_value=40)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    monkeypatch.setattr("paydirt.game_engine.resolve_hail_mary", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (30, "Synthetic roll"))
    if flow == "direct":
        outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    else:
        play = PlayType.HAIL_MARY if flow == "hail-mary" else PlayType.MEDIUM_PASS
        outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
        if flow == "declined":
            assert outcome.pending_penalty_decision
            assert state.time_remaining == seconds / 60
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
    assert state.time_remaining * 60 == pytest.approx(seconds - 5)
    assert state.quarter == quarter
    assert state.down == 2
    assert state.ball_position == 50
    assert state.is_home_possession is home
    assert not state.game_over
    assert not outcome.timeout_used and not outcome.spike_used
    assert state.home_timeouts == state.away_timeouts == 3
    assert len(game.play_log) == 1
    timing.assert_not_called()


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("options", [
    {}, {"no_huddle": True}, {"out_of_bounds_designation": True},
    {"in_bounds_designation": True}, {"call_timeout": True}, {"call_spike": True},
    {"call_defensive_timeout": True},
    {"call_timeout": True, "call_spike": True, "call_defensive_timeout": True},
])
def test_modifiers_cannot_lengthen_or_shorten_incompletion(
    monkeypatch: pytest.MonkeyPatch, direct: bool, options: dict,
) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, 28 / 60
    game.state.two_minute_warning_called = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 50, 1, 10
    result = PlayResult(ResultType.INCOMPLETE, out_of_bounds=True)
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(result))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 40)
    if direct:
        options = {key: value for key, value in options.items() if not key.startswith("call_")}
    run = game.run_play if direct else game.run_play_with_penalty_procedure
    outcome = run(PlayType.MEDIUM_PASS, DefenseType.STANDARD, **options)
    assert game.state.time_remaining * 60 == pytest.approx(23)
    assert game.state.down == 2
    assert game.state.ball_position == 50
    assert not outcome.spike_used and not outcome.timeout_used
    assert game.state.home_timeouts == game.state.away_timeouts == 3


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("seconds", [4, 5, 6])
def test_incompletion_period_boundary(
    monkeypatch: pytest.MonkeyPatch, quarter: int, seconds: int,
) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    game.state.home_score, game.state.away_score = 14, 7
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.INCOMPLETE)))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 40)
    game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    expired = seconds <= 5
    assert game.state.quarter == (quarter + 1 if expired and quarter < 4 else quarter)
    assert game.state.game_over is (expired and quarter == 4)
    expected = 900 if expired and quarter < 4 else max(0, seconds - 5)
    assert game.state.time_remaining * 60 == pytest.approx(expected)


@pytest.mark.parametrize("offsetting", [False, True])
@pytest.mark.parametrize("no_huddle", [False, True])
def test_non_incomplete_timing_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, offsetting: bool, no_huddle: bool,
) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, 1
    game.state.ball_position, game.state.down, game.state.yards_to_go = 50, 1, 10
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: (low + high) / 2)
    result = PlayResult(ResultType.INCOMPLETE if offsetting else ResultType.YARDS, yards=0 if offsetting else 4)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        result, offsetting=offsetting))
    game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD, no_huddle=no_huddle)
    elapsed = 10 if offsetting else 20 if no_huddle else 35
    assert game.state.time_remaining * 60 == pytest.approx(60 - elapsed)
    assert game.state.down == (1 if offsetting else 2)


@pytest.mark.parametrize("quarter", [2, 4])
@pytest.mark.parametrize("seconds", [122, 125, 126])
def test_incompletion_respects_two_minute_warning(
    monkeypatch: pytest.MonkeyPatch, quarter: int, seconds: int,
) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.INCOMPLETE)))
    game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    assert game.state.time_remaining * 60 == pytest.approx(max(120, seconds - 5))
    assert game.state.two_minute_warning_called is (seconds < 125)


@pytest.mark.parametrize("remaining", [0.2, 0.99, 1.0, 1.01])
def test_rounding_guard_preserves_whole_second_not_subsecond_residual(remaining: float) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, (5 + remaining) / 60
    game.state.home_score, game.state.away_score = 14, 7
    game._use_time(5)
    expected = remaining if remaining >= 1 else 0
    assert game.state.time_remaining * 60 == pytest.approx(expected)
    assert game.state.game_over is (remaining < 1)


@pytest.mark.parametrize("home", [False, True])
def test_fourth_down_incompletion_changes_possession_but_uses_only_five_seconds(
    monkeypatch: pytest.MonkeyPatch, home: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.quarter, game.state.time_remaining = 4, 28 / 60
    game.state.down, game.state.ball_position, game.state.yards_to_go = 4, 40, 10
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.INCOMPLETE)))
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_timeout=True, call_spike=True,
        call_defensive_timeout=True)
    assert outcome.turnover_on_downs
    assert game.state.is_home_possession is not home
    assert game.state.down == 1 and game.state.ball_position == 60
    assert game.state.time_remaining * 60 == pytest.approx(23)
    assert game.state.home_timeouts == game.state.away_timeouts == 3
    assert not outcome.timeout_used and not outcome.spike_used

"""RULE-022: a foul retains its clock stop after the choice is resolved."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
    parse_result_string,
)
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("no_huddle", [False, True])
@pytest.mark.parametrize("resolution,elapsed", [("clean", 44), ("declined", 5), ("accepted", 5)])
def test_flagged_completion_stops_dead_time_once(
    home: bool, quarter: int, no_huddle: bool, resolution: str, elapsed: int, monkeypatch,
) -> None:
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home
    state.quarter, state.time_remaining = quarter, 85 / 60
    state.is_overtime = quarter == 5
    state.ot_period = int(quarter == 5)
    state.two_minute_warning_called = True
    state.ball_position, state.down, state.yards_to_go = 35, 3, 4
    result = PlayResult(ResultType.YARDS, yards=9, description="Nine-yard completion", raw_result="6")
    options = [] if resolution == "clean" else [PenaltyOption("DEF", "DEF 5", 5, "Defensive foul")]
    choice = PenaltyChoice(result, penalty_options=options, offended_team="offense")
    timing = Mock(return_value=44)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD, no_huddle=no_huddle)
    if options:
        assert outcome.pending_penalty_decision
        assert state.time_remaining * 60 == pytest.approx(85)
        outcome = game.apply_penalty_decision(outcome, accept_play=resolution == "declined")
    assert state.time_remaining * 60 == pytest.approx(85 - elapsed)
    assert state.ball_position == (40 if resolution == "accepted" else 44)
    assert state.down == 1
    assert state.is_home_possession is home
    assert state.defense_stats.penalties == int(resolution == "accepted")
    assert state.offense_stats.passing_yards == (0 if resolution == "accepted" else 9)
    assert len(game.play_log) == 1
    assert getattr(outcome, "clock_stopped_for_penalty", False) is bool(options)
    assert timing.call_count == int(resolution == "clean")


@pytest.mark.parametrize("clock_request", ["call_spike", "call_defensive_timeout"])
def test_declined_foul_needs_no_additional_clock_procedure(clock_request: str, monkeypatch) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 4, 85 / 60
    game.state.ball_position, game.state.down, game.state.yards_to_go = 35, 3, 4
    result = PlayResult(ResultType.YARDS, yards=9)
    choice = PenaltyChoice(result, penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Foul")], offended_team="offense")
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 44)
    pending = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD, **{clock_request: True})
    outcome = game.apply_penalty_decision(pending, accept_play=True)
    assert game.state.time_remaining * 60 == pytest.approx(80)
    assert game.state.down == 1
    assert game.state.home_timeouts == game.state.away_timeouts == 3
    assert not outcome.spike_used and not outcome.defensive_timeout_used


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5", "PI 12"])
def test_direct_scrimmage_penalty_uses_same_clock_policy(home: bool, foul: str, monkeypatch) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.quarter, game.state.time_remaining = 4, 85 / 60
    game.state.ball_position = 35
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: parse_result_string(foul))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 44)
    outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state.time_remaining * 60 == pytest.approx(80)
    assert outcome.clock_stopped_for_penalty


def test_hail_mary_interference_uses_enforced_scrimmage_foul_time(monkeypatch) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, 85 / 60
    monkeypatch.setattr("paydirt.game_engine.resolve_hail_mary", lambda *args: parse_result_string("PI 12"))
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (39, "Interference"))
    outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
    assert game.state.time_remaining * 60 == pytest.approx(81)
    assert outcome.clock_stopped_for_penalty

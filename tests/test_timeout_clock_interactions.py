"""Public-fixture clock boundary and already-stopped timeout controls."""

import random
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def test_defensive_timeout_does_not_follow_a_completed_spike() -> None:
    game = make_sample_game()
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    game.state.is_home_possession = True
    game.state.two_minute_warning_called = True
    result = PlayResult(ResultType.YARDS, yards=3)
    choice = SimpleNamespace(penalty_options=[], offsetting=False, play_result=result)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice), patch(
        "paydirt.game_engine.random.uniform", return_value=35
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.LINE_PLUNGE, DefenseType.STANDARD, call_spike=True)
    assert outcome.spike_used
    before_time = game.state.time_remaining
    assert not game.apply_defensive_timeout(
        outcome, time_before_play=1.0, quarter_before_play=4,
        offense_was_home=True, two_minute_warning_before=True,
    )
    assert game.state.time_remaining == before_time
    assert game.state.away_timeouts == 3


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("incomplete", [False, True])
def test_defensive_timeout_at_period_boundary(quarter: int, incomplete: bool) -> None:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = 0.5
    game.state.is_home_possession = True
    game.state.home_score = 7
    game.state.two_minute_warning_called = True
    game._use_time(35)
    outcome = PlayOutcome(
        play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
        result=PlayResult(ResultType.INCOMPLETE if incomplete else ResultType.YARDS, yards=3))
    before = (game.state.quarter, game.state.time_remaining,
              game.state.home_timeouts, game.state.away_timeouts, game.state.game_over)
    rng_before = random.getstate()
    used = game.apply_defensive_timeout(
        outcome, time_before_play=0.5, quarter_before_play=quarter,
        offense_was_home=True, two_minute_warning_before=True,
        timeouts_before_play=(3, 3),
    )
    assert random.getstate() == rng_before
    assert used is (not incomplete)
    if incomplete:
        assert before == (game.state.quarter, game.state.time_remaining,
                          game.state.home_timeouts, game.state.away_timeouts, game.state.game_over)
    else:
        assert game.state.quarter == quarter
        assert game.state.time_remaining == pytest.approx(20 / 60, abs=0.001)
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 2
        assert not game.state.game_over


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("seconds", [10.0, 10.01, 10.02, 10.5, 11.0, 11.1, 12.0])
@pytest.mark.parametrize("defensive", [False, True])
def test_timeout_cannot_corrupt_a_period_it_cannot_preserve(
    quarter: int, seconds: float, defensive: bool,
) -> None:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = seconds / 60
    game.state.is_home_possession = True
    game.state.home_score = 7  # Regulation ends without overtime.
    game.state.home_timeouts, game.state.away_timeouts = 1, 2
    game.state.two_minute_warning_called = True
    game._use_time(35)
    after_play = (game.state.quarter, game.state.time_remaining,
                  game.state.home_timeouts, game.state.away_timeouts,
                  game.state.game_over, game.state.two_minute_warning_called)
    outcome = PlayOutcome(
        play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
        result=PlayResult(ResultType.YARDS, yards=3),
    )
    used = game._apply_requested_timeout(
        outcome, timeout_is_home=not defensive,
        time_before_play=seconds / 60, quarter_before_play=quarter,
        offense_was_home=True, two_minute_warning_before=True,
        timeouts_before_play=(1, 2),
    )
    preserves_period = seconds >= 11.1
    assert used is preserves_period
    assert outcome.timeout_used is preserves_period
    if preserves_period:
        assert game.state.quarter == quarter
        assert game.state.time_remaining == pytest.approx(seconds / 60 - .167)
        assert (game.state.home_timeouts, game.state.away_timeouts) == (
            (1, 1) if defensive else (0, 2))
        assert not game.state.game_over
    else:
        assert after_play == (game.state.quarter, game.state.time_remaining,
                              game.state.home_timeouts, game.state.away_timeouts,
                              game.state.game_over, game.state.two_minute_warning_called)


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("seconds", [10.0, 10.02, 10.5, 11.0])
def test_timeout_adjustment_preserves_an_already_advanced_period_without_saved_time(
    quarter: int, seconds: float,
) -> None:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = seconds / 60
    game.state.home_score = 7
    game._use_time(35)
    after_play = (game.state.quarter, game.state.time_remaining, game.state.game_over)
    game._apply_timeout(seconds / 60, quarter)
    assert (game.state.quarter, game.state.time_remaining, game.state.game_over) == after_play


@pytest.mark.parametrize("defensive", [False, True])
def test_sideline_play_with_timeout_request_leaves_clean_halftime(
    defensive: bool,
) -> None:
    game = make_sample_game()
    game.state.quarter = 2
    game.state.time_remaining = 10.5 / 60
    game.state.home_timeouts, game.state.away_timeouts = 1, 2
    game.state.two_minute_warning_called = True
    result = PlayResult(ResultType.YARDS, yards=12, raw_result="12")
    choice = SimpleNamespace(penalty_options=[], offsetting=False, play_result=result)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice), patch(
        "paydirt.game_engine.random.uniform", return_value=35,
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.SCREEN, DefenseType.STANDARD,
            out_of_bounds_designation=True,
            call_timeout=not defensive, call_defensive_timeout=defensive,
        )
    assert game.state.quarter == 3
    assert game.state.time_remaining == 15
    assert (game.state.home_timeouts, game.state.away_timeouts) == (3, 3)
    assert not outcome.timeout_used
    assert not outcome.defensive_timeout_used

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

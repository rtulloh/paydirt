"""Standalone spikes charge three seconds through both engine entry points."""

import pytest

from paydirt.play_resolver import DefenseType, PlayType, ResultType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
def test_standalone_spike_charges_three_seconds(
    direct: bool, quarter: int, monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = 90 / 60
    game.state.down = 1
    game.state.ball_position = 40
    game.state.yards_to_go = 10
    game.state.two_minute_warning_called = True

    def unexpected_roll() -> None:
        pytest.fail("A standalone spike must not roll chart dice")

    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", unexpected_roll)
    run = game.run_play if direct else game.run_play_with_penalty_procedure
    outcome = run(PlayType.SPIKE_BALL, DefenseType.STANDARD)

    assert game.state.time_remaining * 60 == pytest.approx(87)
    assert game.state.quarter == quarter
    assert game.state.down == 2
    assert game.state.ball_position == 40
    assert outcome.result.result_type is ResultType.INCOMPLETE
    assert not outcome.turnover
    assert game.last_clock_trace.requested_seconds == 3
    assert game.last_clock_trace.charged_seconds == pytest.approx(3)


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("quarter", [2, 4])
def test_standalone_spike_expires_a_two_second_half(direct: bool, quarter: int) -> None:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = 2 / 60
    game.state.down = 1
    game.state.two_minute_warning_called = True
    game.state.home_score = 7
    game.state.away_score = 0
    run = game.run_play if direct else game.run_play_with_penalty_procedure

    run(PlayType.SPIKE_BALL, DefenseType.STANDARD)

    assert game.last_clock_trace.requested_seconds == 3
    assert game.last_clock_trace.charged_seconds == pytest.approx(2)
    assert game.last_clock_trace.period_ended
    if quarter == 2:
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15
    else:
        assert game.state.time_remaining == 0
        assert game.state.game_over


@pytest.mark.parametrize("direct", [False, True])
def test_fourth_down_standalone_spike_still_charges_three_seconds(direct: bool) -> None:
    game = make_sample_game()
    game.state.quarter = 2
    game.state.time_remaining = 90 / 60
    game.state.down = 4
    game.state.ball_position = 40
    game.state.yards_to_go = 10
    game.state.is_home_possession = True
    game.state.two_minute_warning_called = True
    run = game.run_play if direct else game.run_play_with_penalty_procedure

    outcome = run(PlayType.SPIKE_BALL, DefenseType.STANDARD)

    assert game.state.time_remaining * 60 == pytest.approx(87)
    assert outcome.turnover_on_downs
    assert game.state.is_home_possession is False
    assert game.state.ball_position == 60

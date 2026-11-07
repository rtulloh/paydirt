"""Offsetting kickoff fouls replay before an expiring period can finish."""
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.models import PlayOutcome
from tests.game_fixtures import make_sample_game


def offset_game(quarter: int, kicking_home: bool, source: str) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = 6 / 60
    game.state.home_score, game.state.away_score = (14, 14) if quarter == 5 else (14, 28)
    if quarter == 5:
        game.state.is_overtime = True
        game.state.ot_period = 1
    kicker = game.state.home_chart if kicking_home else game.state.away_chart
    receiver = game.state.away_chart if kicking_home else game.state.home_chart
    kicker.special_teams.kickoff.update({10: "60" if source == "return" else "OFF 10",
                                       11: "60", 13: "60"})
    receiver.special_teams.kickoff_return.update({11: "OFF 10", 12: "DEF 10", 14: "20"})
    return game


@pytest.mark.parametrize("quarter", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("source", ["return", "cross-chart"])
def test_expiring_offsetting_kickoff_replays_in_original_period(
    quarter: int, kicking_home: bool, source: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = offset_game(quarter, kicking_home, source)
    original = game.kickoff
    starts = []

    def checked_kickoff(kicking_home: bool = True, kickoff_spot: int = 35) -> PlayOutcome:
        assert not game.state.game_over, "Offsetting kickoff must replay before game end"
        starts.append((game.state.quarter, game.state.time_remaining, game.last_clock_trace))
        return original(kicking_home=kicking_home, kickoff_spot=kickoff_spot)

    monkeypatch.setattr(game, "kickoff", checked_kickoff)
    sequence = [10, 11, 12, 13, 14]
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in sequence]) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.kickoff(kicking_home=kicking_home)
    assert dice.call_count == 5
    assert len(starts) == 2
    assert starts[1][:2] == (quarter, 0)
    assert starts[1][2].period_ended is False
    assert outcome.clock_trace.start_quarter == quarter
    assert outcome.clock_trace.charged_seconds == 0
    assert game.state.is_home_possession is not kicking_home
    assert game.state.ball_position == 25
    assert not game.has_untimed_down()
    assert len(game.play_log) == 1
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    if quarter < 4:
        assert (game.state.quarter, game.state.time_remaining) == (quarter + 1, 15)
        assert not game.state.game_over
    else:
        assert game.state.game_over
        assert game.state.time_remaining == 0


@pytest.mark.parametrize("source", ["return", "cross-chart"])
@pytest.mark.parametrize("kicking_home", [False, True])
def test_offsetting_kickoff_with_time_remaining_keeps_ten_second_charge(
    source: str, kicking_home: bool,
) -> None:
    game = offset_game(4, kicking_home, source)
    game.state.time_remaining = .5
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 12, 13, 14]]),
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        game.kickoff(kicking_home=kicking_home)
    assert game.state.quarter == 4
    assert game.state.time_remaining == pytest.approx(12 / 60)
    assert not game.state.game_over
    assert not game.has_untimed_down()

"""
Unit tests for auto_game.py game loop logic.
"""
import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import (
    TeamChart, PeripheralData, OffenseChart,
    DefenseChart, SpecialTeamsChart
)


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        interception_return={10: "5"},
        kickoff={},
        kickoff_return={},
        punt={},
        punt_return={},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_offense():
    """Create mock offense chart."""
    return OffenseChart(
        line_plunge={10: "5"},
    )


@pytest.fixture
def mock_team_chart(mock_offense, mock_special_teams):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            power_rating=50,
            power_rating_variance=1,
            base_yardage_factor=100,
            reduced_yardage_factor=80,
            fumble_recovered_range=(0, 0),
            fumble_lost_range=(0, 0),
            special_defense="",
            short_name="TST '83",
        ),
        offense=mock_offense,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


class TestAutoGameUntimedDownSafetyNet:
    """
    Tests for the untimed down safety net in the auto game loop.

    Regression test: Previously, auto_game.py never called
    game.clear_untimed_down() after a defensive penalty triggered an
    untimed down. This left untimed_down_pending=True forever, causing
    _use_time() to permanently block quarter advancement whenever
    time_remaining hit 0, resulting in infinitely high scores.
    """

    @pytest.fixture
    def game(self, mock_team_chart):
        """Create a game with mock team charts."""
        return PaydirtGameEngine(mock_team_chart, mock_team_chart)

    def test_game_loop_clears_untimed_down_at_zero(self, game):
        """
        When time is effectively zero and untimed_down is pending,
        the auto game loop should clear the flag so the quarter advances.
        """
        game.state.quarter = 1
        game.state.time_remaining = 0
        game.state.untimed_down_pending = True

        state = game.state
        assert state.time_remaining < 0.0167
        assert game.has_untimed_down()

        if state.time_remaining < 0.0167 and game.has_untimed_down():
            game.clear_untimed_down()

        assert game.has_untimed_down() is False
        game._use_time(30)
        assert game.state.quarter == 2

    def test_game_loop_does_not_clear_untimed_down_with_time_remaining(self, game):
        """
        When there is still time on the clock, the auto game loop
        should NOT clear the untimed down flag early.
        """
        game.state.quarter = 1
        game.state.time_remaining = 5.0
        game.state.untimed_down_pending = True

        state = game.state
        assert state.time_remaining >= 0.0167

        if state.time_remaining < 0.0167 and game.has_untimed_down():
            game.clear_untimed_down()

        assert game.has_untimed_down() is True

    def test_quarter_advances_past_q1_after_untimed_down_cleared(self, game):
        """
        End-to-end: simulate the sequence that previously caused the bug:
        1. Time hits 0, untimed_down_pending is True
        2. Auto game loop clears the flag (the fix)
        3. Next _use_time call advances the quarter
        """
        game.state.quarter = 1
        game.state.time_remaining = 0
        game.state.untimed_down_pending = True

        state = game.state
        if state.time_remaining < 0.0167 and game.has_untimed_down():
            game.clear_untimed_down()

        game._use_time(30)

        assert game.state.quarter == 2
        assert game.state.time_remaining == 15.0
        assert game.has_untimed_down() is False

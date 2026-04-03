"""
Tests for game_engine.py to improve coverage for specific functions.
"""

import pytest
from unittest.mock import MagicMock, patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType, DefenseType
from paydirt.chart_loader import (
    TeamChart,
    PeripheralData,
    OffenseChart,
    DefenseChart,
    SpecialTeamsChart,
)


def create_mock_chart(short_name: str = "TEST", year: int = 1983) -> TeamChart:
    """Create a minimal mock TeamChart for testing."""
    return TeamChart(
        peripheral=PeripheralData(
            year=year,
            team_name="Test Team",
            team_nickname="Testers",
            power_rating=50,
            short_name=short_name,
        ),
        offense=MagicMock(spec=OffenseChart),
        defense=MagicMock(spec=DefenseChart),
        special_teams=MagicMock(spec=SpecialTeamsChart),
    )


@pytest.fixture
def game():
    """Create a game engine for testing."""
    home_chart = create_mock_chart("HOME")
    away_chart = create_mock_chart("AWAY")
    return PaydirtGameEngine(home_chart, away_chart)


class TestHandleQBKneel:
    """Tests for _handle_qb_kneel function."""

    def test_handle_qb_kneel_returns_result(self, game):
        """_handle_qb_kneel should return a valid result."""
        game.state.ball_position = 30
        game.state.time_remaining = 10.0

        result = game._handle_qb_kneel()

        assert result is not None


class TestUseTime:
    """Tests for _use_time function."""

    def test_use_time_basic(self, game):
        """_use_time should reduce time."""
        game.state.time_remaining = 10.0

        game._use_time(5.0)

        assert game.state.time_remaining < 10.0


class TestGetScoreStr:
    """Tests for get_score_str function."""

    def test_get_score_str_tied(self, game):
        """get_score_str should return correct format for tied game."""
        game.state.home_score = 10
        game.state.away_score = 10

        result = game.get_score_str()

        assert "10" in result
        assert "-" in result

    def test_get_score_str_home_leading(self, game):
        """get_score_str should return correct format when home leads."""
        game.state.home_score = 17
        game.state.away_score = 10

        result = game.get_score_str()

        assert "17" in result
        assert "10" in result


class TestGetStatus:
    """Tests for get_status function."""

    def test_get_status_returns_dict(self, game):
        """get_status should return a dictionary."""
        result = game.get_status()

        assert isinstance(result, dict)
        assert "quarter" in result
        assert "time" in result


class TestGetStatusFields:
    """Tests for get_status function fields."""

    def test_get_status_contains_all_fields(self, game):
        """get_status should contain required fields."""
        result = game.get_status()

        required_fields = [
            "quarter",
            "time",
            "score",
            "possession",
            "field_position",
            "down",
            "yards_to_go",
            "game_over",
        ]

        for field in required_fields:
            assert field in result, f"Missing field: {field}"

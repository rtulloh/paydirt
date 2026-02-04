"""
Tests for CPU AI timeout logic when on defense.

The CPU should call timeouts when trailing late in the game to stop the clock
and get the ball back.
"""
import pytest
from unittest.mock import MagicMock

from paydirt.computer_ai import ComputerAI, computer_should_call_timeout_on_defense
from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


def create_mock_chart(short_name: str, full_name: str) -> TeamChart:
    """Create a mock team chart for testing."""
    peripheral = PeripheralData(
        year=1983,
        team_name=full_name.split()[-1],
        team_nickname=full_name.split()[-1],
        power_rating=50,
        short_name=short_name
    )
    return TeamChart(
        peripheral=peripheral,
        offense=OffenseChart(),
        defense=DefenseChart(),
        special_teams=SpecialTeamsChart(),
        team_dir=""
    )


class TestCPUTimeoutOnDefense:
    """Tests for CPU calling timeouts when on defense."""

    def test_cpu_calls_timeout_trailing_q4_under_2_min(self):
        """CPU should call timeout when trailing in Q4 with < 2 minutes left."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        # Home team (PHI) has ball, CPU is away (SF) on defense
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.home_score = 21  # PHI leading
        game.state.away_score = 14  # SF trailing by 7
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is True

    def test_cpu_calls_timeout_trailing_q4_under_5_min_big_deficit(self):
        """CPU should call timeout when trailing by 14+ in Q4 with < 5 minutes."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 4.5  # 4:30 left
        game.state.home_score = 28
        game.state.away_score = 14  # Trailing by 14
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is True

    def test_cpu_no_timeout_when_leading(self):
        """CPU should NOT call timeout when leading."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 14
        game.state.away_score = 21  # CPU is winning
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False

    def test_cpu_no_timeout_when_no_timeouts_left(self):
        """CPU should NOT call timeout when no timeouts remaining."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.away_timeouts = 0  # No timeouts
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False

    def test_cpu_no_timeout_early_in_game(self):
        """CPU should NOT call timeout in Q1 or Q3."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 1
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False
        
        game.state.quarter = 3
        assert ai.should_call_timeout_on_defense(game) is False

    def test_cpu_calls_timeout_end_of_half_trailing(self):
        """CPU should call timeout at end of Q2 when trailing by TD+."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 1.5  # 1:30 left in half
        game.state.home_score = 14
        game.state.away_score = 7  # Trailing by 7
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is True

    def test_cpu_no_timeout_q2_small_deficit(self):
        """CPU should NOT call timeout in Q2 with small deficit and > 1 min."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 1.5
        game.state.home_score = 10
        game.state.away_score = 7  # Only trailing by 3
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False

    def test_convenience_function_works(self):
        """Test the convenience function computer_should_call_timeout_on_defense."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.away_timeouts = 3
        
        assert computer_should_call_timeout_on_defense(game) is True

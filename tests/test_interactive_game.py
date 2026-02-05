"""
Tests for interactive_game.py functions that don't require user input.
"""
import pytest
from unittest.mock import MagicMock, patch

from paydirt.interactive_game import (
    analyze_team_strength,
    cpu_should_go_for_two,
    cpu_should_onside_kick,
    computer_select_offense,
    computer_select_defense,
    _apply_timeout,
    format_time,
)
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType, DefenseType
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.computer_ai import ComputerAI


def create_mock_chart(short_name: str = "TEST") -> TeamChart:
    """Create a minimal mock TeamChart for testing."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Testers",
            power_rating=50,
            short_name=short_name
        ),
        offense=MagicMock(spec=OffenseChart),
        defense=MagicMock(spec=DefenseChart),
        special_teams=MagicMock(spec=SpecialTeamsChart)
    )


@pytest.fixture
def game():
    """Create a game engine for testing."""
    home_chart = create_mock_chart("HOME")
    away_chart = create_mock_chart("AWAY")
    return PaydirtGameEngine(home_chart, away_chart)


class TestAnalyzeTeamStrength:
    """Tests for analyze_team_strength function."""
    
    def test_run_heavy_team(self):
        """Team with good running charts should be identified as run-heavy."""
        offense = OffenseChart(
            line_plunge={10: "5", 15: "4", 20: "3", 25: "6", 30: "B"},
            off_tackle={10: "6", 15: "5", 20: "4", 25: "7", 30: "8"},
            end_run={10: "7", 15: "6", 20: "5", 25: "8", 30: "9"},
            draw={10: "4", 15: "3", 20: "2", 25: "5", 30: "6"},
            screen={10: "INC", 15: "INC", 20: "INT", 25: "3", 30: "4"},
            short_pass={10: "INC", 15: "INC", 20: "INT", 25: "5", 30: "6"},
            medium_pass={10: "INC", 15: "INC", 20: "INT", 25: "8", 30: "10"},
            long_pass={10: "INC", 15: "INC", 20: "INT", 25: "15", 30: "20"},
            te_short_long={10: "INC", 15: "INC", 20: "5", 25: "8", 30: "10"},
        )
        
        result = analyze_team_strength(offense)
        
        assert result == "run"
    
    def test_pass_heavy_team(self):
        """Team with good passing charts should be identified as pass-heavy."""
        offense = OffenseChart(
            line_plunge={10: "F", 15: "-2", 20: "0", 25: "1", 30: "2"},
            off_tackle={10: "F", 15: "-1", 20: "0", 25: "2", 30: "3"},
            end_run={10: "F", 15: "-2", 20: "1", 25: "2", 30: "3"},
            draw={10: "F", 15: "-1", 20: "0", 25: "1", 30: "2"},
            screen={10: "5", 15: "6", 20: "7", 25: "8", 30: "10"},
            short_pass={10: "6", 15: "8", 20: "10", 25: "12", 30: "15"},
            medium_pass={10: "10", 15: "12", 20: "15", 25: "20", 30: "25"},
            long_pass={10: "15", 15: "20", 20: "25", 25: "30", 30: "TD"},
            te_short_long={10: "8", 15: "10", 20: "12", 25: "15", 30: "18"},
        )
        
        result = analyze_team_strength(offense)
        
        assert result == "pass"
    
    def test_balanced_team(self):
        """Team with equal run/pass should be identified as balanced."""
        offense = OffenseChart(
            line_plunge={10: "3", 15: "4", 20: "5"},
            off_tackle={10: "4", 15: "5", 20: "6"},
            end_run={10: "5", 15: "6", 20: "7"},
            draw={10: "3", 15: "4", 20: "5"},
            screen={10: "4", 15: "5", 20: "6"},
            short_pass={10: "5", 15: "6", 20: "7"},
            medium_pass={10: "8", 15: "10", 20: "12"},
            long_pass={10: "12", 15: "15", 20: "18"},
            te_short_long={10: "6", 15: "8", 20: "10"},
        )
        
        result = analyze_team_strength(offense)
        
        assert result == "balanced"
    
    def test_handles_variable_yardage(self):
        """Should handle variable yardage results like DS, T1, etc."""
        offense = OffenseChart(
            line_plunge={10: "DS", 15: "T1", 20: "3"},
            off_tackle={10: "4", 15: "5", 20: "6"},
            end_run={10: "5", 15: "6", 20: "7"},
            draw={10: "3", 15: "4", 20: "5"},
            screen={10: "4", 15: "5", 20: "6"},
            short_pass={10: "5", 15: "6", 20: "7"},
            medium_pass={10: "8", 15: "10", 20: "12"},
            long_pass={10: "12", 15: "15", 20: "18"},
            te_short_long={10: "6", 15: "8", 20: "10"},
        )
        
        # Should not raise an error
        result = analyze_team_strength(offense)
        assert result in ["run", "pass", "balanced"]
    
    def test_handles_breakaway(self):
        """Should count breakaway results as very positive."""
        offense = OffenseChart(
            line_plunge={10: "B", 15: "B", 20: "B"},  # Lots of breakaways
            off_tackle={10: "B", 15: "B", 20: "B"},
            end_run={10: "1", 15: "2", 20: "3"},
            draw={10: "1", 15: "2", 20: "3"},
            screen={10: "INC", 15: "INC", 20: "INC"},
            short_pass={10: "INC", 15: "INC", 20: "INC"},
            medium_pass={10: "INC", 15: "INC", 20: "INC"},
            long_pass={10: "INC", 15: "INC", 20: "INC"},
            te_short_long={10: "INC", 15: "INC", 20: "INC"},
        )
        
        result = analyze_team_strength(offense)
        
        # With all those breakaways in running, should be run-heavy
        assert result == "run"


class TestCpuShouldGoForTwo:
    """Tests for cpu_should_go_for_two function."""
    
    def test_kicks_extra_point_by_default(self, game):
        """CPU should kick extra point in normal situations."""
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        game.state.home_score = 7
        game.state.away_score = 0
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is False
    
    def test_goes_for_two_when_tied_very_late(self, game):
        """CPU should go for 2 when tied very late in game."""
        game.state.quarter = 4
        game.state.time_remaining = 1.0  # Under 2 minutes
        game.state.home_score = 14
        game.state.away_score = 14  # Tied after TD
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_goes_for_two_when_down_by_2_late(self, game):
        """CPU should go for 2 when down by 2 late in game."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0  # Late game
        game.state.home_score = 12
        game.state.away_score = 14  # Down by 2
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_goes_for_two_when_down_by_8_late(self, game):
        """CPU should go for 2 when down by 8 late in game."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0
        game.state.home_score = 13
        game.state.away_score = 21  # Down by 8
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_goes_for_two_when_up_by_1_very_late(self, game):
        """CPU should go for 2 when up by 1 very late to go up 3."""
        game.state.quarter = 4
        game.state.time_remaining = 1.0
        game.state.home_score = 15
        game.state.away_score = 14  # Up by 1
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_kicks_when_up_big(self, game):
        """CPU should kick extra point when up big."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0
        game.state.home_score = 28
        game.state.away_score = 7  # Up by 21
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is False


class TestCpuShouldOnsideKick:
    """Tests for cpu_should_onside_kick function."""
    
    def test_no_onside_early_in_game(self, game):
        """CPU should not onside kick early in game."""
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        game.state.home_score = 7
        game.state.away_score = 14  # Trailing
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is False
    
    def test_no_onside_when_leading(self, game):
        """CPU should not onside kick when leading."""
        game.state.quarter = 4
        game.state.time_remaining = 1.0
        game.state.home_score = 21
        game.state.away_score = 14  # Leading
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is False
    
    def test_onside_when_trailing_under_2_min(self, game):
        """CPU should onside kick when trailing under 2 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is True
    
    def test_onside_when_trailing_big_under_5_min(self, game):
        """CPU should onside kick when trailing by 9+ under 5 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 4.0
        game.state.home_score = 7
        game.state.away_score = 21  # Trailing by 14
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is True
    
    def test_no_onside_small_deficit_under_5_min(self, game):
        """CPU should not onside kick with small deficit under 5 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 4.0
        game.state.home_score = 14
        game.state.away_score = 17  # Trailing by only 3
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is False


class TestComputerSelectOffense:
    """Tests for computer_select_offense function."""
    
    def test_returns_valid_play_type(self, game):
        """Should return a valid PlayType."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 25
        
        result = computer_select_offense(game)
        
        assert isinstance(result, PlayType)
    
    def test_uses_provided_ai(self, game):
        """Should use provided AI instance."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 25
        
        ai = ComputerAI(aggression=0.9)
        result = computer_select_offense(game, ai)
        
        assert isinstance(result, PlayType)


class TestComputerSelectDefense:
    """Tests for computer_select_defense function."""
    
    def test_returns_valid_defense_type(self, game):
        """Should return a valid DefenseType."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        
        result = computer_select_defense(game)
        
        assert isinstance(result, DefenseType)
    
    def test_uses_provided_ai(self, game):
        """Should use provided AI instance."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        
        ai = ComputerAI(aggression=0.9)
        result = computer_select_defense(game, ai)
        
        assert isinstance(result, DefenseType)


class TestApplyTimeout:
    """Tests for _apply_timeout function."""
    
    def test_reduces_time_by_10_seconds(self, game):
        """Timeout should reduce time to 10 seconds for the play."""
        game.state.time_remaining = 5.0  # 5 minutes
        time_before = 5.0
        
        _apply_timeout(game, time_before)
        
        # Should be time_before - 0.167 (10 seconds)
        assert abs(game.state.time_remaining - 4.833) < 0.01
    
    def test_does_not_go_negative(self, game):
        """Time should not go negative."""
        game.state.time_remaining = 0.1  # 6 seconds
        time_before = 0.1
        
        _apply_timeout(game, time_before)
        
        assert game.state.time_remaining == 0
    
    def test_prevents_premature_game_over(self, game):
        """Should prevent game from ending prematurely."""
        game.state.time_remaining = 0.2
        game.state.quarter = 4
        game.state.game_over = True
        time_before = 0.2
        
        _apply_timeout(game, time_before)
        
        assert game.state.game_over is False


class TestFormatTime:
    """Tests for format_time function (imported from utils)."""
    
    def test_full_minutes(self):
        assert format_time(5.0) == "5:00"
    
    def test_half_minute(self):
        assert format_time(2.5) == "2:30"
    
    def test_zero(self):
        assert format_time(0.0) == "0:00"

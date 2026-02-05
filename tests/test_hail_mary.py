"""
Tests for Hail Mary pass per official Paydirt rules.

Official rules:
- Available at end of half or overtime
- Defense is "blank" (no response)
- Uses special result table based on dice roll

Dice Total | Result
-----------|--------
10-18      | Complete (25 + T1*10 yards downfield)
19         | Complete (TD)
20-23, 26-29 | INT (25 + T1*10 yards downfield)
24-25      | QT (roll again)
30-38      | INC
39         | DEF PI (25 + T1*10 yards downfield)

T1 = tens digit of dice roll (1, 2, or 3)
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import (
    PlayType, DefenseType, ResultType, resolve_hail_mary
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
def mock_team_chart(mock_special_teams, mock_offense):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '83",
            power_rating=50,
        ),
        offense=mock_offense,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestResolveHailMary:
    """Tests for resolve_hail_mary function."""
    
    def test_roll_10_18_is_complete(self):
        """Rolls 10-18 should be completions."""
        for roll in [10, 11, 12, 13, 14, 15, 16, 17, 18]:
            result = resolve_hail_mary(roll, 50)
            assert result.result_type in [ResultType.YARDS, ResultType.TOUCHDOWN]
            assert "COMPLETE" in result.description
    
    def test_roll_10_18_yardage_calculation(self):
        """Completion yardage should be 25 + T1 (T1 = tens digit)."""
        # Roll 15: T1=1, yards = 25 + 1 = 26
        result = resolve_hail_mary(15, 50)
        assert result.yards == 26
        
        # Roll 28 is INT with T1=2, yards = 25 + 2 = 27
        result = resolve_hail_mary(28, 50)
        assert result.yards == 27
    
    def test_roll_19_is_automatic_td(self):
        """Roll 19 should be automatic touchdown."""
        result = resolve_hail_mary(19, 50)
        assert result.result_type == ResultType.TOUCHDOWN
        assert result.touchdown is True
        assert "TOUCHDOWN" in result.description
    
    def test_roll_20_23_is_interception(self):
        """Rolls 20-23 should be interceptions."""
        for roll in [20, 21, 22, 23]:
            result = resolve_hail_mary(roll, 50)
            assert result.result_type == ResultType.INTERCEPTION
            assert result.turnover is True
            assert "INTERCEPTED" in result.description
    
    def test_roll_26_29_is_interception(self):
        """Rolls 26-29 should be interceptions."""
        for roll in [26, 27, 28, 29]:
            result = resolve_hail_mary(roll, 50)
            assert result.result_type == ResultType.INTERCEPTION
            assert result.turnover is True
    
    def test_roll_24_25_is_qt(self):
        """Rolls 24-25 should be Quick Throw (roll again)."""
        for roll in [24, 25]:
            result = resolve_hail_mary(roll, 50)
            assert "Quick Throw" in result.description or "QT" in result.raw_result
    
    def test_roll_30_38_is_incomplete(self):
        """Rolls 30-38 should be incomplete."""
        for roll in [30, 31, 32, 33, 34, 35, 36, 37, 38]:
            result = resolve_hail_mary(roll, 50)
            assert result.result_type == ResultType.INCOMPLETE
            assert result.yards == 0
            assert "INCOMPLETE" in result.description
    
    def test_roll_39_is_pass_interference(self):
        """Roll 39 should be defensive pass interference."""
        result = resolve_hail_mary(39, 50)
        assert result.result_type == ResultType.PASS_INTERFERENCE
        assert "INTERFERENCE" in result.description
        # T1=3, yards = 25 + 3 = 28
        assert result.yards == 28
    
    def test_completion_for_td_when_close_to_goal(self):
        """Completion should be TD if yardage reaches end zone."""
        # At 80 yard line, 26 yard completion = TD (80 + 26 = 106 >= 100)
        result = resolve_hail_mary(15, 80)  # T1=1, 26 yards
        assert result.result_type == ResultType.TOUCHDOWN
        assert result.touchdown is True


class TestHailMaryGameEngine:
    """Tests for Hail Mary in game engine."""
    
    def test_hail_mary_touchdown(self, game):
        """Hail Mary roll 19 should score touchdown."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (19, "B1+W9+W0=19")
            
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.home_score == initial_score + 6
    
    def test_hail_mary_interception(self, game):
        """Hail Mary interception should turn ball over."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (20, "B2+W0+W0=20")
            
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        assert outcome.turnover is True
        assert game.state.is_home_possession is False
    
    def test_hail_mary_incomplete(self, game):
        """Hail Mary incomplete should advance to next down."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 2
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (35, "B3+W2+W3=35")
            
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        assert outcome.yards_gained == 0
        assert game.state.down == 3
    
    def test_hail_mary_pass_interference(self, game):
        """Hail Mary PI should give automatic first down."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (39, "B3+W4+W5=39")
            
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        assert outcome.first_down is True
        assert game.state.down == 1
    
    def test_hail_mary_qt_rerolls(self, game):
        """Hail Mary QT should automatically reroll."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll is QT (24), second roll is TD (19)
            mock_dice.side_effect = [
                (24, "B2+W2+W2=24"),  # QT - reroll
                (19, "B1+W9+W0=19"),  # TD
            ]
            
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        # Should have rerolled and gotten TD
        assert outcome.touchdown is True
    
    def test_hail_mary_completion_for_yardage(self, game):
        """Hail Mary completion should advance ball."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (15, "B1+W5+W0=15")  # 26 yard completion (25 + T1=1)
            
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        assert outcome.yards_gained == 26
        assert game.state.ball_position == 56


class TestHailMaryDefenseNotParticipating:
    """Tests to verify defense doesn't participate in Hail Mary."""
    
    def test_defense_type_ignored(self, game):
        """Defense type should be ignored for Hail Mary."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (19, "B1+W9+W0=19")
            
            # Try with different defense types - result should be same
            outcome1 = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        
        game.state.ball_position = 50
        game.state.home_score = 0  # Reset score
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (19, "B1+W9+W0=19")
            
            outcome2 = game.run_play(PlayType.HAIL_MARY, DefenseType.BLITZ)
        
        # Both should have same result since defense doesn't participate
        assert outcome1.touchdown == outcome2.touchdown

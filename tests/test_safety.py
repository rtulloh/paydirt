"""
Tests for touchback and safety rules per official Paydirt rules.

Official rules:
- Touchback: No points, defending team gets ball 1st and 10 at their 20
- Safety: 2 points for defense, victims get free kick (kickoff or punt) from own 20
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        interception_return={10: "5"},
        kickoff={10: "50", 11: "55", 12: "60"},
        kickoff_return={10: "20", 11: "15", 12: "25"},
        punt={10: "40", 11: "45", 12: "50"},
        punt_return={10: "5", 11: "10", 12: "8"},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_offense():
    """Create mock offense chart."""
    return OffenseChart(
        line_plunge={10: "5", 11: "3", 12: "-2"},
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


class TestSafetyScoring:
    """Tests for safety scoring."""
    
    def test_safety_scores_2_points_for_defense(self, game):
        """Safety should score 2 points for the defense."""
        game.state.is_home_possession = True
        game.state.ball_position = 5
        initial_away_score = game.state.away_score
        
        game._score_safety()
        
        assert game.state.away_score == initial_away_score + 2
    
    def test_safety_ball_at_20(self, game):
        """After safety, ball should be at the 20 yard line."""
        game.state.is_home_possession = True
        game.state.ball_position = 5
        
        game._score_safety()
        
        assert game.state.ball_position == 20


class TestSafetyFreeKickKickoff:
    """Tests for safety free kick using kickoff."""
    
    def test_safety_kickoff_from_own_20(self, game):
        """Safety free kick kickoff should be from own 20."""
        game.state.is_home_possession = True
        game.state.ball_position = 20
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Kickoff 50 yards from 20 = lands at opponent's 30
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.safety_free_kick(use_punt=False)
        
        # Possession should switch to receiving team
        assert game.state.is_home_possession is False
        assert "Safety free kick" in outcome.description
    
    def test_safety_kickoff_switches_possession(self, game):
        """Safety free kick should switch possession to receiving team."""
        game.state.is_home_possession = True
        game.state.ball_position = 20
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.safety_free_kick(use_punt=False)
        
        assert game.state.is_home_possession is False
    
    def test_safety_kickoff_resets_downs(self, game):
        """Safety free kick should reset to 1st and 10."""
        game.state.is_home_possession = True
        game.state.ball_position = 20
        game.state.down = 3
        game.state.yards_to_go = 5
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.safety_free_kick(use_punt=False)
        
        assert game.state.down == 1
        assert game.state.yards_to_go == 10


class TestSafetyFreeKickPunt:
    """Tests for safety free kick using punt."""
    
    def test_safety_punt_from_own_20(self, game):
        """Safety free kick punt should be from own 20."""
        game.state.is_home_possession = True
        game.state.ball_position = 20
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards from 20 = lands at opponent's 40
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.safety_free_kick(use_punt=True)
        
        assert "Safety free kick punt" in outcome.description
    
    def test_safety_punt_switches_possession(self, game):
        """Safety free kick punt should switch possession."""
        game.state.is_home_possession = True
        game.state.ball_position = 20
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.safety_free_kick(use_punt=True)
        
        assert game.state.is_home_possession is False
    
    def test_safety_punt_resets_downs(self, game):
        """Safety free kick punt should reset to 1st and 10."""
        game.state.is_home_possession = True
        game.state.ball_position = 20
        game.state.down = 4
        game.state.yards_to_go = 15
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.safety_free_kick(use_punt=True)
        
        assert game.state.down == 1
        assert game.state.yards_to_go == 10


class TestTouchbackRules:
    """Tests for touchback rules."""
    
    def test_touchback_ball_at_20(self, game):
        """Touchback should place ball at the 20 yard line."""
        # Simulate a touchback via end zone return helper
        final_pos, is_touchback = game._handle_end_zone_return(5, 3, elect_touchback=True)
        
        assert final_pos == 20
        assert is_touchback is True
    
    def test_touchback_no_points(self, game):
        """Touchback should not score any points."""
        initial_home = game.state.home_score
        initial_away = game.state.away_score
        
        # Simulate touchback via end zone return
        final_pos, is_touchback = game._handle_end_zone_return(5, 3, elect_touchback=True)
        
        assert game.state.home_score == initial_home
        assert game.state.away_score == initial_away

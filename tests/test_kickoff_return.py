"""
Tests for kickoff return penalty handling.
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with kickoff return results."""
    return SpecialTeamsChart(
        kickoff={
            10: "60",   # Normal kickoff
            11: "65",   # Deep kickoff
            12: "TB",   # Touchback
        },
        kickoff_return={
            10: "20",      # Normal return
            11: "OFF 15",  # Offensive penalty on return
            12: "DEF 15",  # Defensive penalty on return
            13: "30",      # Long return
        },
        punt={},
        punt_return={},
        interception_return={},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_team_chart(mock_special_teams):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            power_rating=50,
            short_name="TST '83"
        ),
        offense=OffenseChart(),
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestKickoffReturnPenalties:
    """Tests for penalty handling on kickoff returns."""
    
    def test_offensive_penalty_on_kickoff_return_moves_ball_back(self, game):
        """Offensive penalty on kickoff return should move ball back with half-the-distance rule."""
        # Note: Kickoff uses same dice roll for both kickoff and return charts
        # Set up charts so roll 11 gives 50 yard kickoff and OFF 15 return
        game.state.home_chart.special_teams.kickoff[11] = "50"
        game.state.away_chart.special_teams.kickoff[11] = "50"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Single roll = 11 used for both kickoff (50 yards) and return (OFF 15)
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15 (receiver's perspective)
            # landing_spot = 100 - (35 + 50) = 15
            # OFF 15 penalty would move ball to 0, but half-the-distance applies
            # Half of 15 = 7, so ball at 15 - 7 = 8
            assert game.state.ball_position == 8
    
    def test_defensive_penalty_on_kickoff_return_moves_ball_forward(self, game):
        """Defensive penalty on kickoff return should move ball forward 15 yards."""
        # Note: Kickoff uses same dice roll for both kickoff and return charts
        # Set up charts so roll 12 gives 50 yard kickoff and DEF 15 return
        game.state.home_chart.special_teams.kickoff[12] = "50"
        game.state.away_chart.special_teams.kickoff[12] = "50"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Single roll = 12 used for both kickoff (50 yards) and return (DEF 15)
            mock_dice.return_value = (12, "B1+W0+W2=12")
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15 (receiver's perspective)
            # landing_spot = 100 - (35 + 50) = 15
            # DEF 15 penalty moves ball forward 15 yards = 15 + 15 = 30
            assert game.state.ball_position == 30
    
    def test_normal_kickoff_return_still_works(self, game):
        """Normal kickoff return without penalty should work correctly."""
        # Note: Kickoff uses same dice roll for both kickoff and return charts
        # Set up charts so roll 10 gives 50 yard kickoff and 20 yard return
        game.state.home_chart.special_teams.kickoff[10] = "50"
        game.state.away_chart.special_teams.kickoff[10] = "50"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Single roll = 10 used for both kickoff (50 yards) and return (20 yards)
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15 (receiver's perspective)
            # landing_spot = 100 - (35 + 50) = 15
            # Return 20 yards = receiver at their 35
            # return_position = 15 + 20 = 35
            assert game.state.ball_position == 35


class TestKickoffDiceDisplay:
    """Tests for kickoff dice display format."""

    def test_kickoff_dice_format_in_description(self, game):
        """Kickoff description should include dice in standard format."""
        game.state.home_chart.special_teams.kickoff[10] = "50"
        game.state.away_chart.special_teams.kickoff[10] = "50"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:10→" in outcome.description
            assert "| RT:10→" in outcome.description

    def test_kickoff_touchback_dice_format(self, game):
        """Kickoff touchback description should include dice in standard format."""
        game.state.home_chart.special_teams.kickoff[12] = "TB"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (12, "B1+W0+W2=12")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:12→" in outcome.description
            assert "Touchback" in outcome.description

    def test_kickoff_out_of_bounds_dice_format(self, game):
        """Kickoff out of bounds description should include dice in standard format."""
        game.state.home_chart.special_teams.kickoff[11] = "OB"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:11→" in outcome.description
            assert "out of bounds" in outcome.description

    def test_kickoff_negative_return_dice_format(self, game):
        """Kickoff with negative return should show negative yards in dice format."""
        game.state.home_chart.special_teams.kickoff[10] = "55"
        game.state.away_chart.special_teams.kickoff[10] = "10"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:10→" in outcome.description
            assert "| RT:10→" in outcome.description

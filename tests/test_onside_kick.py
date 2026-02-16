"""
Tests for onside kick functionality per official Paydirt rules.

Official rules:
- Kicking team recovers if dice total is 13-20 (inclusive)
- Receiving team recovers on any other total
- Ball travels 12 yards, no advance or return
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.interactive_game import cpu_should_onside_kick


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        kickoff={},
        kickoff_return={},
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
            short_name="TST '83",
            power_rating=50,
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


class TestOnsideKickRecovery:
    """Tests for onside kick recovery rules."""
    
    def test_kicking_team_recovers_on_13(self, game):
        """Kicking team should recover on roll of 13."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (13, "B1+W2+W1=13")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "RECOVERED" in outcome.description
            assert game.state.is_home_possession is True  # Kicking team keeps it
    
    def test_kicking_team_recovers_on_20(self, game):
        """Kicking team should recover on roll of 20."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (20, "B2+W4+W5=20")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "RECOVERED" in outcome.description
            assert game.state.is_home_possession is True
    
    def test_kicking_team_recovers_on_16(self, game):
        """Kicking team should recover on roll of 16 (middle of range)."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (16, "B2+W3+W2=16")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "RECOVERED" in outcome.description
            assert game.state.is_home_possession is True
    
    def test_receiving_team_recovers_on_12(self, game):
        """Receiving team should recover on roll of 12 (just below range)."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (12, "B1+W2+W0=12")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "FAILED" in outcome.description
            assert game.state.is_home_possession is False  # Receiving team gets it
    
    def test_receiving_team_recovers_on_21(self, game):
        """Receiving team should recover on roll of 21 (just above range)."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (21, "B2+W5+W5=21")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "FAILED" in outcome.description
            assert game.state.is_home_possession is False
    
    def test_receiving_team_recovers_on_10(self, game):
        """Receiving team should recover on low roll."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "FAILED" in outcome.description
            assert game.state.is_home_possession is False


class TestOnsideKickBallPosition:
    """Tests for ball position after onside kick."""
    
    def test_ball_at_47_when_kicking_team_recovers(self, game):
        """Ball should be at kicking team's 47 when they recover."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (15, "B1+W3+W2=15")
            
            game.onside_kick(kicking_home=True)
            
            # Kicking team recovers at their own 47
            assert game.state.ball_position == 47
            assert game.state.is_home_possession is True
    
    def test_ball_at_53_when_receiving_team_recovers(self, game):
        """Ball should be at receiving team's 53 when they recover."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W1+W0=11")
            
            game.onside_kick(kicking_home=True)
            
            # Receiving team recovers at their own 53 (100 - 47)
            assert game.state.ball_position == 53
            assert game.state.is_home_possession is False
    
    def test_downs_reset_after_onside_kick(self, game):
        """Downs should be 1st and 10 after onside kick."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (15, "B1+W3+W2=15")
            
            game.onside_kick(kicking_home=True)
            
            assert game.state.down == 1
            assert game.state.yards_to_go == 10


class TestOnsideKickAwayTeam:
    """Tests for onside kick when away team is kicking."""
    
    def test_away_team_recovers(self, game):
        """Away team should keep possession when they recover."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W3+W3=17")
            
            outcome = game.onside_kick(kicking_home=False)
            
            assert "RECOVERED" in outcome.description
            assert game.state.is_home_possession is False  # Away team keeps it
    
    def test_home_team_recovers_when_away_kicks(self, game):
        """Home team should get ball when away team's onside fails."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W1+W0=11")
            
            outcome = game.onside_kick(kicking_home=False)
            
            assert "FAILED" in outcome.description
            assert game.state.is_home_possession is True  # Home team gets it


class TestCPUOnsideKickDecision:
    """Tests for CPU decision to attempt onside kick."""
    
    @pytest.fixture
    def mock_game(self):
        """Create a mock game for testing."""
        game = MagicMock(spec=PaydirtGameEngine)
        game.state = MagicMock(spec=GameState)
        game.state.quarter = 4
        game.state.time_remaining = 1.0
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 21
        return game
    
    def test_no_onside_in_early_game(self, mock_game):
        """Should not attempt onside kick in early game."""
        mock_game.state.quarter = 2
        mock_game.state.time_remaining = 10.0
        mock_game.state.home_score = 7
        mock_game.state.away_score = 14
        
        assert cpu_should_onside_kick(mock_game) is False
    
    def test_no_onside_when_winning(self, mock_game):
        """Should not attempt onside kick when winning."""
        mock_game.state.home_score = 21
        mock_game.state.away_score = 14
        
        assert cpu_should_onside_kick(mock_game) is False
    
    def test_onside_when_trailing_under_2_minutes(self, mock_game):
        """Should attempt onside kick when trailing with under 2 minutes."""
        mock_game.state.time_remaining = 1.5
        mock_game.state.home_score = 14
        mock_game.state.away_score = 21  # Down by 7
        
        assert cpu_should_onside_kick(mock_game) is True
    
    def test_onside_when_trailing_big_under_5_minutes(self, mock_game):
        """Should attempt onside kick when down by 2+ scores with under 5 minutes."""
        mock_game.state.time_remaining = 4.0
        mock_game.state.home_score = 7
        mock_game.state.away_score = 21  # Down by 14
        
        assert cpu_should_onside_kick(mock_game) is True
    
    def test_no_onside_when_down_by_one_score_with_time(self, mock_game):
        """Should not attempt onside when down by one score with time left."""
        mock_game.state.time_remaining = 4.0
        mock_game.state.home_score = 14
        mock_game.state.away_score = 21  # Down by 7
        
        assert cpu_should_onside_kick(mock_game) is False
    
    def test_no_onside_in_3rd_quarter(self, mock_game):
        """Should not attempt onside kick in 3rd quarter even if trailing."""
        mock_game.state.quarter = 3
        mock_game.state.time_remaining = 5.0
        mock_game.state.home_score = 7
        mock_game.state.away_score = 21
        
        assert cpu_should_onside_kick(mock_game) is False


class TestOnsideKickDiceDisplay:
    """Tests for onside kick dice display format."""

    def test_onside_kick_recovered_dice_format(self, game):
        """Onside kick recovered description should include dice in standard format."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (15, "B1+W2+W3=15")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "(ON:15→" in outcome.description
            assert "RECOVERED" in outcome.description

    def test_onside_kick_failed_dice_format(self, game):
        """Onside kick failed description should include dice in standard format."""
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (8, "B1+W0+W0=8")
            
            outcome = game.onside_kick(kicking_home=True)
            
            assert "(ON:8→" in outcome.description
            assert "FAILED" in outcome.description

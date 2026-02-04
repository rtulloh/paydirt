"""
Tests for punt handling per official Paydirt rules.

Official rules:
- Roll offensive dice, consult Punt column on punting team's Special Team Chart
- If result has † (downed/out of bounds) or * (fair catch), no return allowed
- Otherwise, receiving team rolls offensive dice and consults Punt Return column
"""
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field

from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with various punt results."""
    return SpecialTeamsChart(
        punt={
            10: "40",      # Normal punt, returnable
            11: "45*",     # Fair catch
            12: "38†",     # Downed/out of bounds
            13: "BK -10",  # Blocked punt
            14: "OFF 10",  # Penalty
            15: "50",      # Long punt, returnable
            16: "65",      # Touchback punt
        },
        punt_return={
            10: "5",       # Short return
            11: "15",      # Medium return
            12: "F",       # Fumble on return
            13: "OFF 10",  # Penalty on return
            14: "25",      # Long return
            15: "0",       # No return
        },
        kickoff={},
        kickoff_return={},
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


class TestPuntBasics:
    """Basic punt functionality tests."""
    
    def test_normal_punt_allows_return(self, game):
        """Normal punt (no markers) should allow a return."""
        game.state.ball_position = 30  # Own 30
        game.state.is_home_possession = True
        
        # Mock dice rolls: punt roll = 10 (40 yards), return roll = 11 (15 yards)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Punt 40 yards from own 30 lands at 70 (opponent's 30)
            # Return 15 yards puts ball at opponent's 45 (our 55)
            assert "returned" in outcome.description.lower() or "15" in outcome.description
    
    def test_fair_catch_no_return(self, game):
        """Punt with * (fair catch) should not allow return."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 11 (45* = fair catch)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "fair catch" in outcome.description.lower()
            # Should only have one dice roll (no return roll)
            assert mock_dice.call_count == 1
    
    def test_downed_punt_no_return(self, game):
        """Punt with † (downed/out of bounds) should not allow return."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 12 (38† = downed)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (12, "B1+W0+W2=12")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "downed" in outcome.description.lower()
            # Should only have one dice roll (no return roll)
            assert mock_dice.call_count == 1


class TestBlockedPunt:
    """Tests for blocked punt handling."""
    
    def test_blocked_punt_defense_recovers(self, game):
        """Blocked punt with defense recovery roll should give ball to defense."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice rolls: punt roll = 13 (BK -10 = blocked), recovery roll = 35 (defense recovers)
        # Per rules, recovery uses fumble ranges: 10-31 = offense recovers, 32-39 = defense recovers
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(13, "B1+W0+W3=13"), (35, "B3+W2+W0=35")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Possession should switch (defense recovers on roll 35)
            assert game.state.is_home_possession is False
    
    def test_blocked_punt_kicking_team_recovers(self, game):
        """Blocked punt with kicking team recovery roll should keep possession."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice rolls: punt roll = 13 (BK -10 = blocked), recovery roll = 20 (kicking team recovers)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(13, "B1+W0+W3=13"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Possession should NOT switch (kicking team recovers on roll 20)
            assert game.state.is_home_possession is True
    
    def test_blocked_punt_safety(self, game):
        """Blocked punt in end zone should be a safety."""
        game.state.ball_position = 5  # Own 5
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Mock dice roll: punt roll = 13 (BK -10 = blocked, goes into end zone)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (13, "B1+W0+W3=13")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Should be a safety (2 points for away team)
            assert game.state.away_score == initial_away_score + 2


class TestTouchback:
    """Tests for touchback on punts."""
    
    def test_punt_into_endzone_touchback(self, game):
        """Punt into end zone should result in touchback at 20."""
        game.state.ball_position = 40  # Own 40
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 16 (65 yards = into end zone)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (16, "B1+W0+W6=16")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "touchback" in outcome.description.lower()
            # Ball should be at receiving team's 20
            assert game.state.ball_position == 20
            # Possession should switch
            assert game.state.is_home_possession is False


class TestPuntReturn:
    """Tests for punt return scenarios."""
    
    def test_return_for_touchdown(self, game):
        """Long punt return should result in touchdown."""
        game.state.ball_position = 70  # Own 70 (opponent's 30)
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Short punt that lands close, then big return
        # Punt 15 yards lands at 85 (opponent's 15)
        # Return needs to go 85+ yards for TD
        game.state.ball_position = 30
        
        # Mock: punt 40 yards from 30 = lands at 70 (opp 30)
        # Return 80 yards = TD
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First call for punt, second for return
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W0+W4=14")]
            
            # Modify return chart to have big return
            game.state.home_chart.special_teams.punt_return[14] = "80"
            game.state.away_chart.special_teams.punt_return[14] = "80"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Should be a touchdown
            assert outcome.touchdown is True or "touchdown" in outcome.description.lower()
    
    def test_fumble_on_return(self, game):
        """Fumble on punt return should give ball back to punting team."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock: punt 40 yards, then fumble on return
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (12, "B1+W0+W2=12")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "fumble" in outcome.description.lower()
            # Punting team should retain possession
            assert game.state.is_home_possession is True


class TestPuntFieldPosition:
    """Tests for correct field position calculations."""
    
    def test_punt_from_own_20(self, game):
        """Punt from own 20 should land at correct spot."""
        game.state.ball_position = 20
        game.state.is_home_possession = True
        
        # Mock: punt 45 yards with fair catch
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")  # 45* fair catch
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Punt 45 from own 20 = lands at 65 = opponent's 35
            # After possession switch, ball at 35
            assert game.state.ball_position == 35
            assert game.state.is_home_possession is False
    
    def test_punt_with_return_field_position(self, game):
        """Punt with return should calculate correct final position."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock: punt 40 yards, return 15 yards
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Punt 40 from own 30 = lands at 70 = opponent's 30
            # Return 15 yards = opponent's 45 = our 55
            # After switch, receiving team at their 45
            assert game.state.ball_position == 45
            assert game.state.is_home_possession is False


class TestPuntDownAndDistance:
    """Tests for down and distance after punt."""
    
    def test_punt_resets_downs(self, game):
        """After punt, receiving team should have 1st and 10."""
        game.state.ball_position = 30
        game.state.down = 4
        game.state.yards_to_go = 15
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")  # Fair catch
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert game.state.down == 1
            assert game.state.yards_to_go == 10
    
    def test_punt_fumble_recovery_resets_downs(self, game):
        """When kicking team recovers fumble on punt return, they should get 1st and 10."""
        game.state.ball_position = 9  # Deep in own territory
        game.state.down = 4
        game.state.yards_to_go = 21
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll: punt 45 yards, second roll: fumble on return
            mock_dice.side_effect = [(15, "B1+W5+W0=15"), (12, "B1+W2+W0=12")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Kicking team recovers fumble - should have 1st and 10
            assert game.state.down == 1
            assert game.state.yards_to_go == 10
            # Kicking team still has possession
            assert game.state.is_home_possession is True
            assert "FUMBLE" in outcome.description


class TestPuntReturnCommentary:
    """Tests for punt return commentary based on return yardage."""
    
    def test_long_return_commentary(self, game):
        """Long punt returns (30+ yards) should have 'What a return!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return 35 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W4+W0=14")]
            
            # Patch the return chart to return 35 yards
            game.state.defense_team.special_teams.punt_return[14] = "35"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "What a return!" in outcome.description
    
    def test_good_return_commentary(self, game):
        """Good punt returns (20-29 yards) should have 'Great return!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return 22 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W4+W0=14")]
            
            # Patch the return chart to return 22 yards
            game.state.defense_team.special_teams.punt_return[14] = "22"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "Great return!" in outcome.description
    
    def test_no_return_coverage_commentary(self, game):
        """No return (0 yards) should have 'Excellent coverage!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return 0 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (15, "B1+W5+W0=15")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "Excellent coverage!" in outcome.description
    
    def test_negative_return_coverage_commentary(self, game):
        """Negative return should have 'Outstanding special teams coverage!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return -5 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W4+W0=14")]
            
            # Patch the return chart to return -5 yards
            game.state.defense_team.special_teams.punt_return[14] = "-5"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "Outstanding special teams coverage!" in outcome.description

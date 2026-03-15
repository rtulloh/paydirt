"""
Test cases for NFL Rule 14-5-1 (the "5 vs 15" rule) for special teams penalties.

This rule states that when both teams commit fouls on a special teams play:
- If one foul is 5 yards and the other is 15 yards (and neither has auto first down):
  Apply only the 15-yard penalty, disregard the 5-yard penalty
- Otherwise: Penalties offset, replay the down
"""

import pytest
from unittest.mock import MagicMock
from paydirt.game_engine import PaydirtGameEngine as GameEngine
from paydirt.models import Team


class TestDoubleFoulPenalty:
    """Test the 5 vs 15 rule for punt and kickoff penalties."""
    
    @pytest.fixture
    def mock_game(self):
        """Create a mock game with basic setup."""
        game = MagicMock(spec=GameEngine)
        game.state = MagicMock()
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 3
        game.state.home_team = Team(name="Home", abbreviation="HOM")
        game.state.away_team = Team(name="Away", abbreviation="AWY")
        return game
    
    def test_five_vs_fifteen_apply_fifteen(self, mock_game):
        """Test 5 vs 15 scenario - should apply 15-yard penalty only."""
        # Setup: DEF 5 on punt chart, OFF 15 on return chart
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=5,
            penalty_a_is_offensive=False,  # DEF penalty on kicking team
            penalty_a_has_auto_fd=False,
            penalty_b_yards=15,
            penalty_b_is_offensive=True,   # OFF penalty on receiving team
            penalty_b_has_auto_fd=False,
            landing_spot=70,  # Punt landed at 70 (receiving team's 30)
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 5",
            return_result="OFF 15"
        )
        
        assert result['action'] == 'apply_15'
        assert result['penalty_yards'] == 15
        assert result['is_offensive']  # 15-yard penalty is on offense (receiving team)
        assert "DEF 5-yard (Kicking Team)" in result['description']
        assert "OFF 15-yard (Return Team)" in result['description']
        assert "NFL Rule 14-5-1" in result['description']
        assert "5-yard penalty is disregarded" in result['description']
        assert "P:14→'DEF 5'" in result['description']
        assert "R:16→'OFF 15'" in result['description']
        # 15-yard penalty enforced from landing spot (70) - 15 = 55
        assert result['final_position'] == 55
    
    def test_five_vs_fifteen_reversed_teams(self, mock_game):
        """Test 5 vs 15 scenario with reversed teams - OFF 5 on punt, DEF 15 on return."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=5,
            penalty_a_is_offensive=True,   # OFF penalty on kicking team
            penalty_a_has_auto_fd=False,
            penalty_b_yards=15,
            penalty_b_is_offensive=False,  # DEF penalty on receiving team
            penalty_b_has_auto_fd=False,
            landing_spot=70,
            punt_roll=22,
            return_roll=35,
            punt_result="OFF 5",
            return_result="DEF 15"
        )
        
        assert result['action'] == 'apply_15'
        assert result['penalty_yards'] == 15
        assert not result['is_offensive']  # 15-yard penalty is on defense (receiving team)
        assert "OFF 5-yard (Kicking Team)" in result['description']
        assert "DEF 15-yard (Return Team)" in result['description']
        # DEF penalty adds yards: 70 + 15 = 85
        assert result['final_position'] == 85
    
    def test_five_x_vs_fifteen_offset(self, mock_game):
        """Test 5X vs 15 scenario - should offset due to auto first down."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=5,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=True,   # X modifier - auto first down
            penalty_b_yards=15,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=False,
            landing_spot=70,
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 5X",
            return_result="OFF 15"
        )
        
        assert result['action'] == 'offset'
        assert result['penalty_yards'] == 0
        assert "OFFSETTING PENALTIES" in result['description']
        assert "Down replayed" in result['description']
    
    def test_five_vs_five_offset(self, mock_game):
        """Test 5 vs 5 scenario - should offset."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=5,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=False,
            penalty_b_yards=5,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=False,
            landing_spot=70,
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 5",
            return_result="OFF 5"
        )
        
        assert result['action'] == 'offset'
        assert "OFFSETTING PENALTIES" in result['description']
    
    def test_fifteen_vs_fifteen_offset(self, mock_game):
        """Test 15 vs 15 scenario - should offset."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=15,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=False,
            penalty_b_yards=15,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=False,
            landing_spot=70,
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 15",
            return_result="OFF 15"
        )
        
        assert result['action'] == 'offset'
        assert "OFFSETTING PENALTIES" in result['description']
    
    def test_ten_vs_fifteen_offset(self, mock_game):
        """Test 10 vs 15 scenario - should offset (not 5 vs 15)."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=10,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=False,
            penalty_b_yards=15,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=False,
            landing_spot=70,
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 10",
            return_result="OFF 15"
        )
        
        assert result['action'] == 'offset'
        assert "OFFSETTING PENALTIES" in result['description']
    
    def test_fifteen_vs_five_apply_fifteen(self, mock_game):
        """Test 15 vs 5 scenario - should apply 15-yard penalty."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=15,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=False,
            penalty_b_yards=5,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=False,
            landing_spot=70,
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 15",
            return_result="OFF 5"
        )
        
        assert result['action'] == 'apply_15'
        assert result['penalty_yards'] == 15
    
    def test_half_the_distance_safety_prevention(self, mock_game):
        """Test that 15-yard penalty from landing spot doesn't result in safety."""
        # Landing spot at 10, 15-yard penalty would put ball at -5 (safety)
        # Should apply half-the-distance instead
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=5,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=False,
            penalty_b_yards=15,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=False,
            landing_spot=10,  # Very close to goal line
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 5",
            return_result="OFF 15"
        )
        
        assert result['action'] == 'apply_15'
        # Half-the-distance from 10 = 5, so ball at 5 (not -5)
        assert result['final_position'] == 5
    
    def test_both_penalties_auto_fd_offset(self, mock_game):
        """Test when both penalties have auto first down - should offset."""
        result = GameEngine._handle_double_foul_penalty(
            mock_game,
            penalty_a_yards=5,
            penalty_a_is_offensive=False,
            penalty_a_has_auto_fd=True,   # X modifier
            penalty_b_yards=15,
            penalty_b_is_offensive=True,
            penalty_b_has_auto_fd=True,   # X modifier (hypothetical)
            landing_spot=70,
            punt_roll=14,
            return_roll=16,
            punt_result="DEF 5X",
            return_result="OFF 15X"
        )
        
        assert result['action'] == 'offset'
        assert "OFFSETTING PENALTIES" in result['description']


class TestPuntDoubleFoulIntegration:
    """Integration tests for punt double foul handling - requires full game setup."""
    
    @pytest.mark.skip(reason="Requires full PaydirtGame setup - tested via unit tests above")
    def test_punt_five_vs_fifteen_enforced(self):
        """Test full punt play with 5 vs 15 penalties."""
        pass
    
    @pytest.mark.skip(reason="Requires full PaydirtGame setup - tested via unit tests above")
    def test_punt_five_vs_five_offset(self):
        """Test full punt play with 5 vs 5 penalties - should offset."""
        pass


class TestKickoffDoubleFoulIntegration:
    """Integration tests for kickoff double foul handling - requires full game setup."""
    
    @pytest.mark.skip(reason="Requires full PaydirtGame setup - tested via unit tests above")
    def test_kickoff_five_vs_fifteen_enforced(self):
        """Test full kickoff play with 5 vs 15 penalties."""
        pass
    
    @pytest.mark.skip(reason="Requires full PaydirtGame setup - tested via unit tests above")
    def test_kickoff_five_vs_five_offset(self):
        """Test full kickoff play with 5 vs 5 penalties - should offset."""
        pass

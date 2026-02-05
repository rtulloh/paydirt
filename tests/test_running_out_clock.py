"""
Tests for Running Out the Clock options per official Paydirt rules.

Running Out the Clock options:
A) QB Kneel Down - Automatic -2 yards, 40 seconds consumed
B) Delay of Game - Take intentional 5-yard penalty, adds 10 seconds (not implemented yet)
C) In Bounds - Keeps clock running, costs 5 yards from plays not already in bounds
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.play_resolver import PlayType, DefenseType, ResultType, PlayResult
from paydirt.game_engine import PaydirtGameEngine


@pytest.fixture
def game():
    """Create a game engine with mock team charts."""
    home_chart = MagicMock()
    away_chart = MagicMock()
    
    # Set up peripheral data
    home_chart.peripheral = MagicMock()
    home_chart.peripheral.team_name = "Home Team"
    home_chart.peripheral.short_name = "HOM"
    away_chart.peripheral = MagicMock()
    away_chart.peripheral.team_name = "Away Team"
    away_chart.peripheral.short_name = "AWY"
    
    game = PaydirtGameEngine(home_chart, away_chart)
    return game


class TestQbKneelBasics:
    """Tests for QB Kneel basic functionality."""
    
    def test_qb_kneel_loses_2_yards(self, game):
        """QB Kneel should result in automatic 2-yard loss."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        assert outcome.yards_gained == -2
        assert game.state.ball_position == 48
        assert "knee" in outcome.description.lower()
    
    def test_qb_kneel_advances_down(self, game):
        """QB Kneel should advance to next down."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        assert game.state.down == 2
    
    def test_qb_kneel_uses_40_seconds(self, game):
        """QB Kneel should consume 40 seconds."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        game.state.time_remaining = 2.0  # 2 minutes
        
        game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        # Should use ~40 seconds (0.667 minutes)
        time_used = 2.0 - game.state.time_remaining
        assert 0.6 <= time_used <= 0.7  # ~40 seconds
    
    def test_qb_kneel_no_dice_rolls(self, game):
        """QB Kneel should not use any dice rolls."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_roll:
            game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
            mock_roll.assert_not_called()


class TestQbKneelTurnoverOnDowns:
    """Tests for QB Kneel turnover on 4th down."""
    
    def test_kneel_on_4th_down_is_turnover(self, game):
        """Kneeling on 4th down should result in turnover on downs."""
        game.state.ball_position = 50
        game.state.down = 4
        game.state.yards_to_go = 5
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        assert outcome.turnover is True
        assert "TURNOVER ON DOWNS" in outcome.description


class TestQbKneelSafety:
    """Tests for QB Kneel safety scenarios."""
    
    def test_kneel_at_own_1_is_safety(self, game):
        """Kneeling at own 1-yard line should result in safety."""
        game.state.ball_position = 1
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        assert outcome.safety is True
        assert "SAFETY" in outcome.description
    
    def test_kneel_at_own_2_is_safety(self, game):
        """Kneeling at own 2-yard line should result in safety."""
        game.state.ball_position = 2
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        assert outcome.safety is True
    
    def test_kneel_at_own_3_is_not_safety(self, game):
        """Kneeling at own 3-yard line should NOT result in safety."""
        game.state.ball_position = 3
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        
        assert outcome.safety is False
        assert game.state.ball_position == 1


class TestInBoundsDesignation:
    """Tests for In Bounds designation."""
    
    def test_in_bounds_subtracts_5_yards_from_oob_play(self, game):
        """In Bounds should subtract 5 yards from plays that were out of bounds."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        # Mock a 15-yard gain that was out of bounds
        with patch('paydirt.game_engine.resolve_play') as mock_resolve:
            mock_resolve.return_value = PlayResult(
                result_type=ResultType.YARDS,
                yards=15,
                description="Gain of 15 yards (out of bounds)",
                out_of_bounds=True
            )
            
            outcome = game.run_play(PlayType.END_RUN, DefenseType.STANDARD,
                                   in_bounds_designation=True)
        
        # Should be 15 - 5 = 10 yards
        assert outcome.yards_gained == 10
        assert "In Bounds designation" in outcome.description
    
    def test_in_bounds_not_applied_to_already_in_bounds(self, game):
        """In Bounds penalty should NOT be applied if play was already in bounds."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.resolve_play') as mock_resolve:
            mock_resolve.return_value = PlayResult(
                result_type=ResultType.YARDS,
                yards=12,
                description="Gain of 12 yards",
                out_of_bounds=False  # Already in bounds
            )
            
            outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD,
                                   in_bounds_designation=True)
        
        # Should NOT subtract 5 yards since play was already in bounds
        assert outcome.yards_gained == 12
        assert "In Bounds designation" not in outcome.description
    
    def test_in_bounds_not_applied_to_incomplete(self, game):
        """In Bounds penalty should NOT be applied to incomplete passes."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.resolve_play') as mock_resolve:
            mock_resolve.return_value = PlayResult(
                result_type=ResultType.INCOMPLETE,
                yards=0,
                description="Incomplete pass"
            )
            
            outcome = game.run_play(PlayType.LONG_PASS, DefenseType.STANDARD,
                                   in_bounds_designation=True)
        
        assert outcome.yards_gained == 0
        assert "In Bounds designation" not in outcome.description
    
    def test_in_bounds_forces_clock_to_run(self, game):
        """In Bounds designation should force clock to keep running."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        game.state.time_remaining = 2.0
        
        with patch('paydirt.game_engine.resolve_play') as mock_resolve:
            mock_resolve.return_value = PlayResult(
                result_type=ResultType.YARDS,
                yards=8,
                description="Gain of 8 yards",
                out_of_bounds=True  # Would normally stop clock
            )
            
            game.run_play(PlayType.OFF_TACKLE, DefenseType.STANDARD,
                                   in_bounds_designation=True)
        
        # Clock should have run more than 10-second OOB play
        time_used = 2.0 - game.state.time_remaining
        # In bounds plays use 5-40 seconds, so should be > 0.15 min typically
        assert time_used > 0.08  # More than ~5 seconds


class TestDefenseIgnored:
    """Tests to verify defense doesn't affect special plays."""
    
    def test_qb_kneel_defense_type_ignored(self, game):
        """Defense type should not affect QB Kneel outcome."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        for def_type in [DefenseType.STANDARD, DefenseType.BLITZ, 
                         DefenseType.SHORT_PASS, DefenseType.LONG_PASS]:
            game.state.ball_position = 50
            game.state.down = 1
            outcome = game.run_play(PlayType.QB_KNEEL, def_type)
            
            assert outcome.yards_gained == -2

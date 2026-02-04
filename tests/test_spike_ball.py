"""
Tests for Spike Ball play per official Paydirt rules.

Spiking the ball:
- Automatic incomplete pass (no dice rolls or charts used)
- Wastes a down but stops the clock
- Combined with previous 40-second play, total time is only 20 seconds
- Avoids the hazards of the quick huddle (no penalty risks)
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.play_resolver import PlayType, DefenseType, ResultType
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.chart_loader import TeamChart


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


class TestSpikeBallBasics:
    """Tests for basic Spike Ball functionality."""
    
    def test_spike_ball_is_incomplete(self, game):
        """Spike ball should result in incomplete pass."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        assert outcome.result.result_type == ResultType.INCOMPLETE
        assert outcome.yards_gained == 0
        assert "spike" in outcome.description.lower()
    
    def test_spike_ball_advances_down(self, game):
        """Spike ball should advance to next down."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        assert game.state.down == 2
        assert game.state.yards_to_go == 10  # Unchanged
    
    def test_spike_ball_no_yardage(self, game):
        """Spike ball should not gain or lose yardage."""
        game.state.ball_position = 50
        game.state.down = 2
        game.state.yards_to_go = 7
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        assert outcome.yards_gained == 0
        assert game.state.ball_position == 50
    
    def test_spike_ball_no_turnover_normally(self, game):
        """Spike ball should not cause turnover on 1st-3rd down."""
        for down in [1, 2, 3]:
            game.state.ball_position = 50
            game.state.down = down
            game.state.yards_to_go = 10
            game.state.is_home_possession = True
            
            outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
            
            assert outcome.turnover is False


class TestSpikeBallTurnoverOnDowns:
    """Tests for Spike Ball turnover on 4th down."""
    
    def test_spike_on_4th_down_is_turnover(self, game):
        """Spiking on 4th down should result in turnover on downs."""
        game.state.ball_position = 50
        game.state.down = 4
        game.state.yards_to_go = 5
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        assert outcome.turnover is True
        assert "TURNOVER ON DOWNS" in outcome.description
        # Possession should change
        assert game.state.is_home_possession is False
    
    def test_spike_on_4th_down_changes_possession(self, game):
        """Spiking on 4th down should change possession."""
        game.state.ball_position = 60
        game.state.down = 4
        game.state.yards_to_go = 3
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        # Defense takes over
        assert game.state.is_home_possession is False
        # Ball position flips for new offense
        assert game.state.ball_position == 40  # 100 - 60


class TestSpikeBallDefenseIgnored:
    """Tests to verify defense doesn't affect spike ball."""
    
    def test_defense_type_ignored(self, game):
        """Defense type should not affect spike ball outcome."""
        game.state.ball_position = 50
        game.state.down = 2
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        # Try different defense types - all should result in same outcome
        for def_type in [DefenseType.STANDARD, DefenseType.BLITZ, 
                         DefenseType.SHORT_PASS, DefenseType.LONG_PASS]:
            game.state.down = 2  # Reset
            outcome = game.run_play(PlayType.SPIKE_BALL, def_type)
            
            assert outcome.result.result_type == ResultType.INCOMPLETE
            assert outcome.yards_gained == 0


class TestSpikeBallTimeSavings:
    """Tests for Spike Ball time mechanics."""
    
    def test_spike_uses_minimal_time(self, game):
        """Spike ball should use minimal game time."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        game.state.time_remaining = 2.0  # 2 minutes
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        # Spike should use very little time (< 0.1 minutes = 6 seconds)
        time_used = 2.0 - game.state.time_remaining
        assert time_used < 0.1
    
    def test_spike_concept_time_savings(self):
        """
        Conceptual test: Spike saves time vs normal plays.
        
        Normal: Play 1 (40 sec) + Play 2 (40 sec) = 80 sec
        With Spike: Play 1 (40 sec) + Spike (reduces to 20 sec total) = 20 sec
        
        Time saved: 60 seconds, but costs a down
        """
        normal_two_plays = 40 + 40  # 80 seconds
        spike_combo = 20  # Previous play + spike = 20 sec total
        
        time_saved = normal_two_plays - spike_combo
        assert time_saved == 60  # Saves 60 seconds


class TestSpikeBallNoRolls:
    """Tests to verify spike ball uses no dice rolls."""
    
    def test_no_dice_rolls_used(self, game):
        """Spike ball should not use any dice rolls."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_roll:
            outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
            
            # roll_chart_dice should NOT be called for spike
            mock_roll.assert_not_called()

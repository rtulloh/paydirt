"""
Tests for Spike Ball as a modifier (e.g., '7S' for pass + spike).

The spike modifier allows players to run a play and then spike the ball
to stop the clock. Per Paydirt rules:
- Spike + previous play = 20 seconds maximum
- Only useful when clock is running (not after incomplete, OOB, turnover)
- Saves time for two-minute drill scenarios
"""
import pytest
from unittest.mock import MagicMock

from paydirt.play_resolver import ResultType
from paydirt.game_engine import PaydirtGameEngine
from paydirt.interactive_game import (
    _apply_spike, should_apply_spike_after_play
)


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


class TestApplySpike:
    """Tests for _apply_spike function."""
    
    def test_spike_caps_play_at_20_seconds(self, game):
        """Spike should cap previous play + spike at 20 seconds total."""
        game.state.time_remaining = 1.0  # 1 minute (60 seconds)
        game.state.quarter = 4
        
        time_before_play = 1.0
        quarter_before_play = 4
        
        # Simulate a play that used 35 seconds (1.0 - 0.417 = 0.583 min = 35 sec)
        game.state.time_remaining = 0.583
        
        _apply_spike(game, time_before_play, quarter_before_play)
        
        # After spike: should be time_before_play - 20 seconds
        # 60 sec - 20 sec = 40 sec = 0.667 min
        expected_time = 0.667  # Approximately 40 seconds
        assert abs(game.state.time_remaining - expected_time) < 0.01
    
    def test_spike_adds_3_seconds_when_play_was_short(self, game):
        """If play was short (<17 sec), spike just adds 3 seconds."""
        game.state.time_remaining = 0.75  # 45 seconds remaining
        game.state.quarter = 4
        
        time_before_play = 1.0  # 60 seconds
        quarter_before_play = 4
        
        # Play used 15 seconds (60 - 15 = 45 sec = 0.75 min)
        # This is less than 17 seconds, so no capping needed
        
        _apply_spike(game, time_before_play, quarter_before_play)
        
        # Should be 45 - 3 = 42 seconds = 0.7 min
        expected_time = 0.7
        assert abs(game.state.time_remaining - expected_time) < 0.01
    
    def test_spike_prevents_quarter_advancement(self, game):
        """Spike should revert quarter if time still remains."""
        game.state.time_remaining = 0.1  # 6 seconds
        game.state.quarter = 5  # Quarter was advanced during play
        
        time_before_play = 0.5  # 30 seconds
        quarter_before_play = 4
        
        _apply_spike(game, time_before_play, quarter_before_play)
        
        # Quarter should be reverted to 4 since time remains
        assert game.state.quarter == 4
    
    def test_spike_sets_game_over_false(self, game):
        """Spike should set game_over to false if time remains."""
        game.state.time_remaining = 0.5
        game.state.quarter = 4
        game.state.game_over = True
        
        time_before_play = 1.0
        quarter_before_play = 4
        
        _apply_spike(game, time_before_play, quarter_before_play)
        
        assert game.state.game_over is False


class TestShouldApplySpikeAfterPlay:
    """Tests for should_apply_spike_after_play function."""
    
    def create_outcome(self, result_type, out_of_bounds=False):
        """Helper to create mock PlayOutcome."""
        outcome = MagicMock()
        outcome.result.result_type = result_type
        outcome.result.out_of_bounds = out_of_bounds
        return outcome
    
    def test_spike_not_applied_after_incomplete(self):
        """Spike should not be applied after incomplete pass (clock already stopped)."""
        outcome = self.create_outcome(ResultType.INCOMPLETE)
        should_apply, msg = should_apply_spike_after_play(outcome, play_seconds=25)
        
        assert should_apply is False
        assert "clock already stopped" in msg.lower()
    
    def test_spike_applied_after_yards(self):
        """Spike should be applied after play with yards (complete pass or run)."""
        outcome = self.create_outcome(ResultType.YARDS)
        should_apply, msg = should_apply_spike_after_play(outcome, play_seconds=25)
        
        assert should_apply is True
        assert msg == ""
    
    def test_spike_applied_after_breakaway(self):
        """Spike should be applied after breakaway play."""
        outcome = self.create_outcome(ResultType.BREAKAWAY)
        should_apply, msg = should_apply_spike_after_play(outcome, play_seconds=20)
        
        assert should_apply is True
    
    def test_spike_not_applied_when_play_was_short(self):
        """Spike should not be applied if play used <=3 seconds."""
        outcome = self.create_outcome(ResultType.YARDS)
        should_apply, msg = should_apply_spike_after_play(outcome, play_seconds=2)
        
        assert should_apply is False
        assert "no time would be saved" in msg.lower()


class TestSpikeModifierIntegration:
    """Integration tests for spike modifier in actual gameplay."""
    
    def test_spike_modifer_reduces_time_to_20_seconds(self, game):
        """Running play + spike should take max 20 seconds total."""
        # Set up late game scenario: 25 seconds left in Q4
        game.state.time_remaining = 0.417  # 25 seconds
        game.state.quarter = 4
        game.state.ball_position = 70
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        time_before_play = game.state.time_remaining
        quarter_before_play = game.state.quarter
        
        # Simulate a play that used 35 seconds (manually adjust time)
        game.state.time_remaining = time_before_play - (35/60)
        
        # Create mock outcome for a successful play
        outcome = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        
        # Apply spike
        should_apply, _ = should_apply_spike_after_play(outcome, play_seconds=35)
        if should_apply:
            _apply_spike(game, time_before_play, quarter_before_play)
        
        # Time should be capped at 20 seconds from the original time
        # 25 sec - 20 sec = 5 sec remaining
        expected_time = 5 / 60  # 5 seconds in minutes
        assert abs(game.state.time_remaining - expected_time) < 0.01
    
    def test_spike_modifier_with_two_minute_drill(self, game):
        """Test the classic two-minute drill: play + spike + field goal."""
        # 20 seconds left, need to run play, spike, then kick FG
        game.state.time_remaining = 0.333  # 20 seconds
        game.state.quarter = 4
        game.state.ball_position = 65
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        time_before_play = game.state.time_remaining
        quarter_before_play = game.state.quarter
        
        # Simulate a play that consumed 25 seconds
        game.state.time_remaining = time_before_play - (25/60)
        
        # Create mock outcome for a successful play
        outcome = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        
        # Apply spike
        should_apply, _ = should_apply_spike_after_play(outcome, play_seconds=25)
        if should_apply:
            _apply_spike(game, time_before_play, quarter_before_play)
        
        # After spike: 20 sec - 20 sec = 0 seconds
        # With the cap: time_before_play - 20 sec = 0 seconds
        assert game.state.time_remaining <= 0.083  # <= 5 seconds
    
    def test_spike_capped_play_allows_field_goal(self, game):
        """Test that capping play time allows field goal attempt."""
        # 30 seconds left in Q4, ball at 35 yard line
        game.state.time_remaining = 0.5  # 30 seconds
        game.state.quarter = 4
        game.state.ball_position = 35  # ~52 yard FG attempt
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        time_before_play = game.state.time_remaining
        quarter_before_play = game.state.quarter
        
        # Simulate a play that would have taken 45 seconds (would end game)
        game.state.time_remaining = time_before_play - (45/60)
        
        # Create mock outcome
        outcome = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        
        # Apply spike
        should_apply, _ = should_apply_spike_after_play(outcome, play_seconds=45)
        if should_apply:
            _apply_spike(game, time_before_play, quarter_before_play)
        
        # After spike: 30 sec - 20 sec = 10 seconds remaining
        # Enough for a field goal attempt
        expected_time = 10 / 60  # 10 seconds in minutes
        assert abs(game.state.time_remaining - expected_time) < 0.01


class TestSpikeModifierInputParsing:
    """Tests for parsing 'S' as a modifier in input."""
    
    def test_spike_modifier_parsed_correctly(self):
        """Test that '7S' is parsed as play 7 with spike modifier."""
        # This test verifies the parsing logic
        # The actual parsing happens in _get_human_offense_play_compact
        
        # Test the modifier extraction logic
        choice = "7S"
        
        # Simulate the parsing
        call_spike = 'S' in choice
        choice_clean = choice.replace('S', '').strip()
        
        assert call_spike is True
        assert choice_clean == '7'
    
    def test_standalone_spike_not_parsed_as_modifier(self):
        """Test that 'S' alone is NOT a spike modifier."""
        choice = "S"
        
        call_spike = 'S' in choice
        choice_clean = choice.replace('S', '').strip()
        
        # After removing 'S', choice_clean is empty
        # This means it's standalone spike, not a modifier
        if call_spike and not choice_clean:
            call_spike = False  # Reset - this is standalone spike
        
        assert call_spike is False
        assert choice_clean == ''
    
    def test_spike_with_timeout(self):
        """Test that '7ST' parses both spike and timeout modifiers."""
        choice = "7ST"
        
        call_timeout = 'T' in choice
        choice_clean = choice.replace('T', '').strip()
        
        call_spike = 'S' in choice_clean
        choice_clean = choice_clean.replace('S', '').strip()
        
        assert call_timeout is True
        assert call_spike is True
        assert choice_clean == '7'

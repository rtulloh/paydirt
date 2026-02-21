"""
Tests for timeout tracking and 2-minute warning per official Paydirt rules.

Timeout rules:
- Each team receives 3 timeouts per half
- Timeouts are called after a play to reduce duration to 10 seconds
- Timeouts reset at halftime

2-minute warning rules:
- If a play begins with more than 2 minutes remaining in a half,
  there must be at least 2 minutes remaining when the following play begins
- This is an official's timeout at the 2-minute warning

Final seconds rules:
- Timeouts can be called when less than 40 seconds remain
- Spike ball can be called when less than 40 seconds remain
- These allow for final plays in close games
"""
import pytest
from unittest.mock import MagicMock

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType, DefenseType


@pytest.fixture
def game():
    """Create a game engine with mock team charts."""
    home_chart = MagicMock()
    away_chart = MagicMock()
    
    home_chart.peripheral = MagicMock()
    home_chart.peripheral.team_name = "Home Team"
    home_chart.peripheral.short_name = "HOM"
    away_chart.peripheral = MagicMock()
    away_chart.peripheral.team_name = "Away Team"
    away_chart.peripheral.short_name = "AWY"
    
    game = PaydirtGameEngine(home_chart, away_chart)
    return game


class TestTimeoutTracking:
    """Tests for timeout tracking."""
    
    def test_initial_timeouts_are_3_each(self, game):
        """Each team should start with 3 timeouts."""
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3
    
    def test_use_home_timeout(self, game):
        """Using home timeout should decrement home timeouts."""
        result = game.state.use_timeout(is_home=True)
        
        assert result is True
        assert game.state.home_timeouts == 2
        assert game.state.away_timeouts == 3
    
    def test_use_away_timeout(self, game):
        """Using away timeout should decrement away timeouts."""
        result = game.state.use_timeout(is_home=False)
        
        assert result is True
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 2
    
    def test_cannot_use_timeout_when_none_remaining(self, game):
        """Should return False when no timeouts remaining."""
        game.state.home_timeouts = 0
        
        result = game.state.use_timeout(is_home=True)
        
        assert result is False
        assert game.state.home_timeouts == 0
    
    def test_offense_timeouts_property(self, game):
        """offense_timeouts should return correct team's timeouts."""
        game.state.home_timeouts = 2
        game.state.away_timeouts = 1
        
        # Home on offense
        game.state.is_home_possession = True
        assert game.state.offense_timeouts == 2
        
        # Away on offense
        game.state.is_home_possession = False
        assert game.state.offense_timeouts == 1
    
    def test_defense_timeouts_property(self, game):
        """defense_timeouts should return correct team's timeouts."""
        game.state.home_timeouts = 2
        game.state.away_timeouts = 1
        
        # Home on offense (away on defense)
        game.state.is_home_possession = True
        assert game.state.defense_timeouts == 1
        
        # Away on offense (home on defense)
        game.state.is_home_possession = False
        assert game.state.defense_timeouts == 2


class TestTimeoutResetAtHalftime:
    """Tests for timeout reset at halftime."""
    
    def test_timeouts_reset_at_halftime(self, game):
        """Timeouts should reset to 3 at start of second half."""
        game.state.home_timeouts = 1
        game.state.away_timeouts = 0
        game.state.two_minute_warning_called = True
        
        game.state.reset_timeouts_for_half()
        
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3
        assert game.state.two_minute_warning_called is False


class TestTwoMinuteWarning:
    """Tests for 2-minute warning."""
    
    def test_two_minute_warning_triggers_in_q2(self, game):
        """2-minute warning should trigger when crossing 2:00 in Q2."""
        game.state.quarter = 2
        game.state.time_remaining = 2.5  # 2:30 remaining
        game.state.two_minute_warning_called = False
        
        # Use 40 seconds (would go to 1:50)
        result = game._use_time(40)
        
        assert result is True  # 2-minute warning triggered
        assert game.state.time_remaining == 2.0  # Clock stops at 2:00
        assert game.state.two_minute_warning_called is True
    
    def test_two_minute_warning_triggers_in_q4(self, game):
        """2-minute warning should trigger when crossing 2:00 in Q4."""
        game.state.quarter = 4
        game.state.time_remaining = 2.5  # 2:30 remaining
        game.state.two_minute_warning_called = False
        
        # Use 40 seconds (would go to 1:50)
        result = game._use_time(40)
        
        assert result is True  # 2-minute warning triggered
        assert game.state.time_remaining == 2.0  # Clock stops at 2:00
        assert game.state.two_minute_warning_called is True
    
    def test_two_minute_warning_does_not_trigger_in_q1(self, game):
        """2-minute warning should NOT trigger in Q1."""
        game.state.quarter = 1
        game.state.time_remaining = 2.5
        game.state.two_minute_warning_called = False
        
        result = game._use_time(40)
        
        assert result is False  # No 2-minute warning
        assert game.state.time_remaining < 2.0  # Clock continues normally
    
    def test_two_minute_warning_does_not_trigger_in_q3(self, game):
        """2-minute warning should NOT trigger in Q3."""
        game.state.quarter = 3
        game.state.time_remaining = 2.5
        game.state.two_minute_warning_called = False
        
        result = game._use_time(40)
        
        assert result is False  # No 2-minute warning
        assert game.state.time_remaining < 2.0  # Clock continues normally
    
    def test_two_minute_warning_only_triggers_once(self, game):
        """2-minute warning should only trigger once per half."""
        game.state.quarter = 2
        game.state.time_remaining = 2.0  # Already at 2:00
        game.state.two_minute_warning_called = True  # Already called
        
        # Use 10 seconds
        result = game._use_time(10)
        
        assert result is False  # No new 2-minute warning
        assert game.state.time_remaining < 2.0  # Clock continues
    
    def test_two_minute_warning_resets_at_halftime(self, game):
        """2-minute warning flag should reset at halftime."""
        game.state.quarter = 2
        game.state.time_remaining = 0.5  # 30 seconds left
        game.state.two_minute_warning_called = True
        
        # End the quarter
        game._use_time(60)  # Use 1 minute
        
        # Should now be Q3
        assert game.state.quarter == 3
        assert game.state.two_minute_warning_called is False
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3


class TestHalftimeKickoff:
    """Tests for halftime kickoff - team that received opening kickoff kicks off to start Q3."""
    
    def test_quarter_advances_to_3_at_halftime(self, game):
        """Quarter should advance from 2 to 3 when Q2 time expires."""
        game.state.quarter = 2
        game.state.time_remaining = 0.5  # 30 seconds left
        
        # End the quarter
        game._use_time(60)  # Use 1 minute
        
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15.0  # Reset to full quarter
    
    def test_halftime_resets_timeouts(self, game):
        """Timeouts should reset to 3 for each team at halftime."""
        game.state.quarter = 2
        game.state.time_remaining = 0.5
        game.state.home_timeouts = 1
        game.state.away_timeouts = 0
        
        # End Q2
        game._use_time(60)
        
        assert game.state.quarter == 3
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3
    
    def test_halftime_kickoff_logic(self):
        """The team that kicked to start the game should receive at halftime."""
        # This tests the logic used in interactive_game.py
        # If home kicked to start (first_half_kicking_home = True),
        # then away kicks to start 2nd half (second_half_kicking_home = False)
        
        first_half_kicking_home = True
        second_half_kicking_home = not first_half_kicking_home
        
        assert second_half_kicking_home is False
        
        # And vice versa
        first_half_kicking_home = False
        second_half_kicking_home = not first_half_kicking_home
        
        assert second_half_kicking_home is True


class TestTwoMinuteWarningDisplay:
    """Tests for 2-minute warning display announcement."""
    
    def test_two_minute_warning_is_official_timeout(self, game):
        """2-minute warning should be an official timeout, not charged to either team."""
        game.state.quarter = 2
        game.state.time_remaining = 2.5
        game.state.home_timeouts = 3
        game.state.away_timeouts = 3
        game.state.two_minute_warning_called = False
        
        # Trigger 2-minute warning
        result = game._use_time(40)
        
        assert result is True  # 2-minute warning triggered
        assert game.state.time_remaining == 2.0  # Clock stops at 2:00
        # Timeouts should NOT be decremented (official timeout)
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3
    
    def test_two_minute_warning_state_tracking_for_display(self, game):
        """State should track 2-minute warning for display purposes."""
        game.state.quarter = 4
        game.state.time_remaining = 2.1
        
        # Before play
        assert game.state.two_minute_warning_called is False
        warning_before = game.state.two_minute_warning_called
        
        # Play that crosses 2:00
        game._use_time(10)  # 6 seconds, crosses 2:00
        
        # After play - can detect the change
        warning_after = game.state.two_minute_warning_called
        
        # Display logic: if not warning_before and warning_after, show announcement
        should_display = not warning_before and warning_after
        assert should_display is True
    
    def test_two_minute_warning_display_not_repeated(self, game):
        """2-minute warning display should not repeat on subsequent plays."""
        game.state.quarter = 2
        game.state.time_remaining = 2.0
        game.state.two_minute_warning_called = True  # Already triggered
        
        warning_before = game.state.two_minute_warning_called
        
        # Another play
        game._use_time(10)
        
        warning_after = game.state.two_minute_warning_called
        
        # Should NOT display again
        should_display = not warning_before and warning_after
        assert should_display is False


class TestFinalSecondsClockManagement:
    """Tests for clock management when less than 40 seconds remain."""
    
    def test_spike_ball_with_10_seconds_remaining(self, game):
        """Spike ball should work with only 10 seconds on clock."""
        game.state.quarter = 4
        game.state.time_remaining = 0.167  # ~10 seconds
        game.state.ball_position = 50
        game.state.down = 2
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        outcome = game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        # Spike should complete successfully
        assert outcome.yards_gained == 0
        assert "spike" in outcome.description.lower()
        # Should still have some time (spike uses ~3 seconds)
        assert game.state.time_remaining >= 0
    
    def test_spike_ball_allows_another_play(self, game):
        """After spike with 10 seconds, there should be time for another play."""
        game.state.quarter = 4
        game.state.time_remaining = 0.167  # ~10 seconds
        game.state.ball_position = 50
        game.state.down = 2
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        # Spike the ball
        game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        
        # Should have time remaining for another play
        assert game.state.time_remaining > 0
        assert game.state.game_over is False
    
    def test_spike_ball_uses_minimal_time(self, game):
        """Spike ball should use less than 5 seconds."""
        game.state.quarter = 4
        game.state.time_remaining = 0.5  # 30 seconds
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        time_before = game.state.time_remaining
        game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        time_used = time_before - game.state.time_remaining
        
        # Spike should use less than 0.1 minutes (6 seconds)
        assert time_used < 0.1
    
    def test_game_allows_play_with_1_second_remaining(self, game):
        """Game should allow a play when there's any time remaining."""
        game.state.quarter = 4
        game.state.time_remaining = 0.017  # ~1 second
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        game.state.game_over = False
        
        # Should be able to run a play (time > 0)
        assert game.state.time_remaining > 0
        assert game.state.game_over is False
    
    def test_timeout_calculation_with_30_seconds(self, game):
        """
        Test timeout time calculation with 30 seconds remaining.
        
        With timeout, play should only use 10 seconds, leaving 20 seconds.
        """
        # This tests the concept - actual implementation is in interactive_game.py
        time_before = 0.5  # 30 seconds
        timeout_play_time = 0.167  # 10 seconds
        
        time_after = time_before - timeout_play_time
        
        # Should have ~20 seconds remaining
        assert time_after > 0.3  # More than 18 seconds
        assert time_after < 0.4  # Less than 24 seconds
    
    def test_multiple_spikes_possible(self, game):
        """Should be able to spike multiple times if downs allow."""
        game.state.quarter = 4
        game.state.time_remaining = 0.5  # 30 seconds
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        # Spike 1
        game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        assert game.state.down == 2
        assert game.state.time_remaining > 0.4  # Still have ~25+ seconds
        
        # Spike 2
        game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        assert game.state.down == 3
        assert game.state.time_remaining > 0.3  # Still have ~20+ seconds
        
        # Spike 3
        game.run_play(PlayType.SPIKE_BALL, DefenseType.STANDARD)
        assert game.state.down == 4
        assert game.state.time_remaining > 0.2  # Still have ~15+ seconds
    
    def test_hail_mary_available_at_end_of_game(self, game):
        """Hail Mary should be available at end of half/game."""
        game.state.quarter = 4
        game.state.time_remaining = 0.1  # ~6 seconds
        game.state.ball_position = 60  # At opponent's 40
        game.state.down = 4
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        # Hail Mary should be runnable
        outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.LONG_PASS)
        
        # Play should complete (result varies based on dice)
        assert outcome is not None
        assert outcome.play_type == PlayType.HAIL_MARY


class TestSubSecondClockClamping:
    """Tests for sub-second clock residual clamping.

    When _use_time() consumes most of the remaining time but leaves less than
    1 second (0.0167 minutes), the residual displays as 0:00 but is technically
    > 0, preventing the quarter from advancing. The fix clamps any residual
    under 1 second to 0 so the quarter-end logic triggers correctly.
    """

    def test_sub_second_residual_clamped_to_zero_q2(self, game):
        """Sub-second residual in Q2 should be clamped to 0 and quarter should advance."""
        game.state.quarter = 2
        # 10 seconds remaining = 0.1667 minutes
        game.state.time_remaining = 10 / 60.0
        game.state.two_minute_warning_called = True

        # Use 9.5 seconds - leaves ~0.5 seconds which is < 1 second threshold
        game._use_time(9.5)

        # Should have advanced to Q3 (sub-second residual clamped to 0)
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15.0

    def test_sub_second_residual_clamped_to_zero_q1(self, game):
        """Sub-second residual in Q1 should be clamped to 0 and quarter should advance."""
        game.state.quarter = 1
        game.state.time_remaining = 5 / 60.0  # 5 seconds

        # Use 4.5 seconds - leaves ~0.5 seconds
        game._use_time(4.5)

        assert game.state.quarter == 2
        assert game.state.time_remaining == 15.0

    def test_sub_second_residual_clamped_to_zero_q3(self, game):
        """Sub-second residual in Q3 should be clamped to 0 and quarter should advance."""
        game.state.quarter = 3
        game.state.time_remaining = 8 / 60.0  # 8 seconds

        # Use 7.5 seconds
        game._use_time(7.5)

        assert game.state.quarter == 4
        assert game.state.time_remaining == 15.0

    def test_sub_second_residual_clamped_to_zero_q4(self, game):
        """Sub-second residual in Q4 should be clamped to 0 and trigger game end."""
        game.state.quarter = 4
        game.state.time_remaining = 6 / 60.0  # 6 seconds
        game.state.home_score = 14
        game.state.away_score = 7  # Not tied

        # Use 5.5 seconds
        game._use_time(5.5)

        assert game.state.time_remaining == 0
        assert game.state.game_over is True

    def test_more_than_one_second_not_clamped(self, game):
        """Time remaining > 1 second should NOT be clamped."""
        game.state.quarter = 2
        game.state.time_remaining = 10 / 60.0  # 10 seconds
        game.state.two_minute_warning_called = True

        # Use 7 seconds - leaves 3 seconds (> 1 second threshold)
        game._use_time(7)

        # Should still be in Q2 with ~3 seconds
        assert game.state.quarter == 2
        assert game.state.time_remaining > 0.0167  # More than 1 second

    def test_exact_zero_still_advances_quarter(self, game):
        """Time going to exactly 0 should still advance the quarter."""
        game.state.quarter = 2
        game.state.time_remaining = 10 / 60.0
        game.state.two_minute_warning_called = True

        # Use exactly 10 seconds
        game._use_time(10)

        assert game.state.quarter == 3
        assert game.state.time_remaining == 15.0

    def test_halftime_timeouts_reset_on_sub_second_clamp(self, game):
        """Halftime timeout reset should work when sub-second clamp triggers Q2→Q3."""
        game.state.quarter = 2
        game.state.time_remaining = 6 / 60.0  # 6 seconds
        game.state.two_minute_warning_called = True
        game.state.home_timeouts = 1
        game.state.away_timeouts = 0

        # Use 5.5 seconds - triggers sub-second clamp and Q2→Q3
        game._use_time(5.5)

        assert game.state.quarter == 3
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3

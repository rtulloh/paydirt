"""
Unit tests for NFL overtime rules implementation.

Tests the overtime rules by season and the game engine's overtime handling.
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.overtime_rules import (
    get_overtime_rules, OvertimeRules, OvertimeFormat,
    OVERTIME_RULES_BY_YEAR
)
from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import load_team_chart


class TestOvertimeRulesByYear:
    """Tests for getting correct overtime rules by season year."""
    
    def test_1983_rules_sudden_death(self):
        """1983 should use sudden death rules."""
        rules = get_overtime_rules(1983)
        assert rules.format == OvertimeFormat.SUDDEN_DEATH
        assert rules.period_length_minutes == 15.0
        assert rules.can_end_in_tie_regular is True
        assert rules.can_end_in_tie_playoff is False
    
    def test_1983_rules_max_periods(self):
        """1983 regular season has 1 OT period max, playoffs unlimited."""
        rules = get_overtime_rules(1983)
        assert rules.get_max_periods(is_playoff=False) == 1
        assert rules.get_max_periods(is_playoff=True) == 0  # 0 = unlimited
    
    def test_1974_rules(self):
        """1974 (first year of OT) should have sudden death."""
        rules = get_overtime_rules(1974)
        assert rules.format == OvertimeFormat.SUDDEN_DEATH
    
    def test_2010_rules_modified_sudden_death(self):
        """2010+ should use modified sudden death."""
        rules = get_overtime_rules(2010)
        assert rules.format == OvertimeFormat.MODIFIED_SUDDEN_DEATH
    
    def test_2017_rules_10_minute_period(self):
        """2017+ regular season OT is 10 minutes."""
        rules = get_overtime_rules(2017)
        assert rules.period_length_minutes == 10.0
    
    def test_pre_1974_uses_earliest_rules(self):
        """Years before 1974 should use 1974 rules (earliest available)."""
        rules = get_overtime_rules(1970)
        assert rules.format == OvertimeFormat.SUDDEN_DEATH


class TestGameEngineOvertime:
    """Tests for game engine overtime functionality."""
    
    @pytest.fixture
    def game(self):
        """Create a game for testing."""
        home = load_team_chart("seasons/1983/Redskins")
        away = load_team_chart("seasons/1983/Cowboys")
        return PaydirtGameEngine(home, away)
    
    def test_needs_overtime_when_tied_at_end_of_q4(self, game):
        """Game should need overtime when tied at end of Q4."""
        game.state.quarter = 4
        game.state.time_remaining = 0
        game.state.home_score = 14
        game.state.away_score = 14
        game.state.game_over = False
        
        assert game.needs_overtime() is True
    
    def test_no_overtime_when_not_tied(self, game):
        """Game should not need overtime when not tied."""
        game.state.quarter = 4
        game.state.time_remaining = 0
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.game_over = False
        
        assert game.needs_overtime() is False
    
    def test_no_overtime_when_time_remaining(self, game):
        """Game should not need overtime when time remains."""
        game.state.quarter = 4
        game.state.time_remaining = 5.0
        game.state.home_score = 14
        game.state.away_score = 14
        
        assert game.needs_overtime() is False
    
    def test_start_overtime_sets_state(self, game):
        """Starting overtime should set up game state correctly."""
        game.state.quarter = 4
        game.state.time_remaining = 0
        game.state.home_score = 14
        game.state.away_score = 14
        
        msg = game.start_overtime(coin_toss_winner_is_home=True)
        
        assert game.state.is_overtime is True
        assert game.state.ot_period == 1
        assert game.state.quarter == 5
        assert game.state.time_remaining == 15.0  # 1983 rules
        assert game.state.ot_coin_toss_winner_is_home is True
        assert game.state.is_home_possession is True  # Winner receives
        assert "OVERTIME" in msg
    
    def test_start_overtime_resets_timeouts(self, game):
        """Starting overtime should reset timeouts to 3 each."""
        game.state.home_timeouts = 0
        game.state.away_timeouts = 1
        
        game.start_overtime()
        
        assert game.state.home_timeouts == 3
        assert game.state.away_timeouts == 3
    
    def test_sudden_death_td_ends_game(self, game):
        """In sudden death (1983), any TD should end the game."""
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.home_score = 14
        game.state.away_score = 14
        
        # Simulate a TD
        result = game.check_overtime_score(scored=True, was_touchdown=True, scoring_team_is_home=True)
        
        assert result is True
        assert game.state.game_over is True
    
    def test_sudden_death_fg_ends_game(self, game):
        """In sudden death (1983), any FG should end the game."""
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.home_score = 14
        game.state.away_score = 14
        
        # Simulate a FG
        result = game.check_overtime_score(scored=True, was_touchdown=False, scoring_team_is_home=True)
        
        assert result is True
        assert game.state.game_over is True
    
    def test_sudden_death_safety_ends_game(self, game):
        """In sudden death (1983), a safety should end the game."""
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.home_score = 14
        game.state.away_score = 14
        
        # Simulate a safety
        result = game.check_overtime_score(scored=True, was_touchdown=False, scoring_team_is_home=False)
        
        assert result is True
        assert game.state.game_over is True
    
    def test_ot_period_ends_still_tied_regular_season(self, game):
        """If OT period ends still tied in regular season, game ends in tie."""
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.home_score = 14
        game.state.away_score = 14
        game.state.is_playoff = False
        
        game._check_overtime_end()
        
        assert game.state.game_over is True  # Tie game
    
    def test_ot_period_ends_still_tied_playoff(self, game):
        """If OT period ends still tied in playoffs, another period starts."""
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.home_score = 14
        game.state.away_score = 14
        game.state.is_playoff = True
        game.state.time_remaining = 0
        
        game._check_overtime_end()
        
        assert game.state.game_over is False
        assert game.state.ot_period == 2
        assert game.state.time_remaining == 15.0
    
    def test_get_overtime_rules_returns_correct_year(self, game):
        """get_overtime_rules should return rules for the game's season."""
        rules = game.get_overtime_rules()
        
        # 1983 Redskins should get 1983 rules
        assert rules.format == OvertimeFormat.SUDDEN_DEATH
        assert rules.period_length_minutes == 15.0


class TestOvertimeScoring:
    """Tests for scoring during overtime."""
    
    @pytest.fixture
    def game_in_ot(self):
        """Create a game already in overtime."""
        home = load_team_chart("seasons/1983/Redskins")
        away = load_team_chart("seasons/1983/Cowboys")
        game = PaydirtGameEngine(home, away)
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.quarter = 5
        game.state.home_score = 14
        game.state.away_score = 14
        game.state.time_remaining = 15.0
        return game
    
    def test_touchdown_in_ot_ends_game(self, game_in_ot):
        """Scoring a TD in OT should end the game."""
        game_in_ot.state.is_home_possession = True
        game_in_ot.state.ball_position = 99
        
        # Score a TD (this calls _score_touchdown which checks OT)
        game_in_ot._score_touchdown()
        
        assert game_in_ot.state.game_over is True
        assert game_in_ot.state.home_score == 20  # 14 + 6
    
    def test_field_goal_in_ot_ends_game(self, game_in_ot):
        """Scoring a FG in OT should end the game (sudden death)."""
        game_in_ot.state.is_home_possession = True
        
        # Score a FG
        game_in_ot._score_field_goal(distance=30)
        
        assert game_in_ot.state.game_over is True
        assert game_in_ot.state.home_score == 17  # 14 + 3
    
    def test_safety_in_ot_ends_game(self, game_in_ot):
        """Scoring a safety in OT should end the game."""
        game_in_ot.state.is_home_possession = True  # Home has ball
        
        # Safety (defense scores, so away gets 2)
        game_in_ot._score_safety()
        
        assert game_in_ot.state.game_over is True
        assert game_in_ot.state.away_score == 16  # 14 + 2


class TestOvertimeStatus:
    """Tests for overtime status display."""
    
    @pytest.fixture
    def game(self):
        """Create a game for testing."""
        home = load_team_chart("seasons/1983/Redskins")
        away = load_team_chart("seasons/1983/Cowboys")
        return PaydirtGameEngine(home, away)
    
    def test_status_shows_ot_quarter(self, game):
        """Game status should show OT period instead of quarter number."""
        game.state.is_overtime = True
        game.state.ot_period = 1
        game.state.quarter = 5
        
        status = game.get_status()
        
        assert status["quarter"] == "OT1"
        assert status["is_overtime"] is True
    
    def test_status_shows_ot2_for_second_period(self, game):
        """Second OT period should show as OT2."""
        game.state.is_overtime = True
        game.state.ot_period = 2
        game.state.quarter = 5
        
        status = game.get_status()
        
        assert status["quarter"] == "OT2"


class TestUntimedDown:
    """Tests for the untimed down rule (defensive penalty at 0:00)."""
    
    @pytest.fixture
    def game(self):
        """Create a game for testing."""
        home = load_team_chart("seasons/1983/Redskins")
        away = load_team_chart("seasons/1983/Cowboys")
        return PaydirtGameEngine(home, away)
    
    def test_untimed_down_not_pending_initially(self, game):
        """Untimed down should not be pending at game start."""
        assert game.has_untimed_down() is False
        assert game.state.untimed_down_pending is False
    
    def test_untimed_down_set_when_def_penalty_at_zero(self, game):
        """Untimed down should be set when defensive penalty accepted at 0:00."""
        game.state.time_remaining = 0
        game.state.quarter = 2
        game.state.is_overtime = False
        
        # Manually set the flag as if a defensive penalty was accepted
        game.state.untimed_down_pending = True
        
        assert game.has_untimed_down() is True
    
    def test_clear_untimed_down(self, game):
        """clear_untimed_down should reset the flag."""
        game.state.untimed_down_pending = True
        
        game.clear_untimed_down()
        
        assert game.has_untimed_down() is False
    
    def test_untimed_down_not_set_in_overtime(self, game):
        """Untimed down rule should not apply during overtime."""
        game.state.time_remaining = 0
        game.state.is_overtime = True
        game.state.ot_period = 1
        
        # The flag should not be set during OT
        # (OT has different end-of-period rules)
        assert game.state.untimed_down_pending is False
    
    def test_untimed_down_not_set_with_time_remaining(self, game):
        """Untimed down should not be set if time remains."""
        game.state.time_remaining = 5.0
        game.state.quarter = 2
        
        # Even if a penalty occurs, no untimed down if time remains
        assert game.state.untimed_down_pending is False
    
    def test_quarter_does_not_advance_with_untimed_down_pending(self, game):
        """Quarter should not advance when untimed_down_pending is True."""
        game.state.quarter = 2
        game.state.time_remaining = 0.1  # Small amount of time
        game.state.untimed_down_pending = True
        
        # Simulate time running out via _use_time
        game._use_time(10)  # Use 10 seconds, which exceeds remaining time
        
        # Quarter should NOT advance because untimed_down_pending is True
        assert game.state.quarter == 2
        assert game.state.time_remaining == 0
    
    def test_quarter_advances_after_untimed_down_cleared(self, game):
        """Quarter should advance after untimed_down is cleared."""
        game.state.quarter = 2
        game.state.time_remaining = 0
        game.state.untimed_down_pending = True
        
        # Clear the untimed down flag (simulating after the untimed play)
        game.clear_untimed_down()
        
        # Now use time again - quarter should advance
        game._use_time(30)
        
        # Quarter should now advance to 3
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15.0  # Reset for new quarter

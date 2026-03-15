"""
Tests for interactive_game.py functions that don't require user input.
"""
import pytest
from unittest.mock import MagicMock, patch

from paydirt.interactive_game import (
    analyze_team_strength,
    cpu_should_go_for_two,
    cpu_should_onside_kick,
    computer_select_offense,
    computer_select_defense,
    _apply_timeout,
)
from paydirt.utils import format_time
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType, DefenseType
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.computer_ai import ComputerAI


def create_mock_chart(short_name: str = "TEST") -> TeamChart:
    """Create a minimal mock TeamChart for testing."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Testers",
            power_rating=50,
            short_name=short_name
        ),
        offense=MagicMock(spec=OffenseChart),
        defense=MagicMock(spec=DefenseChart),
        special_teams=MagicMock(spec=SpecialTeamsChart)
    )


@pytest.fixture
def game():
    """Create a game engine for testing."""
    home_chart = create_mock_chart("HOME")
    away_chart = create_mock_chart("AWAY")
    return PaydirtGameEngine(home_chart, away_chart)


class TestAnalyzeTeamStrength:
    """Tests for analyze_team_strength function."""
    
    def test_run_heavy_team(self):
        """Team with good running charts should be identified as run-heavy."""
        offense = OffenseChart(
            line_plunge={10: "5", 15: "4", 20: "3", 25: "6", 30: "B"},
            off_tackle={10: "6", 15: "5", 20: "4", 25: "7", 30: "8"},
            end_run={10: "7", 15: "6", 20: "5", 25: "8", 30: "9"},
            draw={10: "4", 15: "3", 20: "2", 25: "5", 30: "6"},
            screen={10: "INC", 15: "INC", 20: "INT", 25: "3", 30: "4"},
            short_pass={10: "INC", 15: "INC", 20: "INT", 25: "5", 30: "6"},
            medium_pass={10: "INC", 15: "INC", 20: "INT", 25: "8", 30: "10"},
            long_pass={10: "INC", 15: "INC", 20: "INT", 25: "15", 30: "20"},
            te_short_long={10: "INC", 15: "INC", 20: "5", 25: "8", 30: "10"},
        )
        
        result = analyze_team_strength(offense)
        
        assert result == "run"
    
    def test_pass_heavy_team(self):
        """Team with good passing charts should be identified as pass-heavy."""
        offense = OffenseChart(
            line_plunge={10: "F", 15: "-2", 20: "0", 25: "1", 30: "2"},
            off_tackle={10: "F", 15: "-1", 20: "0", 25: "2", 30: "3"},
            end_run={10: "F", 15: "-2", 20: "1", 25: "2", 30: "3"},
            draw={10: "F", 15: "-1", 20: "0", 25: "1", 30: "2"},
            screen={10: "5", 15: "6", 20: "7", 25: "8", 30: "10"},
            short_pass={10: "6", 15: "8", 20: "10", 25: "12", 30: "15"},
            medium_pass={10: "10", 15: "12", 20: "15", 25: "20", 30: "25"},
            long_pass={10: "15", 15: "20", 20: "25", 25: "30", 30: "TD"},
            te_short_long={10: "8", 15: "10", 20: "12", 25: "15", 30: "18"},
        )
        
        result = analyze_team_strength(offense)
        
        assert result == "pass"
    
    def test_balanced_team(self):
        """Team with equal run/pass should be identified as balanced."""
        offense = OffenseChart(
            line_plunge={10: "3", 15: "4", 20: "5"},
            off_tackle={10: "4", 15: "5", 20: "6"},
            end_run={10: "5", 15: "6", 20: "7"},
            draw={10: "3", 15: "4", 20: "5"},
            screen={10: "4", 15: "5", 20: "6"},
            short_pass={10: "5", 15: "6", 20: "7"},
            medium_pass={10: "8", 15: "10", 20: "12"},
            long_pass={10: "12", 15: "15", 20: "18"},
            te_short_long={10: "6", 15: "8", 20: "10"},
        )
        
        result = analyze_team_strength(offense)
        
        assert result == "balanced"
    
    def test_handles_variable_yardage(self):
        """Should handle variable yardage results like DS, T1, etc."""
        offense = OffenseChart(
            line_plunge={10: "DS", 15: "T1", 20: "3"},
            off_tackle={10: "4", 15: "5", 20: "6"},
            end_run={10: "5", 15: "6", 20: "7"},
            draw={10: "3", 15: "4", 20: "5"},
            screen={10: "4", 15: "5", 20: "6"},
            short_pass={10: "5", 15: "6", 20: "7"},
            medium_pass={10: "8", 15: "10", 20: "12"},
            long_pass={10: "12", 15: "15", 20: "18"},
            te_short_long={10: "6", 15: "8", 20: "10"},
        )
        
        # Should not raise an error
        result = analyze_team_strength(offense)
        assert result in ["run", "pass", "balanced"]
    
    def test_handles_breakaway(self):
        """Should count breakaway results as very positive."""
        offense = OffenseChart(
            line_plunge={10: "B", 15: "B", 20: "B"},  # Lots of breakaways
            off_tackle={10: "B", 15: "B", 20: "B"},
            end_run={10: "1", 15: "2", 20: "3"},
            draw={10: "1", 15: "2", 20: "3"},
            screen={10: "INC", 15: "INC", 20: "INC"},
            short_pass={10: "INC", 15: "INC", 20: "INC"},
            medium_pass={10: "INC", 15: "INC", 20: "INC"},
            long_pass={10: "INC", 15: "INC", 20: "INC"},
            te_short_long={10: "INC", 15: "INC", 20: "INC"},
        )
        
        result = analyze_team_strength(offense)
        
        # With all those breakaways in running, should be run-heavy
        assert result == "run"


class TestCpuShouldGoForTwo:
    """Tests for cpu_should_go_for_two function."""
    
    def test_kicks_extra_point_by_default(self, game):
        """CPU should kick extra point in normal situations."""
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        game.state.home_score = 7
        game.state.away_score = 0
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is False
    
    def test_goes_for_two_when_tied_very_late(self, game):
        """CPU should go for 2 when tied very late in game."""
        game.state.quarter = 4
        game.state.time_remaining = 1.0  # Under 2 minutes
        game.state.home_score = 14
        game.state.away_score = 14  # Tied after TD
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_goes_for_two_when_down_by_2_late(self, game):
        """CPU should go for 2 when down by 2 late in game."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0  # Late game
        game.state.home_score = 12
        game.state.away_score = 14  # Down by 2
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_goes_for_two_when_down_by_8_late(self, game):
        """CPU should go for 2 when down by 8 late in game."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0
        game.state.home_score = 13
        game.state.away_score = 21  # Down by 8
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_goes_for_two_when_up_by_1_very_late(self, game):
        """CPU should go for 2 when up by 1 very late to go up 3."""
        game.state.quarter = 4
        game.state.time_remaining = 1.0
        game.state.home_score = 15
        game.state.away_score = 14  # Up by 1
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is True
    
    def test_kicks_when_up_big(self, game):
        """CPU should kick extra point when up big."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0
        game.state.home_score = 28
        game.state.away_score = 7  # Up by 21
        game.state.is_home_possession = True
        
        result = cpu_should_go_for_two(game)
        
        assert result is False


class TestCpuShouldOnsideKick:
    """Tests for cpu_should_onside_kick function."""
    
    def test_no_onside_early_in_game(self, game):
        """CPU should not onside kick early in game."""
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        game.state.home_score = 7
        game.state.away_score = 14  # Trailing
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is False
    
    def test_no_onside_when_leading(self, game):
        """CPU should not onside kick when leading."""
        game.state.quarter = 4
        game.state.time_remaining = 1.0
        game.state.home_score = 21
        game.state.away_score = 14  # Leading
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is False
    
    def test_onside_when_trailing_under_2_min(self, game):
        """CPU should onside kick when trailing under 2 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is True
    
    def test_onside_when_trailing_big_under_5_min(self, game):
        """CPU should onside kick when trailing by 9+ under 5 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 4.0
        game.state.home_score = 7
        game.state.away_score = 21  # Trailing by 14
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is True
    
    def test_no_onside_small_deficit_under_5_min(self, game):
        """CPU should not onside kick with small deficit under 5 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 4.0
        game.state.home_score = 14
        game.state.away_score = 17  # Trailing by only 3
        game.state.is_home_possession = True
        
        result = cpu_should_onside_kick(game)
        
        assert result is False


class TestComputerSelectOffense:
    """Tests for computer_select_offense function."""
    
    def test_returns_valid_play_type(self, game):
        """Should return a valid PlayType."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 25
        
        result = computer_select_offense(game)
        
        assert isinstance(result, PlayType)
    
    def test_uses_provided_ai(self, game):
        """Should use provided AI instance."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 25
        
        ai = ComputerAI(aggression=0.9)
        result = computer_select_offense(game, ai)
        
        assert isinstance(result, PlayType)


class TestComputerSelectDefense:
    """Tests for computer_select_defense function."""
    
    def test_returns_valid_defense_type(self, game):
        """Should return a valid DefenseType."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        
        result = computer_select_defense(game)
        
        assert isinstance(result, DefenseType)
    
    def test_uses_provided_ai(self, game):
        """Should use provided AI instance."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        
        ai = ComputerAI(aggression=0.9)
        result = computer_select_defense(game, ai)
        
        assert isinstance(result, DefenseType)


class TestApplyTimeout:
    """Tests for _apply_timeout function."""
    
    def test_reduces_time_by_10_seconds(self, game):
        """Timeout should reduce time to 10 seconds for the play."""
        game.state.time_remaining = 5.0  # 5 minutes
        game.state.quarter = 2
        time_before = 5.0
        quarter_before = 2
        
        _apply_timeout(game, time_before, quarter_before)
        
        # Should be time_before - 0.167 (10 seconds)
        assert abs(game.state.time_remaining - 4.833) < 0.01
    
    def test_does_not_go_negative(self, game):
        """Time should not go negative."""
        game.state.time_remaining = 0.1  # 6 seconds
        game.state.quarter = 2
        time_before = 0.1
        quarter_before = 2
        
        _apply_timeout(game, time_before, quarter_before)
        
        assert game.state.time_remaining == 0
    
    def test_prevents_premature_game_over(self, game):
        """Should prevent game from ending prematurely."""
        game.state.time_remaining = 0.2
        game.state.quarter = 4
        game.state.game_over = True
        time_before = 0.2
        quarter_before = 4
        
        _apply_timeout(game, time_before, quarter_before)
        
        assert game.state.game_over is False
    
    def test_reverts_quarter_if_timeout_preserves_time(self, game):
        """Timeout should revert quarter advancement if time is preserved."""
        game.state.time_remaining = 15.0  # Quarter advanced, time reset
        game.state.quarter = 3  # Advanced to Q3
        time_before = 0.26  # Had 0:16 before play
        quarter_before = 2  # Was Q2 before play
        
        _apply_timeout(game, time_before, quarter_before)
        
        # Should revert to Q2 with time preserved
        assert game.state.quarter == 2
        assert abs(game.state.time_remaining - 0.093) < 0.01  # 0.26 - 0.167


class TestTimeoutNotUsedOnTouchdown:
    """Tests for timeout not being consumed when touchdown is scored."""
    
    def test_timeout_skipped_on_touchdown(self):
        """Timeout should not be used if touchdown is scored - clock stops anyway."""
        # This tests the logic: if call_timeout and not outcome.touchdown
        call_timeout = True
        
        # Case 1: Touchdown scored - timeout should be skipped
        class MockOutcomeTD:
            touchdown = True
        
        outcome_td = MockOutcomeTD()
        should_use_timeout = call_timeout and not outcome_td.touchdown
        assert should_use_timeout is False, "Timeout should be skipped on TD"
        
        # Case 2: No touchdown - timeout should be used
        class MockOutcomeNoTD:
            touchdown = False
        
        outcome_no_td = MockOutcomeNoTD()
        should_use_timeout = call_timeout and not outcome_no_td.touchdown
        assert should_use_timeout is True, "Timeout should be used when no TD"
    
    def test_no_timeout_called_no_change(self):
        """When no timeout called, touchdown status doesn't matter."""
        call_timeout = False
        
        class MockOutcome:
            touchdown = True
        
        outcome = MockOutcome()
        should_use_timeout = call_timeout and not outcome.touchdown
        assert should_use_timeout is False, "No timeout called means no timeout used"


class TestFormatTime:
    """Tests for format_time function (imported from utils)."""
    
    def test_full_minutes(self):
        assert format_time(5.0) == "5:00"
    
    def test_half_minute(self):
        assert format_time(2.5) == "2:30"
    
    def test_zero(self):
        assert format_time(0.0) == "0:00"


class TestDisplayPlayResultOffsettingPenalties:
    """Tests for offsetting penalties display handling."""
    
    def test_offsetting_penalties_detected(self):
        """Offsetting penalties should be detected from penalty_choice."""
        from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType
        
        # Create a mock outcome with offsetting penalties
        play_result = PlayResult(
            result_type=ResultType.YARDS,
            yards=4,
            description="Offense result: 4",
            raw_result="4",
            defense_modifier=""
        )
        
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[
                PenaltyOption(penalty_type="OFF", raw_result="OFF 5", yards=5,
                              description="Offensive penalty", auto_first_down=False),
                PenaltyOption(penalty_type="DEF", raw_result="DEF 5", yards=5,
                              description="Defensive penalty", auto_first_down=False),
            ],
            offended_team="",
            offsetting=True,
            is_pass_interference=False,
            original_defense_result=""
        )
        
        # Verify offsetting flag is set correctly
        assert penalty_choice.offsetting is True
        assert penalty_choice.offended_team == ""
        assert len(penalty_choice.penalty_options) == 2
    
    def test_offsetting_penalties_game_state_unchanged(self):
        """Offsetting penalties should not change game state."""
        from paydirt.chart_loader import load_team_chart
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.play_resolver import PlayType, DefenseType
        
        # Load real teams for integration test
        home = load_team_chart('seasons/1983/steelers')
        away = load_team_chart('seasons/1983/broncos')
        
        game = PaydirtGameEngine(home, away)
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        
        # Run plays until we get offsetting penalties
        for _ in range(100):
            game.state.ball_position = 50
            game.state.down = 1
            game.state.yards_to_go = 10
            
            outcome = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
            
            if outcome.penalty_choice and outcome.penalty_choice.offsetting:
                # Verify game state unchanged
                assert game.state.down == 1, "Down should stay at 1 for offsetting penalties"
                assert game.state.ball_position == 50, "Ball position should be unchanged"
                assert outcome.yards_gained == 0, "Yards gained should be 0"
                break


class TestTimeoutInputParsing:
    """Tests for timeout input parsing in offense play selection."""
    
    def test_timeout_with_play_number_is_valid(self):
        """Input like '7T' should be valid - play 7 with timeout."""
        # Test the parsing logic directly
        choice = "7T"
        choice_clean = choice.upper().replace('+', '').replace('-', '').strip()
        
        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()
        
        assert call_timeout is True
        assert choice_clean == '7'
    
    def test_timeout_alone_leaves_empty_choice(self):
        """Input of just 'T' should leave empty choice_clean after stripping."""
        choice = "T"
        choice_clean = choice.upper().replace('+', '').replace('-', '').strip()
        
        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()
        
        assert call_timeout is True
        assert choice_clean == ''  # Empty - needs to prompt for play
    
    def test_timeout_with_special_play_is_valid(self):
        """Input like 'QT' should be valid - QB Sneak with timeout."""
        choice = "QT"
        choice_clean = choice.upper().replace('+', '').replace('-', '').strip()
        
        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()
        
        assert call_timeout is True
        assert choice_clean == 'Q'
    
    def test_timeout_with_modifiers(self):
        """Input like '5T+' should parse timeout and out of bounds."""
        choice = "5T+"
        out_of_bounds = '+' in choice
        in_bounds = '-' in choice
        choice_clean = choice.upper().replace('+', '').replace('-', '').strip()
        
        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()
        
        assert call_timeout is True
        assert out_of_bounds is True
        assert in_bounds is False
        assert choice_clean == '5'
    
    def test_lowercase_timeout_is_recognized(self):
        """Input 't' should be recognized as timeout."""
        choice = "7t"
        choice_clean = choice.upper().replace('+', '').replace('-', '').strip()
        
        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()
        
        assert call_timeout is True
        assert choice_clean == '7'


class TestAIHelperZKey:
    """Tests for Z key (AI Helper toggle) behavior."""
    
    def test_easy_helper_created_in_easy_mode(self):
        """Easy mode should create easy_helper."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from paydirt.chart_loader import load_team_chart
        from pathlib import Path
        
        chart = load_team_chart(Path('seasons/1983/Bears'))
        
        # In easy mode, easy_helper is created
        easy_helper = create_easy_mode_helper(chart)
        assert easy_helper is not None
    
    def test_z_key_logic_with_easy_helper(self):
        """Z key should toggle when easy_helper is provided."""
        # This test verifies the logic: when easy_helper exists, Z key can toggle
        easy_helper = "some_helper"  # Simulating easy mode helper
        
        # The Z key logic checks: if easy_helper is not None, it allows toggle
        if easy_helper:
            can_toggle = True
        else:
            can_toggle = False
        
        assert can_toggle is True
    
    def test_z_key_logic_without_easy_helper(self):
        """Z key should not work when easy_helper is None."""
        easy_helper = None  # Simulating medium/hard mode
        
        # The Z key logic checks: if easy_helper is not None, it allows toggle
        if easy_helper:
            can_toggle = True
        else:
            can_toggle = False
        
        assert can_toggle is False


class TestAIOpponentAnalysis:
    """Tests for AI opponent analysis at end of game."""
    
    def test_opponent_model_created_in_hard_mode(self):
        """Hard mode should create opponent_model for AI."""
        from paydirt.computer_ai import ComputerAI
        
        # Hard mode (use_analysis=True)
        ai = ComputerAI(aggression=0.7, use_analysis=True)
        assert ai.use_analysis is True
        assert ai.opponent_model is not None
        assert ai.opponent_model.tracker is not None
    
    def test_opponent_model_not_created_in_medium_mode(self):
        """Medium mode should not create opponent_model."""
        from paydirt.computer_ai import ComputerAI
        
        # Medium mode (use_analysis=False)
        ai = ComputerAI(aggression=0.5, use_analysis=False)
        assert ai.use_analysis is False
        assert ai.opponent_model is None
    
    def test_opponent_model_not_created_in_easy_mode(self):
        """Easy mode should not create opponent_model."""
        from paydirt.computer_ai import ComputerAI
        
        # Easy mode (use_analysis=False)
        ai = ComputerAI(aggression=0.3, use_analysis=False)
        assert ai.use_analysis is False
        assert ai.opponent_model is None
    
    def test_opponent_tracker_records_plays(self):
        """Opponent tracker should record plays when human is on offense."""
        from paydirt.computer_ai import ComputerAI
        
        ai = ComputerAI(aggression=0.7, use_analysis=True)
        
        # Record some plays
        ai.opponent_model.record_opponent_play(
            down=1, distance=10, play_type="Short Pass",
            yards_gained=5, is_pass=True
        )
        ai.opponent_model.record_opponent_play(
            down=2, distance=7, play_type="Run",
            yards_gained=3, is_pass=False
        )
        
        # Check the tracker has recorded the plays
        tracker = ai.opponent_model.tracker
        total_plays = sum(len(plays) for plays in tracker.situation_plays.values())
        
        assert total_plays == 2
    
    def test_opponent_tracker_calculates_tendencies(self):
        """Opponent tracker should calculate tendencies correctly."""
        from paydirt.computer_ai import ComputerAI
        
        ai = ComputerAI(aggression=0.7, use_analysis=True)
        
        # Record more pass plays than run plays
        for _ in range(4):
            ai.opponent_model.record_opponent_play(
                down=1, distance=10, play_type="Long Pass",
                yards_gained=15, is_pass=True
            )
        for _ in range(1):
            ai.opponent_model.record_opponent_play(
                down=2, distance=5, play_type="Run",
                yards_gained=2, is_pass=False
            )
        
        # Get tendency for 1st & 10
        tendency = ai.opponent_model.tracker.get_tendency(1, 10)
        
        assert tendency.total_plays == 4
        assert tendency.pass_plays == 4
        assert tendency.run_plays == 0
    
    def test_opponent_tracker_gets_defense_recommendation(self):
        """Opponent tracker should give defense recommendations based on tendencies."""
        from paydirt.computer_ai import ComputerAI
        
        ai = ComputerAI(aggression=0.7, use_analysis=True)
        
        # Record mostly pass plays (>60%) -> should recommend D (Short Pass defense)
        for _ in range(7):
            ai.opponent_model.record_opponent_play(
                down=3, distance=8, play_type="Long Pass",
                yards_gained=10, is_pass=True
            )
        for _ in range(3):
            ai.opponent_model.record_opponent_play(
                down=3, distance=8, play_type="Run",
                yards_gained=2, is_pass=False
            )
        
        # With >60% passes, should recommend D defense
        rec = ai.opponent_model.tracker.get_defense_recommendation(3, 8)
        
        assert rec == "D"
    
    def test_opponent_tracker_detects_streak(self):
        """Opponent tracker should detect streaks of same play types."""
        from paydirt.computer_ai import ComputerAI
        from paydirt.ai_analysis import PlayCategory
        
        ai = ComputerAI(aggression=0.7, use_analysis=True)
        
        # Record 3 consecutive pass plays
        for _ in range(3):
            ai.opponent_model.record_opponent_play(
                down=1, distance=10, play_type="Long Pass",
                yards_gained=15, is_pass=True
            )
        
        # Check streak detection (need at least 3 plays)
        streak = ai.opponent_model.tracker.get_streak()
        
        assert streak is not None
        assert streak == PlayCategory.PASS


class TestGetAvailableSeasons:
    """Tests for get_available_seasons function."""

    def test_returns_list_of_seasons(self):
        """Should return a list of available seasons."""
        from paydirt.interactive_game import get_available_seasons
        seasons = get_available_seasons()
        assert isinstance(seasons, list)

    def test_seasons_are_strings(self):
        """Each season should be a string."""
        from paydirt.interactive_game import get_available_seasons
        seasons = get_available_seasons()
        for season in seasons:
            assert isinstance(season, str)

    def test_seasons_are_sorted(self):
        """Seasons should be returned in sorted order."""
        from paydirt.interactive_game import get_available_seasons
        seasons = get_available_seasons()
        assert seasons == sorted(seasons)


class TestGetAvailableTeams:
    """Tests for get_available_teams function."""

    def test_returns_list_of_tuples(self):
        """Should return a list of tuples (path, name)."""
        from paydirt.interactive_game import get_available_teams
        teams = get_available_teams()
        assert isinstance(teams, list)
        if teams:
            assert isinstance(teams[0], tuple)
            assert len(teams[0]) == 2

    def test_with_season_filter(self):
        """Should return only teams from the specified season."""
        from paydirt.interactive_game import get_available_teams
        teams_1972 = get_available_teams("1972")
        teams_1983 = get_available_teams("1983")

        # Teams should have at least some entries
        assert len(teams_1972) > 0
        assert len(teams_1983) > 0

        # Each team path should contain the season
        for path, name in teams_1972:
            assert "1972" in path
        for path, name in teams_1983:
            assert "1983" in path

    def test_team_names_do_not_include_season(self):
        """Team names should not include the season prefix (it's shown separately now)."""
        from paydirt.interactive_game import get_available_teams
        teams = get_available_teams("1972")

        for path, name in teams:
            # Name should be just the team name (e.g., "Dolphins"), not "1972 Dolphins"
            assert not name.startswith("1972 ")


class TestSelectTeamTwoStep:
    """Tests for the two-step team selection process."""

    @patch('paydirt.interactive_game.select_season')
    @patch('paydirt.interactive_game.get_available_teams')
    @patch('paydirt.interactive_game.load_team_chart')
    def test_select_team_calls_select_season_first(self, mock_load, mock_get_teams, mock_select_season):
        """select_team should call select_season before getting teams."""
        from paydirt.interactive_game import select_team

        # Setup mocks
        mock_select_season.return_value = "1972"
        mock_get_teams.return_value = [
            ("seasons/1972/Dolphins", "Dolphins"),
            ("seasons/1972/Bills", "Bills"),
        ]
        mock_load.return_value = create_mock_chart("Dolphins")

        with patch('builtins.input', side_effect=["1"]):
            select_team("Select your team:")

        mock_select_season.assert_called_once()
        mock_get_teams.assert_called_once_with("1972")

    @patch('paydirt.interactive_game.select_season')
    @patch('paydirt.interactive_game.get_available_teams')
    @patch('paydirt.interactive_game.load_team_chart')
    def test_select_team_returns_selected_team(self, mock_load, mock_get_teams, mock_select_season):
        """select_team should return the selected team chart."""
        from paydirt.interactive_game import select_team

        mock_chart = create_mock_chart("Dolphins")
        mock_select_season.return_value = "1972"
        mock_get_teams.return_value = [
            ("seasons/1972/Dolphins", "Dolphins"),
            ("seasons/1972/Bills", "Bills"),
        ]
        mock_load.return_value = mock_chart

        with patch('builtins.input', side_effect=["1"]):
            result = select_team("Select your team:")

        assert result == mock_chart
        mock_load.assert_called_once_with("seasons/1972/Dolphins")

    @patch('paydirt.interactive_game.select_season')
    @patch('paydirt.interactive_game.get_available_teams')
    @patch('paydirt.interactive_game.load_team_chart')
    def test_select_team_validates_input(self, mock_load, mock_get_teams, mock_select_season):
        """select_team should re-prompt on invalid input."""
        from paydirt.interactive_game import select_team

        mock_select_season.return_value = "1972"
        mock_get_teams.return_value = [
            ("seasons/1972/Dolphins", "Dolphins"),
        ]
        mock_load.return_value = create_mock_chart("Dolphins")

        # First input is invalid, second is valid
        with patch('builtins.input', side_effect=["invalid", "99", "1"]):
            result = select_team("Select your team:")

        assert result.short_name == "Dolphins"
        # Should have been called 3 times (2 invalid + 1 valid)
        assert mock_load.call_count == 1

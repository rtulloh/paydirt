"""
Tests for interactive_game.py functions that don't require user input.
"""
import pytest
from unittest.mock import MagicMock

from paydirt.interactive_game import (
    analyze_team_strength,
    cpu_should_go_for_two,
    cpu_should_onside_kick,
    computer_select_offense,
    computer_select_defense,
    _apply_timeout,
    format_time,
)
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

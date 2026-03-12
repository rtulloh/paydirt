"""
Tests for play_resolver.py to improve coverage.
"""
import pytest
from unittest.mock import patch

from paydirt.play_resolver import (
    PlayType, is_passing_play, roll_chart_dice,
    resolve_field_goal_with_penalties, parse_result_string
)
from paydirt.chart_loader import SpecialTeamsChart


class TestIsPassingPlay:
    """Tests for is_passing_play function."""
    
    def test_short_pass_is_passing(self):
        assert is_passing_play(PlayType.SHORT_PASS) is True
    
    def test_medium_pass_is_passing(self):
        assert is_passing_play(PlayType.MEDIUM_PASS) is True
    
    def test_long_pass_is_passing(self):
        assert is_passing_play(PlayType.LONG_PASS) is True
    
    def test_screen_is_passing(self):
        assert is_passing_play(PlayType.SCREEN) is True
    
    def test_te_short_long_is_passing(self):
        assert is_passing_play(PlayType.TE_SHORT_LONG) is True
    
    def test_line_plunge_is_not_passing(self):
        assert is_passing_play(PlayType.LINE_PLUNGE) is False
    
    def test_off_tackle_is_not_passing(self):
        assert is_passing_play(PlayType.OFF_TACKLE) is False
    
    def test_end_run_is_not_passing(self):
        assert is_passing_play(PlayType.END_RUN) is False
    
    def test_draw_is_not_passing(self):
        assert is_passing_play(PlayType.DRAW) is False


class TestRollChartDice:
    """Tests for roll_chart_dice function."""
    
    def test_roll_returns_tuple(self):
        roll, desc = roll_chart_dice()
        assert isinstance(roll, int)
        assert isinstance(desc, str)
    
    def test_roll_in_valid_range(self):
        """Dice roll should be between 10 and 39."""
        for _ in range(100):
            roll, _ = roll_chart_dice()
            assert 10 <= roll <= 39


class TestParseResultString:
    """Tests for parse_result_string function."""
    
    def test_parse_positive_yards(self):
        result = parse_result_string("5")
        assert result.yards == 5
        assert result.turnover is False
    
    def test_parse_negative_yards(self):
        result = parse_result_string("-3")
        assert result.yards == -3
    
    def test_parse_touchdown(self):
        result = parse_result_string("TD")
        assert result.touchdown is True
    
    def test_parse_out_of_bounds(self):
        # OB format may vary - test the actual format used
        result = parse_result_string("5OB")
        # Just verify it parses without error
        assert result is not None
    
    def test_parse_zero_yards(self):
        result = parse_result_string("0")
        assert result.yards == 0

    def test_parse_plain_fumble(self):
        """Plain 'F' should be parsed as fumble at line of scrimmage."""
        result = parse_result_string("F")
        from paydirt.play_resolver import ResultType
        assert result.result_type == ResultType.FUMBLE
        assert result.yards == 0
        assert result.turnover is True

    def test_parse_fumble_with_positive_yards(self):
        """'F + 2' should be parsed as fumble with +2 yards."""
        result = parse_result_string("F + 2")
        from paydirt.play_resolver import ResultType
        assert result.result_type == ResultType.FUMBLE
        assert result.yards == 2
        assert result.turnover is True

    def test_parse_fumble_with_negative_yards(self):
        """'F - 4' should be parsed as fumble with -4 yards."""
        result = parse_result_string("F - 4")
        from paydirt.play_resolver import ResultType
        assert result.result_type == ResultType.FUMBLE
        assert result.yards == -4
        assert result.turnover is True

    def test_parse_incomplete_inc(self):
        """'INC' should be parsed as incomplete pass (1972 format)."""
        result = parse_result_string("INC")
        from paydirt.play_resolver import ResultType
        assert result.result_type == ResultType.INCOMPLETE
        assert result.yards == 0

    def test_parse_incomplete_empty_string(self):
        """Empty string should be parsed as incomplete pass."""
        result = parse_result_string("")
        from paydirt.play_resolver import ResultType
        assert result.result_type == ResultType.INCOMPLETE
        assert result.yards == 0


class TestResolveFieldGoalWithPenalties:
    """Tests for resolve_field_goal_with_penalties function."""
    
    @pytest.fixture
    def special_teams(self):
        """Create a mock special teams chart for testing."""
        return SpecialTeamsChart(
            field_goal={
                10: "45",
                11: "35",
                12: "25",
                13: "15",
                14: "BK -8",
                15: "DEF 5",
                16: "OFF 10",
                17: "F - 5",
            }
        )
    
    def test_successful_fg_result(self, special_teams):
        """Test a successful field goal roll."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.return_value = (10, "B1+W0+W0=10")
            
            result = resolve_field_goal_with_penalties(special_teams)
            
            assert result.raw_result == "45"
            assert result.chart_yards == 45
            assert result.is_blocked is False
            assert result.is_fumble is False
    
    def test_blocked_fg_result(self, special_teams):
        """Test a blocked field goal roll."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.return_value = (14, "B1+W2+W2=14")
            
            result = resolve_field_goal_with_penalties(special_teams)
            
            assert "BK" in result.raw_result
            assert result.is_blocked is True
    
    def test_fumbled_fg_result(self, special_teams):
        """Test a fumbled field goal snap."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.return_value = (17, "B1+W3+W3=17")
            
            result = resolve_field_goal_with_penalties(special_teams)
            
            assert "F" in result.raw_result
            assert result.is_fumble is True
    
    def test_defensive_penalty_on_fg(self, special_teams):
        """Test defensive penalty on field goal."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            # First roll is penalty, second is normal result
            mock_roll.side_effect = [(15, "B1+W2+W3=15"), (10, "B1+W0+W0=10")]
            
            result = resolve_field_goal_with_penalties(special_teams)
            
            assert len(result.penalty_options) > 0
            assert result.offended_team == "offense"
    
    def test_offensive_penalty_on_fg(self, special_teams):
        """Test offensive penalty on field goal."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            # First roll is penalty, second is normal result
            mock_roll.side_effect = [(16, "B1+W3+W3=16"), (10, "B1+W0+W0=10")]
            
            result = resolve_field_goal_with_penalties(special_teams)
            
            assert len(result.penalty_options) > 0
            assert result.offended_team == "defense"
    
    def test_offsetting_penalties_on_fg(self, special_teams):
        """Test offsetting penalties on field goal."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            # First roll is DEF penalty, second is OFF penalty, third is normal
            mock_roll.side_effect = [
                (15, "B1+W2+W3=15"),  # DEF penalty
                (16, "B1+W3+W3=16"),  # OFF penalty
                (10, "B1+W0+W0=10")   # Normal result
            ]
            
            result = resolve_field_goal_with_penalties(special_teams)
            
            assert result.offsetting is True
            assert len(result.penalty_options) == 2


class TestBreakawayDiceField:
    """Tests for breakaway_dice field in PlayResult.
    
    Bug fix: Breakaway dice roll should be stored in PlayResult for diagnostic display.
    """
    
    def test_play_result_has_breakaway_dice_field(self):
        """PlayResult should have breakaway_dice field initialized to 0."""
        from paydirt.play_resolver import PlayResult, ResultType
        
        result = PlayResult(
            result_type=ResultType.BREAKAWAY,
            yards=10,
            description="Breakaway!",
            dice_roll=25
        )
        
        # breakaway_dice should default to 0
        assert result.breakaway_dice == 0
    
    def test_play_result_breakaway_dice_can_be_set(self):
        """PlayResult breakaway_dice should be settable."""
        from paydirt.play_resolver import PlayResult, ResultType
        
        result = PlayResult(
            result_type=ResultType.BREAKAWAY,
            yards=15,
            description="Breakaway!",
            dice_roll=25
        )
        
        # Set breakaway_dice
        result.breakaway_dice = 22
        
        assert result.breakaway_dice == 22

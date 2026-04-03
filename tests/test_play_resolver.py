"""
Tests for play_resolver.py to improve coverage.
"""

import pytest
from unittest.mock import patch

from paydirt.play_resolver import (
    PlayType,
    is_passing_play,
    roll_chart_dice,
    resolve_field_goal_with_penalties,
    parse_result_string,
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
        with patch("paydirt.play_resolver.roll_chart_dice") as mock_roll:
            mock_roll.return_value = (10, "B1+W0+W0=10")

            result = resolve_field_goal_with_penalties(special_teams)

            assert result.raw_result == "45"
            assert result.chart_yards == 45
            assert result.is_blocked is False
            assert result.is_fumble is False

    def test_blocked_fg_result(self, special_teams):
        """Test a blocked field goal roll."""
        with patch("paydirt.play_resolver.roll_chart_dice") as mock_roll:
            mock_roll.return_value = (14, "B1+W2+W2=14")

            result = resolve_field_goal_with_penalties(special_teams)

            assert "BK" in result.raw_result
            assert result.is_blocked is True

    def test_fumbled_fg_result(self, special_teams):
        """Test a fumbled field goal snap."""
        with patch("paydirt.play_resolver.roll_chart_dice") as mock_roll:
            mock_roll.return_value = (17, "B1+W3+W3=17")

            result = resolve_field_goal_with_penalties(special_teams)

            assert "F" in result.raw_result
            assert result.is_fumble is True

    def test_defensive_penalty_on_fg(self, special_teams):
        """Test defensive penalty on field goal."""
        with patch("paydirt.play_resolver.roll_chart_dice") as mock_roll:
            # First roll is penalty, second is normal result
            mock_roll.side_effect = [(15, "B1+W2+W3=15"), (10, "B1+W0+W0=10")]

            result = resolve_field_goal_with_penalties(special_teams)

            assert len(result.penalty_options) > 0
            assert result.offended_team == "offense"

    def test_offensive_penalty_on_fg(self, special_teams):
        """Test offensive penalty on field goal."""
        with patch("paydirt.play_resolver.roll_chart_dice") as mock_roll:
            # First roll is penalty, second is normal result
            mock_roll.side_effect = [(16, "B1+W3+W3=16"), (10, "B1+W0+W0=10")]

            result = resolve_field_goal_with_penalties(special_teams)

            assert len(result.penalty_options) > 0
            assert result.offended_team == "defense"

    def test_offsetting_penalties_on_fg(self, special_teams):
        """Test offsetting penalties on field goal."""
        with patch("paydirt.play_resolver.roll_chart_dice") as mock_roll:
            # First roll is DEF penalty, second is OFF penalty, third is normal
            mock_roll.side_effect = [
                (15, "B1+W2+W3=15"),  # DEF penalty
                (16, "B1+W3+W3=16"),  # OFF penalty
                (10, "B1+W0+W0=10"),  # Normal result
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
            result_type=ResultType.BREAKAWAY, yards=10, description="Breakaway!", dice_roll=25
        )

        # breakaway_dice should default to 0
        assert result.breakaway_dice == 0

    def test_play_result_breakaway_dice_can_be_set(self):
        """PlayResult breakaway_dice should be settable."""
        from paydirt.play_resolver import PlayResult, ResultType

        result = PlayResult(
            result_type=ResultType.BREAKAWAY, yards=15, description="Breakaway!", dice_roll=25
        )

        # Set breakaway_dice
        result.breakaway_dice = 22

        assert result.breakaway_dice == 22


class TestRollDice:
    """Tests for roll_dice function."""

    def test_roll_dice_returns_valid_range(self):
        """roll_dice should return 2-12."""
        from paydirt.play_resolver import roll_dice

        for _ in range(100):
            result = roll_dice()
            assert 2 <= result <= 12

    def test_roll_dice_returns_int(self):
        """roll_dice should return an integer."""
        from paydirt.play_resolver import roll_dice

        assert isinstance(roll_dice(), int)


class TestRollD10:
    """Tests for roll_d10 function."""

    def test_roll_d10_returns_valid_range(self):
        """roll_d10 should return 1-10."""
        from paydirt.play_resolver import roll_d10

        for _ in range(100):
            result = roll_d10()
            assert 1 <= result <= 10

    def test_roll_d10_returns_int(self):
        """roll_d10 should return an integer."""
        from paydirt.play_resolver import roll_d10

        assert isinstance(roll_d10(), int)


class TestRollWhiteDice:
    """Tests for roll_white_dice function."""

    def test_roll_white_dice_returns_valid_range(self):
        """roll_white_dice should return 0-10."""
        from paydirt.play_resolver import roll_white_dice

        for _ in range(100):
            result, _ = roll_white_dice()
            assert 0 <= result <= 10

    def test_roll_white_dice_description_format(self):
        """roll_white_dice should return description string."""
        from paydirt.play_resolver import roll_white_dice

        result, desc = roll_white_dice()
        assert isinstance(desc, str)
        assert "W" in desc


class TestRollOffensiveDiceDetailed:
    """Tests for roll_offensive_dice_detailed function."""

    def test_returns_valid_range(self):
        """Should return total in 10-39 range."""
        from paydirt.play_resolver import roll_offensive_dice_detailed

        for _ in range(100):
            total, _, _, _, _, _ = roll_offensive_dice_detailed()
            assert 10 <= total <= 39

    def test_returns_all_components(self):
        """Should return all 6 components."""
        from paydirt.play_resolver import roll_offensive_dice_detailed

        result = roll_offensive_dice_detailed()
        assert len(result) == 6
        total, black, white1, white2, direct_sum, desc = result
        assert isinstance(total, int)
        assert isinstance(black, int)
        assert isinstance(white1, int)
        assert isinstance(white2, int)
        assert isinstance(direct_sum, int)
        assert isinstance(desc, str)

    def test_total_calculation(self):
        """Total should equal black*10 + min(white_sum, 9)."""
        from paydirt.play_resolver import roll_offensive_dice_detailed

        for _ in range(100):
            total, black, white1, white2, direct_sum, _ = roll_offensive_dice_detailed()
            white_sum = white1 + white2
            expected_total = (black * 10) + min(white_sum, 9)
            assert total == expected_total


class TestResolveVariableYardage:
    """Tests for resolve_variable_yardage function."""

    def test_resolve_variable_yardage_ds_range(self):
        """DS: Direct sum of three dice = 1-13."""
        from paydirt.play_resolver import resolve_variable_yardage

        for _ in range(50):
            result, _ = resolve_variable_yardage("DS")
            assert 1 <= result <= 13

    def test_resolve_variable_yardage_x_range(self):
        """X: 40 - normal total = 1-30."""
        from paydirt.play_resolver import resolve_variable_yardage

        for _ in range(50):
            result, _ = resolve_variable_yardage("X")
            assert 1 <= result <= 30

    def test_resolve_variable_yardage_t1_range(self):
        """T1: Normal offensive total = 10-39."""
        from paydirt.play_resolver import resolve_variable_yardage

        for _ in range(50):
            result, _ = resolve_variable_yardage("T1")
            assert 10 <= result <= 39

    def test_resolve_variable_yardage_t2_range(self):
        """T2: Sum of two rolls = 20-78."""
        from paydirt.play_resolver import resolve_variable_yardage

        for _ in range(50):
            result, _ = resolve_variable_yardage("T2")
            assert 20 <= result <= 78

    def test_resolve_variable_yardage_t3_range(self):
        """T3: Sum of three rolls = 30-117."""
        from paydirt.play_resolver import resolve_variable_yardage

        for _ in range(50):
            result, _ = resolve_variable_yardage("T3")
            assert 30 <= result <= 117


class TestIsVariableYardage:
    """Tests for is_variable_yardage function."""

    def test_ds_is_variable(self):
        """DS should be variable yardage."""
        from paydirt.play_resolver import is_variable_yardage

        assert is_variable_yardage("DS") is True

    def test_x_is_variable(self):
        """X should be variable yardage."""
        from paydirt.play_resolver import is_variable_yardage

        assert is_variable_yardage("X") is True

    def test_t1_is_variable(self):
        """T1 should be variable yardage."""
        from paydirt.play_resolver import is_variable_yardage

        assert is_variable_yardage("T1") is True

    def test_numeric_not_variable(self):
        """Numeric values should not be variable."""
        from paydirt.play_resolver import is_variable_yardage

        assert is_variable_yardage("5") is False
        assert is_variable_yardage("10") is False

    def test_td_not_variable(self):
        """TD should not be variable."""
        from paydirt.play_resolver import is_variable_yardage

        assert is_variable_yardage("TD") is False

    def test_inc_not_variable(self):
        """INC should not be variable."""
        from paydirt.play_resolver import is_variable_yardage

        assert is_variable_yardage("INC") is False


class TestResolveQBScramble:
    """Tests for resolve_qb_scramble function."""

    def test_resolve_qb_scramble_signature(self):
        """resolve_qb_scramble requires chart and dice_roll."""
        from paydirt.play_resolver import resolve_qb_scramble
        import inspect

        sig = inspect.signature(resolve_qb_scramble)
        params = list(sig.parameters.keys())
        assert "chart" in params
        assert "dice_roll" in params


class TestParseColumnValue:
    """Tests for _parse_column_value function - verify function exists and is callable."""

    def test_parse_column_value_function_exists(self):
        """_parse_column_value should exist and be callable."""
        from paydirt.play_resolver import _parse_column_value

        assert callable(_parse_column_value)

    def test_parse_column_value_returns_column_result(self):
        """_parse_column_value returns a ColumnResult object."""
        from paydirt.play_resolver import _parse_column_value

        result = _parse_column_value("5")
        assert result is not None
        assert hasattr(result, "yards")


class TestIsPenaltyResult:
    """Tests for _is_penalty_result function - verify function exists."""

    def test_is_penalty_result_function_exists(self):
        """_is_penalty_result should exist and be callable."""
        from paydirt.play_resolver import _is_penalty_result

        assert callable(_is_penalty_result)

    def test_is_penalty_result_returns_tuple(self):
        """_is_penalty_result returns a tuple."""
        from paydirt.play_resolver import _is_penalty_result

        result = _is_penalty_result("PENALTY")
        assert isinstance(result, tuple)


class TestCreatePenaltyOption:
    """Tests for _create_penalty_option function - verify function exists."""

    def test_create_penalty_option_function_exists(self):
        """_create_penalty_option should exist and be callable."""
        from paydirt.play_resolver import _create_penalty_option

        assert callable(_create_penalty_option)

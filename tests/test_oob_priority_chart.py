"""
Tests for OOB (*) marker propagation through the priority chart pipeline.

Bug: The * out-of-bounds marker on offense chart results (e.g., "3*", "9*")
was silently stripped by categorize_result() and never propagated to PlayResult.
This meant ~568 chart entries across all teams lost their OOB flag, causing
incorrect clock behavior in late-game situations.

Fix: apply_priority_chart() now detects * in the raw offense_result string
and sets CombinedResult.out_of_bounds. Callers propagate this to PlayResult.
"""
from paydirt.priority_chart import (
    apply_priority_chart, categorize_result,
    ResultCategory, CombinedResult,
)


class TestCategorizeResultPreservesYards:
    """Verify categorize_result still correctly parses yardage from * entries."""

    def test_positive_with_asterisk(self):
        cat, yards = categorize_result("3*")
        assert cat == ResultCategory.GREEN_NUMBER
        assert yards == 3

    def test_negative_with_asterisk(self):
        cat, yards = categorize_result("-5*")
        assert cat == ResultCategory.RED_NUMBER
        assert yards == -5

    def test_plain_number_no_asterisk(self):
        cat, yards = categorize_result("7")
        assert cat == ResultCategory.GREEN_NUMBER
        assert yards == 7

    def test_zero_with_asterisk(self):
        cat, yards = categorize_result("0*")
        assert cat == ResultCategory.WHITE_NUMBER
        assert yards == 0


class TestApplyPriorityChartOOB:
    """Verify apply_priority_chart propagates OOB from offense result."""

    def test_oob_positive_yards(self):
        """'3*' offense + no defense change → out_of_bounds=True."""
        result = apply_priority_chart("3*", "", is_passing_play=False)
        assert result.out_of_bounds is True
        assert result.final_yards == 3

    def test_oob_negative_yards(self):
        """'-5*' offense → out_of_bounds=True."""
        result = apply_priority_chart("-5*", "", is_passing_play=False)
        assert result.out_of_bounds is True
        assert result.final_yards == -5

    def test_no_oob_plain_number(self):
        """'7' offense → out_of_bounds=False."""
        result = apply_priority_chart("7", "", is_passing_play=False)
        assert result.out_of_bounds is False

    def test_oob_with_defense_add(self):
        """'3*' offense + '2' defense → ADD=5, out_of_bounds=True."""
        result = apply_priority_chart("3*", "2", is_passing_play=False)
        assert result.out_of_bounds is True
        assert result.final_yards == 5

    def test_oob_with_negative_defense(self):
        """'9*' offense + '-3' defense → ADD=6, out_of_bounds=True."""
        result = apply_priority_chart("9*", "-3", is_passing_play=False)
        assert result.out_of_bounds is True
        assert result.final_yards == 6

    def test_no_oob_fumble(self):
        """Fumble offense → out_of_bounds=False (no * in 'F')."""
        result = apply_priority_chart("F", "3", is_passing_play=False)
        assert result.out_of_bounds is False

    def test_no_oob_interception(self):
        """INT offense → out_of_bounds=False."""
        result = apply_priority_chart("INT 20", "3", is_passing_play=True)
        assert result.out_of_bounds is False

    def test_no_oob_td(self):
        """TD offense → out_of_bounds=False."""
        result = apply_priority_chart("TD", "", is_passing_play=False)
        assert result.out_of_bounds is False

    def test_no_oob_qt(self):
        """QT offense (no * in 'QT') → out_of_bounds=False."""
        result = apply_priority_chart("QT", "", is_passing_play=False)
        assert result.out_of_bounds is False
        assert result.use_qt_column is True

    def test_no_oob_breakaway(self):
        """B offense → out_of_bounds=False (B column has its own OOB handling)."""
        result = apply_priority_chart("B", "", is_passing_play=False)
        assert result.out_of_bounds is False

    def test_oob_with_parens_defense_override(self):
        """'3*' offense + '(5)' defense → defense overrules, but OOB still from offense."""
        result = apply_priority_chart("3*", "(5)", is_passing_play=False)
        assert result.out_of_bounds is True
        assert result.final_yards == 5

    def test_no_oob_empty_offense(self):
        """Empty offense → out_of_bounds=False."""
        result = apply_priority_chart("", "", is_passing_play=False)
        assert result.out_of_bounds is False


class TestResolvePlayOOBPropagation:
    """Verify resolve_play propagates OOB from CombinedResult to PlayResult."""

    def test_resolve_play_sets_oob_from_combined(self):
        """When combined.out_of_bounds is True, PlayResult.out_of_bounds should be True."""
        from unittest.mock import patch, MagicMock
        from paydirt.play_resolver import resolve_play, PlayType, DefenseType

        mock_combined = CombinedResult(
            priority=None,
            final_yards=3,
            is_turnover=False,
            is_touchdown=False,
            is_incomplete=False,
            use_qt_column=False,
            use_breakaway=False,
            description="Add: 3 + 0 = 3",
            offense_result="3*",
            defense_result="",
            out_of_bounds=True,
        )

        home_chart = MagicMock()
        away_chart = MagicMock()
        home_chart.peripheral = MagicMock()
        home_chart.peripheral.short_name = "HOM"
        away_chart.peripheral = MagicMock()
        away_chart.peripheral.short_name = "AWY"

        with patch('paydirt.play_resolver.roll_chart_dice', return_value=(20, "20")), \
             patch('paydirt.play_resolver.get_offense_result', return_value="3*"), \
             patch('paydirt.play_resolver.get_defense_modifier', return_value=""), \
             patch('paydirt.play_resolver.apply_priority_chart', return_value=mock_combined):
            result = resolve_play(home_chart, away_chart,
                                  PlayType.LINE_PLUNGE, DefenseType.STANDARD)

        assert result.out_of_bounds is True
        assert result.yards == 3

    def test_resolve_play_no_oob_when_not_asterisk(self):
        """When combined.out_of_bounds is False, PlayResult.out_of_bounds should be False."""
        from unittest.mock import patch, MagicMock
        from paydirt.play_resolver import resolve_play, PlayType, DefenseType

        mock_combined = CombinedResult(
            priority=None,
            final_yards=7,
            is_turnover=False,
            is_touchdown=False,
            is_incomplete=False,
            use_qt_column=False,
            use_breakaway=False,
            description="Add: 7 + 0 = 7",
            offense_result="7",
            defense_result="",
            out_of_bounds=False,
        )

        home_chart = MagicMock()
        away_chart = MagicMock()
        home_chart.peripheral = MagicMock()
        home_chart.peripheral.short_name = "HOM"
        away_chart.peripheral = MagicMock()
        away_chart.peripheral.short_name = "AWY"

        with patch('paydirt.play_resolver.roll_chart_dice', return_value=(20, "20")), \
             patch('paydirt.play_resolver.get_offense_result', return_value="7"), \
             patch('paydirt.play_resolver.get_defense_modifier', return_value=""), \
             patch('paydirt.play_resolver.apply_priority_chart', return_value=mock_combined):
            result = resolve_play(home_chart, away_chart,
                                  PlayType.LINE_PLUNGE, DefenseType.STANDARD)

        assert result.out_of_bounds is False

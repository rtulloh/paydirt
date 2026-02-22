"""
Tests for the Priority Chart resolution.

The Priority Chart determines how offensive and defensive results are combined.
Key rules:
- Defense results in parentheses (#) override most offense results
- Breakaway (B) should NOT override defense parentheses results
- QT (quarterback trouble) should override breakaway
"""

from paydirt.priority_chart import (
    apply_priority_chart, categorize_result, 
    ResultCategory, PriorityResult, PRIORITY_CHART
)
from paydirt.play_resolver import PlayType, is_passing_play


class TestCategorizeResult:
    """Tests for categorizing result strings."""
    
    def test_positive_number(self):
        """Positive numbers should be categorized as green."""
        cat, val = categorize_result("5")
        assert cat == ResultCategory.GREEN_NUMBER
        assert val == 5
    
    def test_positive_decimal_number(self):
        """Positive decimal numbers should be categorized as green."""
        cat, val = categorize_result("2.0")
        assert cat == ResultCategory.GREEN_NUMBER
        assert val == 2
    
    def test_negative_number(self):
        """Negative numbers should be categorized as red."""
        cat, val = categorize_result("-3")
        assert cat == ResultCategory.RED_NUMBER
        assert val == -3
    
    def test_breakaway(self):
        """B should be categorized as breakaway."""
        cat, val = categorize_result("B")
        assert cat == ResultCategory.BREAKAWAY
    
    def test_parentheses_number(self):
        """Numbers in parentheses should be categorized as parens."""
        cat, val = categorize_result("(1)")
        assert cat == ResultCategory.PARENS_NUMBER
        assert val == 1
    
    def test_parentheses_td(self):
        """(TD) should be categorized as PARENS_TD, not WHITE_NUMBER."""
        cat, val = categorize_result("(TD)")
        assert cat == ResultCategory.PARENS_TD
        assert val is None
    
    def test_qt(self):
        """QT should be categorized as quarterback trouble."""
        cat, val = categorize_result("QT")
        assert cat == ResultCategory.QT
    
    def test_interception(self):
        """INT should be categorized as interception."""
        cat, val = categorize_result("INT 15")
        assert cat == ResultCategory.INT

    def test_black_not_breakaway(self):
        """BLACK should be categorized as BLACK, not breakaway.
        
        Bug fix: BLACK starts with 'B' but should be categorized as BLACK,
        not as BREAKAWAY (which would trigger breakaway resolution).
        """
        cat, val = categorize_result("BLACK")
        assert cat == ResultCategory.BLACK
        assert val is None


class TestBreakawayVsDefenseParentheses:
    """Tests for breakaway vs defense (1) priority resolution.
    
    Per Paydirt rules, when defense has parentheses result and offense has
    breakaway, the PARENS priority is used which means the offense result
    is used (not the breakaway). This prevents breakaway from triggering.
    """
    
    def test_breakaway_vs_parens_uses_parens_priority(self):
        """Breakaway vs parentheses should use PARENS priority (no breakaway)."""
        result = apply_priority_chart("B", "(1)")
        
        assert result.priority == PriorityResult.PARENS
        # PARENS means offense overrules - breakaway has no yards value
        assert result.use_breakaway is False
    
    def test_breakaway_vs_parens_no_breakaway_roll(self):
        """Breakaway vs parentheses should NOT trigger breakaway roll."""
        result = apply_priority_chart("B", "(-2)")
        
        assert result.priority == PriorityResult.PARENS
        assert result.use_breakaway is False
    
    def test_priority_chart_entry_is_parens(self):
        """Verify the priority chart entry for B vs (#) is PARENS."""
        priority = PRIORITY_CHART.get(
            (ResultCategory.BREAKAWAY, ResultCategory.PARENS_NUMBER)
        )
        assert priority == PriorityResult.PARENS


class TestBreakawayVsQT:
    """Tests for breakaway vs QT (quarterback trouble) priority."""
    
    def test_breakaway_vs_qt_uses_qt(self):
        """QT should override breakaway."""
        result = apply_priority_chart("B", "QT")
        
        assert result.priority == PriorityResult.QT
    
    def test_priority_chart_entry_is_qt(self):
        """Verify the priority chart entry for B vs QT is QT."""
        priority = PRIORITY_CHART.get(
            (ResultCategory.BREAKAWAY, ResultCategory.QT)
        )
        assert priority == PriorityResult.QT


class TestBreakawayNormalCases:
    """Tests for breakaway in normal (non-override) situations."""
    
    def test_breakaway_vs_positive_number(self):
        """Breakaway vs positive number should use breakaway."""
        result = apply_priority_chart("B", "3")
        
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_negative_number(self):
        """Breakaway vs negative number should use breakaway."""
        result = apply_priority_chart("B", "-2")
        
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_black(self):
        """Breakaway vs empty/black should use breakaway."""
        result = apply_priority_chart("B", "BLACK")
        
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_interception(self):
        """Breakaway vs interception should use interception (turnover)."""
        result = apply_priority_chart("B", "INT 20")
        
        assert result.priority == PriorityResult.INT
    
    def test_breakaway_vs_fumble(self):
        """Breakaway vs fumble should use fumble (turnover)."""
        result = apply_priority_chart("B", "F")
        
        assert result.priority == PriorityResult.FUMBLE


class TestParensTDOverrides:
    """Tests that (TD) defense results trigger PARENS_TD priority (touchdown)."""
    
    def test_green_number_vs_parens_td(self):
        """(TD) on defense should override green number offense with touchdown."""
        result = apply_priority_chart("12", "(TD)")
        
        assert result.priority == PriorityResult.PARENS_TD
        assert result.is_touchdown is True
    
    def test_breakaway_vs_parens_td(self):
        """(TD) on defense should override breakaway with touchdown."""
        result = apply_priority_chart("B", "(TD)")
        
        assert result.priority == PriorityResult.PARENS_TD
        assert result.is_touchdown is True
    
    def test_black_vs_parens_td(self):
        """(TD) on defense should override incomplete with touchdown."""
        result = apply_priority_chart("BLACK", "(TD)")
        
        assert result.priority == PriorityResult.PARENS_TD
        assert result.is_touchdown is True


class TestParenthesesOverridesOtherResults:
    """Tests that parentheses defense results trigger PARENS priority.
    
    PARENS priority means defense's parenthesized number determines the yards offense gains.
    """
    
    def test_positive_vs_parens(self):
        """Positive yardage vs parentheses should use defense's parenthesized yards."""
        result = apply_priority_chart("8", "(1)")
        
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 1  # Defense's parenthesized number
    
    def test_negative_vs_parens(self):
        """Negative yardage vs parentheses should use defense's parenthesized yards."""
        result = apply_priority_chart("-3", "(2)")
        
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 2  # Defense's parenthesized number
    
    def test_qt_vs_parens(self):
        """QT vs parentheses should use PARENS priority."""
        result = apply_priority_chart("QT", "(1)")
        
        assert result.priority == PriorityResult.PARENS
    
    def test_black_vs_parens_uses_defense_yards(self):
        """BLACK (empty) offense vs parentheses should use defense's parenthesized number.
        
        When offense chart is empty and defense has (4), offense gets 4 yards.
        Per the board game chart, (#) on defense always gives offense those yards.
        """
        result = apply_priority_chart("BLACK", "(4)")
        
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 4  # Defense's parenthesized number
        assert "Defense (#)" in result.description
    
    def test_black_vs_parens_various_values(self):
        """BLACK vs various parenthesized numbers should use defense yards."""
        # Test (12)
        result = apply_priority_chart("BLACK", "(12)")
        assert result.final_yards == 12
        
        # Test (0)
        result = apply_priority_chart("BLACK", "(0)")
        assert result.final_yards == 0
        
        # Test negative (-2)
        result = apply_priority_chart("BLACK", "(-2)")
        assert result.final_yards == -2


class TestIsPassingPlay:
    """Tests for the is_passing_play helper function."""
    
    def test_running_plays_are_not_passing(self):
        """Running plays should return False."""
        assert is_passing_play(PlayType.LINE_PLUNGE) is False
        assert is_passing_play(PlayType.OFF_TACKLE) is False
        assert is_passing_play(PlayType.END_RUN) is False
        assert is_passing_play(PlayType.DRAW) is False
    
    def test_passing_plays_are_passing(self):
        """Passing plays should return True."""
        assert is_passing_play(PlayType.SHORT_PASS) is True
        assert is_passing_play(PlayType.MEDIUM_PASS) is True
        assert is_passing_play(PlayType.LONG_PASS) is True
        assert is_passing_play(PlayType.TE_SHORT_LONG) is True
        assert is_passing_play(PlayType.SCREEN) is True
        assert is_passing_play(PlayType.HAIL_MARY) is True


class TestBlackResultForRunningVsPassingPlays:
    """Tests for BLACK (empty) result handling based on play type.
    
    Per Paydirt rules:
    - BLACK vs BLACK on a passing play = Incomplete pass
    - BLACK vs BLACK on a running play = No gain (tackled at line of scrimmage)
    """
    
    def test_black_vs_black_passing_play_is_incomplete(self):
        """BLACK vs BLACK on passing play should be incomplete pass."""
        result = apply_priority_chart("BLACK", "BLACK", is_passing_play=True)
        
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is True
        assert "Incomplete pass" in result.description
    
    def test_black_vs_black_running_play_is_no_gain(self):
        """BLACK vs BLACK on running play should be no gain, not incomplete."""
        result = apply_priority_chart("BLACK", "BLACK", is_passing_play=False)
        
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is False
        assert result.final_yards == 0
        assert "No gain" in result.description
    
    def test_default_is_passing_play(self):
        """Default behavior (no is_passing_play arg) should treat as passing play."""
        result = apply_priority_chart("BLACK", "BLACK")
        
        assert result.is_incomplete is True
        assert "Incomplete pass" in result.description
    
    def test_positive_vs_black_running_play_uses_offense(self):
        """Positive yardage vs BLACK on running play should use offense result."""
        result = apply_priority_chart("5", "BLACK", is_passing_play=False)
        
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == 5
        assert result.is_incomplete is False
    
    def test_positive_vs_black_passing_play_is_incomplete(self):
        """Positive yardage vs BLACK on passing play should be incomplete."""
        result = apply_priority_chart("5", "BLACK", is_passing_play=True)
        
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is True
        assert result.final_yards == 0
        assert "Incomplete" in result.description


# =============================================================================
# COMPREHENSIVE PRIORITY CHART TESTS
# Tests for every combination in the PRIORITY_CHART lookup table
# =============================================================================

class TestGreenNumberOffense:
    """Tests for GREEN_NUMBER (positive yardage) offense results."""
    
    def test_green_vs_green_adds(self):
        """Green # vs Green # should ADD."""
        result = apply_priority_chart("8", "3")
        assert result.priority == PriorityResult.ADD
        assert result.final_yards == 11  # 8 + 3
    
    def test_green_vs_white_adds(self):
        """Green # vs White # should ADD."""
        result = apply_priority_chart("8", "0")
        assert result.priority == PriorityResult.ADD
        assert result.final_yards == 8  # 8 + 0
    
    def test_green_vs_red_adds(self):
        """Green # vs Red # should ADD."""
        result = apply_priority_chart("8", "-3")
        assert result.priority == PriorityResult.ADD
        assert result.final_yards == 5  # 8 + (-3)
    
    def test_green_vs_qt(self):
        """Green # vs QT should use QT."""
        result = apply_priority_chart("8", "QT")
        assert result.priority == PriorityResult.QT
        assert result.use_qt_column is True
    
    def test_green_vs_black_on_pass_is_incomplete(self):
        """Green # vs BLACK on passing play should be incomplete."""
        result = apply_priority_chart("8", "BLACK")
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is True
        assert result.final_yards == 0
    
    def test_green_vs_black_on_run_uses_offense(self):
        """Green # vs BLACK on running play should use offense result."""
        result = apply_priority_chart("8", "BLACK", is_passing_play=False)
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == 8
    
    def test_green_vs_int(self):
        """Green # vs INT should use INT (turnover)."""
        result = apply_priority_chart("8", "INT 15")
        assert result.priority == PriorityResult.INT
        assert result.is_turnover is True
    
    def test_green_vs_fumble(self):
        """Green # vs F should use FUMBLE."""
        result = apply_priority_chart("8", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_green_vs_parens(self):
        """Green # vs (#) should use PARENS (defense's parenthesized yards)."""
        result = apply_priority_chart("8", "(2)")
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 2  # Defense's parenthesized number


class TestWhiteNumberOffense:
    """Tests for WHITE_NUMBER (zero/neutral) offense results."""
    
    def test_white_vs_green(self):
        """White # vs Green # should use OFFENSE."""
        result = apply_priority_chart("0", "5")
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == 0
    
    def test_white_vs_white_adds(self):
        """White # vs White # should ADD."""
        result = apply_priority_chart("0", "0")
        assert result.priority == PriorityResult.ADD
        assert result.final_yards == 0
    
    def test_white_vs_red(self):
        """White # vs Red # should use DEFENSE (defense wins over no gain)."""
        result = apply_priority_chart("0", "-3")
        assert result.priority == PriorityResult.DEFENSE
        assert result.final_yards == -3
    
    def test_white_vs_qt(self):
        """White # vs QT should use QT."""
        result = apply_priority_chart("0", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_white_vs_black(self):
        """White # vs BLACK should use OFFENSE."""
        result = apply_priority_chart("0", "BLACK")
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == 0
    
    def test_white_vs_int(self):
        """White # vs INT should use INT."""
        result = apply_priority_chart("0", "INT 10")
        assert result.priority == PriorityResult.INT
    
    def test_white_vs_fumble(self):
        """White # vs F should use FUMBLE."""
        result = apply_priority_chart("0", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_white_vs_parens(self):
        """White # vs (#) should use PARENS (defense's parenthesized yards)."""
        result = apply_priority_chart("0", "(5)")
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 5  # Defense's parenthesized number


class TestRedNumberOffense:
    """Tests for RED_NUMBER (negative yardage) offense results."""
    
    def test_red_vs_green(self):
        """Red # vs Green # should use OFFENSE."""
        result = apply_priority_chart("-3", "5")
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == -3
    
    def test_red_vs_white(self):
        """Red # vs White # should use DEFENSE (defense wins)."""
        result = apply_priority_chart("-3", "0")
        assert result.priority == PriorityResult.DEFENSE
        assert result.final_yards == 0
    
    def test_red_vs_red_adds(self):
        """Red # vs Red # should ADD."""
        result = apply_priority_chart("-3", "-2")
        assert result.priority == PriorityResult.ADD
        assert result.final_yards == -5
    
    def test_red_vs_qt(self):
        """Red # vs QT should use QT."""
        result = apply_priority_chart("-3", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_red_vs_black(self):
        """Red # vs BLACK should use OFFENSE."""
        result = apply_priority_chart("-3", "BLACK")
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == -3
    
    def test_red_vs_int(self):
        """Red # vs INT should use INT."""
        result = apply_priority_chart("-3", "INT 20")
        assert result.priority == PriorityResult.INT
    
    def test_red_vs_fumble(self):
        """Red # vs F should use FUMBLE."""
        result = apply_priority_chart("-3", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_red_vs_parens(self):
        """Red # vs (#) should use PARENS (defense's parenthesized yards)."""
        result = apply_priority_chart("-3", "(4)")
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 4  # Defense's parenthesized number


class TestQTOffense:
    """Tests for QT (quarterback trouble) offense results."""
    
    def test_qt_vs_green(self):
        """QT vs Green # should use QT."""
        result = apply_priority_chart("QT", "5")
        assert result.priority == PriorityResult.QT
    
    def test_qt_vs_white(self):
        """QT vs White # should use QT."""
        result = apply_priority_chart("QT", "0")
        assert result.priority == PriorityResult.QT
    
    def test_qt_vs_red(self):
        """QT vs Red # should use QT."""
        result = apply_priority_chart("QT", "-3")
        assert result.priority == PriorityResult.QT
    
    def test_qt_vs_qt(self):
        """QT vs QT should use QT."""
        result = apply_priority_chart("QT", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_qt_vs_black(self):
        """QT vs BLACK should use QT."""
        result = apply_priority_chart("QT", "BLACK")
        assert result.priority == PriorityResult.QT
    
    def test_qt_vs_int(self):
        """QT vs INT should use INT."""
        result = apply_priority_chart("QT", "INT 15")
        assert result.priority == PriorityResult.INT
    
    def test_qt_vs_fumble(self):
        """QT vs F should use FUMBLE."""
        result = apply_priority_chart("QT", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_qt_vs_parens(self):
        """QT vs (#) should use PARENS."""
        result = apply_priority_chart("QT", "(3)")
        assert result.priority == PriorityResult.PARENS


class TestBlackOffense:
    """Tests for BLACK (empty/incomplete) offense results."""
    
    def test_black_vs_green(self):
        """BLACK vs Green # should use BLACK (incomplete for pass)."""
        result = apply_priority_chart("BLACK", "5", is_passing_play=True)
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is True
    
    def test_black_vs_white(self):
        """BLACK vs White # should use BLACK."""
        result = apply_priority_chart("BLACK", "0", is_passing_play=True)
        assert result.priority == PriorityResult.BLACK
    
    def test_black_vs_red(self):
        """BLACK vs Red # should use BLACK."""
        result = apply_priority_chart("BLACK", "-3", is_passing_play=True)
        assert result.priority == PriorityResult.BLACK
    
    def test_black_vs_qt(self):
        """BLACK vs QT should use QT."""
        result = apply_priority_chart("BLACK", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_black_vs_black_passing(self):
        """BLACK vs BLACK on passing play should be incomplete."""
        result = apply_priority_chart("BLACK", "", is_passing_play=True)
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is True
    
    def test_black_vs_black_running(self):
        """BLACK vs BLACK on running play should be no gain."""
        result = apply_priority_chart("BLACK", "", is_passing_play=False)
        assert result.priority == PriorityResult.BLACK
        assert result.is_incomplete is False
        assert result.final_yards == 0
    
    def test_black_vs_int(self):
        """BLACK vs INT should use INT."""
        result = apply_priority_chart("BLACK", "INT 20")
        assert result.priority == PriorityResult.INT
    
    def test_black_vs_fumble(self):
        """BLACK vs F should use FUMBLE."""
        result = apply_priority_chart("BLACK", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_black_vs_parens(self):
        """BLACK vs (#) should use PARENS with defense yards."""
        result = apply_priority_chart("BLACK", "(4)")
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 4  # Defense's parenthesized number


class TestINTOffense:
    """Tests for INT (interception) offense results."""
    
    def test_int_vs_green(self):
        """INT vs Green # should use INT."""
        result = apply_priority_chart("INT 15", "5")
        assert result.priority == PriorityResult.INT
    
    def test_int_vs_white(self):
        """INT vs White # should use INT."""
        result = apply_priority_chart("INT 15", "0")
        assert result.priority == PriorityResult.INT
    
    def test_int_vs_red(self):
        """INT vs Red # should use INT."""
        result = apply_priority_chart("INT 15", "-3")
        assert result.priority == PriorityResult.INT
    
    def test_int_vs_qt(self):
        """INT vs QT should use QT."""
        result = apply_priority_chart("INT 15", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_int_vs_black(self):
        """INT vs BLACK should use INT."""
        result = apply_priority_chart("INT 15", "BLACK")
        assert result.priority == PriorityResult.INT
    
    def test_int_vs_int(self):
        """INT vs INT should use D_INT (defense interception)."""
        result = apply_priority_chart("INT 15", "INT 10")
        assert result.priority == PriorityResult.D_INT
    
    def test_int_vs_fumble(self):
        """INT vs F should use FUMBLE."""
        result = apply_priority_chart("INT 15", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_int_vs_parens(self):
        """INT vs (#) should use PARENS."""
        result = apply_priority_chart("INT 15", "(3)")
        assert result.priority == PriorityResult.PARENS


class TestFumbleOffense:
    """Tests for F (fumble) offense results - fumble almost always wins."""
    
    def test_fumble_vs_green(self):
        """F vs Green # should use FUMBLE."""
        result = apply_priority_chart("F", "5")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_white(self):
        """F vs White # should use FUMBLE."""
        result = apply_priority_chart("F", "0")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_red(self):
        """F vs Red # should use FUMBLE."""
        result = apply_priority_chart("F", "-3")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_qt(self):
        """F vs QT should use FUMBLE."""
        result = apply_priority_chart("F", "QT")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_black(self):
        """F vs BLACK should use FUMBLE."""
        result = apply_priority_chart("F", "BLACK")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_int(self):
        """F vs INT should use FUMBLE."""
        result = apply_priority_chart("F", "INT 10")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_fumble(self):
        """F vs F should use FUMBLE."""
        result = apply_priority_chart("F", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_vs_parens(self):
        """F vs (#) should use FUMBLE."""
        result = apply_priority_chart("F", "(3)")
        assert result.priority == PriorityResult.FUMBLE


class TestFumblePlusOffense:
    """Tests for F+# (fumble with positive yardage) offense results."""
    
    def test_fumble_plus_vs_green(self):
        """F+# vs Green # should use FUMBLE."""
        result = apply_priority_chart("F + 3", "5")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_plus_vs_white(self):
        """F+# vs White # should use FUMBLE_PLUS."""
        result = apply_priority_chart("F + 3", "0")
        assert result.priority == PriorityResult.FUMBLE_PLUS
    
    def test_fumble_plus_vs_red(self):
        """F+# vs Red # should use FUMBLE_MINUS."""
        result = apply_priority_chart("F + 3", "-2")
        assert result.priority == PriorityResult.FUMBLE_MINUS
    
    def test_fumble_plus_vs_qt(self):
        """F+# vs QT should use QT."""
        result = apply_priority_chart("F + 3", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_fumble_plus_vs_black(self):
        """F+# vs BLACK should use FUMBLE."""
        result = apply_priority_chart("F + 3", "BLACK")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_plus_vs_int(self):
        """F+# vs INT should use INT."""
        result = apply_priority_chart("F + 3", "INT 10")
        assert result.priority == PriorityResult.INT
    
    def test_fumble_plus_vs_fumble(self):
        """F+# vs F should use D_FUMBLE."""
        result = apply_priority_chart("F + 3", "F")
        assert result.priority == PriorityResult.D_FUMBLE
    
    def test_fumble_plus_vs_parens(self):
        """F+# vs (#) should use FUMBLE."""
        result = apply_priority_chart("F + 3", "(3)")
        assert result.priority == PriorityResult.FUMBLE


class TestFumbleMinusOffense:
    """Tests for F-# (fumble with negative yardage) offense results."""
    
    def test_fumble_minus_vs_green(self):
        """F-# vs Green # should use FUMBLE."""
        result = apply_priority_chart("F - 3", "5")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_minus_vs_white(self):
        """F-# vs White # should use FUMBLE_PLUS."""
        result = apply_priority_chart("F - 3", "0")
        assert result.priority == PriorityResult.FUMBLE_PLUS
    
    def test_fumble_minus_vs_red(self):
        """F-# vs Red # should use FUMBLE_MINUS."""
        result = apply_priority_chart("F - 3", "-2")
        assert result.priority == PriorityResult.FUMBLE_MINUS
    
    def test_fumble_minus_vs_qt(self):
        """F-# vs QT should use QT."""
        result = apply_priority_chart("F - 3", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_fumble_minus_vs_black(self):
        """F-# vs BLACK should use FUMBLE."""
        result = apply_priority_chart("F - 3", "BLACK")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_fumble_minus_vs_int(self):
        """F-# vs INT should use INT."""
        result = apply_priority_chart("F - 3", "INT 10")
        assert result.priority == PriorityResult.INT
    
    def test_fumble_minus_vs_fumble(self):
        """F-# vs F should use D_FUMBLE."""
        result = apply_priority_chart("F - 3", "F")
        assert result.priority == PriorityResult.D_FUMBLE
    
    def test_fumble_minus_vs_parens(self):
        """F-# vs (#) should use FUMBLE."""
        result = apply_priority_chart("F - 3", "(3)")
        assert result.priority == PriorityResult.FUMBLE


class TestParensOffense:
    """Tests for (#) parentheses offense results."""
    
    def test_parens_vs_green(self):
        """(#) vs Green # should use OFFENSE."""
        result = apply_priority_chart("(5)", "3")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_parens_vs_white(self):
        """(#) vs White # should use OFFENSE (parentheses takes precedence)."""
        result = apply_priority_chart("(5)", "0")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_parens_vs_red(self):
        """(#) vs Red # should use PARENS (parentheses takes precedence over negative)."""
        result = apply_priority_chart("(5)", "-2")
        assert result.priority == PriorityResult.PARENS
    
    def test_parens_vs_qt(self):
        """(#) vs QT should use QT."""
        result = apply_priority_chart("(5)", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_parens_vs_black(self):
        """(#) vs BLACK should use OFFENSE."""
        result = apply_priority_chart("(5)", "BLACK")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_parens_vs_int(self):
        """(#) vs INT should use INT."""
        result = apply_priority_chart("(5)", "INT 10")
        assert result.priority == PriorityResult.INT
    
    def test_parens_vs_fumble(self):
        """(#) vs F should use FUMBLE."""
        result = apply_priority_chart("(5)", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_parens_vs_parens(self):
        """(#) vs (#) should use PARENS."""
        result = apply_priority_chart("(5)", "(3)")
        assert result.priority == PriorityResult.PARENS


class TestBreakawayOffense:
    """Tests for B (breakaway) offense results."""
    
    def test_breakaway_vs_green(self):
        """B vs Green # should use OFFENSE_WITH_B."""
        result = apply_priority_chart("B", "5")
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_white(self):
        """B vs White # should use OFFENSE_WITH_B."""
        result = apply_priority_chart("B", "0")
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_red(self):
        """B vs Red # should use OFFENSE_WITH_B."""
        result = apply_priority_chart("B", "-3")
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_qt(self):
        """B vs QT should use QT."""
        result = apply_priority_chart("B", "QT")
        assert result.priority == PriorityResult.QT
    
    def test_breakaway_vs_black(self):
        """B vs BLACK should use OFFENSE_WITH_B."""
        result = apply_priority_chart("B", "BLACK")
        assert result.priority == PriorityResult.OFFENSE_WITH_B
    
    def test_breakaway_vs_int(self):
        """B vs INT should use INT."""
        result = apply_priority_chart("B", "INT 10")
        assert result.priority == PriorityResult.INT
    
    def test_breakaway_vs_fumble(self):
        """B vs F should use FUMBLE."""
        result = apply_priority_chart("B", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_breakaway_vs_parens(self):
        """B vs (#) should use PARENS (no breakaway)."""
        result = apply_priority_chart("B", "(3)")
        assert result.priority == PriorityResult.PARENS
        assert result.use_breakaway is False


class TestTDOffense:
    """Tests for TD (touchdown) offense results - TD generally wins."""
    
    def test_td_vs_green(self):
        """TD vs Green # should use OFFENSE (TD)."""
        result = apply_priority_chart("TD", "5")
        assert result.priority == PriorityResult.OFFENSE
        assert result.is_touchdown is True
    
    def test_td_vs_white(self):
        """TD vs White # should use OFFENSE (TD)."""
        result = apply_priority_chart("TD", "0")
        assert result.priority == PriorityResult.OFFENSE
        assert result.is_touchdown is True
    
    def test_td_vs_red(self):
        """TD vs Red # should use OFFENSE (TD)."""
        result = apply_priority_chart("TD", "-3")
        assert result.priority == PriorityResult.OFFENSE
        assert result.is_touchdown is True
    
    def test_td_vs_qt(self):
        """TD vs QT should use OFFENSE (TD)."""
        result = apply_priority_chart("TD", "QT")
        assert result.priority == PriorityResult.OFFENSE
        assert result.is_touchdown is True
    
    def test_td_vs_black(self):
        """TD vs BLACK should use OFFENSE (TD)."""
        result = apply_priority_chart("TD", "BLACK")
        assert result.priority == PriorityResult.OFFENSE
        assert result.is_touchdown is True
    
    def test_td_vs_int(self):
        """TD vs INT should use INT (turnover beats TD)."""
        result = apply_priority_chart("TD", "INT 10")
        assert result.priority == PriorityResult.INT
    
    def test_td_vs_fumble(self):
        """TD vs F should use FUMBLE (turnover beats TD)."""
        result = apply_priority_chart("TD", "F")
        assert result.priority == PriorityResult.FUMBLE
    
    def test_td_vs_parens(self):
        """TD vs (#) should use OFFENSE (TD wins over parens)."""
        result = apply_priority_chart("TD", "(3)")
        assert result.priority == PriorityResult.OFFENSE
        assert result.is_touchdown is True


class TestPIOffense:
    """Tests for PI (pass interference) offense results - PI always wins."""
    
    def test_pi_vs_green(self):
        """PI vs Green # should use OFFENSE (PI)."""
        result = apply_priority_chart("PI 15", "5")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_white(self):
        """PI vs White # should use OFFENSE (PI)."""
        result = apply_priority_chart("PI 15", "0")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_red(self):
        """PI vs Red # should use OFFENSE (PI)."""
        result = apply_priority_chart("PI 15", "-3")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_qt(self):
        """PI vs QT should use OFFENSE (PI)."""
        result = apply_priority_chart("PI 15", "QT")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_black(self):
        """PI vs BLACK should use OFFENSE (PI)."""
        result = apply_priority_chart("PI 15", "BLACK")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_int(self):
        """PI vs INT should use OFFENSE (PI beats INT)."""
        result = apply_priority_chart("PI 15", "INT 10")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_fumble(self):
        """PI vs F should use OFFENSE (PI beats fumble)."""
        result = apply_priority_chart("PI 15", "F")
        assert result.priority == PriorityResult.OFFENSE
    
    def test_pi_vs_parens(self):
        """PI vs (#) should use OFFENSE (PI)."""
        result = apply_priority_chart("PI 15", "(3)")
        assert result.priority == PriorityResult.OFFENSE


class TestPriorityChartEdgeCaseFixes:
    """
    Tests for edge cases that were previously buggy.
    
    These tests verify the fixes for:
    1. (PARENS_NUMBER, WHITE_NUMBER) - should use OFFENSE, not ADD
    2. (PARENS_NUMBER, RED_NUMBER) - should use PARENS, not ADD
    3. (WHITE_NUMBER, RED_NUMBER) - should use DEFENSE, not ADD
    4. (RED_NUMBER, WHITE_NUMBER) - should use DEFENSE, not ADD
    """

    def test_parens_offense_vs_zero_defense(self):
        """(#) vs 0 - offense parentheses should win, not ADD."""
        result = apply_priority_chart("(5)", "0")
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == 5  # Offense gets their guaranteed yards

    def test_parens_offense_vs_negative_defense(self):
        """(#) vs negative - parentheses should overrule negative, not ADD."""
        result = apply_priority_chart("(5)", "-3")
        assert result.priority == PriorityResult.PARENS
        assert result.final_yards == 5  # Offense gets their guaranteed yards, not -3

    def test_zero_offense_vs_negative_defense(self):
        """0 vs negative - defense should win, not ADD."""
        result = apply_priority_chart("0", "-3")
        assert result.priority == PriorityResult.DEFENSE
        assert result.final_yards == -3  # Defense negative yards apply

    def test_negative_offense_vs_zero_defense(self):
        """negative vs 0 - defense should win, not ADD."""
        result = apply_priority_chart("-3", "0")
        assert result.priority == PriorityResult.DEFENSE
        assert result.final_yards == 0  # Defense 0 (no gain) beats offense -3

    def test_parens_vs_white_adds_correctly_when_appropriate(self):
        """When offense has no parens and defense has positive, ADD works."""
        result = apply_priority_chart("5", "3")
        assert result.priority == PriorityResult.ADD
        assert result.final_yards == 8

    def test_parens_vs_green_still_works(self):
        """(#) vs positive - offense should win."""
        result = apply_priority_chart("(5)", "10")
        assert result.priority == PriorityResult.OFFENSE
        assert result.final_yards == 5

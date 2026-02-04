"""
Priority Chart for combining offensive and defensive results in Paydirt.

The Priority Chart determines the final outcome when both offense and defense
have results that need to be reconciled.
"""
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple


class ResultCategory(Enum):
    """Categories of results for priority chart lookup."""
    GREEN_NUMBER = "green_#"      # Positive yardage in green box
    WHITE_NUMBER = "white_#"      # Yardage in white/empty box
    RED_NUMBER = "red_#"          # Negative yardage in red box
    QT = "QT"                     # Quarterback scramble time
    BLACK = "black"              # Black/empty cell (incomplete)
    INT = "INT"                   # Interception
    FUMBLE = "F"                  # Fumble (F, F+#, F-#)
    FUMBLE_PLUS = "F+#"           # Fumble with positive yardage
    FUMBLE_MINUS = "F-#"          # Fumble with negative yardage
    PARENS_NUMBER = "(#)"         # Number in parentheses (overrule)
    PARENS_TD = "(TD)"            # TD in parentheses (overrule with touchdown)
    PENALTY = "penalty"           # OFF or DEF penalty
    BREAKAWAY = "B"               # Breakaway
    TD = "TD"                     # Touchdown
    PI = "PI"                     # Pass interference


class PriorityResult(Enum):
    """Possible outcomes from priority chart lookup."""
    OFFENSE = "offense"           # Use offense result
    DEFENSE = "defense"           # Use defense result
    ADD = "add"                   # Add the two results together
    QT = "QT"                     # Use QT (roll on QT column)
    INT = "INT"                   # Interception (offense INT)
    D_INT = "D-INT"               # Defense interception
    FUMBLE = "F"                  # Fumble (offense)
    D_FUMBLE = "D-F"              # Defense caused fumble
    FUMBLE_PLUS = "F+#"           # Fumble, add yardage
    FUMBLE_MINUS = "F-#"          # Fumble, subtract yardage
    OFFENSE_WITH_B = "#B"         # Use offense result (breakaway only if offense was B)
    PARENS = "(#)"                # Offense overrules (parentheses)
    PARENS_TD = "(TD)"            # Defense overrules with touchdown
    BLACK = "black"               # Incomplete/no result


def categorize_result(result_str: str) -> Tuple[ResultCategory, Optional[int]]:
    """
    Categorize a result string into a ResultCategory.
    
    Args:
        result_str: The raw result string from the chart
        
    Returns:
        Tuple of (category, optional yardage value)
    """
    if not result_str or result_str.strip() == "":
        return ResultCategory.BLACK, None

    result_str = result_str.strip()

    # Check for penalties first (always take priority)
    if result_str.startswith("OFF") or result_str.startswith("DEF"):
        return ResultCategory.PENALTY, None

    # Check for pass interference
    if result_str.startswith("PI"):
        return ResultCategory.PI, None

    # Check for Touchdown
    if result_str == "TD":
        return ResultCategory.TD, None

    # Check for Breakaway
    if result_str.startswith("B"):
        return ResultCategory.BREAKAWAY, None

    # Check for QT (quarterback scramble)
    if result_str.startswith("QT"):
        return ResultCategory.QT, None

    # Check for Interception
    if result_str.startswith("INT"):
        match = re.match(r'INT\s*(-?\d+)', result_str)
        yards = int(match.group(1)) if match else 0
        return ResultCategory.INT, yards

    # Check for Fumble variants
    fumble_plus = re.match(r'F\s*\+\s*(\d+)', result_str)
    if fumble_plus:
        return ResultCategory.FUMBLE_PLUS, int(fumble_plus.group(1))

    fumble_minus = re.match(r'F\s*-\s*(\d+)', result_str)
    if fumble_minus:
        return ResultCategory.FUMBLE_MINUS, -int(fumble_minus.group(1))

    if result_str == "F":
        return ResultCategory.FUMBLE, 0

    # Check for (TD) - touchdown in parentheses (overrules)
    if result_str == "(TD)":
        return ResultCategory.PARENS_TD, None

    # Check for number in parentheses (defensive modifier that overrules)
    parens_match = re.match(r'\((-?\d+)\)', result_str)
    if parens_match:
        return ResultCategory.PARENS_NUMBER, int(parens_match.group(1))

    # Check for number in square brackets
    bracket_match = re.match(r'\[(-?\d+)\]', result_str)
    if bracket_match:
        # Square brackets also indicate overrule
        return ResultCategory.PARENS_NUMBER, int(bracket_match.group(1))

    # Check for simple number (with optional asterisk)
    num_match = re.match(r'^(-?\d+)\*?$', result_str)
    if num_match:
        yards = int(num_match.group(1))
        if yards > 0:
            return ResultCategory.GREEN_NUMBER, yards
        elif yards < 0:
            return ResultCategory.RED_NUMBER, yards
        else:
            return ResultCategory.WHITE_NUMBER, 0

    # Default to white/neutral
    return ResultCategory.WHITE_NUMBER, None


# Priority Chart lookup table
# Format: PRIORITY_CHART[(offense_category, defense_category)] = result
PRIORITY_CHART = {
    # Green # (positive yardage) offense results
    # When both are positive numbers, ADD them together
    (ResultCategory.GREEN_NUMBER, ResultCategory.GREEN_NUMBER): PriorityResult.ADD,
    (ResultCategory.GREEN_NUMBER, ResultCategory.WHITE_NUMBER): PriorityResult.ADD,
    (ResultCategory.GREEN_NUMBER, ResultCategory.RED_NUMBER): PriorityResult.ADD,
    (ResultCategory.GREEN_NUMBER, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.GREEN_NUMBER, ResultCategory.BLACK): PriorityResult.OFFENSE,
    (ResultCategory.GREEN_NUMBER, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.GREEN_NUMBER, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.GREEN_NUMBER, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.GREEN_NUMBER, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # White # (zero/neutral) offense results
    (ResultCategory.WHITE_NUMBER, ResultCategory.GREEN_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.WHITE_NUMBER, ResultCategory.WHITE_NUMBER): PriorityResult.ADD,
    (ResultCategory.WHITE_NUMBER, ResultCategory.RED_NUMBER): PriorityResult.ADD,
    (ResultCategory.WHITE_NUMBER, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.WHITE_NUMBER, ResultCategory.BLACK): PriorityResult.OFFENSE,
    (ResultCategory.WHITE_NUMBER, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.WHITE_NUMBER, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.WHITE_NUMBER, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.WHITE_NUMBER, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # Red # (negative yardage) offense results
    (ResultCategory.RED_NUMBER, ResultCategory.GREEN_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.RED_NUMBER, ResultCategory.WHITE_NUMBER): PriorityResult.ADD,
    (ResultCategory.RED_NUMBER, ResultCategory.RED_NUMBER): PriorityResult.ADD,
    (ResultCategory.RED_NUMBER, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.RED_NUMBER, ResultCategory.BLACK): PriorityResult.OFFENSE,
    (ResultCategory.RED_NUMBER, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.RED_NUMBER, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.RED_NUMBER, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.RED_NUMBER, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # QT offense results
    (ResultCategory.QT, ResultCategory.GREEN_NUMBER): PriorityResult.QT,
    (ResultCategory.QT, ResultCategory.WHITE_NUMBER): PriorityResult.QT,
    (ResultCategory.QT, ResultCategory.RED_NUMBER): PriorityResult.QT,
    (ResultCategory.QT, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.QT, ResultCategory.BLACK): PriorityResult.QT,
    (ResultCategory.QT, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.QT, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.QT, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.QT, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # Black (empty/incomplete) offense results
    (ResultCategory.BLACK, ResultCategory.GREEN_NUMBER): PriorityResult.BLACK,
    (ResultCategory.BLACK, ResultCategory.WHITE_NUMBER): PriorityResult.BLACK,
    (ResultCategory.BLACK, ResultCategory.RED_NUMBER): PriorityResult.BLACK,
    (ResultCategory.BLACK, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.BLACK, ResultCategory.BLACK): PriorityResult.BLACK,
    (ResultCategory.BLACK, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.BLACK, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.BLACK, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.BLACK, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # INT offense results
    (ResultCategory.INT, ResultCategory.GREEN_NUMBER): PriorityResult.INT,
    (ResultCategory.INT, ResultCategory.WHITE_NUMBER): PriorityResult.INT,
    (ResultCategory.INT, ResultCategory.RED_NUMBER): PriorityResult.INT,
    (ResultCategory.INT, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.INT, ResultCategory.BLACK): PriorityResult.INT,
    (ResultCategory.INT, ResultCategory.INT): PriorityResult.D_INT,
    (ResultCategory.INT, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.INT, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.INT, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # F (Fumble) offense results - Fumble almost always wins
    (ResultCategory.FUMBLE, ResultCategory.GREEN_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.WHITE_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.RED_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.QT): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.BLACK): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.INT): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.PARENS_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # F+# / F-# offense results
    (ResultCategory.FUMBLE_PLUS, ResultCategory.GREEN_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.WHITE_NUMBER): PriorityResult.FUMBLE_PLUS,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.RED_NUMBER): PriorityResult.FUMBLE_MINUS,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.BLACK): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.FUMBLE): PriorityResult.D_FUMBLE,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.PARENS_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE_PLUS, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    (ResultCategory.FUMBLE_MINUS, ResultCategory.GREEN_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.WHITE_NUMBER): PriorityResult.FUMBLE_PLUS,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.RED_NUMBER): PriorityResult.FUMBLE_MINUS,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.BLACK): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.FUMBLE): PriorityResult.D_FUMBLE,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.PARENS_NUMBER): PriorityResult.FUMBLE,
    (ResultCategory.FUMBLE_MINUS, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # (#) parentheses offense results
    (ResultCategory.PARENS_NUMBER, ResultCategory.GREEN_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.PARENS_NUMBER, ResultCategory.WHITE_NUMBER): PriorityResult.ADD,
    (ResultCategory.PARENS_NUMBER, ResultCategory.RED_NUMBER): PriorityResult.ADD,
    (ResultCategory.PARENS_NUMBER, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.PARENS_NUMBER, ResultCategory.BLACK): PriorityResult.OFFENSE,
    (ResultCategory.PARENS_NUMBER, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.PARENS_NUMBER, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.PARENS_NUMBER, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.PARENS_NUMBER, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # Breakaway offense results - when offense result is actually "B"
    # Breakaway is treated like other offense results for priority purposes
    # Defense (#) in parentheses still overrules breakaway
    (ResultCategory.BREAKAWAY, ResultCategory.GREEN_NUMBER): PriorityResult.OFFENSE_WITH_B,
    (ResultCategory.BREAKAWAY, ResultCategory.WHITE_NUMBER): PriorityResult.OFFENSE_WITH_B,
    (ResultCategory.BREAKAWAY, ResultCategory.RED_NUMBER): PriorityResult.OFFENSE_WITH_B,
    (ResultCategory.BREAKAWAY, ResultCategory.QT): PriorityResult.QT,
    (ResultCategory.BREAKAWAY, ResultCategory.BLACK): PriorityResult.OFFENSE_WITH_B,
    (ResultCategory.BREAKAWAY, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.BREAKAWAY, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.BREAKAWAY, ResultCategory.PARENS_NUMBER): PriorityResult.PARENS,
    (ResultCategory.BREAKAWAY, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # TD offense results - TD generally wins
    (ResultCategory.TD, ResultCategory.GREEN_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.TD, ResultCategory.WHITE_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.TD, ResultCategory.RED_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.TD, ResultCategory.QT): PriorityResult.OFFENSE,
    (ResultCategory.TD, ResultCategory.BLACK): PriorityResult.OFFENSE,
    (ResultCategory.TD, ResultCategory.INT): PriorityResult.INT,
    (ResultCategory.TD, ResultCategory.FUMBLE): PriorityResult.FUMBLE,
    (ResultCategory.TD, ResultCategory.PARENS_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.TD, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,

    # PI (Pass Interference) - treated as penalty
    (ResultCategory.PI, ResultCategory.GREEN_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.WHITE_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.RED_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.QT): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.BLACK): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.INT): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.FUMBLE): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.PARENS_NUMBER): PriorityResult.OFFENSE,
    (ResultCategory.PI, ResultCategory.PARENS_TD): PriorityResult.PARENS_TD,
}


@dataclass
class CombinedResult:
    """Result of combining offense and defense using priority chart."""
    priority: PriorityResult
    final_yards: int
    is_turnover: bool
    is_touchdown: bool
    is_incomplete: bool
    use_qt_column: bool
    use_breakaway: bool
    description: str
    offense_result: str
    defense_result: str


def apply_priority_chart(offense_result: str, defense_result: str,
                         offense_yards: Optional[int] = None,
                         defense_yards: Optional[int] = None,
                         is_passing_play: bool = True) -> CombinedResult:
    """
    Apply the Priority Chart to combine offensive and defensive results.
    
    Args:
        offense_result: Raw offensive result string
        defense_result: Raw defensive result string
        offense_yards: Pre-parsed offensive yardage (optional)
        defense_yards: Pre-parsed defensive yardage (optional)
    
    Returns:
        CombinedResult with the final outcome
    """
    # Categorize both results
    off_cat, off_yards = categorize_result(offense_result)
    def_cat, def_yards = categorize_result(defense_result)

    # Use provided yards if available
    if offense_yards is not None:
        off_yards = offense_yards
    if defense_yards is not None:
        def_yards = defense_yards

    # Penalties always take priority
    if off_cat == ResultCategory.PENALTY:
        return CombinedResult(
            priority=PriorityResult.OFFENSE,
            final_yards=off_yards or 0,
            is_turnover=False,
            is_touchdown=False,
            is_incomplete=False,
            use_qt_column=False,
            use_breakaway=False,
            description=f"Penalty: {offense_result}",
            offense_result=offense_result,
            defense_result=defense_result,
        )

    if def_cat == ResultCategory.PENALTY:
        return CombinedResult(
            priority=PriorityResult.DEFENSE,
            final_yards=def_yards or 0,
            is_turnover=False,
            is_touchdown=False,
            is_incomplete=False,
            use_qt_column=False,
            use_breakaway=False,
            description=f"Penalty: {defense_result}",
            offense_result=offense_result,
            defense_result=defense_result,
        )

    # Look up priority
    priority = PRIORITY_CHART.get((off_cat, def_cat), PriorityResult.OFFENSE)

    # Calculate final result based on priority
    final_yards = 0
    is_turnover = False
    is_touchdown = False
    is_incomplete = False
    use_qt = False
    use_breakaway = False
    description = ""

    if priority == PriorityResult.ADD:
        # Add the two yardage values
        off_val = off_yards if off_yards is not None else 0
        def_val = def_yards if def_yards is not None else 0
        final_yards = off_val + def_val
        description = f"Add: {off_val} + {def_val} = {final_yards}"

    elif priority == PriorityResult.OFFENSE:
        final_yards = off_yards if off_yards is not None else 0
        description = f"Offense result: {offense_result}"
        if off_cat == ResultCategory.TD:
            is_touchdown = True

    elif priority == PriorityResult.DEFENSE:
        final_yards = def_yards if def_yards is not None else 0
        description = f"Defense result: {defense_result}"

    elif priority == PriorityResult.PARENS:
        # Parenthesized number on defense means "offense gets these yards"
        # The defense's parenthesized number IS the result - offense gains that yardage
        final_yards = def_yards if def_yards is not None else 0
        description = f"Defense (#) gives offense {final_yards} yards: {defense_result}"

    elif priority == PriorityResult.PARENS_TD:
        # (TD) on defense means touchdown - defense result overrules with TD
        is_touchdown = True
        final_yards = 0  # TD doesn't need yardage
        description = f"Defense (TD) overrules - TOUCHDOWN: {defense_result}"

    elif priority == PriorityResult.QT:
        use_qt = True
        description = "QB Scramble - roll on QT column"

    elif priority == PriorityResult.OFFENSE_WITH_B:
        # #B means use offense result; breakaway only if offense result was actually "B"
        final_yards = off_yards if off_yards is not None else 0
        if off_cat == ResultCategory.BREAKAWAY:
            use_breakaway = True
            description = f"Breakaway! Base: {final_yards}"
        else:
            # Just use the offensive yardage, no breakaway
            description = f"Offense result: {offense_result}"

    elif priority in [PriorityResult.INT, PriorityResult.D_INT]:
        is_turnover = True
        # Use the INT return yards
        if off_cat == ResultCategory.INT:
            final_yards = off_yards if off_yards is not None else 0
        else:
            final_yards = def_yards if def_yards is not None else 0
        description = f"INTERCEPTION! {final_yards} yard return"

    elif priority in [PriorityResult.FUMBLE, PriorityResult.D_FUMBLE,
                      PriorityResult.FUMBLE_PLUS, PriorityResult.FUMBLE_MINUS]:
        is_turnover = True
        # Calculate fumble yardage
        if priority == PriorityResult.FUMBLE_PLUS:
            off_val = off_yards if off_yards is not None else 0
            def_val = def_yards if def_yards is not None else 0
            final_yards = off_val + abs(def_val)
        elif priority == PriorityResult.FUMBLE_MINUS:
            off_val = off_yards if off_yards is not None else 0
            def_val = def_yards if def_yards is not None else 0
            final_yards = off_val - abs(def_val)
        else:
            final_yards = off_yards if off_yards is not None else 0
        description = f"FUMBLE! {final_yards} yards before fumble"

    elif priority == PriorityResult.BLACK:
        # BLACK result means incomplete for passing plays, no gain for running plays
        if is_passing_play:
            is_incomplete = True
            description = "Incomplete pass"
        else:
            # Running play with black/black = no gain (tackled at line of scrimmage)
            final_yards = 0
            description = "No gain (tackled at line of scrimmage)"

    return CombinedResult(
        priority=priority,
        final_yards=final_yards,
        is_turnover=is_turnover,
        is_touchdown=is_touchdown,
        is_incomplete=is_incomplete,
        use_qt_column=use_qt,
        use_breakaway=use_breakaway,
        description=description,
        offense_result=offense_result,
        defense_result=defense_result,
    )

"""
Play resolver that uses actual Paydirt team chart data.
Parses chart result strings and determines play outcomes.
Uses the Priority Chart to combine offensive and defensive results.
"""
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from .chart_loader import TeamChart, OffenseChart, DefenseChart
from .priority_chart import apply_priority_chart


class PlayType(Enum):
    """Offensive play types matching the chart columns."""
    LINE_PLUNGE = "line_plunge"
    OFF_TACKLE = "off_tackle"
    END_RUN = "end_run"
    DRAW = "draw"
    SCREEN = "screen"
    SHORT_PASS = "short_pass"
    MEDIUM_PASS = "medium_pass"
    LONG_PASS = "long_pass"
    TE_SHORT_LONG = "te_short_long"
    PUNT = "punt"
    FIELD_GOAL = "field_goal"
    KICKOFF = "kickoff"
    QB_SNEAK = "qb_sneak"  # Special play - uses Line Plunge column, box color only
    HAIL_MARY = "hail_mary"  # End of half/OT desperation pass - uses special table
    SPIKE_BALL = "spike_ball"  # Stop clock - automatic incomplete, minimal time
    QB_KNEEL = "qb_kneel"  # Running out the clock - automatic -2 yards, 40 seconds


class DefenseType(Enum):
    """Defensive formations matching the chart rows."""
    STANDARD = "A"       # Standard defense
    SHORT_YARDAGE = "B"  # Short yardage defense
    SPREAD = "C"         # Spread defense
    SHORT_PASS = "D"     # Short pass defense
    LONG_PASS = "E"      # Long pass defense
    BLITZ = "F"          # Blitz


class ResultType(Enum):
    """Types of play results."""
    YARDS = "yards"              # Simple yardage gain/loss
    BREAKAWAY = "breakaway"      # B - big gain, roll on breakaway chart
    FUMBLE = "fumble"            # F +/- X
    INTERCEPTION = "interception"  # INT X
    TOUCHDOWN = "touchdown"      # TD
    INCOMPLETE = "incomplete"    # INC or empty for pass
    PENALTY_OFFENSE = "off_penalty"  # OFF X
    PENALTY_DEFENSE = "def_penalty"  # DEF X
    PASS_INTERFERENCE = "pass_interference"  # PI X
    QB_SCRAMBLE = "qb_scramble"  # QT - roll on QB time chart
    SACK = "sack"                # Negative yardage on pass
    SAFETY = "safety"            # Ball in end zone


@dataclass
class PlayResult:
    """Result of a play resolution."""
    result_type: ResultType
    yards: int = 0
    description: str = ""
    turnover: bool = False
    first_down: bool = False
    touchdown: bool = False
    raw_result: str = ""
    dice_roll: int = 0
    defense_modifier: str = ""
    # Interception return details (set by game engine)
    int_return_yards: int = 0
    int_return_dice: int = 0
    int_spot: int = 0
    # Fumble recovery details (set by game engine)
    fumble_recovery_roll: int = 0
    fumble_spot: int = 0
    fumble_recovered: bool = False
    fumble_return_yards: int = 0
    fumble_return_dice: int = 0
    # Out of bounds marker (* or †) - affects clock in final minutes
    out_of_bounds: bool = False


@dataclass
class PenaltyOption:
    """A single penalty option that the offended team can choose."""
    penalty_type: str  # "OFF" or "DEF" or "PI"
    raw_result: str  # Original penalty string (e.g., "DEF 5", "OFF 10")
    yards: int  # Penalty yardage
    description: str  # Human-readable description
    auto_first_down: bool = False  # Whether penalty gives automatic first down
    is_pass_interference: bool = False  # PI has special handling


@dataclass
class PenaltyChoice:
    """
    Result of a play where a penalty occurred.
    
    Per Paydirt rules (PENALTY PROCEDURE):
    - When a penalty occurs, offense rerolls (defense keeps original)
    - Results are combined via Priority Chart
    - Offended team chooses: play result (down counts) OR penalty (down replayed)
    - If multiple penalties, offended team picks ONE (not combined)
    - If offsetting penalties, down is replayed
    - If PI, no rerolls - defensive result cancelled, incomplete pass
    """
    # The play result after rerolling (if applicable)
    play_result: PlayResult
    # Available penalty options (may be multiple if offense rerolled into more penalties)
    penalty_options: List[PenaltyOption] = field(default_factory=list)
    # Who is the offended team? "offense" or "defense"
    offended_team: str = ""
    # Are there offsetting penalties?
    offsetting: bool = False
    # Was this a PI situation (special handling)?
    is_pass_interference: bool = False
    # Original defense result (kept during rerolls)
    original_defense_result: str = ""
    # All reroll descriptions for logging
    reroll_log: List[str] = field(default_factory=list)


def roll_dice() -> int:
    """Roll two six-sided dice and return sum (2-12)."""
    return random.randint(1, 6) + random.randint(1, 6)


def roll_d10() -> int:
    """Roll a single d10 (0-9, where 0 = 10)."""
    result = random.randint(0, 9)
    return 10 if result == 0 else result


def roll_chart_dice() -> tuple[int, str]:
    """
    Roll dice for chart lookup (10-39).
    
    Paydirt offensive dice:
    - Black die (tens digit): faces 1, 1, 2, 2, 3, 3 -> determines 10s, 20s, or 30s
    - Two White dice (ones digit): each 0-4, sum gives 0-8 (capped at 9 for ones digit)
    
    Result = (Black * 10) + min(White1 + White2, 9)
    Range: 10+0=10 to 30+9=39
    
    Probability distribution:
    - 10s (Black=1): 2/6 = 33%
    - 20s (Black=2): 2/6 = 33%
    - 30s (Black=3): 2/6 = 33%
    
    Returns:
        Tuple of (result, description string showing dice breakdown)
    """
    # Black die: 1, 1, 2, 2, 3, 3
    black_die_faces = [1, 1, 2, 2, 3, 3]
    black = random.choice(black_die_faces)

    # Two white dice: each 0-4 (sum 0-8, or 0-5 capped at 9)
    white1 = random.randint(0, 5)
    white2 = random.randint(0, 5)
    white_sum = min(white1 + white2, 9)  # Cap at 9 to stay in 10-39 range

    # Combine: tens digit from black, ones digit from sum of whites
    result = (black * 10) + white_sum
    desc = f"B{black}+W{white1}+W{white2}={result}"
    return result, desc


def roll_white_dice() -> tuple[int, str]:
    """
    Roll only the white offensive dice (for end zone distance per rule VI-12-D-ii).
    
    Two white dice: each 0-5, sum gives 0-10.
    Used to determine how far into the end zone a fumble is recovered.
    
    Returns: (total, description)
    """
    white1 = random.randint(0, 5)
    white2 = random.randint(0, 5)
    total = white1 + white2
    desc = f"W{white1}+W{white2}={total}"
    return total, desc


def roll_offensive_dice_detailed() -> tuple[int, int, int, int, int, str]:
    """
    Roll offensive dice and return all components for variable yardage calculations.
    
    Returns:
        Tuple of (total, black, white1, white2, direct_sum, description)
        - total: Normal offensive total (10-39)
        - black: Black die value (1, 2, or 3)
        - white1: First white die value (0-5)
        - white2: Second white die value (0-5)
        - direct_sum: Sum of all three dice (black + white1 + white2)
        - description: String showing dice breakdown
    """
    black_die_faces = [1, 1, 2, 2, 3, 3]
    black = random.choice(black_die_faces)
    white1 = random.randint(0, 5)
    white2 = random.randint(0, 5)
    white_sum = min(white1 + white2, 9)

    total = (black * 10) + white_sum
    direct_sum = black + white1 + white2
    desc = f"B{black}+W{white1}+W{white2}={total} (DS={direct_sum})"

    return total, black, white1, white2, direct_sum, desc


def resolve_variable_yardage(result_str: str) -> tuple[int, str]:
    """
    Resolve variable yardage entries per official rules.
    
    Variable yardage symbols:
    - DS: Direct Sum of the three dice (1-13 range)
    - X: 40 minus the normal offensive total (1-30 range)
    - T1: The normal offensive total (10-39)
    - T2: Total of two consecutive offensive dice rolls (20-78)
    - T3: Total of three consecutive offensive dice rolls (30-117)
    
    Negative versions (-DS, -X, -T1, etc.) return negative yardage.
    In CSV files, negative entries may be stored as "DS-" instead of "-DS".
    
    Args:
        result_str: The variable yardage symbol (e.g., "DS", "T1", "-T2", "X-")
    
    Returns:
        Tuple of (yardage, description)
    """
    result_str = result_str.strip().upper()

    # Check for negative (either prefix "-" or suffix "-")
    is_negative = result_str.startswith('-') or result_str.endswith('-')
    clean_str = result_str.replace('-', '').strip()

    yards = 0
    desc = ""

    if clean_str == "DS":
        # Direct Sum: add the three dice values
        total, black, white1, white2, direct_sum, roll_desc = roll_offensive_dice_detailed()
        yards = direct_sum
        desc = f"DS={direct_sum} ({roll_desc})"

    elif clean_str == "X":
        # X = 40 minus normal offensive total
        total, roll_desc = roll_chart_dice()
        yards = 40 - total
        desc = f"X=40-{total}={yards} ({roll_desc})"

    elif clean_str == "T1":
        # T1 = normal offensive total
        total, roll_desc = roll_chart_dice()
        yards = total
        desc = f"T1={total} ({roll_desc})"

    elif clean_str == "T2":
        # T2 = sum of two consecutive rolls
        total1, desc1 = roll_chart_dice()
        total2, desc2 = roll_chart_dice()
        yards = total1 + total2
        desc = f"T2={total1}+{total2}={yards}"

    elif clean_str == "T3":
        # T3 = sum of three consecutive rolls
        total1, desc1 = roll_chart_dice()
        total2, desc2 = roll_chart_dice()
        total3, desc3 = roll_chart_dice()
        yards = total1 + total2 + total3
        desc = f"T3={total1}+{total2}+{total3}={yards}"

    else:
        # Unknown symbol - return 0
        return 0, f"Unknown variable yardage: {result_str}"

    if is_negative:
        yards = -yards
        desc = f"-{desc}"

    return yards, desc


def is_variable_yardage(result_str: str) -> bool:
    """Check if a result string contains a variable yardage symbol."""
    if not result_str:
        return False
    clean = result_str.strip().upper().replace('-', '').replace('+', '').strip()
    return clean in ['DS', 'X', 'T1', 'T2', 'T3']


def parse_result_string(result_str: str) -> PlayResult:
    """
    Parse a chart result string into a PlayResult.
    
    Examples:
    - "5" -> 5 yards gain
    - "-3" -> 3 yards loss
    - "B" -> Breakaway
    - "B*" -> Breakaway with modifier
    - "OFF 10" -> Offensive penalty, 10 yards
    - "DEF 5" -> Defensive penalty, 5 yards
    - "DEF 5X" -> Defensive penalty, 5 yards + extra roll
    - "F + 2" -> Fumble, +2 yards before fumble
    - "F - 4" -> Fumble, -4 yards before fumble
    - "INT 11" -> Interception, 11 yard return
    - "INT -1" -> Interception, -1 yard return (or at the 1)
    - "PI 37" -> Pass interference, 37 yards
    - "TD" -> Touchdown
    - "QT" -> QB scramble time
    - "(3)" -> Defensive modifier, subtract 3 from offense result
    - "" or empty -> Incomplete pass / no result
    """
    if not result_str or result_str.strip() == "":
        return PlayResult(ResultType.INCOMPLETE, 0, "Incomplete", raw_result=result_str)

    result_str = result_str.strip()

    # Check for Breakaway
    if result_str.startswith("B"):
        return PlayResult(ResultType.BREAKAWAY, 0, "Breakaway!", raw_result=result_str)

    # Check for Touchdown
    if result_str == "TD":
        return PlayResult(ResultType.TOUCHDOWN, 0, "TOUCHDOWN!", touchdown=True, raw_result=result_str)

    # Check for QB scramble time
    if result_str.startswith("QT"):
        return PlayResult(ResultType.QB_SCRAMBLE, 0, "QB scrambles", raw_result=result_str)

    # Check for Fumble (F + X or F - X)
    fumble_match = re.match(r'F\s*([+-])\s*(\d+)', result_str)
    if fumble_match:
        sign = 1 if fumble_match.group(1) == '+' else -1
        yards = sign * int(fumble_match.group(2))
        return PlayResult(ResultType.FUMBLE, yards, f"FUMBLE! ({yards:+d} yards)",
                         turnover=True, raw_result=result_str)

    # Check for Interception (INT X)
    int_match = re.match(r'INT\s*(-?\d+)', result_str)
    if int_match:
        return_yards = int(int_match.group(1))
        return PlayResult(ResultType.INTERCEPTION, return_yards,
                         f"INTERCEPTED! {return_yards} yard return",
                         turnover=True, raw_result=result_str)

    # Check for Pass Interference (PI X)
    pi_match = re.match(r'PI\s*(\d+)', result_str)
    if pi_match:
        yards = int(pi_match.group(1))
        return PlayResult(ResultType.PASS_INTERFERENCE, yards,
                         f"Pass interference! {yards} yards", raw_result=result_str)

    # Check for Offensive Penalty (OFF X or OFF S or OFF R)
    # Full Feature Method: S = scrimmage penalty, R = return penalty
    # The actual yardage is determined by rolling dice again
    off_match = re.match(r'OFF\s*(\d+|S|R)', result_str, re.IGNORECASE)
    if off_match:
        pen_val = off_match.group(1).upper()
        # Store the penalty code type for Full Feature Method resolution
        # Yards here are placeholder - actual yardage determined by penalty_handler
        if pen_val == 'S':
            desc = "Offensive penalty (scrimmage)"
        elif pen_val == 'R':
            desc = "Offensive penalty (return)"
        else:
            desc = f"Offensive penalty, {pen_val} yards"
        return PlayResult(ResultType.PENALTY_OFFENSE, 0, desc, raw_result=result_str)

    # Check for Defensive Penalty (DEF X or DEF S or DEF R)
    # Full Feature Method: S = scrimmage penalty, R = return penalty
    # The actual yardage is determined by rolling dice again
    def_match = re.match(r'DEF\s*(\d+|S|R)(X|Y)?', result_str, re.IGNORECASE)
    if def_match:
        pen_val = def_match.group(1).upper()
        modifier = def_match.group(2).upper() if def_match.group(2) else None
        # Store the penalty code type for Full Feature Method resolution
        if pen_val == 'S':
            desc = "Defensive penalty (scrimmage)"
        elif pen_val == 'R':
            desc = "Defensive penalty (return)"
        else:
            desc = f"Defensive penalty, {pen_val} yards"
        if modifier:
            desc += f" [{modifier}]"
        return PlayResult(ResultType.PENALTY_DEFENSE, 0, desc, raw_result=result_str)

    # Check for defensive modifier in parentheses (X) or [X]
    mod_match = re.match(r'[\(\[](-?\d+)[\)\]]', result_str)
    if mod_match:
        modifier = int(mod_match.group(1))
        return PlayResult(ResultType.YARDS, 0, f"Modifier: {modifier}",
                         raw_result=result_str, defense_modifier=result_str)

    # Check for out-of-bounds markers (* or †)
    # Per rules: asterisk and dagger indicate play ended out of bounds
    is_out_of_bounds = '*' in result_str or '†' in result_str or '+' in result_str

    # Clean the result string for parsing
    clean_str = result_str.replace('*', '').replace('†', '').replace('+', '').strip()

    # Check for variable yardage symbols (DS, X, T1, T2, T3)
    if is_variable_yardage(clean_str):
        yards, var_desc = resolve_variable_yardage(clean_str)
        if yards > 0:
            desc = f"Gain of {yards} yards ({var_desc})"
        elif yards < 0:
            desc = f"Loss of {abs(yards)} yards ({var_desc})"
        else:
            desc = f"No gain ({var_desc})"
        if is_out_of_bounds:
            desc += " (out of bounds)"
        return PlayResult(ResultType.YARDS, yards, desc, raw_result=result_str, out_of_bounds=is_out_of_bounds)

    # Check for simple yardage (positive or negative number)
    yard_match = re.match(r'^(-?\d+)$', clean_str)
    if yard_match:
        yards = int(yard_match.group(1))
        if yards > 0:
            desc = f"Gain of {yards} yards"
        elif yards < 0:
            desc = f"Loss of {abs(yards)} yards"
        else:
            desc = "No gain"
        if is_out_of_bounds:
            desc += " (out of bounds)"
        return PlayResult(ResultType.YARDS, yards, desc, raw_result=result_str, out_of_bounds=is_out_of_bounds)

    # Default: try to parse as number
    try:
        yards = int(clean_str)
        desc = f"{yards} yards"
        if is_out_of_bounds:
            desc += " (out of bounds)"
        return PlayResult(ResultType.YARDS, yards, desc, raw_result=result_str, out_of_bounds=is_out_of_bounds)
    except ValueError:
        pass

    # Unknown result
    return PlayResult(ResultType.YARDS, 0, f"Unknown: {result_str}", raw_result=result_str)


def get_offense_result(chart: OffenseChart, play_type: PlayType, dice_roll: int) -> str:
    """Get the raw result string from the offense chart."""
    play_charts = {
        PlayType.LINE_PLUNGE: chart.line_plunge,
        PlayType.OFF_TACKLE: chart.off_tackle,
        PlayType.END_RUN: chart.end_run,
        PlayType.DRAW: chart.draw,
        PlayType.SCREEN: chart.screen,
        PlayType.SHORT_PASS: chart.short_pass,
        PlayType.MEDIUM_PASS: chart.medium_pass,
        PlayType.LONG_PASS: chart.long_pass,
        PlayType.TE_SHORT_LONG: chart.te_short_long,
        PlayType.QB_SNEAK: chart.line_plunge,  # QB Sneak uses Line Plunge column
    }

    play_chart = play_charts.get(play_type, {})
    return play_chart.get(dice_roll, "")


def resolve_qb_sneak(chart: OffenseChart, dice_roll: int) -> PlayResult:
    """
    Resolve a QB Sneak play per official rules.
    
    QB Sneak is used to gain a single yard. Only the box COLOR matters:
    - Green boxes (positive yardage) = 1 yard gain
    - White/Yellow boxes (zero/small/penalty) = No gain
    - Red boxes (fumble results) = Fumble at line of scrimmage
    
    The defensive result is automatically "No Change" - defense doesn't participate.
    
    Args:
        chart: The offensive team's chart
        dice_roll: The offensive dice roll result
    
    Returns:
        PlayResult with 1 yard, 0 yards, or fumble
    """
    # Get the Line Plunge result for this roll
    result_str = chart.line_plunge.get(dice_roll, "0")

    if not result_str:
        result_str = "0"

    result_str = str(result_str).strip()

    # Determine box color based on result content
    # Red box = Fumble (F, F+X, F-X)
    if result_str.upper().startswith('F') and not result_str.upper().startswith('OFF'):
        # Fumble at line of scrimmage
        return PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,  # Fumble at LOS
            description="QB Sneak - FUMBLE at line of scrimmage!",
            turnover=True,
            raw_result=result_str,
            dice_roll=dice_roll
        )

    # Check for positive yardage (Green box) = 1 yard gain
    # Green boxes typically have positive numbers
    try:
        # Clean the result string
        clean_str = result_str.replace('*', '').replace('†', '').replace('+', '').strip()

        # Check if it's a simple positive number
        if clean_str.lstrip('-').isdigit():
            value = int(clean_str)
            if value > 0:
                # Green box - 1 yard gain
                return PlayResult(
                    result_type=ResultType.YARDS,
                    yards=1,
                    description="QB Sneak - 1 yard gain",
                    raw_result=result_str,
                    dice_roll=dice_roll
                )
            else:
                # White/Yellow box (zero or negative) - No gain
                return PlayResult(
                    result_type=ResultType.YARDS,
                    yards=0,
                    description="QB Sneak - No gain",
                    raw_result=result_str,
                    dice_roll=dice_roll
                )
    except ValueError:
        pass

    # Check for Breakaway (B, B*) - treat as green box = 1 yard
    if result_str.upper().startswith('B') and not result_str.upper().startswith('BK'):
        return PlayResult(
            result_type=ResultType.YARDS,
            yards=1,
            description="QB Sneak - 1 yard gain",
            raw_result=result_str,
            dice_roll=dice_roll
        )

    # Penalties, interceptions, QT, etc. = White/Yellow box = No gain
    # (OFF, DEF, INT, PI, QT all treated as no gain for QB Sneak)
    return PlayResult(
        result_type=ResultType.YARDS,
        yards=0,
        description="QB Sneak - No gain",
        raw_result=result_str,
        dice_roll=dice_roll
    )


def resolve_hail_mary(dice_roll: int, ball_position: int) -> PlayResult:
    """
    Resolve a Hail Mary pass per official rules.
    
    Hail Mary is available at end of half or overtime. Defense is "blank" (no response).
    
    Dice Total | Result
    -----------|--------
    10-18      | Complete (25 + T1 yards downfield)
    19         | Complete (TD)
    20-23, 26-29 | INT (25 + T1 yards downfield)
    24-25      | QT (Quick Throw - roll again)
    30-38      | INC (Incomplete)
    39         | DEF PI (25 + T1 yards downfield)
    
    T1 = tens digit of dice roll (black die value, 1-3)
    
    Args:
        dice_roll: The offensive dice roll result (10-39)
        ball_position: Current ball position for yardage calculation
    
    Returns:
        PlayResult with the Hail Mary outcome
    """
    # T1 = tens digit (the black die, 1-3)
    # Per rules: yardage is "25 + T1" where T1 is the tens digit
    t1 = dice_roll // 10
    base_yards = 25 + t1  # 25 + 1, 2, or 3 = 26, 27, or 28 yards

    if 10 <= dice_roll <= 18:
        # Complete pass (25 + T1 yards downfield)
        yards = base_yards
        new_position = ball_position + yards
        if new_position >= 100:
            return PlayResult(
                result_type=ResultType.TOUCHDOWN,
                yards=100 - ball_position,
                description=f"Hail Mary COMPLETE for TOUCHDOWN! ({yards} yards)",
                touchdown=True,
                raw_result=f"Hail Mary {dice_roll}",
                dice_roll=dice_roll
            )
        return PlayResult(
            result_type=ResultType.YARDS,
            yards=yards,
            description=f"Hail Mary COMPLETE! {yards} yards downfield",
            raw_result=f"Hail Mary {dice_roll}",
            dice_roll=dice_roll
        )

    elif dice_roll == 19:
        # Automatic touchdown
        return PlayResult(
            result_type=ResultType.TOUCHDOWN,
            yards=100 - ball_position,
            description="Hail Mary COMPLETE for TOUCHDOWN!",
            touchdown=True,
            raw_result=f"Hail Mary {dice_roll}",
            dice_roll=dice_roll
        )

    elif dice_roll in range(20, 24) or dice_roll in range(26, 30):
        # Interception (25 + T1 yards downfield)
        yards = base_yards
        return PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=yards,
            description=f"Hail Mary INTERCEPTED! {yards} yards downfield",
            turnover=True,
            raw_result=f"Hail Mary INT {dice_roll}",
            dice_roll=dice_roll
        )

    elif dice_roll in [24, 25]:
        # QT - Quick Throw (need to roll again)
        return PlayResult(
            result_type=ResultType.YARDS,
            yards=0,
            description="Hail Mary - Quick Throw! Roll again.",
            raw_result=f"Hail Mary QT {dice_roll}",
            dice_roll=dice_roll
        )

    elif 30 <= dice_roll <= 38:
        # Incomplete
        return PlayResult(
            result_type=ResultType.INCOMPLETE,
            yards=0,
            description="Hail Mary INCOMPLETE!",
            raw_result=f"Hail Mary INC {dice_roll}",
            dice_roll=dice_roll
        )

    elif dice_roll == 39:
        # Defensive Pass Interference (25 + T1 yards downfield)
        yards = base_yards
        return PlayResult(
            result_type=ResultType.PASS_INTERFERENCE,
            yards=yards,
            description=f"Hail Mary - PASS INTERFERENCE! {yards} yards downfield",
            raw_result=f"Hail Mary PI {dice_roll}",
            dice_roll=dice_roll
        )

    # Fallback (shouldn't happen with valid dice)
    return PlayResult(
        result_type=ResultType.INCOMPLETE,
        yards=0,
        description=f"Hail Mary - Invalid roll {dice_roll}",
        raw_result=f"Hail Mary {dice_roll}",
        dice_roll=dice_roll
    )


def get_defense_modifier(chart: DefenseChart, defense_type: DefenseType,
                         play_column: int, sub_roll: int) -> str:
    """
    Get the defensive modifier from the defense chart.
    
    Args:
        chart: The defense chart
        defense_type: The defensive formation (A-F)
        play_column: The offensive play column (1-9)
        sub_roll: The sub-row within the formation (1-5)
    
    Returns:
        The modifier string (e.g., "(3)", "-2", "INT 27")
    """
    key = (defense_type.value, sub_roll)
    modifiers = chart.modifiers.get(key, {})
    return modifiers.get(play_column, "")


def resolve_breakaway(chart: OffenseChart, dice_roll: int) -> int:
    """
    Resolve a breakaway result using the B column.
    Returns the yardage gained.
    """
    b_result = chart.breakaway.get(dice_roll, "")
    if b_result:
        try:
            return int(b_result)
        except ValueError:
            pass
    # Default breakaway yardage if not found
    return random.randint(15, 40)


def resolve_qb_scramble(chart: OffenseChart, dice_roll: int) -> int:
    """
    Resolve a QB scramble using the QT column.
    Returns the yardage (positive = gain, negative = sack).
    """
    qt_result = chart.qb_time.get(dice_roll, "")
    if qt_result:
        try:
            return int(qt_result)
        except ValueError:
            pass
    # Default scramble result
    return random.randint(-5, 10)


def resolve_play(offense_chart: TeamChart, defense_chart: TeamChart,
                play_type: PlayType, defense_type: DefenseType) -> PlayResult:
    """
    Resolve a play using the actual team charts and Priority Chart.
    
    Per Paydirt rules:
    1. Roll OFFENSIVE dice and look up result on offensive team chart
    2. Roll DEFENSIVE dice and look up result on defensive team chart
    3. Use Priority Chart to combine the two results
    
    Args:
        offense_chart: The offensive team's chart
        defense_chart: The defensive team's chart  
        play_type: The offensive play called
        defense_type: The defensive formation
    
    Returns:
        PlayResult with the outcome
    """
    # Roll OFFENSIVE dice (10-39 range)
    # Black die (tens): 1,1,2,2,3,3 + Two White dice (ones): 0-5 each
    off_dice_roll, off_dice_desc = roll_chart_dice()

    # Roll DEFENSIVE dice - special Paydirt dice that sum to 1-5
    # Red die faces: 1, 1, 1, 2, 2, 3
    # Green die faces: 0, 0, 0, 0, 1, 2
    red_die_faces = [1, 1, 1, 2, 2, 3]
    green_die_faces = [0, 0, 0, 0, 1, 2]

    def_red = random.choice(red_die_faces)
    def_green = random.choice(green_die_faces)
    sub_row = def_red + def_green  # Range 1-5, maps directly to defense chart row

    # Get offensive result from offensive team's chart
    off_result_str = get_offense_result(offense_chart.offense, play_type, off_dice_roll)

    # Get defensive result from defensive team's chart
    play_column = _play_type_to_column(play_type)
    def_result_str = get_defense_modifier(defense_chart.defense, defense_type,
                                          play_column, sub_row)

    # Apply Priority Chart to combine results
    # Pass whether this is a passing play to handle BLACK results correctly
    combined = apply_priority_chart(off_result_str, def_result_str,
                                    is_passing_play=is_passing_play(play_type))

    # Build the PlayResult based on combined outcome
    result = PlayResult(
        result_type=ResultType.YARDS,
        yards=combined.final_yards,
        description=combined.description,
        turnover=combined.is_turnover,
        touchdown=combined.is_touchdown,
        raw_result=off_result_str,
        dice_roll=off_dice_roll,
        defense_modifier=def_result_str,
    )

    # Handle special priority outcomes
    if combined.use_qt_column:
        # QT result - roll again on QT column
        qt_roll, qt_desc = roll_chart_dice()
        qt_yards = resolve_qb_scramble(offense_chart.offense, qt_roll)
        result.yards = qt_yards
        result.result_type = ResultType.QB_SCRAMBLE if qt_yards >= 0 else ResultType.SACK
        if qt_yards >= 0:
            result.description = f"QB scrambles for {qt_yards} yards (QT roll: {qt_desc})"
        else:
            result.description = f"QB SACKED for {abs(qt_yards)} yard loss (QT roll: {qt_desc})"

    elif combined.use_breakaway:
        # Breakaway - offense result was "B", roll on B column for yardage
        b_roll, b_desc = roll_chart_dice()
        b_yards = resolve_breakaway(offense_chart.offense, b_roll)
        result.yards = b_yards
        result.result_type = ResultType.BREAKAWAY
        result.description = f"BREAKAWAY! Roll {b_desc} = {b_yards} yards!"

    elif combined.is_turnover:
        if "INT" in off_result_str or "INT" in def_result_str:
            result.result_type = ResultType.INTERCEPTION
        else:
            result.result_type = ResultType.FUMBLE

    elif combined.is_incomplete:
        result.result_type = ResultType.INCOMPLETE
        result.description = "Incomplete pass"

    elif combined.is_touchdown:
        result.result_type = ResultType.TOUCHDOWN
        result.description = "TOUCHDOWN!"

    # Check for penalties in original results (penalties always take priority)
    if off_result_str.startswith("OFF"):
        result.result_type = ResultType.PENALTY_OFFENSE
        pen_match = re.match(r'OFF\s*(\d+)', off_result_str)
        if pen_match:
            result.yards = -int(pen_match.group(1))
        result.description = f"Offensive penalty: {off_result_str}"
    elif off_result_str.startswith("DEF") or def_result_str.startswith("DEF"):
        pen_str = off_result_str if off_result_str.startswith("DEF") else def_result_str
        result.result_type = ResultType.PENALTY_DEFENSE
        pen_match = re.match(r'DEF\s*(\d+)', pen_str)
        if pen_match:
            result.yards = int(pen_match.group(1))
        # Check for X (extra yardage)
        if "X" in pen_str:
            extra = random.randint(1, 25)
            result.yards += extra
            result.description = f"Defensive penalty: {pen_str} + {extra} extra = {result.yards} yards"
        else:
            result.description = f"Defensive penalty: {pen_str}"
    elif off_result_str.startswith("PI"):
        result.result_type = ResultType.PASS_INTERFERENCE
        pi_match = re.match(r'PI\s*(\d+)', off_result_str)
        if pi_match:
            result.yards = int(pi_match.group(1))
        result.description = f"Pass interference: {result.yards} yards"

    # Add dice roll info to description
    result.description += f" [Off: {off_dice_desc}, Def: R{def_red}+G{def_green}={sub_row}]"

    return result


def is_passing_play(play_type: PlayType) -> bool:
    """Determine if a play type is a passing play (vs running play)."""
    passing_plays = {
        PlayType.SHORT_PASS,
        PlayType.MEDIUM_PASS,
        PlayType.LONG_PASS,
        PlayType.TE_SHORT_LONG,
        PlayType.SCREEN,  # Screen is a pass play
        PlayType.HAIL_MARY,
    }
    return play_type in passing_plays


def _play_type_to_column(play_type: PlayType) -> int:
    """Convert play type to chart column number (1-9)."""
    column_map = {
        PlayType.LINE_PLUNGE: 1,
        PlayType.OFF_TACKLE: 2,
        PlayType.END_RUN: 3,
        PlayType.DRAW: 4,
        PlayType.SCREEN: 5,
        PlayType.SHORT_PASS: 6,
        PlayType.MEDIUM_PASS: 7,
        PlayType.LONG_PASS: 8,
        PlayType.TE_SHORT_LONG: 9,
    }
    return column_map.get(play_type, 1)


def resolve_special_teams(chart: TeamChart, play_type: PlayType) -> PlayResult:
    """Resolve a special teams play (kickoff, punt, field goal)."""
    dice_roll, dice_desc = roll_chart_dice()
    special = chart.special_teams

    if play_type == PlayType.KICKOFF:
        result_str = special.kickoff.get(dice_roll, "")
        result = parse_result_string(result_str)
        result.dice_roll = dice_roll
        if result.result_type == ResultType.YARDS or result.result_type == ResultType.INCOMPLETE:
            # Kickoff distance
            try:
                yards = int(result_str) if result_str else 65
            except ValueError:
                yards = 65
            result.yards = yards
            result.description = f"Kickoff {yards} yards"
        return result

    elif play_type == PlayType.PUNT:
        result_str = special.punt.get(dice_roll, "")
        result = parse_result_string(result_str)
        result.dice_roll = dice_roll
        return result

    elif play_type == PlayType.FIELD_GOAL:
        result_str = special.field_goal.get(dice_roll, "")
        result = parse_result_string(result_str)
        result.dice_roll = dice_roll
        return result

    return PlayResult(ResultType.INCOMPLETE, 0, "Unknown special teams play")


def _is_penalty_result(result_str: str) -> tuple[bool, str]:
    """
    Check if a result string is a penalty.
    
    Returns:
        (is_penalty, penalty_type) where penalty_type is "OFF", "DEF", or "PI"
    """
    if not result_str:
        return False, ""
    result_upper = result_str.upper().strip()
    if result_upper.startswith("OFF"):
        return True, "OFF"
    elif result_upper.startswith("DEF"):
        return True, "DEF"
    elif result_upper.startswith("PI"):
        return True, "PI"
    return False, ""


def _create_penalty_option(result_str: str) -> PenaltyOption:
    """Create a PenaltyOption from a penalty result string."""
    result_upper = result_str.upper().strip()

    if result_upper.startswith("PI"):
        # Pass interference
        pi_match = re.match(r'PI\s*(\d+)', result_str, re.IGNORECASE)
        yards = int(pi_match.group(1)) if pi_match else 15
        return PenaltyOption(
            penalty_type="PI",
            raw_result=result_str,
            yards=yards,
            description=f"Pass interference, {yards} yards",
            auto_first_down=True,
            is_pass_interference=True
        )
    elif result_upper.startswith("OFF"):
        # Offensive penalty
        off_match = re.match(r'OFF\s*(\d+|S|R)', result_str, re.IGNORECASE)
        if off_match:
            val = off_match.group(1).upper()
            if val in ('S', 'R'):
                yards = 5  # Placeholder - actual determined by penalty_handler
            else:
                yards = int(val)
        else:
            yards = 5
        return PenaltyOption(
            penalty_type="OFF",
            raw_result=result_str,
            yards=yards,
            description=f"Offensive penalty, {yards} yards"
        )
    elif result_upper.startswith("DEF"):
        # Defensive penalty
        def_match = re.match(r'DEF\s*(\d+|S|R)(X|Y)?', result_str, re.IGNORECASE)
        auto_first = False
        if def_match:
            val = def_match.group(1).upper()
            modifier = def_match.group(2).upper() if def_match.group(2) else None
            if val in ('S', 'R'):
                yards = 5  # Placeholder
            else:
                yards = int(val)
            if modifier == 'X':
                auto_first = True
        else:
            yards = 5
        return PenaltyOption(
            penalty_type="DEF",
            raw_result=result_str,
            yards=yards,
            description=f"Defensive penalty, {yards} yards",
            auto_first_down=auto_first
        )

    # Fallback
    return PenaltyOption(
        penalty_type="",
        raw_result=result_str,
        yards=0,
        description=f"Unknown penalty: {result_str}"
    )


@dataclass
class FieldGoalResult:
    """Result of a field goal attempt with penalty handling."""
    dice_roll: int
    dice_desc: str
    raw_result: str  # The chart result (e.g., "15", "BK -8", "OFF 10")
    chart_yards: int  # Parsed yardage from chart (for success check)
    is_blocked: bool = False
    is_fumble: bool = False
    is_penalty: bool = False
    penalty_options: List[PenaltyOption] = field(default_factory=list)
    offsetting: bool = False
    offended_team: str = ""  # "offense" or "defense"
    reroll_log: List[str] = field(default_factory=list)


def resolve_field_goal_with_penalties(special_teams_chart) -> FieldGoalResult:
    """
    Resolve a field goal attempt with full penalty procedure.
    
    Like normal plays, if a penalty occurs:
    - Offense rerolls until a non-penalty result
    - Collects all penalties encountered
    - Checks for offsetting penalties
    - Returns result allowing offended team to choose
    
    Args:
        special_teams_chart: The kicking team's special teams chart
        
    Returns:
        FieldGoalResult with the outcome and any penalty options
    """
    penalty_options: List[PenaltyOption] = []
    reroll_log: List[str] = []
    has_off_penalty = False
    has_def_penalty = False
    
    max_rerolls = 10  # Safety limit
    reroll_count = 0
    
    while reroll_count < max_rerolls:
        dice_roll, dice_desc = roll_chart_dice()
        fg_result = special_teams_chart.field_goal.get(dice_roll, "")
        
        # Check if this is a penalty result
        is_pen, pen_type = _is_penalty_result(fg_result)
        
        if is_pen:
            reroll_log.append(f"FG roll {dice_desc}: {fg_result} (penalty)")
            
            # Track who committed the penalty
            if pen_type == "OFF":
                has_off_penalty = True
            else:
                has_def_penalty = True
            
            penalty_options.append(_create_penalty_option(fg_result))
            reroll_count += 1
            continue
        else:
            # Non-penalty result - we're done rolling
            reroll_log.append(f"FG roll {dice_desc}: {fg_result}")
            break
    
    # Parse the final result
    is_blocked = "BK" in fg_result.upper()
    is_fumble = bool(re.match(r'^F\s*[+-]', fg_result, re.IGNORECASE))
    
    # Parse chart yards for success check
    chart_yards = 0
    if not is_blocked and not is_fumble and fg_result:
        try:
            chart_yards = int(fg_result.strip())
        except ValueError:
            chart_yards = 0
    
    # Determine offended team and offsetting status
    offended_team = ""
    offsetting = False
    
    if has_off_penalty and has_def_penalty:
        offsetting = True
        offended_team = ""
    elif has_off_penalty:
        offended_team = "defense"
    elif has_def_penalty:
        offended_team = "offense"
    
    return FieldGoalResult(
        dice_roll=dice_roll,
        dice_desc=dice_desc,
        raw_result=fg_result,
        chart_yards=chart_yards,
        is_blocked=is_blocked,
        is_fumble=is_fumble,
        is_penalty=len(penalty_options) > 0,
        penalty_options=penalty_options,
        offsetting=offsetting,
        offended_team=offended_team,
        reroll_log=reroll_log
    )


def resolve_play_with_penalties(offense_chart: TeamChart, defense_chart: DefenseChart,
                                 play_type: PlayType, defense_type: DefenseType) -> PenaltyChoice:
    """
    Resolve a play with full penalty procedure per Paydirt rules.
    
    PENALTY PROCEDURE:
    i. When a penalty occurs, the offense rolls its dice again to determine the offensive result of the
       play; the defense still uses the result of its ORIGINAL roll. These results are then combined 
       according to the Priority Chart, and the offended team may accept either the result of the play 
       (down counts) or the penalty yardage (down replayed).
    
    ii. If the offense reroll results in another penalty, the offense continues rolling until a non-penalty
        result occurs. The offended team may then accept the result of the play (down counts) or any ONE 
        of the penalties (penalty yardages are not combined). If offsetting penalties have occurred, 
        10 seconds elapse on the clock, but the play is cancelled and the down is replayed.
    
    iii. If a PI penalty is rolled, there are no further rerolls; the defensive result is cancelled and 
         the final outcome of the play is an incomplete pass.
    
    Returns:
        PenaltyChoice with play result and penalty options for the offended team to choose from
    """
    # Roll DEFENSIVE dice ONCE - this result is kept throughout
    red_die_faces = [1, 1, 1, 2, 2, 3]
    green_die_faces = [0, 0, 0, 0, 1, 2]
    def_red = random.choice(red_die_faces)
    def_green = random.choice(green_die_faces)
    sub_row = def_red + def_green

    # Get defensive result from defensive team's chart
    play_column = _play_type_to_column(play_type)
    def_result_str = get_defense_modifier(defense_chart.defense, defense_type,
                                          play_column, sub_row)
    original_def_result = def_result_str
    def_dice_desc = f"R{def_red}+G{def_green}={sub_row}"

    # Track penalties encountered
    penalty_options: List[PenaltyOption] = []
    reroll_log: List[str] = []
    has_off_penalty = False
    has_def_penalty = False

    # Check if defense result is a penalty
    is_def_pen, def_pen_type = _is_penalty_result(def_result_str)
    if is_def_pen:
        has_def_penalty = True
        penalty_options.append(_create_penalty_option(def_result_str))

    # Roll OFFENSIVE dice - may need to reroll if penalty
    max_rerolls = 10  # Safety limit
    reroll_count = 0
    off_result_str = ""
    off_dice_roll = 0
    off_dice_desc = ""

    while reroll_count < max_rerolls:
        off_dice_roll, off_dice_desc = roll_chart_dice()
        off_result_str = get_offense_result(offense_chart.offense, play_type, off_dice_roll)

        is_off_pen, off_pen_type = _is_penalty_result(off_result_str)

        if is_off_pen:
            reroll_log.append(f"Offense roll {off_dice_desc}: {off_result_str} (penalty)")

            # Check for PI - special handling, no more rerolls
            if off_pen_type == "PI":
                penalty_options.append(_create_penalty_option(off_result_str))
                # PI cancels defensive result, result is incomplete pass
                play_result = PlayResult(
                    result_type=ResultType.INCOMPLETE,
                    yards=0,
                    description=f"Pass interference - incomplete pass [Off: {off_dice_desc}, Def: {def_dice_desc}]",
                    raw_result=off_result_str,
                    dice_roll=off_dice_roll,
                    defense_modifier=def_result_str
                )
                return PenaltyChoice(
                    play_result=play_result,
                    penalty_options=penalty_options,
                    offended_team="offense",  # Defense committed PI
                    offsetting=False,
                    is_pass_interference=True,
                    original_defense_result=original_def_result,
                    reroll_log=reroll_log
                )

            # Non-PI penalty - add to options and reroll
            # Track who committed the penalty:
            # - "OFF 5" on offense chart = OFFENSE committed penalty (defense offended)
            # - "DEF 5" on offense chart = DEFENSE committed penalty (offense offended)
            if off_pen_type == "OFF":
                has_off_penalty = True
            else:
                has_def_penalty = True
            penalty_options.append(_create_penalty_option(off_result_str))
            reroll_count += 1
            continue
        else:
            # Non-penalty result - we're done rolling
            reroll_log.append(f"Offense roll {off_dice_desc}: {off_result_str}")
            break

    # Now combine the final offense result with the original defense result
    # using the Priority Chart
    combined = apply_priority_chart(off_result_str, def_result_str,
                                    is_passing_play=is_passing_play(play_type))

    # Build the PlayResult based on combined outcome
    play_result = PlayResult(
        result_type=ResultType.YARDS,
        yards=combined.final_yards,
        description=combined.description,
        turnover=combined.is_turnover,
        touchdown=combined.is_touchdown,
        raw_result=off_result_str,
        dice_roll=off_dice_roll,
        defense_modifier=def_result_str,
    )

    # Handle special priority outcomes (QT, Breakaway, etc.)
    if combined.use_qt_column:
        qt_roll, qt_desc = roll_chart_dice()
        qt_yards = resolve_qb_scramble(offense_chart.offense, qt_roll)
        play_result.yards = qt_yards
        play_result.result_type = ResultType.QB_SCRAMBLE if qt_yards >= 0 else ResultType.SACK
        if qt_yards >= 0:
            play_result.description = f"QB scrambles for {qt_yards} yards (QT roll: {qt_desc})"
        else:
            play_result.description = f"QB SACKED for {abs(qt_yards)} yard loss (QT roll: {qt_desc})"

    elif combined.use_breakaway:
        b_roll, b_desc = roll_chart_dice()
        b_yards = resolve_breakaway(offense_chart.offense, b_roll)
        play_result.yards = b_yards
        play_result.result_type = ResultType.BREAKAWAY
        play_result.description = f"BREAKAWAY! Roll {b_desc} = {b_yards} yards!"

    elif combined.is_turnover:
        if "INT" in off_result_str or "INT" in def_result_str:
            play_result.result_type = ResultType.INTERCEPTION
        else:
            play_result.result_type = ResultType.FUMBLE

    elif combined.is_incomplete:
        play_result.result_type = ResultType.INCOMPLETE
        play_result.description = "Incomplete pass"

    elif combined.is_touchdown:
        play_result.result_type = ResultType.TOUCHDOWN
        play_result.description = "TOUCHDOWN!"

    # Add dice roll info to description
    play_result.description += f" [Off: {off_dice_desc}, Def: {def_dice_desc}]"

    # Determine offended team and offsetting status
    offended_team = ""
    offsetting = False

    if has_off_penalty and has_def_penalty:
        # Offsetting penalties
        offsetting = True
        offended_team = ""
    elif has_off_penalty:
        # Offense committed penalty - defense is offended
        offended_team = "defense"
    elif has_def_penalty:
        # Defense committed penalty - offense is offended
        offended_team = "offense"

    return PenaltyChoice(
        play_result=play_result,
        penalty_options=penalty_options,
        offended_team=offended_team,
        offsetting=offsetting,
        is_pass_interference=False,
        original_defense_result=original_def_result,
        reroll_log=reroll_log
    )

"""
Penalty handling for Paydirt football simulation.
Implements the Full Feature Method from the official rules.

PENALTY YARDAGE CHART (Full Feature Method):
Roll offensive dice again to determine actual penalty yardage:

                OFF=S   DEF=S   OFF=R   DEF=R
5 yards         10-29   10-24   10      --
5Y yards        --      25-29†  --      11-16†
5X yards        --      30-35*  --      17-19*
10 yards        30-36   --      11-34   --
15 yards        37-39   36-39*† 35-39   20-39*†

Notes:
* = Automatic first down
† = Marked from end of any gain or previous spot (Offensive Player's Choice)

NO HUDDLE OFFENSE PENALTY CHART:
When using no huddle, penalties have different outcomes:

+----------------+----------------+----------------+----------+------------+
| PENALTY        | OFF=S          | DEF=S          | OFF=R    | DEF=R      |
| YARDAGE        |                |                |          |            |
+----------------+----------------+----------------+----------+------------+
| 5 yards        | 10-11 (FS*)    | 10-14 OFF 5    | 10+      | --         |
|                | 12-29          | 15-24 DEF 5    |          |            |
+----------------+----------------+----------------+----------+------------+
| 5Y yards       | --             | 25-29++        | --       | 11-16++    |
+----------------+----------------+----------------+----------+------------+
| 5X yards       | --             | 30-35**        | --       | 17-19**    |
+----------------+----------------+----------------+----------+------------+
| 10 yards       | 30-36          | --             | 11-34    | --         |
+----------------+----------------+----------------+----------+------------+
| 15 yards       | 37-39          | 36-39**++      | 35-39    | 20-39**++  |
+----------------+----------------+----------------+----------+------------+
| Notes:                                                                   |
| *   No Penalty - Bad Snap (F-13 punt, F-7 FG, F-2 all other plays)      |
| **  Automatic first down                                                 |
| +   Prior to the change of possession                                    |
| ++  Marked from end of any gain or previous spot (Off. Player's Choice)  |
+--------------------------------------------------------------------------+

MARKING OFF PENALTIES:
- All penalties marked from PREVIOUS SPOT unless otherwise noted
- No penalty (except PI) may exceed half the distance to offender's goal line
- DEF 5Y: No automatic first down, marked from end of gain if play gained yardage
- DEF 5X: Automatic first down, marked from end of gain if play gained yardage  
- DEF 15: Automatic first down, marked from end of gain if play gained yardage
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .play_resolver import roll_chart_dice


class PenaltyType(Enum):
    """Types of penalties."""
    OFFENSIVE_S = "OFF_S"      # Offensive penalty (scrimmage)
    OFFENSIVE_R = "OFF_R"      # Offensive penalty (return)
    DEFENSIVE_S = "DEF_S"      # Defensive penalty (scrimmage)
    DEFENSIVE_R = "DEF_R"      # Defensive penalty (return)
    PASS_INTERFERENCE = "PI"   # Pass interference (special handling)


@dataclass
class PenaltyResult:
    """Result of penalty resolution."""
    penalty_type: PenaltyType
    yards: int
    automatic_first_down: bool = False
    mark_from_end_of_gain: bool = False  # † marker - offense can choose
    description: str = ""
    dice_roll: int = 0
    raw_penalty_code: str = ""


def roll_penalty_yardage(penalty_type: PenaltyType) -> PenaltyResult:
    """
    Roll offensive dice to determine actual penalty yardage using Full Feature Method.
    
    Args:
        penalty_type: The type of penalty (OFF_S, DEF_S, OFF_R, DEF_R)
    
    Returns:
        PenaltyResult with yards, automatic first down flag, and mark-from-gain flag
    """
    dice_roll, dice_desc = roll_chart_dice()

    yards = 0
    auto_first_down = False
    mark_from_gain = False
    description = ""

    if penalty_type == PenaltyType.OFFENSIVE_S:
        # OFF=S: 5 yards (10-29), 10 yards (30-36), 15 yards (37-39)
        if 10 <= dice_roll <= 29:
            yards = 5
            description = "Offensive penalty, 5 yards"
        elif 30 <= dice_roll <= 36:
            yards = 10
            description = "Offensive penalty, 10 yards"
        elif 37 <= dice_roll <= 39:
            yards = 15
            description = "Offensive penalty, 15 yards"
        else:
            yards = 5  # Default
            description = "Offensive penalty, 5 yards"

    elif penalty_type == PenaltyType.DEFENSIVE_S:
        # DEF=S: 5 yards (10-24), 5Y yards (25-29†), 5X yards (30-35*), 15 yards (36-39*†)
        if 10 <= dice_roll <= 24:
            yards = 5
            description = "Defensive penalty, 5 yards"
        elif 25 <= dice_roll <= 29:
            yards = 5
            mark_from_gain = True  # 5Y - marked from end of gain
            description = "Defensive penalty, 5 yards (facemask)"
        elif 30 <= dice_roll <= 35:
            yards = 5
            auto_first_down = True  # 5X - automatic first down
            mark_from_gain = True
            description = "Defensive holding, 5 yards + automatic first down"
        elif 36 <= dice_roll <= 39:
            yards = 15
            auto_first_down = True
            mark_from_gain = True
            description = "Defensive personal foul, 15 yards + automatic first down"
        else:
            yards = 5
            description = "Defensive penalty, 5 yards"

    elif penalty_type == PenaltyType.OFFENSIVE_R:
        # OFF=R: 5 yards (10), 10 yards (11-34), 15 yards (35-39)
        if dice_roll == 10:
            yards = 5
            description = "Offensive penalty on return, 5 yards"
        elif 11 <= dice_roll <= 34:
            yards = 10
            description = "Offensive penalty on return, 10 yards"
        elif 35 <= dice_roll <= 39:
            yards = 15
            description = "Offensive penalty on return, 15 yards"
        else:
            yards = 10  # Default
            description = "Offensive penalty on return, 10 yards"

    elif penalty_type == PenaltyType.DEFENSIVE_R:
        # DEF=R: -- (10), 5Y yards (11-16†), 5X yards (17-19*), 15 yards (20-39*†)
        # Note: Roll 10 has no entry ("--") - treat as minimum 5 yards
        if dice_roll == 10:
            # No entry in table - use minimum penalty
            yards = 5
            mark_from_gain = True
            description = "Defensive penalty on return, 5 yards"
        elif 11 <= dice_roll <= 16:
            yards = 5
            mark_from_gain = True  # 5Y - marked from end of gain
            description = "Defensive penalty on return, 5 yards"
        elif 17 <= dice_roll <= 19:
            yards = 5
            auto_first_down = True  # 5X - automatic first down
            mark_from_gain = True
            description = "Defensive holding on return, 5 yards + automatic first down"
        elif 20 <= dice_roll <= 39:
            yards = 15
            auto_first_down = True  # 15 yards with * and †
            mark_from_gain = True
            description = "Defensive personal foul on return, 15 yards + automatic first down"
        else:
            yards = 5
            mark_from_gain = True
            description = "Defensive penalty on return, 5 yards"

    return PenaltyResult(
        penalty_type=penalty_type,
        yards=yards,
        automatic_first_down=auto_first_down,
        mark_from_end_of_gain=mark_from_gain,
        description=f"{description} (Roll: {dice_desc})",
        dice_roll=dice_roll,
        raw_penalty_code=penalty_type.value
    )


@dataclass
class NoHuddlePenaltyResult:
    """Result of no huddle penalty resolution."""
    is_bad_snap: bool = False  # True if penalty becomes fumbled snap
    fumble_yards: int = 0  # F-2, F-7, or F-13
    is_false_start: bool = False  # True if DEF penalty becomes OFF 5 (false start)
    normal_penalty: Optional[PenaltyResult] = None  # Normal penalty if not converted
    description: str = ""


def roll_no_huddle_penalty_yardage(penalty_type: PenaltyType,
                                    play_type: str = "normal") -> NoHuddlePenaltyResult:
    """
    Roll penalty yardage using the No Huddle Offense penalty chart.
    
    +----------------+----------------+----------------+----------+------------+
    | PENALTY        | OFF=S          | DEF=S          | OFF=R    | DEF=R      |
    | YARDAGE        |                |                |          |            |
    +----------------+----------------+----------------+----------+------------+
    | 5 yards        | 10-11 (FS*)    | 10-14 OFF 5    | 10+      | --         |
    |                | 12-29          | 15-24 DEF 5    |          |            |
    +----------------+----------------+----------------+----------+------------+
    | 5Y yards       | --             | 25-29++        | --       | 11-16++    |
    +----------------+----------------+----------------+----------+------------+
    | 5X yards       | --             | 30-35**        | --       | 17-19**    |
    +----------------+----------------+----------------+----------+------------+
    | 10 yards       | 30-36          | --             | 11-34    | --         |
    +----------------+----------------+----------------+----------+------------+
    | 15 yards       | 37-39          | 36-39**++      | 35-39    | 20-39**++  |
    +----------------+----------------+----------------+----------+------------+
    *   No Penalty - Bad Snap (F-13 punt, F-7 FG, F-2 all other plays)
    **  Automatic first down
    +   Prior to the change of possession
    ++  Marked from end of any gain or previous spot (Off. Player's Choice)
    
    Args:
        penalty_type: The type of penalty (OFF_S, DEF_S, OFF_R, DEF_R)
        play_type: "punt", "field_goal", or "normal" for bad snap yardage
    
    Returns:
        NoHuddlePenaltyResult with special handling or normal penalty
    """
    dice_roll, dice_desc = roll_chart_dice()

    if penalty_type == PenaltyType.OFFENSIVE_S:
        # OFF=S: 10-11 = Bad Snap (FS*), 12-29 = 5 yards, 30-36 = 10 yards, 37-39 = 15 yards
        if 10 <= dice_roll <= 11:
            # Bad Snap - fumble at line of scrimmage
            if play_type == "punt":
                fumble_yards = -13
            elif play_type == "field_goal":
                fumble_yards = -7
            else:
                fumble_yards = -2
            return NoHuddlePenaltyResult(
                is_bad_snap=True,
                fumble_yards=fumble_yards,
                description=f"BAD SNAP! Fumble at {fumble_yards} yards (Roll: {dice_desc})"
            )
        else:
            # Normal penalty resolution (same as regular)
            normal_result = roll_penalty_yardage(penalty_type)
            # Override with correct roll
            if 12 <= dice_roll <= 29:
                normal_result.yards = 5
                normal_result.description = f"Offensive penalty, 5 yards (Roll: {dice_desc})"
            elif 30 <= dice_roll <= 36:
                normal_result.yards = 10
                normal_result.description = f"Offensive penalty, 10 yards (Roll: {dice_desc})"
            elif 37 <= dice_roll <= 39:
                normal_result.yards = 15
                normal_result.description = f"Offensive penalty, 15 yards (Roll: {dice_desc})"
            normal_result.dice_roll = dice_roll
            return NoHuddlePenaltyResult(
                normal_penalty=normal_result,
                description=normal_result.description
            )

    elif penalty_type == PenaltyType.DEFENSIVE_S:
        # DEF=S: 10-14 = OFF 5 (false start), 15-24 = DEF 5, 25-29 = 5Y, 30-35 = 5X, 36-39 = 15
        if 10 <= dice_roll <= 14:
            # False start - becomes OFF 5, defensive result cancelled, 0 seconds
            return NoHuddlePenaltyResult(
                is_false_start=True,
                description=f"FALSE START! Offensive penalty 5 yards, 0 seconds elapsed (Roll: {dice_desc})"
            )
        elif 15 <= dice_roll <= 24:
            # Normal DEF 5
            return NoHuddlePenaltyResult(
                normal_penalty=PenaltyResult(
                    penalty_type=penalty_type,
                    yards=5,
                    automatic_first_down=False,
                    mark_from_end_of_gain=False,
                    description=f"Defensive penalty, 5 yards (Roll: {dice_desc})",
                    dice_roll=dice_roll,
                    raw_penalty_code=penalty_type.value
                ),
                description=f"Defensive penalty, 5 yards (Roll: {dice_desc})"
            )
        elif 25 <= dice_roll <= 29:
            # 5Y - marked from end of gain
            return NoHuddlePenaltyResult(
                normal_penalty=PenaltyResult(
                    penalty_type=penalty_type,
                    yards=5,
                    automatic_first_down=False,
                    mark_from_end_of_gain=True,
                    description=f"Defensive penalty, 5 yards (facemask) (Roll: {dice_desc})",
                    dice_roll=dice_roll,
                    raw_penalty_code=penalty_type.value
                ),
                description=f"Defensive penalty, 5 yards (facemask) (Roll: {dice_desc})"
            )
        elif 30 <= dice_roll <= 35:
            # 5X - automatic first down
            return NoHuddlePenaltyResult(
                normal_penalty=PenaltyResult(
                    penalty_type=penalty_type,
                    yards=5,
                    automatic_first_down=True,
                    mark_from_end_of_gain=True,
                    description=f"Defensive holding, 5 yards + auto first down (Roll: {dice_desc})",
                    dice_roll=dice_roll,
                    raw_penalty_code=penalty_type.value
                ),
                description=f"Defensive holding, 5 yards + auto first down (Roll: {dice_desc})"
            )
        elif 36 <= dice_roll <= 39:
            # 15 yards with auto first down and mark from gain
            return NoHuddlePenaltyResult(
                normal_penalty=PenaltyResult(
                    penalty_type=penalty_type,
                    yards=15,
                    automatic_first_down=True,
                    mark_from_end_of_gain=True,
                    description=f"Defensive personal foul, 15 yards + auto first down (Roll: {dice_desc})",
                    dice_roll=dice_roll,
                    raw_penalty_code=penalty_type.value
                ),
                description=f"Defensive personal foul, 15 yards + auto first down (Roll: {dice_desc})"
            )

    elif penalty_type == PenaltyType.OFFENSIVE_R:
        # OFF=R: 10† = 5 yards, 11-34 = 10 yards, 35-39 = 15 yards
        # Same ranges as normal table; † on roll 10 = prior to change of possession
        if dice_roll == 10:
            yards = 5
            desc = f"Offensive penalty on return, 5 yards (Roll: {dice_desc})"
        elif 11 <= dice_roll <= 34:
            yards = 10
            desc = f"Offensive penalty on return, 10 yards (Roll: {dice_desc})"
        else:  # 35-39
            yards = 15
            desc = f"Offensive penalty on return, 15 yards (Roll: {dice_desc})"
        return NoHuddlePenaltyResult(
            normal_penalty=PenaltyResult(
                penalty_type=penalty_type,
                yards=yards,
                automatic_first_down=False,
                mark_from_end_of_gain=False,
                description=desc,
                dice_roll=dice_roll,
                raw_penalty_code=penalty_type.value
            ),
            description=desc
        )

    elif penalty_type == PenaltyType.DEFENSIVE_R:
        # DEF=R: -- (10), 5Y (11-16††), 5X (17-19**), 15 (20-39**††)
        # Same ranges as normal table; †† = mark from gain, ** = auto first down
        if dice_roll == 10:
            # No entry in table ("--") - use minimum 5 yards
            yards = 5
            auto_fd = False
            mark_gain = True
            desc = f"Defensive penalty on return, 5 yards (Roll: {dice_desc})"
        elif 11 <= dice_roll <= 16:
            yards = 5
            auto_fd = False
            mark_gain = True
            desc = f"Defensive penalty on return, 5 yards (Roll: {dice_desc})"
        elif 17 <= dice_roll <= 19:
            yards = 5
            auto_fd = True
            mark_gain = True
            desc = f"Defensive holding on return, 5 yards + auto first down (Roll: {dice_desc})"
        else:  # 20-39
            yards = 15
            auto_fd = True
            mark_gain = True
            desc = f"Defensive personal foul on return, 15 yards + auto first down (Roll: {dice_desc})"
        return NoHuddlePenaltyResult(
            normal_penalty=PenaltyResult(
                penalty_type=penalty_type,
                yards=yards,
                automatic_first_down=auto_fd,
                mark_from_end_of_gain=mark_gain,
                description=desc,
                dice_roll=dice_roll,
                raw_penalty_code=penalty_type.value
            ),
            description=desc
        )

    # Fallback
    normal_result = roll_penalty_yardage(penalty_type)
    return NoHuddlePenaltyResult(
        normal_penalty=normal_result,
        description=normal_result.description
    )


def apply_half_distance_rule(penalty_yards: int, ball_position: int,
                              is_offensive_penalty: bool) -> int:
    """
    Apply the half-distance-to-goal rule.
    
    No penalty (except PI) may exceed half the distance to the offender's goal line.
    
    Args:
        penalty_yards: The penalty yardage
        ball_position: Current ball position (0=own goal, 100=opponent goal)
        is_offensive_penalty: True if offense committed the penalty
    
    Returns:
        Adjusted penalty yardage
    """
    if is_offensive_penalty:
        # Offensive penalty moves ball toward own goal
        # Distance to own goal is ball_position
        max_penalty = ball_position // 2
    else:
        # Defensive penalty moves ball toward opponent's goal
        # Distance to opponent's goal is (100 - ball_position)
        max_penalty = (100 - ball_position) // 2

    return min(penalty_yards, max(1, max_penalty))


def calculate_penalty_spot(ball_position: int, yards_gained: int,
                           penalty_yards: int, is_offensive_penalty: bool,
                           mark_from_gain: bool, is_return: bool = False) -> int:
    """
    Calculate the spot where the ball should be placed after a penalty.
    
    Args:
        ball_position: Ball position at start of play (previous spot)
        yards_gained: Yards gained on the play (if any)
        penalty_yards: Penalty yardage
        is_offensive_penalty: True if offense committed the penalty
        mark_from_gain: True if penalty should be marked from end of gain
        is_return: True if this is a return play (special rules apply)
    
    Returns:
        New ball position after penalty
    """
    if is_offensive_penalty:
        if is_return and yards_gained > 0:
            # Special rule for returns: if return exceeds halfway point,
            # mark from halfway point
            halfway = ball_position + (100 - ball_position) // 2
            end_of_return = ball_position + yards_gained
            if end_of_return > halfway:
                # Mark from halfway point
                return halfway - penalty_yards
            else:
                # Mark from end of return
                return end_of_return - penalty_yards
        else:
            # Normal offensive penalty: mark from previous spot
            return ball_position - penalty_yards
    else:
        # Defensive penalty
        if mark_from_gain and yards_gained > 0:
            # Mark from end of gain (offense's choice, we assume they take it)
            return ball_position + yards_gained + penalty_yards
        else:
            # Mark from previous spot
            return ball_position + penalty_yards


def resolve_penalty(penalty_code: str, ball_position: int,
                    yards_gained: int = 0, is_return: bool = False,
                    yards_to_go: int = 10, down: int = 1,
                    chart_yards: int = None, auto_first_down: bool = False) -> Tuple[PenaltyResult, int, int, int, bool]:
    """
    Fully resolve a penalty using the Full Feature Method.
    
    Args:
        penalty_code: The penalty code from the chart (e.g., "OFF S", "DEF S", "OFF R", "DEF R")
        ball_position: Current ball position
        yards_gained: Yards gained on the play (for mark-from-gain penalties)
        is_return: True if this is a return play
        yards_to_go: Current yards to go for first down
        down: Current down
        chart_yards: If provided, use this yardage instead of rolling (for explicit chart penalties like "DEF 15")
        auto_first_down: If True, penalty gives automatic first down (for explicit chart penalties with X modifier)
    
    Returns:
        Tuple of (PenaltyResult, new_ball_position, new_down, new_yards_to_go, first_down)
    """
    # Determine penalty type
    penalty_code_upper = penalty_code.upper().replace(" ", "_")
    if "OFF" in penalty_code_upper:
        if is_return or "R" in penalty_code_upper:
            penalty_type = PenaltyType.OFFENSIVE_R
        else:
            penalty_type = PenaltyType.OFFENSIVE_S
        is_offensive = True
    else:
        if is_return or "R" in penalty_code_upper:
            penalty_type = PenaltyType.DEFENSIVE_R
        else:
            penalty_type = PenaltyType.DEFENSIVE_S
        is_offensive = False

    # Use chart yardage if provided, otherwise roll for penalty yardage
    if chart_yards is not None:
        # Chart explicitly specified yardage (e.g., "DEF 15")
        penalty_result = PenaltyResult(
            penalty_type=penalty_type,
            yards=chart_yards,
            automatic_first_down=auto_first_down,
            mark_from_end_of_gain=False,
            description=f"{'Offensive' if is_offensive else 'Defensive'} penalty, {chart_yards} yards",
            dice_roll=0,
            raw_penalty_code=penalty_code
        )
    else:
        # Roll for actual penalty yardage (Full Feature Method)
        penalty_result = roll_penalty_yardage(penalty_type)

    # Apply half-distance rule
    adjusted_yards = apply_half_distance_rule(
        penalty_result.yards, ball_position, is_offensive
    )

    # Calculate new ball position
    new_position = calculate_penalty_spot(
        ball_position, yards_gained, adjusted_yards,
        is_offensive, penalty_result.mark_from_end_of_gain, is_return
    )

    # Ensure ball stays in bounds
    new_position = max(1, min(99, new_position))

    # Determine down and distance
    first_down = False
    if is_offensive:
        # Offensive penalty: repeat down, add penalty yards to distance
        new_down = down
        new_yards_to_go = yards_to_go + adjusted_yards
    else:
        # Defensive penalty
        if penalty_result.automatic_first_down:
            new_down = 1
            new_yards_to_go = 10
            first_down = True
        else:
            # Subtract penalty yards from yards to go
            new_yards_to_go = yards_to_go - adjusted_yards
            if new_yards_to_go <= 0:
                new_down = 1
                new_yards_to_go = 10
                first_down = True
            else:
                new_down = down

    # Update description with adjusted yards if different
    if adjusted_yards != penalty_result.yards:
        penalty_result.description += f" (half-distance: {adjusted_yards} yards)"

    return penalty_result, new_position, new_down, new_yards_to_go, first_down


def resolve_pass_interference(pi_yards: int, ball_position: int) -> Tuple[int, int, int]:
    """
    Resolve pass interference penalty.
    
    PI is always marked from the previous spot and is always an automatic first down.
    PI is the only penalty that can exceed half-distance-to-goal.
    
    Args:
        pi_yards: The PI yardage from the chart
        ball_position: Current ball position
    
    Returns:
        Tuple of (new_ball_position, new_down, new_yards_to_go)
    """
    new_position = ball_position + pi_yards

    # PI can go into the end zone for a TD, but cap at 99 for goal-to-go
    if new_position >= 100:
        new_position = 99  # 1st and goal at the 1

    return new_position, 1, min(10, 100 - new_position)


def check_offsetting_penalties(off_penalty: bool, def_penalty: bool,
                                pi_penalty: bool) -> bool:
    """
    Check if penalties offset.
    
    Example: OFF 5 + PI 8 = offsetting penalties, replay down.
    
    Args:
        off_penalty: True if offensive penalty occurred
        def_penalty: True if defensive penalty occurred
        pi_penalty: True if pass interference occurred
    
    Returns:
        True if penalties offset
    """
    # Offensive penalty + defensive penalty (including PI) = offsetting
    if off_penalty and (def_penalty or pi_penalty):
        return True
    return False

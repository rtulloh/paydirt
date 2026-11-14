"""Own-end-zone interception return policy.

The engine exposes this decision to a human controller after the interception
catch location is known. A CPU controller uses the same pure policy function so
it cannot see return dice before choosing.
"""
from __future__ import annotations

OWN_GOAL_LINE_DEPTH = 0
DEEPEST_RECORDED_DEPTH = 9
TWO_SCORE_LEAD = 9


def should_attempt_end_zone_return(
    *,
    catch_depth: int,
    score_differential: int,
    quarter: int,
    time_remaining: float,
    is_overtime: bool = False,
) -> bool:
    """Decide whether an intercepting team should attempt a return.

    Args:
        catch_depth: Yards deep in the intercepting team's own end zone
            (0 = goal line, capped at 9 by the board-game depth rule).
        score_differential: Intercepting team's score minus the opponent's.
        quarter: Current quarter (overtime is reported separately).
        time_remaining: Minutes remaining in the current quarter.
        is_overtime: True when the game is in overtime.

    Returns:
        True to attempt the return, False to elect the automatic touchback.

    The policy never consults return dice. Depth dominates: a catch near the
    end line has almost no chance to escape, while a goal-line catch is a free
    opportunity unless a late lead argues for avoiding return risk.
    """
    depth = max(OWN_GOAL_LINE_DEPTH, min(int(catch_depth), DEEPEST_RECORDED_DEPTH))
    if depth >= 5:
        return False

    late = is_overtime or quarter >= 4 or (quarter == 2 and time_remaining <= 2.0)
    protecting_lead = late and score_differential >= TWO_SCORE_LEAD
    if protecting_lead:
        return False

    if depth <= 2:
        return True
    # A mid-depth catch is worth attempting when the team needs the extra
    # possession value, but not in a neutral early-game situation.
    return score_differential < 0 or is_overtime or (late and score_differential <= 0)

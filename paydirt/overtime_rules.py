"""
NFL Overtime Rules by Season.

Overtime rules have changed over the years. This module provides
the correct overtime rules based on the season year.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OvertimeFormat(Enum):
    """Types of overtime formats used in NFL history."""
    SUDDEN_DEATH = "sudden_death"  # First score wins (pre-2010)
    MODIFIED_SUDDEN_DEATH = "modified_sudden_death"  # TD on first possession wins, FG allows response (2010+)


@dataclass
class OvertimeRules:
    """Overtime rules for a specific era."""
    format: OvertimeFormat
    period_length_minutes: float  # Length of each OT period
    max_periods_regular: int  # Max OT periods in regular season (0 = unlimited until score)
    max_periods_playoff: int  # Max OT periods in playoffs (0 = unlimited until score)
    can_end_in_tie_regular: bool  # Can regular season games end in tie?
    can_end_in_tie_playoff: bool  # Can playoff games end in tie? (always False)
    coin_toss_winner_receives: bool  # Does coin toss winner receive the ball?
    
    def get_max_periods(self, is_playoff: bool) -> int:
        """Get max OT periods based on game type."""
        return self.max_periods_playoff if is_playoff else self.max_periods_regular


# Overtime rules by year range
# Key is the first year the rule applies, value is the OvertimeRules
OVERTIME_RULES_BY_YEAR = {
    # 1974-2009: Sudden death, 15-minute period, can tie in regular season
    1974: OvertimeRules(
        format=OvertimeFormat.SUDDEN_DEATH,
        period_length_minutes=15.0,
        max_periods_regular=1,  # One 15-minute period, then tie
        max_periods_playoff=0,  # Unlimited in playoffs
        can_end_in_tie_regular=True,
        can_end_in_tie_playoff=False,
        coin_toss_winner_receives=True
    ),
    
    # 2010-2011: Modified sudden death for playoffs only
    2010: OvertimeRules(
        format=OvertimeFormat.MODIFIED_SUDDEN_DEATH,
        period_length_minutes=15.0,
        max_periods_regular=1,
        max_periods_playoff=0,
        can_end_in_tie_regular=True,
        can_end_in_tie_playoff=False,
        coin_toss_winner_receives=True
    ),
    
    # 2012-2016: Modified sudden death for all games
    2012: OvertimeRules(
        format=OvertimeFormat.MODIFIED_SUDDEN_DEATH,
        period_length_minutes=15.0,
        max_periods_regular=1,
        max_periods_playoff=0,
        can_end_in_tie_regular=True,
        can_end_in_tie_playoff=False,
        coin_toss_winner_receives=True
    ),
    
    # 2017-2022: Reduced to 10-minute OT in regular season
    2017: OvertimeRules(
        format=OvertimeFormat.MODIFIED_SUDDEN_DEATH,
        period_length_minutes=10.0,
        max_periods_regular=1,
        max_periods_playoff=0,
        can_end_in_tie_regular=True,
        can_end_in_tie_playoff=False,
        coin_toss_winner_receives=True
    ),
    
    # 2022+: Both teams get possession in playoffs
    # (For simplicity, we'll treat this as modified sudden death with guaranteed possession)
    2022: OvertimeRules(
        format=OvertimeFormat.MODIFIED_SUDDEN_DEATH,
        period_length_minutes=10.0,
        max_periods_regular=1,
        max_periods_playoff=0,
        can_end_in_tie_regular=True,
        can_end_in_tie_playoff=False,
        coin_toss_winner_receives=True
    ),
}


def get_overtime_rules(year: int) -> OvertimeRules:
    """
    Get the overtime rules for a specific year.
    
    Args:
        year: The season year (e.g., 1983, 2023)
    
    Returns:
        OvertimeRules for that season
    """
    # Find the most recent rule change that applies
    applicable_year = None
    for rule_year in sorted(OVERTIME_RULES_BY_YEAR.keys()):
        if rule_year <= year:
            applicable_year = rule_year
        else:
            break
    
    if applicable_year is None:
        # Default to earliest rules for very old seasons
        applicable_year = min(OVERTIME_RULES_BY_YEAR.keys())
    
    return OVERTIME_RULES_BY_YEAR[applicable_year]


def check_overtime_winner(home_score: int, away_score: int, 
                          rules: OvertimeRules, 
                          is_playoff: bool,
                          first_possession_team_scored: bool,
                          first_possession_was_td: bool,
                          ot_period: int) -> Optional[str]:
    """
    Check if there's an overtime winner based on the rules.
    
    Args:
        home_score: Home team's current score
        away_score: Away team's current score
        rules: The overtime rules in effect
        is_playoff: Whether this is a playoff game
        first_possession_team_scored: Whether the team with first possession scored
        first_possession_was_td: Whether the first possession score was a TD
        ot_period: Current OT period number (1, 2, etc.)
    
    Returns:
        "home", "away", "tie", or None (game continues)
    """
    if home_score == away_score:
        # Still tied - check if we've exceeded max periods
        max_periods = rules.get_max_periods(is_playoff)
        if max_periods > 0 and ot_period >= max_periods:
            if rules.can_end_in_tie_regular and not is_playoff:
                return "tie"
        return None  # Game continues
    
    # Someone is ahead
    if rules.format == OvertimeFormat.SUDDEN_DEATH:
        # Any score wins
        return "home" if home_score > away_score else "away"
    
    elif rules.format == OvertimeFormat.MODIFIED_SUDDEN_DEATH:
        # TD on first possession wins immediately
        # FG on first possession allows other team to respond
        if first_possession_team_scored and first_possession_was_td:
            return "home" if home_score > away_score else "away"
        
        # After both teams have had possession, any score wins
        # (This is simplified - full implementation would track possessions)
        return "home" if home_score > away_score else "away"
    
    return None

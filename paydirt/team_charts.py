"""
Team charts that determine play outcomes based on dice rolls.
These charts are inspired by the Paydirt board game mechanics.
"""
import random
from typing import Dict, Tuple

from .models import PlayType, DefenseType, PlayOutcome, PlayResult, Team


# Dice roll ranges: 2-12 (two six-sided dice)
# Each entry maps (play_type, defense_type) -> list of (roll_range, outcome)
# Roll ranges are tuples of (min_roll, max_roll)

def get_base_rushing_chart() -> Dict[Tuple[int, int], PlayOutcome]:
    """
    Base rushing play outcomes by dice roll.
    Returns dict mapping dice roll to PlayOutcome.
    """
    return {
        2: PlayOutcome(PlayResult.FUMBLE, -2, "Fumble! Ball is loose!", turnover=True),
        3: PlayOutcome(PlayResult.LOSS, -3, "Stuffed in the backfield for a loss"),
        4: PlayOutcome(PlayResult.LOSS, -1, "Tackled behind the line"),
        5: PlayOutcome(PlayResult.NO_GAIN, 0, "No gain on the play"),
        6: PlayOutcome(PlayResult.GAIN, 2, "Short gain up the middle"),
        7: PlayOutcome(PlayResult.GAIN, 4, "Solid gain through the hole"),
        8: PlayOutcome(PlayResult.GAIN, 6, "Good run, breaks a tackle"),
        9: PlayOutcome(PlayResult.GAIN, 8, "Big gain! Found some daylight"),
        10: PlayOutcome(PlayResult.GAIN, 12, "Excellent run! Breaking tackles"),
        11: PlayOutcome(PlayResult.GAIN, 18, "Huge gain! Wide open field"),
        12: PlayOutcome(PlayResult.GAIN, 25, "Breakaway run! Could go all the way!"),
    }


def get_base_short_pass_chart() -> Dict[int, PlayOutcome]:
    """Base short pass outcomes by dice roll."""
    return {
        2: PlayOutcome(PlayResult.INTERCEPTION, 0, "Intercepted! Defender jumped the route!", turnover=True),
        3: PlayOutcome(PlayResult.SACK, -8, "Sacked! Quarterback goes down hard"),
        4: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, thrown away"),
        5: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, dropped"),
        6: PlayOutcome(PlayResult.GAIN, 3, "Short completion for minimal gain"),
        7: PlayOutcome(PlayResult.GAIN, 5, "Completion over the middle"),
        8: PlayOutcome(PlayResult.GAIN, 7, "Nice catch and run"),
        9: PlayOutcome(PlayResult.GAIN, 10, "First down! Great timing"),
        10: PlayOutcome(PlayResult.GAIN, 14, "Big play! Receiver breaks free"),
        11: PlayOutcome(PlayResult.GAIN, 20, "Huge gain after the catch!"),
        12: PlayOutcome(PlayResult.GAIN, 30, "Wide open! Racing downfield!"),
    }


def get_base_medium_pass_chart() -> Dict[int, PlayOutcome]:
    """Base medium pass outcomes by dice roll."""
    return {
        2: PlayOutcome(PlayResult.INTERCEPTION, -5, "Picked off! Returned for yards!", turnover=True),
        3: PlayOutcome(PlayResult.SACK, -10, "Sacked! Big loss"),
        4: PlayOutcome(PlayResult.SACK, -5, "Sacked trying to throw"),
        5: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, well defended"),
        6: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, overthrown"),
        7: PlayOutcome(PlayResult.GAIN, 8, "Completion on the sideline"),
        8: PlayOutcome(PlayResult.GAIN, 12, "Nice catch in traffic"),
        9: PlayOutcome(PlayResult.GAIN, 16, "Big completion! First down"),
        10: PlayOutcome(PlayResult.GAIN, 22, "Great throw and catch!"),
        11: PlayOutcome(PlayResult.GAIN, 30, "Huge play! Defender beaten badly"),
        12: PlayOutcome(PlayResult.GAIN, 45, "Bomb! Could be a touchdown!"),
    }


def get_base_long_pass_chart() -> Dict[int, PlayOutcome]:
    """Base long pass (deep ball) outcomes by dice roll."""
    return {
        2: PlayOutcome(PlayResult.INTERCEPTION, -10, "Intercepted deep! Big return!", turnover=True),
        3: PlayOutcome(PlayResult.INTERCEPTION, 0, "Picked off at the goal line!", turnover=True),
        4: PlayOutcome(PlayResult.SACK, -12, "Sacked! Huge loss"),
        5: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, too long"),
        6: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, good coverage"),
        7: PlayOutcome(PlayResult.INCOMPLETE, 0, "Pass incomplete, just missed"),
        8: PlayOutcome(PlayResult.GAIN, 15, "Caught! Nice deep ball"),
        9: PlayOutcome(PlayResult.GAIN, 25, "Big completion downfield!"),
        10: PlayOutcome(PlayResult.GAIN, 35, "Huge gain! Defender burned"),
        11: PlayOutcome(PlayResult.GAIN, 50, "Incredible catch! Touchdown range!"),
        12: PlayOutcome(PlayResult.GAIN, 65, "BOMB! Wide open deep!"),
    }


def get_base_screen_pass_chart() -> Dict[int, PlayOutcome]:
    """Base screen pass outcomes by dice roll."""
    return {
        2: PlayOutcome(PlayResult.LOSS, -5, "Screen blown up! Big loss"),
        3: PlayOutcome(PlayResult.LOSS, -2, "Screen read perfectly"),
        4: PlayOutcome(PlayResult.NO_GAIN, 0, "Screen stopped at the line"),
        5: PlayOutcome(PlayResult.GAIN, 2, "Short gain on the screen"),
        6: PlayOutcome(PlayResult.GAIN, 5, "Screen works for decent gain"),
        7: PlayOutcome(PlayResult.GAIN, 8, "Good blocks on the screen"),
        8: PlayOutcome(PlayResult.GAIN, 12, "Screen breaks free!"),
        9: PlayOutcome(PlayResult.GAIN, 18, "Big play on the screen!"),
        10: PlayOutcome(PlayResult.GAIN, 25, "Screen goes for huge gain!"),
        11: PlayOutcome(PlayResult.GAIN, 35, "Blockers everywhere! Big play!"),
        12: PlayOutcome(PlayResult.GAIN, 50, "Screen could go all the way!"),
    }


def get_base_draw_chart() -> Dict[int, PlayOutcome]:
    """Base draw play outcomes by dice roll."""
    return {
        2: PlayOutcome(PlayResult.FUMBLE, -3, "Fumble on the draw!", turnover=True),
        3: PlayOutcome(PlayResult.LOSS, -4, "Draw stuffed in backfield"),
        4: PlayOutcome(PlayResult.LOSS, -1, "Draw read by defense"),
        5: PlayOutcome(PlayResult.NO_GAIN, 0, "Draw stopped at the line"),
        6: PlayOutcome(PlayResult.GAIN, 3, "Draw picks up a few"),
        7: PlayOutcome(PlayResult.GAIN, 6, "Draw works! Good blocking"),
        8: PlayOutcome(PlayResult.GAIN, 10, "Draw breaks through!"),
        9: PlayOutcome(PlayResult.GAIN, 15, "Big gain on the draw!"),
        10: PlayOutcome(PlayResult.GAIN, 22, "Draw fools everyone!"),
        11: PlayOutcome(PlayResult.GAIN, 30, "Huge draw play!"),
        12: PlayOutcome(PlayResult.GAIN, 40, "Draw could go the distance!"),
    }


def apply_team_modifier(base_yards: int, offense_rating: int, defense_rating: int) -> int:
    """
    Apply team ratings to modify yardage.
    Offense rating helps, defense rating hurts.
    Ratings are 1-10 scale, 5 is average.
    """
    # Calculate modifier: positive means more yards, negative means fewer
    modifier = (offense_rating - defense_rating) / 2.0

    # Apply modifier as a percentage adjustment
    adjusted = base_yards * (1 + modifier * 0.1)

    # Add some randomness
    variance = random.randint(-1, 1)

    return max(int(adjusted) + variance, base_yards - 3 if base_yards > 0 else base_yards)


def apply_defense_modifier(outcome: PlayOutcome, defense_type: DefenseType,
                          play_type: PlayType) -> PlayOutcome:
    """
    Modify outcome based on defensive formation vs play type.
    """
    yards = outcome.yards

    # Blitz is good vs pass but bad vs run
    if defense_type == DefenseType.BLITZ:
        if play_type in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS]:
            # Blitz helps vs pass - more sacks/incompletions, but if completed, bigger gains
            if outcome.result == PlayResult.GAIN:
                yards = int(yards * 1.2)  # Bigger gains if they beat the blitz
        elif play_type in [PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE]:
            # Blitz is bad vs run
            if outcome.result == PlayResult.GAIN:
                yards = int(yards * 1.3)
        elif play_type in [PlayType.SCREEN_PASS, PlayType.DRAW]:
            # Blitz is terrible vs screens and draws
            if outcome.result == PlayResult.GAIN:
                yards = int(yards * 1.5)

    # Prevent defense is good vs long pass but bad vs run
    elif defense_type == DefenseType.PREVENT:
        if play_type == PlayType.LONG_PASS:
            if outcome.result == PlayResult.GAIN:
                yards = int(yards * 0.7)  # Reduce big plays
        elif play_type in [PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE]:
            if outcome.result == PlayResult.GAIN:
                yards = int(yards * 1.4)  # Easy runs vs prevent

    # Goal line defense is good vs short yardage
    elif defense_type == DefenseType.GOAL_LINE:
        if play_type in [PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE]:
            if outcome.result == PlayResult.GAIN:
                yards = max(1, int(yards * 0.5))  # Harder to run
        elif play_type in [PlayType.MEDIUM_PASS, PlayType.LONG_PASS]:
            if outcome.result == PlayResult.GAIN:
                yards = int(yards * 1.3)  # Vulnerable deep

    return PlayOutcome(
        result=outcome.result,
        yards=yards,
        description=outcome.description,
        turnover=outcome.turnover,
        scoring=outcome.scoring,
        penalty_yards=outcome.penalty_yards
    )


def roll_dice() -> int:
    """Roll two six-sided dice and return the sum."""
    return random.randint(1, 6) + random.randint(1, 6)


def get_play_chart(play_type: PlayType) -> Dict[int, PlayOutcome]:
    """Get the appropriate chart for a play type."""
    if play_type in [PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE]:
        return get_base_rushing_chart()
    elif play_type == PlayType.SHORT_PASS:
        return get_base_short_pass_chart()
    elif play_type == PlayType.MEDIUM_PASS:
        return get_base_medium_pass_chart()
    elif play_type == PlayType.LONG_PASS:
        return get_base_long_pass_chart()
    elif play_type == PlayType.SCREEN_PASS:
        return get_base_screen_pass_chart()
    elif play_type == PlayType.DRAW:
        return get_base_draw_chart()
    else:
        # Default to rushing chart for other plays
        return get_base_rushing_chart()


def resolve_play(play_type: PlayType, defense_type: DefenseType,
                offense: Team, defense: Team) -> Tuple[int, PlayOutcome]:
    """
    Resolve a play and return the dice roll and outcome.
    
    Args:
        play_type: The offensive play called
        defense_type: The defensive formation
        offense: The team on offense
        defense: The team on defense
    
    Returns:
        Tuple of (dice_roll, PlayOutcome)
    """
    dice_roll = roll_dice()
    chart = get_play_chart(play_type)
    base_outcome = chart[dice_roll]

    # Determine which ratings to use
    if play_type in [PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE, PlayType.DRAW]:
        off_rating = offense.rushing_offense
        def_rating = defense.rushing_defense
    else:
        off_rating = offense.passing_offense
        def_rating = defense.passing_defense

    # Apply team modifiers to yards
    modified_yards = apply_team_modifier(base_outcome.yards, off_rating, def_rating)

    # Create modified outcome
    modified_outcome = PlayOutcome(
        result=base_outcome.result,
        yards=modified_yards,
        description=base_outcome.description,
        turnover=base_outcome.turnover,
        scoring=base_outcome.scoring,
        penalty_yards=base_outcome.penalty_yards
    )

    # Apply defense formation modifiers
    final_outcome = apply_defense_modifier(modified_outcome, defense_type, play_type)

    return dice_roll, final_outcome


def resolve_field_goal(distance: int, kicker_rating: int) -> Tuple[int, bool]:
    """
    Resolve a field goal attempt.
    
    Args:
        distance: Distance of the field goal attempt in yards
        kicker_rating: Kicker's rating (1-10)
    
    Returns:
        Tuple of (dice_roll, success)
    """
    dice_roll = roll_dice()

    # Base success threshold depends on distance
    # Short FGs (< 30 yards): need 4+
    # Medium FGs (30-45 yards): need 6+
    # Long FGs (46-55 yards): need 8+
    # Very long FGs (> 55 yards): need 10+

    if distance < 30:
        threshold = 4
    elif distance <= 45:
        threshold = 6
    elif distance <= 55:
        threshold = 8
    else:
        threshold = 10

    # Kicker rating modifies threshold (rating 5 is neutral)
    threshold -= (kicker_rating - 5)

    success = dice_roll >= threshold
    return dice_roll, success


def resolve_punt(punter_rating: int) -> Tuple[int, int]:
    """
    Resolve a punt.
    
    Args:
        punter_rating: Punter's rating (1-10)
    
    Returns:
        Tuple of (dice_roll, punt_distance)
    """
    dice_roll = roll_dice()

    # Base punt distance by roll
    base_distances = {
        2: 25,   # Shank
        3: 30,
        4: 35,
        5: 38,
        6: 40,
        7: 42,
        8: 45,
        9: 48,
        10: 50,
        11: 55,
        12: 60,  # Booming punt
    }

    base_distance = base_distances[dice_roll]

    # Punter rating modifies distance
    modifier = (punter_rating - 5) * 2
    final_distance = base_distance + modifier

    return dice_roll, final_distance


def resolve_extra_point(kicker_rating: int) -> Tuple[int, bool]:
    """
    Resolve an extra point attempt.
    
    Args:
        kicker_rating: Kicker's rating (1-10)
    
    Returns:
        Tuple of (dice_roll, success)
    """
    dice_roll = roll_dice()

    # Extra points are almost automatic - need 3+ (miss on snake eyes basically)
    threshold = 3 - (kicker_rating - 5)
    threshold = max(2, threshold)  # Can't be automatic

    success = dice_roll >= threshold
    return dice_roll, success


def resolve_two_point_conversion(play_type: PlayType, offense: Team,
                                 defense: Team) -> Tuple[int, bool]:
    """
    Resolve a two-point conversion attempt.
    
    Args:
        play_type: The play called for the conversion
        defense: The defending team
    
    Returns:
        Tuple of (dice_roll, success)
    """
    dice_roll = roll_dice()

    # Two-point conversions succeed on 8+ (about 42% success rate)
    # Modified by team ratings
    if play_type in [PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE]:
        modifier = (offense.rushing_offense - defense.rushing_defense) / 2
    else:
        modifier = (offense.passing_offense - defense.passing_defense) / 2

    threshold = 8 - int(modifier)
    success = dice_roll >= threshold

    return dice_roll, success

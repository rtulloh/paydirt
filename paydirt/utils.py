"""
Shared utility functions for Paydirt.
"""


def ordinal_suffix(n: int) -> str:
    """
    Get the ordinal suffix for a number.
    
    Args:
        n: The number (1-4 for downs)
        
    Returns:
        Suffix string like "st", "nd", "rd", "th"
    
    Examples:
        >>> ordinal_suffix(1)
        'st'
        >>> ordinal_suffix(2)
        'nd'
        >>> ordinal_suffix(3)
        'rd'
        >>> ordinal_suffix(4)
        'th'
    """
    if 10 <= n % 100 <= 20:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def ordinal(n: int) -> str:
    """
    Convert a number to its ordinal string representation.
    
    Args:
        n: The number to convert (1-4 for downs)
        
    Returns:
        Ordinal string like "1st", "2nd", "3rd", "4th"
    
    Examples:
        >>> ordinal(1)
        '1st'
        >>> ordinal(2)
        '2nd'
        >>> ordinal(3)
        '3rd'
        >>> ordinal(4)
        '4th'
    """
    return f"{n}{ordinal_suffix(n)}"


def format_down_and_distance(down: int, yards_to_go: int, yards_to_goal: int = None) -> str:
    """
    Format down and distance for display.
    
    Args:
        down: Current down (1-4)
        yards_to_go: Yards needed for first down
        yards_to_goal: Optional yards to goal line (for "& Goal" situations)
        
    Returns:
        Formatted string like "1st & 10", "3rd & Goal"
    """
    if yards_to_goal is not None and yards_to_goal <= 10 and yards_to_go >= yards_to_goal:
        return f"{ordinal(down)} & Goal"
    return f"{ordinal(down)} & {yards_to_go}"


def format_time(minutes: float) -> str:
    """
    Format time remaining as MM:SS.
    
    Args:
        minutes: Time in minutes (e.g., 2.5 = 2:30)
        
    Returns:
        Formatted string like "2:30", "0:45"
    """
    mins = int(minutes)
    secs = int((minutes % 1) * 60)
    return f"{mins}:{secs:02d}"


def format_field_position(position: int, style: str = "verbose") -> str:
    """
    Convert internal ball position (1-99) to human-readable field position.
    
    Internal coordinate system:
    - Position 1-49: Own territory (own 1 to own 49)
    - Position 50: Midfield
    - Position 51-99: Opponent's territory (opponent's 49 to opponent's 1)
    
    Args:
        position: Internal ball position (1-99)
        style: "verbose" for "own 35" / "opponent's 35" / "midfield"
               "short" for "own 35" / "opp 35" / "midfield"
               "neutral" for just the yard line number (e.g., "35", "50")
        
    Returns:
        Human-readable field position string
        
    Examples:
        >>> format_field_position(35)
        'own 35'
        >>> format_field_position(65)
        "opponent's 35"
        >>> format_field_position(50)
        'midfield'
        >>> format_field_position(65, style="short")
        'opp 35'
    """
    if position == 50:
        return "midfield"
    elif position < 50:
        return f"own {position}"
    else:
        yard_line = 100 - position
        if style == "short":
            return f"opp {yard_line}"
        else:
            return f"opponent's {yard_line}"


def format_field_position_with_team(position: int, off_team: str, def_team: str) -> str:
    """
    Convert internal ball position to field position with team name.
    
    Args:
        position: Internal ball position (1-99)
        off_team: Offensive team abbreviation (e.g., "GB", "SF '83")
        def_team: Defensive team abbreviation
        
    Returns:
        Field position with team name (e.g., "GB 35", "SF 20", "50")
        
    Examples:
        >>> format_field_position_with_team(35, "GB", "CHI")
        'GB 35'
        >>> format_field_position_with_team(65, "GB", "CHI")
        'CHI 35'
        >>> format_field_position_with_team(50, "GB", "CHI")
        'midfield'
    """
    # Strip year suffix for cleaner display (e.g., "SF '83" -> "SF")
    off_abbrev = off_team.split()[0] if off_team else off_team
    def_abbrev = def_team.split()[0] if def_team else def_team
    
    if position == 50:
        return "midfield"
    elif position < 50:
        return f"{off_abbrev} {position}"
    else:
        return f"{def_abbrev} {100 - position}"


def format_dice_roll(roll: int, dice_desc: str = None, result: str = None, 
                     prefix: str = "", style: str = "standard") -> str:
    """
    Format a dice roll for display in a standardized way.
    
    Args:
        roll: The dice roll value (e.g., 28)
        dice_desc: Optional dice description (e.g., "B2+W5+W3=28")
        result: The chart result (e.g., "INT 13", "+5")
        prefix: Optional prefix like "O" for offense, "D" for defense, "R" for recovery
        style: "standard" for "O:28→\"+5\"", "verbose" for "Roll: 28 → \"+5\""
        
    Returns:
        Formatted dice roll string
        
    Examples:
        >>> format_dice_roll(28, result="+5", prefix="O")
        'O:28→"+5"'
        >>> format_dice_roll(28, "B2+W5+W3=28", "+5", "O")
        'O:B2+W5+W3=28→"+5"'
        >>> format_dice_roll(28, result="+5", style="verbose")
        'Roll: 28 → "+5"'
    """
    # Use dice_desc if available, otherwise just the roll number
    roll_str = dice_desc if dice_desc else str(roll)
    
    if style == "verbose":
        if result:
            return f"Roll: {roll_str} → \"{result}\""
        else:
            return f"Roll: {roll_str}"
    else:
        # Standard compact format
        if prefix:
            if result:
                return f"{prefix}:{roll_str}→\"{result}\""
            else:
                return f"{prefix}:{roll_str}"
        else:
            if result:
                return f"{roll_str}→\"{result}\""
            else:
                return str(roll_str)


def format_play_dice_line(off_roll: int, off_result: str, def_row: str, def_result: str,
                          off_dice_desc: str = None, def_dice_desc: str = None,
                          priority: str = None, extra_info: str = "") -> str:
    """
    Format the standard dice line for a play showing offense and defense rolls.
    
    Args:
        off_roll: Offensive dice roll value
        off_result: Offensive chart result
        def_row: Defensive row (e.g., "12" or "R1+G2=12")
        def_result: Defensive chart result
        off_dice_desc: Optional full offense dice description
        def_dice_desc: Optional full defense dice description
        priority: Optional priority resolution result
        extra_info: Optional extra info to append (e.g., fumble/INT details)
        
    Returns:
        Formatted dice line like "(O:28→"+5" | D:12→"A" | O-HI)"
    """
    # Build offense part
    off_str = off_dice_desc if off_dice_desc else str(off_roll)
    off_part = f"O:{off_str}→\"{off_result}\""
    
    # Build defense part
    def_str = def_dice_desc if def_dice_desc else def_row
    def_part = f"D:{def_str}→\"{def_result}\""
    
    # Combine parts
    parts = [off_part, def_part]
    if priority:
        parts.append(priority)
    
    result = f"({' | '.join(parts)}"
    if extra_info:
        result += f" | {extra_info}"
    result += ")"
    
    return result


def parse_field_position(field_str: str, off_team: str = None) -> int:
    """
    Convert human-readable field position to internal position (1-99).
    
    Args:
        field_str: Field position string (e.g., "own 35", "opponent's 20", "GB 35", "midfield")
        off_team: Optional offensive team name for team-specific parsing
        
    Returns:
        Internal ball position (1-99)
        
    Examples:
        >>> parse_field_position("own 35")
        35
        >>> parse_field_position("opponent's 20")
        80
        >>> parse_field_position("midfield")
        50
        >>> parse_field_position("opp 20")
        80
    """
    field_str = field_str.lower().strip()
    
    if field_str == "midfield" or field_str == "50":
        return 50
    
    if field_str.startswith("own "):
        return int(field_str.replace("own ", ""))
    
    if field_str.startswith("opponent's ") or field_str.startswith("opp "):
        yard_line = int(field_str.replace("opponent's ", "").replace("opp ", ""))
        return 100 - yard_line
    
    # Try to parse as just a number (assume own territory)
    try:
        return int(field_str)
    except ValueError:
        pass
    
    # Could be team-specific like "GB 35" - would need team context
    # For now, return 50 as fallback
    return 50


def clamp_ball_position(position: int) -> int:
    """
    Clamp ball position to valid field range (1-99).
    
    The ball cannot be at position 0 (own end zone - would be safety/touchback)
    or position 100 (opponent's end zone - would be touchdown).
    
    Args:
        position: Raw ball position that may be out of bounds
        
    Returns:
        Position clamped to range [1, 99]
        
    Examples:
        >>> clamp_ball_position(50)
        50
        >>> clamp_ball_position(0)
        1
        >>> clamp_ball_position(100)
        99
        >>> clamp_ball_position(-5)
        1
        >>> clamp_ball_position(105)
        99
    """
    return max(1, min(99, position))


def yards_to_goal(ball_position: int) -> int:
    """
    Calculate yards remaining to opponent's goal line.
    
    Args:
        ball_position: Current ball position (1-99, yards from own goal)
        
    Returns:
        Yards to opponent's goal line
        
    Examples:
        >>> yards_to_goal(20)
        80
        >>> yards_to_goal(80)
        20
        >>> yards_to_goal(50)
        50
    """
    return 100 - ball_position


def fg_distance(ball_position: int) -> int:
    """
    Calculate field goal distance from current ball position.
    
    FG distance = yards to goal + 17 (10 yard end zone + 7 yard snap/hold)
    
    Args:
        ball_position: Current ball position (1-99, yards from own goal)
        
    Returns:
        Field goal distance in yards
        
    Examples:
        >>> fg_distance(80)
        37
        >>> fg_distance(50)
        67
        >>> fg_distance(97)
        20
    """
    return yards_to_goal(ball_position) + 17

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

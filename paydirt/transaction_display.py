"""
Example display logic using transaction-based play events.

This module demonstrates how the display code would be simplified
by iterating through PlayTransaction events rather than inspecting
scattered attributes on PlayResult/PlayOutcome.

This is a PROTOTYPE to evaluate the viability of the transaction approach.
"""
from typing import Optional

from .play_events import (
    EventType,
    PlayEvent,
    PlayTransaction,
    PendingDecision,
)


def display_transaction_compact(
    txn: PlayTransaction,
    play_name: str,
    commentary: str = ""
) -> None:
    """
    Display a play transaction in compact mode.
    
    This replaces the complex conditional logic in display_play_result
    with a simple iteration through events.
    
    Example output for an interception:
    
    ► MEDIUM PASS: INTERCEPTED! - Bad decision by the QB! ★ TURNOVER!
      (O:38→"INT 13" | D:2→"" | INT)
      INT at own 47, returned 25 yds
      (Return roll: B3+W2+W2=34 → "25")
    """
    # Determine the primary result for the action line
    action_line = _build_action_line(txn, play_name, commentary)
    print(action_line)
    
    # Show each event's dice details on subsequent lines
    for event in txn.events:
        dice_line = event.format_dice_line()
        if dice_line:
            # Indent dice details
            print(f"  {dice_line}")
        
        # For turnovers, show additional context
        if event.event_type == EventType.INTERCEPTION:
            spot = event.spot or 0
            print(f"  INT at own {spot}")
        elif event.event_type == EventType.INT_RETURN:
            if event.yards > 0:
                print(f"  Returned {event.yards} yds")
            elif event.yards == 0:
                print(f"  No return")
        elif event.event_type == EventType.FUMBLE:
            print(f"  Fumble at {'+' if event.yards >= 0 else ''}{event.yards} yds")
        elif event.event_type == EventType.FUMBLE_RECOVERY:
            if event.possession_change:
                print(f"  Defense recovers!")
            else:
                print(f"  Offense recovers")


def _build_action_line(
    txn: PlayTransaction,
    play_name: str,
    commentary: str
) -> str:
    """Build the primary action line based on transaction outcome."""
    # Determine result string based on events
    result_str = ""
    special_marker = ""
    
    if txn.has_event_type(EventType.INTERCEPTION):
        int_event = txn.get_events_by_type(EventType.INTERCEPTION)[0]
        return_events = txn.get_events_by_type(EventType.INT_RETURN)
        
        if return_events and return_events[0].yards > 0:
            result_str = f"INTERCEPTED! Returned {return_events[0].yards} yds"
        else:
            result_str = "INTERCEPTED!"
        
        if txn.touchdown:
            special_marker = " ★ PICK SIX!"
        else:
            special_marker = " ★ TURNOVER!"
    
    elif txn.has_event_type(EventType.FUMBLE):
        recovery_events = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)
        
        if txn.turnover:
            if txn.touchdown:
                result_str = "FUMBLE - Loss! RETURNED FOR TD!"
                special_marker = " ★ SCOOP AND SCORE!"
            else:
                result_str = "FUMBLE - Loss!"
                special_marker = " ★ TURNOVER!"
        else:
            result_str = "FUMBLE - Recovered!"
    
    elif txn.touchdown:
        result_str = "TOUCHDOWN!"
        special_marker = " ★ TOUCHDOWN!"
    
    elif txn.safety:
        result_str = "SAFETY!"
        special_marker = " ★ SAFETY!"
    
    elif txn.first_down:
        result_str = f"+{txn.yards_gained}"
        special_marker = " FIRST DOWN!"
    
    elif txn.yards_gained > 0:
        result_str = f"+{txn.yards_gained}"
    
    elif txn.yards_gained < 0:
        result_str = f"{txn.yards_gained}"
    
    else:
        result_str = "No gain"
    
    # Build final line
    if commentary:
        return f"► {play_name.upper()}: {result_str} - {commentary}{special_marker}"
    else:
        return f"► {play_name.upper()}: {result_str}{special_marker}"


def display_pending_decision(decision: PendingDecision) -> None:
    """Display a pending decision prompt."""
    print(f"\n  *** {decision.prompt} ***")
    print(f"  {decision.deciding_team.upper()} must choose:")
    for i, option in enumerate(decision.options, 1):
        print(f"    [{i}] {option.description}")


def display_transaction_verbose(
    txn: PlayTransaction,
    play_name: str,
    off_team: str,
    def_team: str
) -> None:
    """
    Display a play transaction in verbose mode.
    
    Shows each event as a separate section with full details.
    """
    print("\n" + "=" * 70)
    print(f"  THE PLAY: {off_team} {play_name}")
    print("=" * 70)
    
    for i, event in enumerate(txn.events, 1):
        print(f"\n  Step {i}: {event.event_type.value.upper()}")
        print(f"  {'-' * 40}")
        print(f"  {event.description}")
        
        if event.dice_roll is not None:
            print(f"  Dice: {event.dice_desc}")
            if event.chart_result:
                print(f"  Result: {event.chart_result}")
        
        if event.yards != 0:
            print(f"  Yards: {'+' if event.yards > 0 else ''}{event.yards}")
        
        if event.possession_change:
            print(f"  >>> POSSESSION CHANGE <<<")
    
    # Final state
    print("\n" + "=" * 70)
    print("  FINAL RESULT")
    print("=" * 70)
    
    if txn.touchdown:
        print("  TOUCHDOWN!")
    elif txn.safety:
        print("  SAFETY!")
    elif txn.turnover:
        print(f"  TURNOVER - {def_team} ball")
    elif txn.first_down:
        print(f"  FIRST DOWN - {txn.yards_gained} yards gained")
    else:
        print(f"  {txn.yards_gained} yards - {txn.final_down} & {txn.final_yards_to_go}")


# Example usage demonstrating the simplified display logic
def example_interception_display():
    """
    Example: How an interception would be displayed.
    
    BEFORE (current system):
    - Check outcome.result.result_type == ResultType.INTERCEPTION
    - getattr(outcome.result, 'int_return_yards', None)
    - getattr(outcome.result, 'int_return_dice', None)
    - getattr(outcome.result, 'int_spot', None)
    - Complex conditionals to build display string
    
    AFTER (transaction system):
    - Iterate through txn.events
    - Each event has its own description and dice details
    - Display logic is straightforward iteration
    """
    from .play_events import (
        create_chart_lookup_event,
        create_interception_event,
        create_return_event,
    )
    
    # Build transaction
    txn = PlayTransaction()
    
    txn.add_event(create_chart_lookup_event(
        offense_roll=38,
        offense_desc="B3+W4+W4=38",
        offense_result="INT 13",
        defense_row="2",
        defense_result="",
        priority="INT",
        acting_team="DEN"
    ))
    
    txn.add_event(create_interception_event(
        int_spot=47,
        int_yards_downfield=13,
        acting_team="DEN"
    ))
    
    txn.add_event(create_return_event(
        event_type=EventType.INT_RETURN,
        return_roll=34,
        return_desc="B3+W2+W2=34",
        return_yards=25,
        chart_result="25",
        acting_team="PIT"
    ))
    
    # Set final state
    txn.turnover = True
    txn.final_ball_position = 72
    txn.is_complete = True
    
    # Display
    print("\n--- COMPACT MODE ---")
    display_transaction_compact(txn, "Medium Pass", "Bad decision by the QB!")
    
    print("\n--- VERBOSE MODE ---")
    display_transaction_verbose(txn, "Medium Pass", "DEN", "PIT")


def example_fumble_recovered_display():
    """Example: Fumble recovered by offense."""
    from .play_events import (
        create_chart_lookup_event,
        create_fumble_event,
        create_recovery_event,
    )
    
    txn = PlayTransaction()
    
    txn.add_event(create_chart_lookup_event(
        offense_roll=15,
        offense_desc="B1+W2+W3=15",
        offense_result="F+8",
        defense_row="3",
        defense_result="(3)",
        priority="F-#",
        acting_team="TB"
    ))
    
    txn.add_event(create_fumble_event(
        yards_before_fumble=8,
        fumble_spot=48,
        acting_team="TB"
    ))
    
    txn.add_event(create_recovery_event(
        recovery_roll=24,
        recovery_desc="B2+W2+W2=24",
        offense_recovers=True,
        recovery_range=(11, 29),
        acting_team="TB"
    ))
    
    # Set final state - offense keeps ball, loses yardage to fumble spot
    txn.turnover = False
    txn.yards_gained = 8  # Gained 8 before fumble, recovered at that spot
    txn.final_ball_position = 48
    txn.is_complete = True
    
    print("\n--- FUMBLE RECOVERED ---")
    display_transaction_compact(txn, "Screen")


if __name__ == "__main__":
    # Run examples
    example_interception_display()
    example_fumble_recovered_display()

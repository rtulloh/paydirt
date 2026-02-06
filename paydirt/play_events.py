"""
Transaction-based play event model for Paydirt.

This module provides a structured way to capture each discrete event
that occurs during a play, allowing for cleaner display logic and
better encapsulation of dice rolls and outcomes.

Design Philosophy:
- Each PlayEvent captures a single atomic action with its dice/result
- Events form a chain that can be displayed sequentially
- Decision points (penalties) create branches in the event chain
- Final game state is computed from the resolved event chain
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .utils import format_dice_roll


class EventType(Enum):
    """Types of events that can occur during a play."""
    # Primary play events
    PLAY_CALL = "play_call"           # Initial play selection
    CHART_LOOKUP = "chart_lookup"     # Dice roll and chart result
    PRIORITY_RESOLUTION = "priority"  # Offense vs defense priority
    
    # Turnover events
    FUMBLE = "fumble"                 # Fumble occurred
    FUMBLE_RECOVERY = "recovery"      # Recovery roll result
    FUMBLE_RETURN = "fumble_return"   # Return after recovery
    INTERCEPTION = "interception"     # INT occurred
    INT_RETURN = "int_return"         # INT return roll
    
    # Penalty events
    PENALTY_DETECTED = "penalty"      # Penalty flag thrown
    PENALTY_REROLL = "reroll"         # Offense reroll after penalty
    PENALTY_DECISION = "decision"     # Choice made (accept play/penalty)
    PENALTY_APPLIED = "penalty_applied"  # Penalty yardage applied
    
    # Special plays
    FIELD_GOAL_ATTEMPT = "fg_attempt"
    FIELD_GOAL_RESULT = "fg_result"
    PUNT = "punt"
    PUNT_RETURN = "punt_return"
    KICKOFF = "kickoff"
    KICKOFF_RETURN = "kickoff_return"
    BLOCKED_KICK = "blocked"
    BLOCK_RECOVERY = "block_recovery"
    BLOCK_RETURN = "block_return"
    
    # Scoring events
    TOUCHDOWN = "touchdown"
    SAFETY = "safety"
    
    # Clock events
    TIMEOUT = "timeout"
    TWO_MINUTE_WARNING = "two_min_warning"
    
    # Final state
    PLAY_COMPLETE = "complete"


@dataclass
class PlayEvent:
    """
    A single atomic event in a play sequence.
    
    Each event captures:
    - What happened (event_type, description)
    - The dice mechanics (dice_roll, dice_desc, chart_result)
    - The outcome (yards, result_value)
    
    Events are designed to be displayed in sequence, with each
    generating one line of game action and one line of dice details.
    """
    event_type: EventType
    description: str  # Human-readable action (e.g., "INTERCEPTED!")
    
    # Dice mechanics (optional - not all events have dice)
    dice_roll: Optional[int] = None
    dice_desc: Optional[str] = None  # e.g., "B2+W3+W1=24"
    chart_result: Optional[str] = None  # Raw chart value (e.g., "INT 13")
    
    # Outcome details
    yards: int = 0
    spot: Optional[int] = None  # Field position where event occurred
    
    # For turnovers - who has the ball after this event
    possession_change: bool = False
    
    # For display - team names involved
    acting_team: str = ""
    
    def format_action_line(self) -> str:
        """Format the human-readable action line."""
        return self.description
    
    def format_dice_line(self) -> str:
        """Format the technical dice details line using standardized format."""
        if self.dice_roll is None:
            return ""
        
        # Use standardized format_dice_roll helper
        return f"({format_dice_roll(self.dice_roll, self.dice_desc, self.chart_result)})"


@dataclass
class DecisionOption:
    """A single option in a pending decision."""
    option_id: str  # "accept_play", "accept_penalty_0", etc.
    description: str  # Human-readable description
    yards: int = 0  # Yards gained/lost if this option chosen
    replays_down: bool = False  # Does this option replay the down?


@dataclass
class PendingDecision:
    """
    A decision point that must be resolved before the play can complete.
    
    This handles the coupling between transactions - a penalty creates
    a fork where subsequent events depend on the choice made.
    """
    decision_type: str  # "penalty_choice", "onside_kick", etc.
    deciding_team: str  # Who makes the decision
    options: List[DecisionOption] = field(default_factory=list)
    prompt: str = ""  # Question to display
    
    # Events that would occur for each option (computed but not committed)
    # Key is option_id, value is list of events that would follow
    conditional_events: dict = field(default_factory=dict)


@dataclass
class PlayTransaction:
    """
    Complete transaction for a play, including all sub-events.
    
    A transaction captures everything that happened during a play:
    - The sequence of events (in order)
    - Any pending decision that needs resolution
    - The final game state after resolution
    
    The transaction is "pending" until all decisions are resolved,
    at which point the final state is computed and committed.
    """
    # Event chain - what happened (in order)
    events: List[PlayEvent] = field(default_factory=list)
    
    # Decision point (if any) - must be resolved before completing
    pending_decision: Optional[PendingDecision] = None
    
    # Is this transaction fully resolved?
    is_complete: bool = False
    
    # Final state (computed after all events/decisions resolved)
    final_ball_position: int = 0
    final_down: int = 1
    final_yards_to_go: int = 10
    possession_team: str = ""
    
    # Summary flags
    turnover: bool = False
    touchdown: bool = False
    safety: bool = False
    first_down: bool = False
    field_goal_made: bool = False
    
    # For backward compatibility with existing PlayOutcome
    yards_gained: int = 0
    
    def add_event(self, event: PlayEvent) -> None:
        """Add an event to the transaction chain."""
        self.events.append(event)
    
    def get_events_by_type(self, event_type: EventType) -> List[PlayEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]
    
    def has_event_type(self, event_type: EventType) -> bool:
        """Check if an event type occurred."""
        return any(e.event_type == event_type for e in self.events)
    
    def format_display(self) -> List[tuple[str, str]]:
        """
        Format all events for display.
        
        Returns list of (action_line, dice_line) tuples.
        """
        result = []
        for event in self.events:
            action = event.format_action_line()
            dice = event.format_dice_line()
            if action:  # Only include events with display content
                result.append((action, dice))
        return result


def create_chart_lookup_event(
    offense_roll: int,
    offense_desc: str,
    offense_result: str,
    defense_row: str,
    defense_result: str,
    priority: str,
    acting_team: str = ""
) -> PlayEvent:
    """
    Create a chart lookup event capturing the dice mechanics.
    
    This is the core event for most plays - the offensive and defensive
    dice rolls and their chart results.
    """
    return PlayEvent(
        event_type=EventType.CHART_LOOKUP,
        description=f"Chart: O:{offense_roll}→\"{offense_result}\" vs D:{defense_row}→\"{defense_result}\"",
        dice_roll=offense_roll,
        dice_desc=offense_desc,
        chart_result=f"O:{offense_result} D:{defense_result} → {priority}",
        acting_team=acting_team
    )


def create_fumble_event(
    yards_before_fumble: int,
    fumble_spot: int,
    acting_team: str = ""
) -> PlayEvent:
    """Create a fumble event."""
    yard_str = f"+{yards_before_fumble}" if yards_before_fumble > 0 else str(yards_before_fumble)
    return PlayEvent(
        event_type=EventType.FUMBLE,
        description=f"FUMBLE at {yard_str} yards!",
        yards=yards_before_fumble,
        spot=fumble_spot,
        acting_team=acting_team
    )


def create_recovery_event(
    recovery_roll: int,
    recovery_desc: str,
    offense_recovers: bool,
    recovery_range: tuple[int, int],
    acting_team: str = ""
) -> PlayEvent:
    """Create a fumble recovery event."""
    result = "RECOVERED by offense" if offense_recovers else "LOST to defense"
    return PlayEvent(
        event_type=EventType.FUMBLE_RECOVERY,
        description=f"Recovery roll: {result}",
        dice_roll=recovery_roll,
        dice_desc=recovery_desc,
        chart_result=f"Range {recovery_range[0]}-{recovery_range[1]}: {'Recovered' if offense_recovers else 'Lost'}",
        possession_change=not offense_recovers,
        acting_team=acting_team
    )


def create_interception_event(
    int_spot: int,
    int_yards_downfield: int,
    acting_team: str = ""
) -> PlayEvent:
    """Create an interception event."""
    return PlayEvent(
        event_type=EventType.INTERCEPTION,
        description=f"INTERCEPTED {int_yards_downfield} yards downfield!",
        spot=int_spot,
        yards=int_yards_downfield,
        possession_change=True,
        acting_team=acting_team
    )


def create_return_event(
    event_type: EventType,
    return_roll: int,
    return_desc: str,
    return_yards: int,
    chart_result: str,
    is_touchdown: bool = False,
    acting_team: str = ""
) -> PlayEvent:
    """Create a return event (INT return, fumble return, etc.)."""
    if is_touchdown:
        desc = "Returned for TOUCHDOWN!"
    elif return_yards > 0:
        desc = f"Returned {return_yards} yards"
    elif return_yards < 0:
        desc = f"Tackled for {abs(return_yards)} yard loss"
    else:
        desc = "No return"
    
    return PlayEvent(
        event_type=event_type,
        description=desc,
        dice_roll=return_roll,
        dice_desc=return_desc,
        chart_result=chart_result,
        yards=return_yards,
        acting_team=acting_team
    )


def create_penalty_event(
    penalty_type: str,
    yards: int,
    description: str,
    offended_team: str
) -> PlayEvent:
    """Create a penalty detected event."""
    return PlayEvent(
        event_type=EventType.PENALTY_DETECTED,
        description=f"FLAG: {description}",
        yards=yards,
        chart_result=f"{penalty_type} {yards}",
        acting_team=offended_team
    )


def create_touchdown_event(acting_team: str = "") -> PlayEvent:
    """Create a touchdown event."""
    return PlayEvent(
        event_type=EventType.TOUCHDOWN,
        description="TOUCHDOWN!",
        acting_team=acting_team
    )


def create_safety_event(acting_team: str = "") -> PlayEvent:
    """Create a safety event."""
    return PlayEvent(
        event_type=EventType.SAFETY,
        description="SAFETY!",
        acting_team=acting_team
    )

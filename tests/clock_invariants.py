"""Clock invariants the AI audit can assert on every selected call.

`validate_game` only reconciles the end of a game: the completion flag, the
final scores and the scoring-log sums. A rule bug that yields a plausible,
fully-accounted game passes every audit game - RULE-005 did exactly that. These
checks watch the two transitions RULE-005 broke, on the action that caused them:

1. A period may be extended only through the engine's own defensive-foul clock
   hold. RULE-005 set `untimed_down_pending` directly for an accepted offensive
   field-goal foul, without ever holding the period for a defensive foul.
2. An accepted foul replays the down on the clock. If time remained when the
   action started, the replay must actually consume some of it.

Both use the engine's verdicts rather than re-deriving the rules. The foul
labels on a chart are relative to that chart's offense, and they reverse at a
return - a kicking team's punt foul is a defensive foul once the return is in
progress. Re-deriving "offensive fouls never extend" from the label is wrong;
observing `defensive_penalty` on `_use_time` is exactly the rule the engine
applies, so the observer cannot drift from it.

Read-only: this observer never changes engine state, dice, or the play log.
"""

from __future__ import annotations

from collections import Counter

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome


class ClockInvariantAudit:
    """Reject an unjustified period extension or a free replayed down."""

    EVENTS = ("accepted_foul", "period_extension", "charged_replay")

    def __init__(self) -> None:
        self.counts = Counter({event: 0 for event in self.EVENTS})
        self.live_game: PaydirtGameEngine | None = None
        self.defensive_hold = False
        self.flag_before_action = False
        self.seconds_before_action = 0.0
        self.accepted_foul: str | None = None

    def decision(self, game: PaydirtGameEngine) -> None:
        """Start a new observation window before the next selected call."""
        self.live_game = game
        self.flag_before_action = game.has_untimed_down()
        self.seconds_before_action = game.state.time_remaining * 60
        self.defensive_hold = False
        self.accepted_foul = None

    def charge(self, engine: PaydirtGameEngine, defensive_penalty: bool) -> None:
        """Record a live clock charge that the engine classified as a defensive hold."""
        # Projections run on throwaway copies; only the live engine counts.
        if defensive_penalty and engine is self.live_game:
            self.defensive_hold = True

    def penalty(self, outcome: PlayOutcome, decision: tuple[bool, int | None]) -> None:
        """Remember which foul the offended coach accepted, for diagnostics."""
        choice = outcome.penalty_choice
        if choice is None:
            return
        accept_play, index = decision
        if accept_play and not choice.offsetting:
            return
        self.counts["accepted_foul"] += 1
        label = "an accepted foul"
        options = choice.penalty_options
        position = 0 if index is None else index
        if choice.offsetting:
            label = "offsetting fouls"
        elif options and 0 <= position < len(options):
            label = f"an accepted {options[position].penalty_type} foul"
        self.accepted_foul = label

    def result(self, game: PaydirtGameEngine, outcome: PlayOutcome) -> None:
        """Check the finalized action against the extension and clock rules."""
        extended = game.has_untimed_down()
        newly_extended = extended and not self.flag_before_action

        if newly_extended:
            if not self.defensive_hold:
                raise ValueError(
                    f"Period extended by {self.accepted_foul or 'a non-defensive act'} "
                    "without a defensive-foul clock hold"
                )
            self.counts["period_extension"] += 1

        if (outcome.penalty_applied and not extended and self.seconds_before_action > 0):
            trace = outcome.clock_trace
            charged = trace.charged_seconds if trace is not None else 0.0
            if charged <= 0:
                raise ValueError(
                    f"{self.accepted_foul or 'An accepted foul'} charged no clock "
                    "time; "
                    "a replayed down must consume its interval"
                )
            self.counts["charged_replay"] += 1

    def report(self) -> dict:
        """Return observed coverage; absent events are reported, not inferred."""
        return {
            "covered": dict(self.counts),
            "unexercised": [event for event in self.EVENTS if not self.counts[event]],
            "limits": "Selected calls only; the extension hold and clock charge of "
                      "accepted fouls. Kickoff chains and CLI announcements still "
                      "require deterministic tests.",
        }

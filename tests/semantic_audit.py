"""Read-only semantic checks; reports contain counts, never private narrative text.

These narrow oracles supplement deterministic tests, not a complete rules audit.
"""

from collections import Counter

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import CHART_PLAY_TYPES, ResultType


class SemanticAudit:
    """Count observed events separately from absent/untested event categories."""

    EVENTS = ("scoring_penalty_choice", "qb_scramble_td", "qb_scramble_td_accounting",
              "incomplete", "fumble_at_spot")

    def __init__(self) -> None:
        self.counts = Counter({event: 0 for event in self.EVENTS})
        self.snapshot = None

    def before(self, game: PaydirtGameEngine) -> None:
        """Capture independent pre-call attribution, not mutable stats references."""
        state = game.state
        stats = state.offense_stats
        self.snapshot = (state.is_home_possession, state.ball_position,
                         stats.rushing_yards, stats.passing_yards, len(state.scoring_plays))

    def penalty(self, outcome: PlayOutcome, decision: tuple[bool, int]) -> None:
        """Keep our TD, erase theirs when a legal replay penalty is available."""
        choice = outcome.penalty_choice
        if not choice or not (outcome.projected_touchdown is True or choice.play_result.touchdown is True):
            return
        offense = choice.offended_team == "offense"
        eligible = [(i, option) for i, option in enumerate(choice.penalty_options)
                    if option.penalty_type in (("DEF", "PI") if offense else ("OFF",))]
        if not eligible:
            return
        accept, index = decision
        scorer_is_offense = not choice.play_result.turnover
        if accept != (offense == scorer_is_offense):
            raise ValueError("Incorrect scoring-side penalty choice")
        if not accept and index not in [i for i, _ in eligible]:
            raise ValueError("Scoring penalty choice used an ineligible index")
        self.counts["scoring_penalty_choice"] += 1

    def result(self, game: PaydirtGameEngine, outcome: PlayOutcome) -> None:
        """Check finalized actions; accepted/offset penalties have no live action."""
        if outcome.penalty_applied or (outcome.penalty_choice and outcome.penalty_choice.offsetting):
            return
        result = outcome.result
        if result.result_type == ResultType.QB_SCRAMBLE and outcome.touchdown:
            text = game.get_play_narrative(outcome).lower()
            if "scrambl" not in text or "pass complete" in text:
                raise ValueError("QB scramble touchdown narrative is not rushing")
            self.counts["qb_scramble_td"] += 1
            if self.snapshot is not None:
                home, spot, rushing, passing, scores = self.snapshot
                stats = game.state.home_stats if home else game.state.away_stats
                new_scores = game.state.scoring_plays[scores:]
                if (stats.rushing_yards - rushing != min(outcome.yards_gained, 100 - spot)
                        or stats.passing_yards != passing
                        or len(new_scores) != 1 or new_scores[0].play_type != "TD"
                        or new_scores[0].is_home_team != home):
                    raise ValueError("QB scramble touchdown accounting disagrees with action")
                self.counts["qb_scramble_td_accounting"] += 1
        if result.result_type == ResultType.INCOMPLETE:
            if outcome.yards_gained != 0 or outcome.touchdown:
                raise ValueError("Incomplete pass credited yards or touchdown")
            self.counts["incomplete"] += 1
        if (outcome.play_type in CHART_PLAY_TYPES
                and result.result_type == ResultType.FUMBLE and result.fumble_recovered
                and not result.fumble_return_dice and not outcome.touchdown and not outcome.safety):
            text = (result.rule_explanation or "").lower()
            if "before fumble" not in text or "at the spot" not in text or "advanced" in text:
                raise ValueError("Recovery at spot narrative invents an advance")
            self.counts["fumble_at_spot"] += 1

    def report(self) -> dict:
        """Zero coverage is explicit; random games need not contain rare events."""
        return {"covered": dict(self.counts),
                "unexercised": [event for event in self.EVENTS if not self.counts[event]],
                "limits": "Selected final calls and CPU scoring penalty choices only; conversion periods checked separately. CLI announcement counts, player identity, stat deltas, other coaching choices and unobserved kickoff chains require deterministic tests."}

"""Bounded chart estimates and weighted Hard offense, not a second rules engine.

Scores are coaching utilities, never defense-adjusted conversion probabilities.
Unresolved symbols retain their full probability mass with neutral utility; they
are not rerolled or removed to inflate the remaining positive-yardage rate.
"""

from collections import Counter
from math import ceil, exp

from .chart_loader import OffenseChart
from .play_resolver import CHART_PLAY_TYPES, PlayType, chart_roll_weights
from .priority_chart import ResultCategory, categorize_result


def situation_key(down: int, distance: int) -> tuple[int, int]:
    """Keep first downs and distance bands distinct, including very long yardage."""
    band = 0 if distance <= 3 else 1 if distance <= 6 else 2 if distance <= 10 else 3
    return down, band


class OffensiveStrategy:
    """Select among credible calls while gently discounting recent repetition."""

    # These are coaching parameters, not usage quotas or gameplay probabilities.
    TEMPERATURE = .45
    COMPETITIVE_GAP = .9
    HISTORY_DECAY = .94
    REPETITION_FLOOR = .30

    def __init__(self, chart: OffenseChart) -> None:
        self.chart = chart
        self._score_cache: dict[tuple[int, int], dict[PlayType, float]] = {}

    def scores(self, down: int, distance: int) -> dict[PlayType, float]:
        """Estimate target attainment/progress and known risks under full dice mass.

        First/second downs target half/70% of the distance; later downs target
        the line to gain. Numeric gains are bounded so rare huge cells cannot
        dominate. B/QT, variable yardage, defensive penalties and priority-only
        results remain unresolved. No hypothetical dice or hidden defense enter.
        """
        key = down, max(1, distance)
        if key in self._score_cache:
            return dict(self._score_cache[key])
        fraction = .5 if down == 1 else .7 if down == 2 else 1.0
        target = max(1, ceil(key[1] * fraction))
        weights = chart_roll_weights()
        total = sum(weights.values())
        scores = {}
        for play in CHART_PLAY_TYPES:
            rows = getattr(self.chart, play.value)
            if not any(roll in weights for roll in rows):
                continue
            utility = 0.0
            for roll, raw in rows.items():
                if roll not in weights:
                    continue
                text = str(raw).strip().upper()
                category, yards = categorize_result(text.rstrip("*†+"))
                value = 0.0
                if category in (
                    ResultCategory.GREEN_NUMBER, ResultCategory.WHITE_NUMBER, ResultCategory.RED_NUMBER,
                ) and yards is not None:
                    value = float(yards >= target) + .4 * max(-1., min(2., yards / target))
                    if yards < 0:
                        value -= .4
                elif category == ResultCategory.INT:
                    value = -1.5
                elif category in (ResultCategory.FUMBLE, ResultCategory.FUMBLE_PLUS, ResultCategory.FUMBLE_MINUS):
                    value = -1.0  # Fumble risk, not a claim that every fumble is lost.
                elif category == ResultCategory.PENALTY and text.startswith("OFF"):
                    value = -.3  # Enforcement/choice remains the engine's job.
                elif category == ResultCategory.TD:
                    value = 1.8
                # BLACK/INC/blank are zero; other unresolved outcomes also have
                # neutral utility. Importantly, none renormalize the dice mass.
                utility += weights[roll] / total * value
            scores[play] = utility
        self._score_cache[key] = scores
        return dict(scores)

    def conversion_scores(self, distance: int, points: int) -> dict[PlayType, float]:
        """Bounded try utilities, not defense-adjusted success probabilities.

        Extra yards have no value beyond the goal. Unknown cells keep neutral
        utility and their full dice mass; turnovers/fumbles retain risk costs.
        """
        weights = chart_roll_weights()
        total = sum(weights.values())
        scores = {}
        for play in CHART_PLAY_TYPES:
            rows = getattr(self.chart, play.value)
            if not any(roll in weights for roll in rows):
                continue
            utility = 0.0
            for roll, raw in rows.items():
                if roll not in weights:
                    continue
                text = str(raw).strip().upper()
                category, yards = categorize_result(text.rstrip("*†+"))
                value = 0.0
                if category in (
                    ResultCategory.GREEN_NUMBER, ResultCategory.WHITE_NUMBER, ResultCategory.RED_NUMBER,
                ) and yards is not None:
                    value = points if yards >= distance else 0.0
                elif category == ResultCategory.TD:
                    value = points
                elif category == ResultCategory.INT:
                    value = -points
                elif category in (ResultCategory.FUMBLE, ResultCategory.FUMBLE_PLUS, ResultCategory.FUMBLE_MINUS):
                    value = -points / 2
                utility += weights[roll] / total * value
            scores[play] = utility
        return scores

    def weights(
        self, down: int, distance: int, history: list[dict], is_home: bool,
    ) -> dict[PlayType, float]:
        """Return unnormalized weights; previews never mutate call history."""
        scores = self.scores(down, distance)
        if not scores:
            return {}
        best = max(scores.values())
        recent = Counter()
        own_calls = [call for call in history if call["is_home"] == is_home]
        for age, call in enumerate(reversed(own_calls[-96:])):
            if situation_key(call["down"], call["distance"]) == situation_key(down, distance):
                recent[call["play"]] += self.HISTORY_DECAY ** age
        return {
            play: exp((score - best) / self.TEMPERATURE) * max(
                self.REPETITION_FLOOR, 1 / (1 + .9 * recent[play.value]))
            for play, score in scores.items()
            if best - score <= self.COMPETITIVE_GAP
        }

"""Weighted primary and fresh-primary-reroll controls for chart placement tests."""

from collections import Counter
from dataclasses import fields
from unittest.mock import patch

from paydirt.chart_loader import TeamChart
from paydirt.play_resolver import (
    DefenseType,
    PlayType,
    chart_roll_weights,
    resolve_play,
    resolve_play_with_penalties,
)


def primary_result_distribution(
    chart: TeamChart, defender: TeamChart, play: PlayType,
    defense: DefenseType, penalties: bool,
) -> Counter:
    """Integrate raw nonfoul primary rerolls; keep supplemental roll 23 fixed.

    A foul rerolls the primary column, whose row positions may have changed.
    Enumerate each distinct nonfoul token at its full physical mass rather than
    conditioning that independent primary reroll on a fixed printed row. This
    covers the selected result after the first nonfoul reroll, not every possible
    repeated-foul history or penalty-option transaction.
    """
    weights = chart_roll_weights()
    column = getattr(chart.offense, "line_plunge" if play == PlayType.QB_SNEAK else play.value)
    nonfoul_mass: Counter[str] = Counter()
    representative = {}
    for row, token in column.items():
        if not token.startswith(("OFF", "DEF", "PI")):
            nonfoul_mass[token] += weights[row]
            representative.setdefault(token, row)
    denominator = sum(nonfoul_mass.values())
    assert denominator > 0, "Distribution control requires a supported nonfoul result"
    route = resolve_play_with_penalties if penalties else resolve_play
    observed = Counter()
    for roll, weight in weights.items():
        rerolls = ([(representative[token], mass) for token, mass in sorted(nonfoul_mass.items())]
                   if penalties and column[roll].startswith(("OFF", "DEF"))
                   else [(None, denominator)])
        for reroll, reroll_weight in rerolls:
            stream = [(roll, "primary")]
            if reroll is not None:
                stream.append((reroll, "fresh primary reroll"))
            stream.extend([(23, "fresh supplemental")] * 20)
            with (
                patch("paydirt.play_resolver.roll_chart_dice", side_effect=stream),
                patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
            ):
                output = route(chart, defender, play, defense)
            result = output.play_result if penalties else output
            signature = tuple((item.name, repr(getattr(result, item.name))) for item in fields(result)
                              if item.name not in {"dice_roll", "description", "rule_explanation"})
            observed[signature] += weight * reroll_weight
    return observed

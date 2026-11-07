"""Unwired, source-independent components of the reviewed gain experiment.

No generator or game path calls these helpers. A future caller must establish
complete supported source, eligible pooled training receipts and final recipe
identity; this module cannot confer those approvals or statistical acceptance.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .play_resolver import chart_roll_weights

_RUNS = ("line_plunge", "off_tackle", "end_run", "draw")
_PASSES = ("screen", "short_pass", "medium_pass", "long_pass", "te_short_long")
_COLUMNS = (*_RUNS, *_PASSES, "breakaway", "qb_time")
_NUMERIC = re.compile(r"([+-]?\d+)([*†]?)")
_ROUNDING = "binary64-product / nearest-integer ties-to-even"
_QUANTILES = ("0", ".1", ".25", ".5", ".75", ".9", ".99", "1")


@dataclass(frozen=True)
class GainBaseline:
    """Pooled credited numerators/counts, with explicit source support.

    Counts and yard totals are positive integers. Source attempts determine
    shrinkage support; simulated attempts determine the pooled engine mean.
    Neither represents acceptance of a source projection or training history.
    """

    source_attempts: int
    source_yards: int
    engine_attempts: int
    engine_yards: int
    supported: bool


def _positive_integer(value: int, label: str) -> None:
    """Reject unknown, fractional, boolean or nonrepresentable input counts."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    try:
        finite = math.isfinite(float(value))
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{label} must be finite in binary64")


def derive_gain_normalization(
    cohort: Sequence[str], baselines: Mapping[str, Mapping[str, GainBaseline]],
) -> dict[str, Any]:
    """Derive both metric adjustments for every declared cohort member once.

    Args:
        cohort: Complete expected membership, independent of any failing subset.
        baselines: Passing/rushing pooled source and engine credited counts.

    Returns:
        Formula constants, weighted anchors and each intermediate adjustment.
        This is a pure arithmetic component, not an approved fitting recipe.

    Raises:
        ValueError: A required member, metric, support or positive count is absent.
    """
    if (isinstance(cohort, (str, bytes)) or not cohort
            or any(not isinstance(name, str) or not name for name in cohort)
            or len(set(cohort)) != len(cohort)):
        raise ValueError("Expected cohort must contain distinct nonempty team identities")
    if not isinstance(baselines, Mapping) or set(baselines) != {"passing", "rushing"}:
        raise ValueError("Complete cohort requires passing and rushing baselines")
    metrics: dict[str, Any] = {}
    for metric in ("passing", "rushing"):
        members = baselines[metric]
        if not isinstance(members, Mapping) or set(members) != set(cohort):
            raise ValueError(f"{metric} cohort membership is incomplete or contains extra teams")
        inputs: dict[str, dict[str, float | int]] = {}
        for name in cohort:
            row = members[name]
            if not isinstance(row, GainBaseline) or row.supported is not True:
                raise ValueError(f"{metric}/{name} requires explicit supported source counts")
            for field in ("source_attempts", "source_yards", "engine_attempts", "engine_yards"):
                _positive_integer(getattr(row, field), f"{metric}/{name}/{field}")
            target = row.source_yards / row.source_attempts
            engine_mean = row.engine_yards / row.engine_attempts
            if not all(math.isfinite(v) and 0 < v <= 99 for v in (target, engine_mean)):
                raise ValueError(f"{metric}/{name} requires finite positive means at most 99")
            inputs[name] = {
                "source_attempts": row.source_attempts,
                "source_yards": row.source_yards,
                "engine_attempts": row.engine_attempts,
                "engine_yards": row.engine_yards,
                "target": target,
                "engine_mean": engine_mean,
                "log_ratio": math.log(target) - math.log(engine_mean),
            }
        source_total = sum(members[name].source_attempts for name in cohort)
        # Sort values, rather than names, so renaming/permutation cannot change
        # the floating summation order. Normalized weights avoid n*r overflow.
        anchor = math.fsum(sorted(
            (members[name].source_attempts / source_total) * float(inputs[name]["log_ratio"])
            for name in cohort
        ))
        teams = {}
        for name in cohort:
            row = inputs[name]
            n = members[name].source_attempts
            centered = float(row["log_ratio"]) - anchor
            unconstrained = n / (n + 200) * centered
            z = max(math.log(.8), min(math.log(1.25), unconstrained))
            teams[name] = {
                **row, "centered_log_ratio": centered,
                "unclamped_log_adjustment": unconstrained, "log_adjustment": z,
                "multiplier": math.exp(z), "clamped": z != unconstrained,
            }
        metrics[metric] = {"anchor": anchor, "teams": teams}
    return {
        "method": "pooled-engine-baseline-fixed-anchor-v1",
        "component_only": True, "cohort": list(cohort), "pseudo_count": 200,
        "multiplier_bounds": [.8, 1.25], "numeric_representation": "binary64 math.log/fsum/exp",
        "rounding": _ROUNDING, "metrics": metrics,
    }


def _distribution(column: Mapping[int, str], weights: Mapping[int, int]) -> dict[str, Any]:
    """Report complete token mass and conditional ordinary-numeric summaries."""
    tokens: Counter[str] = Counter()
    numbers: Counter[int] = Counter()
    for row, token in column.items():
        tokens[token] += weights[row]
        match = _NUMERIC.fullmatch(token)
        if match:
            numbers[int(match[1])] += weights[row]
    mass = sum(numbers.values())
    quantiles: dict[str, int | None] = {}
    for label in _QUANTILES:
        q = Fraction(label)
        cumulative = 0
        quantiles[label] = None
        for value, count in sorted(numbers.items()):
            cumulative += count
            if cumulative * q.denominator >= mass * q.numerator:
                quantiles[label] = value
                break
    return {
        "token_masses": dict(sorted(tokens.items())), "numeric_mass": mass,
        "numeric_mean": sum(value * count for value, count in numbers.items()) / mass if mass else None,
        "zero_share": numbers[0] / mass if mass else None,
        "loss_share": sum(count for value, count in numbers.items() if value < 0) / mass if mass else None,
        "tail_20_share": sum(count for value, count in numbers.items() if value >= 20) / mass if mass else None,
        "tail_40_share": sum(count for value, count in numbers.items() if value >= 40) / mass if mass else None,
        "minimum": min(numbers) if numbers else None,
        "maximum": max(numbers) if numbers else None, "quantiles": quantiles,
    }


def _protected_masses(
    offense: Mapping[str, Mapping[int, str]], weights: Mapping[int, int],
) -> dict[str, dict[str, int]]:
    """Preserve symbols, numeric signs/zeroes and flags at each column's mass."""
    result = {}
    for name, column in offense.items():
        counts: Counter[str] = Counter()
        for row, token in column.items():
            match = _NUMERIC.fullmatch(token)
            if match and name != "qb_time":
                value = int(match[1])
                sign = "negative" if value < 0 else "positive" if value > 0 else "zero"
                key = f"numeric/{sign}/{match[2]}"
            else:
                key = f"protected/{token}"
            counts[key] += weights[row]
        result[name] = dict(counts)
    return result


def transform_offense_gains(
    offense: Mapping[str, Mapping[int, str]], *,
    passing_multiplier: float, rushing_multiplier: float,
) -> tuple[dict[str, dict[int, str]], dict[str, Any]]:
    """Transform an allocated synthetic offense before a future final layout.

    Ordinary primary numbers and numeric rushing B gains alone are eligible.
    F/F INC/QT, all other symbols and the complete QT column are copied exactly.
    The input is never mutated. Defense, special teams, rules and recovery
    ranges are outside this function's input and cannot be rewritten here.

    Args:
        offense: Complete eleven-column, thirty-row allocated offense.
        passing_multiplier: Approved bounded arithmetic factor, not a fitting knob.
        rushing_multiplier: Corresponding factor for direct runs and numeric B.

    Returns:
        Fresh offense plus weighted distributions and every rounding/cap effect.
        Numeric summaries are conditional on numeric cells, never whole-game YPA.

    Raises:
        ValueError: Shape, generated grammar, numeric domain or factor is invalid.
    """
    # Reuse the generator's existing grammar; do not invent a second decoder.
    # Kept local so this unwired component need not add a generator import edge
    # to the game's observer/calibration path.
    from .chart_generator import supported_generated_cell

    for factor in (passing_multiplier, rushing_multiplier):
        if (isinstance(factor, bool) or not isinstance(factor, (float, int))
                or not .8 <= factor <= 1.25 or not math.isfinite(factor)):
            raise ValueError("Gain multiplier must be finite and within [.8, 1.25]")
    if not isinstance(offense, Mapping) or set(offense) != set(_COLUMNS):
        raise ValueError("Allocated offense requires all eleven columns")
    weights = chart_roll_weights()
    for name, column in offense.items():
        if (not isinstance(column, Mapping) or set(column) != set(weights)
                or any(type(row) is not int for row in column)):
            raise ValueError(f"{name} requires exactly the physical dice rows")
        for token in column.values():
            if not isinstance(token, str) or not supported_generated_cell("offense", name, token):
                raise ValueError(f"Unsupported allocated baseline cell in {name}: {token!r}")
            match = _NUMERIC.fullmatch(token)
            if match:
                value = int(match[1])
                if not -99 <= value <= 99 or (name in _RUNS and value > 18):
                    raise ValueError(f"Invalid allocated numeric baseline in {name}: {token}")
    changed = {name: dict(column) for name, column in offense.items()}
    effects = []
    for name in (*_RUNS, *_PASSES, "breakaway"):
        multiplier = passing_multiplier if name in _PASSES else rushing_multiplier
        for row, token in offense[name].items():
            match = _NUMERIC.fullmatch(token)
            if not match:
                continue
            value = int(match[1])
            if value == 0:
                continue
            product = float(value) * float(multiplier)
            rounded = round(product)
            cap = 18 if name in _RUNS and rounded > 0 else 99
            final = max(-99, min(cap, rounded))
            if final != value:
                prefix = "+" if token.startswith("+") and final > 0 else ""
                changed[name][row] = f"{prefix}{final}{match[2]}"
            if product != rounded or final != rounded or final != value:
                effects.append({
                    "column": name, "row": row, "weight": weights[row],
                    "before": token, "after": changed[name][row], "multiplier": multiplier,
                    "unrounded": product, "rounded": rounded, "final": final,
                    "rounding_error": rounded - product, "capped": final != rounded,
                })
    before_protected = _protected_masses(offense, weights)
    after_protected = _protected_masses(changed, weights)
    if before_protected != after_protected:
        raise ValueError("Normalization changed protected mass")
    return changed, {
        "component_only": True, "rounding": _ROUNDING,
        "protected_mass_preserved": True, "protected_masses": before_protected,
        "effects": effects, "columns": {
            name: {"before": _distribution(offense[name], weights),
                   "after": _distribution(changed[name], weights)}
            for name in _COLUMNS
        },
    }

"""Probability and preservation controls for generated chart allocations."""
from __future__ import annotations

import itertools
import math
import random
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import replace
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from . import chart_generator as generator
from .chart_audit import feature
from .play_resolver import chart_roll_weights

_NUMERIC = re.compile(r"[+-]?\d+\*?")


def check_symbolic_allocation(
    before: Mapping[int, str],
    after: Mapping[int, str],
    target_rate: float,
    allocated_results: Sequence[str],
    *,
    minimum_one: bool = False,
) -> list[str]:
    """Validate one symbolic allocation against physical dice feasibility."""
    weights = chart_roll_weights()
    errors = []
    if set(before) != set(weights) or set(after) != set(weights):
        errors.append("allocation must retain all physical rows")
    if not math.isfinite(target_rate) or not 0 <= target_rate <= 1:
        return [*errors, "target probability must be finite and between zero and one"]
    accepted = set(allocated_results)
    candidates = {roll for roll, cell in before.items() if _NUMERIC.fullmatch(cell)}
    for roll, cell in before.items():
        if roll not in after:
            continue
        replacement = after[roll]
        if roll not in candidates and replacement != cell:
            errors.append(f"protected result displaced on roll {roll}: {cell} -> {replacement}")
        elif roll in candidates and replacement != cell and replacement not in accepted:
            errors.append(f"unexpected replacement on roll {roll}: {cell} -> {replacement}")

    # Independent exact subset feasibility, using physical mass rather than a
    # percentage tolerance or the generator's subset selector as its own oracle.
    attainable = {0}
    for roll in candidates:
        if roll in weights:
            attainable |= {mass + weights[roll] for mass in tuple(attainable)}
    if minimum_one and target_rate > 0 and len(attainable) > 1:
        attainable.remove(0)
    target = target_rate * sum(weights.values())
    best_error = min(abs(mass - target) for mass in attainable)
    allocated_mass = sum(
        weights.get(roll, 0)
        for roll in candidates
        if after.get(roll) in accepted and after.get(roll) != before[roll]
    )
    if abs(allocated_mass - target) > best_error + 1e-10:
        errors.append(
            f"allocation is not nearest attainable: target {target:.8g} physical units, "
            f"allocated {allocated_mass}, optimal absolute error {best_error:.8g}"
        )
    if minimum_one and target_rate > 0 and not candidates:
        errors.append("required positive event has no eligible physical row")
    return errors


def _synthetic_stats() -> generator.TeamSeasonStats:
    """Return self-contained inputs, independent of all installed season data."""
    return generator.TeamSeasonStats(
        season=2026,
        team_name="Allocation Gate Synthetic",
        short_name="AGS",
        offense=generator.UnitStats(
            rushing=generator.StatLine(attempts=500, yards=2250, touchdowns=20, fumbles=12),
            passing=generator.StatLine(
                attempts=1000, completions=650, yards=7800, touchdowns=40,
                interceptions=25, sacks=65, sack_yards=455, fumbles=10,
            ),
        ),
        defense=generator.UnitStats(
            rushing=generator.StatLine(attempts=500, yards=2050),
            passing=generator.StatLine(
                attempts=1000, completions=650, yards=7200,
                interceptions=25, sacks=65,
            ),
        ),
        special_teams=generator.SpecialTeamsStats(
            kickoff=generator.StatLine(attempts=80, yards=4960),
            kickoff_return=generator.StatLine(attempts=50, yards=1100),
            punt=generator.StatLine(attempts=70, yards=2940, blocked=1),
            punt_return=generator.StatLine(attempts=40, yards=400),
            interception_return=generator.StatLine(attempts=20, yards=240),
            field_goal=generator.StatLine(attempts=300, made=180, blocked=6),
            field_goal_by_distance=(
                generator.FieldGoalDistanceStats(distance=30, attempts=100, made=80, blocked=2),
                generator.FieldGoalDistanceStats(distance=45, attempts=100, made=60, blocked=2),
                generator.FieldGoalDistanceStats(distance=55, attempts=100, made=40, blocked=2),
            ),
        ),
    )


def audit_allocations(seeds: Sequence[int] = (8306, 9241, 11713)) -> dict[str, Any]:
    """Audit the current generator using synthetic mixed-event controls."""
    if not seeds:
        raise ValueError("Allocation audit requires at least one seed")
    errors: list[str] = []
    checks = 0
    context = ""
    original = generator._replace_rate
    original_selector = generator._nearest_roll_mass
    protected_columns: dict[int, tuple[str, dict[int, str], dict[int, str]]] = {}
    quantization: dict[str, float] = {}
    weights = chart_roll_weights()
    total_weight = sum(weights.values())
    checking_replacement = False

    def checked_selector(rate: float, candidates: Sequence[int]) -> set[int]:
        nonlocal checks
        selected = original_selector(rate, candidates)
        if checking_replacement:
            # _replace_rate may intentionally repair an empty selection for a
            # required rare event. Its final allocation is checked below.
            return selected
        before = {roll: "10" if roll in candidates else "BLACK" for roll in weights}
        after = dict(before)
        for roll in selected:
            after[roll] = "AUDIT SELECTION"
        errors.extend(
            f"{context} subset selector: {error}"
            for error in check_symbolic_allocation(
                before, after, rate, ("AUDIT SELECTION",)
            )
        )
        checks += 1
        return selected

    def checked_replace(
        column: dict[int, str], rate: float, values: str | Sequence[str],
        rng: random.Random, minimum_one: bool = False,
    ) -> None:
        nonlocal checks, checking_replacement
        before = dict(column)
        checking_replacement = True
        try:
            original(column, rate, values, rng, minimum_one=minimum_one)
        finally:
            checking_replacement = False
        symbols = (values,) if isinstance(values, str) else tuple(values)
        errors.extend(
            f"{context}: {error}" for error in check_symbolic_allocation(
                before, column, rate, symbols, minimum_one=minimum_one
            )
        )
        checks += 1
        protected = {roll: cell for roll, cell in column.items() if not _NUMERIC.fullmatch(cell)}
        protected_columns[id(column)] = (context, column, protected)
        mass = sum(
            weights[roll] for roll, cell in column.items()
            if cell in symbols and before[roll] != cell
        ) / total_weight
        label = feature(symbols[0])
        quantization[label] = max(quantization.get(label, 0.0), abs(mass - rate))

    with (
        patch.object(generator, "_replace_rate", checked_replace),
        patch.object(generator, "_nearest_roll_mass", checked_selector),
    ):
        for completion, interception, sacks, delta, seed in itertools.product(
            (.40, .65, .85), (.005, .025, .07), (20, 80, 160), (-.25, 0, .13), seeds
        ):
            context = f"pass completion={completion} interception={interception} sacks={sacks} delta={delta} seed={seed}"
            stats = generator.StatLine(
                attempts=1000, completions=round(completion * 1000), yards=12000,
                touchdowns=40, interceptions=round(interception * 1000), sacks=sacks,
            )
            # This synthetic 15-yard completion profile audits physical event
            # allocation; name its call so INT support uses the correct model.
            generator._pass_column(
                stats, delta, 15, 9, random.Random(seed), column_name="medium_pass",
            )
        for style, fumbles, touchdowns, seed in itertools.product(
            ("line", "tackle", "end", "draw"), (0, 12, 30), (0, 20, 40), seeds
        ):
            context = f"run style={style} fumbles={fumbles} touchdowns={touchdowns} seed={seed}"
            generator._run_column(4.5, 500, touchdowns, fumbles, 20, random.Random(seed), style)
        for seed in seeds:
            context = f"special seed={seed}"
            generator._generate_special(_synthetic_stats(), seed)
            for size in (73, 1000):
                context = f"empirical mixed-event size={size} seed={seed}"
                outcomes = tuple(
                    ["BLACK"] * round(size * .40)
                    + ["QT"] * round(size * .126)
                    + ["INT 5"] * round(size * .025)
                    + ["F + 2"] * round(size * .01)
                    + ["F - 1"] * round(size * .015)
                    + ["OFF 5"] * round(size * .03)
                    + ["DEF 5"] * round(size * .025)
                    + ["12*"] * round(size * .1)
                    + ["4"] * round(size * .269)
                )
                column = generator._empirical_column(outcomes, seed)
                if set(column.values()) - set(outcomes):
                    errors.append(f"{context}: empirical quantization introduces unobserved results")
                checks += 1
            context = f"empirical sparse-interception seed={seed}"
            generator._empirical_column(
                ("BLACK",) * 300 + ("QT",) * 50 + ("INT 5",) * 5 + ("4",) * 645,
                seed,
            )
            context = f"full generation missing-annotation defaults seed={seed}"
            with TemporaryDirectory(prefix="paydirt-allocation-gate-") as destination:
                generator.generate_team_charts(
                    _synthetic_stats(), destination, seed=seed,
                    missing_source_features=(
                        "offense_oob", "punt_fair_catch", "kickoff_out",
                        *generator._MISSING_SPECIAL_PROFILES,
                    ),
                )

    for label, column, protected in protected_columns.values():
        for roll, value in protected.items():
            if column[roll] != value:
                errors.append(f"{label}: post-allocation transformation displaced protected result at {roll}")
        checks += 1

    baseline_stats = _synthetic_stats()
    baseline = generator._generate_defense(baseline_stats)
    transitions: dict[str, dict[str, int]] = {}
    for name, values, allowed in (
        ("interceptions", range(81), {
            ("interception", "incomplete"), ("incomplete", "interception"),
            ("numeric", "interception"), ("override_numeric", "interception"),
        }),
        ("sacks", range(201), {("pressure", "numeric"), ("numeric", "pressure")}),
    ):
        observed: Counter[tuple[str, str]] = Counter()
        for value in values:
            passing = replace(baseline_stats.defense.passing, **{name: value})
            stats = replace(baseline_stats, defense=replace(baseline_stats.defense, passing=passing))
            chart = generator._generate_defense(stats)
            for key, cells in chart.items():
                for column, cell in cells.items():
                    pair = feature(baseline[key][column]), feature(cell)
                    if pair[0] != pair[1]:
                        observed[pair] += 1
                        if pair not in allowed:
                            errors.append(f"defense {name}={value} changes unrelated result {pair} at {key}/{column}")
            checks += 1
        transitions[name] = {f"{a}->{b}": count for (a, b), count in sorted(observed.items())}
    return {
        "passed": not errors, "errors": errors, "checks": checks,
        "diagnostics": {
            "seeds": list(seeds), "maximum_local_quantization_error": quantization,
            "defense_mechanism_transitions": transitions,
            "interpretation": "Exact finite-row allocation and symbol preservation; not a historical engine fit.",
        },
    }

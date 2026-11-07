"""Allocate and disperse primary outcomes while preserving exact token mass."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from itertools import combinations, pairwise
from typing import Any

from .play_resolver import chart_roll_weights

PRIMARY_COLUMNS = (
    "line_plunge", "off_tackle", "end_run", "draw", "screen", "short_pass",
    "medium_pass", "long_pass", "te_short_long",
)
_METRICS = ("longest_vertical_black_run", "black_2x2_blocks",
            "squared_vertical_black_runs", "horizontal_black_pairs")
_METHOD = "equal-weight-primary-outcome-dispersion-v3"


def validate_primary_layout(
    before: Mapping[str, Mapping[int, str]], after: Mapping[str, Mapping[int, str]],
) -> dict[str, Any]:
    """Check raw token counts within each physical-weight group, including flags."""
    errors = []
    weights = chart_roll_weights()
    if set(before) != set(after):
        errors.append("Layout column inventory changed")
    for name in PRIMARY_COLUMNS:
        if name not in before or name not in after:
            errors.append(f"{name}: missing primary column")
            continue
        if set(before[name]) != set(weights) or set(after[name]) != set(weights):
            errors.append(f"{name}: primary dice row inventory differs")
            continue
        for weight in sorted(set(weights.values())):
            rows = [roll for roll in weights if weights[roll] == weight]
            if Counter(before[name][roll] for roll in rows) != Counter(after[name][roll] for roll in rows):
                errors.append(f"{name}: whole-token inventory changed at physical weight {weight}")
    for name in (set(before) & set(after)) - set(PRIMARY_COLUMNS):
        if before[name] != after[name]:
            errors.append(f"{name}: nonprimary dependency changed")
    return {"passed": not errors, "errors": errors}


def _score(columns: list[list[bool]]) -> tuple[int, int, int, int]:
    longest = squared = blocks = horizontal = 0
    for column in columns:
        run = 0
        for black in (*column, False):
            if black:
                run += 1
            else:
                longest = max(longest, run)
                squared += run * run
                run = 0
    for left, right in pairwise(columns):
        horizontal += sum(a and b for a, b in zip(left, right))
        blocks += sum(left[i] and left[i + 1] and right[i] and right[i + 1]
                      for i in range(len(left) - 1))
    return longest, blocks, squared, horizontal



def chart_cell_color(raw: str) -> str:
    """Classify the viewer's display fill without interpreting game outcomes.

    Args:
        raw: Complete printed chart token, including wrappers and flags.

    Returns:
        The viewer's color name, preserving its existing classification order.
    """
    token = raw.strip().upper()
    unwrapped = token.strip("()[]")
    if token in ("BLACK", "INC"):
        return "black"
    if token.startswith(("OFF", "DEF", "PI")):
        return "yellow"
    if (token in {"SACK 0", "SACK 0*"} or token.startswith(("INT", "F"))
            or unwrapped.startswith("-") or unwrapped == "DS-" or token == "NG"):
        return "red"
    if unwrapped in ("TD", "B", "B*", "GOOD") or unwrapped.startswith("DS"):
        return "green"
    try:
        yards = float(unwrapped.rstrip("*†"))
    except ValueError:
        return "neutral"
    return "green" if yards > 0 else "red" if yards < 0 else "neutral"


def _outcome_features(raw: str) -> frozenset[str]:
    """Describe whole tokens without interpreting or rewriting their semantics."""
    token = raw.strip().upper()
    value = token.strip("()[]").rstrip("*†")
    labels = {"exact:" + token, "color:" + chart_cell_color(raw)}
    family = value
    for prefix in ("OFF", "DEF", "PI", "SACK", "INT", "BK", "QT", "DS", "F"):
        if value.startswith(prefix):
            family = prefix
            break
    if family in {"OFF", "DEF", "PI"}:
        labels.add("group:penalty")
    if family in {"F", "INT", "BK"}:
        labels.add("group:turnover_risk")
    if "*" in token or "†" in token or value == "OB":
        labels.add("flag:sideline")
    for marker, name in (("(", "parenthesized"), ("[", "bracketed")):
        if token.startswith(marker):
            labels.add("flag:" + name)
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        number = float(value)
        family = "positive" if number > 0 else "negative" if number < 0 else "zero"
        band = ("loss10plus" if number <= -10 else "loss1to9" if number < 0 else
                "zero" if number == 0 else "gain1to4" if number < 5 else
                "gain5to9" if number < 10 else "gain10to19" if number < 20 else "gain20plus")
        labels.add("band:" + band)
    labels.add("family:" + family)
    return frozenset(labels)


def _vertical_cost(mask: int) -> int:
    # Sum n*(n-1) over runs: a constant-free squared-run measure.
    total = 0
    shifted = mask >> 1
    while shifted:
        mask &= shifted
        total += 2 * mask.bit_count()
        shifted = mask >> 1
    return total


def _neighbor_cost(left: int, right: int) -> int:
    common = left & right
    return common.bit_count() + (common & (common >> 1)).bit_count()


def _feature_masks(
    result: Mapping[str, Mapping[int, str]], rows: list[int],
) -> tuple[dict[str, frozenset[str]], list[dict[str, int]], dict[str, int]]:
    """Describe one grid with fixed initial frequency normalization."""
    features = {token: _outcome_features(token)
                for name in PRIMARY_COLUMNS for token in result[name].values()}
    masks = []
    for name in PRIMARY_COLUMNS:
        column: dict[str, int] = defaultdict(int)
        for index, row in enumerate(rows):
            for label in features[result[name][row]]:
                column[label] |= 1 << index
        masks.append(dict(column))
    population = Counter({label: sum(column.get(label, 0).bit_count() for column in masks)
                          for label in {label for column in masks for label in column}})
    coefficients = {label: max(1, 2700 // count) for label, count in population.items()}
    return features, masks, coefficients


def _feature_cost(masks: list[dict[str, int]], coefficients: dict[str, int]) -> int:
    return sum(coefficient * (
        sum(_vertical_cost(column.get(label, 0)) for column in masks)
        + sum((left.get(label, 0) & right.get(label, 0)).bit_count()
              for left, right in combinations(masks, 2))
        + sum(_neighbor_cost(left.get(label, 0), right.get(label, 0))
              - (left.get(label, 0) & right.get(label, 0)).bit_count()
              for left, right in pairwise(masks))) for label, coefficient in coefficients.items())


def _local_feature_cost(
    masks: list[dict[str, int]], coefficients: dict[str, int],
    column: int, label: str, mask: int,
) -> int:
    return coefficients[label] * (
        _vertical_cost(mask)
        + sum((other.get(label, 0) & mask).bit_count()
              for index, other in enumerate(masks) if index != column)
        + sum(_neighbor_cost(masks[index].get(label, 0), mask)
              - (masks[index].get(label, 0) & mask).bit_count()
              for index in (column - 1, column + 1) if 0 <= index < len(masks)))


def validate_primary_allocation(
    before: Mapping[str, Mapping[int, str]], after: Mapping[str, Mapping[int, str]],
) -> dict[str, Any]:
    """Require exact full-token mass, fixed BLACK positions and fixed dependencies.

    Args:
        before: Original primary columns and any protected dependent columns.
        after: Candidate allocation with the same complete column inventory.

    Returns:
        A pass flag and descriptive errors for any violated invariant.
    """
    errors = []
    weights = chart_roll_weights()
    if set(before) != set(after):
        errors.append("Allocation column inventory changed")
    for name in PRIMARY_COLUMNS:
        if name not in before or name not in after:
            errors.append(f"{name}: missing primary column")
            continue
        if set(before[name]) != set(weights) or set(after[name]) != set(weights):
            errors.append(f"{name}: primary dice row inventory differs")
            continue
        inventories = []
        for column in (before[name], after[name]):
            mass: Counter[str] = Counter()
            for row, token in column.items():
                mass[token] += weights[row]
            inventories.append(mass)
        if inventories[0] != inventories[1]:
            errors.append(f"{name}: full-token physical mass changed")
        if any((before[name][row].strip().upper() == "BLACK")
               != (after[name][row].strip().upper() == "BLACK") for row in weights):
            errors.append(f"{name}: protected BLACK position changed")
    for name in (set(before) & set(after)) - set(PRIMARY_COLUMNS):
        if before[name] != after[name]:
            errors.append(f"{name}: nonprimary dependency changed")
    return {"passed": not errors, "errors": errors}


def rebalance_primary_allocation(
    offense: Mapping[str, Mapping[int, str]],
) -> tuple[dict[str, dict[int, str]], dict[str, Any]]:
    """Improve the feasible primary mask through bounded exact-mass exchanges.

    Exchange up to three rows of one complete token against up to three rows of
    another token, only when their physical masses are identical. Unlike layout
    swaps, this may change printed counts and per-weight inventories. Calibrated
    token/flag probabilities and the BLACK map stay exact. Protected tables never
    enter the search. The original quantizer remains the probability authority.

    Args:
        offense: Complete primary columns and any fixed supplemental columns.

    Returns:
        A copied offense map and exchange, objective and invariant evidence.
    """
    initial = validate_primary_allocation(offense, offense)
    if not initial["passed"]:
        raise ValueError("Invalid primary allocation: " + "; ".join(initial["errors"]))
    result = {name: dict(column) for name, column in offense.items()}
    weights = chart_roll_weights()
    rows = sorted(weights)
    positions = {row: index for index, row in enumerate(rows)}
    features, masks, coefficients = _feature_masks(result, rows)
    initial_cost = cost = _feature_cost(masks, coefficients)
    exchanges = []
    while True:
        best_delta, best = 0, None
        for ci, name in enumerate(PRIMARY_COLUMNS):
            token_rows: dict[str, list[int]] = defaultdict(list)
            for row in rows:
                token = result[name][row]
                if token.strip().upper() != "BLACK":
                    token_rows[token].append(row)
            subsets: dict[str, dict[int, list[tuple[int, ...]]]] = {}
            for token, candidates in sorted(token_rows.items()):
                by_mass: dict[int, list[tuple[int, ...]]] = defaultdict(list)
                for count in range(1, min(3, len(candidates)) + 1):
                    for selected in combinations(candidates, count):
                        by_mass[sum(weights[row] for row in selected)].append(selected)
                subsets[token] = by_mass
            for a, b in combinations(sorted(subsets), 2):
                labels = features[a] ^ features[b]
                for mass in sorted(subsets[a].keys() & subsets[b].keys()):
                    for left in subsets[a][mass]:
                        for right in subsets[b][mass]:
                            flip = sum(1 << positions[row] for row in (*left, *right))
                            delta = sum(
                                _local_feature_cost(masks, coefficients, ci, label,
                                                    masks[ci].get(label, 0) ^ flip)
                                - _local_feature_cost(masks, coefficients, ci, label,
                                                      masks[ci].get(label, 0))
                                for label in labels)
                            if delta < best_delta:
                                best_delta, best = delta, (ci, name, a, b, left, right, mass, labels, flip)
        if best is None:
            break
        ci, name, a, b, left, right, mass, labels, flip = best
        for row in left:
            result[name][row] = b
        for row in right:
            result[name][row] = a
        for label in labels:
            masks[ci][label] = masks[ci].get(label, 0) ^ flip
        cost += best_delta
        exchanges.append({"column": name, "tokens": [a, b], "rows": [list(left), list(right)],
                          "physical_mass_each": mass, "cost_delta": best_delta})
    invariants = validate_primary_allocation(offense, result)
    if not invariants["passed"]:
        raise RuntimeError("Primary allocation invariant failed: " + "; ".join(invariants["errors"]))
    return result, {
        "method": "exact-token-mass-primary-exchanges-v1",
        "before_cost": initial_cost, "after_cost": cost,
        "accepted_exchanges": len(exchanges), "exchanges": exchanges,
        "features": sorted(coefficients), "initial_feature_coefficients": coefficients,
        "invariants_passed": True, "black_positions_fixed": True,
        "maximum_rows_per_side": 3,
        "cost_basis": "Original-grid frequency-normalized squared runs, all-call aligned rows and adjacent 2x2 blocks",
        "scope": "Primary exact full-token physical mass; BLACK and all dependent tables fixed; bounded local search",
    }


def _disperse_outcomes(
    result: dict[str, dict[int, str]], rows: list[int], pairs: list[tuple[int, int]],
) -> dict[str, Any]:
    """Improve all features together while freezing the first-stage BLACK map.

    Feature frequencies are normalized across the nine-column grid. A changed
    input column can therefore relocate another column's tokens; allocation and
    each complete token's physical mass remain protected by the invariant.
    """
    features, masks, coefficients = _feature_masks(result, rows)

    def local(column: int, label: str, mask: int) -> int:
        return _local_feature_cost(masks, coefficients, column, label, mask)

    cost = _feature_cost(masks, coefficients)
    initial_cost = cost
    positions = {row: index for index, row in enumerate(rows)}
    accepted = 0
    while True:
        best_delta, best = 0, None
        for ci, name in enumerate(PRIMARY_COLUMNS):
            for first, second in pairs:
                a, b = result[name][first], result[name][second]
                if a == b or any(token.strip().upper() == "BLACK" for token in (a, b)):
                    continue
                labels = features[a] ^ features[b]
                flip = (1 << positions[first]) | (1 << positions[second])
                delta = sum(local(ci, label, masks[ci].get(label, 0) ^ flip)
                            - local(ci, label, masks[ci].get(label, 0)) for label in labels)
                if delta < best_delta:
                    best_delta, best = delta, (ci, name, first, second, labels, flip)
        if best is None:
            break
        ci, name, first, second, labels, flip = best
        result[name][first], result[name][second] = result[name][second], result[name][first]
        for label in labels:
            masks[ci][label] = masks[ci].get(label, 0) ^ flip
        cost += best_delta
        accepted += 1
    return {"before_cost": initial_cost, "after_cost": cost, "accepted_swaps": accepted,
            "features": sorted(coefficients), "black_positions_fixed": True,
            "cost_basis": "Frequency-normalized squared runs, all-call aligned rows and adjacent 2x2 blocks; after BLACK stage",
            "scope": "Primary only; defense, supplemental, recovery and special tables protected"}

def disperse_primary_layout(
    offense: Mapping[str, Mapping[int, str]],
) -> tuple[dict[str, dict[int, str]], dict[str, Any]]:
    """Reach a deterministic local dispersion optimum without changing allocation.

    Args:
        offense: Complete primary columns and any fixed supplemental columns.

    Returns:
        A copied offense map and before/after metrics with invariant evidence.
    """
    initial = validate_primary_layout(offense, offense)
    if not initial["passed"]:
        raise ValueError("Invalid primary layout: " + "; ".join(initial["errors"]))
    result = {name: dict(column) for name, column in offense.items()}
    weights = chart_roll_weights()
    rows = sorted(weights)
    positions = {roll: index for index, roll in enumerate(rows)}
    groups: dict[int, list[int]] = defaultdict(list)
    for roll in rows:
        groups[weights[roll]].append(roll)
    pairs = [(a, b) for weight in sorted(groups) for a, b in combinations(groups[weight], 2)]
    pairs.sort()
    black = [[result[name][roll].strip().upper() == "BLACK" for roll in rows]
             for name in PRIMARY_COLUMNS]
    original_score = current_score = _score(black)
    accepted = 0
    while True:
        best_score, best = current_score, None
        for column, name in enumerate(PRIMARY_COLUMNS):
            flags = black[column]
            for first, second in pairs:
                a, b = positions[first], positions[second]
                if flags[a] == flags[b]:
                    continue
                flags[a], flags[b] = flags[b], flags[a]
                score = _score(black)
                flags[a], flags[b] = flags[b], flags[a]
                if score < best_score:
                    best_score, best = score, (column, name, first, second)
        if best is None:
            break
        column, name, first, second = best
        result[name][first], result[name][second] = result[name][second], result[name][first]
        a, b = positions[first], positions[second]
        black[column][a], black[column][b] = black[column][b], black[column][a]
        current_score = best_score
        accepted += 1
    outcome_placement = _disperse_outcomes(result, rows, pairs)
    invariants = validate_primary_layout(offense, result)
    if not invariants["passed"]:
        raise RuntimeError("Primary layout invariant failed: " + "; ".join(invariants["errors"]))
    return result, {
        "method": _METHOD, "before": dict(zip(_METRICS, original_score)),
        "after": dict(zip(_METRICS, current_score)), "accepted_swaps": accepted + outcome_placement["accepted_swaps"],
        "black_accepted_swaps": accepted, "outcome_placement": outcome_placement,
        "invariants_passed": True,
        "scope": "Nine primary columns; whole tokens within equal physical-weight groups; supplements fixed",
    }

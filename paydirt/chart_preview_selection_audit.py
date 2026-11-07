"""Derive a compact review set from fixed fit bounds and frozen source efficiencies."""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from .chart_engine_audit import TEAM_TOLERANCES

_SOURCE_METRICS = ("yards_per_pass_attempt", "rushing_yards_per_attempt")


def _number(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Preview selection requires finite numeric metrics, not booleans")
    return float(value)


def preview_selection_roles(contract: Mapping[str, Any], reports: Mapping[str, Any]) -> dict[str, Any]:
    """Choose source offense extremes and the worst normalized reference-policy error.

    Efficiency ranks describe the review sample, not overall team quality. Exact
    ties use folder, phase (training first), then metric name.
    """
    teams = contract["teams"]
    if not isinstance(teams, dict) or len(teams) < 2 or set(reports) != {"training", "held_out"}:
        raise ValueError("Preview selection requires complete team targets and both reference families")
    if not all(isinstance(name, str) and name for name in teams):
        raise ValueError("Preview selection requires named source teams")
    targets = {team: {metric: _number(values["rates"][metric]) for metric in TEAM_TOLERANCES}
               for team, values in teams.items()}
    errors = []
    for phase_index, phase in enumerate(("training", "held_out")):
        report = reports[phase]
        names = report["metadata"]["team_names"]
        if (not isinstance(names, dict) or set(names) != set(teams)
                or not all(isinstance(value, str) and value for value in names.values())
                or len(set(names.values())) != len(names) or set(report["teams"]) != set(names.values())):
            raise ValueError("Preview campaign team identities differ from the frozen source cohort")
        for team, engine_name in names.items():
            for metric, tolerance in TEAM_TOLERANCES.items():
                observed = _number(report["teams"][engine_name][metric])
                target = targets[team][metric]
                difference = _number(abs(observed - target))
                normalized = _number(difference / tolerance)
                errors.append({"team": team, "phase": phase, "metric": metric,
                               "observed": observed, "target": target, "absolute_error": difference,
                               "tolerance": tolerance, "normalized_error": normalized,
                               "phase_index": phase_index})
    worst = min(errors, key=lambda item: (-item["normalized_error"], item["team"],
                                         item["phase_index"], item["metric"]))
    worst = {key: value for key, value in worst.items() if key != "phase_index"}
    source = {}
    for team in sorted(teams):
        ranks = {}
        for metric in _SOURCE_METRICS:
            value = targets[team][metric]
            lower = sum(targets[other][metric] < value for other in teams)
            tied = sum(targets[other][metric] == value for other in teams)
            ranks[metric] = 1 + lower + (tied - 1) / 2
        source[team] = {"team": team, "source_rates": {metric: targets[team][metric] for metric in _SOURCE_METRICS},
                        "source_ranks": ranks, "rank_sum": sum(ranks.values())}
    strong = min(source.values(), key=lambda item: (-item["rank_sum"], item["team"]))
    weak = min(source.values(), key=lambda item: (item["rank_sum"], item["team"]))
    if strong["rank_sum"] == weak["rank_sum"]:
        raise ValueError("Source efficiency ranks cannot distinguish strong/weak preview representatives")
    return {"worst_outlier": worst, "strong_source_offense": strong, "weak_source_offense": weak}

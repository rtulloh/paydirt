"""Paired full-engine reference report diagnostics; no source-accuracy authority."""
from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from .chart_engine_audit import REQUIRED_METRICS, validate_engine_report
from .chart_loader import load_team_chart
from .play_resolver import CHART_PLAY_TYPES
from .season_rules import load_season_rules

MASTER = 20461108
SEED_DERIVATION = "master + repetition_index * 1000003 + game_index * 1009"
METRICS = (*REQUIRED_METRICS, "points_per_team_game", "plays_per_team_game",
           "fumble_loss_rate_per_play", "field_goal_rate")
_ERRORS = (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError, OverflowError)


def _folder(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value not in {".", ".."} and Path(value).name == value and "\\" not in value


def _contracts(contract: dict, mapping: Mapping[str, str]) -> tuple[dict, dict]:
    schedule = [(row["away"], row["home"]) if isinstance(row, dict) else tuple(row) for row in contract["schedule"]]
    if (not isinstance(mapping, Mapping) or len(mapping) < 2
            or any(not _folder(value) for pair in mapping.items() for value in pair)
            or len(set(mapping.values())) != len(mapping) or set(contract["teams"]) != set(mapping)
            or not schedule or any(len(pair) != 2 or pair[0] == pair[1] for pair in schedule)
            or {name for pair in schedule for name in pair} != set(mapping)):
        raise ValueError("Requires a complete source schedule, team targets and folder bijection")
    generated = deepcopy(contract)
    generated["schedule"] = schedule
    original = deepcopy(generated)
    original["schedule"] = [(mapping[away], mapping[home]) for away, home in schedule]
    original["teams"] = {mapping[name]: target for name, target in generated["teams"].items()}
    return generated, original


def _summary(differences: list[float]) -> dict[str, int | float | None]:
    return {"replications": len(differences), "mean_repetition_delta": statistics.mean(differences),
            "between_repetition_standard_error": (statistics.stdev(differences) / math.sqrt(len(differences))
                                                   if len(differences) > 1 else None),
            "minimum": min(differences), "maximum": max(differences)}


def _diagnostics(report: dict, folders: dict[str, str]) -> dict[str, Any]:
    def mapped(row: dict) -> dict:
        return {**row, "situation": [folders[row["situation"][0]], *row["situation"][1:]]}
    result = {field: [mapped(row) for row in report[field]]
              for field in ("call_mix", "outcome_distributions", "comparable_situations")}
    tails = {name: dict.fromkeys(("retained_primary_calls", "losses", "zero_gains", "explosive_20", "explosive_40"), 0)
             for name in folders.values()}
    primary = {play.name for play in CHART_PLAY_TYPES}
    for game in report["game_receipts"]:
        for call in game["decision_results"]:
            team, play, *_ = call["situation"]
            if call["retained"] and play in primary:
                counts = tails[folders[team]]
                counts["retained_primary_calls"] += 1
                for label, value in (("losses", call["yards"] < 0), ("zero_gains", call["yards"] == 0),
                                     ("explosive_20", call["yards"] >= 20), ("explosive_40", call["yards"] >= 40)):
                    counts[label] += int(value)
    result["primary_tails"] = tails
    return result


def compare_campaigns(
    generated: dict[str, Any], original: dict[str, Any], contract: dict[str, Any],
    generated_dir: Path, reference_dir: Path, mapping: Mapping[str, str], *, master: int = MASTER,
) -> dict[str, Any]:
    """Validate raw campaigns and compute paired schedule-repetition diagnostics.

    Args:
        generated: Full raw generated-cohort engine report.
        original: Full raw reference-cohort engine report.
        contract: Unchanged generated-folder source schedule and target contract.
        generated_dir: Actual generated chart directory.
        reference_dir: Actual reference chart directory.
        mapping: Complete generated-folder to reference-folder bijection.
        master: Initial game-seed family; training diagnostics may name their own.

    Returns:
        Both accounting/source-fit verdicts, paired estimates and explicit exposure.
    """
    errors: list[str] = []
    result: dict[str, Any] = {
        "passed": False, "errors": errors, "sets": {}, "teams": {}, "league": {}, "paired": {},
        "game_pairs": [], "rankings": {}, "coverage": {}, "paired_validated": False, "exposure_complete": False,
        "benchmark_complete": False, "source_accepted": False, "ready_for_owner_review": False, "release_certified": False,
        "interpretation": "Same initial seeds pair mapped games; later dice/calls may diverge. "
                          "Aggregate deltas differ from means of repetition deltas. Uncertainty uses paired source-schedule "
                          "repetitions, not independent plays. Primary tails condition on retained primary selections. "
                          "Strength and formation summaries depend on policy; source fit and material outliers require review.",
    }
    try:
        if type(master) is not int or master < 0:
            raise ValueError("Paired master must be a nonnegative integer")
        generated_contract, original_contract = _contracts(contract, mapping)
        if load_season_rules(Path(generated_dir)) != load_season_rules(Path(reference_dir)):
            raise ValueError("Paired cohorts must use identical source-year rules")
    except _ERRORS as error:
        errors.append(str(error))
        return result
    for label, report, source, directory in (
        ("generated", generated, generated_contract, Path(generated_dir)),
        ("reference", original, original_contract, Path(reference_dir)),
    ):
        reasons: list[str] = []
        details: dict[str, Any] = {"mechanics": {"passed": False, "errors": reasons}}
        result["sets"][label] = details
        try:
            metadata = report["metadata"]
            if (type(metadata.get("seed")) is not int or metadata["seed"] != master
                    or type(metadata.get("repetitions")) is not int or metadata["repetitions"] < 1
                    or metadata.get("policy") != "chart-focused" or metadata.get("seed_derivation") != SEED_DERIVATION):
                reasons.append("Paired protocol requires equal declared master, positive repetitions and fixed chart-focused policy")
            names = {folder: load_team_chart(directory / folder).peripheral.short_name for folder in source["teams"]}
            if metadata.get("team_names") != names:
                reasons.append("Paired report team identifiers differ from actual mapped charts")
            checked = validate_engine_report(report, source, directory, minimum_team_games=1,
                                             minimum_repetitions=1, require_fit=False)
            if checked["passed"] is not True or checked["errors"]:
                reasons.extend(checked["errors"] or ["Failed full-engine evidence"])
            details["mechanics"]["passed"] = not reasons
            if not reasons:
                details["source_fit"] = validate_engine_report(report, source, directory, minimum_team_games=1,
                                                              minimum_repetitions=1, require_fit=True)
        except _ERRORS as error:
            reasons.append(str(error))
        errors.extend(f"{label}: {reason}" for reason in reasons)
    if errors:
        return result
    try:
        repetitions = generated["metadata"]["repetitions"]
        if repetitions != original["metadata"]["repetitions"]:
            raise ValueError("Paired reports must have equal independent repetition counts")
        names = sorted(mapping)
        reports = {"generated": generated, "reference": original}
        report_names = {label: report["metadata"]["team_names"] for label, report in reports.items()}

        def values(label: str, name: str, replication: int | None = None) -> dict:
            report = reports[label] if replication is None else reports[label]["replications"][replication]
            if name == "league":
                return report["league"]
            folder = mapping[name] if label == "reference" else name
            return report["teams"][report_names[label][folder]]

        for name in ("league", *names):
            contrasts = {metric: {"generated": values("generated", name)[metric],
                                  "reference": values("reference", name)[metric],
                                  "delta": values("generated", name)[metric] - values("reference", name)[metric]}
                         for metric in METRICS}
            if name == "league":
                result["league"] = contrasts
            else:
                result["teams"][name] = {"reference_folder": mapping[name], "metrics": contrasts}
            result["paired"][name] = {metric: _summary([
                values("generated", name, index)[metric] - values("reference", name, index)[metric]
                for index in range(repetitions)]) for metric in METRICS}
        for label, report in reports.items():
            folders = {short_name: (folder if label == "generated" else next(name for name in names if mapping[name] == folder))
                       for folder, short_name in report_names[label].items()}
            result["sets"][label]["diagnostics"] = _diagnostics(report, folders)
            result["rankings"][label] = {
                metric: sorted(names, key=lambda name, metric=metric, label=label: (-values(label, name)[metric], name))
                for metric in ("points_per_team_game", "yards_per_pass_attempt", "rushing_yards_per_attempt")}
        for index, (candidate, baseline) in enumerate(zip(generated["game_receipts"], original["game_receipts"], strict=True)):
            result["game_pairs"].append({
                "repetition": index // len(generated_contract["schedule"]), "game_index": index % len(generated_contract["schedule"]),
                "seed": candidate["seed"], "away": candidate["away"], "home": candidate["home"],
                "reference_away": baseline["away"], "reference_home": baseline["home"],
                "score_delta": {side: candidate[side + "_score"] - baseline[side + "_score"] for side in ("away", "home")},
            })
        team_games = {name: values("generated", name)["team_games"] for name in names}
        result["coverage"] = {"repetitions": repetitions, "games_per_set": generated["league"]["games"],
                              "paired_games": len(result["game_pairs"]), "team_games": team_games}
        result["metadata"] = {"master": master, "seed_derivation": SEED_DERIVATION, "policy": "chart-focused",
                              "schedule_hash": generated["metadata"]["schedule_hash"],
                              "paired_unit": "source-schedule repetition"}
        result["exposure_complete"] = master == MASTER and repetitions >= 64 and min(team_games.values()) >= 1000
        result["passed"] = result["paired_validated"] = True
    except _ERRORS as error:
        errors.append(str(error))
    return result


def validate_paired_summary(report: dict[str, Any], contract: dict[str, Any], mapping: Mapping[str, str]) -> None:
    """Require complete main comparison exposure and mapped game-pair receipts."""
    from collections import Counter

    from .chart_engine_audit import _schedule_hash

    if (not isinstance(report, dict) or report.get("passed") is not True or report.get("errors") != []
            or report.get("paired_validated") is not True or report.get("exposure_complete") is not True
            or any(report.get(flag) is not False for flag in (
                "benchmark_complete", "source_accepted", "ready_for_owner_review", "release_certified"))):
        raise ValueError("Failed or malformed paired comparison")
    source, _ = _contracts(contract, mapping)
    schedule = source["schedule"]
    repetitions = report["coverage"]["repetitions"]
    if type(repetitions) is not int or repetitions < 64:
        raise ValueError("Paired comparison requires at least 64 complete source schedules")
    appearances = Counter(team for pair in schedule for team in pair)
    team_games = {name: count * repetitions for name, count in appearances.items()}
    expected = {"repetitions": repetitions, "games_per_set": len(schedule) * repetitions,
                "paired_games": len(schedule) * repetitions, "team_games": team_games}
    if (report["coverage"] != expected or min(team_games.values()) < 1000
            or any(type(value) is not int for value in report["coverage"]["team_games"].values())
            or any(type(report["coverage"][key]) is not int for key in ("games_per_set", "paired_games"))
            or report["metadata"] != {"master": MASTER, "seed_derivation": SEED_DERIVATION, "policy": "chart-focused",
                                      "schedule_hash": _schedule_hash(schedule), "paired_unit": "source-schedule repetition"}
            or set(report["teams"]) != set(mapping) or set(report["sets"]) != {"generated", "reference"}):
        raise ValueError("Paired comparison protocol, team census or exposure does not reconcile")
    for name, details in report["teams"].items():
        if details["reference_folder"] != mapping[name] or set(details["metrics"]) != set(METRICS):
            raise ValueError("Paired mapped team metrics are incomplete")
    for details in report["sets"].values():
        if (details["mechanics"]["passed"] is not True or details["mechanics"]["errors"] != []
                or type(details["source_fit"]["passed"]) is not bool or not isinstance(details["source_fit"]["errors"], list)):
            raise ValueError("Paired raw-engine/source-fit verdicts are incomplete")
    if set(report["paired"]) != {"league", *mapping} or set(report["league"]) != set(METRICS):
        raise ValueError("Paired estimates omit league/team metrics")
    for metrics in report["paired"].values():
        if set(metrics) != set(METRICS):
            raise ValueError("Missing paired metric estimates")
        for summary in metrics.values():
            if (type(summary["replications"]) is not int or summary["replications"] != repetitions
                    or any(isinstance(summary[key], bool) or not isinstance(summary[key], (int, float))
                           or not math.isfinite(summary[key]) for key in (
                               "mean_repetition_delta", "between_repetition_standard_error", "minimum", "maximum"))
                    or summary["between_repetition_standard_error"] < 0
                    or not summary["minimum"] <= summary["mean_repetition_delta"] <= summary["maximum"]):
                raise ValueError("Invalid paired repetition uncertainty")
    if set(report["rankings"]) != {"generated", "reference"} or any(
        len(names) != len(mapping) or set(names) != set(mapping)
        for rankings in report["rankings"].values() for names in rankings.values()
    ):
        raise ValueError("Incomplete paired strength rankings")
    if len(report["game_pairs"]) != expected["paired_games"]:
        raise ValueError("Incomplete paired game census")
    for index, pair in enumerate(report["game_pairs"]):
        away, home = schedule[index % len(schedule)]
        expected_pair = {"repetition": index // len(schedule), "game_index": index % len(schedule),
                         "seed": MASTER + (index // len(schedule)) * 1000003 + (index % len(schedule)) * 1009,
                         "away": away, "home": home, "reference_away": mapping[away], "reference_home": mapping[home]}
        if (any(pair[key] != value or (isinstance(value, int) and type(pair[key]) is not int)
                for key, value in expected_pair.items()) or set(pair["score_delta"]) != {"home", "away"}
                or any(type(value) is not int for value in pair["score_delta"].values())):
            raise ValueError(f"Invalid mapped paired game receipt: {index}")

"""Bounded matched engine contexts for local reference diagnostics."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import random
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import asdict
from fractions import Fraction
from typing import Any

from .auto_game import _resolve_auto_penalties
from .chart_calibration import EngineCalibrationObserver
from .chart_loader import TeamChart
from .computer_ai import ComputerAI
from .game_engine import PaydirtGameEngine, PlayOutcome
from .play_resolver import CHART_PLAY_TYPES, DefenseType, PlayType, ResultType

CONTEXTS = {
    "own1-first": (1, 1, 10), "own40-first": (40, 1, 10), "opp2-first": (98, 1, 2),
    "own1-fourth": (1, 4, 1), "own40-fourth": (40, 4, 1), "opp2-fourth": (98, 4, 1),
}
MASTER = 20261108
MAX_CALLS = 4
SEED_DOMAIN = "paydirt-reference-context-v1"
_OFFICIAL = ("offensive_plays", "pass_attempts", "rushing_attempts", "completions")
_COUNTS = ("turnover_on_downs", "losses", "zero_gains", "explosive_20", "explosive_40",
           "breakaways", "qt", "retained_fumbles", "lost_fumbles", "pending_penalties")
_METRICS = ("net_offensive_yards", "home_points", "away_points", "first_downs",
            "turnovers", "turnover_on_downs", "official_plays")


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


class _PenaltyAI(ComputerAI):
    def __init__(self) -> None:
        super().__init__(aggression=0.5, use_analysis=False)
        self.decisions = 0

    def should_accept_penalty(
        self, outcome: PlayOutcome, is_human_offense: bool = True, human_is_home: bool = False,
    ) -> tuple[bool, int | None]:
        self.decisions += 1
        return super().should_accept_penalty(outcome, is_human_offense=is_human_offense, human_is_home=human_is_home)


def run_context_trial(
    offense: TeamChart, defense: TeamChart, context: str, play: PlayType, formation: DefenseType, seed: int,
) -> dict[str, Any]:
    """Execute one bounded repeated-call sequence through the core engine.

    Args:
        offense: Home offensive chart, including its unmodified yardage factors.
        defense: Away defending chart and its recovery/return mechanisms.
        context: One of the six fixed field-position/down setups.
        play: A primary scrimmage call repeated through the trial.
        formation: The fixed defensive formation.
        seed: Independent initial RNG seed, shared across crossed combinations.

    Returns:
        Final engine state, official statistics and bounded sequence observations.
    """
    if (not isinstance(offense, TeamChart) or not isinstance(defense, TeamChart)
            or not isinstance(context, str) or context not in CONTEXTS
            or not isinstance(play, PlayType) or play not in CHART_PLAY_TYPES
            or not isinstance(formation, DefenseType) or type(seed) is not int or seed < 0):
        raise ValueError("Requires complete charts, a fixed context, primary call, formation and nonnegative integer seed")
    rng = random.getstate()
    try:
        random.seed(seed)
        game = PaydirtGameEngine(offense, defense)
        state = game.state
        state.is_home_possession = True
        state.ball_position, state.down, state.yards_to_go = CONTEXTS[context]
        observer = EngineCalibrationObserver()
        home_ai, away_ai = _PenaltyAI(), _PenaltyAI()
        counts = dict.fromkeys(_COUNTS, 0)
        results: Counter[str] = Counter()
        termination = "call_limit"
        selected = 0
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(MAX_CALLS):
                observer.on_decision(game, None, play, formation)
                outcome = game.run_play_with_penalty_procedure(play, formation)
                outcome = _resolve_auto_penalties(game, outcome, True, home_ai, away_ai)
                if outcome.pending_penalty_decision:
                    raise ValueError("Context trial left a pending penalty")
                observer.on_result(game, outcome)
                selected += 1
                result = outcome.result
                results[result.result_type.value] += 1
                counts["turnover_on_downs"] += int(outcome.turnover_on_downs)
                counts["losses"] += int(outcome.yards_gained < 0)
                counts["zero_gains"] += int(outcome.yards_gained == 0)
                counts["explosive_20"] += int(outcome.yards_gained >= 20)
                counts["explosive_40"] += int(outcome.yards_gained >= 40)
                counts["breakaways"] += int(result.breakaway_dice > 0)
                counts["qt"] += int(result.qb_scramble_dice > 0)
                counts["retained_fumbles"] += int(result.retained_fumble_incompletion
                                                  or result.result_type == ResultType.FUMBLE and result.fumble_recovered)
                if state.home_score or state.away_score:
                    termination = "score"
                    break
                if not state.is_home_possession:
                    termination = "possession_change"
                    break
                if state.game_over:
                    termination = "game_over"
                    break
        counts["lost_fumbles"] = state.home_stats.fumbles_lost
        totals = observer.team_totals(offense.peripheral.short_name)
        receipt = {
            "seed": seed, "context": context, "play": play.value, "formation": formation.value,
            "selected_calls": selected, "official": {name: getattr(totals, name) for name in _OFFICIAL},
            "home_stats": asdict(state.home_stats), "away_stats": asdict(state.away_stats),
            "score": {"home": state.home_score, "away": state.away_score},
            "scoring": [{"is_home_team": score.is_home_team, "points": score.points} for score in state.scoring_plays],
            "counts": counts, "result_counts": dict(sorted(results.items())),
            "penalty_decisions": home_ai.decisions + away_ai.decisions, "termination": termination,
            "final": {name: getattr(state, name) for name in ("ball_position", "down", "yards_to_go",
                      "is_home_possession", "quarter", "time_remaining", "game_over")},
        }
        validate_context_trial(receipt)
        return receipt
    finally:
        random.setstate(rng)


def _integer(value: object, minimum: int | None = 0) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError("Context evidence needs valid integer counts")
    return value


def validate_context_trial(receipt: dict[str, Any]) -> None:
    """Reject malformed or unreconciled trial evidence before aggregation."""
    if not isinstance(receipt, dict):
        raise TypeError("Missing context trial receipt")
    selected = _integer(receipt["selected_calls"], 1)
    if selected > MAX_CALLS:
        raise ValueError("Context trial exceeds its fixed call limit")
    home = _validate_accounting(receipt, selected)
    counts = receipt["counts"]
    if not isinstance(counts, dict) or set(counts) != set(_COUNTS):
        raise ValueError("Incomplete context branch counts")
    for value in counts.values():
        _integer(value)
    if counts["pending_penalties"] or counts["lost_fumbles"] != home["fumbles_lost"]:
        raise ValueError("Context pending/fumble counts do not reconcile")
    if not isinstance(receipt["result_counts"], dict) or sum(_integer(value) for value in receipt["result_counts"].values()) != selected:
        raise ValueError("Context result counts do not reconcile")
    _integer(receipt["penalty_decisions"])
    if receipt["termination"] not in {"call_limit", "score", "possession_change", "game_over"}:
        raise ValueError("Invalid context termination")
    for side in ("home", "away"):
        score = _integer(receipt["score"][side])
        if score != sum(_integer(item["points"]) for item in receipt["scoring"] if item["is_home_team"] is (side == "home")):
            raise ValueError("Context scoring log does not reconcile")
    final = receipt["final"]
    if (not 0 <= _integer(final["ball_position"]) <= 100 or not 1 <= _integer(final["down"]) <= 4
            or not 1 <= _integer(final["quarter"]) <= 4 or _integer(final["yards_to_go"]) > 100
            or type(final["is_home_possession"]) is not bool or type(final["game_over"]) is not bool
            or isinstance(final["time_remaining"], bool) or not isinstance(final["time_remaining"], (int, float))
            or not math.isfinite(final["time_remaining"]) or not 0 <= final["time_remaining"] <= 15):
        raise ValueError("Context final engine state is invalid")
    json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _bucket() -> dict[str, Any]:
    return {"attempted": 0, "trials": 0, "failures": 0, "selected_calls": 0, "penalty_decisions": 0,
            "official": Counter(), "home_stats": Counter(), "away_stats": Counter(),
            "counts": Counter(), "result_counts": Counter(), "terminations": Counter(), "sequence_lengths": Counter(),
            "totals": dict.fromkeys(_METRICS, 0), "_digest": hashlib.sha256()}


def _add(bucket: dict[str, Any], receipt: dict[str, Any]) -> None:
    bucket["trials"] += 1
    for field in ("selected_calls", "penalty_decisions"):
        bucket[field] += receipt[field]
    for field in ("official", "home_stats", "away_stats", "counts", "result_counts"):
        bucket[field].update(receipt[field])
    bucket["terminations"][receipt["termination"]] += 1
    bucket["sequence_lengths"][str(receipt["selected_calls"])] += 1
    for metric, value in (
        ("net_offensive_yards", receipt["home_stats"]["total_yards"]),
        ("home_points", receipt["score"]["home"]), ("away_points", receipt["score"]["away"]),
        ("first_downs", receipt["home_stats"]["first_downs"]), ("turnovers", receipt["home_stats"]["turnovers"]),
        ("turnover_on_downs", receipt["counts"]["turnover_on_downs"]),
        ("official_plays", receipt["official"]["offensive_plays"]),
    ):
        bucket["totals"][metric] += value
    bucket["_digest"].update(json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n")


def _finish(bucket: dict[str, Any]) -> None:
    bucket["receipt_sha256"] = bucket.pop("_digest").hexdigest()
    bucket["per_trial"] = {metric: _pair(Fraction(value, bucket["trials"])) if bucket["trials"] else None
                           for metric, value in bucket["totals"].items()}
    for field in ("official", "home_stats", "away_stats", "counts", "result_counts", "terminations", "sequence_lengths"):
        bucket[field] = dict(sorted(bucket[field].items()))


def _delta(left: dict[str, list[int]], right: dict[str, list[int]]) -> dict[str, list[int]]:
    return {key: _pair(Fraction(*right[key]) - Fraction(*left[key])) for key in _METRICS if right[key] != left[key]}


def collect_reference_contexts(
    generated: Mapping[str, TeamChart], originals: Mapping[str, TeamChart],
    runner: Callable[[TeamChart, TeamChart, str, PlayType, DefenseType, int], dict[str, Any]],
) -> dict[str, Any]:
    """Collect the fixed full matched context grid without accepting source fit.

    Args:
        generated: Complete mapped generated cohort.
        originals: Complete identically mapped reference cohort.
        runner: Engine trial function, independently checked before aggregation.

    Returns:
        Complete census, empirical diagnostics, failure seeds and limited flags.
    """
    errors: list[str] = []
    failures: list[dict[str, Any]] = []
    teams: dict[str, Any] = {}
    result: dict[str, Any] = {
        "passed": False, "errors": errors, "failures": failures, "teams": teams,
        "metadata": {"master": MASTER, "seed_domain": SEED_DOMAIN, "max_calls": MAX_CALLS,
                     "policy": "fixed-repeat-with-balanced-penalty-choice", "home_offense": True},
        "context_grid": sorted(CONTEXTS), "expected_trials": 0, "attempted_trials": 0,
        "completed_trials": 0, "failed_trials": 0, "rankings": {},
        "contexts_validated": False, "stateful_crossed_complete": False, "benchmark_complete": False,
        "source_accepted": False, "ready_for_owner_review": False, "release_certified": False,
        "interpretation": "Bounded stateful sampled contexts, not analytical probabilities, full games or source accuracy. "
                          "Shared initial seeds do not imply identical later paths. Scores precede conversion/kickoff. "
                          "Strength/formation/repetition contrasts require outlier review; no universal agreement cap.",
    }
    if (not isinstance(generated, Mapping) or not isinstance(originals, Mapping) or len(generated) < 2
            or set(generated) != set(originals) or any(not isinstance(name, str) or not name for name in generated)
            or any(not isinstance(chart, TeamChart) for cohort in (generated, originals) for chart in cohort.values())):
        errors.append("Requires complete, identically mapped cohorts with at least two TeamChart entries")
        return result
    names = sorted(generated)
    result["expected_trials"] = len(names) * (len(names) - 1) * len(CONTEXTS) * len(CHART_PLAY_TYPES) * len(DefenseType) * 4
    for name in names:
        details: dict[str, Any] = {"passed": False, "errors": [], "scenarios": {key: {} for key in ("rr", "gr", "rg", "gg")}}
        teams[name] = details
        for context in sorted(CONTEXTS):
            for play in CHART_PLAY_TYPES:
                for formation in DefenseType:
                    key = f"{context}/{play.value}/{formation.value}"
                    for scenario in details["scenarios"].values():
                        scenario[key] = _bucket()
                    for opponent in names:
                        if opponent == name:
                            continue
                        seed = int(hashlib.sha256(json.dumps(
                            [SEED_DOMAIN, MASTER, name, opponent, context, play.value, formation.value],
                            separators=(",", ":"), ensure_ascii=True,
                        ).encode()).hexdigest()[:16], 16)
                        for scenario, offense, defense in (
                            ("rr", originals[name], originals[opponent]), ("gr", generated[name], originals[opponent]),
                            ("rg", originals[name], generated[opponent]), ("gg", generated[name], generated[opponent]),
                        ):
                            bucket = details["scenarios"][scenario][key]
                            bucket["attempted"] += 1
                            result["attempted_trials"] += 1
                            try:
                                receipt = runner(offense, defense, context, play, formation, seed)
                                validate_context_trial(receipt)
                                if (receipt["seed"] != seed or receipt["context"] != context
                                        or receipt["play"] != play.value or receipt["formation"] != formation.value):
                                    raise ValueError("Context receipt does not match its declared trial")
                                _add(bucket, receipt)
                                result["completed_trials"] += 1
                            except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError, OverflowError) as error:
                                failure = {"team": name, "opponent": opponent, "context": context,
                                           "play": play.value, "formation": formation.value, "scenario": scenario,
                                           "seed": seed, "error": str(error)}
                                failures.append(failure)
                                reason = json.dumps(failure, sort_keys=True)
                                errors.append(reason)
                                details["errors"].append(reason)
                                bucket["failures"] += 1
                                result["failed_trials"] += 1
        for scenario in details["scenarios"].values():
            for bucket in scenario.values():
                _finish(bucket)
        details["passed"] = not details["errors"]
        if not details["passed"]:
            continue
        scenarios = details["scenarios"]
        details["contrasts"] = {}
        for key in scenarios["rr"]:
            values = {label: scenario[key]["per_trial"] for label, scenario in scenarios.items()}
            interaction = {metric: Fraction(*values["gg"][metric]) - Fraction(*values["gr"][metric])
                           - Fraction(*values["rg"][metric]) + Fraction(*values["rr"][metric]) for metric in _METRICS}
            details["contrasts"][key] = {
                **{label: _delta(values["rr"], values[scenario])
                   for label, scenario in (("offense", "gr"), ("defense", "rg"), ("joint", "gg"))},
                "interaction": {metric: _pair(value) for metric, value in interaction.items() if value},
            }
        details["formation_contrasts"] = {
            label: {key: _delta(scenario[key.rsplit("/", 1)[0] + "/A"]["per_trial"], bucket["per_trial"])
                    for key, bucket in scenario.items()} for label, scenario in scenarios.items()}
    for scenario in ("rr", "gr", "rg", "gg"):
        def rank(name: str, scenario: str = scenario) -> tuple[Fraction, str]:
            buckets = teams[name]["scenarios"][scenario]
            return (-Fraction(sum(bucket["totals"]["net_offensive_yards"] for bucket in buckets.values()),
                              sum(bucket["trials"] for bucket in buckets.values())), name)
        result["rankings"][scenario] = sorted((name for name in names if teams[name]["passed"]), key=rank)
    if result["attempted_trials"] != result["expected_trials"] or result["completed_trials"] + result["failed_trials"] != result["attempted_trials"]:
        errors.append("Context trial census does not reconcile")
    result["passed"] = result["contexts_validated"] = not errors
    return result


def _validate_accounting(receipt: dict[str, Any], selected: int) -> dict[str, int]:
    official = receipt["official"]
    if not isinstance(official, dict) or set(official) != set(_OFFICIAL):
        raise ValueError("Incomplete official context counts")
    for count in official.values():
        _integer(count)
    if not 0 <= official["completions"] <= official["pass_attempts"] <= official["offensive_plays"] <= selected:
        raise ValueError("Context pass/selected counts do not reconcile")
    for label in ("home_stats", "away_stats"):
        stats = receipt[label]
        for key, value in stats.items():
            _integer(value, None if key in {"total_yards", "rushing_yards", "passing_yards"} else 0)
        if stats["total_yards"] != stats["rushing_yards"] + stats["passing_yards"] - stats["sack_yards"]:
            raise ValueError("Context official yardage identity does not reconcile")
        if stats["turnovers"] != stats["interceptions_thrown"] + stats["fumbles_lost"]:
            raise ValueError("Context official turnover identity does not reconcile")
    home = receipt["home_stats"]
    if (official["offensive_plays"] != official["pass_attempts"] + official["rushing_attempts"] + home["sacks"]
            or home["interceptions_thrown"] > official["pass_attempts"]):
        raise ValueError("Context official play identity does not reconcile")
    return home


def validate_context_collection(report: dict[str, Any], names: set[str]) -> None:
    """Reconcile a complete context collection without granting benchmark acceptance.

    Args:
        report: Computed context report, never a replacement for its engine trials.
        names: Complete expected matched team identifiers.

    Returns:
        None when the full fixed census, accounting and contrasts reconcile.
    """
    if (not isinstance(report, dict) or report.get("passed") is not True or report.get("errors") != []
            or report.get("contexts_validated") is not True or report.get("failures") != []
            or any(report.get(flag) is not False for flag in (
                "stateful_crossed_complete", "benchmark_complete", "source_accepted", "ready_for_owner_review", "release_certified"))):
        raise ValueError("Failed or malformed context collection")
    if (report["metadata"] != {"master": MASTER, "seed_domain": SEED_DOMAIN, "max_calls": MAX_CALLS,
                              "policy": "fixed-repeat-with-balanced-penalty-choice", "home_offense": True}
            or report["context_grid"] != sorted(CONTEXTS) or len(names) < 2 or set(report["teams"]) != names):
        raise ValueError("Context protocol, grid or team census does not match")
    expected = len(names) * (len(names) - 1) * len(CONTEXTS) * len(CHART_PLAY_TYPES) * len(DefenseType) * 4
    if (any(_integer(report[field]) != expected for field in ("expected_trials", "attempted_trials", "completed_trials"))
            or _integer(report["failed_trials"]) != 0):
        raise ValueError("Context trial census is incomplete")
    keys = {f"{context}/{play.value}/{formation.value}" for context in CONTEXTS for play in CHART_PLAY_TYPES for formation in DefenseType}
    for details in report["teams"].values():
        if (details["passed"] is not True or details["errors"] != []
                or set(details["scenarios"]) != {"rr", "gr", "rg", "gg"}):
            raise ValueError("Incomplete team context evidence")
        for scenario in details["scenarios"].values():
            if set(scenario) != keys:
                raise ValueError("Missing or extra context/call/formation bucket")
            for bucket in scenario.values():
                if (any(_integer(bucket[field]) != len(names) - 1 for field in ("trials", "attempted"))
                        or _integer(bucket["failures"]) != 0):
                    raise ValueError("Context bucket has missing or failed opponents")
                selected = _integer(bucket["selected_calls"], 1)
                if not bucket["trials"] <= selected <= bucket["trials"] * MAX_CALLS:
                    raise ValueError("Context bucket call budget does not reconcile")
                home = _validate_accounting(bucket, selected)
                _integer(bucket["penalty_decisions"])
                if (set(bucket["counts"]) != set(_COUNTS) or any(_integer(value) < 0 for value in bucket["counts"].values())
                        or bucket["counts"]["pending_penalties"] or bucket["counts"]["lost_fumbles"] != home["fumbles_lost"]
                        or not set(bucket["result_counts"]) <= {kind.value for kind in ResultType}
                        or sum(_integer(value) for value in bucket["result_counts"].values()) != selected):
                    raise ValueError("Context branch/result accounting does not reconcile")
                if (not set(bucket["terminations"]) <= {"call_limit", "score", "possession_change", "game_over"}
                        or sum(_integer(value) for value in bucket["terminations"].values()) != bucket["trials"]
                        or not set(bucket["sequence_lengths"]) <= {"1", "2", "3", "4"}
                        or sum(_integer(value) for value in bucket["sequence_lengths"].values()) != bucket["trials"]
                        or sum(int(length) * value for length, value in bucket["sequence_lengths"].items()) != selected):
                    raise ValueError("Context sequence lengths/terminations do not reconcile")
                if (not isinstance(bucket["receipt_sha256"], str) or len(bucket["receipt_sha256"]) != 64
                        or any(character not in "0123456789abcdef" for character in bucket["receipt_sha256"])):
                    raise ValueError("Context receipt digest is invalid")
                if set(bucket["totals"]) != set(_METRICS) or set(bucket["per_trial"]) != set(_METRICS):
                    raise ValueError("Context metrics are incomplete")
                for metric, value in bucket["totals"].items():
                    _integer(value, None if metric == "net_offensive_yards" else 0)
                    if bucket["per_trial"][metric] != _pair(Fraction(value, bucket["trials"])):
                        raise ValueError("Context empirical metric denominator/value does not reconcile")
                if any(bucket["totals"][key] != value for key, value in (
                    ("net_offensive_yards", home["total_yards"]), ("first_downs", home["first_downs"]),
                    ("turnovers", home["turnovers"]), ("turnover_on_downs", bucket["counts"]["turnover_on_downs"]),
                    ("official_plays", bucket["official"]["offensive_plays"]),
                )):
                    raise ValueError("Context metrics differ from authoritative accounting")
        if set(details["contrasts"]) != keys or set(details["formation_contrasts"]) != {"rr", "gr", "rg", "gg"}:
            raise ValueError("Context contrasts are incomplete")
        for key in keys:
            values = {label: scenario[key]["per_trial"] for label, scenario in details["scenarios"].items()}
            interaction = {metric: Fraction(*values["gg"][metric]) - Fraction(*values["gr"][metric])
                           - Fraction(*values["rg"][metric]) + Fraction(*values["rr"][metric]) for metric in _METRICS}
            expected_contrast = {
                **{label: _delta(values["rr"], values[scenario])
                   for label, scenario in (("offense", "gr"), ("defense", "rg"), ("joint", "gg"))},
                "interaction": {metric: _pair(value) for metric, value in interaction.items() if value},
            }
            if details["contrasts"][key] != expected_contrast:
                raise ValueError("Context crossed contrasts do not reconcile")
        for label, scenario in details["scenarios"].items():
            if details["formation_contrasts"][label] != {
                key: _delta(scenario[key.rsplit("/", 1)[0] + "/A"]["per_trial"], bucket["per_trial"])
                for key, bucket in scenario.items()
            }:
                raise ValueError("Context formation contrasts do not reconcile")
    if set(report["rankings"]) != {"rr", "gr", "rg", "gg"}:
        raise ValueError("Context rankings are incomplete")
    for scenario in ("rr", "gr", "rg", "gg"):
        def rank(name: str, scenario: str = scenario) -> tuple[Fraction, str]:
            buckets = report["teams"][name]["scenarios"][scenario]
            return (-Fraction(sum(bucket["totals"]["net_offensive_yards"] for bucket in buckets.values()),
                              sum(bucket["trials"] for bucket in buckets.values())), name)
        if report["rankings"][scenario] != sorted(names, key=rank):
            raise ValueError("Context ranking does not reconcile")

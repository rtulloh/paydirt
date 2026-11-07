"""Matched stateful reference controls use only synthetic chart fixtures."""
from __future__ import annotations

import random
from copy import deepcopy
from fractions import Fraction

import pytest

import paydirt.chart_reference_audit as reference
from paydirt.chart_loader import TeamChart
from paydirt.play_resolver import DefenseType, PlayType
from tests.test_chart_reference_weighted import team

CONTEXTS = {"own1-first", "own40-first", "opp2-first", "own1-fourth", "own40-fourth", "opp2-fourth"}
SCENARIOS = {"rr", "gr", "rg", "gg"}


def trial(chart: TeamChart, context: str = "own40-first", *, defender: TeamChart | None = None,
          play: PlayType = PlayType.SHORT_PASS, seed: int = 20261108) -> dict:
    function = getattr(reference, "run_reference_context_trial", None)
    assert callable(function), "Stateful reference contexts must use the authoritative engine"
    return function(chart, defender or team("Defense"), context, play, DefenseType.STANDARD, seed)


def compare(generated: dict, originals: dict) -> dict:
    function = getattr(reference, "compare_reference_contexts", None)
    assert callable(function), "Reference comparison needs matched stateful four-combination contexts"
    return function(generated, originals)


@pytest.fixture
def cohorts() -> tuple[dict, dict]:
    originals = {name: team(name) for name in ("Alpha", "Beta")}
    return deepcopy(originals), originals


@pytest.mark.parametrize("token,context,position,home_points,away_points,termination", [
    ("5", "own40-first", 60, 0, 0, "call_limit"),
    ("5", "opp2-first", 100, 6, 0, "score"),
    ("-5", "own1-first", 20, 0, 2, "score"),
    ("0", "own40-fourth", 60, 0, 0, "possession_change"),
    ("BLACK", "own40-first", 60, 0, 0, "possession_change"),
    ("B", "opp2-first", 100, 6, 0, "score"),
    ("QT", "own1-first", 20, 0, 2, "score"),
])
def test_core_clipping_scoring_downs_and_secondary_contexts(
    token: str, context: str, position: int, home_points: int, away_points: int, termination: str,
) -> None:
    result = trial(team("Offense", token), context)
    assert result["final"]["ball_position"] == position
    assert result["score"] == {"home": home_points, "away": away_points}
    assert result["termination"] == termination
    assert result["selected_calls"] <= 4
    assert result["official"]["offensive_plays"] == (
        result["official"]["pass_attempts"] + result["official"]["rushing_attempts"] + result["home_stats"]["sacks"])
    if token == "0" and context.endswith("fourth"):
        assert result["counts"]["turnover_on_downs"] == 1
    if token == "5" and context == "own40-first":
        assert result["selected_calls"] == 4 and result["home_stats"]["first_downs"] == 2
        assert result["home_stats"]["passing_yards"] == 20


@pytest.mark.parametrize("retained,return_cell,home_points,away_points", [
    (True, "0", 0, 0), (False, "0", 0, 0), (False, "TD", 0, 6),
])
def test_core_recovery_and_return_score_are_observed_not_recalculated(
    retained: bool, return_cell: str, home_points: int, away_points: int,
) -> None:
    chart, defender = team("Offense", "F + 2"), team("Defense")
    if not retained:
        chart.peripheral.fumble_recovered_range = (0, 0)
        chart.peripheral.fumble_lost_range = (10, 39)
    for candidate in (chart, defender):
        candidate.special_teams.fumble_return = dict.fromkeys(range(10, 40), return_cell)
        candidate.special_teams.interception_return = dict.fromkeys(range(10, 40), return_cell)
    if not retained and return_cell == "TD":
        from unittest.mock import patch
        with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(10, "primary"), (37, "eligible recovery")]):
            result = trial(chart, defender=defender)
    else:
        result = trial(chart, defender=defender)
    assert result["score"] == {"home": home_points, "away": away_points}
    assert result["home_stats"]["fumbles_lost"] == (0 if retained else 1)
    assert result["counts"]["retained_fumbles" if retained else "lost_fumbles"] >= 1
    assert result["selected_calls"] == (4 if retained else 1)
    assert result["termination"] == ("score" if away_points else "possession_change")
    if retained:
        assert result["counts"]["turnover_on_downs"] == 1


@pytest.mark.parametrize("token", ["OFF 5", "DEF 5", "PI 10"])
def test_pending_penalties_are_finalized_through_existing_policy(token: str) -> None:
    result = trial(team("Offense", token))
    assert result["penalty_decisions"] > 0
    assert result["counts"]["pending_penalties"] == 0
    assert result["selected_calls"] == 4
    assert result["official"]["offensive_plays"] == (4 if token == "OFF 5" else 0)
    assert result["home_stats"]["total_yards"] == 0


def test_trial_preserves_inputs_and_caller_rng_even_on_core_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.game_engine import PaydirtGameEngine

    chart = team("Offense")
    before = deepcopy(chart)
    random.seed(711)
    rng = random.getstate()
    first = trial(chart)
    assert trial(chart) == first and random.getstate() == rng and chart == before
    def broken(*args: object, **kwargs: object) -> object:
        random.random()
        raise RuntimeError("Synthetic engine exception")
    monkeypatch.setattr(PaydirtGameEngine, "run_play_with_penalty_procedure", broken)
    with pytest.raises(RuntimeError, match="Synthetic engine exception"):
        trial(chart)
    assert random.getstate() == rng and chart == before


@pytest.mark.parametrize("mutation", ["context", "seed-bool", "seed-negative", "chart", "play", "formation"])
def test_invalid_trial_setup_fails_explicitly(mutation: str) -> None:
    function = getattr(reference, "run_reference_context_trial", None)
    assert callable(function), "Stateful context setup needs strict validation"
    arguments = [team("Offense"), team("Defense"), "own40-first", PlayType.SHORT_PASS, DefenseType.STANDARD, 20261108]
    index, value = {"context": (2, "unknown"), "seed-bool": (5, True), "seed-negative": (5, -1),
                    "chart": (0, {}), "play": (3, PlayType.PUNT), "formation": (4, "A")}[mutation]
    arguments[index] = value
    with pytest.raises((ValueError, TypeError)):
        function(*arguments)


def test_complete_crossed_collection_has_exact_census_and_no_acceptance_claim(cohorts: tuple) -> None:
    before = deepcopy(cohorts)
    result = compare(*cohorts)
    assert result["passed"], result["errors"]
    assert result["contexts_validated"]
    assert not result["stateful_crossed_complete"] and not result["benchmark_complete"]
    assert not result["source_accepted"] and not result["ready_for_owner_review"] and not result["release_certified"]
    assert result["metadata"]["master"] == 20261108 and result["metadata"]["max_calls"] == 4
    assert result["expected_trials"] == result["attempted_trials"] == result["completed_trials"] == 2 * 54 * 6 * 4
    assert result["failed_trials"] == 0 and result["context_grid"] == sorted(CONTEXTS)
    for details in result["teams"].values():
        assert details["passed"] and set(details["scenarios"]) == SCENARIOS
        assert len(details["contrasts"]) == 54 * 6
        assert all(not values["joint"] for values in details["contrasts"].values())
        for scenario in details["scenarios"].values():
            assert len(scenario) == 54 * 6
            assert all(bucket["trials"] == 1 and len(bucket["receipt_sha256"]) == 64 for bucket in scenario.values())
    assert cohorts == before


def test_offense_defense_interactions_and_formation_costs_are_separate(cohorts: tuple) -> None:
    generated, originals = cohorts
    for chart in generated.values():
        chart.offense.short_pass = dict.fromkeys(range(10, 40), "8")
        for (formation, _row), cells in chart.defense.modifiers.items():
            if formation == "A":
                cells[6] = "-2"
    result = compare(generated, originals)
    assert result["passed"], result["errors"]
    details = result["teams"]["Alpha"]
    key = "own40-first/short_pass/A"
    metrics = {name: values[key]["per_trial"]["net_offensive_yards"] for name, values in details["scenarios"].items()}
    assert {name: Fraction(*pair) for name, pair in metrics.items()} == {"rr": 20, "gr": 32, "rg": 12, "gg": 24}
    delta = details["contrasts"][key]
    assert Fraction(*delta["offense"]["net_offensive_yards"]) == 12
    assert Fraction(*delta["defense"]["net_offensive_yards"]) == -8
    assert Fraction(*delta["joint"]["net_offensive_yards"]) == 4
    assert delta["interaction"].get("net_offensive_yards", [0, 1]) == [0, 1]
    assert delta["interaction"]["first_downs"] == [1, 1]
    assert Fraction(*details["formation_contrasts"]["gg"]["own40-first/short_pass/B"]["net_offensive_yards"]) == 8
    assert result["rankings"]["gg"] == ["Alpha", "Beta"]


@pytest.mark.parametrize("mutation", ["empty", "one-team", "missing", "extra", "non-chart"])
def test_invalid_shared_cohorts_cannot_be_partially_compared(cohorts: tuple, mutation: str) -> None:
    generated, originals = cohorts
    if mutation == "empty": generated.clear(); originals.clear()
    elif mutation == "one-team": generated.pop("Beta"); originals.pop("Beta")
    elif mutation == "missing": generated.pop("Beta")
    elif mutation == "extra": generated["Other"] = team("Other")
    else: generated["Alpha"] = {}
    result = compare(generated, originals)
    assert not result["passed"] and result["errors"] and not result["contexts_validated"]
    assert not result["benchmark_complete"] and not result["release_certified"]


@pytest.mark.parametrize("mutation", ["exception", "negative-count", "nonfinite", "inconsistent-score", "missing-official"])
def test_failed_trial_is_retained_with_seed_and_other_teams_continue(
    cohorts: tuple, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    function = getattr(reference, "run_reference_context_trial", None)
    assert callable(function), "Stateful collector needs independently validated trial receipts"
    calls = 0
    def corrupted(*args: object) -> dict:
        nonlocal calls
        calls += 1
        result = function(*args)
        if calls != 1:
            return result
        if mutation == "exception": raise RuntimeError("Synthetic one-trial failure")
        if mutation == "negative-count": result["selected_calls"] = -1
        elif mutation == "nonfinite": result["final"]["time_remaining"] = float("nan")
        elif mutation == "inconsistent-score": result["score"]["home"] += 1
        else: result.pop("official")
        return result
    monkeypatch.setattr(reference, "run_reference_context_trial", corrupted)
    result = compare(*cohorts)
    assert not result["passed"] and result["failed_trials"] == 1 and result["errors"]
    assert result["attempted_trials"] == result["expected_trials"] == result["completed_trials"] + 1
    failure = result["failures"][0]
    assert failure["team"] == "Alpha" and failure["opponent"] == "Beta" and type(failure["seed"]) is int
    assert result["teams"]["Beta"]["passed"]
    assert not result["contexts_validated"] and not result["benchmark_complete"]


@pytest.mark.parametrize("return_cell,points", [("0", 0), ("TD", 6)])
def test_interception_return_uses_defender_chart_and_official_credit(return_cell: str, points: int) -> None:
    defender = team("Defense")
    defender.special_teams.interception_return = dict.fromkeys(range(10, 40), return_cell)
    result = trial(team("Offense", "INT 10"), defender=defender)
    assert result["selected_calls"] == 1 and result["home_stats"]["interceptions_thrown"] == 1
    assert result["official"]["pass_attempts"] == 1 and result["official"]["completions"] == 0
    assert result["score"] == {"home": 0, "away": points}


@pytest.mark.parametrize("secondary,sacks,rushes", [("SACK 0", 4, 0), ("6", 0, 4), ("F - 3", 4, 0), ("F + 3", 0, 4)])
def test_qt_credit_remains_engine_owned(secondary: str, sacks: int, rushes: int) -> None:
    chart = team("Offense", "QT")
    chart.offense.qb_time = dict.fromkeys(range(10, 40), secondary)
    for column in ("fumble_return", "interception_return"):
        setattr(chart.special_teams, column, dict.fromkeys(range(10, 40), "0"))
    result = trial(chart)
    assert result["home_stats"]["sacks"] == sacks
    assert result["official"]["rushing_attempts"] == rushes
    assert result["official"]["pass_attempts"] == result["official"]["completions"] == 0
    assert result["counts"]["qt"] == 4

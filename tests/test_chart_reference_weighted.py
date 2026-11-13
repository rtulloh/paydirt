"""Exact weighted comparisons use only synthetic charts and public sample fixtures."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction

import pytest

import paydirt.chart_audit as mechanics
import paydirt.chart_reference_audit as reference
from paydirt.chart_loader import TeamChart
from paydirt.chart_tactics_audit import controlled_offense
from paydirt.play_resolver import chart_roll_weights

SCENARIOS = {"rr", "gr", "rg", "gg"}


def team(name: str, token: str = "5", modifier: str = "0") -> TeamChart:
    chart = controlled_offense(token)
    chart.peripheral.team_name = name
    chart.defense.modifiers = {
        (formation, row): dict.fromkeys(range(1, 10), modifier)
        for formation in "ABCDEF"
        for row in range(1, 6)
    }
    for column, value in (
        ("kickoff", "60"),
        ("kickoff_return", "20"),
        ("punt", "40"),
        ("punt_return", "8"),
        ("interception_return", "5"),
        ("fumble_return", "5"),
        ("field_goal", "40"),
    ):
        setattr(chart.special_teams, column, dict.fromkeys(range(10, 40), value))
    return chart


def comparison(generated: dict, original: dict) -> dict:
    function = getattr(reference, "compare_reference_weighted", None)
    assert callable(function), (
        "Reference benchmark needs exact four-combination weighted comparisons"
    )
    return function(generated, original)


@pytest.fixture
def cohorts() -> tuple[dict, dict]:
    original = {name: team(name) for name in ("Alpha", "Beta")}
    return deepcopy(original), original


@pytest.mark.parametrize(
    "token,modifier,secondary,expected",
    [
        ("5*", "0", None, "yards:5|oob=1"),
        ("5*", "(3)", None, "yards:3|oob=0"),
        ("B", "0", "25*", "breakaway:25|oob=1"),
        ("QT", "0", "SACK 0*", "sack:0|oob=1"),
        ("QT", "BLACK", None, "incomplete:0|oob=0"),
        ("F + 2", "INT 10", None, "pending_fumble:2|oob=0"),
        ("INT 10", "F", None, "pending_fumble:10|oob=0"),
        ("TD", "0", None, "pending_touchdown_distance|oob=0"),
        ("OFF 5", "0", None, "pending_penalty|oob=0"),
    ],
)
def test_existing_exact_enumerator_preserves_joint_chart_flags(
    token: str,
    modifier: str,
    secondary: str | None,
    expected: str,
) -> None:
    chart = team("Synthetic", token, modifier)
    if secondary is not None:
        setattr(
            chart.offense,
            "breakaway" if token == "B" else "qb_time",
            dict.fromkeys(range(10, 40), secondary),
        )
    play = mechanics._exact_team_mechanics(chart, [chart])["plays"]["short_pass/A"]
    assert set(play["exact_joint_masses"]) == {expected}
    assert sum(Fraction(*mass) for mass in play["exact_joint_masses"].values()) == 1
    assert sum(Fraction(*mass) for mass in play["exact_masses"].values()) == 1
    assert Fraction(*play["trigger_exact_masses"]["qt"]) == (
        1 if token == "QT" and modifier == "0" else 0
    )
    assert Fraction(*play["trigger_exact_masses"]["breakaway"]) == (1 if token == "B" else 0)


def test_existing_special_recovery_ep_and_distance_masses_are_exact() -> None:
    chart = team("Synthetic")
    chart.special_teams.field_goal[10] = "BK"
    chart.special_teams.extra_point_no_good = [10]
    report = mechanics._exact_team_mechanics(chart, [chart])
    mass = Fraction(chart_roll_weights()[10], 216)
    field_goals = report["special_teams"]["field_goal"]
    assert Fraction(*field_goals["exact_masses"]["BK"]) == mass
    assert sum(Fraction(*pair) for pair in field_goals["exact_masses"].values()) == 1
    assert Fraction(*field_goals["exact_by_distance"]["57"]) == 1 - mass
    assert Fraction(*field_goals["exact_by_distance"]["58"]) == 0
    assert Fraction(*report["extra_point_exact_miss_mass"]) == mass
    assert report["exact_recovery"] == {"retained": [216, 216], "lost": [0, 216]}


def test_identical_cohorts_cover_all_calls_and_four_combinations_without_mutation(
    cohorts: tuple,
) -> None:
    generated, original = cohorts
    before = deepcopy(cohorts)
    result = comparison(generated, original)
    assert result["passed"], result["errors"]
    assert result["weighted_validated"] and result["behavior_matches_reference"]
    assert not result["stateful_crossed_complete"] and not result["benchmark_complete"]
    assert (
        not result["source_accepted"]
        and not result["ready_for_owner_review"]
        and not result["release_certified"]
    )
    assert result["uniform_defense_team_count"] == 2
    for details in result["teams"].values():
        assert set(details["scenarios"]) == SCENARIOS and len(details["plays"]) == 54
        assert details["max_joint_total_variation"] == [0, 1]
        for values in details["plays"].values():
            assert all(
                values[name]["total_variation"] == [0, 1]
                for name in ("offense", "defense", "joint")
            )
            assert values["interaction"]["delta"] == {} and values["interaction"]["l1"] == [0, 1]
    assert cohorts == before


def test_offense_and_defense_effects_are_crossed_separately(cohorts: tuple) -> None:
    generated, original = cohorts
    for chart in generated.values():
        for cells in chart.defense.modifiers.values():
            cells.update(dict.fromkeys(range(1, 10), "-2"))
        chart.offense.short_pass = dict.fromkeys(range(10, 40), "8")
    result = comparison(generated, original)
    assert result["passed"] and not result["behavior_matches_reference"]
    values = result["teams"]["Alpha"]["plays"]["short_pass/A"]
    assert values["offense"]["delta"] == {"yards:5|oob=0": [-1, 1], "yards:8|oob=0": [1, 1]}
    assert values["defense"]["delta"] == {"yards:3|oob=0": [1, 1], "yards:5|oob=0": [-1, 1]}
    assert values["joint"]["delta"] == {"yards:5|oob=0": [-1, 1], "yards:6|oob=0": [1, 1]}
    assert Fraction(*values["interaction"]["l1"]) == 4


def test_numeric_yield_does_not_assign_zero_to_unresolved_branches(cohorts: tuple) -> None:
    generated, original = cohorts
    for charts in cohorts:
        for chart in charts.values():
            chart.offense.short_pass = dict.fromkeys(range(10, 40), "TD")
    result = comparison(generated, original)
    assert result["passed"] and result["behavior_matches_reference"]
    numeric = result["teams"]["Alpha"]["scenarios"]["rr"]["known_numeric"]["short_pass/A"]
    assert numeric["probability"] == [0, 1] and numeric["conditional_mean"] is None
    assert numeric["yard_moment_per_lookup"] == [0, 1] and numeric["pending_probability"] == [1, 1]
    assert "whole_play_ypa" not in numeric


@pytest.mark.parametrize("equal_weight", [False, True])
def test_layout_changes_use_physical_mass_and_joint_oob_correlation(
    cohorts: tuple, equal_weight: bool
) -> None:
    generated, original = cohorts
    weights = chart_roll_weights()
    left = 10
    right = next(
        roll
        for roll in weights
        if roll != left and (weights[roll] == weights[left]) == equal_weight
    )
    for charts in cohorts:
        charts["Alpha"].offense.short_pass[left] = "20*"
    generated["Alpha"].offense.short_pass[left], generated["Alpha"].offense.short_pass[right] = (
        generated["Alpha"].offense.short_pass[right],
        generated["Alpha"].offense.short_pass[left],
    )
    result = comparison(generated, original)
    assert result["passed"]
    observed = Fraction(
        *result["teams"]["Alpha"]["plays"]["short_pass/A"]["joint"]["total_variation"]
    )
    assert observed == abs(Fraction(weights[left] - weights[right], 216))
    assert result["behavior_matches_reference"] is equal_weight


def test_same_numeric_distribution_with_different_oob_correlation_is_detected(
    cohorts: tuple,
) -> None:
    generated, original = cohorts
    for chart in generated.values():
        chart.offense.short_pass = dict.fromkeys(range(10, 40), "5*")
    result = comparison(generated, original)
    assert result["passed"] and not result["behavior_matches_reference"]
    values = result["teams"]["Alpha"]["plays"]["short_pass/A"]
    assert values["joint"]["total_variation"] == [1, 1]
    assert values["joint"]["delta"] == {"yards:5|oob=0": [-1, 1], "yards:5|oob=1": [1, 1]}


@pytest.mark.parametrize(
    "trigger,column,cell,count",
    [
        ("QT", "qb_time", "OFF 5", 16),
        ("B", "breakaway", "DEF 5", 26),
    ],
)
def test_fallback_distribution_is_explicit_not_missing_or_historical_truth(
    cohorts: tuple,
    trigger: str,
    column: str,
    cell: str,
    count: int,
) -> None:
    for charts in cohorts:
        for chart in charts.values():
            chart.offense.short_pass = dict.fromkeys(range(10, 40), trigger)
            setattr(chart.offense, column, dict.fromkeys(range(10, 40), cell))
    result = comparison(*cohorts)
    assert result["passed"]
    play = result["teams"]["Alpha"]["scenarios"]["rr"]["plays"]["short_pass/A"]
    assert Fraction(*play["secondary_fallback_exact_mass"]) == 1
    assert len(play["exact_joint_masses"]) == count
    assert {Fraction(*pair) for pair in play["exact_joint_masses"].values()} == {Fraction(1, count)}


def test_rare_special_ep_and_recovery_changes_are_not_rounded_away(cohorts: tuple) -> None:
    generated, original = cohorts
    chart = generated["Alpha"]
    chart.special_teams.field_goal[10] = "BK"
    chart.special_teams.extra_point_no_good = [10]
    chart.peripheral.fumble_recovered_range = (10, 38)
    chart.peripheral.fumble_lost_range = (39, 39)
    result = comparison(generated, original)
    assert result["passed"] and not result["behavior_matches_reference"]
    details = result["teams"]["Alpha"]
    assert Fraction(*details["special_teams"]["field_goal"]["total_variation"]) == Fraction(
        chart_roll_weights()[10], 216
    )
    assert Fraction(*details["field_goal_by_distance"]["57"]["delta"]) == -Fraction(
        chart_roll_weights()[10], 216
    )
    assert Fraction(*details["extra_point_miss"]["delta"]) == Fraction(
        chart_roll_weights()[10], 216
    )
    assert Fraction(*details["recovery"]["total_variation"]) == Fraction(
        chart_roll_weights()[39], 216
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-team",
        "extra-team",
        "empty",
        "non-chart",
        "missing-play",
        "extra-play",
        "bad-pair",
        "bool-mass",
        "zero-denominator",
        "negative",
        "missing-mass",
        "joint-marginal",
        "joint-label",
        "special-mass",
        "fg-distance",
        "recovery",
        "trigger",
        "fallback",
    ],
)
def test_invalid_corpora_or_exact_results_fail_and_keep_other_teams(
    cohorts: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    generated, original = cohorts
    if mutation == "missing-team":
        generated.pop("Alpha")
    elif mutation == "extra-team":
        generated["Other"] = team("Other")
    elif mutation == "empty":
        generated.clear()
        original.clear()
    elif mutation == "non-chart":
        generated["Alpha"] = {}
    else:
        exact = mechanics._exact_team_mechanics

        def broken(chart: TeamChart, opponents: list[TeamChart]) -> dict:
            report = exact(chart, opponents)
            if chart.peripheral.team_name != "Alpha":
                return report
            play = report["plays"]["short_pass/A"]
            if mutation == "missing-play":
                report["plays"].pop("long_pass/F")
            elif mutation == "extra-play":
                report["plays"]["invented/A"] = deepcopy(play)
            elif mutation == "bad-pair":
                play["exact_joint_masses"] = {"yards:5|oob=0": [1]}
            elif mutation == "bool-mass":
                play["exact_joint_masses"] = {"yards:5|oob=0": [True, 1]}
            elif mutation == "zero-denominator":
                play["exact_joint_masses"] = {"yards:5|oob=0": [1, 0]}
            elif mutation == "negative":
                play["exact_joint_masses"] = {"yards:5|oob=0": [-1, 1]}
            elif mutation == "missing-mass":
                play["exact_joint_masses"] = {"yards:5|oob=0": [1, 2]}
            elif mutation == "joint-marginal":
                play["exact_joint_masses"] = {"yards:8|oob=0": [1, 1]}
            elif mutation == "joint-label":
                play["exact_joint_masses"] = {"yards:5|oob=maybe": [1, 1]}
            elif mutation == "special-mass":
                report["special_teams"]["punt"]["exact_masses"] = {"40": [1, 2]}
            elif mutation == "fg-distance":
                report["special_teams"]["field_goal"]["exact_by_distance"].pop("57")
            elif mutation == "recovery":
                report["exact_recovery"]["retained"] = [215, 216]
            elif mutation == "trigger":
                play["trigger_exact_masses"]["qt"] = [2, 1]
            elif mutation == "fallback":
                play["secondary_fallback_exact_mass"] = [2, 1]
            return report

        monkeypatch.setattr(mechanics, "_exact_team_mechanics", broken)
    result = comparison(generated, original)
    assert not result["passed"] and result["errors"] and not result["weighted_validated"]
    assert not result["benchmark_complete"] and not result["release_certified"]
    # A malformed defender invalidates the shared opposing-cohort mixture for every team.
    if mutation not in {"missing-team", "extra-team", "empty", "non-chart"}:
        assert result["teams"]["Beta"]["passed"]


def test_team_ranking_is_deterministic_and_reports_worst_call(cohorts: tuple) -> None:
    generated, original = cohorts
    for chart in generated.values():
        chart.offense.short_pass = dict.fromkeys(range(10, 40), "7")
    result = comparison(dict(reversed(list(generated.items()))), original)
    assert result["passed"]
    assert result["ranking"] == ["Alpha", "Beta"]
    assert result["teams"]["Alpha"]["worst_joint_call"] == "short_pass/A"


@pytest.mark.parametrize("token", ["F + 3", "F - 3"])
def test_decoder_rejects_signed_defensive_fumble_priority_fallback(token: str) -> None:
    assert mechanics._decoder_cell_class("defense", "A/short_pass", token) == "unsupported"
    assert mechanics._decoder_cell_class("defense", "A/short_pass", "F") == "supported"
    assert mechanics._decoder_cell_class("offense", "short_pass", token) == "supported"


@pytest.mark.parametrize(
    "trigger,column,low,high", [("B", "breakaway", 15, 40), ("QT", "qb_time", -5, 10)]
)
@pytest.mark.parametrize("missing", [False, True])
def test_missing_or_blank_secondary_rows_retain_actual_random_fallback(
    trigger: str,
    column: str,
    low: int,
    high: int,
    missing: bool,
) -> None:
    from unittest.mock import patch

    from paydirt.play_resolver import resolve_breakaway, resolve_qb_scramble

    chart = team("Synthetic", trigger)
    cells = getattr(chart.offense, column)
    if missing:
        cells.pop(10)
    else:
        cells[10] = ""
    resolver = resolve_breakaway if trigger == "B" else resolve_qb_scramble
    with patch("paydirt.play_resolver.random.randint", return_value=low) as fallback:
        actual = resolver(chart.offense, 10)
    assert actual.yards == low and not actual.out_of_bounds
    fallback.assert_called_once_with(low, high)
    play = mechanics._exact_team_mechanics(chart, [chart])["plays"]["short_pass/A"]
    expected = Fraction(chart_roll_weights()[10], 216)
    assert Fraction(*play["secondary_fallback_exact_mass"]) == expected
    for yards in range(low, high + 1):
        kind = "breakaway" if trigger == "B" else "sack" if yards < 0 else "scramble"
        observed = Fraction(*play["exact_joint_masses"][f"{kind}:{yards}|oob=0"])
        normal = Fraction(1) - expected if cells.get(11) == str(yards) else Fraction()
        assert observed == normal + expected / (high - low + 1)

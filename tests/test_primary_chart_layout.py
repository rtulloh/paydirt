"""Playable placement must preserve whole tokens at exact physical dice mass."""

from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from paydirt import chart_generator as generator
from paydirt import chart_layout
from paydirt.play_resolver import chart_roll_weights

PRIMARY = ("line_plunge", "off_tackle", "end_run", "draw", "screen", "short_pass",
           "medium_pass", "long_pass", "te_short_long")


def _clustered() -> dict[str, dict[int, str]]:
    offense = {name: {roll: "BLACK" if roll < 25 else "4" for roll in range(10, 40)}
               for name in PRIMARY}
    for name in PRIMARY:
        offense[name].update({26: "4*", 27: "4†", 28: "B*", 29: "QT*", 30: "F - 2",
                              31: "INT 5", 32: "OFF 5", 33: "PI 8", 34: "TD"})
    offense["qb_time"] = dict.fromkeys(range(10, 40), "SACK 0*")
    offense["breakaway"] = dict.fromkeys(range(10, 40), "30*")
    offense["fumble_return"] = dict.fromkeys(range(10, 40), "7")
    return offense


def _api(name: str):
    function = getattr(chart_layout, name, None)
    assert callable(function), f"Generator must provide {name} before changing chart placement"
    return function


def _inventory(column: dict[int, str]) -> Counter:
    return Counter((chart_roll_weights()[roll], token) for roll, token in column.items())


def test_clustered_primary_layout_improves_without_changing_any_weighted_token() -> None:
    before = _clustered()
    original = deepcopy(before)
    after, evidence = _api("disperse_primary_layout")(before)
    assert before == original
    assert evidence["accepted_swaps"] > 0
    assert evidence["after"]["longest_vertical_black_run"] < evidence["before"]["longest_vertical_black_run"]
    assert evidence["after"]["black_2x2_blocks"] < evidence["before"]["black_2x2_blocks"]
    assert evidence["invariants_passed"] is True
    assert evidence["method"] == "equal-weight-primary-outcome-dispersion-v3"
    for name in PRIMARY:
        assert _inventory(before[name]) == _inventory(after[name])
    for name in set(before) - set(PRIMARY):
        assert after[name] == before[name]
    assert _api("validate_primary_layout")(before, after)["passed"]


def test_primary_dispersion_is_deterministic_and_idempotent() -> None:
    disperse = _api("disperse_primary_layout")
    first, evidence = disperse(_clustered())
    assert disperse(_clustered()) == (first, evidence)
    second, again = disperse(first)
    assert second == first
    assert again["accepted_swaps"] == 0
    assert again["before"] == again["after"] == evidence["after"]


@pytest.mark.parametrize("token", ["BLACK", "4*", "QT", "F - 2"])
def test_unavoidable_or_minimal_layout_remains_unchanged(token: str) -> None:
    before = {name: dict.fromkeys(range(10, 40), token) for name in PRIMARY}
    after, evidence = _api("disperse_primary_layout")(before)
    assert after == before
    assert evidence["accepted_swaps"] == 0
    assert evidence["invariants_passed"] is True


@pytest.mark.parametrize("mutation", ["unequal_weight", "oob", "rare", "supplemental", "row", "column"])
def test_layout_invariant_rejects_probability_flags_and_dependency_corruption(mutation: str) -> None:
    before = _clustered()
    after = deepcopy(before)
    column = after["short_pass"]
    if mutation == "unequal_weight":
        column[19], column[39] = column[39], column[19]
    elif mutation == "oob":
        column[26] = "4"  # Numeric gain/class checks alone would miss this.
    elif mutation == "rare":
        column[31] = "4"
    elif mutation == "supplemental":
        after["qb_time"][10] = "0"
    elif mutation == "row":
        column[40] = column.pop(10)
    else:
        after.pop("long_pass")
    result = _api("validate_primary_layout")(before, after)
    assert result["passed"] is False
    assert result["errors"]


def test_layout_accepts_equal_weight_whole_token_permutation() -> None:
    before = _clustered()
    after = deepcopy(before)
    column = after["line_plunge"]
    column[14], column[27] = column[27], column[14]
    assert chart_roll_weights()[14] == chart_roll_weights()[27]
    assert _api("validate_primary_layout")(before, after)["passed"]


def test_generation_includes_primary_placement_evidence(tmp_path) -> None:
    stats = generator.TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Synthetic Layout", "short_name": "LAY",
        "offense": {"rushing": {"attempts": 100, "yards": 400},
                    "passing": {"attempts": 200, "completions": 120, "yards": 1400,
                                "interceptions": 4, "sacks": 10, "sack_yards": 60}},
    })
    generated = generator.generate_team_charts(stats, tmp_path / "Layout")
    evidence = getattr(generated, "primary_layout", None)
    assert isinstance(evidence, dict) and evidence.get("invariants_passed") is True
    assert evidence["method"] == "equal-weight-primary-outcome-dispersion-v3"


@pytest.mark.parametrize("penalties", [False, True])
@pytest.mark.parametrize("reallocation", [False, True])
def test_public_core_distributions_keep_flags_and_fresh_secondary_resolution(
    penalties: bool, reallocation: bool,
) -> None:
    from paydirt.chart_loader import load_team_chart
    from paydirt.play_resolver import (
        DefenseType,
        PlayType,
    )
    from tests.primary_distribution import primary_result_distribution

    public = Path(__file__).resolve().parents[1] / "seasons" / "2026"
    original = load_team_chart(public / "Ironclads")
    defender = load_team_chart(public / "Thunderhawks")
    before = {name: dict(getattr(original.offense, name)) for name in PRIMARY}
    before.update(qb_time=dict(original.offense.qb_time), breakaway=dict(original.offense.breakaway))
    allocated = _api("rebalance_primary_allocation")(before)[0] if reallocation else before
    after, _ = _api("disperse_primary_layout")(allocated)
    changed = deepcopy(original)
    for name in PRIMARY:
        setattr(changed.offense, name, after[name])
    for play in [*(PlayType(name) for name in PRIMARY), PlayType.QB_SNEAK]:
        for defense in DefenseType:
            distributions = [primary_result_distribution(chart, defender, play, defense, penalties)
                             for chart in (original, changed)]
            assert distributions[0] == distributions[1], (play, defense, penalties)


def _longest(cells: list[bool]) -> int:
    best = run = 0
    for selected in cells:
        run = run + 1 if selected else 0
        best = max(best, run)
    return best


@pytest.mark.parametrize("tokens,member", [
    (("OFF 5", "DEF 5"), "penalty"),
    (("1", "4"), "small_gain"),
    (("4*", "8†"), "sideline"),
    (("QT", "QT*"), "qb_time"),
    (("F - 2", "F + 2"), "fumble"),
    (("B", "B*"), "breakaway"),
])
def test_nonblack_families_disperse_as_whole_weighted_tokens(tokens, member) -> None:
    before = {name: {row: tokens[row % 2] if row < 18 else "20"
                     for row in range(10, 40)} for name in PRIMARY}
    # These are coupled lookups, not extra primary placement opportunities.
    before["qb_time"] = {row: f"SACK {row - 10}*" for row in range(10, 40)}
    before["fumble_return"] = {row: str(row - 10) for row in range(10, 40)}
    original = deepcopy(before)
    after, evidence = chart_layout.disperse_primary_layout(before)
    assert before == original
    assert evidence["accepted_swaps"] > 0, member
    before_run = max(_longest([value in tokens for value in before[name].values()])
                     for name in PRIMARY)
    after_run = max(_longest([after[name][row] in tokens for row in range(10, 40)])
                    for name in PRIMARY)
    assert after_run < before_run, member
    assert chart_layout.disperse_primary_layout(after)[0] == after
    for name in PRIMARY:
        assert _inventory(before[name]) == _inventory(after[name])
        # Exact joint mass with a fresh independent supplemental roll, including
        # every raw flag and dependent lookup value, not only marginal mean gain.
        def joint(layout: dict[str, dict[int, str]], column_name: str) -> Counter:
            return Counter({(weight, token, second, supplemental): count
                            for (weight, token), count in _inventory(layout[column_name]).items()
                            for second, supplemental in layout["qb_time"].items()})
        assert joint(before, name) == joint(after, name)
    assert after["qb_time"] == before["qb_time"]
    assert after["fumble_return"] == before["fumble_return"]


def test_general_placement_retains_black_priority_with_conflicting_family_clusters(monkeypatch) -> None:
    before = _clustered()
    black_only = []
    outcome_stage = chart_layout._disperse_outcomes

    def capture(columns, rows, pairs):
        black_only.append(deepcopy(columns))
        return outcome_stage(columns, rows, pairs)

    monkeypatch.setattr(chart_layout, "_disperse_outcomes", capture)
    after, evidence = chart_layout.disperse_primary_layout(before)
    assert black_only
    for name in PRIMARY:
        assert {row for row, token in after[name].items() if token == "BLACK"} == {
            row for row, token in black_only[0][name].items() if token == "BLACK"
        }
    assert tuple(evidence["after"].values()) <= tuple(evidence["before"].values())
    assert evidence["outcome_placement"]["after_cost"] <= evidence["outcome_placement"]["before_cost"]
    assert evidence["outcome_placement"]["features"]
    for name in PRIMARY:
        assert _inventory(after[name]) == _inventory(before[name])

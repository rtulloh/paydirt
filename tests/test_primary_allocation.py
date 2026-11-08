"""Exact-mass primary allocation must not freeze mixed families into light rows."""

from collections import Counter
from copy import deepcopy
from itertools import pairwise

import pytest

from paydirt import chart_generator as generator
from paydirt import chart_layout
from paydirt.play_resolver import chart_roll_weights

PASSING = chart_layout.PRIMARY_COLUMNS[4:]
WEIGHTS = chart_roll_weights()


def _mass(column: dict[int, str]) -> Counter:
    result = Counter()
    for row, token in column.items():
        result[token] += WEIGHTS[row]
    return result


def _longest(rows: list[int]) -> int:
    best = run = 0
    for row in WEIGHTS:
        run = run + 1 if row in rows else 0
        best = max(best, run)
    return best


def _stats() -> generator.TeamSeasonStats:
    return generator.TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Synthetic Allocation", "short_name": "ALL",
        "offense": {"rushing": {"attempts": 100, "yards": 400},
                    "passing": {"attempts": 200, "completions": 120, "yards": 1400,
                                "interceptions": 4, "sacks": 10, "sack_yards": 60}},
    })


def _fixture(monkeypatch, tokens: tuple[str, str], seed: int = 8306):
    stats = _stats()
    offense = generator._generate_offense(stats, seed)
    column = generator._empirical_column((tokens[0],) * 18 + (tokens[1],) * 19
                                         + ("4",) * 179, seed)
    for name in PASSING:
        offense[name] = dict(column)
    original = deepcopy(offense)
    monkeypatch.setattr(generator, "_generate_offense", lambda *args: deepcopy(original))
    return stats, original


@pytest.mark.parametrize("seed,expected", [(1, (18, 19)), (8306, (20, 17)), (2026, (18, 19))])
def test_mixed_qt_allocation_unlocks_pooled_family_without_probability_change(
    monkeypatch, tmp_path, seed: int, expected: tuple[int, int],
) -> None:
    stats, before = _fixture(monkeypatch, ("QT", "QT*"), seed)
    # Control: this is the actual quantized full-token target, not a new rate.
    assert _mass(before["screen"]) == {"QT": expected[0], "QT*": expected[1], "4": 179}
    assert [row for row in WEIGHTS if before["screen"][row].startswith("QT")] == [
        10, 11, 12, 13, 16, 17, 18, 19, 20, 28, 29, 39,
    ]
    generated = generator.generate_team_charts(stats, tmp_path / "Synthetic", seed=seed)
    for name in chart_layout.PRIMARY_COLUMNS:
        assert _mass(generated.offense[name]) == _mass(before[name])
    for name in set(before) - set(chart_layout.PRIMARY_COLUMNS):
        assert generated.offense[name] == before[name]
    masks = [[row for row in WEIGHTS if generated.offense[name][row].startswith("QT")]
             for name in PASSING]
    assert max(map(_longest, masks)) < 5
    assert all(len(rows) < 12 for rows in masks)
    assert len({tuple(rows) for rows in masks}) > 1
    allocation = generated.primary_layout["allocation"]
    assert allocation["invariants_passed"] is True
    assert allocation["accepted_exchanges"] > 0
    assert allocation["black_positions_fixed"] is True


@pytest.mark.parametrize("tokens", [
    ("B", "B*"), ("INT 5", "INT 12"), ("OFF 5", "DEF 5"),
    ("F - 2", "F + 2"), ("2*", "8*"), ("-1", "-2"),
])
def test_primary_allocation_handles_complete_tokens_and_other_families(
    monkeypatch, tmp_path, tokens: tuple[str, str],
) -> None:
    if tokens[0].startswith("INT"):
        # Multiple depths must declare source call attribution. An aggregate
        # baseline injecting these labels into every call is correctly invalid.
        samples = (tokens[0],) * 18 + (tokens[1],) * 19 + ("4",) * 179
        empirical = generator.EmpiricalChartData(offense={name: samples for name in PASSING})
        before: dict[str, dict[int, str]] = {}
        rebalance = generator.rebalance_primary_allocation

        def measured(offense: dict[str, dict[int, str]]) -> tuple:
            before.update(deepcopy(offense))
            return rebalance(offense)

        monkeypatch.setattr(generator, "rebalance_primary_allocation", measured)
        generated = generator.generate_team_charts(_stats(), tmp_path / "Synthetic", empirical=empirical)
        assert all(set(before[name].values()) == {*tokens, "4"} for name in PASSING)
    else:
        stats, before = _fixture(monkeypatch, tokens)
        generated = generator.generate_team_charts(stats, tmp_path / "Synthetic")
    for name in chart_layout.PRIMARY_COLUMNS:
        assert _mass(generated.offense[name]) == _mass(before[name])
    # Existing BLACK optimization has the same freedom and the same result.
    black_only, _ = chart_layout.disperse_primary_layout(before)
    for name in chart_layout.PRIMARY_COLUMNS:
        assert {row for row in WEIGHTS if generated.offense[name][row] == "BLACK"} == {
            row for row in WEIGHTS if black_only[name][row] == "BLACK"}
    for name in set(before) - set(chart_layout.PRIMARY_COLUMNS):
        assert generated.offense[name] == before[name]
    allocation = generated.primary_layout["allocation"]
    assert allocation["invariants_passed"] is True
    assert allocation["after_cost"] <= allocation["before_cost"]


def test_generator_rejects_undeclared_pooled_interception_depths(monkeypatch, tmp_path) -> None:
    stats, _before = _fixture(monkeypatch, ("INT 5", "INT 12"))
    with pytest.raises(ValueError, match="Invalid interception spot support in offense/screen"):
        generator.generate_team_charts(stats, tmp_path / "InvalidAggregate")


def test_uniform_primary_and_protected_dependencies_are_passing_controls(monkeypatch, tmp_path) -> None:
    stats, offense = _fixture(monkeypatch, ("QT", "QT*"))
    for name in chart_layout.PRIMARY_COLUMNS:
        offense[name] = dict.fromkeys(WEIGHTS, "4*")
    monkeypatch.setattr(generator, "_generate_offense", lambda *args: deepcopy(offense))
    generated = generator.generate_team_charts(stats, tmp_path / "Uniform")
    assert generated.offense == offense


def test_empirical_quantization_controls_keep_sparse_events_and_all_variants() -> None:
    outcomes = (("BLACK",) * 400 + ("QT",) * 26 + ("QT*",) * 26
                + ("OFF 5", "OFF 10", "DEF 5X", "PI 8") * 14 + ("4",) * 492)
    column = generator._empirical_column(outcomes, 8306)
    assert set(column) == set(WEIGHTS)
    assert set(column.values()) == set(outcomes)
    assert sum(mass for token, mass in _mass(column).items() if token.startswith("QT")) == 11


@pytest.mark.parametrize("token,color", [
    ("B*", "green"), ("TD", "green"), ("DS+", "green"), ("2†", "green"),
    ("INT 5", "red"), ("F + 2", "red"), ("-1*", "red"), ("SACK 0*", "red"),
    ("OFF 5", "yellow"), ("DEF 5X", "yellow"), ("PI 8", "yellow"),
    ("BLACK", "black"), ("INC", "black"), ("QT*", "neutral"), ("0", "neutral"),
])
def test_layout_explicitly_tracks_display_colors_apart_from_result_families(token, color) -> None:
    labels = chart_layout._outcome_features(token)
    assert "exact:" + token in labels
    assert any(label.startswith("family:") for label in labels)
    assert "color:" + color in labels


def _saturated(tokens: tuple[str, ...]) -> dict[str, dict[int, str]]:
    offense = {name: dict.fromkeys(WEIGHTS, "0") for name in chart_layout.PRIMARY_COLUMNS}
    for name in PASSING:
        for index, row in enumerate(row for row in WEIGHTS if WEIGHTS[row] <= 5):
            offense[name][row] = tokens[index % len(tokens)]
    offense["qb_time"] = {row: "F - 2" if row < 25 else "SACK 0*" for row in WEIGHTS}
    offense["breakaway"] = dict.fromkeys(WEIGHTS, "30*")
    offense["fumble_return"] = {row: str(row - 10) for row in WEIGHTS}
    return offense


def _geometry(offense, selected: tuple[str, ...]) -> tuple[int, int, int]:
    masks = [{row for row, token in offense[name].items() if token in selected} for name in PASSING]
    return (
        max(_longest(list(rows)) for rows in masks),
        sum(row in left & right and row + 1 in left & right
            for left, right in pairwise(masks) for row in range(10, 39)),
        sum(len(left & right) for left, right in pairwise(masks)),
    )


@pytest.mark.parametrize("tokens,label", [
    (("B", "B*"), "family:B"), (("QT", "QT*"), "family:QT"),
    (("INT 5", "INT 12"), "family:INT"), (("OFF 5", "DEF 5"), "color:yellow"),
    (("B*", "1", "TD"), "color:green"), (("F + 2", "-1", "INT 5"), "color:red"),
])
def test_saturated_families_and_color_unions_reduce_runs_blocks_and_row_repetition(tokens, label) -> None:
    before = _saturated(tokens)
    assert all(label in chart_layout._outcome_features(token) for token in tokens)
    assert _geometry(before, tokens) == (5, 32, 48)
    # The old layout invariant cannot alter these pooled masks at all.
    old_layout, _ = chart_layout.disperse_primary_layout(before)
    assert _geometry(old_layout, tokens) == (5, 32, 48)
    allocated, receipt = chart_layout.rebalance_primary_allocation(before)
    after, _ = chart_layout.disperse_primary_layout(allocated)
    run, blocks, aligned_pairs = _geometry(after, tokens)
    assert run < 5, label
    assert blocks < 32, label
    assert aligned_pairs < 48, label
    masks = {tuple(row for row in WEIGHTS if after[name][row] in tokens) for name in PASSING}
    assert len(masks) == len(PASSING), label
    assert receipt["accepted_exchanges"] > 0
    assert chart_layout.validate_primary_allocation(before, allocated)["passed"]
    assert chart_layout.validate_primary_layout(allocated, after)["passed"]
    for name in chart_layout.PRIMARY_COLUMNS:
        assert _mass(before[name]) == _mass(after[name])
    for name in set(before) - set(chart_layout.PRIMARY_COLUMNS):
        assert after[name] == before[name]


@pytest.mark.parametrize("token", ["BLACK", "QT*", "B*", "INT 5", "OFF 5", "4*", "F + 2"])
def test_allocation_uniform_categories_are_passing_controls_without_universal_run_caps(token) -> None:
    before = {name: dict.fromkeys(WEIGHTS, token) for name in chart_layout.PRIMARY_COLUMNS}
    after, receipt = chart_layout.rebalance_primary_allocation(before)
    assert after == before
    assert receipt["accepted_exchanges"] == 0


@pytest.mark.parametrize("mutation", ["mass", "flag", "black", "dependency", "row", "column"])
def test_allocation_validator_rejects_probability_and_dependency_corruption(mutation) -> None:
    before = _saturated(("QT", "QT*"))
    after = deepcopy(before)
    if mutation == "mass":
        after["screen"][10], after["screen"][34] = after["screen"][34], after["screen"][10]
    elif mutation == "flag":
        after["screen"][11] = "QT"
    elif mutation == "black":
        after["screen"][10] = "BLACK"
    elif mutation == "dependency":
        after["qb_time"][10] = "0"
    elif mutation == "row":
        after["screen"][40] = after["screen"].pop(10)
    else:
        after.pop("screen")
    result = chart_layout.validate_primary_allocation(before, after)
    assert result["passed"] is False
    assert result["errors"]


def test_high_frequency_green_run_respects_protected_black_constraint() -> None:
    before = {name: dict.fromkeys(WEIGHTS, "0") for name in chart_layout.PRIMARY_COLUMNS}
    before["draw"] = {row: "BLACK" if row in {13, 16, 25} else "B*" if row % 2 else "4"
                      for row in WEIGHTS}
    after, _ = chart_layout.rebalance_primary_allocation(before)
    def green(column):
        return [row for row, token in column.items()
                if chart_layout.chart_cell_color(token) == "green"]
    assert len(green(before["draw"])) == 27
    assert _longest(green(before["draw"])) == 14
    assert green(after["draw"]) == green(before["draw"])
    assert _mass(after["draw"]) == _mass(before["draw"])

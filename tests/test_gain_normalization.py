"""Synthetic contracts for the approved, unwired gain-normalization component."""
import importlib
import math
from copy import deepcopy
from types import ModuleType
from typing import Any

import pytest

from paydirt.chart_generator import supported_generated_cell
from paydirt.play_resolver import chart_roll_weights

RUNS = ("line_plunge", "off_tackle", "end_run", "draw")
PASSES = ("screen", "short_pass", "medium_pass", "long_pass", "te_short_long")
COLUMNS = (*RUNS, *PASSES, "breakaway", "qb_time")


def implementation() -> ModuleType:
    # Import within cases so existing fixture controls still run on the RED baseline.
    return importlib.import_module("paydirt.gain_normalization")


def offense() -> dict[str, dict[int, str]]:
    cells = {name: {row: "4" for row in chart_roll_weights()} for name in COLUMNS}
    cells["breakaway"] = {row: "20" for row in chart_roll_weights()}
    cells["qb_time"] = {row: "-5" for row in chart_roll_weights()}
    return cells


def baseline(
    module: ModuleType, n: int = 400, source_yards: int = 2400,
    engine_attempts: int = 800, engine_yards: int = 4800, supported: bool = True,
) -> Any:
    return module.GainBaseline(n, source_yards, engine_attempts, engine_yards, supported)


def objective(z: float, n: int, r: float, anchor: float) -> float:
    return n * (z - (r - anchor)) ** 2 + 200 * z ** 2


def cohort(module: ModuleType) -> dict[str, dict[str, Any]]:
    return {
        metric: {"A": baseline(module), "B": baseline(module)}
        for metric in ("passing", "rushing")
    }


def test_synthetic_offense_fixture_uses_only_supported_public_grammar() -> None:
    cells = offense()
    assert len(cells) == 11 and len(chart_roll_weights()) == 30
    assert sum(chart_roll_weights().values()) == 216
    assert all(supported_generated_cell("offense", name, token)
               for name, column in cells.items() for token in column.values())


def test_new_component_fixture_contains_no_private_season_input() -> None:
    assert set(offense()["breakaway"].values()) == {"20"}
    assert set(offense()["qb_time"].values()) == {"-5"}


def test_flat_cohort_derives_identity_for_both_metrics() -> None:
    m = implementation()
    inputs = cohort(m)
    before = deepcopy(inputs)
    result = m.derive_gain_normalization(("A", "B"), inputs)
    assert inputs == before
    assert result["pseudo_count"] == 200 and result["multiplier_bounds"] == [.8, 1.25]
    for metric in ("passing", "rushing"):
        assert result["metrics"][metric]["anchor"] == 0
        assert set(result["metrics"][metric]["teams"]) == {"A", "B"}
        assert all(row["multiplier"] == 1 for row in result["metrics"][metric]["teams"].values())


def test_pooled_counts_weighted_anchor_shrinkage_and_objective() -> None:
    m = implementation()
    data = cohort(m)
    data["passing"] = {
        "A": baseline(m, n=200, source_yards=1800, engine_attempts=400, engine_yards=2400),
        "B": baseline(m, n=600, source_yards=3600, engine_attempts=900, engine_yards=5400),
    }
    result = m.derive_gain_normalization(("A", "B"), data)
    anchor = math.log(1.5) / 4
    assert result["metrics"]["passing"]["anchor"] == pytest.approx(anchor)
    for name, n, r in (("A", 200, math.log(1.5)), ("B", 600, 0.0)):
        row = result["metrics"]["passing"]["teams"][name]
        expected_z = n / (n + 200) * (r - anchor)
        assert row["target"] == data["passing"][name].source_yards / n
        assert row["engine_mean"] == 6
        assert row["log_adjustment"] == pytest.approx(expected_z)
        assert row["multiplier"] == pytest.approx(math.exp(expected_z))
        assert objective(expected_z, n, r, anchor) < objective(expected_z - .001, n, r, anchor)
        assert objective(expected_z, n, r, anchor) < objective(expected_z + .001, n, r, anchor)
    assert all(row["multiplier"] == 1 for row in result["metrics"]["rushing"]["teams"].values())


def test_bounds_and_sparse_support_are_explicit() -> None:
    m = implementation()
    data = cohort(m)
    data["passing"] = {
        "A": baseline(m, n=400, source_yards=4000, engine_attempts=400, engine_yards=40),
        "B": baseline(m, n=400, source_yards=40, engine_attempts=400, engine_yards=4000),
    }
    rows = m.derive_gain_normalization(("A", "B"), data)["metrics"]["passing"]["teams"]
    assert rows["A"]["multiplier"] == pytest.approx(1.25)
    assert rows["B"]["multiplier"] == pytest.approx(.8)
    assert rows["A"]["clamped"] and rows["B"]["clamped"]
    data["passing"]["A"] = baseline(m, n=1, source_yards=9, engine_attempts=800, engine_yards=4800)
    rows = m.derive_gain_normalization(("A", "B"), data)["metrics"]["passing"]["teams"]
    assert abs(rows["A"]["unclamped_log_adjustment"]) < .1


def test_renaming_and_permutation_hold_underlying_inputs_fixed() -> None:
    m = implementation()
    data = cohort(m)
    data["passing"]["A"] = baseline(m, source_yards=3000)
    first = m.derive_gain_normalization(("A", "B"), data)
    renamed = {metric: {"zzz": values["A"], "aaa": values["B"]}
               for metric, values in data.items()}
    second = m.derive_gain_normalization(("aaa", "zzz"), renamed)
    for metric in data:
        assert first["metrics"][metric]["anchor"] == second["metrics"][metric]["anchor"]
        for old, new in (("A", "zzz"), ("B", "aaa")):
            assert first["metrics"][metric]["teams"][old] == second["metrics"][metric]["teams"][new]


@pytest.mark.parametrize("bad_cohort", [(), ("A", "A"), ("A",), ("A", "B", "C")])
def test_incomplete_empty_extra_or_duplicate_cohorts_are_rejected(bad_cohort: tuple[str, ...]) -> None:
    m = implementation()
    with pytest.raises(ValueError, match="cohort"):
        m.derive_gain_normalization(bad_cohort, cohort(m))


@pytest.mark.parametrize("field,value", [
    ("source_attempts", 0), ("source_attempts", -1), ("source_attempts", True),
    ("source_attempts", 1.5), ("source_yards", 0), ("source_yards", -5),
    ("source_yards", float("nan")), ("source_yards", float("inf")),
    ("engine_attempts", 0), ("engine_attempts", False), ("engine_attempts", 1.2),
    ("engine_yards", 0), ("engine_yards", -1), ("engine_yards", float("nan")),
    ("supported", False), ("supported", 1),
])
def test_missing_support_and_invalid_credited_counts_are_rejected(field: str, value: object) -> None:
    m = implementation()
    values: dict[str, Any] = {"source_attempts": 400, "source_yards": 2400,
                              "engine_attempts": 800, "engine_yards": 4800, "supported": True}
    values[field] = value
    data = cohort(m)
    data["passing"]["A"] = m.GainBaseline(**values)
    with pytest.raises(ValueError):
        m.derive_gain_normalization(("A", "B"), data)


def test_missing_metric_or_member_is_never_omitted() -> None:
    m = implementation()
    for kind in ("metric", "member"):
        data = cohort(m)
        if kind == "metric":
            del data["rushing"]
        else:
            del data["rushing"]["B"]
        with pytest.raises(ValueError):
            m.derive_gain_normalization(("A", "B"), data)


def test_transform_keeps_symbols_flags_zeroes_secondary_qt_and_input() -> None:
    m = implementation()
    cells = offense()
    protected = {10: "F INC", 11: "BLACK", 12: "QT*", 13: "F - 3",
                 14: "INT 17", 15: "PI 10", 16: "OFF 5", 17: "DEF 5", 18: "TD"}
    cells["short_pass"].update(protected)
    cells["line_plunge"].update({10: "F + 4", 11: "B*", 20: "17*", 21: "-3†", 22: "0"})
    cells["long_pass"].update({20: "98*", 21: "+3†"})
    original = deepcopy(cells)
    changed, report = m.transform_offense_gains(cells, passing_multiplier=1.25, rushing_multiplier=1.25)
    assert cells == original
    assert changed["qb_time"] == original["qb_time"]
    assert all(changed["short_pass"][row] == token for row, token in protected.items())
    assert changed["line_plunge"][10] == "F + 4" and changed["line_plunge"][11] == "B*"
    assert changed["line_plunge"][20] == "18*" and changed["line_plunge"][21] == "-4†"
    assert changed["line_plunge"][22] == "0"
    assert changed["long_pass"][20] == "99*" and changed["long_pass"][21] == "+4†"
    assert set(changed["breakaway"].values()) == {"25"}
    assert report["protected_mass_preserved"] is True
    assert report["rounding"] == "binary64-product / nearest-integer ties-to-even"
    effects = {(x["column"], x["row"]): x for x in report["effects"]}
    assert effects["line_plunge", 20]["capped"] and effects["long_pass", 20]["capped"]
    assert effects["line_plunge", 20]["weight"] == chart_roll_weights()[20]


@pytest.mark.parametrize("gain,expected", [("2", "2"), ("6", "8"), ("-2", "-2"), ("-6", "-8")])
def test_declared_ties_to_even_rounding(gain: str, expected: str) -> None:
    m = implementation()
    cells = offense()
    cells["medium_pass"][10] = gain
    changed, _ = m.transform_offense_gains(cells, passing_multiplier=1.25, rushing_multiplier=1)
    assert changed["medium_pass"][10] == expected


def test_identity_transform_preserves_every_byte_and_weighted_distribution() -> None:
    m = implementation()
    cells = offense()
    changed, report = m.transform_offense_gains(cells, passing_multiplier=1, rushing_multiplier=1)
    assert changed == cells
    assert report["effects"] == []
    for column in COLUMNS:
        data = report["columns"][column]
        assert data["before"] == data["after"]
        assert sum(data["before"]["token_masses"].values()) == 216


def test_transform_preserves_order_signs_and_reports_weighted_tails() -> None:
    m = implementation()
    cells = offense()
    cells["long_pass"].update({10: "-99", 11: "-2", 12: "0", 13: "1", 14: "19", 15: "49", 16: "99"})
    changed, report = m.transform_offense_gains(cells, passing_multiplier=.8, rushing_multiplier=.8)
    assert [int(changed["long_pass"][row]) for row in range(10, 17)] == sorted(
        int(changed["long_pass"][row]) for row in range(10, 17))
    assert changed["long_pass"][12] == "0" and int(changed["long_pass"][13]) > 0
    before = report["columns"]["long_pass"]["before"]
    after = report["columns"]["long_pass"]["after"]
    assert before["numeric_mass"] == after["numeric_mass"] == 216
    assert before["zero_share"] == after["zero_share"]
    assert before["loss_share"] == after["loss_share"]
    assert before["tail_40_share"] > after["tail_40_share"]
    assert set(before["quantiles"]) == {"0", ".1", ".25", ".5", ".75", ".9", ".99", "1"}


@pytest.mark.parametrize("factor", [0, -.8, .79, 1.26, float("inf"), float("nan"), True,
                                    pytest.param(10**1000, id="enormous-int")])
def test_invalid_or_out_of_approved_bound_multiplier_is_rejected(factor: float) -> None:
    m = implementation()
    with pytest.raises(ValueError):
        m.transform_offense_gains(offense(), passing_multiplier=factor, rushing_multiplier=1)


@pytest.mark.parametrize("column,token", [("line_plunge", "19"), ("draw", "-100"),
                                        ("long_pass", "100"), ("screen", "garbage")])
def test_invalid_baseline_is_rejected_instead_of_repaired(column: str, token: str) -> None:
    m = implementation()
    cells = offense()
    cells[column][10] = token
    original = deepcopy(cells)
    with pytest.raises(ValueError):
        m.transform_offense_gains(cells, passing_multiplier=.8, rushing_multiplier=.8)
    assert cells == original


def test_incomplete_columns_or_rows_are_rejected() -> None:
    m = implementation()
    for kind in ("column", "row"):
        cells = offense()
        if kind == "column":
            del cells["qb_time"]
        else:
            del cells["screen"][10]
        with pytest.raises(ValueError):
            m.transform_offense_gains(cells, passing_multiplier=1, rushing_multiplier=1)

@pytest.mark.parametrize("metric", ["passing", "rushing"])
@pytest.mark.parametrize("field,value", [("source_yards", 40000), ("engine_yards", 80000)])
def test_impossible_more_than_field_length_mean_is_rejected(metric: str, field: str, value: int) -> None:
    m = implementation()
    values: dict[str, Any] = {"source_attempts": 400, "source_yards": 2400,
                              "engine_attempts": 800, "engine_yards": 4800, "supported": True}
    values[field] = value
    data = cohort(m)
    data[metric]["A"] = m.GainBaseline(**values)
    with pytest.raises(ValueError, match="mean"):
        m.derive_gain_normalization(("A", "B"), data)


def verify_numeric_report(cells: dict[str, dict[int, str]], report: dict[str, Any]) -> None:
    # Independent physical-face expansion rather than the implementation's CDF counters.
    for name, column in cells.items():
        values = []
        for row, token in column.items():
            try:
                value = int(token.rstrip("*†"))
            except ValueError:
                continue
            values.extend([value] * chart_roll_weights()[row])
        values.sort()
        expected = report["columns"][name]["after"]
        assert expected["numeric_mass"] == len(values)
        if values:
            assert expected["numeric_mean"] == pytest.approx(sum(values) / len(values))
            assert expected["tail_20_share"] == sum(v >= 20 for v in values) / len(values)
            assert expected["tail_40_share"] == sum(v >= 40 for v in values) / len(values)
            assert expected["zero_share"] == values.count(0) / len(values)
            assert expected["loss_share"] == sum(v < 0 for v in values) / len(values)
            for q, result in expected["quantiles"].items():
                assert result == values[max(0, math.ceil(float(q) * len(values)) - 1)]


def test_independent_physical_numeric_cdf_and_warped_tail_mutant() -> None:
    m = implementation()
    cells = offense()
    cells["long_pass"].update({10: "-9", 11: "0", 12: "19", 13: "49", 14: "99"})
    changed, report = m.transform_offense_gains(cells, passing_multiplier=.8, rushing_multiplier=1.25)
    verify_numeric_report(changed, report)
    mutant = deepcopy(changed)
    mutant["long_pass"][15] = "99"
    with pytest.raises(AssertionError):
        verify_numeric_report(mutant, report)


def protected_signature(cells: dict[str, dict[int, str]]) -> dict[tuple[str, str], int]:
    signature: dict[tuple[str, str], int] = {}
    for name, column in cells.items():
        for row, token in column.items():
            try:
                number = int(token.rstrip("*†"))
            except ValueError:
                category = token
            else:
                flags = token[len(token.rstrip("*†")):]
                category = token if name == "qb_time" else (
                    "positive" if number > 0 else "negative" if number < 0 else "zero") + flags
            key = name, category
            signature[key] = signature.get(key, 0) + chart_roll_weights()[row]
    return signature


@pytest.mark.parametrize("replacement", ["F + 5", "0", "BLACK", "QT", "4*"])
def test_independent_protected_mass_control_rejects_mutants(replacement: str) -> None:
    m = implementation()
    cells = offense()
    cells["short_pass"][10] = "F + 4"
    cells["line_plunge"][11] = "B*"
    changed, _ = m.transform_offense_gains(cells, passing_multiplier=1.25, rushing_multiplier=.8)
    assert protected_signature(changed) == protected_signature(cells)
    changed["short_pass"][10] = replacement
    with pytest.raises(AssertionError):
        assert protected_signature(changed) == protected_signature(cells)


@pytest.mark.parametrize("name,sign", [("A", 1), ("B", -1)])
def test_each_clamped_solution_minimizes_objective_on_complete_feasible_grid(name: str, sign: int) -> None:
    m = implementation()
    data = cohort(m)
    data["passing"] = {
        "A": baseline(m, n=400, source_yards=4000, engine_attempts=400, engine_yards=40),
        "B": baseline(m, n=400, source_yards=40, engine_attempts=400, engine_yards=4000),
    }
    selected = m.derive_gain_normalization(("A", "B"), data)["metrics"]["passing"]["teams"][name]
    # Reciprocal ratios and equal source counts fix the independent anchor at zero.
    r = sign * math.log(100)
    lower, upper = math.log(.8), math.log(1.25)
    z = selected["log_adjustment"]
    assert z == pytest.approx(upper if sign > 0 else lower)
    assert sign * selected["unclamped_log_adjustment"] > max(abs(lower), abs(upper))
    optimum = objective(z, 400, r, 0)
    for tick in range(1001):
        feasible_z = lower + (upper - lower) * tick / 1000
        assert optimum <= objective(feasible_z, 400, r, 0) + 1e-10

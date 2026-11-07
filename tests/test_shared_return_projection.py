"""One shared column jointly allocates terminal risk and scoped gains."""

import importlib
from fractions import Fraction

import pytest

from paydirt.play_resolver import chart_roll_weights


def project(**changes):
    values = {
        "interception_outcomes": {"int-1": "F + 40", "int-2": "0", "int-3": "8"},
        "shared_fumble_outcomes": {"int-1": "F + 40", "recovery-1": "F + 2"},
        "shared_fumble_losses": {"int-1": False, "recovery-1": True},
        "terminal_exposures": 8,
        "baseline_column": {roll: "0" for roll in chart_roll_weights()}, "seed": 8306,
    }
    values.update(changes)
    return importlib.import_module("paydirt.chart_generator").project_shared_return_column(**values)


def test_interception_f_subset_is_allocated_once_with_scoped_gain_variants() -> None:
    column, receipt = project()
    weights = chart_roll_weights()
    f_mass = sum(weights[r] for r, cell in column.items() if cell.startswith("F"))
    assert f_mass == 54
    assert receipt["source_shared_fumbles"] == 2
    assert receipt["interception_fumble_subset"] == 1
    assert receipt["requested_nonfoul_f_probability"] == .25
    assert receipt["physical_nonfoul_f_probability"] == .25
    assert receipt["source_fumble_gains"] == [2, 40]
    assert receipt["conditional_nonfoul_gain_target"] is None
    assert receipt["physical_initial_gains_verified"] is False
    assert set(column.values()) == {"F + 2", "F + 40", "0", "8"}


def test_penalties_and_f_gains_are_quantized_together_once() -> None:
    weights = chart_roll_weights()
    baseline = {r: "OFF 15" if r < 20 else "0" for r in weights}
    column, receipt = project(baseline_column=baseline)
    penalty = sum(weights[r] for r, cell in column.items() if cell == "OFF 15")
    f_mass = sum(weights[r] for r, cell in column.items() if cell.startswith("F"))
    assert penalty == 36
    assert abs(f_mass - 180 * .25) <= 1
    assert set(column) == set(weights)
    assert receipt["requested_penalty_probability"] == 1 / 6
    assert receipt["ordinary_int_gains"] == [0, 8]


def test_zero_source_events_and_zero_exposure_is_explicit_zero_risk() -> None:
    column, receipt = project(interception_outcomes={"i": "0"},
                              shared_fumble_outcomes={}, shared_fumble_losses={},
                              terminal_exposures=0)
    assert set(column.values()) == {"0"}
    assert receipt["requested_nonfoul_f_probability"] == 0


def test_fractional_per_season_exposure_has_no_pseudo_sample_rounding() -> None:
    _, receipt = project(terminal_exposures=Fraction(25, 3))
    assert receipt["requested_nonfoul_f_probability"] == pytest.approx(6 / 25)


def test_probability_one_requires_no_fabricated_ordinary_observation() -> None:
    column, receipt = project(interception_outcomes={"i": "F + 2"},
                              shared_fumble_outcomes={"i": "F + 2"},
                              shared_fumble_losses={"i": False}, terminal_exposures=1)
    assert set(column.values()) == {"F + 2"}
    assert receipt["ordinary_int_gains"] == []
    assert receipt["physical_nonfoul_f_probability"] == 1


def test_unknown_baseline_symbol_does_not_disappear_into_penalty_prior() -> None:
    with pytest.raises(ValueError):
        project(baseline_column={roll: "UNKNOWN" for roll in chart_roll_weights()})


def test_scoped_shared_return_gains_preserve_endzone_length_without_primary_caps() -> None:
    column, receipt = project(
        interception_outcomes={"i": "100", "j": "F + 102"},
        shared_fumble_outcomes={"j": "F + 102"}, shared_fumble_losses={"j": False},
        terminal_exposures=2,
    )
    assert set(column.values()) == {"100", "F + 102"}
    assert receipt["source_fumble_gains"] == [102]
    assert receipt["ordinary_int_gains"] == [100]


def test_all_supported_return_foul_variants_retain_their_requested_mass() -> None:
    weights = chart_roll_weights()
    baseline = {r: "OFF S" if r < 20 else "DEF 5X" if r < 25 else "0" for r in weights}
    column, receipt = project(baseline_column=baseline)
    expected = sum(weights[r] for r, cell in baseline.items() if cell != "0")
    actual = sum(weights[r] for r, cell in column.items() if cell.startswith(("OFF", "DEF")))
    assert abs(actual - expected) <= 1
    assert receipt["requested_penalty_probability"] == expected / 216
    assert {cell for cell in column.values() if cell.startswith(("OFF", "DEF"))} == {"OFF S", "DEF 5X"}


@pytest.mark.parametrize("changes", [
    {"terminal_exposures": 0}, {"terminal_exposures": 1},
    {"terminal_exposures": -1}, {"terminal_exposures": float("nan")},
    {"terminal_exposures": True},
    {"shared_fumble_outcomes": {"recovery-1": "F + 2"}},
    {"shared_fumble_outcomes": {"int-1": "F + 4"}},
    {"shared_fumble_outcomes": {"int-1": "F + 40", "recovery-1": None}},
    {"shared_fumble_outcomes": {"int-1": "F + 40", "recovery-1": "F INC"}},
    {"interception_outcomes": {"i": "BLACK"}},
    {"interception_outcomes": {"i": "F + 40"}, "shared_fumble_outcomes": {"i": "F + 40"}},
    {"interception_outcomes": {"": "0"}},
    {"baseline_column": {10: "0"}},
    {"shared_fumble_losses": {"int-1": False, "recovery-1": None}},
    {"shared_fumble_losses": {}},
])
def test_missing_incompatible_or_untyped_support_blocks_projection(changes: dict) -> None:
    with pytest.raises(ValueError):
        project(**changes)


def test_input_mapping_order_does_not_change_projection() -> None:
    first = project()
    second = project(interception_outcomes={"int-3": "8", "int-2": "0", "int-1": "F + 40"},
                     shared_fumble_outcomes={"recovery-1": "F + 2", "int-1": "F + 40"})
    assert first == second

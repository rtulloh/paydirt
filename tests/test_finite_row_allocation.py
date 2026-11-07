"""Finite-row selection compares attainable masses to the unrounded target."""

import pytest

from paydirt.chart_generator import _empirical_column, _nearest_roll_mass
from paydirt.play_resolver import chart_roll_weights


@pytest.mark.parametrize("rate,candidates,expected", [
    (.005, (10,), {10}),  # 1.08 physical units: 2 is closer than 0.
    (1 / 216, (10,), set()),  # Exact tie chooses smaller mass.
    (0, (10, 11), set()),
    (1, (10, 11), {10, 11}),  # Saturates available physical mass.
    (.5, (), set()),
    (.015, (10, 11), {11}),
])
def test_nearest_selection_uses_actual_requested_probability(
    rate: float, candidates: tuple[int, ...], expected: set[int],
) -> None:
    assert _nearest_roll_mass(rate, candidates) == expected


@pytest.mark.parametrize("seed", [8306, 9241, 11713])
def test_sparse_empirical_event_uses_closer_attainable_row(seed: int) -> None:
    outcomes = ("BLACK",) * 300 + ("QT",) * 50 + ("INT 5",) * 5 + ("4",) * 645
    column = _empirical_column(outcomes, seed)
    weights = chart_roll_weights()
    mass = sum(weights[roll] for roll, value in column.items() if value == "INT 5")
    # Compact equal-mass earlier allocations leave the 1/216 row available.
    # It is closer to 1.08 than either zero or two physical units.
    assert mass == 1
    assert set(column) == set(weights)
    assert set(column.values()) <= set(outcomes)


@pytest.mark.parametrize("seed", [8306, 9241, 11713])
def test_qt_variants_share_one_finite_pressure_allocation(seed: int) -> None:
    outcomes = ("BLACK",) * 400 + ("QT",) * 26 + ("QT*",) * 26 + ("4",) * 548
    column = _empirical_column(outcomes, seed)
    weights = chart_roll_weights()
    mass = sum(weights[roll] for roll, value in column.items() if value.startswith("QT"))
    assert mass == 11  # 52 / 1000 * 216 = 11.232; 11 is attainable.
    assert {value for value in column.values() if value.startswith("QT")} == {"QT", "QT*"}


def test_attainable_penalty_variants_survive_shared_family_allocation() -> None:
    outcomes = (("BLACK",) * 400 + ("QT",) * 26 + ("QT*",) * 26
                + ("OFF 5", "OFF 10", "DEF 5X", "PI 8") * 14 + ("4",) * 492)
    column = _empirical_column(outcomes, 8306)
    penalties = {cell for cell in column.values() if cell.startswith(("OFF", "DEF", "PI"))}
    assert penalties == {"OFF 5", "OFF 10", "DEF 5X", "PI 8"}
    weights = chart_roll_weights()
    assert sum(weights[roll] for roll, cell in column.items() if cell in penalties) == 12


def test_equal_mass_selection_preserves_rows_for_later_event_families() -> None:
    weights = chart_roll_weights()
    chosen = _nearest_roll_mass(.4, tuple(weights))
    assert sum(weights[roll] for roll in chosen) == 86
    # Six rows cannot total 86: their maximum is 87 with the sole odd 15;
    # excluding it reduces the maximum to 84. Seven rows can attain 86.
    assert len(chosen) == 7

"""Synthetic controls for the release chart-allocation audit."""

from paydirt.chart_allocation_gate import audit_allocations, check_symbolic_allocation
from paydirt.play_resolver import chart_roll_weights


def _column() -> dict[int, str]:
    return {roll: "10" for roll in chart_roll_weights()}


def test_valid_allocation_and_preserved_control_pass() -> None:
    before = _column()
    before[19] = "BLACK"
    after = dict(before)
    after[11] = "QT"
    assert check_symbolic_allocation(before, after, 3 / 216, ("QT",)) == []


def test_gate_rejects_event_displacement_even_when_requested_mass_is_correct() -> None:
    before = _column()
    before[19] = "BLACK"
    after = dict(before)
    after[19] = "QT"
    errors = check_symbolic_allocation(before, after, 1 / 216, ("QT",))
    assert any("protected result" in error for error in errors)


def test_gate_rejects_bad_probability_when_closer_physical_mass_exists() -> None:
    before = _column()
    after = dict(before)
    after[10] = "QT"
    errors = check_symbolic_allocation(before, after, 3 / 216, ("QT",))
    assert any("nearest attainable" in error for error in errors)


def test_gate_accepts_nearest_attainable_mass_without_arbitrary_tolerance() -> None:
    before = {roll: "BLACK" for roll in chart_roll_weights()}
    before[10] = "10"  # Only 2/216 remains available.
    after = dict(before)
    after[10] = "QT"
    assert check_symbolic_allocation(before, after, 3 / 216, ("QT",)) == []


def test_minimum_one_accepts_declared_rare_event_quantization() -> None:
    before = _column()
    after = dict(before)
    after[19] = "BK -7"
    assert check_symbolic_allocation(
        before, after, .0001, ("BK -7",), minimum_one=True
    ) == []
    errors = check_symbolic_allocation(before, after, .0001, ("BK -7",))
    assert any("nearest attainable" in error for error in errors)


def test_gate_rejects_unknown_replacement_and_missing_physical_rows() -> None:
    before = _column()
    after = dict(before)
    after[11] = "INT 5"
    after.pop(10)
    errors = check_symbolic_allocation(before, after, 3 / 216, ("QT",))
    assert any("physical rows" in error for error in errors)
    assert any("unexpected replacement" in error for error in errors)


def test_audit_accepts_corrected_final_sparse_empirical_probability() -> None:
    report = audit_allocations(seeds=(8306,))
    assert report["checks"] > 100
    assert report["passed"], report["errors"]
    assert not report["errors"]


def test_corrected_sparse_selection_is_a_passing_control(monkeypatch) -> None:
    from paydirt import chart_generator

    original = chart_generator._nearest_roll_mass
    weights = chart_roll_weights()

    def use_closer_single_row(rate, candidates):
        selected = original(rate, candidates)
        if not candidates:
            return selected
        target = rate * sum(weights.values())
        nearest_single = min(candidates, key=lambda roll: abs(weights[roll] - target))
        selected_error = abs(sum(weights[roll] for roll in selected) - target)
        if abs(weights[nearest_single] - target) < selected_error:
            return {nearest_single}
        return selected

    monkeypatch.setattr(chart_generator, "_nearest_roll_mass", use_closer_single_row)
    report = audit_allocations(seeds=(8306,))
    assert report["passed"], report["errors"]


def test_gate_detects_corrupt_allocator_in_actual_generation(monkeypatch) -> None:
    from paydirt import chart_generator

    original = chart_generator._replace_rate

    def broken(column, rate, values, rng, minimum_one=False):
        original(column, rate, values, rng, minimum_one=minimum_one)
        if any(value.startswith("INT") for value in column.values()):
            for roll, value in column.items():
                if value.startswith("INT"):
                    column[roll] = "BLACK"
                    break

    monkeypatch.setattr(chart_generator, "_replace_rate", broken)
    report = audit_allocations(seeds=(8306,))
    assert not report["passed"]
    assert any("protected result" in error or "nearest attainable" in error
               for error in report["errors"])


def test_gate_detects_symbol_erased_after_final_allocation(monkeypatch) -> None:
    from paydirt import chart_generator

    original = chart_generator._adjust_numeric_mean

    def broken(column, target, minimum):
        original(column, target, minimum)
        for roll, cell in column.items():
            if cell == "BLACK":
                column[roll] = "10"
                break

    monkeypatch.setattr(chart_generator, "_adjust_numeric_mean", broken)
    report = audit_allocations(seeds=(8306,))
    assert not report["passed"]
    assert any("post-allocation transformation" in error for error in report["errors"])


def test_gate_rejects_invalid_targets_and_empty_sampling_plan() -> None:
    import pytest

    for target in (-.1, 1.1, float("nan")):
        assert check_symbolic_allocation(_column(), _column(), target, ("QT",))
    with pytest.raises(ValueError, match="at least one seed"):
        audit_allocations(seeds=())

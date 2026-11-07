"""Synthetic contracts for the generated-defense release gate."""

from fractions import Fraction
from types import SimpleNamespace

import pytest

from paydirt.chart_generator import _generate_defense
from paydirt.chart_loader import DefenseChart
from paydirt.chart_tactics_audit import (
    audit_defense_tactics,
    audit_engine_controls,
    audit_generated_strength_order,
    audit_priority_resolution,
    audit_strength_order,
    controlled_offense,
    resolved_outcome_distribution,
)
from paydirt.play_resolver import DefenseType, PlayType


@pytest.fixture
def tactical_defense() -> DefenseChart:
    passing = SimpleNamespace(average=7.2, attempts=1000, sacks=65, interceptions=25)
    stats = SimpleNamespace(
        defense=SimpleNamespace(
            rushing=SimpleNamespace(average=4.1),
            passing=passing,
        )
    )
    return DefenseChart(_generate_defense(stats))


def test_nonzero_template_retains_formation_benefits_and_costs(tactical_defense):
    result = audit_defense_tactics(tactical_defense)
    assert result.passed, result.findings
    assert len(result.contrasts) == 27
    assert all(value >= 2 for value in result.contrasts.values())


def test_weight_equivalent_rearranged_formations_are_rejected():
    # Row1 has mass12, and rows2+5 have mass11+1. The six printed formations
    # differ, but every column has exactly the same weighted distribution.
    rows = {}
    for index, formation in enumerate("ABCDEF", 1):
        for subrow in range(1, 6):
            rows[(formation, subrow)] = {
                column: (
                    "1" if subrow in ((1,) if index & (1 << (column % 3)) else (2, 5)) else "0"
                )
                for column in range(1, 10)
            }
    printed = {tuple(tuple(rows[(f, s)].items()) for s in range(1, 6)) for f in "ABCDEF"}
    assert len(printed) == 6
    result = audit_defense_tactics(DefenseChart(rows))
    assert not result.passed
    assert any(f.code == "formation_contrast" for f in result.findings)
    assert any(f.code == "tactical_tradeoff" for f in result.findings)


def test_missing_short_yardage_cost_is_rejected(tactical_defense):
    # Preserve its line-plunge benefit but erase the draw vulnerability.
    for subrow in range(1, 6):
        tactical_defense.modifiers[("B", subrow)][4] = "-10"
    result = audit_defense_tactics(tactical_defense)
    assert not result.passed
    assert any(
        f.code == "tactical_tradeoff" and f.contract == "short_yardage_draw_cost"
        for f in result.findings
    )


def test_protected_offense_is_allowed_to_erase_formation_contrast(tactical_defense):
    offense = controlled_offense("(7)")
    outcomes = [
        resolved_outcome_distribution(offense, tactical_defense, PlayType.LINE_PLUNGE, f)
        for f in DefenseType
    ]
    assert all(distribution == outcomes[0] for distribution in outcomes)
    assert {(out.kind, out.yards) for out in outcomes[0]} == {("yards", 7)}
    assert audit_defense_tactics(tactical_defense).passed


@pytest.mark.parametrize(
    ("token", "expected_kind", "expected_yards"),
    [
        ("B", "breakaway", 25),
        ("QT", "sack", -6),
    ],
)
def test_secondary_columns_use_core_resolution(
    tactical_defense, token, expected_kind, expected_yards
):
    distribution = resolved_outcome_distribution(
        controlled_offense(token), tactical_defense, PlayType.LINE_PLUNGE, DefenseType.STANDARD
    )
    assert sum(distribution.values()) == 1
    assert {(out.kind, out.yards, mass) for out, mass in distribution.items()} == {
        (expected_kind, expected_yards, Fraction(1))
    }


def test_mixed_secondary_rolls_use_actual_216_face_weights(tactical_defense):
    offense = controlled_offense("QT")
    offense.offense.qb_time = {row: "-6" if row == 10 else "4" for row in range(10, 40)}
    distribution = resolved_outcome_distribution(
        offense, tactical_defense, PlayType.LINE_PLUNGE, DefenseType.STANDARD
    )
    assert {(out.kind, out.yards, mass) for out, mass in distribution.items()} == {
        ("sack", -6, Fraction(2, 216)),
        ("qb_scramble", 4, Fraction(214, 216)),
    }


@pytest.mark.parametrize("token", ["F + 2", "OFF 5", "PI 13"])
def test_unknown_recovery_or_penalty_choice_is_not_zero_gain(tactical_defense, token):
    distribution = resolved_outcome_distribution(
        controlled_offense(token), tactical_defense, PlayType.LINE_PLUNGE, DefenseType.STANDARD
    )
    assert sum(distribution.values()) == 1
    assert all(out.pending and out.yards is None for out in distribution)


def test_engine_entry_point_matches_chart_resolution(tactical_defense):
    assert audit_engine_controls(tactical_defense).passed


def test_engine_state_application_drift_is_rejected(tactical_defense, monkeypatch):
    from paydirt.game_engine import PaydirtGameEngine

    original = PaydirtGameEngine.run_play_with_penalty_procedure

    def changed_gain(self, *args, **kwargs):
        outcome = original(self, *args, **kwargs)
        outcome.yards_gained += 1
        return outcome

    monkeypatch.setattr(PaydirtGameEngine, "run_play_with_penalty_procedure", changed_gain)
    result = audit_engine_controls(tactical_defense)
    assert not result.passed
    assert any(f.code == "engine_resolution" for f in result.findings)


def test_low_gain_spread_screen_exception_is_visible(tactical_defense):
    result = audit_defense_tactics(tactical_defense)
    assert any(
        f.contract == "spread_screen_benefit" and f.message.startswith("4:")
        for f in result.diagnostics
    )
    assert result.contracts["4:spread_screen_benefit"] == {
        "standard": "17/6",
        "specialized": "26/9",
    }


def test_selected_fumble_displacement_is_reported_by_release_gate(monkeypatch):
    from paydirt import play_resolver

    original = play_resolver.resolve_play_with_penalties

    def displaced_fumble(*args, **kwargs):
        choice = original(*args, **kwargs)
        choice.play_result.result_type = play_resolver.ResultType.INTERCEPTION
        return choice

    monkeypatch.setattr(play_resolver, "resolve_play_with_penalties", displaced_fumble)
    result = audit_priority_resolution()
    assert not result.passed
    assert any(f.code == "priority_resolution" for f in result.findings)


def test_priority_gate_accepts_correctly_classified_fumbles(monkeypatch):
    from paydirt import play_resolver

    def corrected(function):
        def wrapped(*args, **kwargs):
            output = function(*args, **kwargs)
            result = output.play_result if hasattr(output, "play_result") else output
            result.result_type = play_resolver.ResultType.FUMBLE
            return output

        return wrapped

    monkeypatch.setattr(
        play_resolver,
        "resolve_play_with_penalties",
        corrected(play_resolver.resolve_play_with_penalties),
    )
    monkeypatch.setattr(play_resolver, "resolve_play", corrected(play_resolver.resolve_play))
    from paydirt import game_engine

    # The engine imports this callable by name, so patch its bound reference too.
    monkeypatch.setattr(
        game_engine, "resolve_play_with_penalties", play_resolver.resolve_play_with_penalties
    )
    assert audit_priority_resolution().passed


def test_distribution_uses_selected_fumble_before_enumerating_recovery():
    from fractions import Fraction

    from paydirt.chart_tactics_audit import controlled_offense

    offense = controlled_offense("F + 2")
    defender = DefenseChart({("A", row): dict.fromkeys(range(1, 10), "INT 5")
                             for row in range(1, 6)})
    distribution = resolved_outcome_distribution(
        offense, defender, PlayType.SHORT_PASS, DefenseType.STANDARD,
    )
    assert sum(distribution.values()) == Fraction(1)
    assert all(outcome.kind == "pending_fumble" for outcome in distribution)
    assert all(outcome.yards is None and outcome.pending for outcome in distribution)


def test_declared_strength_order_is_checked_after_resolution():
    def defense(run_average, pass_average):
        passing = SimpleNamespace(average=pass_average, attempts=1000, sacks=65, interceptions=25)
        stats = SimpleNamespace(
            defense=SimpleNamespace(
                rushing=SimpleNamespace(average=run_average),
                passing=passing,
            )
        )
        return DefenseChart(_generate_defense(stats))

    strong = defense(3.3, 5.5)
    weak = defense(5.0, 8.5)
    assert audit_strength_order(strong, weak).passed
    reversed_order = audit_strength_order(weak, strong)
    assert not reversed_order.passed
    assert any(f.code == "strength_order" for f in reversed_order.findings)


def test_generated_strength_gate_accepts_controlled_source_profiles():
    assert audit_generated_strength_order().passed


def test_generator_mutant_erasing_team_strength_is_rejected(tactical_defense, monkeypatch):
    from copy import deepcopy

    from paydirt import chart_generator

    monkeypatch.setattr(
        chart_generator, "_generate_defense", lambda stats: deepcopy(tactical_defense.modifiers)
    )
    result = audit_generated_strength_order()
    assert not result.passed
    assert any(f.code == "strength_order" for f in result.findings)


def test_offense_interception_strength_is_ordered_against_the_same_defense():
    import paydirt.chart_tactics_audit as audit
    check = getattr(audit, "audit_generated_offense_risk_order", lambda *_: audit.TacticalAuditResult())
    result = check()
    assert result.passed, result.findings
    assert len(result.contracts) == 30


def test_erased_offense_interception_strength_is_rejected():
    import paydirt.chart_tactics_audit as audit
    from paydirt.chart_generator import EmpiricalPassCalibration

    check = getattr(audit, "audit_generated_offense_risk_order", lambda *_: audit.TacticalAuditResult())
    result = check(EmpiricalPassCalibration(
        interception_rate_adjustment=-.10,
    ))
    assert not result.passed
    assert all("interception" in finding.message for finding in result.findings)


def test_offense_risk_control_discloses_complete_protected_screen_overrides():
    import paydirt.chart_tactics_audit as audit
    check = getattr(audit, "audit_generated_offense_risk_order", lambda *_: audit.TacticalAuditResult())
    result = check()
    for formation in ("B", "F"):
        evidence = result.contracts.get(f"screen/{formation}", {})
        assert evidence.get("protected_override") == "true"
        assert evidence["low"] == evidence["neutral"] == evidence["high"] == "0.0"

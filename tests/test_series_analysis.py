"""Exact diagnostic mathematics; no historical chart fixtures or AI wiring."""

from fractions import Fraction as F
from importlib import import_module

import pytest


def api():
    """Import during each test so missing new API is an explicit RED failure."""
    return import_module("paydirt.series_analysis")


def node(prior, outcomes):
    return api().SeriesNode(prior, outcomes)


def branch(mass=F(1), *, success=None, successor=None):
    return api().SeriesOutcome(mass, success=success, successor=successor)


def test_existing_released_strategy_control():
    from paydirt.offense_strategy import situation_key

    assert situation_key(1, 10) != situation_key(3, 10)
    assert situation_key(3, 3) != situation_key(3, 10)


def test_success_failure_and_unknown_keep_full_mass():
    root = node(
        {"pass": F(1)},
        {
            "pass": {
                "standard": (
                    branch(F(4, 5), success=True),
                    branch(F(1, 10), success=False),
                    branch(F(1, 10)),
                )
            }
        },
    )
    result = api().evaluate_series("root", lambda _: root)
    assert result.baseline == api().ProbabilityInterval(F(4, 5), F(9, 10))
    assert result.action_bounds["pass"] == result.baseline
    assert result.unknown_reasons == {"explicit": 1}


def test_remaining_down_values_use_baseline_future_not_best_future():
    nodes = {
        "root": node(
            {"safe": F(1), "gamble": F(1)},
            {
                "safe": {"standard": (branch(successor="second"),)},
                "gamble": {
                    "standard": (branch(F(1, 2), success=True), branch(F(1, 2), success=False))
                },
            },
        ),
        "second": node(
            {"good": F(1), "bad": F(3)},
            {
                "good": {"standard": (branch(success=True),)},
                "bad": {"standard": (branch(success=False),)},
            },
        ),
    }
    result = api().evaluate_series("root", nodes.__getitem__)
    assert result.action_bounds["safe"] == api().ProbabilityInterval(F(1, 4), F(1, 4))
    assert result.action_bounds["gamble"] == api().ProbabilityInterval(F(1, 2), F(1, 2))
    assert result.baseline == api().ProbabilityInterval(F(3, 8), F(3, 8))


def test_all_formations_are_bounded_without_a_hidden_selected_formation():
    root = node(
        {"pass": F(1)},
        {
            "pass": {
                "run": (branch(success=True),),
                "pass": (branch(success=False),),
            }
        },
    )
    result = api().evaluate_series("root", lambda _: root)
    assert result.baseline == api().ProbabilityInterval(F(0), F(1))


def test_full_state_identity_keeps_histories_and_phases_distinct():
    # Same down/field position is insufficient: revealed history and phase differ.
    first = (2, 40, ("screen",), "ordinary")
    second = (2, 40, ("long_pass",), "ordinary")
    third = (2, 40, ("screen",), "pending_penalty")
    nodes = {
        "root": node(
            {"pass": F(1)},
            {
                "pass": {
                    "standard": (
                        branch(F(1, 3), successor=first),
                        branch(F(1, 3), successor=second),
                        branch(F(1, 3), successor=third),
                    )
                }
            },
        )
    }
    for state, success in [(first, True), (second, False), (third, None)]:
        nodes[state] = node({"pass": F(1)}, {"pass": {"standard": (branch(success=success),)}})
    result = api().evaluate_series("root", nodes.__getitem__)
    assert result.baseline == api().ProbabilityInterval(F(1, 3), F(2, 3))
    assert result.expanded_nodes == 4


def test_cycles_and_node_or_depth_limits_remain_unknown():
    root = node(
        {"pass": F(1)},
        {
            "pass": {
                "standard": (
                    branch(F(1, 2), success=True),
                    branch(F(1, 2), successor="root"),
                )
            }
        },
    )
    result = api().evaluate_series("root", lambda _: root)
    assert result.baseline == api().ProbabilityInterval(F(1, 2), F(1))
    assert result.unknown_reasons == {"cycle": 1}
    def chain(state):
        return node({"pass": F(1)}, {"pass": {"standard": (branch(successor=state + 1),)}})
    limited = api().evaluate_series(0, chain, max_nodes=2)
    assert limited.expanded_nodes == 2
    assert limited.baseline == api().ProbabilityInterval(F(0), F(1))
    assert limited.unknown_reasons == {"node_limit": 1}
    depth = api().evaluate_series(0, chain, max_depth=1)
    assert depth.expanded_nodes == 1
    assert depth.unknown_reasons == {"depth_limit": 1}


@pytest.mark.parametrize("masses", [(F(1, 2),), (F(3, 4), F(3, 4)), (F(-1), F(2))])
def test_invalid_physical_mass_is_rejected_instead_of_renormalized(masses):
    root = node(
        {"pass": F(1)}, {"pass": {"standard": tuple(branch(mass, success=True) for mass in masses)}}
    )
    with pytest.raises(ValueError, match="probability|mass"):
        api().evaluate_series("root", lambda _: root)


@pytest.mark.parametrize("prior", [{"pass": F(0)}, {"pass": F(-1)}, {"pass": float("nan")}])
def test_invalid_prior_rejected(prior):
    root = node(prior, {"pass": {"standard": (branch(success=True),)}})
    with pytest.raises(ValueError, match="weight"):
        api().evaluate_series("root", lambda _: root)


def test_missing_action_or_formation_coverage_is_rejected():
    root = node(
        {"pass": F(1), "run": F(1)},
        {
            "pass": {"standard": (branch(success=True),)},
            "run": {"blitz": (branch(success=True),)},
        },
    )
    with pytest.raises(ValueError, match="formation"):
        api().evaluate_series("root", lambda _: root)
    missing = node(
        {"pass": F(1), "run": F(1)},
        {
            "pass": {"standard": (branch(success=True),)},
        },
    )
    with pytest.raises(ValueError, match="action"):
        api().evaluate_series("root", lambda _: missing)


def test_ambiguous_terminal_and_successor_is_rejected():
    root = node(
        {"pass": F(1)}, {"pass": {"standard": (branch(success=True, successor="another"),)}}
    )
    with pytest.raises(ValueError, match="terminal|successor"):
        api().evaluate_series("root", lambda _: root)


def test_exact_certificate_accepts_supported_improvement_and_preserves_support():
    bounds = {
        "safe": api().ProbabilityInterval(F(4, 5), F(4, 5)),
        "bad": api().ProbabilityInterval(F(1, 5), F(1, 5)),
        "excluded": api().ProbabilityInterval(F(1), F(1)),
    }
    result = api().certify_proposal(
        {"safe": F(1), "bad": F(1), "excluded": F(0)},
        {"safe": F(3), "bad": F(1), "excluded": F(0)},
        bounds,
    )
    assert result.accepted
    assert result.proposal_lower_advantage == F(3, 20)
    assert result.returned_weights == {"safe": F(3, 4), "bad": F(1, 4), "excluded": F(0)}
    assert result.total_variation == F(1, 4)
    with pytest.raises(ValueError, match="support"):
        api().certify_proposal(
            {"safe": F(1), "bad": F(1), "excluded": F(0)},
            {"safe": F(1), "bad": F(1), "excluded": F(1)},
            bounds,
        )


def test_uncertainty_cannot_masquerade_as_safe_improvement():
    bounds = {
        "known": api().ProbabilityInterval(F(3, 4), F(3, 4)),
        "unknown": api().ProbabilityInterval(F(0), F(1)),
    }
    result = api().certify_proposal(
        {"known": F(1), "unknown": F(1)}, {"known": F(1), "unknown": F(3)}, bounds
    )
    assert not result.accepted
    assert result.proposal_lower_advantage == F(-3, 16)
    assert result.returned_weights == {"known": F(1, 2), "unknown": F(1, 2)}
    assert result.total_variation == 0


def test_results_are_immutable_and_input_maps_are_not_modified():
    prior = {"pass": F(2)}
    root = node(prior, {"pass": {"standard": (branch(success=True),)}})
    result = api().evaluate_series("root", lambda _: root)
    assert prior == {"pass": F(2)}
    with pytest.raises(TypeError):
        result.action_bounds["pass"] = api().ProbabilityInterval(F(0), F(1))
    with pytest.raises(TypeError):
        result.unknown_reasons["invented"] = 1


@pytest.mark.parametrize("limits", [{"max_nodes": 0}, {"max_depth": 0}, {"max_depth": 10000}])
def test_invalid_limits_fail_before_model_is_read(limits):
    def fail(_):
        raise AssertionError("invalid limit must not inspect model")

    with pytest.raises(ValueError, match="limit|depth|nodes"):
        api().evaluate_series("root", fail, **limits)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize(
    "changed_call,modifier,expected",
    [
        (None, "0", 0.7981686716503044),
        ("short_pass", "-4", 0.7707350774),
        ("long_pass", "-10", 0.04111004676),
    ],
)
def test_public_numeric_witness_matches_actual_resolver_core_and_factory(
    home,
    changed_call,
    modifier,
    expected,
):
    """A test-only adapter, not a generic football transition implementation.

    All unknown/special/clock branches remain outside this fixed Q1 numeric
    witness. Resolve every physical cell, project through actual core clones,
    retain full state/history identity, and capture actual Hard factory weights.
    """
    import pickle
    import random
    from collections import defaultdict
    from copy import deepcopy
    from unittest.mock import patch

    from paydirt import play_resolver as resolver
    from paydirt.chart_loader import DefenseChart
    from paydirt.computer_ai import create_computer_ai
    from tests.game_fixtures import make_sample_game

    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.down = 1
    game.state.yards_to_go = 10
    game.state.ball_position = 40
    game.state.quarter = 1
    game.state.time_remaining = 10.0
    for chart in (game.state.home_chart, game.state.away_chart):
        for play in resolver.CHART_PLAY_TYPES:
            rows = {
                row: ("4" if play.value == "short_pass" else "10" if row >= 30 else "0")
                if play.value in ("short_pass", "long_pass")
                else "-20"
                for row in resolver.chart_roll_weights()
            }
            setattr(chart.offense, play.value, rows)
        chart.defense = DefenseChart(
            {
                (formation.value, row): {
                    column: modifier if play.value == changed_call else "0"
                    for column, play in enumerate(resolver.CHART_PLAY_TYPES, 1)
                }
                for formation in resolver.DefenseType
                for row in range(1, 6)
            }
        )
    initial_bytes = pickle.dumps((game.state, game.offensive_call_history))
    global_before = random.getstate()

    class Capture(random.Random):
        def choices(self, population, weights=None, *, cum_weights=None, k=1):
            self.record = dict(zip(population, weights))
            return [population[0]]

    def actual_weights(current):
        ai = create_computer_ai("hard", current, home)
        ai._offense_rng = Capture(8306)
        ai.select_offense_with_clock_management(current)
        assert ai.last_mode is None
        return ai._offense_rng.record

    # Source matrix is independent of the solver. No selected formation input.
    own = game.state.home_chart if home else game.state.away_chart
    opponent = game.state.away_chart if home else game.state.home_chart
    physical_subrows = {1: (1, 0, 1), 2: (2, 0, 2), 3: (3, 0, 3), 4: (2, 2, 4), 5: (3, 2, 5)}
    physical = {}
    # Later long-yardage states can admit calls excluded at the initial root.
    # Compile all nine, never truncate the future policy to initial support.
    for play in resolver.CHART_PLAY_TYPES:
        physical[play] = {}
        for formation in resolver.DefenseType:
            grouped = defaultdict(F)
            representatives = {}
            for row, row_mass in resolver.chart_roll_weights().items():
                for subrow, subrow_mass in resolver.defense_subrow_weights().items():
                    with (
                        patch.object(resolver, "roll_chart_dice", return_value=(row, "test")),
                        patch.object(
                            resolver, "roll_defense_dice", return_value=physical_subrows[subrow]
                        ),
                    ):
                        result = resolver.resolve_play(own, opponent, play, formation)
                    assert result.result_type == resolver.ResultType.YARDS
                    key = (result.result_type, result.yards, result.turnover, result.touchdown)
                    grouped[key] += F(row_mass * subrow_mass, 216 * 36)
                    representatives[key] = result
            assert sum(grouped.values(), F()) == 1
            physical[play][formation] = tuple(
                (mass, representatives[key]) for key, mass in grouped.items()
            )

    games = {}

    def identity(current):
        key = pickle.dumps((current.state, current.offensive_call_history))
        games[key] = current
        return key

    def model(key):
        current = games[key]
        assert current.state.quarter == 1 and current.state.time_remaining > 5
        weights = actual_weights(current)
        outcomes = {}
        for play in weights:
            outcomes[play.value] = {}
            for formation, events in physical[play].items():
                branches = []
                for mass, result in events:
                    clone = deepcopy(current)
                    before = clone.state
                    saved_random = random.getstate()
                    try:
                        # Test-only deterministic numeric projection; this does
                        # not assert a production clock/penalty/replay adapter.
                        random.seed(8306)
                        clone._record_offensive_call(play)
                        outcome = clone._apply_play_result(
                            play,
                            formation,
                            deepcopy(result),
                            "test",
                            before.down,
                            before.ball_position,
                            before.yards_to_go,
                            False,
                            False,
                        )
                    finally:
                        random.setstate(saved_random)
                    if outcome.touchdown or outcome.first_down:
                        event = branch(mass, success=True)
                    elif outcome.safety or outcome.turnover or clone.state.down >= 4:
                        event = branch(mass, success=False)
                    else:
                        assert clone.state.is_home_possession == home
                        event = branch(mass, successor=identity(clone))
                    branches.append(event)
                outcomes[play.value][formation.value] = tuple(branches)
        return node(
            {play.value: F.from_float(weight) for play, weight in weights.items()}, outcomes
        )

    preview = api().evaluate_series(identity(game), model, max_nodes=256)
    assert preview.baseline.lower == preview.baseline.upper
    assert float(preview.baseline.lower) == pytest.approx(expected, abs=1e-9)
    assert not preview.unknown_reasons
    prior = {play.value: F.from_float(weight) for play, weight in actual_weights(game).items()}
    best = max(preview.action_bounds, key=lambda play: preview.action_bounds[play].lower)
    assert best == ("short_pass" if changed_call == "long_pass" else "long_pass")
    proposal = dict(prior)
    proposal[best] *= 2  # Test proposal only; no production sampling rule added.
    certificate = api().certify_proposal(prior, proposal, preview.action_bounds)
    assert certificate.accepted and certificate.proposal_lower_advantage > 0
    returned_value = sum(
        (
            weight * preview.action_bounds[play].lower
            for play, weight in certificate.returned_weights.items()
        ),
        F(),
    )
    assert returned_value - preview.baseline.lower == certificate.proposal_lower_advantage
    assert pickle.dumps((game.state, game.offensive_call_history)) == initial_bytes
    assert random.getstate() == global_before

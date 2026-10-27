"""Exact coaching-score arithmetic and bounded history, not gameplay odds."""

import random
from copy import deepcopy

import pytest

from paydirt.chart_loader import OffenseChart
from paydirt.computer_ai import create_computer_ai
from paydirt.offense_strategy import OffensiveStrategy
from paydirt.play_resolver import PlayType, chart_roll_weights
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("cell,utility", [("10", 1.4), ("10*", 1.4), ("10†", 1.4),
    ("-5", -.6), ("INT 10", -1.5), ("F", -1), ("F+3", -1), ("OFF 5", -.3),
    ("BLACK", 0), ("", 0), ("B", 0), ("QT", 0), ("DS", 0), ("(4)", 0),
    ("DEF 5X", 0), ("PI 10", 0), ("TD", 1.8)])
def test_estimates_use_full_dice_mass_and_explicit_unresolved_values(cell: str, utility: float) -> None:
    chart = OffenseChart(line_plunge={15: cell, 10: "0"})
    before = deepcopy(chart), random.getstate()
    strategy = OffensiveStrategy(chart)
    scores = strategy.scores(3, 10)
    weights = chart_roll_weights()
    assert scores == {PlayType.LINE_PLUNGE: pytest.approx(weights[15] / sum(weights.values()) * utility)}
    scores.clear()
    assert strategy.scores(3, 10)  # Callers cannot mutate cached scores.
    assert (chart, random.getstate()) == before


def test_repetition_floor_never_removes_a_competitive_call() -> None:
    strategy = OffensiveStrategy(OffenseChart(
        screen={roll: "6" for roll in range(10, 40)},
        medium_pass={roll: "6" for roll in range(10, 40)}))
    history = [{"is_home": True, "down": 1, "distance": 10, "play": "screen"}] * 96
    weights = strategy.weights(1, 10, history, True)
    assert weights[PlayType.SCREEN] == pytest.approx(.3 * weights[PlayType.MEDIUM_PASS])
    assert history == [dict(history[0])] * 96


def test_lazy_offense_rng_does_not_advance_gameplay_randomness() -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 1, 10
    game.state.ball_position = 40
    before = random.getstate()
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    assert ai._offense_rng is None
    for _ in range(20):
        ai.select_offense(game)
    assert random.getstate() == before
    assert game.offensive_call_history == []


def test_missing_charts_retain_legal_fallback_and_reset_replacing_team() -> None:
    game = make_sample_game()
    game.state.home_chart.offense = OffenseChart()
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    assert ai.offense_strategy.weights(1, 10, [], True) == {}
    assert isinstance(ai.select_offense(game), PlayType)
    game.state.home_chart.offense = OffenseChart(screen={15: "6"})
    ai.set_team(game.state.home_chart)
    assert ai.offense_strategy.weights(1, 10, [], True) == {PlayType.SCREEN: 1}

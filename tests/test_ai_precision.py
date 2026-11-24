"""Easy and Medium coach with bounded, seeded imprecision (AI-034).

Precision is separate from aggression: lower difficulties may misjudge a
marginal call, but never an obvious one, and the noise uses its own stream so
gameplay dice odds are unchanged.
"""

import random

import pytest

from paydirt.computer_ai import (
    EASY_PRECISION,
    FG_KICK_PROBABILITY,
    HARD_PRECISION,
    MEDIUM_PRECISION,
    CoachingPrecision,
    ComputerAI,
    create_computer_ai,
)
from paydirt.play_resolver import PlayType
from paydirt.season_rules import AIBehavior, AIStrategic
from tests.game_fixtures import make_sample_game
from tests.test_fourth_down_probability import fourth_down, set_fg_chart


def coach(precision: CoachingPrecision | None, aggression: float = 0.5) -> ComputerAI:
    return ComputerAI(
        aggression=aggression,
        ai_behavior=AIBehavior(strategic=AIStrategic(fourth_down_aggression=0.5)),
        precision=precision,
    )


def test_factory_wires_profiles_and_keeps_legacy_construction_sharp() -> None:
    game = make_sample_game()
    assert create_computer_ai("easy", game, cpu_is_home=True).precision is EASY_PRECISION
    assert create_computer_ai("medium", game, cpu_is_home=True).precision is MEDIUM_PRECISION
    assert create_computer_ai("hard", game, cpu_is_home=True).precision is HARD_PRECISION
    assert create_computer_ai("unknown", game, cpu_is_home=True).precision is MEDIUM_PRECISION
    # Balanced auto and existing unit constructions must stay exact.
    assert ComputerAI(aggression=0.5).precision is None


def test_hard_stays_bounded_and_legacy_ai_never_adjusts_the_probability() -> None:
    hard = coach(HARD_PRECISION)
    hard._decision_rng = random.Random(1)
    for value in (0.0, 0.01, 0.14, 0.15, 0.2, 0.349, 0.35, 0.5, 0.699, 0.7, 1.0):
        assert abs(hard._perceived_field_goal_probability(value) - value) <= (
            HARD_PRECISION.fg_optimism + HARD_PRECISION.band_margin)
        assert coach(None)._perceived_field_goal_probability(value) == value


def test_perception_stays_within_the_documented_bounds() -> None:
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=34)  # true p ~= 0.31, just under 0.35
    for profile in (EASY_PRECISION, MEDIUM_PRECISION):
        ai = coach(profile)
        ai._decision_rng = random.Random(7)
        for _ in range(200):
            seen = ai._perceived_field_goal_probability(0.31)
            assert 0.31 - 0.06 <= seen <= 0.31 + 0.06 + profile.fg_optimism


def test_optimism_makes_easy_overrate_a_marginal_kick() -> None:
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=34)  # p ~= 0.306
    ai = coach(EASY_PRECISION)
    ai._decision_rng = random.Random(3)
    assert ai.select_offense(game) == PlayType.FIELD_GOAL
    medium = coach(MEDIUM_PRECISION)
    medium._decision_rng = random.Random(3)
    hard = coach(HARD_PRECISION)
    hard._decision_rng = random.Random(3)
    assert medium.select_offense(game) == PlayType.PUNT
    assert hard.select_offense(game) == PlayType.PUNT


def test_marginal_call_order_easy_more_fallible_than_medium_than_hard() -> None:
    """Seeded decision counts, not luck: Easy strays most, Hard never does."""
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=34)  # p ~= 0.306 around the 0.35 edge
    attempts = 300

    def kicks(profile: CoachingPrecision) -> int:
        ai = coach(profile)
        ai._decision_rng = random.Random(20261115)
        return sum(ai.select_offense(game) == PlayType.FIELD_GOAL
                   for _ in range(attempts))

    hard = kicks(HARD_PRECISION)
    medium = kicks(MEDIUM_PRECISION)
    easy = kicks(EASY_PRECISION)

    assert 0 < hard < medium
    assert 0 < medium < easy
    assert easy > attempts * 0.6


def test_confusion_only_applies_near_a_band_edge() -> None:
    ai = coach(EASY_PRECISION)
    ai._decision_rng = random.Random(11)
    # Far enough from every edge that optimism cannot carry it there.
    for value in (0.05, 0.20, 0.55, 0.90):
        assert ai._perceived_field_goal_probability(value) == pytest.approx(
            min(1.0, value + EASY_PRECISION.fg_optimism)
        )


def test_precision_noise_never_touches_gameplay_dice() -> None:
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=34)
    ai = coach(EASY_PRECISION)
    ai._decision_rng = random.Random(5)
    before = random.getstate()
    for _ in range(100):
        ai.select_offense(game)
    assert random.getstate() == before


def test_precision_is_reproducible_from_the_decision_stream() -> None:
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=34)

    def sequence(seed: int) -> list[PlayType]:
        ai = coach(EASY_PRECISION)
        ai._decision_rng = random.Random(seed)
        return [ai.select_offense(game) for _ in range(40)]

    assert sequence(99) == sequence(99)
    assert sequence(99) != sequence(100)


@pytest.mark.parametrize("profile", [None, EASY_PRECISION, MEDIUM_PRECISION, HARD_PRECISION])
def test_endgame_priorities_are_not_noised(profile) -> None:
    """A tying kick with seconds left stays sharp at every difficulty."""
    game = fourth_down(position=70, ytg=5, quarter=4, time_left=1.0, lead=-3)
    set_fg_chart(game, makes_from_roll=33)  # p ~= 0.375
    ai = coach(profile)
    ai._decision_rng = random.Random(1)
    assert ai.select_offense(game) == PlayType.FIELD_GOAL


def test_band_edges_are_the_documented_decision_thresholds() -> None:
    assert 0 < HARD_PRECISION.fg_optimism < MEDIUM_PRECISION.fg_optimism
    assert 0 < HARD_PRECISION.band_confusion < MEDIUM_PRECISION.band_confusion
    assert MEDIUM_PRECISION.band_confusion < EASY_PRECISION.band_confusion
    assert FG_KICK_PROBABILITY == 0.35

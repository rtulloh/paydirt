"""Field-goal make probability derived from the kicking team's own chart.

The AI must reason about the same chance the engine resolves, so these tests
bind the analytic helper to the real penalty-aware field-goal procedure.
"""

import random
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from paydirt.chart_loader import SpecialTeamsChart
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import (
    chart_roll_weights,
    field_goal_make_probability,
    resolve_field_goal_with_penalties,
)
from tests.game_fixtures import make_sample_game


def chart(rows: dict[int, str]) -> SpecialTeamsChart:
    return SpecialTeamsChart(field_goal=dict(rows))


def full_chart(value_by_roll: dict[int, str]) -> SpecialTeamsChart:
    """Complete 10-39 chart so missing rows cannot hide the tested behaviour."""
    rows = {roll: "" for roll in range(10, 40)}
    rows.update(value_by_roll)
    return chart(rows)


def test_uses_chart_dice_weights_and_counts_missing_rows_as_misses() -> None:
    # Roll 10 carries 2/216 dice combinations, roll 35 carries 18/216.
    # A sparse chart's unlisted rows are empty cells, which the engine resolves
    # as a miss, so the denominator stays 216.
    special = chart({10: "40", 35: "10"})
    assert field_goal_make_probability(special, 20) == pytest.approx(2 / 216)


def test_penalty_rows_reroll_and_are_renormalized_away() -> None:
    special = chart({10: "OFF 5", 35: "40", 39: "DEF 5"})
    usable = 216 - chart_roll_weights()[10] - chart_roll_weights()[39]
    assert field_goal_make_probability(special, 20) == pytest.approx(
        chart_roll_weights()[35] / usable
    )


@pytest.mark.parametrize("cell", ["BK -7", "BK 3", "F - 7", "F 2", "F SNAP LOST 0", "NG", ""])
def test_blocks_fumbles_and_no_goods_are_misses(cell: str) -> None:
    special = chart({20: "40", 30: cell})
    assert field_goal_make_probability(special, 20) == pytest.approx(
        chart_roll_weights()[20] / 216
    )


def test_chart_yards_equal_to_distance_is_good() -> None:
    special = full_chart({roll: "40" for roll in range(10, 40)})
    assert field_goal_make_probability(special, 40) == pytest.approx(1.0)
    assert field_goal_make_probability(special, 41) == pytest.approx(0.0)


def test_all_penalty_chart_has_no_usable_mass() -> None:
    special = chart({roll: "OFF 5" for roll in range(10, 40)})
    assert field_goal_make_probability(special, 20) is None


@pytest.mark.parametrize("special", [MagicMock(spec=SpecialTeamsChart), None])
def test_unreadable_chart_returns_none(special) -> None:
    assert field_goal_make_probability(special, 20) is None


def test_helper_never_touches_gameplay_dice() -> None:
    special = full_chart({roll: "40" for roll in range(10, 40)})
    before = random.getstate()
    field_goal_make_probability(special, 25)
    assert random.getstate() == before


def test_matches_penalty_aware_resolution_frequency() -> None:
    special = full_chart({
        10: "45", 11: "45", 12: "42", 13: "39", 14: "36", 15: "OFF 5",
        16: "33", 17: "30", 18: "28", 19: "25", 20: "45", 21: "42",
        22: "39", 23: "36", 24: "33", 25: "30", 26: "28", 27: "25",
        28: "22", 29: "20", 30: "45", 31: "42", 32: "DEF 5", 33: "36",
        34: "33", 35: "30", 36: "28", 37: "25", 38: "22", 39: "NG",
    })
    distance_to_goal = 30
    expected = field_goal_make_probability(special, distance_to_goal)

    random.seed(20261115)
    attempts = 4000
    makes = 0
    for _ in range(attempts):
        result = resolve_field_goal_with_penalties(special)
        if result.is_blocked or result.is_fumble:
            continue
        if result.chart_yards >= distance_to_goal:
            makes += 1
    assert makes / attempts == pytest.approx(expected, abs=0.03)


def test_engine_wrapper_uses_the_possession_team_chart() -> None:
    game = make_sample_game()
    game.state.home_chart.special_teams = full_chart({roll: "50" for roll in range(10, 40)})
    game.state.away_chart.special_teams = full_chart({roll: "10" for roll in range(10, 40)})

    game.state.is_home_possession = True
    assert game.field_goal_make_probability(30) == pytest.approx(1.0)

    game.state.is_home_possession = False
    assert game.field_goal_make_probability(30) == pytest.approx(0.0)


def test_engine_wrapper_matches_public_sample_chart() -> None:
    game = make_sample_game()
    assert isinstance(game, PaydirtGameEngine)
    probability = game.field_goal_make_probability(28)
    assert probability == pytest.approx(
        field_goal_make_probability(
            SimpleNamespace(field_goal=game.state.home_chart.special_teams.field_goal), 28
        )
    )

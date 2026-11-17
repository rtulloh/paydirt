"""Season-aware late-game urgency regressions for AI-035."""

import random
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

import pytest

from paydirt.play_resolver import PlayType
from tests.test_ai_offense_variety import synthetic_ai


@pytest.fixture(autouse=True)
def preserve_randomness():
    before = random.getstate()
    yield
    random.setstate(before)

def urgency_state(
    *,
    minutes: float,
    deficit: int,
    can_go_for_two: bool,
    quarter: int = 4,
    overtime: bool = False,
):
    game, ai = synthetic_ai()
    game.state.quarter = quarter
    game.state.is_overtime = overtime
    game.state.time_remaining = minutes
    game.state.home_score = 0
    game.state.away_score = deficit
    game.season_rules = replace(
        deepcopy(game.season_rules),
        two_point_conversion=can_go_for_two,
    )
    ai.ai_behavior = deepcopy(game.season_rules.ai_behavior)
    ai.ai_behavior.hurry_up.q4_deficit_9_minutes = 3.0
    ai.ai_behavior.hurry_up.q4_any_minutes = 2.0
    ai.ai_behavior.two_minute_drill.q4_deficit_9_minutes = 3.0
    ai.ai_behavior.two_minute_drill.q4_always_minutes = 2.0
    return game, ai


@pytest.mark.parametrize(
    ("can_go_for_two", "deficit", "expected"),
    [
        (False, 7, 1),
        (False, 8, 2),
        (False, 14, 2),
        (False, 15, 3),
        (True, 8, 1),
        (True, 9, 2),
        (True, 16, 2),
        (True, 17, 3),
    ],
)
def test_scores_needed_uses_active_conversion_rules(
    can_go_for_two: bool,
    deficit: int,
    expected: int,
) -> None:
    game, _ = urgency_state(
        minutes=2.99,
        deficit=deficit,
        can_go_for_two=can_go_for_two,
    )

    assert game.season_rules.scores_needed(deficit) == expected


@pytest.mark.parametrize("minutes", [2.99, 2.5, 1.0])
def test_no_conversion_eight_point_deficit_hurries_inside_three_minutes(
    minutes: float,
) -> None:
    game, ai = urgency_state(
        minutes=minutes,
        deficit=8,
        can_go_for_two=False,
    )

    _, _, no_huddle, _, _, _ = ai.select_offense_with_clock_management(game)

    assert no_huddle
    assert ai._needs_hurry_up(game, minutes, 4, -8)
    assert ai._is_two_minute_drill(game, minutes, 4, -8)


def test_eight_point_deficit_with_conversion_stays_ordinary_at_2_59() -> None:
    game, ai = urgency_state(
        minutes=2.99,
        deficit=8,
        can_go_for_two=True,
    )

    assert not ai._needs_hurry_up(game, 2.99, 4, -8)
    assert not ai._is_two_minute_drill(game, 2.99, 4, -8)


@pytest.mark.parametrize(
    ("minutes", "quarter", "overtime"),
    [
        (3.0, 4, False),
        (2.99, 3, False),
        (2.99, 4, True),
    ],
)
def test_no_conversion_two_score_boundary_excludes_non_regulation_q4_states(
    minutes: float,
    quarter: int,
    overtime: bool,
) -> None:
    game, ai = urgency_state(
        minutes=minutes,
        deficit=8,
        can_go_for_two=False,
        quarter=quarter,
        overtime=overtime,
    )

    assert not ai._needs_hurry_up(game, minutes, quarter, -8)
    assert not ai._is_two_minute_drill(game, minutes, quarter, -8)


def test_two_score_urgency_does_not_change_tied_offense() -> None:
    game, ai = urgency_state(minutes=2.99, deficit=0, can_go_for_two=False)

    assert not ai._needs_hurry_up(game, 2.99, 4, 0)
    assert not ai._is_two_minute_drill(game, 2.99, 4, 0)


def test_two_score_urgency_does_not_change_leading_offense() -> None:
    game, ai = urgency_state(minutes=2.99, deficit=0, can_go_for_two=False)
    game.state.home_score = 7

    assert not ai._needs_hurry_up(game, 2.99, 4, 7)
    assert not ai._is_two_minute_drill(game, 2.99, 4, 7)


def test_hurry_up_oob_uses_seeded_offense_rng() -> None:
    game, ai = urgency_state(minutes=2.99, deficit=8, can_go_for_two=False)
    ai.ai_behavior.strategic.oob_designation_aggression = 1.0
    ai._offense_rng.seed(8306)

    with patch("paydirt.computer_ai.random.random", side_effect=AssertionError):
        flags = ai._hurry_up_flags(game, PlayType.SHORT_PASS, 2.99, 4, -8)

    assert flags == (True, True)


@pytest.mark.parametrize(
    ("can_go_for_two", "deficit", "expected"),
    [
        (False, 8, True),
        (True, 8, False),
        (True, 9, True),
    ],
)
def test_fourth_down_urgency_uses_season_score_count(
    can_go_for_two: bool,
    deficit: int,
    expected: bool,
) -> None:
    game, ai = urgency_state(
        minutes=2.99,
        deficit=deficit,
        can_go_for_two=can_go_for_two,
    )
    game.state.home_timeouts = 0

    assert ai._multi_score_fourth_down_urgent(
        game, distance=5, field_position=50, minutes_left=2.99,
        deficit=deficit,
    ) is expected

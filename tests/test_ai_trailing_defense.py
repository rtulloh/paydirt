"""Late multi-score Hard defense mixes risks without spending engine dice."""

from collections import Counter
from copy import deepcopy
import random
from unittest.mock import Mock, patch

import pytest

from paydirt.computer_ai import ComputerAI, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType
from tests.game_fixtures import make_sample_game


A, B, F = DefenseType.STANDARD, DefenseType.SHORT_YARDAGE, DefenseType.BLITZ


def late_game(home_offense: bool = True, deficit: int = 9, two_point: bool = False) -> PaydirtGameEngine:
    """Public charts with synthetic score and season-rule configuration."""
    game = make_sample_game()
    game.season_rules.two_point_conversion = two_point
    state = game.state
    state.is_home_possession = home_offense
    state.home_score, state.away_score = (deficit, 0) if home_offense else (0, deficit)
    state.quarter, state.time_remaining = 4, 4.0
    state.ball_position, state.down, state.yards_to_go = 50, 1, 10
    return game


@pytest.mark.parametrize("home_offense", [False, True])
@pytest.mark.parametrize("two_point,deficit,down,distance,weights", [
    (False, 8, 1, 10, (55, 30, 15)),
    (False, 14, 2, 5, (55, 30, 15)),
    (False, 15, 1, 10, (40, 35, 25)),
    (True, 9, 1, 10, (55, 30, 15)),
    (True, 16, 2, 5, (55, 30, 15)),
    (True, 17, 1, 10, (40, 35, 25)),
    (False, 8, 3, 2, (45, 40, 15)),
    (False, 15, 4, 3, (30, 45, 25)),
    (False, 9, 3, 6, (55, 30, 15)),
    (False, 9, 3, 7, (45, 10, 45)),
    (True, 21, 4, 10, (45, 10, 45)),
])
def test_exact_mix_and_engine_rng_isolation(
    home_offense: bool, two_point: bool, deficit: int, down: int, distance: int,
    weights: tuple[int, int, int],
) -> None:
    game = late_game(home_offense, deficit, two_point)
    game.state.down, game.state.yards_to_go = down, distance
    ai = create_computer_ai("hard", game, cpu_is_home=not home_offense)
    ai._defense_rng = random.Random(123)
    before_state, before_rng = deepcopy(game.state), random.getstate()
    # Midpoints of 100 equal probability buckets: exact proportions, no flaky sampling.
    with patch.object(ai._defense_rng, "random", side_effect=[(i + .5) / 100 for i in range(100)]):
        calls = Counter(ai.select_defense(game) for _ in range(100))
    assert calls == Counter(dict(zip((A, B, F), weights)))
    assert random.getstate() == before_rng
    assert game.state == before_state
    assert ai.opponent_model.score_differential_history == [deficit] * 100


@pytest.mark.parametrize("changes,two_point,deficit,expected", [
    ({}, False, 7, A),
    ({}, True, 8, A),
    ({}, False, 0, DefenseType.SHORT_PASS),
    ({}, False, -14, DefenseType.LONG_PASS),
    ({"quarter": 3}, False, 14, DefenseType.SHORT_PASS),
    ({"quarter": 5}, False, 14, A),
    ({"time_remaining": 5.0}, False, 14, DefenseType.SHORT_PASS),
    ({"time_remaining": 0.0}, False, 14, A),
    ({"game_over": True}, False, 14, A),
    ({"ball_position": 80}, False, 14, A),
    ({"ball_position": 95}, False, 14, A),
    ({"ball_position": 100}, False, 14, A),
    ({"ball_position": 0}, False, 14, A),
])
def test_noneligible_situations_keep_existing_model_behavior(
    changes: dict, two_point: bool, deficit: int, expected: DefenseType,
) -> None:
    game = late_game(deficit=deficit, two_point=two_point)
    for name, value in changes.items():
        setattr(game.state, name, value)
    ai = create_computer_ai("hard", game, cpu_is_home=False)
    ai.opponent_model.tracker.get_defense_recommendation = Mock(return_value="D")
    ai._defense_rng = Mock()
    assert ai.select_defense(game) == expected
    ai._defense_rng.random.assert_not_called()
    ai._defense_rng.choices.assert_not_called()


@pytest.mark.parametrize("difficulty", ["easy", "medium"])
def test_lower_difficulties_do_not_use_pressure_mix(difficulty: str) -> None:
    game = late_game(deficit=21)
    ai = create_computer_ai(difficulty, game, cpu_is_home=False)
    ai._early_down_defense = Mock(return_value=DefenseType.SPREAD)
    ai._defense_rng = Mock()
    assert ai.select_defense(game) == DefenseType.SPREAD
    ai._early_down_defense.assert_called_once_with(1, 10)
    ai._defense_rng.choices.assert_not_called()


def test_last_included_field_position_and_clock_boundary() -> None:
    game = late_game(deficit=21)
    game.state.ball_position, game.state.time_remaining = 79, 4.999
    ai = create_computer_ai("hard", game, cpu_is_home=False)
    ai._defense_rng = random.Random(0)
    with patch.object(ai._defense_rng, "random", return_value=.99):
        assert ai.select_defense(game) == F


def test_pressure_rng_is_seed_reproducible_and_does_not_consume_global_rng() -> None:
    original = random.getstate()
    try:
        sequences = []
        for _ in range(2):
            random.seed(19831623)
            game = late_game(deficit=21)
            before = random.getstate()
            ai = create_computer_ai("hard", game, cpu_is_home=False)
            calls = [ai.select_defense(game) for _ in range(120)]
            assert random.getstate() == before
            assert set(calls) == {A, B, F}
            sequences.append(calls)
        assert sequences[0] == sequences[1]
    finally:
        random.setstate(original)


def test_pressure_rng_does_not_follow_subsequent_engine_draws() -> None:
    game = late_game(deficit=21)
    first = ComputerAI(use_analysis=True)
    second = ComputerAI(use_analysis=True)
    before = random.getstate()
    try:
        assert first.select_defense(game) == second.select_defense(game)
        one, two = [], []
        for _ in range(40):
            one.append(first.select_defense(game))
            random.random()  # Unrelated engine activity must not advance the AI stream.
            two.append(second.select_defense(game))
        assert one == two
    finally:
        random.setstate(before)


@pytest.mark.parametrize("formation,play,expected", [
    (A, "LINE_PLUNGE", 4), (A, "DRAW", 3), (A, "SCREEN", 3),
    (B, "LINE_PLUNGE", -1), (B, "DRAW", 9), (B, "SCREEN", 10),
    (F, "LINE_PLUNGE", -3), (F, "DRAW", 12), (F, "SCREEN", 15),
])
def test_synthetic_stress_chart_exercises_real_run_counter_tradeoff(
    formation: DefenseType, play: str, expected: int,
) -> None:
    """Validate the experiment's premise without claiming historical team strength."""
    from paydirt.play_resolver import PlayType
    from tests.run_trailing_defense import configure_synthetic_defense

    game = late_game()
    configure_synthetic_defense(game)
    for column in (game.state.possession_team.offense.line_plunge,
                   game.state.possession_team.offense.draw, game.state.possession_team.offense.screen):
        column.update({roll: "4" for roll in range(10, 40)})
    with (
        patch("paydirt.play_resolver.random.choice", side_effect=lambda faces: faces[0]),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(25, "synthetic 25")),
    ):
        outcome = game.run_play_with_penalty_procedure(PlayType[play], formation)
    assert not outcome.pending_penalty_decision
    assert outcome.yards_gained == expected
    assert game.state.ball_position == 50 + expected

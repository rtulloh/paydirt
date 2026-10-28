"""Conversion coaching observes an untimed try, not the previous scrimmage."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI, cpu_should_go_for_two, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.interactive_game import _complete_touchdown_sequence
from paydirt.offense_strategy import OffensiveStrategy
from paydirt.play_resolver import (
    CHART_PLAY_TYPES,
    DefenseType,
    PlayType,
    chart_roll_weights,
    parse_result_string,
)
from tests.game_fixtures import make_sample_game


def conversion_game(home: bool = True, seconds: int = 18, margin: int = 1) -> PaydirtGameEngine:
    game = make_sample_game()
    game.season_rules.two_point_conversion = True
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 97, 4, 13
    game.state.quarter, game.state.time_remaining = 4, seconds / 60
    game.state.home_score, game.state.away_score = (8 + margin, 8) if home else (8, 8 + margin)
    game.state.game_over = seconds == 0
    return game


def test_engine_exposes_untimed_two_point_situation_without_mutating_state() -> None:
    game = conversion_game()
    before = deepcopy(game.state)
    observation = game.get_two_point_situation()
    assert observation["ball_position"] == 98
    assert observation["down"] == 1
    assert observation["yards_to_go"] == 2
    assert observation["time_remaining"] is None
    assert observation["points"] == 2
    assert set(observation["legal_plays"]) == set(CHART_PLAY_TYPES)
    assert game.state == before


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("seconds,margin", [(18, 1), (8, -2), (0, -2)])
def test_conversion_selectors_ignore_stale_clock_field_and_series(
    difficulty: str, home: bool, seconds: int, margin: int,
) -> None:
    game = conversion_game(home, seconds, margin)
    ai = create_computer_ai(difficulty, game, home)
    before = deepcopy(game.state)
    with (
        patch.object(ai, "select_offense", side_effect=AssertionError("ordinary offense on a try")),
        patch.object(ai, "select_offense_with_clock_management", side_effect=AssertionError("clock policy on a try")),
        patch.object(ai, "select_defense", side_effect=AssertionError("ordinary defense on a try")),
    ):
        for _ in range(8):
            assert ai.select_two_point_offense(game) in CHART_PLAY_TYPES
            assert ai.select_two_point_defense(game) in DefenseType
    assert game.state == before
    assert game.offensive_call_history == []


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("allowed", [False, True])
@pytest.mark.parametrize("overtime", [False, True])
def test_expired_clock_requires_two_when_regulation_try_is_pending(
    home: bool, allowed: bool, overtime: bool,
) -> None:
    game = conversion_game(home, seconds=0, margin=-2)
    game.season_rules.two_point_conversion = allowed
    game.state.is_overtime = overtime
    ai = ComputerAI()
    assert ai.should_go_for_two(game, try_pending=True) is (allowed and not overtime)
    assert cpu_should_go_for_two(game, ai, try_pending=True) is (allowed and not overtime)
    assert not ai.should_go_for_two(game)  # A finished game without an owed try stays finished.


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("seconds,margin", [(18, 1), (8, -2), (0, -2)])
def test_cli_cpu_try_uses_conversion_offense_and_human_defense(home: bool, seconds: int, margin: int) -> None:
    game = conversion_game(home, seconds, margin)
    ai = create_computer_ai("hard", game, home)
    touchdown = PlayOutcome(PlayType.SHORT_PASS, DefenseType.STANDARD, parse_result_string("TD"), touchdown=True)
    with (
        patch.object(ai, "select_offense", side_effect=AssertionError("stale ordinary policy")),
        patch("paydirt.interactive_game.get_human_defense_for_conversion", return_value=DefenseType.BLITZ, create=True),
        patch.object(game, "attempt_two_point", return_value=(False, 0, "try resolved")) as attempt,
        patch.object(game, "attempt_extra_point") as extra,
        patch.object(game, "can_kickoff_after_play", return_value=False),
    ):
        _complete_touchdown_sequence(game, touchdown, not home, ai)
    extra.assert_not_called()
    assert attempt.call_count == 1
    play, defense = attempt.call_args.args
    assert play in CHART_PLAY_TYPES
    assert defense == DefenseType.BLITZ


def test_cli_human_try_gets_cpu_conversion_defense() -> None:
    game = conversion_game()
    ai = create_computer_ai("hard", game, False)
    touchdown = PlayOutcome(PlayType.SHORT_PASS, DefenseType.STANDARD, parse_result_string("TD"), touchdown=True)
    with (
        patch("builtins.input", return_value="2"),
        patch("paydirt.interactive_game.get_human_offense_play_for_conversion", return_value=PlayType.DRAW),
        patch.object(ai, "select_two_point_defense", return_value=DefenseType.SHORT_YARDAGE, create=True) as defense,
        patch.object(game, "attempt_two_point", return_value=(False, 0, "try resolved")) as attempt,
        patch.object(game, "can_kickoff_after_play", return_value=False),
    ):
        _complete_touchdown_sequence(game, touchdown, True, ai)
    defense.assert_called_once_with(game)
    attempt.assert_called_once_with(PlayType.DRAW, DefenseType.SHORT_YARDAGE)


def test_conversion_chart_utility_targets_two_points_not_extra_yards() -> None:
    game = make_sample_game()
    chart = game.state.home_chart.offense
    for play in CHART_PLAY_TYPES:
        getattr(chart, play.value).clear()
        getattr(chart, play.value).update({roll: "1" for roll in chart_roll_weights()})
    chart.line_plunge.update({roll: "2" for roll in chart_roll_weights()})
    chart.long_pass.update({roll: "80" for roll in chart_roll_weights()})
    strategy = OffensiveStrategy(chart)
    scores = strategy.conversion_scores(distance=2, points=2)
    assert scores[PlayType.LINE_PLUNGE] == pytest.approx(2)
    assert scores[PlayType.LONG_PASS] == scores[PlayType.LINE_PLUNGE]
    assert scores[PlayType.SHORT_PASS] == 0


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_conversion_selection_does_not_consume_engine_randomness(difficulty: str) -> None:
    import random

    game = conversion_game()
    ai = create_computer_ai(difficulty, game, True)
    before = random.getstate()
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("preview rolled dice")):
        ai.select_two_point_offense(game)
        ai.select_two_point_defense(game)
    assert random.getstate() == before


def test_conversion_unknown_cells_keep_full_dice_mass_and_risk_costs() -> None:
    game = make_sample_game()
    chart = game.state.home_chart.offense
    weights = chart_roll_weights()
    total = sum(weights.values())
    for play in CHART_PLAY_TYPES:
        getattr(chart, play.value).clear()
    roll = next(iter(weights))
    chart.line_plunge[roll] = "2"
    chart.line_plunge[99] = "TD"  # Impossible dice totals never add weight.
    chart.off_tackle.update({key: "B" for key in weights})
    chart.draw.update({key: "INT" for key in weights})
    chart.screen.update({key: "F" for key in weights})
    chart.short_pass.update({key: "TD" for key in weights})
    scores = OffensiveStrategy(chart).conversion_scores(2, 2)
    assert scores[PlayType.LINE_PLUNGE] == pytest.approx(2 * weights[roll] / total)
    assert scores[PlayType.OFF_TACKLE] == 0
    assert scores[PlayType.DRAW] == pytest.approx(-2)
    assert scores[PlayType.SCREEN] == pytest.approx(-1)
    assert scores[PlayType.SHORT_PASS] == pytest.approx(2)
    assert PlayType.LONG_PASS not in scores


def test_human_try_defense_validates_input_without_ordinary_state_menu() -> None:
    from paydirt.interactive_game import get_human_defense_for_conversion

    game = conversion_game()
    with patch("builtins.input", side_effect=["punt", "", "f"]):
        assert get_human_defense_for_conversion(game) == DefenseType.BLITZ


def test_resumed_human_try_uses_conversion_defense() -> None:
    from paydirt.interactive_game import resume_game

    class StopAtTry(Exception):
        pass

    game = conversion_game()
    info = {"saved_at": "synthetic", "away_team": "AWAY", "home_team": "HOME",
            "away_score": 8, "home_score": 3, "quarter": 4, "time_remaining": .3}
    with (
        patch("builtins.input", side_effect=["", "2"]),
        patch("paydirt.interactive_game.get_save_info", return_value=info),
        patch("paydirt.interactive_game.load_game", return_value=(game, False, True, "touchdown")),
        patch("paydirt.interactive_game.get_human_offense_play_for_conversion", return_value=PlayType.DRAW),
        patch.object(ComputerAI, "select_two_point_defense", return_value=DefenseType.BLITZ) as defense,
        patch.object(game, "attempt_two_point", side_effect=StopAtTry) as attempt,
        pytest.raises(StopAtTry),
    ):
        resume_game("synthetic-save.json")
    defense.assert_called_once_with(game)
    attempt.assert_called_once_with(PlayType.DRAW, DefenseType.BLITZ)

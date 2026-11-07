"""Pending scrimmage previews must match real enforcement, without moving state."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from paydirt.utils import format_down_and_distance
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("down,kind,yards", [
    (3, ResultType.INCOMPLETE, 0), (2, ResultType.YARDS, 3),
    (3, ResultType.YARDS, -4), (2, ResultType.YARDS, 12),
    (4, ResultType.INCOMPLETE, 0),
])
@pytest.mark.parametrize("accept_play", [True, False])
def test_preview_matches_real_decision(home: bool, down: int, kind: ResultType, yards: int, accept_play: bool) -> None:
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home
    state.ball_position, state.down, state.yards_to_go = 77, down, 9
    choice = PenaltyChoice(
        play_result=PlayResult(kind, yards=yards, description="Incomplete pass" if kind == ResultType.INCOMPLETE else "Synthetic gain"),
        penalty_options=[PenaltyOption("OFF", "OFF 5", 5, "Offensive penalty, 5 yards")],
        offended_team="defense",
    )
    before = deepcopy(state)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice), patch("paydirt.penalty_handler.roll_chart_dice", side_effect=AssertionError("preview must not roll")):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state == before
    original_choice = deepcopy(choice)
    preview_choice = game.get_penalty_choice_preview(outcome)
    assert choice == original_choice
    assert game.state == before
    preview = preview_choice.play_result_preview if accept_play else preview_choice.penalty_options[0].result_preview
    assert preview is not None
    with patch("paydirt.game_engine.random.uniform", return_value=40):
        game.apply_penalty_decision(outcome, accept_play=accept_play)
    actual = f"{format_down_and_distance(state.down, state.yards_to_go, 100 - state.ball_position)} at {state.field_position_str()}"
    if accept_play:
        summary = "Incomplete pass" if kind == ResultType.INCOMPLETE else ("No gain" if yards == 0 else f"{yards:+d} yards")
        actual = f"{summary} — {actual}"
    assert preview == (f"Turnover on downs: {actual}" if accept_play and down == 4 else actual)


@pytest.mark.parametrize("accept_play", [True, False])
def test_existing_incomplete_enforcement_is_already_correct(accept_play: bool) -> None:
    """Passing control: misleading UI text must not cause a rules change."""
    game = make_sample_game()
    game.state.ball_position, game.state.down, game.state.yards_to_go = 77, 3, 9
    choice = PenaltyChoice(PlayResult(ResultType.INCOMPLETE), [PenaltyOption("OFF", "OFF 5", 5, "Offensive foul")], offended_team="defense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    game.apply_penalty_decision(outcome, accept_play=accept_play)
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == ((77, 4, 9) if accept_play else (72, 3, 14))

"""Engine-owned call history: execution, penalty decisions, persistence, isolation."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("penalty", ["none", "offsetting", "accepted", "declined"])
def test_engine_records_one_actual_call_with_preplay_situation(
    home: bool, procedure: bool, penalty: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.down, game.state.yards_to_go = 2, 8
    game.state.ball_position = 40
    result = PlayResult(ResultType.YARDS, yards=9, description="Synthetic gain")
    choice = PenaltyChoice(result, offsetting=penalty == "offsetting")
    if penalty in ("accepted", "declined"):
        choice.penalty_options = [PenaltyOption(
            penalty_type="OFF", raw_result="OFF 5", yards=5, description="Offensive penalty")]
        choice.offended_team = "defense"
    with patch("paydirt.game_engine.resolve_play", return_value=result), patch(
        "paydirt.game_engine.resolve_play_with_penalties", return_value=choice,
    ):
        if procedure:
            outcome = game.run_play_with_penalty_procedure(PlayType.SCREEN, DefenseType.STANDARD)
            if outcome.pending_penalty_decision:
                game.apply_penalty_decision(outcome, accept_play=penalty == "declined")
        else:
            game.run_play(PlayType.SCREEN, DefenseType.STANDARD)
    assert getattr(game, "offensive_call_history", None) == [
        {"is_home": home, "down": 2, "distance": 8, "play": PlayType.SCREEN.value}]


def test_previews_and_rejected_execution_do_not_create_history() -> None:
    game = make_sample_game()
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    for _ in range(10):
        ai.select_offense(game)
    game.state.game_over = True
    with pytest.raises(ValueError, match="Game is over"):
        game.run_play(PlayType.SCREEN, DefenseType.STANDARD)
    assert getattr(game, "offensive_call_history", None) == []


def test_history_is_bounded_and_fresh_games_do_not_inherit_it() -> None:
    game = make_sample_game()
    for _ in range(110):
        game.state.quarter, game.state.time_remaining = 1, 15
        game.state.down, game.state.ball_position = 1, 40
        with patch("paydirt.game_engine.resolve_play", return_value=PlayResult(ResultType.INCOMPLETE)):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert len(getattr(game, "offensive_call_history", [])) == 96
    assert getattr(make_sample_game(), "offensive_call_history", None) == []


def test_save_resume_preserves_history_and_legacy_saves_start_empty(tmp_path: Path) -> None:
    game = make_sample_game()
    history = [{"is_home": True, "down": 1, "distance": 10, "play": PlayType.DRAW.value}]
    game.offensive_call_history = history
    path = tmp_path / "game.json"
    save_game(game, str(path))
    loaded = load_game(str(path))[0]
    assert getattr(loaded, "offensive_call_history", None) == history
    original_ai = create_computer_ai("hard", game, cpu_is_home=True)
    resumed_ai = create_computer_ai("hard", loaded, cpu_is_home=True)
    assert original_ai.offense_strategy.weights(1, 10, history, True) == (
        resumed_ai.offense_strategy.weights(1, 10, loaded.offensive_call_history, True))
    loaded.offensive_call_history.append(dict(history[0]))
    assert len(game.offensive_call_history) == 1
    data = json.loads(path.read_text())
    data.pop("offensive_call_history", None)
    path.write_text(json.dumps(data))
    assert getattr(load_game(str(path))[0], "offensive_call_history", None) == []


@pytest.mark.parametrize("invalid", [None, {}, ["screen"], [
    {"is_home": "false", "down": 1, "distance": 10, "play": "screen"}], [
    {"is_home": True, "down": 5, "distance": 10, "play": "screen"}], [
    {"is_home": True, "down": 1, "distance": 10, "play": "punt"}],
])
def test_invalid_saved_history_is_rejected_clearly(tmp_path: Path, invalid: object) -> None:
    path = tmp_path / "game.json"
    save_game(make_sample_game(), str(path))
    data = json.loads(path.read_text())
    data["offensive_call_history"] = invalid
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="offensive call history"):
        load_game(str(path))

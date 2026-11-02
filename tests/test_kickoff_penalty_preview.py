"""AUD-026: kickoff choices preview the kick, independent of the old spot."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from paydirt.interactive_game import handle_penalty_decision
from tests.test_kickoff_return_penalties import kick, kick_game


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("old_position", [1, 35, 100])
def test_kickoff_penalty_preview_uses_rolled_kick_and_return(
    kicking_home: bool, old_position: int, monkeypatch, capsys,
) -> None:
    game, kicker, receiver = kick_game(kicking_home)
    game.state.ball_position = old_position
    game.state.home_score, game.state.away_score = 30, 10
    kicker.kickoff.update({10: "DEF 5", 18: "66"})
    receiver.kickoff_return[32] = "14"
    pending = kick(game, kicking_home, 10, 18, 32)
    assert pending.pending_penalty_decision
    preview = pending.penalty_choice.play_result_preview
    assert preview is not None
    assert "13" in preview and "1st and 10" in preview
    assert "TOUCHDOWN" not in preview
    assert pending.penalty_choice.penalty_options[0].result_preview == "Re-kick from 30"
    assert game.state.ball_position == old_position
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert not game.state.scoring_plays
    monkeypatch.setattr("builtins.input", lambda *args: "1")
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("no reroll")), \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = handle_penalty_decision(game, pending, True, not kicking_home)
    output = capsys.readouterr().out
    assert preview in output
    assert "TOUCHDOWN" not in output
    assert "FIRST DOWN" not in output  # A kickoff does not earn a scrimmage first down.
    assert "down counts" not in output
    assert game.state.ball_position == 13
    assert game.state.is_home_possession is not kicking_home
    assert (game.state.home_score, game.state.away_score) == (30, 10)
    assert not outcome.touchdown


@pytest.mark.parametrize("distance,return_cell,expected", [
    ("75", "", "Touchback"), ("66", "110", "TOUCHDOWN"),
    ("66", "F + 7", "FUMBLE"), ("66", "DEF 15", "DEF 15"),
])
def test_kickoff_preview_never_rolls_unresolved_return_chains(
    distance: str, return_cell: str, expected: str,
) -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({10: "DEF 5", 18: distance})
    receiver.kickoff_return[32] = return_cell
    dice = (10, 18) if distance == "75" else (10, 18, 32)
    outcome = kick(game, True, *dice)
    assert expected in (outcome.penalty_choice.play_result_preview or "")
    assert not game.state.scoring_plays
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0

"""CLI presentation of the kickoff return-penalty choice (RULE-013)."""

from unittest.mock import patch

from paydirt.interactive_game import handle_penalty_decision
from tests.test_kickoff_return_penalty_choice import pending_return_penalty


def test_human_kicker_is_prompted_with_engine_previews(monkeypatch, capsys) -> None:
    game, pending = pending_return_penalty(kicking_home=True, cell="OFF 15")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "2")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = handle_penalty_decision(game, pending, is_human_offense=False, human_is_home=True)
    out = capsys.readouterr().out
    assert 'KO:24→"60"' in out and 'RT:31→"OFF 15"' in out and 'RT reroll:13→"30"' in out
    assert "K:0" not in out
    play_line = next(line for line in out.splitlines() if "[1] Accept PLAY result" in line)
    assert "AWAY 35" in play_line
    penalty_line = next(line for line in out.splitlines() if "[2] Accept PENALTY" in line)
    assert "1st and 10" in penalty_line and "AWAY 20" in penalty_line
    assert outcome.penalty_applied is True
    assert game.state.ball_position == 20


def test_human_kicker_may_decline(monkeypatch) -> None:
    game, pending = pending_return_penalty(kicking_home=True, cell="OFF 15")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "1")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = handle_penalty_decision(game, pending, is_human_offense=False, human_is_home=True)
    assert outcome.penalty_applied is False
    assert game.state.ball_position == 35


def test_cpu_kicker_decides_and_is_named_correctly(monkeypatch, capsys) -> None:
    game, pending = pending_return_penalty(kicking_home=True, cell="OFF 15")
    monkeypatch.setattr("builtins.input", lambda _prompt="": (_ for _ in ()).throw(AssertionError("no prompt")))
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = handle_penalty_decision(game, pending, is_human_offense=True, human_is_home=False)
    out = capsys.readouterr().out
    assert "HOME accepts penalty" in out, "the CPU kicking team (HOME) decides, not the receiver"
    assert outcome.penalty_applied is True
    assert game.state.ball_position == 20


def test_human_receiver_is_prompted_for_a_kicking_team_foul(monkeypatch, capsys) -> None:
    game, pending = pending_return_penalty(kicking_home=True, cell="DEF 15")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "2")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = handle_penalty_decision(game, pending, is_human_offense=True, human_is_home=False)
    out = capsys.readouterr().out
    assert "[2] Accept PENALTY" in out
    assert outcome.penalty_applied is True
    assert game.state.ball_position == 50

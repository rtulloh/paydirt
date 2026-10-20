"""CLI presentation of kickoff return penalties: automatic, except the recovered-fumble choice."""

from unittest.mock import patch

from paydirt.interactive_game import handle_penalty_decision
from tests.test_kickoff_return_penalties import kick, kick_game


def pending_fumble_choice():
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({31: "OFF 15", 13: "F + 17"})
    pending = kick(game, True, 24, 31, 13, 30)
    assert pending.pending_penalty_decision is True
    return game, pending


def test_human_kicker_is_offered_the_recovery_or_the_penalty(monkeypatch, capsys) -> None:
    game, pending = pending_fumble_choice()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "1")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = handle_penalty_decision(game, pending, is_human_offense=False, human_is_home=True)
    out = capsys.readouterr().out
    assert 'KO:24→"60"' in out and 'RT:31→"OFF 15"' in out and 'RT reroll:13→"F + 17"' in out
    assert "K:0" not in out
    play_line = next(line for line in out.splitlines() if "[1] Accept PLAY result" in line)
    assert "HOME" in play_line and "22" in play_line
    penalty_line = next(line for line in out.splitlines() if "[2] Accept PENALTY" in line)
    assert "AWAY 7" in penalty_line
    assert game.state.is_home_possession is True
    assert game.state.ball_position == 78
    assert outcome.turnover is True


def test_human_kicker_may_take_the_penalty(monkeypatch) -> None:
    game, pending = pending_fumble_choice()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "2")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        handle_penalty_decision(game, pending, is_human_offense=False, human_is_home=True)
    assert game.state.is_home_possession is False
    assert game.state.ball_position == 7


def test_cpu_kicker_keeps_the_recovery_and_is_named_correctly(monkeypatch, capsys) -> None:
    game, pending = pending_fumble_choice()
    monkeypatch.setattr("builtins.input", lambda _prompt="": (_ for _ in ()).throw(AssertionError("no prompt")))
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        handle_penalty_decision(game, pending, is_human_offense=True, human_is_home=False)
    out = capsys.readouterr().out
    assert "HOME accepts play result" in out, "the CPU kicking team (HOME) decides, not the receiver"
    assert game.state.is_home_possession is True
    assert game.state.ball_position == 78

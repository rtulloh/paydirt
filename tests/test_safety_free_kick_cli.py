"""A safety free kick must resolve its kickoff penalty before the next snap."""
import pytest

from paydirt import interactive_game
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


def _outcome(description: str, *, pending: bool) -> PlayOutcome:
    play_type = PlayType.KICKOFF
    result = PlayResult(result_type=ResultType.YARDS, description=description)
    return PlayOutcome(
        play_type=play_type,
        defense_type=DefenseType.STANDARD,
        result=result,
        description=description,
        pending_penalty_decision=pending,
        penalty_choice=PenaltyChoice(play_result=result, offended_team="offense")
        if pending else None,
    )


def test_safety_free_kick_resolves_kickoff_penalty_for_human_receiver(monkeypatch) -> None:
    game = make_sample_game()
    pending = _outcome("PENALTY on kickoff", pending=True)
    resolved = _outcome("kick resolved", pending=False)
    monkeypatch.setattr(game, "safety_free_kick", lambda use_punt=False: pending)

    calls = []

    def fake_handle(game_arg, outcome, is_human_offense, human_is_home):
        calls.append((outcome, is_human_offense, human_is_home))
        return resolved

    monkeypatch.setattr(interactive_game, "handle_penalty_decision", fake_handle)
    monkeypatch.setattr(
        interactive_game, "_complete_touchdown_sequence",
        lambda game_arg, outcome, human_is_home, cpu_ai: outcome,
    )

    outcome = interactive_game.handle_safety_free_kick(
        game, kicking_home=False, human_is_home=True, cpu_ai=None
    )

    assert outcome is resolved
    assert calls == [(pending, True, True)]


def test_safety_free_kick_without_penalty_skips_decision(monkeypatch) -> None:
    game = make_sample_game()
    resolved = _outcome("kick resolved", pending=False)
    monkeypatch.setattr(game, "safety_free_kick", lambda use_punt=False: resolved)
    monkeypatch.setattr(
        interactive_game, "_complete_touchdown_sequence",
        lambda game_arg, outcome, human_is_home, cpu_ai: outcome,
    )
    monkeypatch.setattr(
        interactive_game, "handle_penalty_decision",
        lambda *args, **kwargs: pytest.fail("No penalty decision should be needed"),
    )

    assert interactive_game.handle_safety_free_kick(
        game, kicking_home=False, human_is_home=True, cpu_ai=None
    ) is resolved

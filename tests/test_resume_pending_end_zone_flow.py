"""FLOW-027: resumed end-zone interception scoring receives its follow-up kick."""

from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


class StopBeforeNextSnap(Exception):
    """Stop the resumed loop after checking the scoring follow-up."""


def pending_game() -> tuple[object, object]:
    """Save a home-defense end-zone interception whose return choice is pending."""
    game = make_sample_game()
    game.state.is_home_possession = False
    game.state.ball_position = 90
    game.state.quarter = 1
    game.state.time_remaining = 10
    game.set_end_zone_interception_policy(True, "ask")
    result = PlayResult(
        result_type=ResultType.INTERCEPTION,
        yards=14,
        turnover=True,
        raw_result="INT 14",
        dice_roll=10,
    )
    with patch(
        "paydirt.game_engine.resolve_play_with_penalties",
        return_value=PenaltyChoice(play_result=result),
    ):
        pending = game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD
        )
    assert pending.pending_end_zone_interception_return_decision is True
    return game, pending


def resume_with_return_cell(
    monkeypatch: pytest.MonkeyPatch, tmp_path, cell: str, rolls: list[tuple[int, str]],
) -> dict:
    game, pending = pending_game()
    save_path = tmp_path / "pending-end-zone.json"
    save_game(game, str(save_path), human_is_away=False, human_is_home=True)

    attempts = Mock(return_value=(True, "Synthetic extra point"))
    kicks = Mock(return_value=PlayOutcome(
        PlayType.KICKOFF,
        DefenseType.STANDARD,
        PlayResult(ResultType.YARDS),
        description="Synthetic kickoff",
    ))
    free_kicks = Mock(return_value=PlayOutcome(
        PlayType.KICKOFF,
        DefenseType.STANDARD,
        PlayResult(ResultType.YARDS),
        description="Synthetic safety free kick",
    ))
    real_load_game = load_game

    def load_for_resume(path: str):
        loaded, away, home, pending_score = real_load_game(path)
        loaded.state.home_chart.special_teams.interception_return = {26: cell}
        loaded.state.home_chart.special_teams.extra_point_no_good = []
        loaded.attempt_extra_point = attempts
        loaded.kickoff = kicks
        loaded.safety_free_kick = free_kicks
        return loaded, away, home, pending_score

    monkeypatch.setattr(cli, "load_game", load_for_resume)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: Mock(use_analysis=False))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_box_score", lambda *args: None)
    monkeypatch.setattr(cli, "display_game_status", Mock(side_effect=StopBeforeNextSnap))
    monkeypatch.setattr("builtins.input", lambda prompt="": "R" if "T/R" in prompt else "")

    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls),
        pytest.raises(StopBeforeNextSnap),
    ):
        cli.resume_game(str(save_path), compact=True)
    return {"attempts": attempts, "kicks": kicks, "free_kicks": free_kicks, "game": game}


def test_resumed_return_touchdown_runs_try_then_kickoff(monkeypatch, tmp_path) -> None:
    """A return TD restored from a save must not fall straight into a snap."""
    calls = resume_with_return_cell(monkeypatch, tmp_path, "TD", [(26, "return")])
    assert calls["attempts"].called
    assert calls["kicks"].called
    assert not calls["free_kicks"].called


def test_resumed_return_safety_runs_free_kick(monkeypatch, tmp_path) -> None:
    """A return safety restored from a save must run the free kick."""
    calls = resume_with_return_cell(monkeypatch, tmp_path, "F - 6", [(26, "fumble"), (30, "lost")])
    assert calls["free_kicks"].called
    assert not calls["attempts"].called
    assert not calls["kicks"].called

"""AI wiring regressions using public sample charts and deterministic plays."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional
from unittest.mock import Mock

import pytest

from paydirt import interactive_game as cli
from paydirt.ai_analysis import OpponentModel
from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType, parse_result_string
from tests.game_fixtures import make_sample_game


class StopSession(Exception):
    """Stop a real CLI loop without saving or completing a game."""


@pytest.fixture
def cli_session(monkeypatch: pytest.MonkeyPatch) -> Callable[..., tuple]:
    game = make_sample_game()
    created = []
    defended = []
    original_init = ComputerAI.__init__

    def track_init(self: ComputerAI, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        created.append(self)

    def defend(self: ComputerAI, engine: PaydirtGameEngine) -> DefenseType:
        defended.append(self)
        return DefenseType.STANDARD

    monkeypatch.setattr(ComputerAI, "__init__", track_init)
    monkeypatch.setattr(ComputerAI, "select_defense", defend)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, not human_home[0], human_home[0], None))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME", "away_score": 0,
        "home_score": 0, "quarter": 1, "time_remaining": 15.0,
    })
    monkeypatch.setattr(cli, "load_ai_data", lambda *args: None)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_play_result", lambda *args: None)
    monkeypatch.setattr(cli, "create_easy_mode_helper", lambda *args: object())
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli.random, "choice", lambda choices: choices[0])
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(game, "kickoff", lambda **kwargs: PlayOutcome(
        PlayType.KICKOFF, DefenseType.STANDARD, parse_result_string("0")))
    human_home = [True]

    def run(
        resume: bool, difficulty: str, is_home: bool,
        after_play: Callable[[PaydirtGameEngine], None] | None = None,
    ) -> tuple:
        human_home[0] = is_home
        game.state.is_home_possession = is_home
        game.state.down, game.state.yards_to_go = 3, 7
        selections = iter([game.state.home_chart, game.state.away_chart] if is_home
                          else [game.state.away_chart, game.state.home_chart])
        monkeypatch.setattr(cli, "select_team", lambda *args, **kwargs: next(selections))
        # Choose the same home/away position in the new-game prompt.
        monkeypatch.setattr("builtins.input", lambda prompt="":
                            ("H" if is_home else "A") if prompt == "\nYour choice: " else "")
        status_count = 0

        def status(*args: Any) -> None:
            nonlocal status_count
            status_count += 1
            if status_count > 1:
                raise StopSession

        def execute(*args: Any, **kwargs: Any) -> PlayOutcome:
            if after_play is None:
                raise StopSession
            after_play(game)
            return PlayOutcome(PlayType.SHORT_PASS, DefenseType.STANDARD,
                               parse_result_string("8"), yards_gained=8, down_before=3,
                               turnover=game.state.is_home_possession != is_home)

        monkeypatch.setattr(cli, "display_game_status", status)
        monkeypatch.setattr(cli, "get_human_offense_play", lambda *args:
                            (PlayType.SHORT_PASS, False, False, False, False, False))
        monkeypatch.setattr(game, "run_play_with_penalty_procedure", execute)
        with pytest.raises(StopSession):
            if resume:
                cli.resume_game("unused-save.json", difficulty=difficulty)
            else:
                cli.run_interactive_game(difficulty=difficulty)
        return game, created, defended

    return run


@pytest.mark.parametrize("resume", [False, True], ids=["new", "resume"])
@pytest.mark.parametrize("is_home", [False, True], ids=["human-away", "human-home"])
@pytest.mark.parametrize("difficulty,aggression", [("easy", .3), ("medium", .5), ("hard", .7)])
def test_cli_uses_configured_ai(
    cli_session: Callable[..., tuple], resume: bool, is_home: bool,
    difficulty: str, aggression: float,
) -> None:
    game, created, defended = cli_session(resume, difficulty, is_home)
    assert len(created) == 1, "Defensive calls must not create a default AI"
    ai = created[0]
    assert defended == [ai]
    assert ai.aggression == aggression
    assert ai.ai_behavior is game.season_rules.ai_behavior
    assert ai.use_analysis is (difficulty == "hard")
    assert (ai.opponent_model is not None) is (difficulty == "hard")
    if difficulty == "hard":
        assert ai.team_analyzer.team_chart is (game.state.away_chart if is_home else game.state.home_chart)
    else:
        assert ai.team_analyzer is None


@pytest.mark.parametrize("resume", [False, True], ids=["new", "resume"])
@pytest.mark.parametrize("is_home", [False, True])
@pytest.mark.parametrize("transition", ["first-down", "turnover", "unchanged"])
def test_cli_learns_preplay_situation(
    cli_session: Callable[..., tuple], resume: bool, is_home: bool, transition: str,
) -> None:
    def change_state(game: PaydirtGameEngine) -> None:
        if transition != "unchanged":
            game.state.down, game.state.yards_to_go = 1, 10
        if transition == "turnover":
            game.state.is_home_possession = not is_home

    _, created, _ = cli_session(resume, "hard", is_home, change_state)
    tracker = created[0].opponent_model.tracker
    assert tracker.get_tendency(3, 7).pass_plays == 1
    assert sum(len(plays) for plays in tracker.situation_plays.values()) == 1
    assert tracker.get_tendency(1, 10).total_plays == 0


@pytest.mark.parametrize("is_home_possession", [False, True])
@pytest.mark.parametrize("opponent_lead,expected", [(7, DefenseType.STANDARD), (-7, DefenseType.LONG_PASS)])
def test_hard_defense_uses_opponent_score(
    is_home_possession: bool, opponent_lead: int, expected: DefenseType,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = is_home_possession
    game.state.quarter, game.state.time_remaining = 4, 3.0
    game.state.home_score = 14 + (opponent_lead if is_home_possession else 0)
    game.state.away_score = 14 + (opponent_lead if not is_home_possession else 0)
    ai = ComputerAI(use_analysis=True)
    assert ai.select_defense(game) == expected
    assert ai.opponent_model.score_differential_history == [opponent_lead]


@pytest.mark.parametrize("previous_lead", [-7, 7])
@pytest.mark.parametrize("quarter,time_left,lead", [(4, 3., 0), (3, 3., 7), (4, 5., -7)])
def test_model_resets_situational_flags(
    previous_lead: int, quarter: int, time_left: float, lead: int,
) -> None:
    model = OpponentModel()
    model.update_game_state(previous_lead, 4, 3.)
    model.tracker.get_defense_recommendation = Mock(return_value="D")
    assert model.predict_defense(3, 7, lead, quarter, time_left) == "D"
    assert not model.is_protecting_lead
    assert not model.is_comeback_mode
    model.tracker.get_defense_recommendation.assert_called_once_with(3, 7)


@pytest.mark.parametrize("lead,expected", [(7, "A"), (-7, "E")])
def test_model_retains_opponent_perspective_contract(lead: int, expected: str) -> None:
    assert OpponentModel().predict_defense(3, 7, lead, 4, 3.) == expected

"""FG penalty choices must not consume scrimmage time or double-kick at halftime."""

from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def prepare_kick(home: bool, quarter: int, seconds: int) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    game.state.two_minute_warning_called = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 95, 4, 3
    game.state.home_score, game.state.away_score = 14, 2
    game.state.possession_team.special_teams.field_goal.update({15: "DEF 5", 29: "8"})
    return game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True], ids=["direct", "procedure"])
@pytest.mark.parametrize("quarter", [2, 4])
@pytest.mark.parametrize("seconds", [5, 21])
@pytest.mark.parametrize("penalties", [False, True], ids=["clean-control", "declined-penalties"])
@pytest.mark.parametrize("raw", ["8", "4"], ids=["good", "miss"])
def test_field_goal_kept_after_penalties_uses_normal_kick_time(
    home: bool, procedure: bool, quarter: int, seconds: int, penalties: bool, raw: str,
) -> None:
    game = prepare_kick(home, quarter, seconds)
    game.state.possession_team.special_teams.field_goal[29] = raw
    rolls = [(15, "penalty"), (15, "penalty")] if penalties else []
    rolls.append((29, "kick"))
    with (
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls) as dice,
        patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: (low + high) / 2) as timing,
    ):
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = run(PlayType.FIELD_GOAL, DefenseType.STANDARD)
        if penalties:
            assert outcome.pending_penalty_decision
            assert game.state.time_remaining == seconds / 60
            assert not game.state.scoring_plays
            timing.assert_not_called()
            outcome = game.apply_fg_penalty_decision(outcome, accept_play=True)
        timing.assert_called_once_with(5, 10)
    assert dice.call_count == len(rolls)
    assert outcome.field_goal_made is (raw == "8")
    assert not outcome.pending_penalty_decision and not outcome.penalty_applied
    assert outcome.result.dice_roll == 29
    assert len(game.play_log) == 1
    assert len(game.state.scoring_plays) == int(raw == "8")
    if raw == "8":
        assert game.state.scoring_plays[0].quarter == quarter
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    expired = seconds <= 7.5
    assert not game.has_untimed_down()
    if expired and quarter == 2:
        assert game.state.quarter == 3 and game.state.time_remaining == 15
        assert not game.state.game_over
    else:
        assert game.state.quarter == quarter
        assert game.state.time_remaining * 60 == pytest.approx(max(0, seconds - 7.5))
        assert game.state.game_over is (expired and quarter == 4)


class StopSession(Exception):
    """Stop before the next scrimmage play without saving anything."""


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("home_kicking", [False, True])
@pytest.mark.parametrize("seconds", [5, 21], ids=["half-expires", "time-remains"])
def test_cli_field_goal_does_not_spend_next_half_on_a_duplicate_kickoff(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, home_kicking: bool, seconds: int,
) -> None:
    game = prepare_kick(home_kicking, 2, seconds)
    kicks = []
    halves = []
    statuses = 0
    ai = Mock(use_analysis=False)
    ai.select_offense_with_clock_management.return_value = (PlayType.FIELD_GOAL, False, False, False, 0, False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout.return_value = False
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=[game.state.home_chart, game.state.away_chart]))
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, False, True, None))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: dict(
        saved_at="synthetic", away_team="AWAY", home_team="HOME", away_score=2, home_score=14,
        quarter=2, time_remaining=seconds / 60,
    ))
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_play_result", lambda *args: None)
    monkeypatch.setattr(cli, "display_box_score", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args:
                        (PlayType.FIELD_GOAL, False, False, False, False, False))
    monkeypatch.setattr(cli, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, False))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "handle_penalty_decision", lambda engine, outcome, *args:
                        engine.apply_fg_penalty_decision(outcome, accept_play=True))
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)

    def answer(prompt: str = "") -> str:
        if "2nd half kickoff" in prompt:
            halves.append(game.state.time_remaining * 60)
        return ""

    def status(*args: object) -> None:
        nonlocal statuses
        statuses += 1
        if statuses > 1:
            raise StopSession

    def kickoff(*, kicking_home: bool) -> PlayOutcome:
        opening = not resumed and not kicks
        kicks.append((game.state.quarter, bool(halves), opening))
        if not opening:
            game._use_time(7.5)
            game.state.is_home_possession = not kicking_home
            game.state.ball_position = 27
            game.state.down, game.state.yards_to_go = 1, 10
        return PlayOutcome(PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
                           description="Synthetic kickoff")

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(cli, "display_game_status", status)
    monkeypatch.setattr(game, "kickoff", kickoff)
    with (
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(15, "penalty"), (15, "penalty"), (29, "kick")]),
        patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: (low + high) / 2),
        pytest.raises(StopSession),
    ):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()
    actual_kicks = [(quarter, halftime) for quarter, halftime, opening in kicks if not opening]
    if seconds == 5:
        assert actual_kicks == [(3, True)], "Only the scheduled second-half kickoff may run in Q3"
        assert halves == [900], "The second-half clock must be untouched at the halftime prompt"
        assert game.state.quarter == 3
        assert game.state.time_remaining * 60 == pytest.approx(892.5)
    else:
        assert actual_kicks == [(2, False)]
        assert not halves
        assert game.state.quarter == 2
        assert game.state.time_remaining * 60 == pytest.approx(6)
    assert len(game.state.scoring_plays) == 1
    assert not game.state.home_stats.penalties and not game.state.away_stats.penalties

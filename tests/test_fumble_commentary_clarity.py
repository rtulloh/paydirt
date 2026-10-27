"""Synthetic regressions for clear offensive-recovery commentary and defense calls."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from paydirt.result_formatter import ResultFormatter
from tests.game_fixtures import make_sample_game


def recovery_play(
    home: bool, flow: str, recovery: int = 17, advance: str = "11",
) -> tuple[PaydirtGameEngine, PlayOutcome, str, str]:
    """Gain nine from the opponent 13, then resolve only synthetic recovery cells."""
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 87
    game.state.down, game.state.yards_to_go = 3, 12
    game.state.quarter, game.state.time_remaining = 2, 58 / 60
    offense = game.state.possession_team.peripheral.short_name
    defense = game.state.defense_team.peripheral.short_name
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)
    game.state.possession_team.special_teams.interception_return[11] = advance
    result = PlayResult(ResultType.FUMBLE, yards=9, raw_result="F + 9",
                        dice_roll=26, description="FUMBLE!")
    options = [PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty")] if flow == "declined" else []
    choice = PenaltyChoice(result, penalty_options=options, offended_team="offense")
    rolls = [(recovery, "recovery")]
    if recovery in (17, 18, 19):
        rolls.append((11, "advance"))
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as dice,
    ):
        run = game.run_play if flow == "direct" else game.run_play_with_penalty_procedure
        outcome = run(PlayType.SHORT_PASS, DefenseType.LONG_PASS)
        if flow == "declined":
            assert outcome.pending_penalty_decision
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
        assert dice.call_count == len(rolls)
    return game, outcome, offense, defense


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined"])
@pytest.mark.parametrize("recovery", [17, 18, 19])
def test_offensive_recovery_description_separates_rolls_and_positions(
    home: bool, flow: str, recovery: int,
) -> None:
    game, outcome, offense, defense = recovery_play(home, flow, recovery)
    assert outcome.touchdown and not outcome.turnover and not outcome.safety
    assert outcome.yards_gained == 13
    assert outcome.result.fumble_spot == 96
    assert outcome.result.fumble_return_dice == 11
    assert outcome.result.fumble_return_yards == 4
    assert game.state.is_home_possession is home
    assert (game.state.home_score, game.state.away_score) == ((6, 0) if home else (0, 6))
    assert game.state.offense_stats.total_yards == 13
    assert game.state.offense_stats.first_downs == 1
    assert game.state.offense_stats.fumbles_lost == 0
    assert f"{defense} 4" in outcome.description
    assert "at the 96" not in outcome.description
    assert f"Recovery: {recovery}→11" not in outcome.description
    assert "Return roll 11" in outcome.description
    assert 'chart "11"' in outcome.description
    assert "4 yard" in outcome.description
    assert offense in outcome.description
    formatted = ResultFormatter(offense, defense).format(outcome)
    assert formatted.commentary == outcome.description


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined"])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
def test_offensive_recovery_cli_has_one_touchdown_announcement(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, flow: str, view: str,
) -> None:
    game, outcome, offense, defense = recovery_play(home, flow)
    if view == "legacy-compact":
        outcome.transaction = None
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    with patch("paydirt.commentary.Commentary.generate", return_value="WRONG SCORER") as generate:
        cli.display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.LONG_PASS,
                                game.state.home_chart, offense_was_home=home)
    output = capsys.readouterr().out
    generate.assert_not_called()
    assert output.upper().count("TOUCHDOWN") == 1
    assert "9 yards before fumble" in output
    assert f"Fumble at {defense} 4, recovered by {offense}" in output
    assert f"advanced 4 yards to {defense} end zone" in output
    assert "net gain 13 yards" in output
    assert "at the 96" not in output
    assert "Recovery: 17→11" not in output
    assert "WRONG SCORER" not in output
    if view != "full":
        headline = next(line for line in output.splitlines() if line.startswith("►"))
        assert "FUMBLE" in headline and "TOUCHDOWN" in headline
        assert "9 yards before" not in headline


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("recovery,advance,expected_yards", [(17, "2", 11), (20, "11", 9), (33, "11", 9)])
def test_non_scoring_recovery_controls(home: bool, recovery: int, advance: str, expected_yards: int) -> None:
    game, outcome, _, _ = recovery_play(home, "procedure", recovery, advance)
    assert not outcome.touchdown and not outcome.safety
    assert outcome.yards_gained == expected_yards
    assert outcome.turnover is (recovery == 33)
    assert game.state.is_home_possession is (not home if recovery == 33 else home)
    assert game.state.home_score == game.state.away_score == 0


class ReachedEngine(Exception):
    """Stop a real interactive loop after its call announcements."""


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("human_home", [False, True])
@pytest.mark.parametrize("down", [3, 4])
@pytest.mark.parametrize("compact", [False, True])
def test_defense_call_is_named_and_confirmed_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    resumed: bool, human_home: bool, down: int, compact: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = not human_home
    game.state.down, game.state.yards_to_go = down, 12
    ai = Mock(use_analysis=False)
    ai.select_offense_with_clock_management.return_value = (
        PlayType.SHORT_PASS, False, False, False, 0, False)
    ai.should_call_timeout_on_offense.return_value = False
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_game_status", lambda *args: None)
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "_complete_touchdown_sequence", lambda game, outcome, *args: outcome)
    monkeypatch.setattr("builtins.input", lambda prompt="": (
        "A" if prompt == "\nYour choice: " and not human_home else ""))
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    kickoff = SimpleNamespace(pending_penalty_decision=False, description="Synthetic kickoff")
    monkeypatch.setattr(game, "kickoff", lambda **kwargs: kickoff)
    charts = [game.state.home_chart, game.state.away_chart] if human_home else [
        game.state.away_chart, game.state.home_chart]
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=charts))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME", "away_score": 0, "home_score": 0,
        "quarter": 1, "time_remaining": 15})
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, not human_home, human_home, None))
    monkeypatch.setattr(game, "run_play_with_penalty_procedure", Mock(side_effect=ReachedEngine))
    with pytest.raises(ReachedEngine):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()
    output = capsys.readouterr().out
    assert output.count("Defense: Long Pass (E)") == 1
    assert "You called:" not in output
    assert output.count("Offense runs: Short Pass") == 1


@pytest.mark.parametrize("home", [False, True])
def test_compact_recovery_trace_keeps_raw_chart_and_actual_advance(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, home: bool,
) -> None:
    game, outcome, _, _ = recovery_play(home, "procedure")
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    cli.display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.LONG_PASS,
                            game.state.home_chart, offense_was_home=home)
    trace = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("  (O:"))
    assert 'R:17→"kept"' in trace
    assert 'Ret:11→4 (chart "11")' in trace

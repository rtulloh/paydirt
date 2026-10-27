"""Synthetic regressions for authoritative fourth-down outcome announcements."""

from types import SimpleNamespace
from unittest.mock import Mock

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
from tests.game_fixtures import make_sample_game


def fourth_down_game(home: bool = True) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 65
    game.state.down = 4
    game.state.yards_to_go = 1
    game.state.time_remaining = 10
    return game


def resolve_scenario(
    game: PaydirtGameEngine, monkeypatch: pytest.MonkeyPatch, scenario: str,
    procedure: bool = True,
) -> PlayOutcome:
    kind, yards = {
        "offsetting": (ResultType.YARDS, 0),
        "accepted": (ResultType.INCOMPLETE, 0),
        "declined": (ResultType.YARDS, 0),
        "failed": (ResultType.YARDS, 0),
        "incomplete": (ResultType.INCOMPLETE, 0),
        "sack": (ResultType.SACK, -3),
        "converted": (ResultType.YARDS, 2),
        "touchdown": (ResultType.YARDS, 35),
        "interception": (ResultType.INTERCEPTION, 5),
        "fumble-kept": (ResultType.FUMBLE, 0),
        "fumble-lost": (ResultType.FUMBLE, 0),
    }[scenario]
    result = PlayResult(
        kind, yards=yards, raw_result="F" if kind == ResultType.FUMBLE else str(yards),
        description="Synthetic play", turnover=kind == ResultType.INTERCEPTION,
    )
    choice = PenaltyChoice(result, offsetting=scenario == "offsetting")
    if scenario in ("accepted", "declined"):
        choice.penalty_options = [PenaltyOption(
            penalty_type="OFF", raw_result="OFF 5", yards=5,
            description="Synthetic offensive penalty",
        )]
        choice.offended_team = "defense"
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 19)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (
        12 if scenario != "fumble-lost" else 30, "Synthetic recovery"))
    game.state.defense_team.special_teams.interception_return = {12: "0", 30: "0"}
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 30)
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    play = PlayType.MEDIUM_PASS if kind in (ResultType.INCOMPLETE, ResultType.INTERCEPTION, ResultType.SACK) else PlayType.LINE_PLUNGE
    if not procedure:
        return game.run_play(play, DefenseType.STANDARD)
    outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
    if scenario in ("accepted", "declined"):
        assert outcome.pending_penalty_decision
        assert not getattr(outcome, "turnover_on_downs", False)
        outcome = game.apply_penalty_decision(outcome, accept_play=scenario == "declined")
    return outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("scenario", [
    "failed", "incomplete", "sack", "converted", "touchdown",
    "interception", "fumble-kept", "fumble-lost",
])
def test_engine_identifies_actual_turnover_on_downs(
    monkeypatch: pytest.MonkeyPatch, home: bool, procedure: bool, scenario: str,
) -> None:
    game = fourth_down_game(home)
    outcome = resolve_scenario(game, monkeypatch, scenario, procedure)
    expected = scenario in ("failed", "incomplete", "sack", "fumble-kept")
    assert getattr(outcome, "turnover_on_downs", False) is expected
    assert game.state.is_home_possession is (not home if expected or scenario in ("interception", "fumble-lost") else home)
    assert game.state.home_stats.turnovers + game.state.away_stats.turnovers == int(scenario in ("interception", "fumble-lost"))


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("scenario", ["offsetting", "accepted", "declined", "failed", "converted", "interception", "fumble-lost"])
def test_display_uses_resolved_fourth_down_outcome(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, compact: bool, scenario: str,
) -> None:
    game = fourth_down_game()
    outcome = resolve_scenario(game, monkeypatch, scenario)
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_play_result(
        game, outcome, outcome.play_type, outcome.defense_type,
        game.state.home_chart, offense_was_home=True,
    )
    output = capsys.readouterr().out
    assert ("TURNOVER ON DOWNS" in output) is (scenario in ("declined", "failed"))
    if scenario == "offsetting":
        assert "replayed" in output.lower()
        assert game.state.is_home_possession
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (65, 4, 1)


class ReachedNextSnap(Exception):
    """Stop after the CLI has printed every announcement for the first play."""


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("scenario", ["offsetting", "accepted", "failed"])
def test_cli_loop_announces_only_actual_turnover_on_downs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    resumed: bool, compact: bool, scenario: str,
) -> None:
    game = fourth_down_game()
    ai = Mock(use_analysis=False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout_on_defense.return_value = False
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.LINE_PLUNGE, False, False, False, False, False))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=[game.state.home_chart, game.state.away_chart]))
    monkeypatch.setattr(game, "kickoff", lambda **kwargs: SimpleNamespace(
        pending_penalty_decision=False, touchdown=False, description="Synthetic kickoff"))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME", "away_score": 0,
        "home_score": 0, "quarter": 1, "time_remaining": 10})
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, False, True, None))
    original_run = game.run_play_with_penalty_procedure
    displayed = False
    original_display = cli.display_play_result

    def display(*args, **kwargs) -> None:
        nonlocal displayed
        original_display(*args, **kwargs)
        displayed = True

    def status(*args, **kwargs) -> None:
        if displayed:
            raise ReachedNextSnap

    def play(*args, **kwargs) -> PlayOutcome:
        monkeypatch.setattr(game, "run_play_with_penalty_procedure", original_run)
        outcome = resolve_scenario(game, monkeypatch, scenario)
        return outcome

    monkeypatch.setattr(game, "run_play_with_penalty_procedure", play)
    monkeypatch.setattr(cli, "display_play_result", display)
    monkeypatch.setattr(cli, "display_game_status", status)
    with pytest.raises(ReachedNextSnap):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()
    output = capsys.readouterr().out
    assert output.count("TURNOVER ON DOWNS") == int(scenario == "failed")
    if scenario != "failed":
        assert game.state.is_home_possession
        assert game.state.down == 4


@pytest.mark.parametrize("play", [PlayType.QB_SNEAK, PlayType.HAIL_MARY, PlayType.SPIKE_BALL, PlayType.QB_KNEEL])
def test_special_scrimmage_failures_have_authoritative_flag(
    monkeypatch: pytest.MonkeyPatch, play: PlayType,
) -> None:
    game = fourth_down_game()
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (30, "Synthetic roll"))
    monkeypatch.setattr("paydirt.game_engine.resolve_qb_sneak", lambda *args: PlayResult(ResultType.YARDS, yards=0))
    monkeypatch.setattr("paydirt.game_engine.resolve_hail_mary", lambda *args: PlayResult(ResultType.INCOMPLETE))
    outcome = game.run_play(play, DefenseType.STANDARD)
    assert getattr(outcome, "turnover_on_downs", False)
    assert not game.state.is_home_possession
    assert game.state.home_stats.turnovers == 0


@pytest.mark.parametrize("play", [PlayType.PUNT, PlayType.FIELD_GOAL])
@pytest.mark.parametrize("compact", [False, True])
def test_special_teams_possession_changes_are_not_turnovers_on_downs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    play: PlayType, compact: bool,
) -> None:
    game = fourth_down_game()
    game.state.home_chart.special_teams.punt = {12: "20*"}
    game.state.home_chart.special_teams.field_goal = {12: "0"}
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (12, "Synthetic kick"))
    outcome = game.run_play(play, DefenseType.STANDARD)
    assert not outcome.turnover_on_downs
    assert not game.state.is_home_possession
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_play_result(
        game, outcome, play, outcome.defense_type,
        game.state.home_chart, offense_was_home=True,
    )
    assert "TURNOVER ON DOWNS" not in capsys.readouterr().out


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("down", [1, 2, 3])
def test_earlier_down_failure_does_not_mark_turnover(
    monkeypatch: pytest.MonkeyPatch, procedure: bool, down: int,
) -> None:
    game = fourth_down_game()
    game.state.down = down
    outcome = resolve_scenario(game, monkeypatch, "failed", procedure)
    assert not outcome.turnover_on_downs
    assert game.state.down == down + 1
    assert game.state.is_home_possession


@pytest.mark.parametrize("procedure", [False, True])
def test_fourth_down_safety_is_not_turnover_on_downs(
    monkeypatch: pytest.MonkeyPatch, procedure: bool,
) -> None:
    game = fourth_down_game()
    game.state.ball_position = 2
    outcome = resolve_scenario(game, monkeypatch, "sack", procedure)
    assert outcome.safety
    assert not outcome.turnover_on_downs


@pytest.mark.parametrize("recovered", [False, True])
def test_qb_sneak_fumble_distinguishes_recovery_from_loss(
    monkeypatch: pytest.MonkeyPatch, recovered: bool,
) -> None:
    game = fourth_down_game()
    game.state.home_chart.peripheral.fumble_recovered_range = (10, 19)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (
        12 if recovered else 30, "Synthetic sneak"))
    monkeypatch.setattr("paydirt.game_engine.resolve_qb_sneak", lambda *args: PlayResult(ResultType.FUMBLE))
    outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
    assert outcome.turnover_on_downs is recovered
    assert not game.state.is_home_possession
    assert game.state.home_stats.turnovers == int(not recovered)

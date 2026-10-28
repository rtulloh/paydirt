"""SPIKE-002: a useful defensive timeout wins before a planned S modifier."""

from __future__ import annotations

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


class ReachedDisplay(Exception):
    """Stop after the real engine and penalty/timeout procedures finish."""


def run_cli_play(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine,
    resumed: bool, human_home: bool, choice: PenaltyChoice,
    accept_play: bool = True,
) -> PlayOutcome:
    ai = Mock(use_analysis=False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout_on_defense.return_value = True
    ai.should_call_timeout_on_offense.return_value = False
    monkeypatch.setattr("paydirt.computer_ai.computer_should_call_timeout_on_offense", lambda *args: False)
    ai.select_offense_with_clock_management.return_value = (
        PlayType.MEDIUM_PASS, False, False, False, 0, True)
    monkeypatch.setattr(cli, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, True))
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_game_status", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.MEDIUM_PASS, False, False, False, False, True))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "_complete_touchdown_sequence", lambda game, outcome, *args: outcome)
    monkeypatch.setattr("builtins.input", lambda prompt="": (
        "A" if prompt == "\nYour choice: " and not human_home else ""))
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    monkeypatch.setattr(game, "kickoff", lambda **kwargs: SimpleNamespace(
        pending_penalty_decision=False, description="Synthetic kickoff"))
    charts = [game.state.home_chart, game.state.away_chart] if human_home else [
        game.state.away_chart, game.state.home_chart]
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=charts))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME", "away_score": 0,
        "home_score": 0, "quarter": 4, "time_remaining": 1})
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, not human_home, human_home, None))
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: (low + high) / 2)
    seen = []

    def decide(engine: PaydirtGameEngine, outcome: PlayOutcome, *args) -> PlayOutcome:
        assert outcome.pending_penalty_decision
        assert not outcome.timeout_used and not outcome.spike_used
        assert engine.state.down == 1
        assert engine.state.time_remaining == 1
        assert not engine.play_log
        return engine.apply_penalty_decision(outcome, accept_play)

    def display(engine: PaydirtGameEngine, outcome: PlayOutcome, *args) -> None:
        seen.append(outcome)
        raise ReachedDisplay

    monkeypatch.setattr(cli, "handle_penalty_decision", decide)
    monkeypatch.setattr(cli, "display_play_result", display)
    with pytest.raises(ReachedDisplay):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()
    return seen[0]


@pytest.fixture(params=[False, True], ids=["human-away", "human-home"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 50
    engine.state.down = 1
    engine.state.yards_to_go = 10
    engine.state.quarter = 4
    engine.state.time_remaining = 1
    engine.state.two_minute_warning_called = True
    engine.state.home_score, engine.state.away_score = 21, 7
    return engine


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("available", [0, 1])
@pytest.mark.parametrize("case", ["short", "first-down", "incomplete", "oob"])
def test_cli_defensive_timeout_cancels_only_an_eligible_spike(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine,
    resumed: bool, available: int, case: str,
) -> None:
    human_home = game.state.is_home_possession
    if human_home:
        game.state.away_timeouts = available
    else:
        game.state.home_timeouts = available
    result = PlayResult(ResultType.YARDS, yards=14 if case == "first-down" else 4)
    if case == "incomplete":
        result = PlayResult(ResultType.INCOMPLETE)
    elif case == "oob":
        result.out_of_bounds = True
    outcome = run_cli_play(monkeypatch, game, resumed, human_home, PenaltyChoice(result))
    eligible = case in ("short", "first-down")
    assert outcome.timeout_used is (eligible and bool(available))
    assert outcome.spike_used is (eligible and not available)
    assert game.state.defense_timeouts == (0 if eligible else available)
    assert game.state.offense_timeouts == 3
    expected_down = (1 if case == "first-down" else 2) if (available or not eligible) else 3
    assert game.state.down == outcome.down_after == expected_down
    assert game.state.is_home_possession is human_home
    expected_time = 1 - (.167 if available or not eligible else .333)
    if case == "incomplete":
        expected_time = 1 - 5 / 60  # AI-007: incompletion needs neither procedure.
    assert game.state.time_remaining == pytest.approx(expected_time, abs=.001)
    if eligible and available:
        assert "defensive timeout" in outcome.description.lower()
        assert "spike cancelled" in outcome.description.lower()
    assert len(game.play_log) == len(game.offensive_call_history) == 1
    assert outcome.transaction.final_down == game.state.down


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("accept_play", [False, True])
@pytest.mark.parametrize("available", [0, 1])
def test_cli_penalty_decision_precedes_timeout_and_spike_arbitration(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine,
    resumed: bool, accept_play: bool, available: int,
) -> None:
    home = game.state.is_home_possession
    if home:
        game.state.away_timeouts = available
    else:
        game.state.home_timeouts = available
    choice = PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4),
        penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "synthetic foul")],
        offended_team="offense",
    )
    outcome = run_cli_play(monkeypatch, game, resumed, home, choice, accept_play)
    assert outcome.timeout_used is (accept_play and bool(available))
    assert outcome.spike_used is (accept_play and not available)
    assert game.state.defense_timeouts == (0 if accept_play else available)
    assert game.state.down == outcome.down_after == ((2 if available else 3) if accept_play else 1)
    assert game.state.ball_position == (54 if accept_play else 55)
    assert len(game.play_log) == len(game.offensive_call_history) == 1


@pytest.mark.parametrize("available", [0, 1])
def test_halftime_arbitration_uses_old_half_budgets_and_preserves_spike_fallback(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine, available: int,
) -> None:
    game.state.quarter = 2
    game.state.time_remaining = .5
    home = game.state.is_home_possession
    game.state.home_timeouts, game.state.away_timeouts = ((2, available) if home else (available, 2))
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4)))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 35)
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True, call_defensive_timeout=True,
    )
    assert outcome.timeout_used is bool(available)
    assert outcome.spike_used is (not available)
    assert game.state.quarter == 2
    assert game.state.defense_timeouts == 0
    assert game.state.offense_timeouts == 2
    assert game.state.time_remaining == pytest.approx(.5 - (.167 if available else .333))
    assert game.state.down == outcome.down_after == (2 if available else 3)


def test_two_minute_warning_needs_neither_timeout_nor_spike(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine,
) -> None:
    game.state.time_remaining = 2.25
    game.state.two_minute_warning_called = False
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4)))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 35)
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True, call_defensive_timeout=True,
    )
    assert game.state.two_minute_warning_called
    assert not outcome.timeout_used and not outcome.spike_used
    assert game.state.time_remaining == 2
    assert game.state.down == outcome.down_after == 2
    assert game.state.defense_timeouts == 3


@pytest.mark.parametrize("time_left", [.25, .333])
def test_unavailable_timeout_cannot_spike_after_half_has_irrevocably_ended(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine, time_left: float,
) -> None:
    game.state.quarter = 2
    game.state.time_remaining = time_left
    game.state.home_timeouts = game.state.away_timeouts = 0
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4)))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 35)
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True, call_defensive_timeout=True,
    )
    assert not outcome.timeout_used and not outcome.spike_used
    assert game.state.quarter == 3
    assert game.state.time_remaining == 15
    assert game.state.down == outcome.down_after == 2
    assert game.state.home_timeouts == game.state.away_timeouts == 3


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("available", [0, 1])
def test_human_defensive_at_takes_priority_over_cpu_spike(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine,
    resumed: bool, available: int,
) -> None:
    offense_home = game.state.is_home_possession
    if offense_home:
        game.state.away_timeouts = available
    else:
        game.state.home_timeouts = available
    outcome = run_cli_play(
        monkeypatch, game, resumed, not offense_home,
        PenaltyChoice(PlayResult(ResultType.YARDS, yards=4)),
    )
    assert outcome.timeout_used is bool(available)
    assert outcome.defensive_timeout_used is bool(available)
    assert outcome.spike_used is (not available)
    assert game.state.down == outcome.down_after == (2 if available else 3)
    assert game.state.defense_timeouts == 0
    assert game.state.offense_timeouts == 3


@pytest.mark.parametrize("case", ["touchdown", "failed-fourth", "offsetting"])
def test_core_does_not_charge_either_procedure_after_ineligible_final_play(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine, case: str,
) -> None:
    result = PlayResult(ResultType.YARDS, yards=4)
    if case == "touchdown":
        result = PlayResult(ResultType.TOUCHDOWN, touchdown=True)
    elif case == "failed-fourth":
        game.state.down = 4
    choice = PenaltyChoice(result, offsetting=case == "offsetting")
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 35)
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True, call_defensive_timeout=True,
    )
    assert not outcome.timeout_used and not outcome.spike_used
    assert game.state.home_timeouts == game.state.away_timeouts == 3


def test_core_timeout_can_save_regulation_without_charging_spike_down(
    monkeypatch: pytest.MonkeyPatch, game: PaydirtGameEngine,
) -> None:
    game.state.time_remaining = .5
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4)))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 35)
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True, call_defensive_timeout=True,
    )
    assert outcome.defensive_timeout_used and not outcome.spike_used
    assert not game.state.game_over
    assert game.state.time_remaining == pytest.approx(.5 - .167)
    assert game.state.down == outcome.down_after == 2
    assert game.state.defense_timeouts == 2
    assert not game.apply_defensive_timeout(
        outcome, time_before_play=.5, quarter_before_play=4,
        offense_was_home=game.state.is_home_possession, two_minute_warning_before=True,
    )
    assert game.state.defense_timeouts == 2


def test_defensive_timeout_still_works_for_core_special_play_bypass(
    game: PaydirtGameEngine,
) -> None:
    outcome = game.run_play_with_penalty_procedure(
        PlayType.QB_KNEEL, DefenseType.STANDARD, call_defensive_timeout=True,
    )
    assert outcome.defensive_timeout_used and not outcome.spike_used
    assert game.state.defense_timeouts == 2
    assert game.state.offense_timeouts == 3
    assert game.state.time_remaining == pytest.approx(1 - .167)
    assert game.state.down == 2

"""Synthetic regressions for penalty timing found in the Chiefs/Raiders audit."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)
from tests.game_fixtures import make_sample_game


def prepare_game(home: bool, quarter: int, seconds: float) -> PaydirtGameEngine:
    """Use public sample charts, with every clock/scenario input explicit."""
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home
    state.quarter = quarter
    state.time_remaining = seconds / 60
    state.two_minute_warning_called = True
    state.ball_position, state.down, state.yards_to_go = 33, 1, 10
    state.home_score, state.away_score = 26, 7
    if quarter == 5:
        state.is_overtime = True
        state.ot_period = 1
        state.home_score = state.away_score = 0
    return game


def choice_for(penalty_type: str | None) -> PenaltyChoice:
    """Keep the underlying play incomplete so timing is not affected by a return."""
    result = PlayResult(ResultType.INCOMPLETE, raw_result="BLACK", description="Incomplete pass")
    if penalty_type is None:
        return PenaltyChoice(result)
    return PenaltyChoice(
        result,
        penalty_options=[PenaltyOption(
            penalty_type=penalty_type,
            raw_result=f"{penalty_type} 5",
            yards=5,
            description="Synthetic penalty",
            auto_first_down=penalty_type == "PI",
            is_pass_interference=penalty_type == "PI",
        )],
        offended_team="defense" if penalty_type == "OFF" else "offense",
    )


def apply_choice(
    game: PaydirtGameEngine, monkeypatch: pytest.MonkeyPatch,
    penalty_type: str | None, *, no_huddle: bool, accept_play: bool = False,
) -> PlayOutcome:
    resolver = Mock(return_value=choice_for(penalty_type))
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", resolver)
    before = game.state.time_remaining
    outcome = game.run_play_with_penalty_procedure(
        PlayType.MEDIUM_PASS, DefenseType.LONG_PASS, no_huddle=no_huddle,
    )
    if penalty_type is not None:
        assert outcome.pending_penalty_decision
        assert game.state.time_remaining == before  # Choosing must not consume time twice.
        assert game.state.ball_position == 33
        assert not game.has_untimed_down()
        assert not game.state.game_over
        outcome = game.apply_penalty_decision(outcome, accept_play=accept_play)
    resolver.assert_called_once()
    assert not outcome.pending_penalty_decision
    return outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter", [2, 4])
@pytest.mark.parametrize("no_huddle", [False, True], ids=["ordinary", "hurry-up"])
@pytest.mark.parametrize("resolution", ["clean", "declined", "OFF", "DEF", "PI"])
def test_penalty_resolution_preserves_requested_clock_pace(
    monkeypatch: pytest.MonkeyPatch, home: bool, quarter: int,
    no_huddle: bool, resolution: str,
) -> None:
    game = prepare_game(home, quarter, 90)
    # Deterministic midpoint: ordinary plays take 35 sec; no-huddle takes 20 sec.
    timing = Mock(side_effect=lambda low, high: (low + high) / 2)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)
    penalty_type = None if resolution == "clean" else "OFF" if resolution == "declined" else resolution
    outcome = apply_choice(
        game, monkeypatch, penalty_type,
        no_huddle=no_huddle, accept_play=resolution == "declined",
    )
    assert game.state.time_remaining * 60 == pytest.approx(90 - (20 if no_huddle else 35))
    timing.assert_called_once()
    assert game.state.quarter == quarter
    assert not game.state.game_over
    assert not game.has_untimed_down()
    assert game.state.is_home_possession is home
    accepted = resolution in ("OFF", "DEF", "PI")
    stats = game.state.offense_stats if penalty_type == "OFF" else game.state.defense_stats
    assert stats.penalties == int(accepted)
    assert stats.penalty_yards == (5 if accepted else 0)
    assert outcome.penalty_applied is accepted


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter", [2, 4, 5], ids=["half", "regulation", "overtime"])
@pytest.mark.parametrize("penalty_type", ["DEF", "PI"])
@pytest.mark.parametrize("seconds,elapsed", [
    (39, 45),  # The audited failure: snap outside the 30-sec heuristic, time expires.
    (39, 39),  # Exact expiry must extend the period too.
    (25, 25),  # Passing control inside the old threshold.
    (39, 25),  # Passing control: time remains, no extension is armed.
    (30, 25),  # Threshold must not arm a phantom untimed down with 5 sec left.
])
def test_accepted_defensive_foul_extends_only_when_time_actually_expires(
    monkeypatch: pytest.MonkeyPatch, home: bool, quarter: int,
    penalty_type: str, seconds: int, elapsed: int,
) -> None:
    game = prepare_game(home, quarter, seconds)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: elapsed)
    apply_choice(game, monkeypatch, penalty_type, no_huddle=False)
    expired = elapsed >= seconds
    assert game.has_untimed_down() is expired
    assert game.state.time_remaining * 60 == pytest.approx(max(0, seconds - elapsed))
    assert game.state.quarter == quarter
    assert not game.state.game_over
    assert game.state.is_home_possession is home
    assert game.state.defense_stats.penalties == 1
    assert game.state.defense_stats.penalty_yards == 5


@pytest.mark.parametrize("quarter", [2, 4, 5], ids=["half", "regulation", "overtime"])
@pytest.mark.parametrize("resolution", ["OFF", "declined-DEF", "declined-PI"])
def test_offensive_or_declined_foul_does_not_extend_expired_period(
    monkeypatch: pytest.MonkeyPatch, quarter: int, resolution: str,
) -> None:
    game = prepare_game(True, quarter, 39)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: 45)
    penalty_type = resolution.removeprefix("declined-")
    apply_choice(
        game, monkeypatch, penalty_type,
        no_huddle=False, accept_play=resolution.startswith("declined-"),
    )
    assert not game.has_untimed_down()
    if quarter == 2:
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15
        assert not game.state.game_over
    else:
        assert game.state.game_over
        assert game.state.time_remaining == 0


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter", [2, 4, 5])
@pytest.mark.parametrize("flow,seconds,elapsed", [
    ("direct-DEF", 39, 45), ("direct-DEF", 30, 25),
    ("direct-PI", 39, 45), ("direct-PI", 30, 25),
    ("hail-mary", 5, 10), ("hail-mary", 15, 10),
    ("offsetting", 5, 10), ("offsetting", 15, 10),
])
def test_other_defensive_foul_paths_use_actual_period_expiry(
    monkeypatch: pytest.MonkeyPatch, home: bool, quarter: int,
    flow: str, seconds: int, elapsed: int,
) -> None:
    game = prepare_game(home, quarter, seconds)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: elapsed)
    if flow == "offsetting":
        choice = choice_for("DEF")
        choice.offsetting = True
        monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
        outcome = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.LONG_PASS)
    else:
        result = PlayResult(
            ResultType.PENALTY_DEFENSE if flow == "direct-DEF" else ResultType.PASS_INTERFERENCE,
            yards=5, raw_result="DEF 5", description="Synthetic defensive foul",
        )
        monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
        monkeypatch.setattr("paydirt.game_engine.resolve_hail_mary", lambda *args: result)
        monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (39, "Hail Mary PI"))
        play = PlayType.HAIL_MARY if flow == "hail-mary" else PlayType.MEDIUM_PASS
        outcome = game.run_play(play, DefenseType.LONG_PASS)
    expired = elapsed >= seconds
    assert game.has_untimed_down() is expired
    assert ("(Untimed down)" in outcome.description) is expired
    assert outcome.description.count("(Untimed down)") == int(expired)
    assert game.state.time_remaining * 60 == pytest.approx(max(0, seconds - elapsed))
    assert game.state.quarter == quarter
    assert not game.state.game_over
    assert game.state.is_home_possession is home

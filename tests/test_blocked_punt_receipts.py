"""Blocked punts retain their physical class and clock receipt through foul choices."""

from unittest.mock import patch

import pytest

from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType, parse_result_string
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("cell,yards", [
    ("BK -8", -8), ("BK - 8", -8), ("BK\t-\t8", -8), ("bk -8", -8),
    ("BK +3", 3), ("BK 0", 0),
])
def test_blocked_kick_parser_has_its_own_class(cell: str, yards: int) -> None:
    result = parse_result_string(cell)
    assert result.result_type.value == "blocked_kick"
    assert result.yards == yards
    assert result.raw_result == cell


@pytest.mark.parametrize("cell", ["B", "B*", "B†"])
def test_breakaway_control_keeps_its_existing_class(cell: str) -> None:
    assert parse_result_string(cell).result_type.value == "breakaway"


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("foul", [None, "OFF 5", "DEF 5"])
@pytest.mark.parametrize("position,recovery,return_yards,spot,scorer", [
    (40, 20, None, 68, None),  # Own recovery short of the fourth-down marker.
    (40, 35, None, 68, None),
    (40, 17, "10", 58, None),
    (40, 37, "10", 78, None),
    (40, 19, "0", 97, "kicker"),
    (40, 39, "0", 97, "receiver"),
    (5, None, None, 20, "safety"),
])
def test_blocked_punt_completion_carries_class_and_actual_clock(
    home: bool, procedure: bool, foul: str | None, position: int,
    recovery: int | None, return_yards: str | None, spot: int, scorer: str | None,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = position, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 3 / 60
    kicker = game.state.possession_team
    receiver = game.state.defense_team
    kicker.peripheral.fumble_recovered_range = (10, 31)
    kicker.special_teams.punt = {10: foul, 11: "BK - 8"} if foul else {11: "BK - 8"}
    kicker.special_teams.interception_return = {21: return_yards or "0"}
    receiver.special_teams.interception_return = {21: return_yards or "0"}
    physical_rolls = ([] if recovery is None else [recovery]) + ([] if return_yards is None else [21])
    rolls = ([10, 11] if foul else [11]) + physical_rolls
    run = game.run_play_with_penalty_procedure if procedure else game.run_play
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in rolls]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=5),
    ):
        outcome = run(PlayType.PUNT, DefenseType.STANDARD)
        if foul:
            assert dice.call_count == 2
            assert outcome.pending_penalty_decision
            assert not game.play_log
            assert game.state.time_remaining == 3 / 60
            outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
    assert dice.call_count == len(rolls)
    assert game.state.ball_position == spot
    assert not game.has_untimed_down()
    assert len(game.play_log) == 1 and game.play_log[0] is outcome
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.state.home_stats.total_yards == game.state.away_stats.total_yards == 0
    expected_home = 6 if scorer == ("kicker" if home else "receiver") else 2 if scorer == "safety" and not home else 0
    expected_away = 6 if scorer == ("receiver" if home else "kicker") else 2 if scorer == "safety" and home else 0
    assert (game.state.home_score, game.state.away_score) == (expected_home, expected_away)
    assert not outcome.penalty_applied
    assert outcome.result.result_type.value == "blocked_kick"
    assert outcome.result.yards == -8
    assert outcome.result.raw_result == "BK - 8" and outcome.result.dice_roll == 11
    assert outcome.result.description == outcome.description
    assert outcome.clock_trace is not None
    assert outcome.clock_trace == game.last_clock_trace
    assert outcome.clock_trace.start_quarter == 2
    assert outcome.clock_trace.start_seconds == 3
    assert outcome.clock_trace.requested_seconds == 5
    assert outcome.clock_trace.charged_seconds == 3
    assert outcome.clock_trace.end_quarter == 3
    assert outcome.clock_trace.end_seconds == 900
    assert outcome.clock_trace.period_ended


@pytest.mark.parametrize("field", ["clock", "description"])
def test_plain_blocked_punt_reports_completed_clock_and_description(field: str) -> None:
    game = make_sample_game()
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 3 / 60
    game.state.possession_team.special_teams.punt = {11: "BK -8"}
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 31)
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(11, "Kick"), (20, "Recovery")]),
        patch("paydirt.game_engine.random.uniform", return_value=5),
    ):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert (game.state.quarter, game.state.time_remaining) == (3, 15)
    assert game.state.ball_position == 68
    if field == "clock":
        assert outcome.clock_trace is not None
        assert outcome.clock_trace.charged_seconds == 3
    else:
        assert outcome.result.description == outcome.description


@pytest.mark.parametrize("corruption", ["class", "clock"])
def test_gate_rejects_blocked_punt_receipt_corruption(
    monkeypatch: pytest.MonkeyPatch, corruption: str,
) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance
    from paydirt.game_engine import PaydirtGameEngine
    from paydirt.play_resolver import ResultType

    original = PaydirtGameEngine._handle_punt

    def corrupt(self: PaydirtGameEngine, *args: object, **kwargs: object) -> PlayOutcome:
        outcome = original(self, *args, **kwargs)
        if outcome.result.raw_result.upper().startswith("BK") and not outcome.pending_penalty_decision:
            if corruption == "class":
                outcome.result.result_type = ResultType.BREAKAWAY
            else:
                outcome.clock_trace = None
        return outcome

    monkeypatch.setattr(PaydirtGameEngine, "_handle_punt", corrupt)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("PUNT/BK" in error for error in report["errors"])

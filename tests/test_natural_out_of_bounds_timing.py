"""RULE-023: numeric defense changes must retain natural sideline timing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayType
from paydirt.priority_chart import apply_priority_chart
from tests.game_fixtures import make_sample_game


def run_sideline_play(
    *, home: bool = True, flow: str = "procedure", defense: str = "-1",
    quarter: int = 4, seconds: int = 286, options: dict | None = None,
) -> tuple:
    """Resolve real synthetic chart cells through the public game methods."""
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home
    state.quarter, state.time_remaining = quarter, seconds / 60
    state.two_minute_warning_called = seconds <= 120
    state.ball_position, state.down, state.yards_to_go = 35, 2, 10
    state.home_score, state.away_score = 14, 7
    state.possession_team.offense.end_run.update({10: "DEF 5", 29: "3*"})
    state.defense_team.defense.modifiers[("B", 1)] = {3: defense}
    rolls = [10, 29] if flow == "declined" else [29]
    with (
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[
            (roll, f"Synthetic {roll}") for roll in rolls
        ]),
        patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
        patch("paydirt.game_engine.random.uniform", return_value=29),
    ):
        run = game.run_play if flow == "direct" else game.run_play_with_penalty_procedure
        outcome = run(PlayType.END_RUN, DefenseType.SHORT_YARDAGE, **(options or {}))
        if flow == "declined":
            assert outcome.pending_penalty_decision
            assert state.time_remaining * 60 == pytest.approx(seconds)
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
    return game, outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined"])
@pytest.mark.parametrize("defense,yards,elapsed", [
    ("", 3, 10), ("0", 3, 10), ("2", 5, 10), ("-1", 2, 10),
    ("(1)", 1, 29), ("[1]", 1, 29),
])
def test_only_an_actual_defensive_overrule_cancels_sideline_timing(
    home: bool, flow: str, defense: str, yards: int, elapsed: int,
) -> None:
    game, outcome = run_sideline_play(home=home, flow=flow, defense=defense)
    if flow == "declined":
        elapsed = 5  # The flagged run uses action time with zero dead time.
    assert game.state.time_remaining * 60 == pytest.approx(286 - elapsed)
    assert outcome.yards_gained == yards
    assert game.state.ball_position == 35 + yards
    assert game.state.down == 3
    assert game.state.yards_to_go == 10 - yards
    assert game.state.is_home_possession is home
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0


@pytest.mark.parametrize("flow", ["direct", "procedure"])
@pytest.mark.parametrize("quarter,seconds,elapsed", [
    (1, 120, 29), (2, 150, 29), (2, 121, 1), (2, 120, 10),
    (4, 301, 29), (4, 300, 10), (4, 120, 10), (3, 120, 29),
])
def test_natural_sideline_timing_respects_half_windows_and_warning(
    flow: str, quarter: int, seconds: int, elapsed: int,
) -> None:
    game, _ = run_sideline_play(flow=flow, quarter=quarter, seconds=seconds)
    assert game.state.quarter == quarter
    assert game.state.time_remaining * 60 == pytest.approx(seconds - elapsed)


@pytest.mark.parametrize("options", [
    {"call_spike": True}, {"call_timeout": True},
    {"call_defensive_timeout": True},
    {"call_spike": True, "call_defensive_timeout": True},
])
def test_natural_sideline_stop_needs_no_spike_or_timeout(options: dict) -> None:
    game, outcome = run_sideline_play(options=options, seconds=85)
    assert game.state.time_remaining * 60 == pytest.approx(75)
    assert game.state.down == 3
    assert game.state.home_timeouts == game.state.away_timeouts == 3
    assert not outcome.spike_used
    assert not outcome.timeout_used
    assert not outcome.defensive_timeout_used


@pytest.mark.parametrize("offense,defense,expected", [
    ("3*", "-1", True), ("3†", "2", True),
    ("(3)*", "(1)", True), ("3*", "(1)", False),
    ("3*", "[1]", False), ("3*", "QT", False),
    ("3*", "INT 10", False), ("3*", "BLACK", False),
    ("3", "-1", False),
])
def test_priority_result_preserves_only_the_retained_sideline_marker(
    offense: str, defense: str, expected: bool,
) -> None:
    assert apply_priority_chart(offense, defense).out_of_bounds is expected

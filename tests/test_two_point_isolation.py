"""RULE-001/STAT-003: actual chart tries never become ordinary game plays."""

from copy import deepcopy
from dataclasses import fields
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import ScoringPlay
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


def pending_try(home: bool = True) -> PaydirtGameEngine:
    game = make_sample_game()
    game.season_rules.two_point_conversion = True
    state = game.state
    state.is_home_possession = home
    state.home_score, state.away_score = (6, 8) if home else (8, 6)
    state.ball_position, state.down, state.yards_to_go = 97, 3, 7
    state.quarter, state.time_remaining = 2, 20 / 60
    state.home_timeouts, state.away_timeouts = 1, 2
    state.scoring_plays.append(ScoringPlay(
        quarter=2, time_remaining=20 / 60, team="HOME" if home else "AWAY",
        is_home_team=home, play_type="TD", description="Touchdown", points=6,
    ))
    state.defense_team.defense.modifiers = {}
    game._last_play_start_quarter = 2
    return game


def ordinary_state(game: PaydirtGameEngine) -> dict:
    """Snapshot every state field except the permitted scoring/final flag changes."""
    return deepcopy({
        field.name: getattr(game.state, field.name)
        for field in fields(game.state)
        if field.name not in {"home_chart", "away_chart", "home_score", "away_score",
                              "scoring_plays", "game_over"}
    })


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("cell,good", [("3", True), ("TD", True), ("1", False),
                                      ("-3", False), ("BLACK", False), ("F INC", False)])
def test_real_chart_try_has_only_try_scoring_and_no_ordinary_accounting(home: bool, cell: str, good: bool) -> None:
    game = pending_try(home)
    state, stats = game.state, game.state.offense_stats
    state.possession_team.offense.short_pass = {26: cell}
    before = ordinary_state(game)
    with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
          patch("paydirt.game_engine.random.uniform", return_value=35)):
        success, defensive_points, _ = game.attempt_two_point(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert (success, defensive_points) == (good, 0)
    assert (state.home_score, state.away_score) == ((6 + 2 * good, 8) if home else (8, 6 + 2 * good))
    assert [score.play_type for score in state.scoring_plays] == (["TD", "2PT"] if good else ["TD"])
    assert ordinary_state(game) == before
    assert game.state is state and state.offense_stats is stats
    assert game.play_log == [] and game.offensive_call_history == []
    assert game._last_play_start_quarter == 2 and not game._conversion_in_progress
    assert game.last_clock_trace.charged_seconds == 0
    if good:
        score = state.scoring_plays[-1]
        assert (score.points, score.is_home_team, score.quarter, score.time_remaining) == (2, home, 2, 20 / 60)


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("return_cell,defensive_points", [("0", 0), ("TD", 2)])
def test_interception_restores_touchdown_team_and_credits_only_defensive_try(home: bool, return_cell: str, defensive_points: int) -> None:
    game = pending_try(home)
    game.state.possession_team.offense.short_pass = {26: "INT 0"}
    game.state.defense_team.special_teams.interception_return = {26: return_cell}
    before = ordinary_state(game)
    with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Return26"))):
        success, points, _ = game.attempt_two_point(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert (success, points) == (False, defensive_points)
    assert (game.state.home_score, game.state.away_score) == ((6, 8 + points) if home else (8 + points, 6))
    assert ordinary_state(game) == before
    assert game.play_log == [] and game.offensive_call_history == []
    assert [score.play_type for score in game.state.scoring_plays] == (["TD", "Def 2PT"] if points else ["TD"])
    if points:
        score = game.state.scoring_plays[-1]
        assert score.is_home_team is not home
        assert (score.points, score.quarter, score.time_remaining) == (2, 2, 20 / 60)


@pytest.mark.parametrize("quarter,minutes,overtime", [(2, 2.1, False), (2, 0, False),
                                                     (3, 15, False), (4, 0, False), (5, 0, True)])
def test_try_preserves_period_warning_timeout_and_overtime_state(quarter: int, minutes: float, overtime: bool) -> None:
    game = pending_try()
    state = game.state
    state.quarter, state.time_remaining, state.is_overtime = quarter, minutes, overtime
    state.game_over = quarter == 4
    state.ot_period = int(overtime)
    state.possession_team.offense.line_plunge = {26: "2"}
    before = ordinary_state(game)
    with patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")):
        assert game.attempt_two_point(PlayType.LINE_PLUNGE)[0]
    assert ordinary_state(game) == before
    assert (state.home_score, state.away_score) == (8, 8)
    assert not state.game_over
    assert game.last_clock_trace.charged_seconds == 0
    assert state.scoring_plays[-1].quarter == 2


def test_resolver_exception_leaves_live_state_and_histories_unchanged() -> None:
    game = pending_try()
    before = deepcopy(game.state)
    with (patch("paydirt.game_engine.resolve_play", side_effect=ValueError("invalid chart cell")),
          pytest.raises(ValueError, match="invalid chart cell")):
        game.attempt_two_point(PlayType.SHORT_PASS)
    assert game.state == before
    assert game.play_log == [] and game.offensive_call_history == []
    assert not game._conversion_in_progress


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("recovered,cell,good,defensive_points", [
    (True, "F+2", True, 0), (True, "F+0", False, 0),
    (False, "F+2", False, 0), (False, "F-100", False, 2),
])
def test_fumble_recovery_does_not_leak_try_accounting(home: bool, recovered: bool, cell: str, good: bool, defensive_points: int) -> None:
    game = pending_try(home)
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 20) if recovered else (10, 10)
    game.state.possession_team.offense.line_plunge = {26: cell}
    game.state.defense_team.special_teams.interception_return = {20: "0"}
    before = ordinary_state(game)
    with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Recovery20"))):
        success, points, _ = game.attempt_two_point(PlayType.LINE_PLUNGE)
    assert (success, points) == (good, defensive_points)
    assert ordinary_state(game) == before
    assert game.play_log == [] and game.offensive_call_history == []
    assert (game.state.home_score, game.state.away_score) == (
        (6 + 2 * good, 8 + points) if home else (8 + points, 6 + 2 * good)
    )


def test_exception_after_result_processing_cannot_change_live_game() -> None:
    game = pending_try()
    game.state.possession_team.offense.line_plunge = {26: "3"}
    before = deepcopy(game.state)
    with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
          patch("paydirt.game_engine.PaydirtGameEngine._use_time", side_effect=RuntimeError("late resolution failure")),
          pytest.raises(RuntimeError, match="late resolution failure")):
        game.attempt_two_point(PlayType.LINE_PLUNGE)
    assert game.state == before
    assert not game._conversion_in_progress
    assert game.play_log == [] and game.offensive_call_history == []


def test_ordinary_touchdown_control_still_scores_six_and_records_play() -> None:
    game = pending_try()
    game.state.ball_position = 98
    game.state.possession_team.offense.line_plunge = {26: "2"}
    with patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Play26")):
        outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert outcome.touchdown and game.state.home_score == 12
    assert len(game.play_log) == len(game.offensive_call_history) == 1

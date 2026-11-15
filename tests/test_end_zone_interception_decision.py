"""FLOW-023: decide own-end-zone interception returns after the catch.

The catch location, score and clock must be known before the choice, and no
return dice may be rolled until the decision is resolved. These tests use only
the public sample teams under ``seasons/2026`` with explicit synthetic cells.
"""
import json
import random
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.interception_policy import should_attempt_end_zone_return
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PlayResult,
    PlayType,
    ResultType,
)
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game

OWN_GOAL_LINE = 100
ONE_YARD_DEEP = 101
FOUR_YARDS_DEEP = 104
MAX_RECORDED_DEPTH = 109
PAST_END_LINE = 112


def interception_result(raw_spot: int) -> PlayResult:
    """Build a synthetic interception caught at ``raw_spot`` (offense perspective)."""
    return PlayResult(
        result_type=ResultType.INTERCEPTION,
        yards=raw_spot - 90,
        turnover=True,
        raw_result=f"INT {raw_spot - 90}",
        dice_roll=10,
    )


def throw_interception(game: PaydirtGameEngine, result: PlayResult):
    """Run a scrimmage pass that the patched resolver turns into an interception."""
    choice = PenaltyChoice(play_result=result)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        return game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD
        )


def decision_game(offense_home: bool = True, raw_spot: int = FOUR_YARDS_DEEP):
    """Sample game at the offense's own 10 with the intercepting team asking."""
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    game.state.ball_position = 90
    defense_home = not offense_home
    game.set_end_zone_interception_policy(defense_home, "ask")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    return game, interception_result(raw_spot)


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize(
    "raw_spot,depth",
    [
        (OWN_GOAL_LINE, 0),
        (ONE_YARD_DEEP, 1),
        (FOUR_YARDS_DEEP, 4),
        (MAX_RECORDED_DEPTH, 9),
        (PAST_END_LINE, 9),
    ],
)
def test_ask_defers_choice_until_catch_depth_is_known(
    offense_home: bool, raw_spot: int, depth: int
) -> None:
    game, result = decision_game(offense_home, raw_spot)
    before = (
        game.state.ball_position,
        game.state.is_home_possession,
        game.state.down,
        game.state.home_score,
        game.state.away_score,
    )
    with patch(
        "paydirt.game_engine.roll_chart_dice",
        side_effect=AssertionError("return dice rolled before the decision"),
    ) as dice:
        outcome = throw_interception(game, result)
    dice.assert_not_called()
    assert outcome.pending_end_zone_interception_return_decision is True
    assert outcome.int_catch_depth == depth
    assert outcome.turnover is False
    assert outcome.touchdown is False
    assert "end zone" in outcome.description.lower()
    # The catch depth is engine-provided, so the offense-derived LOS is untouched.
    assert before == (
        game.state.ball_position,
        game.state.is_home_possession,
        game.state.down,
        game.state.home_score,
        game.state.away_score,
    )
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0


@pytest.mark.parametrize("offense_home", [True, False])
def test_touchback_resolution_records_turnover_once_without_dice(offense_home: bool) -> None:
    game, result = decision_game(offense_home)
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        pending = throw_interception(game, result)
        dice.assert_not_called()
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=False
        )
    dice.assert_not_called()
    assert final.pending_end_zone_interception_return_decision is False
    assert final.turnover is True
    assert game.state.ball_position == 20
    assert game.state.is_home_possession is not offense_home
    assert game.state.away_stats.interceptions_thrown + game.state.home_stats.interceptions_thrown == 1
    with pytest.raises(ValueError):
        game.apply_end_zone_interception_return_decision(pending, attempt_return=False)


@pytest.mark.parametrize("offense_home", [True, False])
def test_return_resolution_rolls_once_and_matches_predeclared_policy(offense_home: bool) -> None:
    game, result = decision_game(offense_home)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice:
        pending = throw_interception(game, result)
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    dice.assert_called_once()
    assert final.turnover is True
    assert game.state.ball_position == 11
    assert result.int_spot == -4
    assert result.int_return_yards == 15
    assert final.description == result.description


def test_field_interception_is_unaffected_by_ask_policy() -> None:
    game, _ = decision_game(raw_spot=95)
    result = interception_result(95)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")) as dice:
        outcome = throw_interception(game, result)
    dice.assert_called_once()
    assert outcome.pending_end_zone_interception_return_decision is False


def test_explicit_touchback_policy_never_asks() -> None:
    game, result = decision_game()
    game.set_end_zone_interception_policy(False, "touchback")
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        outcome = throw_interception(game, result)
    dice.assert_not_called()
    assert outcome.pending_end_zone_interception_return_decision is False
    assert game.state.ball_position == 20


@pytest.mark.parametrize(
    "depth,differential,quarter,minutes,expected",
    [
        (0, 0, 4, 1.5, True),    # goal-line catch, tie game, late
        (0, 14, 4, 1.0, False),  # protect a two-score lead
        (1, -3, 4, 1.0, True),   # trailing, shallow catch
        (1, 14, 4, 1.0, False),  # leading, shallow catch still protects
        (3, -7, 3, 5.0, True),   # trailing by a score
        (3, 0, 1, 10.0, False),  # neutral early situation
        (6, -7, 4, 2.0, False),  # too deep to escape reliably
        (9, -7, 4, 0.5, False),
    ],
)
def test_cpu_policy_uses_depth_score_and_clock(
    depth: int, differential: int, quarter: int, minutes: float, expected: bool
) -> None:
    assert should_attempt_end_zone_return(
        catch_depth=depth,
        score_differential=differential,
        quarter=quarter,
        time_remaining=minutes,
    ) is expected


@pytest.mark.parametrize("depth,leading,should_roll", [
    (9, False, False),  # deep catch -> automatic touchback
    (0, False, True),   # goal-line catch trailing late -> return
    (1, True, False),   # shallow but protecting a lead -> touchback
])
def test_auto_policy_resolves_without_a_pending_decision(
    depth: int, leading: bool, should_roll: bool
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 90
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    if leading:  # away defense leads by 14
        game.state.away_score = 24
        game.state.home_score = 10
    else:  # home offense leads, away defense trails
        game.state.home_score = 24
        game.state.away_score = 10
    game.set_end_zone_interception_policy(False, "auto")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    result = interception_result(100 + depth)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")) as dice:
        outcome = throw_interception(game, result)
    assert outcome.pending_end_zone_interception_return_decision is False
    if should_roll:
        dice.assert_called_once()
        assert game.state.ball_position == 15
    else:
        dice.assert_not_called()
        assert game.state.ball_position == 20


def test_pending_decision_survives_save_and_load_with_random_state(tmp_path: Path) -> None:
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        pending = throw_interception(game, result)
    save_path = tmp_path / "pending-int.json"
    save_game(game, str(save_path))
    saved = json.loads(save_path.read_text())
    assert saved["pending_end_zone_interception"]["catch_depth"] == 4
    deferred_state = game._pending_end_zone_interception["random_state"]
    return_chart = dict(game.state.defense_team.special_teams.interception_return)

    # Resolving the live engine advances the global dice RNG after the save.
    live = game.apply_end_zone_interception_return_decision(
        pending, attempt_return=True
    )
    loaded = load_game(str(save_path))[0]
    assert loaded.has_pending_end_zone_interception is True
    assert random.getstate() == deferred_state
    loaded.state.defense_team.special_teams.interception_return = return_chart
    replay_pending = loaded._last_play_outcome
    replay = loaded.apply_end_zone_interception_return_decision(
        replay_pending, attempt_return=True
    )
    assert replay.result.int_return_dice == live.result.int_return_dice
    assert loaded.state.ball_position == game.state.ball_position
    assert loaded.state.is_home_possession == game.state.is_home_possession
    assert loaded.home_end_zone_interception_policy == game.home_end_zone_interception_policy
    assert loaded.away_end_zone_interception_policy == game.away_end_zone_interception_policy


def test_return_resolution_reports_yardage_and_spot_in_description() -> None:
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        pending = throw_interception(game, result)
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    assert "Return" in final.description
    assert "11" in final.description
    assert final.description.count("Return:") == 1


def test_return_touchdown_description_is_explicit() -> None:
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    game.state.defense_team.special_teams.interception_return = {26: "TD"}
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "TD")):
        pending = throw_interception(game, result)
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    assert final.touchdown is True
    assert "TOUCHDOWN" in final.description.upper()
    assert final.description.count("TOUCHDOWN") == 1


def test_pending_decision_preserves_requested_spike_until_resolution() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 90
    game.state.quarter = 4
    game.state.time_remaining = 0.5
    game.set_end_zone_interception_policy(False, "ask")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    result = interception_result(FOUR_YARDS_DEEP)
    choice = PenaltyChoice(play_result=result)
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15"))):
        pending = game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD, call_spike=True
        )
        assert pending.pending_end_zone_interception_return_decision is True
        assert pending.spike_used is False
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True
        )
    assert final.result.int_return_dice == 26
    assert game.state.ball_position == 11


def test_pending_choice_blocks_a_new_snap_until_it_is_resolved() -> None:
    """FLOW-026: a snap cannot run while the return choice is unresolved."""
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        pending = throw_interception(game, result)
    assert pending.pending_end_zone_interception_return_decision is True
    state_before = deepcopy(game.state)
    with pytest.raises(ValueError, match="end-zone interception"):
        game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    with pytest.raises(ValueError, match="end-zone interception"):
        game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state == state_before
    assert not game.play_log
    assert game.has_pending_end_zone_interception
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        final = game.apply_end_zone_interception_return_decision(pending, attempt_return=False)
    assert not game.has_pending_end_zone_interception
    assert final.turnover is True
    assert game.state.ball_position == 20
    # The guard only covers the unresolved choice.
    game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)


@pytest.mark.parametrize(
    "action",
    [
        lambda game, pending: game.kickoff(),
        lambda game, pending: game.onside_kick(),
        lambda game, pending: game.safety_free_kick(),
        lambda game, pending: game.attempt_extra_point(),
        lambda game, pending: game.apply_defensive_timeout(
            pending,
            time_before_play=1.0,
            quarter_before_play=4,
            offense_was_home=True,
            two_minute_warning_before=True,
        ),
        lambda game, pending: game.apply_penalty_decision(
            pending, accept_play=True
        ),
        lambda game, pending: game.apply_punt_penalty_decision(
            pending, accept_penalty=True
        ),
        lambda game, pending: game.apply_kickoff_penalty_decision(
            pending, accept_penalty=True
        ),
        lambda game, pending: game.apply_fg_penalty_decision(
            pending, accept_play=True
        ),
        lambda game, pending: game.start_overtime(
            coin_toss_winner_is_home=True
        ),
    ],
    ids=[
        "kickoff",
        "onside-kick",
        "safety-free-kick",
        "extra-point",
        "defensive-timeout",
        "scrimmage-penalty",
        "punt-penalty",
        "kickoff-penalty",
        "field-goal-penalty",
        "overtime-start",
    ],
)
def test_pending_choice_blocks_other_game_changing_entry_points(action) -> None:
    """FLOW-026: every public game-changing action honors the pending choice."""
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(7, "10")):
        pending = throw_interception(game, result)
    assert pending.pending_end_zone_interception_return_decision is True
    state_before = deepcopy(game.state)
    log_before = list(game.play_log)
    history_before = list(game.offensive_call_history)
    start_quarter_before = game._last_play_start_quarter
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(7, "10")):
        with pytest.raises(ValueError, match="end-zone interception"):
            action(game, pending)
    assert game.state == state_before
    assert game.play_log == log_before
    assert game.offensive_call_history == history_before
    assert game._last_play_start_quarter == start_quarter_before
    assert game.has_pending_end_zone_interception


def test_pending_choice_blocks_two_point_before_conversion_setup() -> None:
    """FLOW-026: a try cannot enter its isolated conversion setup."""
    game, result = decision_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(7, "10")):
        pending = throw_interception(game, result)
    assert pending.pending_end_zone_interception_return_decision is True
    state_before = deepcopy(game.state)
    with patch.object(
        game,
        "get_two_point_situation",
        side_effect=AssertionError("two-point conversion setup started"),
    ):
        with pytest.raises(ValueError, match="end-zone interception"):
            game.attempt_two_point(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state == state_before
    assert game.has_pending_end_zone_interception


@pytest.mark.parametrize("path", ["hail-mary", "run-play"])
def test_direct_interception_paths_defer_own_end_zone_ask(path: str) -> None:
    """FLOW-028: Hail Mary and direct run_play honor the same ask policy."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 90
    game.set_end_zone_interception_policy(False, "ask")
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    result = interception_result(104)
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=result),
        patch("paydirt.game_engine.resolve_play", return_value=result),
    ):
        if path == "hail-mary":
            outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        else:
            outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert outcome.pending_end_zone_interception_return_decision is True
    assert outcome.int_catch_depth == 4
    assert game.has_pending_end_zone_interception is True
    assert game.state.is_home_possession is True
    assert game.state.ball_position == 90
    assert game.state.home_score == game.state.away_score == 0
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        final = game.apply_end_zone_interception_return_decision(
            outcome, attempt_return=True
        )
    assert final.pending_end_zone_interception_return_decision is False

@pytest.mark.parametrize(
    "path,designation",
    [
        ("penalty-procedure", "none"),
        ("penalty-procedure", "out-of-bounds"),
        ("penalty-procedure", "in-bounds"),
        ("run-play", "none"),
        ("run-play", "out-of-bounds"),
        ("run-play", "in-bounds"),
    ],
)
def test_end_zone_deferral_uses_raw_catch_depth_and_applies_designation_once(
    path: str, designation: str,
) -> None:
    """RULE-031: catch depth is fixed before the choice, whatever the designation."""
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    if designation == "in-bounds":
        result.out_of_bounds = True
    designations = {
        "out-of-bounds": {"out_of_bounds_designation": True},
        "in-bounds": {"in_bounds_designation": True},
    }.get(designation, {})

    if path == "penalty-procedure":
        choice = PenaltyChoice(play_result=result)
        with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
            pending = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD, **designations,
            )
    else:
        with patch("paydirt.game_engine.resolve_play", return_value=result):
            pending = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD, **designations,
            )

    assert pending.pending_end_zone_interception_return_decision is True
    assert pending.int_catch_depth == 4
    assert pending.description == (
        "INTERCEPTION in the end zone at the own 4-yard line - "
        "choose touchback or attempt return"
    )
    assert result.description == ""
    assert result.yards == FOUR_YARDS_DEEP - 90
    assert result.out_of_bounds is (designation == "in-bounds")

    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True,
        )

    assert final.pending_end_zone_interception_return_decision is False
    assert final.turnover is True
    assert game.state.is_home_possession is False
    assert game.state.ball_position == 11
    assert "designation: -5 yards" not in final.result.description


def test_cli_prompt_shows_the_engine_catch_depth_used_by_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """RULE-031: the CLI prompt and final spot use the same engine depth."""
    from paydirt.interactive_game import handle_end_zone_interception_decision

    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    with patch(
        "paydirt.game_engine.resolve_play_with_penalties",
        return_value=PenaltyChoice(play_result=result),
    ):
        pending = game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD, out_of_bounds_designation=True,
        )
    monkeypatch.setattr("builtins.input", lambda prompt: "R")
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        final = handle_end_zone_interception_decision(game, pending, human_is_home=False)

    output = capsys.readouterr().out
    assert "Catch depth: 4 yard(s) deep in the end zone." in output
    assert final.pending_end_zone_interception_return_decision is False
    assert "designation" not in final.result.description


@pytest.mark.parametrize("clock_stopped", [False, True])
def test_hail_mary_defensive_timeout_is_deferred_with_pending_interception(
    clock_stopped: bool,
) -> None:
    """FLOW-031: a pending Hail Mary interception defers its timeout request."""
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    game.state.two_minute_warning_called = True
    result.out_of_bounds = clock_stopped
    game.state.home_timeouts = game.state.away_timeouts = 3
    state_before = deepcopy(game.state)

    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=result),
    ):
        pending = game.run_play_with_penalty_procedure(
            PlayType.HAIL_MARY, DefenseType.STANDARD, call_defensive_timeout=True,
        )

    assert pending.pending_end_zone_interception_return_decision is True
    assert pending.defensive_timeout_context is not None
    assert game.state == state_before
    assert game.play_log == []
    assert game.has_pending_end_zone_interception is True
    assert game._pending_end_zone_interception["follow_ups"][
        "defensive_timeout_context"
    ] is not None

    timeouts_before = (game.state.home_timeouts, game.state.away_timeouts)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")):
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True,
        )

    # A completed interception is a turnover, so the engine conserves the timeout.
    assert final.turnover is True
    assert final.timeout_used is False
    assert final.defensive_timeout_used is False
    assert (game.state.home_timeouts, game.state.away_timeouts) == timeouts_before
    assert game._pending_end_zone_interception is None


def test_pending_hail_mary_timeout_request_survives_save_and_load(
    tmp_path: Path,
) -> None:
    """FLOW-031: a restored pending interception keeps its timeout request."""
    game, result = decision_game(raw_spot=FOUR_YARDS_DEEP)
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    game.state.two_minute_warning_called = True
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=result),
    ):
        pending = game.run_play_with_penalty_procedure(
            PlayType.HAIL_MARY, DefenseType.STANDARD, call_defensive_timeout=True,
        )
    assert pending.pending_end_zone_interception_return_decision is True
    save_path = tmp_path / "pending-hail-mary-timeout.json"
    save_game(game, str(save_path))
    saved = json.loads(save_path.read_text())
    context = saved["pending_end_zone_interception"]["follow_ups"][
        "defensive_timeout_context"
    ]
    assert context["time_before_play"] == 1.0
    assert context["quarter_before_play"] == 4
    assert context["timeouts_before_play"] == [3, 3]

    loaded = load_game(str(save_path))[0]
    assert loaded.has_pending_end_zone_interception is True
    restored = loaded._pending_end_zone_interception["follow_ups"][
        "defensive_timeout_context"
    ]
    assert restored["time_before_play"] == 1.0
    assert restored["quarter_before_play"] == 4
    assert tuple(restored["timeouts_before_play"]) == (3, 3)
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")),
        patch("paydirt.game_engine.random.uniform", return_value=5.0),
    ):
        final = loaded.apply_end_zone_interception_return_decision(
            loaded._last_play_outcome, attempt_return=True,
        )
    assert final.turnover is True
    assert final.defensive_timeout_used is False
    assert loaded.state.time_remaining == pytest.approx(1.0 - 5 / 60, abs=0.001)

HAIL_MARY_SECONDS = (5.0, 15.0)
SCRIMMAGE_SECONDS = (25.0, 45.0)


def hail_mary_game(policy: str, offense_home: bool = True) -> PaydirtGameEngine:
    """First-half Hail Mary from the offense's own 10 with the defense's policy."""
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    game.state.ball_position = 90
    game.state.quarter = 2
    game.state.time_remaining = 5.0
    game.state.down = 2
    game.state.yards_to_go = 10
    game.set_end_zone_interception_policy(not offense_home, policy)
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    return game


def hail_mary_interception() -> PlayResult:
    """Synthetic Hail Mary interception 26 yards downfield, nine deep in the end zone."""
    return PlayResult(
        result_type=ResultType.INTERCEPTION,
        yards=26,
        turnover=True,
        description="Hail Mary INTERCEPTED! 26 yards downfield",
        raw_result="Hail Mary INT 20",
        dice_roll=20,
    )


def _capture_uniform(calls: list) -> object:
    def fake_uniform(low: float, high: float) -> float:
        calls.append((low, high))
        return (low + high) / 2
    return fake_uniform


def play_hail_mary(
    game: PaydirtGameEngine, resolution: bool | None = None,
) -> tuple[object, list]:
    """Run one Hail Mary, resolving a pending ask with ``resolution``."""
    calls: list = []
    return_rolls = [(26, "15")] if resolution else []
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(20, "Hail Mary INT"), *return_rolls]),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=hail_mary_interception()),
        patch("paydirt.game_engine.random.uniform", side_effect=_capture_uniform(calls)),
    ):
        outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        if outcome.pending_end_zone_interception_return_decision:
            outcome = game.apply_end_zone_interception_return_decision(
                outcome, attempt_return=bool(resolution),
            )
    return outcome, calls


def _stats(game: PaydirtGameEngine, home: bool) -> tuple:
    stats = game.state.home_stats if home else game.state.away_stats
    return (
        stats.interceptions_thrown,
        stats.fumbles_lost,
        stats.turnovers,
        stats.total_yards,
        stats.passing_yards,
        stats.first_downs,
    )


def _applied_state(game: PaydirtGameEngine, outcome) -> tuple:
    """Everything resolution must apply exactly once, per team.

    After a turnover ``offense_stats`` belongs to the receiving team, so both
    teams are read explicitly to avoid missing a wrong-side interception or
    turnover count.
    """
    return (
        game.state.time_remaining,
        game.state.home_score,
        game.state.away_score,
        game.state.ball_position,
        game.state.is_home_possession,
        game.state.down,
        game.state.yards_to_go,
        _stats(game, home=True),
        _stats(game, home=False),
        len(game.play_log),
        outcome.turnover,
        outcome.result.int_return_yards,
        outcome.description,
    )


@pytest.mark.parametrize("offense_home", [True, False])
def test_hail_mary_touchback_choice_keeps_immediate_hail_mary_timing(
    offense_home: bool,
) -> None:
    """FLOW-032: asking, then choosing touchback, must not charge scrimmage time."""
    immediate = hail_mary_game("touchback", offense_home)
    immediate_outcome, immediate_calls = play_hail_mary(immediate)

    deferred = hail_mary_game("ask", offense_home)
    deferred_outcome, deferred_calls = play_hail_mary(deferred, resolution=False)

    assert immediate_calls == [HAIL_MARY_SECONDS]
    assert deferred_calls == [HAIL_MARY_SECONDS]
    assert _applied_state(immediate, immediate_outcome) == _applied_state(
        deferred, deferred_outcome
    )
    assert deferred.state.time_remaining == pytest.approx(5.0 - 10 / 60)
    assert deferred_outcome.clock_trace.requested_seconds == pytest.approx(10.0)


@pytest.mark.parametrize("offense_home", [True, False])
def test_hail_mary_return_choice_keeps_immediate_hail_mary_timing(
    offense_home: bool,
) -> None:
    """FLOW-032: an attempted Hail Mary return also keeps 5-15 second timing."""
    immediate = hail_mary_game("return", offense_home)
    immediate_outcome, immediate_calls = play_hail_mary(immediate, resolution=True)

    deferred = hail_mary_game("ask", offense_home)
    deferred_outcome, deferred_calls = play_hail_mary(deferred, resolution=True)

    assert immediate_calls == [HAIL_MARY_SECONDS]
    assert deferred_calls == [HAIL_MARY_SECONDS]
    assert _applied_state(immediate, immediate_outcome) == _applied_state(
        deferred, deferred_outcome
    )
    assert deferred.state.ball_position == immediate.state.ball_position
    assert deferred.state.time_remaining == pytest.approx(5.0 - 10 / 60)


def test_direct_scrimmage_deferral_keeps_scrimmage_timing() -> None:
    """FLOW-032 control: ordinary own-end-zone deferrals still use 25-45 seconds."""
    game, result = decision_game()
    calls: list = []
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")),
        patch("paydirt.game_engine.random.uniform", side_effect=_capture_uniform(calls)),
    ):
        pending = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        assert pending.pending_end_zone_interception_return_decision is True
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=True,
        )
    assert calls == [SCRIMMAGE_SECONDS]
    assert final.turnover is True


def test_pending_hail_mary_timing_context_survives_save_and_load(
    tmp_path: Path,
) -> None:
    """FLOW-032: a resumed Hail Mary keeps Hail Mary timing, not scrimmage timing."""
    game = hail_mary_game("ask")
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=hail_mary_interception()),
    ):
        pending = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
    assert pending.pending_end_zone_interception_return_decision is True

    save_path = tmp_path / "pending-hail-mary-timing.json"
    save_game(game, str(save_path))
    saved = json.loads(save_path.read_text())
    assert saved["pending_end_zone_interception"]["play_seconds_range"] == [5.0, 15.0]

    loaded = load_game(str(save_path))[0]
    assert loaded.has_pending_end_zone_interception is True
    calls: list = []
    with patch("paydirt.game_engine.random.uniform", side_effect=_capture_uniform(calls)):
        final = loaded.apply_end_zone_interception_return_decision(
            loaded._last_play_outcome, attempt_return=False,
        )
    assert calls == [HAIL_MARY_SECONDS]
    assert final.turnover is True
    assert loaded.state.ball_position == 20
    assert loaded.state.time_remaining == pytest.approx(5.0 - 10 / 60)

    # Legacy saves lack the field; they derive Hail Mary timing from play_type
    # rather than replaying the old scrimmage-range defect.
    legacy = deepcopy(saved)
    del legacy["pending_end_zone_interception"]["play_seconds_range"]
    legacy_path = tmp_path / "legacy-pending-hail-mary-timing.json"
    legacy_path.write_text(json.dumps(legacy))
    legacy_game = load_game(str(legacy_path))[0]
    assert legacy_game._pending_end_zone_interception["play_seconds_range"] == HAIL_MARY_SECONDS
    legacy_calls: list = []
    with patch(
        "paydirt.game_engine.random.uniform", side_effect=_capture_uniform(legacy_calls)
    ):
        legacy_game.apply_end_zone_interception_return_decision(
            legacy_game._last_play_outcome, attempt_return=False,
        )
    assert legacy_calls == [HAIL_MARY_SECONDS]


def test_deferred_hail_mary_applies_clock_possession_and_stats_once() -> None:
    """FLOW-032: deferred Hail Mary resolution is a single applied play."""
    game = hail_mary_game("ask")
    calls: list = []
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=hail_mary_interception()),
        patch("paydirt.game_engine.random.uniform", side_effect=_capture_uniform(calls)),
    ):
        pending = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
        assert calls == []
        final = game.apply_end_zone_interception_return_decision(
            pending, attempt_return=False,
        )
    assert calls == [HAIL_MARY_SECONDS]
    assert len(game.play_log) == 1
    assert final.turnover is True
    assert game.state.is_home_possession is False
    assert game.state.ball_position == 20
    assert game.state.home_stats.interceptions_thrown == 1
    assert game.state.home_stats.turnovers == 1
    assert game.state.away_stats.turnovers == 0
    assert game.state.time_remaining == pytest.approx(5.0 - 10 / 60)
    with pytest.raises(ValueError, match="end-zone interception"):
        game.apply_end_zone_interception_return_decision(
            pending, attempt_return=False,
        )
    assert len(game.play_log) == 1



@pytest.mark.parametrize(
    "value",
    [["hi", 15.0], [15.0], [40.0, 5.0], {"low": 5.0, "high": 15.0}, "5-15"],
)
def test_restored_play_seconds_range_rejects_malformed_saves(
    tmp_path: Path, value: object,
) -> None:
    """FLOW-032: a malformed saved clock range is rejected, not silently reused."""
    game = hail_mary_game("ask")
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=hail_mary_interception()),
    ):
        game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
    save_path = tmp_path / "bad-range.json"
    save_game(game, str(save_path))
    saved = json.loads(save_path.read_text())
    saved["pending_end_zone_interception"]["play_seconds_range"] = value
    save_path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="play_seconds_range"):
        load_game(str(save_path))

def _pending_hail_mary_save(tmp_path: Path, name: str = "range.json") -> Path:
    """Save an unresolved Hail Mary ask so the pending payload can be edited."""
    game = hail_mary_game("ask")
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Hail Mary INT")),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=hail_mary_interception()),
    ):
        game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
    save_path = tmp_path / name
    save_game(game, str(save_path))
    return save_path


@pytest.mark.parametrize(
    "bounds_json,reason",
    [
        ("[1e309, 1e309]", "finite"),   # Infinity
        ("[5, 1e309]", "finite"),       # Infinite upper bound
        ("[-1e309, 15]", "finite"),     # Negative infinity
        ("[NaN, 15]", "finite"),        # Not a number
        ("[1e999999999999999999999, 15]", "finite"),  # Unconvertible float
        (f"[1{'0' * 400}, 15]", "finite"),  # Integer too large to convert
    ],
)
def test_non_finite_saved_clock_ranges_are_rejected(
    tmp_path: Path, bounds_json: str, reason: str,
) -> None:
    """FLOW-032 review: a non-finite range must never reach the game clock."""
    save_path = _pending_hail_mary_save(tmp_path)
    text = save_path.read_text()
    marker = '"play_seconds_range": [\n      5.0,\n      15.0\n    ]'
    assert marker in text, "saved range layout changed; update this fixture"
    save_path.write_text(text.replace(marker, f'"play_seconds_range": {bounds_json}'))
    with pytest.raises(ValueError, match=f"play_seconds_range.*{reason}"):
        load_game(str(save_path))


def test_legacy_save_derives_hail_mary_timing_from_play_type(tmp_path: Path) -> None:
    """FLOW-032: a legacy Hail Mary save gets Hail Mary timing, not scrimmage."""
    save_path = _pending_hail_mary_save(tmp_path, "legacy-hail-mary.json")
    saved = json.loads(save_path.read_text())
    del saved["pending_end_zone_interception"]["play_seconds_range"]
    assert saved["pending_end_zone_interception"]["play_type"] == "hail_mary"
    save_path.write_text(json.dumps(saved))

    loaded = load_game(str(save_path))[0]
    assert loaded._pending_end_zone_interception["play_seconds_range"] == HAIL_MARY_SECONDS
    calls: list = []
    with patch("paydirt.game_engine.random.uniform", side_effect=_capture_uniform(calls)):
        loaded.apply_end_zone_interception_return_decision(
            loaded._last_play_outcome, attempt_return=False,
        )
    assert calls == [HAIL_MARY_SECONDS]
    assert loaded.state.time_remaining == pytest.approx(5.0 - 10 / 60)


def test_legacy_save_keeps_scrimmage_timing_for_direct_play(tmp_path: Path) -> None:
    """FLOW-032: legacy scrimmage saves still resolve with scrimmage timing."""
    game, result = decision_game()
    with patch("paydirt.game_engine.resolve_play", return_value=result):
        game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    save_path = tmp_path / "legacy-direct.json"
    save_game(game, str(save_path))
    saved = json.loads(save_path.read_text())
    del saved["pending_end_zone_interception"]["play_seconds_range"]
    save_path.write_text(json.dumps(saved))

    loaded = load_game(str(save_path))[0]
    assert loaded._pending_end_zone_interception["play_seconds_range"] == SCRIMMAGE_SECONDS
    calls: list = []
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "15")),
        patch("paydirt.game_engine.random.uniform", side_effect=_capture_uniform(calls)),
    ):
        loaded.apply_end_zone_interception_return_decision(
            loaded._last_play_outcome, attempt_return=True,
        )
    assert calls == [SCRIMMAGE_SECONDS]

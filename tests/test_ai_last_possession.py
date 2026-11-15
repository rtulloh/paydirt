"""AI-029: last-possession fourth downs respect time and scoring distance."""

import random
from collections import Counter

import pytest

from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType, is_passing_play,
)
from tests.game_fixtures import make_sample_game


PASS_CONVERSIONS = {
    PlayType.SCREEN,
    PlayType.SHORT_PASS,
    PlayType.MEDIUM_PASS,
    PlayType.LONG_PASS,
    PlayType.TE_SHORT_LONG,
}


@pytest.fixture(params=[(mode, home) for mode in ("easy", "medium", "hard") for home in (False, True)],
                ids=[f"{mode}-{'home' if home else 'away'}"
                     for mode in ("easy", "medium", "hard") for home in (False, True)])
def last_possession(request: pytest.FixtureRequest):
    """Build the public-2026 scenario from the CPU's own perspective."""
    mode, home = request.param
    game = make_sample_game()
    game.season_rules.two_point_conversion = False
    ai = create_computer_ai(mode, game, cpu_is_home=home)
    state = game.state
    state.is_home_possession = home
    state.quarter = 4
    state.is_overtime = False
    state.home_score = 14 + (0 if home else 9)
    state.away_score = 14 + (9 if home else 0)
    state.time_remaining = 18 / 60
    state.down = 4
    state.yards_to_go = 2
    state.ball_position = 28
    state.home_timeouts = 0 if home else 3
    state.away_timeouts = 3 if home else 0
    state.two_minute_warning_called = True
    return game, ai


def _decisions(last_possession, count: int = 100):
    game, ai = last_possession
    choices = []
    for seed in range(count):
        random.seed(seed)
        choices.append(ai.select_offense_with_clock_management(game))
    return choices


def test_short_time_needs_clock_stopping_conversion(last_possession):
    """The 18-second reproduction cannot choose an ordinary in-bounds run."""
    decisions = _decisions(last_possession)
    plays = [decision[0] for decision in decisions]

    assert set(plays) <= PASS_CONVERSIONS
    assert all(decision[1] for decision in decisions)  # OOB stops a completion.
    assert all(decision[2] for decision in decisions)  # No-huddle also cuts snap time.
    assert last_possession[1].last_mode == "Last-Possession 4th Down"


def test_preserves_pass_variety_in_short_time(last_possession):
    """Clock urgency narrows run/pass choice without prescribing one deep shot."""
    decisions = _decisions(last_possession)
    plays = Counter(decision[0] for decision in decisions)
    assert len(plays) >= 3


def test_available_timeout_does_not_make_the_pass_clock_safe():
    """Auto-game never spends an offensive timeout, so the pass still needs OOB."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 4, 28
    state.home_timeouts = 1
    state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert all(decision[0] in PASS_CONVERSIONS for decision in decisions)
    assert all(decision[2] for decision in decisions)
    assert all(decision[1] is True for decision in decisions)
    assert ai.last_mode == "Last-Possession 4th Down"


def test_goal_line_down_nine_with_a_timeout_still_passes():
    """A run cannot stop the clock in auto-game, even with a timeout banked."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 1, 97
    state.home_timeouts = 1
    state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert all(is_passing_play(decision[0]) for decision in decisions)
    assert all(decision[1] for decision in decisions)


@pytest.mark.parametrize("two_point,run_allowed", [(False, False), (True, True)])
def test_goal_line_uses_season_two_point_rules(two_point, run_allowed):
    """An eight-point deficit is one possession only where a two-point try exists."""
    game = make_sample_game()
    game.season_rules.two_point_conversion = two_point
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 22
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 1, 97
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert any(not is_passing_play(decision[0]) for decision in decisions) is run_allowed
    assert all(
        decision[1] for decision in decisions if is_passing_play(decision[0])
    )


def test_makeable_tying_or_winning_field_goal_still_wins():
    """The new conversion policy must not displace an available tie/win kick."""
    game = make_sample_game()
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 17
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 72
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    play, oob, no_huddle, _, _, _ = ai.select_offense_with_clock_management(game)
    assert play == PlayType.FIELD_GOAL
    assert oob is False
    assert no_huddle is True


def test_short_time_near_goal_line_keeps_short_conversions():
    """A compact field removes deep routes but not legal short-yardage calls."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 1, 97
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert {decision[0] for decision in decisions} <= PASS_CONVERSIONS
    assert all(decision[0] != PlayType.LONG_PASS for decision in decisions)


def test_goal_line_touchdown_attempt_can_use_a_short_run():
    """When a touchdown ties or wins, a short run remains credible at the goal line."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 17
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 1, 97
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert any(not is_passing_play(decision[0]) for decision in decisions)


def test_second_reproduced_case_uses_a_clock_stopping_conversion():
    """13.42 seconds, fourth-and-four at the own 40, trailing 14."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 0, 14
    state.time_remaining = 13.42 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 4, 40
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert {decision[0] for decision in decisions} <= PASS_CONVERSIONS
    assert all(decision[1] for decision in decisions)
    assert all(decision[2] for decision in decisions)
    assert ai.last_mode == "Last-Possession 4th Down"


def test_long_yardage_prefers_deeper_clock_stopping_concepts():
    """A short pass plus the five-yard OOB cost is not a plausible 4th-and-15 call."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 15, 28
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert {decision[0] for decision in decisions} <= {
        PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.TE_SHORT_LONG,
    }
    assert any(decision[0] == PlayType.LONG_PASS for decision in decisions)


def test_enough_time_retains_ordinary_conversion_variety():
    """Three minutes is not a last-possession emergency."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 3.0
    state.down, state.yards_to_go, state.ball_position = 4, 2, 28
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    plays = {decision[0] for decision in decisions}
    assert any(not is_passing_play(play) for play in plays)
    assert any(is_passing_play(play) for play in plays)
    assert ai.last_mode != "Last-Possession 4th Down"


@pytest.mark.parametrize("seconds,expected_mode", [(30, True), (31, False)])
def test_clock_critical_window_boundary(seconds, expected_mode):
    """The last-possession plan starts only when one no-huddle snap is at risk."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = seconds / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 28
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    _decisions((game, ai), count=1)
    assert (ai.last_mode == "Last-Possession 4th Down") is expected_mode


@pytest.mark.parametrize("lead,expected_mode", [
    (1, "4th Down"), (0, "4th Down"),
])
def test_last_possession_plan_does_not_displace_existing_priorities(
    lead, expected_mode,
):
    """Leading and tied games retain the ordinary fourth-down branch."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14 + lead, 14
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 28
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    _decisions((game, ai), count=1)
    assert ai.last_mode == expected_mode


def test_last_second_field_goal_and_hail_mary_keep_priority():
    """Special scoring branches still precede the conversion planner."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 17
    state.time_remaining = 5 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 72
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    _decisions((game, ai), count=1)
    assert ai.last_mode == "End-of-Half FG"

    state.home_score, state.away_score = 14, 23
    state.ball_position = 50
    _decisions((game, ai), count=1)
    assert ai.last_mode == "Two-Minute Drill"


def test_last_second_hail_mary_priority_is_unchanged():
    """The last-play end-zone attempt still precedes conversion planning."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 21
    state.time_remaining = 6 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 50
    state.two_minute_warning_called = True

    play, oob, no_huddle, _, _, _ = ai.select_offense_with_clock_management(game)
    assert play == PlayType.HAIL_MARY
    assert oob is False
    assert no_huddle is True


@pytest.mark.parametrize("seconds,down,ytg,position,deficit", [
    (18, 4, 2, 28, 9),
    (13.42, 4, 4, 40, 14),
])
def test_real_engine_keeps_a_snap_after_the_conversion_attempt(
    seconds, down, ytg, position, deficit, monkeypatch,
):
    """Both reproduced cases must leave clock for a later snap."""
    game = make_sample_game()
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 14 + deficit
    state.time_remaining = seconds / 60
    state.down, state.yards_to_go, state.ball_position = down, ytg, position
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    random.seed(17)
    play, oob, no_huddle, _, _, _ = ai.select_offense_with_clock_management(game)
    result = PlayResult(ResultType.INCOMPLETE, description="Synthetic incomplete pass")
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(result),
    )
    outcome = game.run_play_with_penalty_procedure(
        play, DefenseType.STANDARD, out_of_bounds_designation=oob, no_huddle=no_huddle,
    )
    assert state.quarter == 4
    assert state.time_remaining > 0
    assert outcome.result.result_type == ResultType.INCOMPLETE
    assert outcome.clock_trace.requested_seconds == 5.0


def test_real_engine_completion_uses_sideline_timing(monkeypatch):
    """A completed designated pass pays the OOB cost but preserves a snap."""
    game = make_sample_game()
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 28
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    random.seed(0)
    play, oob, no_huddle, _, _, _ = ai.select_offense_with_clock_management(game)
    assert oob is True
    result = PlayResult(ResultType.YARDS, yards=7, description="Synthetic completion")
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(result),
    )
    outcome = game.run_play_with_penalty_procedure(
        play, DefenseType.STANDARD, out_of_bounds_designation=oob, no_huddle=no_huddle,
    )
    assert outcome.yards_gained == 2
    assert state.time_remaining == pytest.approx(8 / 60)


def test_last_possession_mode_is_visible_to_audits():
    """The audit should distinguish this policy from an ordinary fourth down."""
    game = make_sample_game()
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.quarter = 4
    state.home_score, state.away_score = 14, 23
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, 2, 28
    state.home_timeouts = state.away_timeouts = 0
    state.two_minute_warning_called = True

    ai.select_offense_with_clock_management(game)
    assert ai.last_mode == "Last-Possession 4th Down"


@pytest.mark.parametrize("deficit,position,ytg", [(7, 40, 4), (7, 72, 2), (4, 97, 1)])
def test_overtime_trailing_fourth_down_uses_the_same_clock_rule(
    deficit, position, ytg,
):
    """A normalized overtime quarter must reach the clock-critical plan."""
    game = make_sample_game()
    game.season_rules.two_point_conversion = False
    game.season_rules.overtime.format = "modified_sudden_death"
    ai = create_computer_ai("hard", game, cpu_is_home=True)
    state = game.state
    state.is_home_possession = True
    state.is_overtime = True
    state.ot_period = 1
    state.quarter = 5
    state.home_score, state.away_score = 17, 17 + deficit
    state.time_remaining = 18 / 60
    state.down, state.yards_to_go, state.ball_position = 4, ytg, position
    state.home_timeouts = state.away_timeouts = 3
    state.two_minute_warning_called = True

    decisions = _decisions((game, ai))
    assert all(decision[2] for decision in decisions)
    assert all(
        decision[1] for decision in decisions if is_passing_play(decision[0])
    )
    runs = [decision[0] for decision in decisions if not is_passing_play(decision[0])]
    if position >= 95:
        assert runs  # A four-point deficit makes a winning touchdown one score.
    else:
        assert not runs
    assert ai.last_mode == "Last-Possession 4th Down"

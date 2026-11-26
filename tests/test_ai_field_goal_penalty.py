"""AI-017: the defense should erase a made field goal with an offensive foul.

A made kick with an offensive foul offers the defense the foul instead of the
three points: enforce it and the offense re-kicks from farther back. The old
made-field-goal branch kept the score unconditionally. These tests build real
pending outcomes from a synthetic field-goal chart on the public 2026 sample
teams, then decide and apply through the engine.
"""

from __future__ import annotations

import random
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import (
    DefenseType,
    FieldGoalResult,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


def incomplete() -> PlayResult:
    return PlayResult(ResultType.INCOMPLETE, yards=0, description="Incomplete pass")


@pytest.fixture(params=[False, True], ids=["away-offense", "home-offense"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 75  # opponent's 25: chart 45 is good
    engine.state.down = 4
    engine.state.yards_to_go = 5
    engine.state.quarter = 1
    engine.state.time_remaining = 10
    return engine


def foul(yards: int, kind: str = "OFF") -> PenaltyOption:
    return PenaltyOption(kind, f"{kind} {yards}", yards, "synthetic foul")


def pending_kick(
    game: PaydirtGameEngine, options: list[PenaltyOption], *, offended: str,
    chart_yards: int = 45,
) -> object:
    """Return the engine's pending decision for one synthetic field-goal chart cell."""
    result = FieldGoalResult(
        dice_roll=15,
        dice_desc="B1+W0+W5=15",
        raw_result=str(chart_yards),
        chart_yards=chart_yards,
        is_penalty=True,
        penalty_options=options,
        offsetting=False,
        offended_team=offended,
        reroll_log=[],
    )
    state_before = deepcopy(game.state)
    rng_before = random.getstate()
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=result):
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision
    assert outcome.penalty_choice is not None
    # Deciding is a coach's choice: no state, log or dice change happens first.
    assert game.state == state_before
    assert not game.play_log
    assert random.getstate() == rng_before
    return outcome


def decide(game: PaydirtGameEngine, outcome: object) -> tuple[bool, int]:
    accept_play, index = ComputerAI().should_accept_penalty(
        outcome, True, not game.state.is_home_possession, game=game,
    )
    return accept_play, index or 0


def score(game: PaydirtGameEngine) -> tuple[int, int]:
    return game.state.home_score, game.state.away_score


def test_defense_enforces_an_offensive_foul_on_a_made_field_goal(
    game: PaydirtGameEngine,
) -> None:
    """Erasing three points and forcing a longer re-kick beats the made kick."""
    outcome = pending_kick(game, [foul(10)], offended="defense")
    assert outcome.field_goal_made is True

    before = score(game)
    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    final = game.apply_fg_penalty_decision(outcome, accept_play, index)
    assert final.penalty_applied
    assert final.field_goal_made is False
    assert score(game) == before
    assert game.state.down == 4
    assert game.state.yards_to_go == 15
    assert game.state.ball_position == 65
    assert game.state.offense_stats.penalties == 1
    assert game.state.offense_stats.penalty_yards == 10
    assert game.state.defense_stats.penalties == 0


def test_offense_keeps_a_made_field_goal_when_the_defense_fouled(
    game: PaydirtGameEngine,
) -> None:
    """The kicking team never trades three points for a first down."""
    outcome = pending_kick(
        game, [foul(5, kind="DEF"), foul(15, kind="DEF")], offended="offense",
    )
    assert outcome.field_goal_made is True

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (True, 0)

    game.apply_fg_penalty_decision(outcome, accept_play, index)
    assert 3 in score(game)
    assert game.state.offense_stats.penalties == 0


def test_defense_keeps_a_missed_field_goal_and_its_offensive_foul_option(
    game: PaydirtGameEngine,
) -> None:
    """Control: a miss is already the defense's best result."""
    outcome = pending_kick(game, [foul(10)], offended="defense", chart_yards=15)
    assert outcome.field_goal_made is False

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (True, 0)


def test_offense_takes_a_defensive_foul_on_a_missed_field_goal(
    game: PaydirtGameEngine,
) -> None:
    """Control: the offense still prefers a fresh set of downs to a miss."""
    outcome = pending_kick(game, [foul(15, kind="DEF")], offended="offense", chart_yards=15)
    assert outcome.field_goal_made is False

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    game.apply_fg_penalty_decision(outcome, accept_play, index)
    assert game.state.down == 1
    # 15 yards from the opponent's 25 is half the distance: 12 yards to 87.
    assert game.state.ball_position == 87
    assert game.state.yards_to_go == 10


def test_multiple_fouls_enforce_the_longest_at_its_original_index(
    game: PaydirtGameEngine,
) -> None:
    """The defense takes the longest offensive foul, reporting its real index."""
    options = [foul(5, kind="DEF"), foul(10), foul(15)]
    outcome = pending_kick(game, options, offended="defense")

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 2)

    game.apply_fg_penalty_decision(outcome, accept_play, index)
    # Fifteen yards back from the opponent's 25 is the 40.
    assert game.state.ball_position == 60
    assert game.state.offense_stats.penalty_yards == 15

def situational_game(
    *, seconds: float, quarter: int, kicking_score: int, defending_score: int,
    ball_position: int = 97, down: int = 4, yards_to_go: int = 3,
    kicking_is_home: bool = True,
) -> PaydirtGameEngine:
    """Build a scored, clocked game about to attempt a field goal."""
    engine = make_sample_game()
    engine.state.is_home_possession = kicking_is_home
    engine.state.ball_position = ball_position
    engine.state.down = down
    engine.state.yards_to_go = yards_to_go
    engine.state.quarter = quarter
    engine.state.time_remaining = seconds / 60
    if kicking_is_home:
        engine.state.home_score, engine.state.away_score = kicking_score, defending_score
    else:
        engine.state.home_score, engine.state.away_score = defending_score, kicking_score
    return engine


def test_defense_enforces_a_terminal_made_kick_foul_to_run_out_the_clock(
    game: PaydirtGameEngine,
) -> None:
    """RULE-005: enforcement expires the clock, so the defense wins 6-0, not 6-3.

    This test previously expected the defense to keep the made kick. That
    expectation depended on an accepted *offensive* foul incorrectly setting
    ``untimed_down_pending``: with a phantom extra down, enforcing traded a won
    game for a live snap. An offensive foul no longer extends the period, so the
    replay interval expires the clock and denying the three points is strictly
    better for the defense.
    """
    kicking_is_home = game.state.is_home_possession
    game = situational_game(
        seconds=3, quarter=4, kicking_score=0, defending_score=6,
        kicking_is_home=kicking_is_home,
    )
    outcome = pending_kick(game, [foul(5)], offended="defense")
    assert outcome.field_goal_made is True

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    final = game.apply_fg_penalty_decision(outcome, accept_play, index)
    assert final.penalty_applied
    assert game.state.game_over is True
    assert game.has_untimed_down() is False
    # The erased kick never scores: the defense wins 6-0 in either orientation.
    kicked, defender = ((0, 6) if kicking_is_home else (6, 0))
    assert score(game) == (kicked, defender)


def test_terminal_guard_does_not_apply_when_time_remains(game: PaydirtGameEngine) -> None:
    """With two minutes left the same lede still denies the three points."""
    kicking_is_home = game.state.is_home_possession
    game = situational_game(
        seconds=120, quarter=4, kicking_score=0, defending_score=6,
        kicking_is_home=kicking_is_home,
    )
    outcome = pending_kick(game, [foul(5)], offended="defense")

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    game.apply_fg_penalty_decision(outcome, accept_play, index)
    assert game.state.untimed_down_pending is False
    assert game.state.game_over is False


def test_defense_enforces_when_the_made_kick_does_not_win(game: PaydirtGameEngine) -> None:
    """A made kick that loses anyway never blocks enforcement."""
    kicking_is_home = game.state.is_home_possession
    game = situational_game(
        seconds=3, quarter=4, kicking_score=0, defending_score=2,
        kicking_is_home=kicking_is_home,
    )
    outcome = pending_kick(game, [foul(5)], offended="defense")

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)


def test_engine_projects_a_field_goal_choice_without_side_effects(
    game: PaydirtGameEngine,
) -> None:
    """The AI reads an engine projection, not a hand-built model of the rules."""
    outcome = pending_kick(game, [foul(10)], offended="defense")
    state_before = deepcopy(game.state)
    log_before = list(game.play_log)
    rng_before = random.getstate()

    retained = game.project_field_goal_penalty_choice(outcome, True)
    enforced = game.project_field_goal_penalty_choice(outcome, False, 0)

    assert game.state == state_before
    assert game.play_log == log_before
    assert random.getstate() == rng_before
    kicking = game.state.is_home_possession
    assert retained is not None and enforced is not None
    assert retained.field_goal_made is True
    assert (retained.points_for(kicking), retained.points_against(kicking)) == (3, 0)
    assert enforced.field_goal_made is False
    assert (enforced.points_for(kicking), enforced.points_against(kicking)) == (0, 0)
    assert (enforced.ball_position, enforced.down, enforced.yards_to_go) == (65, 4, 15)
    assert enforced.time_remaining < retained.time_remaining


def test_projection_is_none_for_a_non_field_goal_outcome(game: PaydirtGameEngine) -> None:
    choice = PenaltyChoice(incomplete(), penalty_options=[foul(5)], offended_team="defense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS, DefenseType.STANDARD,
        )
    assert game.project_field_goal_penalty_choice(outcome, True) is None


@pytest.mark.parametrize("raw,chart", [("BK -8", 0), ("F - 5", 0)], ids=["blocked", "snap-fumble"])
def test_projection_of_a_live_kick_error_consumes_no_dice_or_statistics(
    game: PaydirtGameEngine, raw: str, chart: int,
) -> None:
    """Replaying blocked or fumbled kicks must not steal recovery dice."""
    result = FieldGoalResult(
        dice_roll=15, dice_desc="B1+W0+W5=15", raw_result=raw, chart_yards=chart,
        is_penalty=True, penalty_options=[foul(5)], offsetting=False,
        offended_team="defense", reroll_log=[],
    )
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=result):
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision

    state_before = deepcopy(game.state)
    rng_before = random.getstate()
    assert game.project_field_goal_penalty_choice(outcome, True) is not None
    assert game.project_field_goal_penalty_choice(outcome, False, 0) is not None

    assert game.state == state_before
    assert not game.play_log
    assert random.getstate() == rng_before

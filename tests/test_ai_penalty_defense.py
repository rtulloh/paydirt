"""AI-002: the defense compares enforced fouls with the retained play.

An offensive foul replays the down from the previous spot. The old defensive
policy only looked at whether the retained play gained positive yardage, so it
kept an incomplete first-down pass instead of enforcing a fifteen-yard foul
(first-and-25 instead of second-and-10). These tests use synthetic, dice-free
pending choices against the public 2026 sample teams.
"""

from __future__ import annotations

import random
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PenaltySituation, PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[False, True], ids=["away-offense", "home-offense"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 50
    engine.state.down = 1
    engine.state.yards_to_go = 10
    engine.state.quarter = 1
    engine.state.time_remaining = 10
    return engine


def foul(yards: int, kind: str = "OFF") -> PenaltyOption:
    return PenaltyOption(kind, f"{kind} {yards}", yards, "synthetic foul")


def incomplete(description: str = "Incomplete pass") -> PlayResult:
    return PlayResult(ResultType.INCOMPLETE, yards=0, description=description)


def pending(
    game: PaydirtGameEngine,
    result: PlayResult,
    options: list[PenaltyOption],
    **procedure,
) -> PlayOutcome:
    choice = PenaltyChoice(result, penalty_options=options, offended_team="defense")
    state_before = deepcopy(game.state)
    rng_before = random.getstate()
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS, DefenseType.STANDARD, **procedure,
        )
    assert outcome.pending_penalty_decision
    assert game.state == state_before
    assert not game.play_log
    assert random.getstate() == rng_before
    return outcome


def decide(game: PaydirtGameEngine, outcome: PlayOutcome) -> tuple[bool, int]:
    accept_play, index = ComputerAI().should_accept_penalty(
        outcome, True, not game.state.is_home_possession,
    )
    return accept_play, index or 0


@pytest.mark.parametrize("down", [1, 2, 3])
def test_defense_enforces_fifteen_yards_instead_of_second_and_ten(
    game: PaydirtGameEngine, down: int,
) -> None:
    """AI-002: first-and-25 from midfield beats second-and-10 at midfield."""
    game.state.down = down
    outcome = pending(game, incomplete(), [foul(15)])
    assert outcome.retained_play_situation == PenaltySituation(50, down + 1, 10, False)
    assert outcome.penalty_situations == {0: PenaltySituation(35, down, 25, False)}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    final = game.apply_penalty_decision(outcome, accept_play, index)
    assert final.penalty_applied
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (35, down, 25)
    assert game.state.offense_stats.penalties == 1
    assert game.state.offense_stats.penalty_yards == 15
    assert game.state.defense_stats.penalties == 0


def test_defense_keeps_a_retained_loss_that_beats_a_shorter_foul(
    game: PaydirtGameEngine,
) -> None:
    """Ten yards back on third-and-22 is better than five back on second-and-15."""
    game.state.ball_position = 40
    game.state.down = 2
    outcome = pending(game, PlayResult(ResultType.SACK, yards=-12, description="Sack"), [foul(5)])
    assert outcome.retained_play_situation == PenaltySituation(28, 3, 22, False)
    assert outcome.penalty_situations == {0: PenaltySituation(35, 2, 15, False)}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (True, 0)

    game.apply_penalty_decision(outcome, accept_play, index)
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (28, 3, 22)
    assert game.state.offense_stats.penalties == 0


def test_defense_enforces_a_longer_foul_over_a_short_retained_loss(
    game: PaydirtGameEngine,
) -> None:
    """Five yards back on second-and-15 beats three yards back on third-and-13."""
    game.state.ball_position = 40
    game.state.down = 2
    outcome = pending(game, PlayResult(ResultType.YARDS, yards=-3, description="Loss of 3"), [foul(5)])
    assert outcome.retained_play_situation == PenaltySituation(37, 3, 13, False)
    assert outcome.penalty_situations == {0: PenaltySituation(35, 2, 15, False)}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    game.apply_penalty_decision(outcome, accept_play, index)
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (35, 2, 15)


def test_defense_declines_when_the_retained_play_turns_the_ball_over_on_downs(
    game: PaydirtGameEngine,
) -> None:
    """A fourth-down stop is worth more than replaying fourth down."""
    game.state.ball_position = 40
    game.state.down = 4
    game.state.yards_to_go = 1
    offense_was_home = game.state.is_home_possession
    outcome = pending(game, incomplete(), [foul(5)])
    assert outcome.retained_play_situation is None
    assert outcome.penalty_situations == {}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (True, 0)

    final = game.apply_penalty_decision(outcome, accept_play, index)
    assert final.turnover_on_downs
    assert game.state.is_home_possession is not offense_was_home
    assert game.state.defense_stats.penalties == 0


def test_half_distance_enforcement_uses_the_real_spot_without_state_changes(
    game: PaydirtGameEngine,
) -> None:
    """Backed up on the five, the enforced half distance is only two yards."""
    game.state.ball_position = 5
    game.state.down = 2
    game.state.yards_to_go = 10
    outcome = pending(game, incomplete(), [foul(15)])
    assert outcome.retained_play_situation == PenaltySituation(5, 3, 10, False)
    assert outcome.penalty_situations == {0: PenaltySituation(3, 2, 12, False)}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    for situation_index, situation in outcome.penalty_situations.items():
        clone = deepcopy(game)
        final = clone.apply_penalty_decision(deepcopy(outcome), False, situation_index)
        assert (situation.ball_position, situation.down, situation.yards_to_go, situation.first_down) == (
            clone.state.ball_position, clone.state.down, clone.state.yards_to_go, final.first_down,
        )


def test_multiple_fouls_compare_all_options_with_original_indices(
    game: PaydirtGameEngine,
) -> None:
    """An ineligible defensive option must not shift the reported index."""
    outcome = pending(game, incomplete(), [foul(10, kind="DEF"), foul(5), foul(15)])
    assert sorted(outcome.penalty_situations) == [1, 2]

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 2)

    game.apply_penalty_decision(outcome, accept_play, index)
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (35, 1, 25)


def test_requested_spike_keeps_the_existing_policy(game: PaydirtGameEngine) -> None:
    choice = PenaltyChoice(incomplete(), penalty_options=[foul(15)], offended_team="defense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True,
        )
    assert outcome.retained_play_situation is None
    assert outcome.penalty_situations == {}
    assert decide(game, outcome) == (True, 0)


def test_projected_touchdown_keeps_the_existing_erasure_policy(
    game: PaydirtGameEngine,
) -> None:
    """A foul still erases a projected score through the score path."""
    game.state.ball_position = 90
    outcome = pending(game, PlayResult(ResultType.YARDS, yards=10, description="Gain of 10"), [foul(5)])
    assert outcome.projected_touchdown
    assert outcome.retained_play_situation is None
    assert outcome.penalty_situations == {}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)

    final = game.apply_penalty_decision(outcome, accept_play, index)
    assert not final.touchdown
    assert game.state.home_score + game.state.away_score == 0


def test_retained_safety_keeps_the_existing_decline(game: PaydirtGameEngine) -> None:
    game.state.ball_position = 3
    game.state.down = 2
    outcome = pending(game, PlayResult(ResultType.SACK, yards=-3, description="Sack"), [foul(5)])
    assert outcome.retained_play_situation is None
    assert outcome.penalty_situations == {}
    assert decide(game, outcome) == (True, 0)


def test_real_priority_chart_foul_projects_the_enforced_situation(
    game: PaydirtGameEngine,
) -> None:
    with (
        patch("paydirt.play_resolver.get_offense_result", side_effect=["OFF 15", "BLACK"]),
        patch("paydirt.play_resolver.get_defense_modifier", return_value="0"),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(10, "synthetic 10")),
    ):
        outcome = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision
    assert outcome.penalty_choice.penalty_options[0].penalty_type == "OFF"
    assert outcome.retained_play_situation == PenaltySituation(50, 2, 10, False)
    assert outcome.penalty_situations == {0: PenaltySituation(35, 1, 25, False)}

    accept_play, index = decide(game, outcome)
    assert (accept_play, index) == (False, 0)
    game.apply_penalty_decision(outcome, accept_play, index)
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (35, 1, 25)


def late_game(
    down: int, *, defense_timeouts: int, defense_trailing: bool = True,
    seconds: int = 35,
) -> PaydirtGameEngine:
    """Q4, 35 seconds left, offense leading by seven at midfield."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 50
    game.state.down = down
    game.state.yards_to_go = 10
    game.state.quarter = 4
    game.state.time_remaining = seconds / 60
    game.state.home_score = 7 if defense_trailing else 0
    game.state.away_score = 0 if defense_trailing else 7
    game.state.home_timeouts = 3
    game.state.away_timeouts = defense_timeouts
    return game


def timed_decision(game: PaydirtGameEngine, outcome) -> tuple[bool, int]:
    """Decide with the live engine so clock, score and timeouts are visible."""
    accept_play, index = ComputerAI().should_accept_penalty(
        outcome, True, not game.state.is_home_possession, game=game,
    )
    return accept_play, index or 0


def applied(game: PaydirtGameEngine, outcome, accept_play: bool, index: int = 0):
    clone = deepcopy(game)
    return clone, clone.apply_penalty_decision(deepcopy(outcome), accept_play, index)


def _first_down(game: PaydirtGameEngine) -> bool:
    """Whether the most recently applied play earned a first down."""
    return bool(game.play_log and game.play_log[-1].first_down)


@pytest.mark.parametrize(
    "down,defense_timeouts",
    [(2, 1), (3, 0)],
    ids=["second-down-one-timeout", "third-down-no-timeouts"],
)
def test_trailing_defense_declines_a_foul_that_lets_the_offense_kneel_out(
    down: int, defense_timeouts: int,
) -> None:
    """AI-031: enforcement can create a kneel-out that the decline prevents."""
    game = late_game(down, defense_timeouts=defense_timeouts)
    outcome = pending(game, incomplete(), [foul(5)])
    accepted, index = timed_decision(game, outcome)

    enforced_game, enforced = applied(game, outcome, False, index)
    declined_game, _declined = applied(game, outcome, True, index)

    assert enforced.penalty_applied is True
    assert enforced_game.can_kneel_out_game() is True, "fixture must reproduce the bug"
    assert declined_game.can_kneel_out_game() is False, "declining must preserve a chance"
    assert (accepted, index) == (True, 0)


def test_trailing_defense_enforces_when_both_choices_allow_a_kneel_out() -> None:
    """AI-031: with no clock gain available, keep the better field position."""
    game = late_game(2, defense_timeouts=0)
    outcome = pending(game, incomplete(), [foul(5)])
    accepted, index = timed_decision(game, outcome)

    enforced_game, _ = applied(game, outcome, False, index)
    declined_game, _ = applied(game, outcome, True, 0)
    assert enforced_game.can_kneel_out_game() is True
    assert declined_game.can_kneel_out_game() is True
    assert (accepted, index) == (False, 0)


def test_trailing_defense_enforces_when_neither_choice_allows_a_kneel_out() -> None:
    """AI-031 control: the guard only applies when it changes the outcome."""
    game = late_game(3, defense_timeouts=1)
    outcome = pending(game, incomplete(), [foul(5)])
    accepted, index = timed_decision(game, outcome)

    enforced_game, _ = applied(game, outcome, False, index)
    declined_game, _ = applied(game, outcome, True, 0)
    assert enforced_game.can_kneel_out_game() is False
    assert declined_game.can_kneel_out_game() is False
    assert (accepted, index) == (False, 0)


def test_leading_defense_keeps_the_strict_position_comparison() -> None:
    """AI-031: urgency applies only to a defense that must get the ball back."""
    game = late_game(3, defense_timeouts=0, defense_trailing=False)
    outcome = pending(game, incomplete(), [foul(5)])
    accepted, index = timed_decision(game, outcome)

    enforced_game, _ = applied(game, outcome, False, index)
    assert enforced_game.state.home_score < enforced_game.state.away_score
    assert enforced_game.can_kneel_out_game() is False
    assert (accepted, index) == (False, 0)


def test_decision_without_game_context_keeps_the_position_heuristic() -> None:
    """AI-031: callers that pass no game keep the AI-002 ordering."""
    game = late_game(2, defense_timeouts=1)
    outcome = pending(game, incomplete(), [foul(5)])
    assert ComputerAI().should_accept_penalty(outcome, True, False) == (False, 0)


def test_declining_after_the_late_game_check_does_not_return_a_stale_index() -> None:
    """AI-031: a decline must not carry the enforcement it chose not to take."""
    game = late_game(2, defense_timeouts=1)
    outcome = pending(game, incomplete(), [foul(5), foul(10)])
    assert outcome.penalty_situations[1].ball_position < outcome.penalty_situations[0].ball_position

    accepted, index = ComputerAI().should_accept_penalty(
        outcome, True, not game.state.is_home_possession, game=game,
    )

    decided_game, decided = applied(game, outcome, accepted, index or 0)
    assert (accepted, index) == (True, None)
    assert decided.penalty_applied is False
    assert decided_game.state.down == 3

@pytest.mark.parametrize(
    "seconds,enforced_kneels_out",
    [(40, True), (45, True), (46, False)],
    ids=["forty-seconds", "forty-five-seconds", "forty-six-seconds"],
)
def test_late_game_guard_uses_the_post_decision_clock(
    seconds: int, enforced_kneels_out: bool,
) -> None:
    """AI-033: enforcement charges five seconds before the offense kneels."""
    game = late_game(3, defense_timeouts=0, seconds=seconds)
    outcome = pending(game, incomplete(), [foul(5)])

    accepted, index = timed_decision(game, outcome)
    enforced_game, _ = applied(game, outcome, False, 0)
    declined_game, _ = applied(game, outcome, True, 0)

    assert enforced_game.state.time_remaining == pytest.approx((seconds - 5) / 60)
    assert declined_game.state.time_remaining == pytest.approx((seconds - 5) / 60)
    assert enforced_game.can_kneel_out_game() is enforced_kneels_out
    assert declined_game.can_kneel_out_game() is False
    assert (accepted, index) == (True, 0) if enforced_kneels_out else (False, 0)


@pytest.mark.parametrize(
    "accept_play", [True, False], ids=["retained-play", "enforced-foul"],
)
def test_projected_situation_matches_the_applied_decision_clock(
    accept_play: bool,
) -> None:
    """AI-033: coaching must see the clock the decision actually produces."""
    game = late_game(3, defense_timeouts=0, seconds=45)
    outcome = pending(
        game,
        PlayResult(ResultType.YARDS, 9, description="Nine-yard completion"),
        [foul(5)],
    )
    projected = (
        outcome.retained_play_situation if accept_play
        else outcome.penalty_situations[0]
    )
    clone, _ = applied(game, outcome, accept_play, 0)

    assert (projected.ball_position, projected.down, projected.yards_to_go,
            projected.first_down) == (
        clone.state.ball_position, clone.state.down,
        clone.state.yards_to_go, _first_down(clone),
    )
    assert projected.time_remaining == pytest.approx(clone.state.time_remaining)


def test_projection_preserves_a_deferred_timeout_as_an_ineligible_request() -> None:
    """AI-033: a retained foul stops the clock, so the timeout saves no time."""
    game = late_game(3, defense_timeouts=1, seconds=45)
    game.state.ball_position = 30
    outcome = pending(
        game,
        PlayResult(ResultType.YARDS, 60, description="Sixty-yard completion"),
        [foul(5)],
        call_defensive_timeout=True,
    )
    projected = outcome.retained_play_situation
    clone, final = applied(game, outcome, True, 0)

    assert outcome.defensive_timeout_context is not None
    assert final.timeout_used is False
    assert clone.state.away_timeouts == 1
    assert clone.state.time_remaining == pytest.approx(34 / 60)
    assert projected.time_remaining == pytest.approx(clone.state.time_remaining)

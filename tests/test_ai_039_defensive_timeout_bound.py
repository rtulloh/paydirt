"""AI-039: defensive timeouts require a plausible late-game comeback.

A trailing defense calls a timeout to stop the clock, but the stop is only
useful when the deficit can still be erased in the time left. These regressions
keep the existing one- and two-score windows and reject unrecoverable multi-score
states, including the 32-point fourth-quarter blowout from the play-test.
"""

import random
from collections.abc import Iterator

import pytest

from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.fixture(autouse=True)
def preserve_randomness() -> Iterator[None]:
    before = random.getstate()
    yield
    random.setstate(before)


def timeout_state(
    *,
    minutes: float,
    deficit: int,
    home_cpu: bool,
    quarter: int = 4,
    overtime: bool = False,
    two_point: bool = True,
    timeouts: int = 3,
):
    """Public 2026 charts with the CPU defending and trailing by ``deficit``."""
    game = make_sample_game()
    game.season_rules.two_point_conversion = two_point
    state = game.state
    state.is_home_possession = not home_cpu
    if home_cpu:
        state.home_score, state.away_score = 0, deficit
        state.home_timeouts = timeouts
    else:
        state.home_score, state.away_score = deficit, 0
        state.away_timeouts = timeouts
    state.quarter = 5 if overtime else quarter
    state.is_overtime = overtime
    state.time_remaining = minutes
    state.two_minute_warning_called = True
    ai = create_computer_ai("hard", game, cpu_is_home=home_cpu)
    return game, ai


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize("two_point", [False, True])
@pytest.mark.parametrize("minutes", [4.5, 1.0])
def test_unrecoverable_q4_blowout_does_not_call_defensive_timeout(
    home_cpu: bool, two_point: bool, minutes: float,
) -> None:
    """Down 32, even inside two minutes, cannot be erased; retain the timeouts."""
    game, ai = timeout_state(minutes=minutes, deficit=32, home_cpu=home_cpu,
                             two_point=two_point)

    assert ai.should_call_timeout_on_defense(game) is False


@pytest.mark.parametrize("home_cpu", [False, True])
def test_final_two_minute_branch_keeps_a_two_score_bound(home_cpu: bool) -> None:
    """The old unconditional final-two-minute branch still needs a comeback."""
    blowout, blowout_ai = timeout_state(
        minutes=1.0, deficit=40, home_cpu=home_cpu, two_point=False)
    comeback, comeback_ai = timeout_state(
        minutes=1.0, deficit=14, home_cpu=home_cpu, two_point=False)

    assert blowout_ai.should_call_timeout_on_defense(blowout) is False
    assert comeback_ai.should_call_timeout_on_defense(comeback) is True


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize("two_point", [False, True])
@pytest.mark.parametrize(
    ("minutes", "deficit", "expected"),
    [
        (4.5, 8, False),
        (3.98, 8, True),
        (4.5, 10, False),
        (3.98, 10, True),
        (4.5, 13, False),
        (3.98, 13, True),
    ],
)
def test_touchdown_plus_window_remains_four_minutes(
    home_cpu: bool, two_point: bool, minutes: float, deficit: int, expected: bool,
) -> None:
    """AI-039 must not widen the existing 8-13 point window from 4:00 to 5:00."""
    game, ai = timeout_state(minutes=minutes, deficit=deficit, home_cpu=home_cpu,
                             two_point=two_point)

    assert ai.should_call_timeout_on_defense(game) is expected


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize("two_point", [False, True])
def test_fourteen_point_deficit_keeps_the_five_minute_window(
    home_cpu: bool, two_point: bool,
) -> None:
    """The original five-minute branch remains available at -14 and worse."""
    game, ai = timeout_state(minutes=4.5, deficit=14, home_cpu=home_cpu,
                             two_point=two_point)

    assert ai.should_call_timeout_on_defense(game) is True


@pytest.mark.parametrize("home_cpu", [False, True])
def test_last_minute_field_goal_deficit_still_calls_timeout(home_cpu: bool) -> None:
    """Trailing by three with 1:30 left is a genuine one-score comeback."""
    game, ai = timeout_state(minutes=1.5, deficit=3, home_cpu=home_cpu, two_point=False)

    assert ai.should_call_timeout_on_defense(game) is True


@pytest.mark.parametrize("home_cpu", [False, True])
def test_two_score_deficit_stays_aggressive_in_the_final_minutes(home_cpu: bool) -> None:
    """The AI-039 bound must not remove existing two-score timeout behaviour."""
    game, ai = timeout_state(minutes=1.5, deficit=13, home_cpu=home_cpu, two_point=False)

    assert ai.should_call_timeout_on_defense(game) is True


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize("two_point", [False, True])
def test_three_score_deficit_without_the_clock_does_not_call(
    home_cpu: bool, two_point: bool,
) -> None:
    """A 17-point deficit with 2:58 left requires three scoring possessions."""
    game, ai = timeout_state(minutes=2 + 58 / 60, deficit=17, home_cpu=home_cpu,
                             two_point=two_point)

    assert ai.should_call_timeout_on_defense(game) is False


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize("deficit", [15, 21, 24])
def test_three_or_more_score_deficit_is_always_bounded(
    home_cpu: bool, deficit: int,
) -> None:
    """Every three-score state inside the five-minute window is unrecoverable."""
    game, ai = timeout_state(minutes=4.5, deficit=deficit, home_cpu=home_cpu, two_point=False)

    assert ai.should_call_timeout_on_defense(game) is False


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize(("two_point", "expected"), [(True, True), (False, False)])
def test_fifteen_point_deficit_uses_the_seasons_score_count(
    home_cpu: bool, two_point: bool, expected: bool,
) -> None:
    """Down 15 is two scores with conversions and three without."""
    game, ai = timeout_state(minutes=4.5, deficit=15, home_cpu=home_cpu,
                             two_point=two_point)

    assert game.season_rules.scores_needed(15) == (2 if two_point else 3)
    assert ai.should_call_timeout_on_defense(game) is expected


def test_comeback_estimate_admits_a_longer_clock() -> None:
    """The clock bound is live even though the five-minute window caps it."""
    game, ai = timeout_state(minutes=6.0, deficit=15, home_cpu=True, two_point=False)

    assert ai._defensive_timeout_comeback_reachable(game, 15, 6.0) is True
    assert ai._defensive_timeout_comeback_reachable(game, 15, 5.0) is False
    assert ai.should_call_timeout_on_defense(game) is False


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize(
    ("minutes", "deficit", "expected"),
    [(1.5, 3, False), (1.5, 7, True), (0.9, 3, True), (0.9, 13, True)],
)
def test_second_quarter_trailing_behaviour_is_unchanged(
    home_cpu: bool, minutes: float, deficit: int, expected: bool,
) -> None:
    """End-of-half timeouts keep their existing score rules."""
    game, ai = timeout_state(minutes=minutes, deficit=deficit, home_cpu=home_cpu,
                             quarter=2, two_point=False)

    assert ai.should_call_timeout_on_defense(game) is expected


@pytest.mark.parametrize("home_cpu", [False, True])
@pytest.mark.parametrize(("minutes", "cpu_lead"), [(1.0, 0), (4.0, 0), (1.0, 7)])
def test_tied_or_leading_cpu_never_calls_defensive_timeout(
    home_cpu: bool, minutes: float, cpu_lead: int,
) -> None:
    """Only a trailing defense has a reason to stop the clock."""
    game = make_sample_game()
    state = game.state
    state.is_home_possession = not home_cpu
    cpu_score = 21 + cpu_lead
    opponent_score = 21
    if home_cpu:
        state.home_score, state.away_score = cpu_score, opponent_score
        state.home_timeouts = 3
    else:
        state.home_score, state.away_score = opponent_score, cpu_score
        state.away_timeouts = 3
    state.quarter, state.time_remaining = 4, minutes
    ai = create_computer_ai("hard", game, cpu_is_home=home_cpu)

    assert ai.should_call_timeout_on_defense(game) is False


def test_seeded_hard_drive_keeps_all_timeouts_in_a_blowout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A seeded Hard defense does not spend a timeout while down 32 in Q4.

    The offense is held to a repeatable nine-yard run so possession and the
    clock advance through the real engine. Before AI-039 every snap in this
    state requested a timeout, spending all three by the two-minute mark.
    """
    game, ai = timeout_state(minutes=4.5, deficit=32, home_cpu=True, two_point=True)
    game.state.possession_team.offense.line_plunge = dict.fromkeys(range(10, 40), "9")
    game.state.home_chart.defense.modifiers.clear()
    game.state.away_chart.defense.modifiers.clear()
    game.state.down, game.state.yards_to_go = 1, 10
    game.state.ball_position = 40
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: 35)

    random.seed(39039)
    decisions = 0
    while game.state.time_remaining > 1.0 and not game.state.game_over:
        decision = ai.should_call_timeout_on_defense(game)
        assert decision is False
        decisions += 1
        outcome = game.run_play_with_penalty_procedure(
            PlayType.LINE_PLUNGE, DefenseType.STANDARD,
            call_defensive_timeout=decision,
        )
        assert not outcome.pending_penalty_decision
        assert game.state.home_timeouts == 3

    assert decisions >= 3
    assert game.state.home_timeouts == 3

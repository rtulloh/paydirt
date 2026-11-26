"""AI-037: fourth down must reach the two-minute drill and stay off the global dice.

The fourth-down block returns before the two-minute drill is evaluated, so a
conversion attempt in a genuine hurry-up state (end of half, or a Q4 blowout)
was called with ordinary pace. Its sideline designation also drew from the
global ``random`` module, which the coaching/dice isolation invariant forbids.
"""

import random
from collections import Counter
from unittest.mock import patch

import pytest

from paydirt.play_resolver import CHART_PLAY_TYPES, PlayType, is_passing_play
from paydirt.season_rules import _era_ai_behavior
from tests.test_ai_offense_variety import synthetic_ai


@pytest.fixture(autouse=True)
def preserve_randomness():
    before = random.getstate()
    yield
    random.setstate(before)


def fourth_down_game(
    *,
    minutes: float,
    deficit: int,
    quarter: int = 4,
    distance: int = 5,
    position: int = 45,
    year: int = 2024,
):
    """Public 2026 charts on fourth down, with an era profile and a fixed clock."""
    game, ai = synthetic_ai()
    game.state.quarter = quarter
    game.state.time_remaining = minutes
    game.state.home_score, game.state.away_score = 0, deficit
    game.state.down, game.state.yards_to_go = 4, distance
    game.state.ball_position = position
    ai.ai_behavior = _era_ai_behavior(year)
    ai._offense_rng = random.Random(8306)
    return game, ai


@pytest.mark.parametrize(
    ("minutes", "deficit", "quarter", "position", "label"),
    [
        (3.25, 21, 4, 45, "Q4 blowout inside the desperation window"),
        (1.5, 4, 2, 45, "Q2 end of half while trailing"),
        (1.5, -3, 2, 45, "Q2 end of half while leading"),
    ],
)
def test_fourth_down_conversion_reaches_the_two_minute_drill(
    minutes: float, deficit: int, quarter: int, position: int, label: str,
) -> None:
    """A conversion attempt gets the same pace treatment as 1st-3rd down."""
    game, ai = fourth_down_game(
        minutes=minutes, deficit=deficit, quarter=quarter,
        distance=1, position=position,
    )

    assert ai._is_two_minute_drill(game, minutes, quarter, -deficit), label

    play, _oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)

    assert play not in (PlayType.PUNT, PlayType.FIELD_GOAL), label
    assert ai.last_mode == "Two-Minute Drill", label
    assert no_huddle is True, label


@pytest.mark.parametrize("minutes,deficit", [(3.25, 21), (1.5, 4)])
@pytest.mark.parametrize("kick", [PlayType.PUNT, PlayType.FIELD_GOAL])
def test_fourth_down_kick_pace_is_unchanged(
    minutes: float, deficit: int, kick: PlayType,
) -> None:
    """Kicks keep their pre-existing pace flagging, which this fix must not alter.

    The kick decision is supplied directly so the test isolates the pace path
    rather than arguing with the fourth-down go/punt/field-goal policy.
    """
    game, ai = fourth_down_game(minutes=minutes, deficit=deficit, position=35, distance=8)
    expected = ai._needs_hurry_up(game, minutes, 4, -deficit)

    with patch.object(ai, "_fourth_down_decision", return_value=(kick, False, 0)):
        play, use_oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)

    assert play is kick
    assert ai.last_mode == "4th Down"
    assert use_oob is False
    assert no_huddle is expected


@pytest.mark.parametrize(
    ("minutes", "deficit", "quarter", "two_minute", "label"),
    [
        (12.0, 21, 4, False, "Q4 blowout with the whole quarter left"),
        (1.5, 4, 2, True, "Q2 end of half while trailing"),
    ],
)
def test_fourth_down_punt_inside_a_two_minute_state_stays_a_punt(
    minutes: float, deficit: int, quarter: int, two_minute: bool, label: str,
) -> None:
    """Reaching the two-minute drill must not turn a kick into a conversion."""
    game, ai = fourth_down_game(
        minutes=minutes, deficit=deficit, quarter=quarter, distance=5, position=60,
    )

    assert ai._is_two_minute_drill(game, minutes, quarter, -deficit) is two_minute, label

    play, _oob, _no_huddle, *_ = ai.select_offense_with_clock_management(game)

    assert play in (PlayType.PUNT, PlayType.FIELD_GOAL), label
    assert ai.last_mode == "4th Down", label


@pytest.mark.parametrize(
    ("minutes", "deficit", "quarter", "distance"),
    [(3.25, 21, 4, 5), (1.5, 3, 2, 1)],
)
def test_fourth_down_hurry_choice_keeps_chart_calls(
    minutes: float, deficit: int, quarter: int, distance: int,
) -> None:
    """Pace never becomes pass-only: credible runs stay in the mixture.

    Uses the states where the conversion decision itself goes for it; the
    invariant here is that hurry-up does not add a pass quota or ban runs.
    """
    game, ai = fourth_down_game(minutes=minutes, deficit=deficit, quarter=quarter, distance=distance)
    counts: Counter[PlayType] = Counter()
    for seed in range(60):
        ai._offense_rng = random.Random(seed)
        play, _oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)
        if play in (PlayType.PUNT, PlayType.FIELD_GOAL):
            continue
        assert no_huddle is True
        counts[play] += 1

    assert sum(counts.values()) > 0
    assert any(not is_passing_play(play) for play in counts), counts
    assert any(is_passing_play(play) for play in counts), counts


def test_fourth_down_hurry_oob_uses_the_coaching_stream() -> None:
    """The sideline draw must never advance the gameplay dice."""
    game, ai = fourth_down_game(minutes=3.25, deficit=21, distance=8, position=45)
    ai.ai_behavior.strategic.oob_designation_aggression = 1.0

    with patch("paydirt.computer_ai.random.random", side_effect=AssertionError("global dice used")):
        play, use_oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)

    assert is_passing_play(play)
    assert (use_oob, no_huddle) == (True, True)


def test_fourth_down_hurry_oob_is_seed_reproducible() -> None:
    """The same coaching seed reproduces the same sideline decision."""
    results = []
    for _ in range(2):
        game, ai = fourth_down_game(minutes=3.25, deficit=21, distance=8)
        ai.ai_behavior.strategic.oob_designation_aggression = 0.5
        for seed in range(12):
            ai._offense_rng = random.Random(seed)
            play, use_oob, _no_huddle, *_ = ai.select_offense_with_clock_management(game)
            results.append((seed, play, use_oob))
    assert results[:12] == results[12:]
    assert any(use_oob for _seed, _play, use_oob in results[:12])


@pytest.mark.parametrize("down", [1, 4])
@pytest.mark.parametrize(
    ("forced_play", "expected_oob"),
    [
        (PlayType.TE_SHORT_LONG, False),
        (PlayType.SCREEN, True),
        (PlayType.MEDIUM_PASS, True),
        (PlayType.DRAW, False),
    ],
)
def test_fourth_down_sideline_predicate_matches_first_through_third(
    down: int, forced_play: PlayType, expected_oob: bool,
) -> None:
    """The sideline predicate must not differ between 4th down and 1st-3rd.

    The canonical hurry-up paths gate the sideline draw on an explicit
    short/medium/long/screen tuple. ``is_passing_play`` is wider and includes
    ``TE_SHORT_LONG``, so using it here would hand a fourth-down tight-end
    route a sideline designation that the same call never gets on 1st-3rd.
    """
    game, ai = fourth_down_game(minutes=3.25, deficit=21, distance=8, position=45)
    game.state.down = down
    ai.ai_behavior.strategic.oob_designation_aggression = 1.0

    with patch.object(ai, "get_hurry_up_weights", return_value={forced_play: 1.0}):
        play, use_oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)

    assert play is forced_play
    assert no_huddle is True
    assert use_oob is expected_oob


def test_fourth_down_conversion_falls_back_to_the_ordinary_hurry_gate() -> None:
    """A conversion outside the two-minute drill still uses the hurry gate.

    Q4, 3:00, down 5 is inside ``_needs_hurry_up`` (five-minute window) but
    outside the two-minute drill (three-minute window is strict), so the
    conversion path must keep the ordinary sideline/no-huddle flagging rather
    than forcing the mixture.
    """
    game, ai = fourth_down_game(minutes=3.0, deficit=5, distance=5, position=65)
    score_diff = game.state.home_score - game.state.away_score

    assert ai._needs_hurry_up(game, 3.0, 4, score_diff)
    assert not ai._is_two_minute_drill(game, 3.0, 4, score_diff)

    ai.ai_behavior.strategic.oob_designation_aggression = 1.0
    ai._offense_rng = random.Random(8306)
    play, use_oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)

    assert play not in (PlayType.PUNT, PlayType.FIELD_GOAL)
    assert ai.last_mode == "4th Down"
    assert no_huddle is True
    assert use_oob is ai._sideline_eligible(play)

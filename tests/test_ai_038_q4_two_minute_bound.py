"""AI-038: the Q4 catch-all must not run all quarter, and pace predicates agree."""

import pytest

from paydirt.computer_ai import create_computer_ai
from tests.test_ai_offense_variety import synthetic_ai


@pytest.fixture
def game_and_ai():
    game, _ = synthetic_ai(home=True)
    ai = create_computer_ai("hard", game, True)
    game.state.is_home_possession = True
    game.state.home_score = 0
    game.state.away_score = 14
    return game, ai


@pytest.mark.parametrize("minutes,quarter,deficit,expected", [
    (12.0, 4, 14, False),
    (5.0, 4, 14, False),
    (3.01, 4, 14, True),
    (2.5, 4, 14, True),
    (1.0, 4, 14, True),
    (1.0, 3, 14, False),
    (12.0, 4, 13, False),
    (1.0, 4, 13, True),
])
def test_q4_fourteen_catch_all_respects_documented_clock_window(
    game_and_ai, minutes: float, quarter: int, deficit: int, expected: bool,
) -> None:
    game, ai = game_and_ai
    game.state.quarter = quarter
    game.state.time_remaining = minutes
    game.state.home_score = 0
    game.state.away_score = deficit
    score_diff = game.state.home_score - game.state.away_score
    assert ai._is_two_minute_drill(game, minutes, quarter, score_diff) is expected


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("deficit", [0, 3, 7, 8, 9, 13, 14, 17, 21, 28])
@pytest.mark.parametrize("minutes", [15.0, 12.0, 5.0, 3.01, 3.0, 2.99, 2.5, 2.0, 1.0, 0.1])
def test_two_minute_drill_implies_hurry_up(
    game_and_ai, quarter: int, deficit: int, minutes: float,
) -> None:
    game, ai = game_and_ai
    game.state.quarter = quarter
    game.state.time_remaining = minutes
    for signed_diff in (deficit, -deficit):
        game.state.home_score = max(signed_diff, 0)
        game.state.away_score = max(-signed_diff, 0)
        if ai._is_two_minute_drill(game, minutes, quarter, signed_diff):
            assert ai._needs_hurry_up(game, minutes, quarter, signed_diff), (
                quarter, minutes, signed_diff
            )


def test_q4_twelve_minute_deficit_is_ordinary_not_two_minute_drill(game_and_ai) -> None:
    game, ai = game_and_ai
    game.state.quarter, game.state.time_remaining = 4, 12.0
    play, use_oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)
    assert ai.last_mode != "Two-Minute Drill"
    assert no_huddle is False
    assert play.value in {
        "line_plunge", "off_tackle", "end_run", "draw", "screen",
        "short_pass", "medium_pass", "long_pass", "te_short_long",
    }


def test_q4_two_thirty_deficit_still_uses_two_minute_drill(game_and_ai) -> None:
    game, ai = game_and_ai
    game.state.quarter, game.state.time_remaining = 4, 2.5
    play, use_oob, no_huddle, *_ = ai.select_offense_with_clock_management(game)
    assert ai.last_mode == "Two-Minute Drill"
    assert no_huddle is True
    assert ai._needs_hurry_up(game, 2.5, 4, -14)

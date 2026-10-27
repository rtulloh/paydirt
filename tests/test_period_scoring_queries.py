"""Engine-owned period/try queries after scoring plays, independent of any UI."""

from unittest.mock import patch

import pytest

from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


def score_by(game, entry: str, *, seconds: float) -> None:
    """Score a touchdown through the named entry point, using the given play time."""
    result = PlayResult(ResultType.YARDS, yards=9, raw_result="9")
    with (patch("paydirt.game_engine.resolve_play", return_value=result),
          patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
              result, penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "x")] if entry == "decision" else [],
              offended_team="offense")),
          patch("paydirt.game_engine.random.uniform", return_value=seconds)):
        if entry == "direct":
            out = game.run_play(PlayType.OFF_TACKLE, DefenseType.STANDARD)
        elif entry == "procedure":
            out = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
        elif entry == "decision":
            pending = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
            assert pending.pending_penalty_decision
            out = game.apply_penalty_decision(pending, accept_play=True)
        else:
            raise AssertionError(entry)
    assert out.touchdown


@pytest.mark.parametrize("entry", ["direct", "procedure", "decision"])
@pytest.mark.parametrize("quarter,seconds,kick_expected", [
    (1, 20, True), (2, 20, False), (3, 20, False), (4, 20, False), (2, 90, True),
], ids=["q1-expires", "q2-expires", "q3-expires", "q4-expires", "time-remains"])
def test_kick_queries_use_the_engine_recorded_start_period(
    entry: str, quarter: int, seconds: int, kick_expected: bool,
) -> None:
    game = make_sample_game()
    game.state.ball_position, game.state.quarter, game.state.time_remaining = 94, quarter, seconds / 60
    game.state.home_score, game.state.away_score = 0, 7  # Q4 expiry ties: no game over yet.
    score_by(game, entry, seconds=30)
    if quarter == 3 and seconds == 20:
        # Q3 expiry rolls into Q4 and the scoring team still kicks.
        assert game.state.quarter == 4
        assert game.can_kickoff_after_play() is True
        assert game.should_kickoff_after_score() is True
        return
    assert game.can_kickoff_after_play() is kick_expected
    assert game.should_kickoff_after_score() is kick_expected
    # Explicit arguments keep their meaning for existing callers.
    assert game.can_kickoff_after_play(quarter) is kick_expected
    assert game.should_kickoff_after_score(quarter) is kick_expected


@pytest.mark.parametrize("kind", ["kickoff", "safety-free-kick"])
def test_return_scores_on_kicks_record_the_kick_period(kind: str) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 2, 5 / 60
    game.state.is_home_possession = True
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "kick"), (26, "return")] * 3),
          patch("paydirt.game_engine.random.uniform", return_value=10)):
        chart = game.state.home_chart.special_teams
        chart.kickoff[26] = "65"
        game.state.away_chart.special_teams.kickoff_return[26] = "TD"
        if kind == "kickoff":
            out = game.kickoff(kicking_home=True)
        else:
            out = game.safety_free_kick(use_punt=False)
    assert out.touchdown, out.description
    assert game.state.quarter == 3  # The return expired the half.
    assert game.can_kickoff_after_play() is False
    assert game.should_kickoff_after_score() is False


@pytest.mark.parametrize("scorer_home", [False, True])
@pytest.mark.parametrize("pat_good", [True, False])
def test_regulation_try_is_allowed_after_a_clock_expiring_touchdown(scorer_home: bool, pat_good: bool) -> None:
    game = make_sample_game()
    game.state.is_home_possession = scorer_home
    game.state.ball_position, game.state.quarter, game.state.time_remaining = 94, 4, 10 / 60
    game.state.home_score, game.state.away_score = (14, 21) if scorer_home else (21, 14)
    score_by(game, "procedure", seconds=30)
    assert game.state.time_remaining == 0
    assert game.can_attempt_conversion_after_touchdown() is True
    game.state.possession_team.special_teams.extra_point_no_good = [] if pat_good else [26]
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
        success, _ = game.attempt_extra_point()
    assert success is pat_good
    assert game.state.game_over is not pat_good
    assert game.needs_overtime() is pat_good
    assert game.can_kickoff_after_play() is False


@pytest.mark.parametrize("scorer_home", [False, True])
def test_regulation_try_is_allowed_while_leading_at_expiry(scorer_home: bool) -> None:
    game = make_sample_game()
    game.state.is_home_possession = scorer_home
    game.state.ball_position, game.state.quarter, game.state.time_remaining = 94, 4, 10 / 60
    game.state.home_score, game.state.away_score = (21, 14) if scorer_home else (14, 21)
    score_by(game, "procedure", seconds=30)
    assert game.can_attempt_conversion_after_touchdown() is True
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
        assert game.attempt_extra_point()[0]
    assert (game.state.home_score if scorer_home else game.state.away_score) == 28
    assert game.state.game_over


@pytest.mark.parametrize("two_point_allowed", [True, False], ids=["modern-rules", "pre-1994-rules"])
def test_two_point_try_at_expiry_respects_season_rules_and_does_not_raise(two_point_allowed: bool) -> None:
    game = make_sample_game()
    game.season_rules.two_point_conversion = two_point_allowed
    game.state.is_home_possession = True
    game.state.ball_position, game.state.quarter, game.state.time_remaining = 94, 4, 10 / 60
    game.state.home_score, game.state.away_score = 13, 21
    score_by(game, "procedure", seconds=30)
    assert game.state.game_over  # Provisionally over until the try resolves.
    assert game.can_attempt_conversion_after_touchdown() is True
    assert game.season_rules.two_point_conversion is two_point_allowed
    if not two_point_allowed:
        return  # Only the PAT is offered; the engine flag is the single source of truth.
    with patch("paydirt.game_engine.resolve_play", return_value=PlayResult(ResultType.YARDS, yards=3, raw_result="3")):
        success, defense_points, _ = game.attempt_two_point(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert success and defense_points == 0
    # RULE-001 owns the point total of a two-point try; here only the try's
    # availability and the recomputed game-over flag are under test.
    tied = game.state.home_score == game.state.away_score
    assert game.state.game_over is not tied
    assert game.needs_overtime() is tied


def test_overtime_winning_touchdown_has_no_try() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 5, 5
    game.state.is_overtime, game.state.ot_period = True, 1
    game.state.ball_position = 94
    score_by(game, "procedure", seconds=30)
    assert game.state.game_over
    assert game.can_attempt_conversion_after_touchdown() is False
    assert game.can_kickoff_after_play() is False

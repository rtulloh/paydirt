"""A voided punt return preserves the next play decision and period rights."""

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("seconds", [600, 3])
def test_return_offset_replays_the_down_without_executing_the_next_call(
    home: bool, procedure: bool, quarter: int, seconds: int,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    game.state.possession_team.special_teams.punt = {10: "40", 14: "40"}
    game.state.defense_team.special_teams.punt_return = {11: "OFF 10", 12: "DEF 15", 15: "3"}
    # Extra rolls are available to expose an accidental automatic second punt.
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 12, 14, 15]]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = run(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 3
    assert outcome.result.replay_down
    assert not outcome.pending_penalty_decision
    assert not outcome.turnover and not outcome.first_down and not outcome.touchdown
    assert game.state.is_home_possession is home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (40, 4, 8)
    assert game.state.quarter == quarter
    assert game.state.time_remaining == pytest.approx(max(0, seconds - 10) / 60)
    assert game.has_untimed_down() is (seconds <= 10)
    assert not game.state.game_over
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
    assert game.play_log == [outcome]
    assert outcome.clock_trace.requested_seconds == 10
    assert outcome.clock_trace.charged_seconds == min(10, seconds)
    assert outcome.result.dice_roll == 10
    assert outcome.result.punt_return_dice == 11
    assert "11" in outcome.description and "12" in outcome.description


def test_the_next_explicit_punt_uses_the_untimed_down() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 3 / 60
    game.state.home_chart.special_teams.punt = {10: "40", 14: "40"}
    game.state.away_chart.special_teams.punt_return = {11: "OFF 10", 12: "DEF 15", 15: "3"}
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 12, 14, 15]]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        first = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
        assert rolls.call_count == 3
        assert game.has_untimed_down()
        second = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 5
    assert first.result.replay_down and not second.result.replay_down
    assert not game.has_untimed_down()
    assert game.state.quarter == 3 and game.state.time_remaining == 15
    assert not game.state.is_home_possession
    assert game.state.ball_position == 23
    assert game.play_log == [first, second]


def test_gate_covers_return_only_offset_without_an_automatic_punt() -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    report = audit_observer_conformance()
    assert "PUNT/return-offset/next-call-preserved" in {row["case"] for row in report["checks"]}

"""A return foul can void a fumble after its primary result was selected."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.game_state import TeamStats
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("procedure", [False, True], ids=["direct", "penalty-procedure"])
@pytest.mark.parametrize("recovery", [17, 37], ids=["own-return", "lost-return"])
@pytest.mark.parametrize("category", ["rush", "completion", "qt-sack"])
@pytest.mark.parametrize("offsetting", [False, True], ids=["retained-control", "voided"])
def test_fumble_return_replay_has_no_scrimmage_credit(
    procedure: bool, recovery: int, category: str, offsetting: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 50, 2, 10
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_stats = TeamStats(total_yards=21, rushing_yards=8, passing_yards=13)
    before_home, before_away = deepcopy(game.state.home_stats), deepcopy(game.state.away_stats)
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = (10, 27)
        chart.special_teams.interception_return = {14: "DEF 15", 15: "OFF 15"} if offsetting else {14: "5"}
    play = PlayType.LINE_PLUNGE if category == "rush" else PlayType.SHORT_PASS
    initial = -12 if category == "qt-sack" else 3
    result = PlayResult(ResultType.FUMBLE, yards=initial, qb_scramble_dice=22 if category == "qt-sack" else 0)
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, play, DefenseType.STANDARD)
    dice = [recovery, 14, 15] if offsetting else [recovery, 14]
    with (patch("paydirt.game_engine.resolve_play", return_value=result),
          patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
          patch("paydirt.game_engine.roll_chart_dice", side_effect=[(roll, f"Roll {roll}") for roll in dice]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        if procedure:
            outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
        else:
            outcome = game.run_play(play, DefenseType.STANDARD)
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    assert rolls.call_count == len(dice)
    assert outcome.result.replay_down is offsetting
    totals = observer.report()["teams"][game.state.home_chart.peripheral.short_name]
    if offsetting:
        assert game.state.home_stats == before_home
        assert game.state.away_stats == before_away
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (50, 2, 10)
        assert game.state.is_home_possession
        assert game.state.time_remaining == pytest.approx(10 - 10 / 60)
        assert not outcome.turnover and not outcome.touchdown and not outcome.safety
        assert totals["offensive_plays"] == totals["pass_attempts"] == totals["rushing_attempts"] == totals["sacks"] == 0
    else:
        net = initial + (5 if recovery == 17 else 0)
        assert game.state.home_stats.total_yards == before_home.total_yards + net
        assert game.state.home_stats.sacks == int(category == "qt-sack")
        assert game.state.home_stats.turnovers == int(recovery == 37)
        assert totals["offensive_plays"] == totals["pass_attempts"] + totals["rushing_attempts"] + totals["sacks"] == 1

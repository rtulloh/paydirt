"""A fumbled punt snap never becomes a numeric punt or punt return."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType, ResultType
from paydirt.result_formatter import ResultFormatter
from tests.game_fixtures import make_sample_game


def punt_game(cell: str, position: int = 40, down: int = 4) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = position, down, 5
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: cell}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = (10, 31)
        chart.special_teams.interception_return = {14: "5"}
        chart.special_teams.punt_return = {14: "80"}
    return game


def run_punt(
    game: PaydirtGameEngine, dice: list[int], procedure: bool = False, **options: bool | int,
) -> tuple[PlayOutcome, dict[str, int | float]]:
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, PlayType.PUNT, DefenseType.STANDARD)
    with (patch("paydirt.game_engine.roll_chart_dice",
                side_effect=[(roll, f"Roll {roll}") for roll in dice]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        method = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = method(PlayType.PUNT, DefenseType.STANDARD, **options)
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    assert rolls.call_count == len(dice)
    return outcome, observer.report()["teams"]["HOME"]


@pytest.mark.parametrize("procedure", [False, True], ids=["direct", "procedure"])
@pytest.mark.parametrize("cell,yards", [("F", 0), ("F - 10", -10), ("F + 6", 6)])
@pytest.mark.parametrize("recovery", [20, 35], ids=["own", "lost"])
def test_punt_snap_fumble_uses_raw_spot_and_recovery(
    procedure: bool, cell: str, yards: int, recovery: int,
) -> None:
    game = punt_game(cell)
    outcome, totals = run_punt(game, [10, recovery], procedure)
    keeps_ball = recovery == 20 and yards >= 5
    assert game.state.is_home_possession is keeps_ball
    assert game.state.ball_position == (40 + yards if keeps_ball else 60 - yards)
    assert game.state.down == 1
    assert game.state.yards_to_go == 10
    assert outcome.result.result_type == ResultType.FUMBLE
    assert outcome.result.raw_result == cell
    assert outcome.result.yards == yards
    assert outcome.result.dice_roll == 10
    assert outcome.result.fumble_recovery_roll == recovery
    assert outcome.result.fumble_recovered is (recovery == 20)
    assert outcome.result.fumble_resolved
    assert outcome.result.punt_snap_fumble
    assert outcome.result.punt_return_dice == 0
    assert not outcome.result.punt_return_result
    assert outcome.turnover_on_downs is (recovery == 20 and not keeps_ball)
    assert outcome.turnover is (not keeps_ball)
    assert outcome.first_down is keeps_ball
    assert game.state.home_stats.fumbles_lost == int(recovery == 35)
    assert game.state.home_stats.turnovers == int(recovery == 35)
    assert totals["offensive_plays"] == totals["rushing_attempts"] == 1
    assert totals["pass_attempts"] == totals["sacks"] == 0
    assert game.play_log == [outcome]
    assert game.state.time_remaining == pytest.approx(10 - 8 / 60)
    assert "fumble" in outcome.description.lower()
    assert "40 yards" not in outcome.description.lower()


@pytest.mark.parametrize("short_drop,coffin", [(False, 0), (True, 0), (False, 20), (True, 20)])
def test_punt_options_cannot_replace_snap_fumble(short_drop: bool, coffin: int) -> None:
    game = punt_game("F - 2", position=4, down=2)
    outcome, _ = run_punt(game, [10, 20], punt_short_drop=short_drop,
                          punt_coffin_corner_yards=coffin)
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (2, 3, 7)
    assert outcome.result.fumble_spot == 2
    assert outcome.yards_gained == -2
    assert not outcome.turnover and not outcome.turnover_on_downs


def test_snap_fumble_headline_does_not_claim_a_negative_punt_distance() -> None:
    game = punt_game("F - 10", down=2)
    outcome, _ = run_punt(game, [10, 20])
    formatted = ResultFormatter("HOME", "AWAY").format(outcome)
    assert "FUMBLE" in formatted.headline
    assert "Punt -10 yards" not in formatted.headline


def test_own_snap_recovery_result_and_outcome_agree_on_possession() -> None:
    game = punt_game("F - 10", down=2)
    outcome, _ = run_punt(game, [10, 20])
    assert outcome.result.turnover is outcome.turnover is False


@pytest.mark.parametrize("recovery", [20, 35], ids=["own-safety", "defense-td"])
def test_punt_snap_fumble_in_own_end_zone(recovery: int) -> None:
    game = punt_game("F - 10", position=4)
    outcome, totals = run_punt(game, [10, recovery])
    assert outcome.safety is (recovery == 20)
    assert outcome.touchdown is (recovery == 35)
    assert game.state.away_score == (2 if recovery == 20 else 6)
    assert game.state.home_score == 0
    assert game.state.home_stats.fumbles_lost == int(recovery == 35)
    assert totals["rushing_attempts"] == totals["offensive_plays"] == 1


@pytest.mark.parametrize("recovery,home,spot", [(17, True, 35), (19, True, 35),
                                                        (37, False, 75), (39, False, 75)])
def test_punt_snap_fumble_uses_ordinary_fumble_return_rules(
    recovery: int, home: bool, spot: int,
) -> None:
    game = punt_game("F - 10", down=2)
    outcome, totals = run_punt(game, [10, recovery, 14])
    assert game.state.is_home_possession is home
    assert game.state.ball_position == spot
    assert outcome.result.fumble_return_dice == 14
    assert outcome.result.fumble_return_yards == 5
    assert not outcome.touchdown and not outcome.safety
    assert game.state.home_score == game.state.away_score == 0
    assert game.state.home_stats.fumbles_lost == int(not home)
    assert totals["offensive_plays"] == 1


@pytest.mark.parametrize("recovery", [17, 37])
@pytest.mark.parametrize("procedure", [False, True])
def test_punt_snap_fumble_offsetting_return_has_no_credit(recovery: int, procedure: bool) -> None:
    game = punt_game("F - 10", down=2)
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.special_teams.interception_return = {14: "DEF 15", 15: "OFF 15"}
    before = deepcopy((game.state.home_stats, game.state.away_stats))
    outcome, totals = run_punt(game, [10, recovery, 14, 15], procedure)
    assert outcome.result.replay_down
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (40, 2, 5)
    assert (game.state.home_stats, game.state.away_stats) == before
    assert not outcome.touchdown and not outcome.turnover and not outcome.safety
    assert totals["offensive_plays"] == totals["rushing_attempts"] == 0
    assert game.state.time_remaining == pytest.approx(10 - 10 / 60)


@pytest.mark.parametrize("cell,dice", [("40*", [10]), ("40†", [10]),
                                     ("40", [10, 14]), ("BK -10", [10, 35])])
@pytest.mark.parametrize("procedure", [False, True])
def test_actual_punts_do_not_become_aborted_scrimmage_calls(
    cell: str, dice: list[int], procedure: bool,
) -> None:
    game = punt_game(cell)
    outcome, totals = run_punt(game, dice, procedure)
    assert not getattr(outcome.result, "punt_snap_fumble", False)
    assert totals["offensive_plays"] == totals["rushing_attempts"] == 0

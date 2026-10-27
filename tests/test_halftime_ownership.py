"""Halftime is an engine fact: when it is pending and who kicks off the second half."""

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
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


def scrimmage(game, result: PlayResult, *, seconds: float = 30, penalty: bool = False):
    options = [PenaltyOption("DEF", "DEF 5", 5, "x")] if penalty else []
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
              result, penalty_options=options, offended_team="offense")),
          patch("paydirt.game_engine.random.uniform", return_value=seconds)):
        out = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
        if penalty:
            out = game.apply_penalty_decision(out, accept_play=True)
    return out


def kick(game, kicking_home: bool, *, seconds: float = 8, onside: bool = False):
    chart = (game.state.home_chart if kicking_home else game.state.away_chart).special_teams
    receiving = (game.state.away_chart if kicking_home else game.state.home_chart).special_teams
    chart.kickoff[24] = "60"
    receiving.kickoff_return[24] = "20"
    with (patch("paydirt.game_engine.roll_chart_dice", return_value=(24, "Roll24")),
          patch("paydirt.game_engine.random.uniform", return_value=seconds)):
        return game.onside_kick(kicking_home=kicking_home) if onside else game.kickoff(kicking_home=kicking_home)


@pytest.mark.parametrize("opening_home", [True, False])
@pytest.mark.parametrize("onside", [False, True])
def test_first_kick_records_the_opening_kicker_once(opening_home: bool, onside: bool) -> None:
    game = make_sample_game()
    assert game.state.opening_kicking_home is None
    kick(game, opening_home, onside=onside)
    assert game.state.opening_kicking_home is opening_home
    kick(game, not opening_home)  # A later kick never overwrites the opening record.
    assert game.state.opening_kicking_home is opening_home
    assert game.second_half_kicking_home() is (not opening_home)


def test_second_half_kicker_falls_back_to_possession_for_legacy_games() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    assert game.second_half_kicking_home() is False
    game.state.is_home_possession = False
    assert game.second_half_kicking_home() is True


TD = PlayResult(ResultType.YARDS, yards=9, raw_result="9")
SAFETY = PlayResult(ResultType.SACK, yards=-5, raw_result="-5")


@pytest.mark.parametrize("ending", ["touchdown", "touchdown-after-pat", "safety", "penalty-decision", "ordinary"])
def test_halftime_is_pending_after_any_play_that_expires_the_second_quarter(ending: str) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 2, 20 / 60
    game.state.is_home_possession = True
    game.state.ball_position = 3 if ending == "safety" else 94 if ending.startswith("touchdown") else 50
    result = SAFETY if ending == "safety" else TD if ending.startswith("touchdown") else PlayResult(ResultType.YARDS, yards=4, raw_result="4")
    scrimmage(game, result, penalty=(ending == "penalty-decision"))
    if ending == "touchdown-after-pat":
        with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
            game.attempt_extra_point()
    assert game.state.quarter == 3
    assert game.halftime_pending() is True
    assert game.should_kickoff_after_score() is False
    # The scheduled second-half kickoff clears it.
    kick(game, game.second_half_kicking_home())
    assert game.halftime_pending() is False


def test_halftime_is_pending_after_a_kick_return_that_expires_the_second_quarter() -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 2, 5 / 60
    kick(game, True, seconds=10)
    assert game.state.quarter == 3
    assert game.halftime_pending() is True


@pytest.mark.parametrize("quarter,seconds", [(1, 20), (3, 20), (4, 20), (2, 90)],
                         ids=["q1-expires", "q3-expires", "q4-expires", "time-remains"])
def test_other_period_changes_are_not_halftime(quarter: int, seconds: int) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    game.state.home_score, game.state.away_score = 0, 7
    game.state.ball_position = 94
    scrimmage(game, TD)
    assert game.halftime_pending() is False


def test_prepare_second_half_kickoff_gives_the_ball_to_the_correct_kicker() -> None:
    game = make_sample_game()
    kick(game, True)  # Home kicked to open.
    game.state.quarter, game.state.time_remaining = 2, 20 / 60
    game.state.is_home_possession = True
    game.state.ball_position = 94
    scrimmage(game, TD)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
        game.attempt_extra_point()
    assert game.halftime_pending()
    game.prepare_second_half_kickoff()
    assert game.state.is_home_possession is False  # Away kicks to start the second half.
    assert game.state.ball_position == 35
    assert game.state.down == 1 and game.state.yards_to_go == 10


@pytest.mark.parametrize("opening", [True, False, None])
def test_opening_kicker_survives_save_and_resume(tmp_path, opening) -> None:
    game = make_sample_game()
    game.state.opening_kicking_home = opening
    path = str(tmp_path / "halftime.json")
    save_game(game, filepath=path, human_is_away=True, human_is_home=False)
    loaded, _, _, _ = load_game(path)
    assert loaded.state.opening_kicking_home is opening

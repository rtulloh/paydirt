"""Public-fixture interception boundary controls for rule VI-12-E."""

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("raw_spot", [-11, -10])
@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("apply_path", ["handler", "run_play", "retained_play"])
def test_own_end_line_is_out_of_play_safety(
    raw_spot: int, offense_home: bool, apply_path: str,
) -> None:
    """An out-of-play lateral cannot become a defensive catch or return."""
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    game.state.ball_position = 5
    offense_stats = game.state.offense_stats
    defending_team = game.state.defense_team.peripheral.short_name
    result = PlayResult(
        result_type=ResultType.INTERCEPTION, yards=raw_spot - 5,
        turnover=True, raw_result=f"INT {raw_spot - 5}", dice_roll=10,
    )
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.roll_chart_dice") as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        if apply_path == "handler":
            turnover, touchdown, safety = game._handle_interception(result, 5, result.yards)
        else:
            if apply_path == "run_play":
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
            else:
                outcome = game._apply_play_result(
                    PlayType.SHORT_PASS, DefenseType.STANDARD, result,
                    game.state.field_position_str(), game.state.down, 5,
                    game.state.yards_to_go, False, False,
                )
            turnover, touchdown, safety = outcome.turnover, outcome.touchdown, outcome.safety
            assert outcome.yards_gained == 0
            assert "SAFETY" in outcome.description

    assert (turnover, touchdown, safety) == (False, False, True)
    dice.assert_not_called()
    assert game.state.is_home_possession is offense_home
    assert game.state.ball_position == 20
    assert (game.state.home_score, game.state.away_score) == (
        (0, 2) if offense_home else (2, 0)
    )
    assert len(game.state.scoring_plays) == 1
    assert game.state.scoring_plays[0].team == defending_team
    assert game.state.scoring_plays[0].points == 2
    assert offense_stats.interceptions_thrown == offense_stats.turnovers == 0
    assert result.turnover is False
    assert result.scoring_team == defending_team
    assert result.int_return_yards == result.int_return_dice == 0


@pytest.mark.parametrize("raw_spot", [-9, -1, 0])
@pytest.mark.parametrize("offense_home", [True, False])
def test_catch_within_offense_end_zone_is_defensive_touchdown(
    raw_spot: int, offense_home: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    result = PlayResult(
        result_type=ResultType.INTERCEPTION, yards=raw_spot - 5,
        turnover=True, raw_result=f"INT {raw_spot - 5}",
    )
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        flags = game._handle_interception(result, 5, result.yards)
    assert flags == (True, True, False)
    assert game.state.is_home_possession is not offense_home
    assert (game.state.home_score, game.state.away_score) == (
        (0, 6) if offense_home else (6, 0)
    )
    dice.assert_not_called()


@pytest.mark.parametrize("raw_spot", [100, 105, 109, 110, 115])
@pytest.mark.parametrize("offense_home", [True, False])
def test_defense_end_zone_automatic_touchback_control(
    raw_spot: int, offense_home: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    result = PlayResult(
        result_type=ResultType.INTERCEPTION, yards=raw_spot - 90,
        turnover=True, raw_result=f"INT {raw_spot - 90}",
    )
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        flags = game._handle_interception(result, 90, result.yards)
    assert flags == (True, False, False)
    assert game.state.ball_position == 20
    assert game.state.is_home_possession is not offense_home
    assert (game.state.home_score, game.state.away_score) == (0, 0)
    dice.assert_not_called()


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("retained", [True, False])
def test_interception_depth_remains_catch_geometry_not_offensive_gain(
    offense_home: bool, retained: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    game.state.ball_position = 40
    game.state.defense_team.special_teams.interception_return = {10: "0"}
    result = PlayResult(
        result_type=ResultType.INTERCEPTION, yards=7, turnover=True,
        raw_result="INT 7", dice_roll=10,
    )
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.roll_chart_dice", return_value=(10, "test roll")),
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        if retained:
            outcome = game._apply_play_result(
                PlayType.SHORT_PASS, DefenseType.STANDARD, result,
                game.state.field_position_str(), game.state.down, 40,
                game.state.yards_to_go, False, False,
            )
        else:
            outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert outcome.yards_gained == 0
    assert outcome.turnover is True
    assert result.yards == 7
    assert result.int_spot == game.state.ball_position == 53

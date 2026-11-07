"""Rule VI-12-F own-end-zone INT choices use public charts and synthetic rolls."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


def game_for_return(offense_home: bool, attempt: bool = True) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = offense_home
    game.state.ball_position = 90
    # Predeclare the receiving team's choice before the play or any return dice.
    setattr(game, "away_end_zone_interception_return" if offense_home else
            "home_end_zone_interception_return", attempt)
    return game


def interception(raw_spot: int) -> PlayResult:
    return PlayResult(result_type=ResultType.INTERCEPTION, yards=raw_spot - 90,
                      turnover=True, raw_result=f"INT {raw_spot - 90}", dice_roll=10)


def execute(game: PaydirtGameEngine, result: PlayResult, path: str) -> tuple[bool, bool, bool]:
    if path == "handler":
        return game._handle_interception(result, 90, result.yards)
    if path == "run_play":
        outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
    else:
        outcome = game._apply_play_result(
            PlayType.SHORT_PASS, DefenseType.STANDARD, result,
            game.state.field_position_str(), game.state.down, 90,
            game.state.yards_to_go, False, False)
    assert outcome.yards_gained == 0
    return outcome.turnover, outcome.touchdown, outcome.safety


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("path", ["handler", "run_play", "retained_play"])
@pytest.mark.parametrize("raw_spot,start", [(100, 0), (101, -1), (104, -4), (109, -9), (110, -9), (115, -9)])
def test_opted_return_counts_depth_and_caps_catch_at_nine_deep(offense_home: bool, path: str,
                                                             raw_spot: int, start: int) -> None:
    game = game_for_return(offense_home)
    result = interception(raw_spot)
    game.state.defense_team.special_teams.interception_return = {26: "15"}
    with (patch("paydirt.game_engine.resolve_play", return_value=result),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        assert execute(game, result, path) == (True, False, False)
    dice.assert_called_once()
    assert game.state.is_home_possession is not offense_home
    assert result.int_spot == start
    assert result.int_return_yards == 15
    assert game.state.ball_position == start + 15
    assert game.state.home_score == game.state.away_score == 0
    assert game.state.away_stats.interceptions_thrown + game.state.home_stats.interceptions_thrown == 1


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("gain", ["-2", "0", "4"])
def test_attempt_not_crossing_goal_line_is_touchback(offense_home: bool, gain: str) -> None:
    game = game_for_return(offense_home)
    game.state.defense_team.special_teams.interception_return = {26: gain}
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice:
        assert execute(game, result, "handler") == (True, False, False)
    dice.assert_called_once()
    assert game.state.ball_position == 20
    assert result.int_spot == -4
    assert result.int_return_dice == 26
    assert "TOUCHBACK" in result.description


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("raw_spot,cell", [(100, "100"), (104, "104"), (110, "109"), (115, "TD")])
def test_attempt_touchdown_counts_full_end_zone_distance(offense_home: bool, raw_spot: int, cell: str) -> None:
    game = game_for_return(offense_home)
    game.state.defense_team.special_teams.interception_return = {26: cell}
    result = interception(raw_spot)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")):
        assert execute(game, result, "handler") == (True, True, False)
    assert (game.state.home_score, game.state.away_score) == ((0, 6) if offense_home else (6, 0))
    assert result.int_return_yards == 100 - result.int_spot


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("raw_spot", [100, 104, 109, 110, 115])
def test_touchback_election_preserves_no_roll_control(offense_home: bool, raw_spot: int) -> None:
    game = game_for_return(offense_home, attempt=False)
    # The OTHER team's preference cannot control this interception.
    setattr(game, "home_end_zone_interception_return" if offense_home else
            "away_end_zone_interception_return", True)
    result = interception(raw_spot)
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        assert execute(game, result, "handler") == (True, False, False)
    dice.assert_not_called()
    assert game.state.ball_position == 20
    assert result.int_return_yards == result.int_return_dice == 0


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("gain,recovery,position,turnover,touchdown", [
    (12, 10, 8, True, False), (12, 30, 92, False, False),
    (2, 10, 20, True, False), (2, 30, 97, False, True),
])
def test_attempt_resolves_fumble_recovery_and_possession(offense_home: bool, gain: int, recovery: int,
                                                        position: int, turnover: bool, touchdown: bool) -> None:
    game = game_for_return(offense_home)
    returner = game.state.defense_team
    returner.peripheral.fumble_recovered_range = (10, 29)
    returner.special_teams.interception_return = {26: f"F + {gain}"}
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "return"), (recovery, "recovery")]) as dice:
        assert execute(game, result, "handler") == (turnover, touchdown, False)
    assert dice.call_count == 2
    assert game.state.ball_position == position
    assert game.state.is_home_possession is (not offense_home if turnover else offense_home)
    assert game.state.offense_stats.interceptions_thrown == (0 if turnover else 1)
    assert (game.state.home_score + game.state.away_score) == (6 if touchdown else 0)


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("gain", [-6, -7])
def test_return_fumble_on_or_behind_own_end_line_is_safety_without_recovery(offense_home: bool, gain: int) -> None:
    game = game_for_return(offense_home)
    game.state.defense_team.special_teams.interception_return = {26: f"F - {abs(gain)}"}
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice:
        assert execute(game, result, "handler") == (True, False, True)
    dice.assert_called_once()
    assert game.state.is_home_possession is not offense_home
    assert game.state.ball_position == 20
    assert (game.state.home_score, game.state.away_score) == ((2, 0) if offense_home else (0, 2))
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("foul,final", [("DEF 5", 13), ("OFF 5", 4)])
def test_attempt_foul_reroll_counts_depth_before_enforcement(offense_home: bool, foul: str, final: int) -> None:
    game = game_for_return(offense_home)
    game.state.defense_team.special_teams.interception_return = {26: foul, 27: "12"}
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "foul"), (27, "return")]):
        assert execute(game, result, "handler") == (True, False, False)
    assert game.state.ball_position == final
    assert game.state.home_stats.penalties + game.state.away_stats.penalties == 1


@pytest.mark.parametrize("offense_home", [True, False])
def test_attempt_offsetting_fouls_nullify_interception(offense_home: bool) -> None:
    game = game_for_return(offense_home)
    game.state.defense_team.special_teams.interception_return = {26: "OFF 5", 27: "DEF 5"}
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "foul"), (27, "foul")]):
        assert execute(game, result, "handler") == (False, False, False)
    assert result.replay_down
    assert game.state.is_home_possession is offense_home
    assert game.state.ball_position == 90
    assert game.state.home_stats.interceptions_thrown == game.state.away_stats.interceptions_thrown == 0


@pytest.mark.parametrize("offense_home", [True, False])
def test_attempt_reuses_saved_return_without_reroll(offense_home: bool) -> None:
    game = game_for_return(offense_home)
    result = interception(104)
    result.int_return_yards, result.int_return_dice, result.int_spot = 15, 26, -4
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        assert execute(game, result, "handler") == (True, False, False)
    dice.assert_not_called()
    assert game.state.ball_position == 11


@pytest.mark.parametrize("home,away", [(True, False), (False, True), (True, True)])
def test_core_save_restores_predeclared_team_policies(tmp_path: Path, home: bool, away: bool) -> None:
    game = make_sample_game()
    game.home_end_zone_interception_return, game.away_end_zone_interception_return = home, away
    path = tmp_path / "save.json"
    save_game(game, str(path))
    saved = json.loads(path.read_text())
    assert saved["home_end_zone_interception_return"] is home
    assert saved["away_end_zone_interception_return"] is away
    loaded = load_game(str(path))[0]
    assert loaded.home_end_zone_interception_return is home
    assert loaded.away_end_zone_interception_return is away


def test_legacy_core_save_defaults_to_touchbacks(tmp_path: Path) -> None:
    game = make_sample_game()
    path = tmp_path / "save.json"
    save_game(game, str(path))
    data = json.loads(path.read_text())
    for key in ("home_end_zone_interception_return", "away_end_zone_interception_return"):
        data.pop(key, None)
    path.write_text(json.dumps(data))
    loaded = load_game(str(path))[0]
    assert getattr(loaded, "home_end_zone_interception_return", False) is False
    assert getattr(loaded, "away_end_zone_interception_return", False) is False


@pytest.mark.parametrize("returning_home", [True, False])
@pytest.mark.parametrize("gain", [-6, -7])
def test_chain_end_line_fumble_is_out_of_play_before_recovery(returning_home: bool, gain: int) -> None:
    game = make_sample_game()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice:
        chain = game._resolve_return_chain(
            returning_home, -4, {26: f"F - {abs(gain)}"}, "Ret",
            end_rule=lambda yards: game._handle_end_zone_return(4, yards))
    dice.assert_called_once()
    assert chain.spot == 0
    assert chain.possession_home is returning_home
    assert not chain.touchback
    assert chain.fumbles_lost == []


@pytest.mark.parametrize("returning_home", [True, False])
def test_chain_live_end_zone_fumble_retains_recovery_control(returning_home: bool) -> None:
    game = make_sample_game()
    chart = game.state.home_chart if returning_home else game.state.away_chart
    chart.peripheral.fumble_recovered_range = (10, 29)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "return"), (10, "recovery")]) as dice:
        chain = game._resolve_return_chain(
            returning_home, -4, {26: "F - 5"}, "Ret",
            end_rule=lambda yards: game._handle_end_zone_return(4, yards))
    assert dice.call_count == 2
    assert chain.touchback
    assert chain.spot == 20
    assert chain.possession_home is returning_home


@pytest.mark.parametrize("home", [True, False])
def test_policy_setter_changes_only_selected_team(home: bool) -> None:
    game = make_sample_game()
    game.set_end_zone_interception_return(home, True)
    assert game.home_end_zone_interception_return is home
    assert game.away_end_zone_interception_return is not home


@pytest.mark.parametrize("home,attempt", [(1, True), (True, "yes"), (None, False)])
def test_policy_setter_rejects_non_boolean_values(home: object, attempt: object) -> None:
    game = make_sample_game()
    with pytest.raises(ValueError, match="boolean"):
        game.set_end_zone_interception_return(home, attempt)


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("foul,final", [("OFF 5", 15), ("DEF 5", 25)])
def test_attempt_foul_on_failed_escape_uses_touchback_spot(offense_home: bool, foul: str, final: int) -> None:
    game = game_for_return(offense_home)
    game.state.defense_team.special_teams.interception_return = {26: foul, 27: "4"}
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "foul"), (27, "return")]):
        assert execute(game, result, "handler") == (True, False, False)
    assert game.state.ball_position == final
    assert game.state.home_stats.penalties + game.state.away_stats.penalties == 1


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("path", ["handler", "retained_play"])
@pytest.mark.parametrize("gain", [-2, 0, 4])
def test_cached_failed_escape_is_touchback_without_new_dice(offense_home: bool, path: str, gain: int) -> None:
    game = game_for_return(offense_home)
    result = interception(104)
    result.int_return_yards, result.int_return_dice, result.int_spot = gain, 26, -4
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("cached return rerolled")) as dice:
        assert execute(game, result, path) == (True, False, False)
    dice.assert_not_called()
    assert game.state.ball_position == 20
    assert result.int_return_yards == gain
    assert result.int_return_dice == 26
    assert "TOUCHBACK" in result.description


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("path", ["handler", "retained_play"])
@pytest.mark.parametrize("cells,rolls", [
    ({26: "F + 12"}, [26, 30]),
    ({26: "F + 2"}, [26, 30]),
    ({26: "OFF 5", 27: "12"}, [26, 27]),
    ({26: "DEF 5", 27: "F + 12"}, [26, 27, 30]),
])
def test_cached_chain_preserves_recovery_and_fouls(offense_home: bool, path: str,
                                                   cells: dict[int, str], rolls: list[int]) -> None:
    from dataclasses import asdict

    first = game_for_return(offense_home)
    first.state.defense_team.peripheral.fumble_recovered_range = (10, 29)
    first.state.defense_team.special_teams.interception_return = cells
    result = interception(104)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(roll, "synthetic") for roll in rolls]):
        expected_flags = execute(first, result, "handler")
    replay = game_for_return(offense_home)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("resolved chain rerolled")) as dice:
        assert execute(replay, result, path) == expected_flags
    dice.assert_not_called()
    for field in ("ball_position", "is_home_possession", "home_score", "away_score"):
        assert getattr(replay.state, field) == getattr(first.state, field)
    for field in ("home_stats", "away_stats"):
        # Retained scrimmage paths also record pass attempts; compare chain accounting.
        actual, expected = asdict(getattr(replay.state, field)), asdict(getattr(first.state, field))
        for counter in ("turnovers", "interceptions_thrown", "fumbles_lost", "penalties", "penalty_yards"):
            assert actual[counter] == expected[counter]


@pytest.mark.parametrize("offense_home", [True, False])
@pytest.mark.parametrize("cell", ["F + 12", "OFF 5"])
def test_resolved_return_core_save_and_rollback_reapply(tmp_path: Path, offense_home: bool, cell: str) -> None:
    from copy import deepcopy
    from dataclasses import asdict

    game = game_for_return(offense_home)
    game.state.defense_team.peripheral.fumble_recovered_range = (10, 29)
    game.state.defense_team.special_teams.interception_return = {26: cell, 27: "12"}
    result = interception(104)
    before = deepcopy(game.state)
    rolls = [26, 30] if cell.startswith("F") else [26, 27]
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(roll, "synthetic") for roll in rolls]):
        flags = execute(game, result, "handler")
    chain = result.int_return_chain
    assert chain is not None
    retained_chain = deepcopy(asdict(chain))
    expected = deepcopy(game.state)
    for _ in range(2):
        game.state = deepcopy(before)
        with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("resolved chain rerolled")):
            assert execute(game, result, "retained_play") == flags
        assert result.int_return_chain is chain
        assert asdict(chain) == retained_chain
        assert result.description.count(" | ".join(chain.trace)) == 1
        for field in ("home_stats", "away_stats"):
            actual, wanted = asdict(getattr(game.state, field)), asdict(getattr(expected, field))
            for counter in ("turnovers", "interceptions_thrown", "fumbles_lost", "penalties", "penalty_yards"):
                assert actual[counter] == wanted[counter]
    path = tmp_path / "retained.json"
    save_game(game, str(path))
    json.loads(path.read_text())  # A resolved chain must not leak non-JSON objects into saves.
    loaded = load_game(str(path))[0]
    assert loaded.state.ball_position == game.state.ball_position
    assert loaded.state.is_home_possession is game.state.is_home_possession
    assert loaded.home_end_zone_interception_return is game.home_end_zone_interception_return
    assert loaded.away_end_zone_interception_return is game.away_end_zone_interception_return
    assert asdict(loaded.state.home_stats) == asdict(game.state.home_stats)
    assert asdict(loaded.state.away_stats) == asdict(game.state.away_stats)

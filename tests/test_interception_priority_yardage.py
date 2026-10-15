"""Interception depth comes from the winning INT, not unrelated chart yardage."""

from unittest.mock import patch

import pytest

from paydirt.play_events import EventType
from paydirt.play_resolver import DefenseType, PlayType, ResultType
from paydirt.priority_chart import PriorityResult, apply_priority_chart
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("offense", ["BLACK", "", "0", "12", "-7", "B", "QT", "TD"])
@pytest.mark.parametrize("depth", [-5, 0, 13])
def test_defensive_interception_uses_defensive_depth(offense: str, depth: int) -> None:
    result = apply_priority_chart(offense, f"INT {depth}")
    assert result.is_turnover
    assert not result.is_incomplete
    assert not result.is_touchdown
    assert not result.use_qt_column
    assert not result.use_breakaway
    assert result.final_yards == depth
    assert result.priority == PriorityResult.INT


@pytest.mark.parametrize("defense", ["", "0", "12", "-7"])
@pytest.mark.parametrize("depth", [-5, 0, 13])
def test_offensive_interception_keeps_offensive_depth(defense: str, depth: int) -> None:
    result = apply_priority_chart(f"INT {depth}", defense)
    assert result.is_turnover
    assert result.final_yards == depth
    assert result.priority == PriorityResult.INT


@pytest.mark.parametrize("off_depth,def_depth,expected,priority", [
    (4, 13, 4, PriorityResult.INT),
    (13, 4, 4, PriorityResult.D_INT),
    (4, 4, 4, PriorityResult.INT),
    (-5, 4, -5, PriorityResult.INT),
    (4, -5, -5, PriorityResult.D_INT),
    (0, 13, 0, PriorityResult.INT),
    (13, 0, 0, PriorityResult.D_INT),
])
def test_two_interceptions_keep_shortest_depth(off_depth: int, def_depth: int,
                                              expected: int, priority: PriorityResult) -> None:
    result = apply_priority_chart(f"INT {off_depth}", f"INT {def_depth}")
    assert result.is_turnover
    assert result.final_yards == expected
    assert result.priority == priority


def test_defensive_black_still_cancels_offensive_interception() -> None:
    result = apply_priority_chart("INT 13", "BLACK")
    assert result.is_incomplete
    assert not result.is_turnover
    assert result.priority == PriorityResult.BLACK


@pytest.mark.parametrize("offense,defense,expected", [
    ("INT 4", "-10", 4), ("BLACK", "INT 13", 13),
    ("INT 13", "INT 4", 4), ("BLACK", "INT -5", -5),
])
def test_description_distinguishes_depth_from_return(offense: str, defense: str, expected: int) -> None:
    result = apply_priority_chart(offense, defense)
    assert result.description == f"INTERCEPTION! {expected} yards downfield"


@pytest.mark.parametrize("home_possession", [False, True], ids=["away-offense", "home-offense"])
@pytest.mark.parametrize("flow", ["direct", "procedure", "decline-penalty"])
@pytest.mark.parametrize("position,depth,return_yards,spot,final_position,touchdown,return_rolled", [
    (19, 13, 0, 68, 68, False, True),
    (19, 13, 25, 68, 93, False, True),  # Wrong zero depth would give a pick-six.
    (19, 13, 32, 68, 97, True, True),  # Return exactly reaches the goal line.
    (19, 13, 38, 68, 97, True, True),
    (86, 13, 0, 1, 1, False, True),
    (87, 13, 0, 20, 20, False, False),  # Catch on the defense's goal line.
    (88, 13, 0, 20, 20, False, False),  # Catch in the defense's end zone.
    (3, -2, 0, 99, 99, False, True),
    (3, -3, 0, 100, 97, True, False),  # Catch on the offense's goal line.
    (3, -4, 0, 100, 97, True, False),
])
def test_real_engine_uses_defensive_interception_depth(
    home_possession: bool, flow: str, position: int, depth: int, return_yards: int,
    spot: int, final_position: int, touchdown: bool, return_rolled: bool,
) -> None:
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home_possession
    state.ball_position = position
    state.possession_team.offense.medium_pass[16] = "BLACK"
    state.possession_team.offense.medium_pass[14] = "OFF 5"
    state.defense_team.defense.modifiers.setdefault(("A", 1), {})[7] = f"INT {depth}"
    state.defense_team.special_teams.interception_return[22] = str(return_yards)
    offense_stats = state.offense_stats
    rolls = [(16, "B1+W3+W3=16")]
    if flow == "decline-penalty":
        rolls.insert(0, (14, "B1+W2+W2=14"))

    with (
        patch("paydirt.play_resolver.random.choice", side_effect=lambda choices: choices[0]),
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls) as offense_roll,
        patch("paydirt.game_engine.roll_chart_dice", return_value=(22, "B2+W1+W1=22")) as return_roll,
    ):
        if flow == "direct":
            outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
        else:
            outcome = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
            if flow == "decline-penalty":
                assert outcome.pending_penalty_decision
                assert state.is_home_possession is home_possession
                assert state.ball_position == position
                assert offense_stats.interceptions_thrown == 0
                assert return_roll.call_count == 0
                outcome = game.apply_penalty_decision(outcome, accept_play=True)

    assert offense_roll.call_count == len(rolls)
    assert return_roll.call_count == int(return_rolled)
    assert outcome.result.result_type == ResultType.INTERCEPTION
    assert outcome.result.yards == depth
    assert outcome.result.int_spot == spot
    assert outcome.result.int_return_yards == (return_yards if return_rolled else 0)
    assert outcome.turnover
    assert outcome.touchdown is touchdown
    assert not outcome.safety
    assert state.is_home_possession is not home_possession
    assert state.ball_position == final_position
    assert state.home_score == (6 if touchdown and not home_possession else 0)
    assert state.away_score == (6 if touchdown and home_possession else 0)
    assert offense_stats.interceptions_thrown == 1
    assert offense_stats.passing_yards == 0
    assert offense_stats.total_yards == 0
    if flow != "direct" and return_rolled:
        interceptions = outcome.transaction.get_events_by_type(EventType.INTERCEPTION)
        returns = outcome.transaction.get_events_by_type(EventType.INT_RETURN)
        assert len(interceptions) == len(returns) == 1
        assert interceptions[0].spot == spot
        assert returns[0].yards == return_yards

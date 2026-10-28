"""End-zone fumbles on returns retain the raw spot until recovery is resolved."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType
from tests.game_fixtures import make_sample_game
from tests.test_kickoff_return_penalties import kick, kick_game
from tests.test_return_chart_rules import fumble, game_with_return_chart, interception


@pytest.mark.parametrize("returning_home", [False, True])
@pytest.mark.parametrize("recovery", [17, 20, 30, 37])
@pytest.mark.parametrize("kind", ["kickoff", "interception", "advance"])
@pytest.mark.parametrize("end", [-6, 0, 100, 105, 110])
def test_end_zone_recovery_uses_unclamped_spot(
    returning_home: bool, recovery: int, kind: str, end: int,
) -> None:
    game = make_sample_game()
    start = 3
    yards = end - start
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = (10, 27)
        chart.special_teams.interception_return.clear()
    end_rule = None
    if kind == "kickoff":
        end_rule = lambda advance: game._kickoff_return_spot(start, advance)
    elif kind == "interception":
        end_rule = lambda advance: (20, True) if start + advance <= 0 else (min(100, start + advance), False)
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(recovery, "Recovery")) as dice,
        patch("paydirt.game_engine.roll_white_dice", return_value=(7, "W3+W4=7")) as white,
    ):
        chain = game._resolve_return_chain(
            returning_home, start, {13: f"F {yards:+d}"}, "Ret",
            first=(13, f"F {yards:+d}"), end_rule=end_rule,
        )
    recovered = recovery < 28
    touchback = (end >= 100 and not recovered) or (end <= 0 and recovered and kind == "interception")
    expected_spot = 20 if touchback else (100 if recovered else 20) if end >= 100 else 0 if recovered else 100
    assert chain.possession_home == (returning_home if recovered else not returning_home)
    assert chain.spot == expected_spot
    assert chain.touchback is touchback
    assert chain.fumbled
    assert chain.fumbles_lost == ([] if recovered else [returning_home])
    assert f'R:{recovery}→"{"recovered" if recovered else "lost"}"' in chain.trace
    assert "end zone" in " ".join(chain.notes).lower()
    assert dice.call_count == 1, "end-zone recoveries do not start another return"
    assert white.call_count == (1 if end >= 110 else 0)
    if end >= 110:
        assert "W3+W4=7" in " ".join(chain.trace)
    touchdown = game._apply_return_chain(chain)
    assert touchdown is (expected_spot == 100)
    safety = expected_spot == 0
    scorer_home = not chain.possession_home if safety else chain.possession_home
    points = 2 if safety else 6 if touchdown else 0
    assert (game.state.home_score, game.state.away_score) == (points if scorer_home else 0, 0 if scorer_home else points)
    returner_stats = game.state.home_stats if returning_home else game.state.away_stats
    assert returner_stats.fumbles_lost == (0 if recovered else 1)
    assert returner_stats.turnovers == (0 if recovered else 1)


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("recovery", [17, 20, 30, 37])
def test_kickoff_fumble_before_leaving_end_zone(kicking_home: bool, recovery: int) -> None:
    game, kicker, receiver = kick_game(kicking_home)
    kicker.kickoff[24] = "74"  # Caught nine yards deep.
    receiver.kickoff_return[13] = "F + 3"
    outcome = kick(game, kicking_home, 24, 13, recovery)
    recovered = recovery < 28
    assert game.state.is_home_possession == (not kicking_home if recovered else kicking_home)
    assert outcome.touchdown is (not recovered)
    assert not outcome.safety
    assert outcome.turnover is (not recovered)
    if recovered:
        assert game.state.ball_position == 20
        assert "touchback" in outcome.description.lower()
    else:
        assert (game.state.home_score if kicking_home else game.state.away_score) == 6
    assert f"R:{recovery}" in outcome.description
    assert "end zone" in outcome.description.lower()


def run_scrimmage(
    game: PaydirtGameEngine, result: PlayResult, penalty_procedure: bool, *rolls: int,
) -> PlayOutcome:
    run_play = game.run_play_with_penalty_procedure if penalty_procedure else game.run_play
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(roll, f"Roll {roll}") for roll in rolls]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert dice.call_count == len(rolls)
    return outcome


@pytest.mark.parametrize("penalty_procedure", [False, True])
@pytest.mark.parametrize("recovery", [20, 30])
def test_interception_fumble_momentum_into_own_end_zone(penalty_procedure: bool, recovery: int) -> None:
    game = game_with_return_chart({13: "F -5"}, returning_home=False)
    game.state.ball_position = 90  # INT +7 at the defender's three.
    outcome = run_scrimmage(game, interception(), penalty_procedure, 13, recovery)
    assert outcome.touchdown is (recovery == 30)
    assert not outcome.safety
    assert game.state.is_home_possession is (recovery == 30)
    if recovery == 20:
        assert game.state.ball_position == 20
        assert "touchback" in outcome.description.lower()
    else:
        assert game.state.home_score == 6
    assert f"R:{recovery}" in outcome.description


@pytest.mark.parametrize("penalty_procedure", [False, True])
@pytest.mark.parametrize("recovery", [20, 30])
def test_own_fumble_advance_fumbles_back_into_own_end_zone(penalty_procedure: bool, recovery: int) -> None:
    game = game_with_return_chart({13: "F -5"}, returning_home=True)
    game.state.ball_position = 1
    outcome = run_scrimmage(game, fumble(2), penalty_procedure, 17, 13, recovery)
    assert outcome.safety is (recovery == 20)
    assert outcome.touchdown is (recovery == 30)
    assert game.state.is_home_possession is (recovery == 20)
    assert game.state.away_score == (2 if recovery == 20 else 6)
    assert f"R:{recovery}" in outcome.description


@pytest.mark.parametrize("recovery", [20, 30])
def test_field_recovery_control(recovery: int) -> None:
    game = make_sample_game()
    game.state.home_chart.peripheral.fumble_recovered_range = (10, 27)
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(recovery, "Recovery")):
        chain = game._resolve_return_chain(True, 40, {13: "F + 3"}, "Ret", first=(13, "F + 3"))
    assert chain.spot == (43 if recovery == 20 else 57)
    assert not chain.touchback
    assert not chain.touchdown


@pytest.mark.parametrize("penalty_procedure", [False, True])
@pytest.mark.parametrize("recovery", [20, 30])
def test_own_advance_fumbles_in_opponent_end_zone(penalty_procedure: bool, recovery: int) -> None:
    game = game_with_return_chart({13: "F + 5"}, returning_home=True)
    game.state.ball_position = 95
    outcome = run_scrimmage(game, fumble(2), penalty_procedure, 17, 13, recovery)
    assert outcome.touchdown is (recovery == 20)
    assert not outcome.safety
    assert game.state.home_score == (6 if recovery == 20 else 0)
    assert game.state.is_home_possession is (recovery == 20)
    if recovery == 30:
        assert game.state.ball_position == 20
        assert game.state.home_stats.fumbles_lost == 1
    assert "end zone" in outcome.description.lower()
    assert f"R:{recovery}" in outcome.description


@pytest.mark.parametrize("penalty_procedure", [False, True])
def test_nested_fumble_return_touchback_survives_chain_merge(penalty_procedure: bool) -> None:
    game = game_with_return_chart({13: "F + 5"}, returning_home=True)
    game.state.away_chart.special_teams.interception_return[14] = "F + 99"
    game.state.away_chart.peripheral.fumble_recovered_range = (10, 27)
    game.state.ball_position = 40
    # HOME loses the advance at its 47; AWAY fumbles into HOME's end zone.
    with patch("paydirt.game_engine.roll_white_dice", return_value=(7, "W3+W4=7")):
        outcome = run_scrimmage(game, fumble(2), penalty_procedure, 17, 13, 37, 14, 30)
    assert not outcome.touchdown
    assert not outcome.safety
    assert game.state.is_home_possession
    assert game.state.ball_position == 20
    assert "TOUCHBACK" in outcome.description
    assert "W3+W4=7" in outcome.description
    assert game.state.home_stats.fumbles_lost == 1
    assert game.state.away_stats.fumbles_lost == 1


@pytest.mark.parametrize("penalty_procedure", [False, True])
def test_nested_fumble_return_safety_is_reported(penalty_procedure: bool) -> None:
    game = game_with_return_chart({13: "F + 5"}, returning_home=True)
    game.state.away_chart.special_teams.interception_return[14] = "F - 60"
    game.state.away_chart.peripheral.fumble_recovered_range = (10, 27)
    game.state.ball_position = 40
    outcome = run_scrimmage(game, fumble(2), penalty_procedure, 17, 13, 37, 14, 20)
    assert outcome.safety
    assert not outcome.touchdown
    assert not game.state.is_home_possession
    assert game.state.home_score == 2
    assert game.state.away_score == 0
    assert game.state.ball_position == 20
    assert "SAFETY" in outcome.description


@pytest.mark.parametrize("kind,recovery", [("punt", 17), ("punt", 37), ("field_goal", 17), ("field_goal", 37), ("snap", 37)])
def test_blocked_kick_return_fumble_safety_propagates_to_outcome(kind: str, recovery: int) -> None:
    from tests.test_field_goal import create_fg_result

    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 50
    game.state.down = 4
    game.state.yards_to_go = 10
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = (10, 27)
        chart.special_teams.interception_return[13] = "F - 100"
    fg_result = create_fg_result(24, "F - 8" if kind == "snap" else "BK -8", is_blocked=kind != "snap")
    game.state.home_chart.special_teams.punt[24] = "BK -8"
    rolls = [recovery, 13, 20] if kind != "punt" else [24, recovery, 13, 20]
    with (
        patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=fg_result),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(roll, f"Roll {roll}") for roll in rolls]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.run_play(PlayType.PUNT if kind == "punt" else PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert dice.call_count == len(rolls)
    assert outcome.safety
    assert not outcome.touchdown
    assert game.state.is_home_possession is (recovery == 17)
    assert game.state.ball_position == 20
    assert (game.state.home_score, game.state.away_score) == ((0, 2) if recovery == 17 else (2, 0))
    assert "SAFETY" in outcome.description
    assert "TURNOVER ON DOWNS" not in outcome.description

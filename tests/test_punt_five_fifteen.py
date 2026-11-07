"""The existing five-versus-fifteen punt policy uses actual teams and catch spots."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def make_punt(home: bool, kick: str, returned_foul: str, returned: str) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 20, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.possession_team.special_teams.punt = {10: kick, 11: "40"}
    game.state.defense_team.special_teams.punt_return = {12: returned_foul, 13: returned}
    for team in (game.state.home_chart, game.state.away_chart):
        team.peripheral.fumble_recovered_range = (10, 31)
        team.special_teams.interception_return = {14: "4"}
    return game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("kick,returned_foul", [("OFF 5", "OFF 15"), ("OFF 15", "OFF 5")])
@pytest.mark.parametrize("position,punt_yards,catch", [(20, 40, 40), (50, 40, 10), (10, 10, 80)])
@pytest.mark.parametrize("returned,recovery", [("3", []), ("TD", []), ("F + 3", [20]),
                                           ("F + 3", [35]), ("F + 3", [37, 14])])
def test_legacy_exception_assesses_one_actual_team_from_the_catch(
    home: bool, procedure: bool, kick: str, returned_foul: str,
    position: int, punt_yards: int, catch: int, returned: str, recovery: list[int],
) -> None:
    game = make_punt(home, kick, returned_foul, returned)
    game.state.ball_position = position
    game.state.possession_team.special_teams.punt[11] = str(punt_yards)
    dice = [10, 11, 12, 13, *recovery]
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = run(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == len(dice)
    assert not outcome.pending_penalty_decision
    assert not outcome.result.replay_down
    assert game.state.is_home_possession is not home
    # Preserve this existing policy: disregard the five, cancel the return,
    # and assess the fifteen at the catch, in the receiver's coordinate frame.
    receiver_foul = returned_foul == "OFF 15"
    distance = catch if receiver_foul else 100 - catch
    effective = 15 if 30 <= distance else distance // 2
    expected = catch - effective if receiver_foul else catch + effective
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (expected, 1, 10)
    fouling_home = not home if receiver_foul else home
    fouler = game.state.home_stats if fouling_home else game.state.away_stats
    other = game.state.away_stats if fouling_home else game.state.home_stats
    assert (fouler.penalties, fouler.penalty_yards, other.penalties, other.penalty_yards) == (1, effective, 0, 0)
    assert outcome.penalty_applied
    assert not outcome.touchdown and not outcome.safety and not outcome.turnover
    assert not outcome.first_down
    assert game.state.home_score == game.state.away_score == 0
    assert not game.state.scoring_plays
    for stats in (game.state.home_stats, game.state.away_stats):
        assert stats.first_downs == stats.fumbles_lost == stats.turnovers == 0
        assert stats.rushing_yards == stats.passing_yards == stats.total_yards == stats.sacks == 0
    assert outcome.result.result_type == ResultType.PENALTY_OFFENSE
    assert not outcome.result.fumble_resolved
    assert outcome.result.raw_result == kick
    assert outcome.result.dice_roll == 10
    assert outcome.result.punt_return_dice == 12
    assert outcome.result.punt_return_result == returned_foul
    assert "5-yard penalty is disregarded" in outcome.description
    assert "return canceled" in outcome.description.lower()
    assert game.state.possession_team.peripheral.short_name in outcome.description
    assert game.play_log == [outcome]
    assert outcome.clock_trace.requested_seconds == 8
    assert outcome.clock_trace.charged_seconds == pytest.approx(8)
    assert game.state.time_remaining == pytest.approx(10 - 8 / 60)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("kick,returned_foul", [("OFF 5", "OFF 15"), ("OFF 15", "OFF 5")])
@pytest.mark.parametrize("quarter", [2, 4])
def test_legacy_exception_extension_depends_on_actual_fifteen_yard_fouler(
    home: bool, kick: str, returned_foul: str, quarter: int,
) -> None:
    game = make_punt(home, kick, returned_foul, "3")
    game.state.quarter, game.state.time_remaining = quarter, 3 / 60
    game.state.home_score = 7
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 12, 13]]),
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    defensive_foul = kick == "OFF 15"
    assert outcome.penalty_applied
    assert game.state.untimed_down_pending is defensive_foul
    assert game.state.is_home_possession is not home
    if defensive_foul:
        assert game.state.quarter == quarter
        assert game.state.time_remaining == 0
        assert not game.state.game_over
        assert "UNTIMED DOWN" in outcome.description.upper()
        assert not outcome.clock_trace.period_ended
    elif quarter == 2:
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15
        assert outcome.clock_trace.period_ended
    else:
        assert game.state.game_over
        assert outcome.clock_trace.period_ended


@pytest.mark.parametrize("kick,returned_foul", [("DEF 15", "DEF 5"), ("OFF 5", "OFF 15")])
def test_automatic_first_down_and_ordinary_return_controls(kick: str, returned_foul: str) -> None:
    # DEF 15 carries an automatic first down, so its opposite-team pair offsets.
    # A receiver's OFF 15 alone remains ordinary return enforcement at the end.
    game = make_punt(True, kick, returned_foul, "3")
    if kick == "OFF 5":
        game.state.possession_team.special_teams.punt[10] = "40"
        dice = [10, 12, 13]
    else:
        dice = [10, 11, 12, 13]
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]),
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    if kick == "DEF 15":
        assert outcome.result.replay_down
        assert (game.state.is_home_possession, game.state.ball_position, game.state.down) == (True, 20, 4)
        assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
        assert outcome.clock_trace.requested_seconds == 10
    else:
        assert not game.state.is_home_possession
        assert game.state.ball_position == 28  # Catch 40 + return 3 - penalty 15.
        assert (game.state.away_stats.penalties, game.state.away_stats.penalty_yards) == (1, 15)
        assert outcome.penalty_applied


def test_gate_covers_both_actual_fifteen_yard_teams() -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    report = audit_observer_conformance()
    assert report["passed"], report["errors"]
    cases = {check["case"] for check in report["checks"]}
    assert {"PUNT/five-fifteen/receiver-catch", "PUNT/five-fifteen/kicker-catch"} <= cases


@pytest.mark.parametrize("mutation", ["coordinate", "assessment"])
def test_gate_rejects_legacy_exception_mutants(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    original = PaydirtGameEngine.run_play

    def corrupted(game: PaydirtGameEngine, *args: object, **kwargs: object) -> PlayOutcome:
        outcome = original(game, *args, **kwargs)
        if outcome.description.startswith("Legacy five-versus-fifteen"):
            if mutation == "coordinate":
                game.state.ball_position = 100 - game.state.ball_position
            else:
                game.state.home_stats.penalties = game.state.home_stats.penalty_yards = 0
                game.state.away_stats.penalties = game.state.away_stats.penalty_yards = 0
                outcome.penalty_applied = False
        return outcome

    monkeypatch.setattr(PaydirtGameEngine, "run_play", corrupted)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("PUNT/five-fifteen/" in error for error in report["errors"])

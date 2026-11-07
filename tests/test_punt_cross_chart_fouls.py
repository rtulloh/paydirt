"""Punt fouls identify the actual team and preserve one accepted assessment."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


def punt_game(home: bool, kick: str, returned: str = "3") -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.possession_team.special_teams.punt = {10: kick, 11: "40"}
    game.state.defense_team.special_teams.punt_return = {12: "DEF 15X", 13: returned}
    for team in (game.state.home_chart, game.state.away_chart):
        team.peripheral.fumble_recovered_range = (10, 31)
        team.special_teams.interception_return = {14: "4"}
    return game


def punt(game: PaydirtGameEngine, dice: list[int], procedure: bool = False) -> PlayOutcome:
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = run(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == len(dice)
    return outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("kick,returned_foul", [("OFF 5", "DEF 15X"), ("DEF 5", "OFF 15")])
@pytest.mark.parametrize("recovery", [None, 20, 35, 37])
@pytest.mark.parametrize("accept", [False, True])
def test_same_team_cross_chart_fouls_offer_one_foul_without_combining(
    home: bool, procedure: bool, kick: str, returned_foul: str, recovery: int | None, accept: bool,
) -> None:
    game = punt_game(home, kick, "3" if recovery is None else "F + 3")
    game.state.defense_team.special_teams.punt_return[12] = returned_foul
    dice = [10, 11, 12, 13]
    if recovery is not None:
        dice.append(recovery)
        if recovery == 37:
            dice.append(14)
    pending = punt(game, dice, procedure)
    assert pending.pending_penalty_decision
    assert "OFFSETTING" not in pending.description
    assert "NFL Rule 14-5-1" not in pending.description
    assert pending.penalty_choice.offended_team == ("defense" if kick.startswith("OFF") else "offense")
    assert not any("KEEP" in option.raw_result for option in pending.penalty_choice.penalty_options)
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (40, 4, 8)
    assert game.state.time_remaining == 10
    assert not game.play_log
    with (patch("paydirt.game_engine.roll_chart_dice") as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.apply_punt_penalty_decision(pending, accept)
    rolls.assert_not_called()
    assert not outcome.pending_penalty_decision
    assert not hasattr(game, "_pending_punt_state")
    assert game.play_log == [outcome]
    assert game.state.time_remaining == pytest.approx(10 - 8 / 60)
    fouling_home = home if kick.startswith("OFF") else not home
    fouler = game.state.home_stats if fouling_home else game.state.away_stats
    other = game.state.away_stats if fouling_home else game.state.home_stats
    recovery_stands = not accept and kick.startswith("DEF") and recovery in (35, 37)
    assert fouler.penalties == (0 if recovery_stands else 1)
    assert other.penalties == 0
    assert game.state.home_stats.first_downs == game.state.away_stats.first_downs == 0
    if accept:
        assert game.state.is_home_possession is home
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (
            (35, 4, 13) if kick.startswith("OFF") else (45, 4, 3)
        )
        assert fouler.penalty_yards == 5
        assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
        assert not outcome.first_down
    else:
        # The independently resolved return is a passing control for nested recoveries.
        control = punt_game(home, "40", "3" if recovery is None else "F + 3")
        control.state.defense_team.special_teams.punt_return[12] = returned_foul
        punt(control, [10, *dice[2:]], procedure)
        assert game.state.is_home_possession is control.state.is_home_possession
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (
            control.state.ball_position, control.state.down, control.state.yards_to_go
        )
        assert game.state.home_stats == control.state.home_stats
        assert game.state.away_stats == control.state.away_stats
        assert fouler.penalty_yards == (0 if recovery_stands else 15 if kick.startswith("OFF") else 11)
        if recovery is None:
            assert game.state.ball_position == (38 if kick.startswith("OFF") else 12)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("quarter", [2, 4])
@pytest.mark.parametrize("seconds", [600, 3])
@pytest.mark.parametrize("source", ["kick", "cross-def", "cross-off"])
def test_real_punt_offsets_replay_once_with_clock_and_period_extension(
    home: bool, procedure: bool, quarter: int, seconds: int, source: str,
) -> None:
    game = punt_game(home, "DEF 5" if source == "cross-def" else "OFF 5")
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    if source == "kick":
        game.state.possession_team.special_teams.punt[11] = "DEF 15X"
        dice = [10, 11]
    else:
        game.state.defense_team.special_teams.punt_return[12] = (
            "DEF 15X" if source == "cross-def" else "OFF 10"
        )
        dice = [10, 11, 12, 13]
    outcome = punt(game, dice, procedure)
    assert not outcome.pending_penalty_decision
    assert outcome.result.replay_down
    assert not outcome.first_down and not outcome.turnover and not outcome.touchdown
    assert game.state.is_home_possession is home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (40, 4, 8)
    assert game.state.quarter == quarter
    assert game.state.time_remaining == pytest.approx(max(0, seconds - 10) / 60)
    assert game.has_untimed_down() is (seconds < 10)
    assert not game.state.game_over
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.state.home_stats.first_downs == game.state.away_stats.first_downs == 0
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
    assert game.play_log == [outcome]
    assert outcome.clock_trace.requested_seconds == 10
    assert outcome.clock_trace.charged_seconds == min(seconds, 10)


def test_plain_punt_control() -> None:
    game = punt_game(True, "40")
    game.state.defense_team.special_teams.punt_return[12] = "3"
    outcome = punt(game, [10, 12])
    assert not outcome.pending_penalty_decision and not outcome.result.replay_down
    assert not game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (23, 1, 10)
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.state.time_remaining == pytest.approx(10 - 8 / 60)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("kick,returned_foul", [("OFF 5", "DEF 15X"), ("DEF 5", "OFF 15")])
def test_selected_kick_foul_has_its_own_half_expiration_rights(
    home: bool, kick: str, returned_foul: str,
) -> None:
    game = punt_game(home, kick)
    game.state.defense_team.special_teams.punt_return[12] = returned_foul
    pending = punt(game, [10, 11, 12, 13])
    assert pending.pending_penalty_decision
    game.state.time_remaining = 3 / 60
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_punt_penalty_decision(pending, True)
    defensive = kick.startswith("DEF")
    assert game.has_untimed_down() is defensive
    assert game.state.quarter == (2 if defensive else 3)
    assert not outcome.first_down
    assert game.state.home_stats.first_downs == game.state.away_stats.first_downs == 0


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("kick,returned_foul", [
    ("40", "DEF 15X"), ("OFF 5", "DEF 15X"), ("40", "OFF 15"), ("DEF 5", "OFF 15"),
])
def test_retained_return_uses_the_accepted_fouls_period_extension(
    home: bool, kick: str, returned_foul: str,
) -> None:
    game = punt_game(home, kick)
    game.state.defense_team.special_teams.punt_return[12] = returned_foul
    game.state.time_remaining = 3 / 60
    outcome = punt(game, [10, 12, 13] if kick == "40" else [10, 11, 12, 13])
    if outcome.pending_penalty_decision:
        with patch("paydirt.game_engine.random.uniform", return_value=8):
            outcome = game.apply_punt_penalty_decision(outcome, False)
    defensive = returned_foul.startswith("DEF")
    assert game.has_untimed_down() is defensive
    assert game.state.quarter == (2 if defensive else 3)
    assert game.state.is_home_possession is (not home)
    assert game.state.ball_position == (38 if defensive else 12)
    assert outcome.penalty_applied
    assert not outcome.first_down
    assert game.play_log == [outcome]


def test_gate_has_punt_fouling_team_and_offset_clock_controls() -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    report = audit_observer_conformance()
    cases = {check["case"] for check in report["checks"]}
    assert {"PUNT/same-team-fouls/one-assessment", "PUNT/opposite-team-fouls/offset-clock"} <= cases


def test_gate_rejects_punt_offsets_without_time(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    original = PaydirtGameEngine._use_time

    def erase(self: PaydirtGameEngine, seconds: float, *args: object, **kwargs: object) -> bool:
        if seconds == 10 and kwargs.get("defensive_penalty"):
            return False
        return original(self, seconds, *args, **kwargs)

    monkeypatch.setattr(PaydirtGameEngine, "_use_time", erase)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("opposite-team-fouls/offset-clock" in error for error in report["errors"])


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("recovery,spot", [(35, 77), (37, 81)])
def test_saved_return_preview_names_the_actual_fumble_recoverer(home: bool, recovery: int, spot: int) -> None:
    game = punt_game(home, "DEF 5", "F + 3")
    game.state.defense_team.special_teams.punt_return[12] = "OFF 15"
    pending = punt(game, [10, 11, 12, 13, recovery, *([14] if recovery == 37 else [])])
    kicker, receiver = ("HOME", "AWAY") if home else ("AWAY", "HOME")
    assert pending.penalty_choice.play_result_preview == f"{kicker} 1st and 10 at {receiver} {100 - spot}"


def test_gate_rejects_erased_punt_fouling_team(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    original = PaydirtGameEngine._resolve_return_chain

    def erase(self: PaydirtGameEngine, *args: object, **kwargs: object) -> object:
        chain = original(self, *args, **kwargs)
        for penalty in chain.penalties:
            penalty.fouling_home = not penalty.fouling_home
        return chain

    monkeypatch.setattr(PaydirtGameEngine, "_resolve_return_chain", erase)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("same-team-fouls/one-assessment" in error for error in report["errors"])

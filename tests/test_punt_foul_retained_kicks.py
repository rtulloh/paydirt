"""A kick-foul reroll keeps the first actual kick and consumes it only once."""

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
@pytest.mark.parametrize("cell", ["40*", "40†", "70"])
@pytest.mark.parametrize("accept", [False, True])
def test_no_return_kick_reroll_preserves_choice_markers_and_actual_roll(
    home: bool, procedure: bool, foul: str, cell: str, accept: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.possession_team.special_teams.punt = {10: foul, 11: cell}
    game.state.defense_team.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 20]]) as rolls:
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        pending = run(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 2
    assert pending.pending_penalty_decision
    assert not game.play_log and game.state.time_remaining == 10
    assert game.state.is_home_possession is home
    assert game.state.ball_position == 40
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    with (patch("paydirt.game_engine.roll_chart_dice") as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.apply_punt_penalty_decision(pending, accept)
    rolls.assert_not_called()
    assert not outcome.pending_penalty_decision
    assert game.play_log == [outcome]
    assert not hasattr(game, "_pending_punt_state")
    assert not outcome.result.punt_snap_fumble
    assert outcome.result.punt_return_dice == 0
    if accept:
        assert game.state.is_home_possession is home
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (
            (35, 4, 13) if foul.startswith("OFF") else (45, 4, 3)
        )
        assert game.state.offense_stats.penalties == int(foul.startswith("OFF"))
        assert game.state.defense_stats.penalties == int(foul.startswith("DEF"))
        assert outcome.penalty_applied and not outcome.first_down
    else:
        assert game.state.is_home_possession is (not home)
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (20, 1, 10)
        assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
        assert outcome.result.dice_roll == 11
        assert outcome.result.raw_result == cell
        assert not outcome.penalty_applied


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
@pytest.mark.parametrize("accept", [False, True])
@pytest.mark.parametrize("home", [False, True])
def test_blocked_punt_reroll_waits_for_choice_and_never_becomes_a_later_punt(
    foul: str, accept: bool, home: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.possession_team.special_teams.punt = {10: foul, 11: "BK - 8", 12: "40"}
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 31)
    game.state.defense_team.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 12, 20]]) as rolls:
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 2
    assert pending.pending_penalty_decision
    assert game.state.ball_position == 40 and not game.play_log
    assert pending.result.raw_result == "BK - 8"
    with (patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Recovery")) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.apply_punt_penalty_decision(pending, accept)
    assert rolls.call_count == (0 if accept else 1)
    assert outcome.result.punt_return_dice == 0
    assert not outcome.result.punt_snap_fumble
    assert game.play_log == [outcome]
    if accept:
        assert game.state.is_home_possession is home
        assert game.state.ball_position == (35 if foul.startswith("OFF") else 45)
    else:
        assert game.state.is_home_possession is (not home)
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (68, 1, 10)
        assert "BLOCKED PUNT" in outcome.description
        assert outcome.result.raw_result == "BK - 8"
        assert outcome.result.dice_roll == 11
        assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0


def test_plain_fair_catch_control_has_no_return() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position = 40
    game.state.home_chart.special_teams.punt = {11: "40*"}
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(11, "Kick")) as rolls:
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    rolls.assert_called_once()
    assert not game.state.is_home_possession
    assert game.state.ball_position == 20
    assert not outcome.pending_penalty_decision
    assert outcome.result.punt_return_dice == 0


@pytest.mark.parametrize("cell", ["BK -8", "BK - 8", "BK\t-\t8", "bk -8"])
def test_blocked_punt_signed_yards_do_not_depend_on_spacing(cell: str) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.home_chart.special_teams.punt = {10: cell}
    game.state.home_chart.peripheral.fumble_recovered_range = (10, 31)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Punt"), (20, "Recovery")]):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert not game.state.is_home_possession
    assert game.state.ball_position == 68
    assert outcome.yards_gained == -8


@pytest.mark.parametrize("cell", ["40*", "40†", "70"])
def test_keeping_no_return_result_with_kick_foul_preserves_the_actual_chart_lookup(cell: str) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: cell}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Foul"), (11, "Punt")]) as rolls:
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 2
    with patch("paydirt.game_engine.roll_chart_dice") as rolls:
        outcome = game.apply_punt_penalty_decision(pending, True, penalty_index=1)
    rolls.assert_not_called()
    assert not game.state.is_home_possession
    assert game.state.ball_position == 25
    assert game.state.home_stats.penalties == 1 and game.state.home_stats.penalty_yards == 5
    assert outcome.result.raw_result == cell and outcome.result.dice_roll == 11
    assert outcome.result.punt_return_dice == 0


def test_gate_covers_retained_punt_classes_and_actual_chart_lookups() -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    report = audit_observer_conformance()
    cases = {row["case"] for row in report["checks"]}
    assert {
        "PUNT/BK - 8/retained-decline", "PUNT/BK - 8/retained-accept",
        "PUNT/70/retained-decline", "PUNT/40*/retained-decline", "PUNT/40†/retained-decline",
    } <= cases


def test_gate_rejects_a_blocked_kick_replaced_by_numeric_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance
    from paydirt.game_engine import PaydirtGameEngine
    from paydirt.game_state import PlayOutcome
    from paydirt.play_resolver import PlayResult

    original = PaydirtGameEngine._pending_punt_retained_result

    def substitute(self: PaydirtGameEngine, result: PlayResult, *args: object, **kwargs: object) -> PlayOutcome:
        if result.raw_result.startswith("BK"):
            result.raw_result = "40"
        return original(self, result, *args, **kwargs)

    monkeypatch.setattr(PaydirtGameEngine, "_pending_punt_retained_result", substitute)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("BK - 8/retained-decline" in error for error in report["errors"])


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
@pytest.mark.parametrize("cell", ["F + 0", "BK - 8", "70"])
def test_declined_retained_kick_keeps_the_foul_annotation(
    home: bool, procedure: bool, foul: str, cell: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.possession_team.special_teams.punt = {10: foul, 11: cell}
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 31)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Foul"), (11, "Saved")]) as rolls:
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        pending = run(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 2
    assert pending.pending_penalty_decision
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "Recovery")) as rolls:
        outcome = game.apply_punt_penalty_decision(pending, False)
    assert rolls.call_count == int(cell != "70")
    assert not outcome.pending_penalty_decision
    assert not outcome.penalty_applied
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.play_log == [outcome]
    assert foul in outcome.description
    assert "declin" in outcome.description.lower()
    assert outcome.result.description == outcome.description
    assert outcome.result.raw_result == cell
    assert outcome.result.dice_roll == 11


def test_gate_rejects_erased_declined_foul_annotation(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance
    from paydirt.game_engine import PaydirtGameEngine
    from paydirt.game_state import PlayOutcome

    original = PaydirtGameEngine.apply_punt_penalty_decision

    def erase(game: PaydirtGameEngine, pending: PlayOutcome, accept_penalty: bool, penalty_index: int = 0) -> PlayOutcome:
        outcome = original(game, pending, accept_penalty, penalty_index)
        if not accept_penalty and outcome.result.raw_result == "BK - 8":
            outcome.description = outcome.description.replace("OFF 5 declined; ", "")
            outcome.result.description = outcome.description
        return outcome

    monkeypatch.setattr(PaydirtGameEngine, "apply_punt_penalty_decision", erase)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("PUNT/BK - 8/retained-decline" in error for error in report["errors"])

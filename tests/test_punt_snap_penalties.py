"""A punt-foul reroll keeps the fumbled-snap option without applying it early."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def pending_snap(
    foul: str, down: int, position: int = 40, procedure: bool = False, cell: str = "F - 10",
) -> tuple[PaydirtGameEngine, PlayOutcome, EngineCalibrationObserver]:
    game = make_sample_game()
    game.state.is_home_possession = True
    distance = min(8, 100 - position)
    game.state.ball_position, game.state.down, game.state.yards_to_go = position, down, distance
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: foul, 11: cell, 12: "40*"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = (10, 31)
        chart.special_teams.punt_return = {20: "0"}
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, PlayType.PUNT, DefenseType.STANDARD)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, f"Roll {n}") for n in [10, 11, 12, 20]]) as rolls:
        method = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = method(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 2
    assert outcome.pending_penalty_decision
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (position, down, distance)
    assert game.state.is_home_possession
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0
    assert game.state.home_score == game.state.away_score == 0
    assert not game.play_log
    assert game.state.time_remaining == 10
    assert outcome.result.raw_result == cell
    assert outcome.result.fumble_recovery_roll == 0
    assert not outcome.touchdown and not outcome.safety and not outcome.turnover
    return game, outcome, observer


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("recovery", [20, 35])
def test_declining_punt_foul_resolves_the_saved_snap_fumble(
    foul: str, procedure: bool, down: int, recovery: int,
) -> None:
    game, pending, observer = pending_snap(foul, down, procedure=procedure)
    with (patch("paydirt.game_engine.roll_chart_dice", return_value=(recovery, "recovery")) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.apply_punt_penalty_decision(pending, accept_penalty=False)
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    keeps = recovery == 20 and down < 4
    assert game.state.is_home_possession is keeps
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == ((30, 3, 18) if keeps else (70, 1, 10))
    assert outcome.result.result_type == ResultType.FUMBLE
    assert outcome.result.punt_snap_fumble
    assert outcome.result.fumble_recovery_roll == recovery
    assert outcome.result.dice_roll == 11
    assert outcome.result.punt_return_dice == 0
    assert not outcome.pending_penalty_decision and not outcome.penalty_applied
    assert outcome.turnover_on_downs is (down == 4 and recovery == 20)
    assert game.state.home_stats.fumbles_lost == int(recovery == 35)
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert observer.report()["teams"]["HOME"]["rushing_attempts"] == 1
    assert game.play_log == [outcome]
    assert game.state.time_remaining == pytest.approx(10 - 8 / 60)
    rolls.assert_called_once()
    assert not hasattr(game, "_pending_punt_state")


@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("foul,position,final,remaining,automatic", [
    ("OFF 5", 40, 35, 13, False), ("OFF 5", 4, 2, 10, False),
    ("DEF 5", 40, 45, 3, False), ("DEF 5", 97, 98, 2, False),
    ("DEF 5X", 40, 45, 10, True),
])
def test_accepting_punt_foul_erases_snap_without_recovery_or_attempt(
    down: int, foul: str, position: int, final: int, remaining: int, automatic: bool,
) -> None:
    game, pending, observer = pending_snap(foul, down, position)
    with (patch("paydirt.game_engine.roll_chart_dice") as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.apply_punt_penalty_decision(pending, accept_penalty=True)
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (final, 1 if automatic else down, remaining)
    stats = game.state.home_stats if foul.startswith("OFF") else game.state.away_stats
    assert (stats.penalties, stats.penalty_yards) == (1, abs(final - position))
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
    assert observer.report()["teams"]["HOME"]["offensive_plays"] == 0
    assert outcome.first_down is automatic
    assert not outcome.pending_penalty_decision and outcome.penalty_applied
    assert not outcome.turnover and not outcome.touchdown and not outcome.safety
    assert game.play_log == [outcome]
    assert not hasattr(game, "_pending_punt_state")
    rolls.assert_not_called()


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
def test_accepting_punt_foul_never_applies_a_projected_end_zone_fumble(foul: str) -> None:
    game, pending, _ = pending_snap(foul, 4, 4)
    before = deepcopy(game.state.scoring_plays)
    with patch("paydirt.game_engine.roll_chart_dice") as rolls:
        game.apply_punt_penalty_decision(pending, accept_penalty=True)
    assert game.state.scoring_plays == before
    assert game.state.home_score == game.state.away_score == 0
    rolls.assert_not_called()


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
def test_accepted_foul_after_snap_reroll_uses_core_half_expiration(foul: str) -> None:
    game, pending, _ = pending_snap(foul, 4)
    game.state.time_remaining = 3 / 60
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_punt_penalty_decision(pending, accept_penalty=True)
    assert game.has_untimed_down() is foul.startswith("DEF")
    assert game.state.quarter == (2 if foul.startswith("DEF") else 3)
    assert not outcome.touchdown and not outcome.safety
    assert game.state.home_score == game.state.away_score == 0


def test_pending_snap_choice_has_a_core_owned_unresolved_preview() -> None:
    _, pending, _ = pending_snap("OFF 5", 2)
    assert pending.penalty_choice.play_result_preview
    assert "recovery pending" in pending.penalty_choice.play_result_preview.lower()


def test_pending_snap_does_not_fabricate_a_resolved_turnover() -> None:
    _, pending, _ = pending_snap("OFF 5", 2)
    assert not pending.result.fumble_resolved
    assert not pending.result.turnover


def test_pending_snap_penalty_has_a_core_owned_enforcement_preview() -> None:
    _, pending, _ = pending_snap("OFF 5", 2)
    preview = pending.penalty_choice.penalty_options[0].result_preview
    assert preview == "2nd & 13 at HOME 35"


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
def test_accepted_snap_reroll_reports_the_applied_penalty(foul: str) -> None:
    game, pending, _ = pending_snap(foul, 2)
    outcome = game.apply_punt_penalty_decision(pending, accept_penalty=True)
    expected = ResultType.PENALTY_OFFENSE if foul.startswith("OFF") else ResultType.PENALTY_DEFENSE
    assert outcome.result.result_type == expected
    assert not outcome.result.punt_snap_fumble
    assert outcome.penalty_choice.play_result.result_type == ResultType.FUMBLE


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
def test_cli_displays_core_snap_preview_instead_of_fabricated_punt(
    foul: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    from paydirt import interactive_game as cli

    game, pending, _ = pending_snap(foul, 2)
    preview = "Synthetic engine snap fumble preview; recovery pending"
    pending.penalty_choice.play_result_preview = preview
    monkeypatch.setattr("builtins.input", lambda *args: "1")
    human_home = foul.startswith("DEF")
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(20, "recovery")):
        cli.handle_penalty_decision(game, pending, human_home, human_home)
    output = capsys.readouterr().out
    choice = next(line for line in output.splitlines() if "[1] Accept PLAY result:" in line)
    assert preview in choice
    assert "Punt stands as called" not in choice

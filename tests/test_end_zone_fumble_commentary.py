"""Distinguish a defensive end-zone recovery from a fumble return touchdown."""

from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)
from paydirt.result_formatter import ResultFormatter
from tests.game_fixtures import make_sample_game


def resolve_fumble(
    home: bool, yards: int, recovery: int, flow: str,
) -> tuple[PaydirtGameEngine, PlayOutcome, str, str]:
    """Resolve synthetic fumbles using public charts and real engine handling."""
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 7
    game.state.down, game.state.yards_to_go = 2, 16
    offense = game.state.possession_team.peripheral.short_name
    defense = game.state.defense_team.peripheral.short_name
    game.state.possession_team.peripheral.fumble_recovered_range = (1, 10)
    # Recovery 39 is a chart return like 37/38 (RULE-015): the touchdown comes from the cell.
    game.state.defense_team.special_teams.interception_return[34] = "TD" if recovery == 39 else "0"
    result = PlayResult(ResultType.FUMBLE, yards=yards, raw_result=f"F {yards:+d}",
                        dice_roll=26, defense_modifier="(-3)", description="FUMBLE!")
    penalties = [PenaltyOption("OFF", "OFF 5", 5, "Offensive penalty, 5 yards")] if flow == "declined" else []
    choice = PenaltyChoice(result, penalty_options=penalties, offended_team="defense")
    rolls = [(recovery, "recovery")]
    if yards > -7 and recovery in (37, 38, 39):
        rolls.append((34, "return"))
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as dice,
    ):
        run = game.run_play if flow == "direct" else game.run_play_with_penalty_procedure
        outcome = run(PlayType.SCREEN, DefenseType.SHORT_PASS)
        if flow == "declined":
            assert outcome.pending_penalty_decision
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
        assert dice.call_count == len(rolls)
    return game, outcome, offense, defense


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("yards", [-7, -8], ids=["goal-line", "end-zone"])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined"])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
def test_end_zone_recovery_is_not_described_as_a_return(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, yards: int, flow: str, view: str,
) -> None:
    game, outcome, offense, defense = resolve_fumble(home, yards, 33, flow)
    if view == "legacy-compact":
        outcome.transaction = None
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    cli.display_play_result(game, outcome, PlayType.SCREEN, DefenseType.SHORT_PASS,
                            game.state.home_chart if home else game.state.away_chart, home)
    output = capsys.readouterr().out
    expected = f"{defense} recovers the fumble in {offense}'s end zone. TOUCHDOWN!"
    assert expected in output
    assert "RETURNED FOR TD" not in output
    assert "FUMBLE RETURN TOUCHDOWN" not in output
    assert "SCOOP AND SCORE" not in output
    assert "Ret:" not in output
    assert outcome.touchdown and outcome.turnover and not outcome.safety
    assert getattr(outcome.result, "fumble_end_zone_touchdown", False)
    assert outcome.result.scoring_team == defense
    assert outcome.result.fumble_return_dice == outcome.result.fumble_return_yards == 0
    assert game.state.scoring_plays[-1].team == defense
    assert game.state.defense_stats.fumbles_lost == game.state.defense_stats.turnovers == 1
    assert ResultFormatter(offense, defense).format(outcome).commentary == expected


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined"])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
@pytest.mark.parametrize("recovery", [37, 39], ids=["rolled-zero-return", "return-touchdown"])
def test_genuine_return_rolls_and_touchdowns_remain_visible(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, flow: str, view: str, recovery: int,
) -> None:
    game, outcome, offense, defense = resolve_fumble(home, -6, recovery, flow)
    if view == "legacy-compact":
        outcome.transaction = None
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    cli.display_play_result(game, outcome, PlayType.SCREEN, DefenseType.SHORT_PASS,
                            game.state.home_chart if home else game.state.away_chart, home)
    output = capsys.readouterr().out
    assert not getattr(outcome.result, "fumble_end_zone_touchdown", False)
    assert outcome.result.fumble_return_dice == 34
    assert outcome.touchdown is (recovery == 39)
    if recovery == 39:
        assert ("FUMBLE RETURN TOUCHDOWN" if view == "full" else "SCOOP AND SCORE") in output
        assert outcome.result.scoring_team == defense
    if view == "compact" and flow != "direct":
        assert "Ret:34" in output
    assert f"{defense} recovers the fumble in {offense}'s end zone" not in output


@pytest.mark.parametrize("yards,recovery,safety", [(-6, 33, False), (-7, 10, True), (93, 33, False)])
def test_non_scoring_recoveries_are_not_end_zone_touchdowns(
    yards: int, recovery: int, safety: bool,
) -> None:
    game, outcome, _, _ = resolve_fumble(True, yards, recovery, "procedure")
    assert not outcome.touchdown
    assert outcome.safety is safety
    assert not getattr(outcome.result, "fumble_end_zone_touchdown", False)
    assert game.state.home_score == 0
    assert game.state.away_score == (2 if safety else 0)

"""Announcement audit controls reuse only synthetic/public-team fumbles."""

import pytest

from paydirt import interactive_game as cli
from paydirt.play_resolver import DefenseType, PlayType
from tests.test_end_zone_fumble_commentary import resolve_fumble


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
@pytest.mark.parametrize("recovery,yards", [(33, -7), (39, -6)])
def test_defensive_fumble_score_announced_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, view: str, recovery: int, yards: int,
) -> None:
    game, outcome, _, defense = resolve_fumble(home, yards, recovery, "procedure")
    if view == "legacy-compact":
        outcome.transaction = None
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    cli.display_play_result(game, outcome, PlayType.SCREEN, DefenseType.SHORT_PASS,
                            game.state.home_chart, home)
    output = capsys.readouterr().out
    assert outcome.touchdown and outcome.turnover
    assert outcome.result.scoring_team == defense
    if recovery == 33 or view == "full":
        assert output.upper().count("TOUCHDOWN") == 1
    else:
        assert output.count("SCOOP AND SCORE") == 1
        assert "RETURNED FOR TD" not in output
        assert "TOUCHDOWN" not in output


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
def test_offensive_fumble_advance_safety_announced_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, home: bool, view: str,
) -> None:
    from unittest.mock import patch

    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType
    from tests.game_fixtures import make_sample_game

    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 10
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)
    game.state.possession_team.special_teams.interception_return[11] = "-11"
    result = PlayResult(ResultType.FUMBLE, yards=-1, raw_result="F - 1", description="FUMBLE!")
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
          patch("paydirt.game_engine.roll_chart_dice", side_effect=[(17, "recovery"), (11, "advance")]) as dice):
        outcome = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    assert dice.call_count == 2
    assert outcome.safety and not outcome.touchdown and not outcome.turnover
    assert (game.state.home_score, game.state.away_score) == ((0, 2) if home else (2, 0))
    if view == "legacy-compact":
        outcome.transaction = None
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    cli.display_play_result(game, outcome, PlayType.OFF_TACKLE, DefenseType.STANDARD,
                            game.state.home_chart, home)
    output = capsys.readouterr().out
    assert output.upper().count("SAFETY") == 1
    assert outcome.result.rule_explanation in output

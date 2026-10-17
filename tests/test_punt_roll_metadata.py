"""Punt dice must survive touchback and coffin-corner early-return paths."""

from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


# Original position, chart result, subtraction, final receiving position.
PUNT_CASES = [
    pytest.param(51, "49", 0, 20, id="touchback"),
    pytest.param(56, "55", 15, 4, id="coffin-corner"),
    pytest.param(40, "35*", 0, 25, id="fair-catch-control"),
    pytest.param(40, "35†", 0, 25, id="downed-control"),
    pytest.param(40, "35", 0, 30, id="return-control"),
    pytest.param(40, "35", 10, 40, id="shortened-return-control"),
]


def punt(
    home: bool, procedure: bool, position: int, raw: str, subtraction: int,
) -> tuple[PaydirtGameEngine, PlayOutcome]:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = position, 4, 10
    game.state.possession_team.special_teams.punt[26] = raw
    game.state.defense_team.special_teams.punt_return[18] = "5"
    returnable = (
        position + int(raw.rstrip("*†")) - subtraction < 100
        and subtraction < 15
        and raw[-1] not in "*†"
    )
    rolls = [(26, "B2+W1+W5=26")]
    if returnable:
        rolls.append((18, "B1+W3+W5=18"))
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as dice:
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = run(PlayType.PUNT, DefenseType.STANDARD, punt_coffin_corner_yards=subtraction)
    assert dice.call_count == len(rolls)
    assert not outcome.pending_penalty_decision
    return game, outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True], ids=["direct", "procedure"])
@pytest.mark.parametrize("position,raw,subtraction,receiving_position", PUNT_CASES)
def test_punt_preserves_original_roll_without_changing_field_position(
    home: bool, procedure: bool, position: int, raw: str,
    subtraction: int, receiving_position: int,
) -> None:
    game, outcome = punt(home, procedure, position, raw, subtraction)
    assert game.state.is_home_possession is not home
    assert game.state.ball_position == receiving_position
    assert game.state.down == 1 and game.state.yards_to_go == 10
    assert not outcome.turnover and not outcome.touchdown
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0
    # Existing ordinary-return results store adjusted yardage and strip the downed marker.
    # Preserve that convention; this regression concerns the missing dice, not raw formatting.
    expected_raw = "35" if raw == "35†" else "25" if subtraction == 10 else raw
    assert outcome.result.raw_result == expected_raw
    assert outcome.result.dice_roll == 26
    if receiving_position == 20:
        assert "touchback" in outcome.description.lower()
    elif subtraction >= 15:
        assert "out of bounds" in outcome.description.lower()
        assert outcome.result.punt_return_dice == 0
    elif raw[-1] not in "*†":
        assert outcome.result.punt_return_dice == 18


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("position,raw,subtraction", [
    pytest.param(51, "49", 0, id="touchback"),
    pytest.param(56, "55", 15, id="coffin-corner"),
])
def test_compact_punt_display_shows_real_roll_not_placeholder_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, position: int, raw: str, subtraction: int,
) -> None:
    game, outcome = punt(home, True, position, raw, subtraction)
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    original_offense = game.state.home_chart if home else game.state.away_chart
    cli.display_play_result(
        game, outcome, PlayType.PUNT, DefenseType.STANDARD, original_offense, home,
    )
    output = capsys.readouterr().out
    assert f'Roll: 26 → "{raw}"' in output
    assert 'Roll: 0' not in output

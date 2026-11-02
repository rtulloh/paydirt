"""STAT-005: show assessed return fouls as well as the net advance.

All rolls and cells are synthetic. This is not a reconstruction of missing
reroll dice from the original manual game.
"""

from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


def return_play(
    home: bool, kind: str, flow: str, cell: str,
) -> tuple[PaydirtGameEngine, PlayOutcome]:
    """Lose nine yards from midfield, then return 21 before any enforcement."""
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home
    state.ball_position, state.down, state.yards_to_go = 50, 2, 10
    state.time_remaining = 10
    offense, defense = state.possession_team, state.defense_team
    offense.peripheral.fumble_recovered_range = (10, 32)
    returning = offense if kind == "kept" else defense
    returning.special_teams.interception_return.update({11: cell, 22: "21"})
    is_interception = kind == "interception"
    result = PlayResult(
        ResultType.INTERCEPTION if is_interception else ResultType.FUMBLE,
        yards=-9, raw_result="INT -9" if is_interception else "F -9",
        dice_roll=27, description="INTERCEPTION!" if is_interception else "FUMBLE!",
    )
    options = [PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty")] if flow == "declined" else []
    choice = PenaltyChoice(result, penalty_options=options, offended_team="offense")
    rolls = [] if is_interception else [(17 if kind == "kept" else 37, "Recovery")]
    rolls.append((11, "Return"))
    if cell != "21":
        rolls.append((22, "Reroll"))
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as dice,
    ):
        run = game.run_play if flow == "direct" else game.run_play_with_penalty_procedure
        outcome = run(PlayType.MEDIUM_PASS, DefenseType.SHORT_PASS)
        if flow == "declined":
            assert outcome.pending_penalty_decision
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
        assert dice.call_count == len(rolls)
    return game, outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("kind", ["kept", "lost", "interception"])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined"])
@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("cell", ["OFF 15", "DEF 15", "21"])
def test_return_penalty_is_visible_without_changing_its_accounting(
    home: bool, kind: str, flow: str, compact: bool, cell: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    game, outcome = return_play(home, kind, flow, cell)
    state = game.state
    returning_home = home if kind == "kept" else not home
    # A defensive foul after a return to the opponent 20 is half the distance.
    effective = 0 if cell == "21" else 10 if cell == "DEF 15" and kind != "kept" else 15
    net = 21 + (effective if cell.startswith("DEF") else -effective)
    assert state.is_home_possession is returning_home
    assert state.ball_position == (41 if kind == "kept" else 59) + net
    stats = (state.home_stats, state.away_stats)
    assert sum(team.penalties for team in stats) == int(cell != "21")
    assert sum(team.penalty_yards for team in stats) == effective
    if cell != "21":
        offender_home = returning_home if cell.startswith("OFF") else not returning_home
        offender = state.home_stats if offender_home else state.away_stats
        assert (offender.penalties, offender.penalty_yards) == (1, effective)
    returned = outcome.result.int_return_yards if kind == "interception" else outcome.result.fumble_return_yards
    assert returned == net

    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_play_result(
        game, outcome, PlayType.MEDIUM_PASS, DefenseType.SHORT_PASS,
        state.home_chart if home else state.away_chart, home,
    )
    output = capsys.readouterr().out
    if cell != "21":
        # The authoritative explanation must survive both CLI presentation paths.
        explanation = outcome.result.rule_explanation or ""
        assert cell in explanation
        assert f'Ret:11→"{cell}"' in explanation
        assert 'Ret reroll:22→"21"' in explanation
        assert explanation in output
    else:
        assert "OFF 15" not in output and "DEF 15" not in output

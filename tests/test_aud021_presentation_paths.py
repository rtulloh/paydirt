"""AUD-021: kick/return and compact trace presentation.

Only synthetic cells are used; no private season data is loaded.
"""

from unittest.mock import patch

import pytest

from paydirt.chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.interactive_game import display_play_result
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def chart(name: str) -> TeamChart:
    return TeamChart(
        peripheral=PeripheralData(
            year=2026, team_name=name, team_nickname=name,
            power_rating=50, short_name=name[:3].upper(),
        ),
        offense=OffenseChart(),
        defense=DefenseChart(),
        special_teams=SpecialTeamsChart(),
        team_dir="",
    )


def test_onside_failure_describes_receiving_teams_own_47_not_invalid_own_53() -> None:
    game = PaydirtGameEngine(chart("Home"), chart("Away"))
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(8, "B1+W0+W0=8")):
        outcome = game.onside_kick(kicking_home=True)

    assert "Receiving team recovers" in outcome.description
    assert "HOM 47" in outcome.description
    assert "own 53" not in outcome.description
    assert game.state.ball_position == 53
    assert game.state.field_position_str() == "HOM 47"


def test_kickoff_end_zone_return_trace_keeps_chart_value_and_final_spot_separate() -> None:
    game = make_sample_game()
    game.state.is_home_possession = False
    kicker = game.state.home_chart
    receiver = game.state.away_chart
    kicker.special_teams.kickoff.update({10: "74"})
    receiver.special_teams.kickoff_return.update({12: "18"})
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (10, "kick"), (12, "return"),
        ]),
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff(kicking_home=True)

    assert outcome.result.kickoff_return_dice == 12
    assert outcome.result.kickoff_return_result == "18"
    assert 'RT:12→"18"' in outcome.description


@pytest.mark.parametrize("play_type", [PlayType.QB_SNEAK, PlayType.QB_KNEEL])
def test_no_defense_roll_omits_the_defense_field(capsys, play_type: PlayType) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    result = PlayResult(
        result_type=ResultType.YARDS,
        yards=1 if play_type == PlayType.QB_SNEAK else -2,
        raw_result="4" if play_type == PlayType.QB_SNEAK else "KNEEL",
        dice_roll=14 if play_type == PlayType.QB_SNEAK else 0,
    )
    outcome = PlayOutcome(
        play_type=play_type,
        defense_type=DefenseType.STANDARD,
        result=result,
        description="Synthetic no-defense-roll play",
    )

    with patch("paydirt.interactive_game.COMPACT_MODE", True):
        display_play_result(
            game, outcome, play_type, DefenseType.STANDARD,
            game.state.home_chart, offense_was_home=True,
        )

    output = capsys.readouterr().out
    assert "D:?" not in output
    assert ' | D:' not in output


def test_quarterback_qb_human_sees_qt_secondary_roll(capsys) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    result = PlayResult(
        result_type=ResultType.FUMBLE,
        yards=-4,
        raw_result="QT",
        dice_roll=17,
        defense_dice="R2+G0=2",
        defense_modifier="-4",
        qb_scramble_dice=13,
        qb_scramble_yards=-4,
        fumble_recovery_roll=13,
        fumble_recovered=True,
        fumble_resolved=True,
    )
    outcome = PlayOutcome(
        play_type=PlayType.SHORT_PASS,
        defense_type=DefenseType.STANDARD,
        result=result,
        description="Synthetic QB-time fumble",
    )

    with patch("paydirt.interactive_game.COMPACT_MODE", True):
        display_play_result(
            game, outcome, PlayType.SHORT_PASS, DefenseType.STANDARD,
            game.state.home_chart, offense_was_home=True,
        )

    output = capsys.readouterr().out
    assert "QT:13→-4" in output
    assert "O:17" in output

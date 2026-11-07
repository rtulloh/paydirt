"""Selected priority, rather than discarded cells, defines the result class."""

from unittest.mock import patch

import pytest

from paydirt.chart_tactics_audit import controlled_offense
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import (
    DefenseType,
    PlayType,
    ResultType,
    resolve_play,
    resolve_play_with_penalties,
)
from paydirt.priority_chart import PriorityResult, apply_priority_chart


@pytest.mark.parametrize("token,yards", [("F", 0), ("F + 2", 2), ("F - 2", -2)])
@pytest.mark.parametrize("penalties", [False, True])
@pytest.mark.parametrize("recovery", [10, 39])
def test_selected_fumble_survives_discarded_interception(
    token: str, yards: int, penalties: bool, recovery: int,
) -> None:
    offense = controlled_offense(token)
    defender = controlled_offense("0")
    offense.peripheral.fumble_recovered_range = (10, 32)
    defender.defense.modifiers = {("A", row): {6: "INT 5"} for row in range(1, 6)}
    selected = apply_priority_chart(token, "INT 5")
    assert selected.priority == PriorityResult.FUMBLE
    assert selected.final_yards == yards
    route = resolve_play_with_penalties if penalties else resolve_play
    with (
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(10, "play"), (recovery, "recovery")]),
        patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
    ):
        output = route(offense, defender, PlayType.SHORT_PASS, DefenseType.STANDARD)
    result = output.play_result if penalties else output
    assert result.result_type == ResultType.FUMBLE
    assert result.yards == yards
    if penalties:
        assert result.fumble_resolved
        assert result.fumble_recovered == (recovery == 10)
        assert result.turnover == (recovery == 39)
        assert result.fumble_recovery_roll == recovery


@pytest.mark.parametrize("offense_cell,defense_cell,expected,yards", [
    ("INT 20", "INT 5", ResultType.INTERCEPTION, 5),
    ("INT 5", "INT 20", ResultType.INTERCEPTION, 5),
    ("BLACK", "INT 5", ResultType.INTERCEPTION, 5),
    ("INT 5", "BLACK", ResultType.INCOMPLETE, 0),
    ("INT 5", "(8)", ResultType.YARDS, 8),
    ("F + 2", "BLACK", ResultType.FUMBLE, 2),
])
@pytest.mark.parametrize("penalties", [False, True])
def test_selected_result_classes_keep_priority_controls(
    offense_cell: str, defense_cell: str, expected: ResultType, yards: int, penalties: bool,
) -> None:
    offense = controlled_offense(offense_cell)
    defender = controlled_offense("0")
    defender.defense.modifiers = {("A", row): {6: defense_cell} for row in range(1, 6)}
    with (
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(10, "control")),
        patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
    ):
        output = (resolve_play_with_penalties if penalties else resolve_play)(
            offense, defender, PlayType.SHORT_PASS, DefenseType.STANDARD,
        )
    result = output.play_result if penalties else output
    assert (result.result_type, result.yards) == (expected, yards)


@pytest.mark.parametrize("recovery", [10, 39])
@pytest.mark.parametrize("penalty_reroll", [False, True])
def test_engine_fumble_recovery_and_reroll_do_not_become_interceptions(
    recovery: int, penalty_reroll: bool,
) -> None:
    offense = controlled_offense("F + 2")
    defender = controlled_offense("0")
    offense.peripheral.fumble_recovered_range = (10, 32)
    defender.defense.modifiers = {("A", row): {6: "INT 5"} for row in range(1, 6)}
    defender.special_teams.interception_return = dict.fromkeys(range(10, 40), "0")
    if penalty_reroll:
        offense.offense.short_pass[11] = "DEF 5"
    engine = PaydirtGameEngine(offense, defender)
    engine.state.is_home_possession = True
    engine.state.ball_position = 40
    rolls = ([(11, "penalty")] if penalty_reroll else []) + [(10, "play"), (recovery, "recovery")]
    with (
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls),
        patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
        patch("paydirt.game_engine.roll_chart_dice", return_value=(12, "return")),
    ):
        outcome = engine.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert outcome.result.result_type == ResultType.FUMBLE
    assert outcome.result.fumble_resolved
    assert outcome.result.fumble_recovered == (recovery == 10)
    assert outcome.result.fumble_recovery_roll == recovery
    if not penalty_reroll:
        assert outcome.turnover == (recovery == 39)
        assert engine.state.home_stats.interceptions_thrown == 0
    else:
        assert outcome.penalty_choice is not None
        assert outcome.penalty_choice.offended_team == "offense"

"""The receiving CPU must take offered punt yardage without surrendering possession."""

from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI
from paydirt.play_resolver import DefenseType, PenaltyOption, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("kicking_home", [True, False])
@pytest.mark.parametrize("spot,coffin,expected", [(50, 0, 6), (60, 0, 25), (50, 15, 21)])
def test_receiving_cpu_keeps_punt_plus_penalty_yards(
    kicking_home: bool, spot: int, coffin: int, expected: int,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = kicking_home
    game.state.ball_position, game.state.down, game.state.yards_to_go = spot, 4, 10
    game.state.possession_team.special_teams.punt = {10: "OFF 5", 11: "49"}
    game.state.defense_team.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Roll10"), (11, "Roll11"), (20, "Roll20"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD, punt_coffin_corner_yards=coffin)
    assert pending.pending_penalty_decision
    assert pending.penalty_choice.penalty_options[1].raw_result == "KEEP+5"

    # Preserve the original index even when an ineligible option precedes it.
    pending.penalty_choice.penalty_options.insert(
        0, PenaltyOption("DEF", "DEF 5", 5, "Ineligible receiving-team foul"),
    )
    accept_play, index = ComputerAI().should_accept_penalty(pending, True, kicking_home)
    assert (accept_play, index) == (False, 2)
    with patch("paydirt.game_engine.roll_chart_dice") as rolls:
        final = game.apply_punt_penalty_decision(pending, not accept_play, index)
    rolls.assert_not_called()
    assert game.state.is_home_possession is not kicking_home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (expected, 1, 10)
    assert not final.pending_penalty_decision
    assert game.state.defense_stats.penalties == 1
    assert game.state.defense_stats.penalty_yards == 5


def test_receiving_cpu_keeps_its_return_touchdown() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 50, 4, 10
    game.state.possession_team.special_teams.punt = {10: "OFF 5", 11: "40"}
    game.state.defense_team.special_teams.punt_return = {20: "TD"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Roll10"), (11, "Roll11"), (20, "Roll20"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    accept_play, index = ComputerAI().should_accept_penalty(pending, True, True)
    final = game.apply_punt_penalty_decision(pending, not accept_play, index)
    assert final.touchdown
    assert game.state.away_score == 6

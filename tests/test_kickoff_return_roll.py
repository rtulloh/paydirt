"""Kickoff returns are the receiving team's own roll (rules: Kickoff / Kickoff Return).

Public 2026 charts with explicit synthetic cells; every test states exactly which
chart rolls a kickoff may consume and in what order.
"""

from unittest.mock import patch

import pytest

from tests.game_fixtures import make_sample_game


def kick_game(kicking_home: bool = True):
    game = make_sample_game()
    kicker = game.state.home_chart if kicking_home else game.state.away_chart
    receiver = game.state.away_chart if kicking_home else game.state.home_chart
    kicker.special_teams.kickoff.clear()
    receiver.special_teams.kickoff_return.clear()
    return game, kicker.special_teams, receiver.special_teams


def rolls(*values):
    return [(value, f"Roll{value}") for value in values]


@pytest.mark.parametrize("kicking_home", [True, False])
def test_return_uses_the_receiving_teams_own_second_roll(kicking_home: bool) -> None:
    game, kicker, receiver = kick_game(kicking_home)
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({24: "5", 31: "25"})
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.kickoff(kicking_home=kicking_home)
    assert dice.call_count == 2, "kick roll, then a separate return roll"
    assert game.state.is_home_possession is not kicking_home
    assert game.state.ball_position == 30  # Landed at the 5, returned 25.
    assert outcome.result.dice_roll == 24
    assert outcome.result.kickoff_return_dice == 31
    assert outcome.result.kickoff_return_result == "25"
    assert 'KO:24→"60"' in outcome.description
    assert 'RT:31→"25"' in outcome.description
    assert "RT:24" not in outcome.description


@pytest.mark.parametrize("cell,expected_spot", [("TB", 20), ("76", 20), ("OB", 40)],
                         ids=["touchback-marker", "beyond-end-line", "out-of-bounds"])
def test_kicks_without_a_return_consume_no_return_roll(cell: str, expected_spot: int) -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[12] = cell
    receiver.kickoff_return[12] = "100"  # Must never be read.
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(12)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.kickoff(kicking_home=True)
    assert dice.call_count == 1
    assert game.state.ball_position == expected_spot
    assert not outcome.touchdown
    assert outcome.result.kickoff_return_dice == 0
    assert "RT:12" not in outcome.description
    assert "RT:none" in outcome.description


@pytest.mark.parametrize("return_cell,expected_spot,touchback", [("18", 9, False), ("9", 20, True), ("30", 21, False)])
def test_end_zone_kick_counts_end_zone_depth_and_shows_the_chart_value(
    return_cell: str, expected_spot: int, touchback: bool,
) -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "74"  # Nine yards deep from the 35.
    receiver.kickoff_return.update({24: "99", 31: return_cell})
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.kickoff(kicking_home=True)
    assert dice.call_count == 2
    assert game.state.ball_position == expected_spot
    assert ("Touchback" in outcome.description) is touchback
    assert f'RT:31→"{return_cell}"' in outcome.description


def test_kick_chart_penalty_rolls_kick_reroll_then_return_and_decline_uses_that_return() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({10: "OFF 5", 11: "65"})
    receiver.kickoff_return.update({10: "100", 11: "100", 31: "20"})
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(10, 11, 31)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        pending = game.kickoff(kicking_home=True)
        assert pending.pending_penalty_decision
        assert dice.call_count == 3
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
    assert dice.call_count == 3, "declining must not roll again"
    assert not outcome.touchdown
    assert game.state.ball_position == 20  # Landed at the goal line, returned 20.
    assert game.state.home_score == game.state.away_score == 0


def test_kick_chart_penalty_accepted_rekicks_with_fresh_kick_and_return_rolls() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({10: "OFF 5", 11: "65"})
    receiver.kickoff_return.update({31: "20", 13: "10"})
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(10, 11, 31, 11, 13)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        pending = game.kickoff(kicking_home=True)
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert dice.call_count == 5
    assert "from 40" in outcome.description or "Kickoff 65" in outcome.description
    # Re-kick from the 40: 65 yards lands five deep; a 10-yard return reaches the 5.
    assert game.state.ball_position == 5
    assert outcome.result.kickoff_return_dice == 13


def test_return_chart_penalty_rerolls_from_the_separate_return_roll_and_offers_the_choice() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({24: "0", 31: "DEF 15", 13: "30"})
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        pending = game.kickoff(kicking_home=True)
        assert dice.call_count == 3
        assert pending.pending_penalty_decision is True  # RULE-013: the receiving team chooses.
        game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert dice.call_count == 3
    # Landed at the 5, returned 30, plus the 15-yard kicking-team foul.
    assert game.state.ball_position == 50


def test_safety_free_kick_also_rolls_the_return_separately() -> None:
    game, kicker, receiver = kick_game()
    game.state.is_home_possession = True
    kicker.kickoff[24] = "50"
    receiver.kickoff_return.update({24: "0", 31: "15"})
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.safety_free_kick(use_punt=False)
    assert dice.call_count == 2
    assert game.state.ball_position == 45  # From the 20: lands at the 30, returned 15.
    assert "Safety free kick" in outcome.description


def test_onside_kick_still_uses_one_roll() -> None:
    game, _, _ = kick_game()
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(15)) as dice,
          patch("paydirt.game_engine.random.uniform", return_value=5)):
        game.onside_kick(kicking_home=True)
    assert dice.call_count == 1

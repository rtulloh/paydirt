"""Kickoff return-chart penalties are offered to the offended team (RULE-013).

The penalty procedure gives the offended team the choice of the penalty or the
play result. A receiving-team foul on the return (OFF) is the kicking team's
choice; a kicking-team foul (DEF) is the receiving team's choice. Kickoff
decisions use the receiving team's perspective as "offense", as the CLI and
auto game already do. Public 2026 charts with explicit synthetic cells.
"""

from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI, cpu_should_accept_penalty
from paydirt.auto_game import _resolve_auto_penalties
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


def pending_return_penalty(kicking_home: bool = True, cell: str = "OFF 15", reroll_cell: str = "30"):
    """Kick 60 from the 35 (lands at the 5); return-chart penalty, reroll for yardage."""
    game, kicker, receiver = kick_game(kicking_home)
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({31: cell, 13: reroll_cell})
    dice = patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13))
    with dice as mock, patch("paydirt.game_engine.random.uniform", return_value=8):
        pending = game.kickoff(kicking_home=kicking_home)
    assert mock.call_count == 3
    return game, pending


def receiver_label(game, kicking_home: bool) -> str:
    chart = game.state.away_chart if kicking_home else game.state.home_chart
    return chart.peripheral.short_name


@pytest.mark.parametrize("kicking_home", [True, False])
def test_receiving_team_foul_offers_the_kicking_team_the_choice(kicking_home: bool) -> None:
    game, pending = pending_return_penalty(kicking_home)
    assert pending.pending_penalty_decision is True
    choice = pending.penalty_choice
    assert choice.kick_phase == "return"
    assert choice.offended_team == "defense", "the kicking team chooses; the receiver is 'offense'"
    assert [opt.penalty_type for opt in choice.penalty_options] == ["OFF"]
    assert choice.penalty_options[0].yards == 15
    receiver = receiver_label(game, kicking_home)
    assert f"{receiver} 20" in choice.penalty_options[0].result_preview  # 5 + 30 - 15
    assert f"{receiver} 35" in choice.play_result_preview  # 5 + 30
    assert choice.play_result.yards == 30
    assert choice.play_result.touchdown is False
    # Nothing is applied until the decision: the kicker still has the ball at the tee.
    assert game.state.is_home_possession is kicking_home
    assert game.play_log == []
    assert 'KO:24→"60"' in pending.description
    assert 'RT:31→"OFF 15"' in pending.description
    assert 'RT reroll:13→"30"' in pending.description
    assert "Kicking team chooses" in pending.description


@pytest.mark.parametrize("kicking_home", [True, False])
def test_kicking_team_accepts_the_receiving_team_foul(kicking_home: bool) -> None:
    game, pending = pending_return_penalty(kicking_home)
    receiver_stats = game.state.away_stats if kicking_home else game.state.home_stats
    with patch("paydirt.game_engine.roll_chart_dice") as dice, \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert dice.call_count == 0, "a decision never rolls"
    assert game.state.is_home_possession is not kicking_home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (20, 1, 10)
    assert outcome.pending_penalty_decision is False
    assert outcome.penalty_applied is True
    assert outcome.touchdown is False
    assert outcome.yards_gained == 20
    assert outcome.result.dice_roll == 24
    assert outcome.result.kickoff_return_dice == 31
    assert outcome.result.kickoff_return_result == "OFF 15"
    assert "accepted" in outcome.description
    assert 'KO:24→"60"' in outcome.description and 'RT reroll:13→"30"' in outcome.description
    assert (receiver_stats.penalties, receiver_stats.penalty_yards) == (1, 15)
    assert len(game.play_log) == 1 and game.play_log[-1] is outcome


@pytest.mark.parametrize("kicking_home", [True, False])
def test_kicking_team_declines_and_the_return_stands(kicking_home: bool) -> None:
    game, pending = pending_return_penalty(kicking_home)
    receiver_stats = game.state.away_stats if kicking_home else game.state.home_stats
    with patch("paydirt.game_engine.roll_chart_dice") as dice, \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
    assert dice.call_count == 0
    assert game.state.is_home_possession is not kicking_home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (35, 1, 10)
    assert outcome.penalty_applied is False
    assert outcome.yards_gained == 35
    assert "declined" in outcome.description
    assert 'RT:31→"OFF 15"' in outcome.description
    assert (receiver_stats.penalties, receiver_stats.penalty_yards) == (0, 0)
    assert len(game.play_log) == 1


def test_kicking_team_foul_offers_the_receiving_team_the_choice_and_adds_yards() -> None:
    game, pending = pending_return_penalty(cell="DEF 15")
    choice = pending.penalty_choice
    assert choice.offended_team == "offense", "the receiving team chooses"
    assert [opt.penalty_type for opt in choice.penalty_options] == ["DEF"]
    assert "AWAY 50" in choice.penalty_options[0].result_preview or "midfield" in choice.penalty_options[0].result_preview
    assert "Receiving team chooses" in pending.description
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert game.state.ball_position == 50
    assert game.state.is_home_possession is False
    assert outcome.penalty_applied is True
    # The kicking team committed the foul.
    assert (game.state.home_stats.penalties, game.state.home_stats.penalty_yards) == (1, 15)
    assert (game.state.away_stats.penalties, game.state.away_stats.penalty_yards) == (0, 0)


def test_receiving_team_may_decline_a_kicking_team_foul() -> None:
    game, pending = pending_return_penalty(cell="DEF 15")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
    assert game.state.ball_position == 35
    assert outcome.penalty_applied is False
    assert game.state.home_stats.penalties == 0


def test_kicking_team_foul_near_the_goal_is_half_the_distance() -> None:
    game, pending = pending_return_penalty(cell="DEF 15", reroll_cell="90")  # 5 + 90 = 95
    assert pending.penalty_choice.play_result.touchdown is False
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert game.state.ball_position == 97, "half the distance from the 95, never a penalty touchdown"
    assert game.state.home_score == game.state.away_score == 0


def test_receiving_team_foul_that_negates_a_return_touchdown_is_enforced_from_the_catch_spot() -> None:
    game, pending = pending_return_penalty(cell="OFF 15", reroll_cell="95")  # 5 + 95 = 100
    choice = pending.penalty_choice
    assert choice.play_result.touchdown is True
    assert "TOUCHDOWN" in choice.play_result_preview
    assert "AWAY 3" in choice.penalty_options[0].result_preview  # From the 5: half the distance is 2.
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert outcome.touchdown is False
    assert game.state.ball_position == 3
    assert game.state.away_score == 0
    assert game.state.scoring_plays == []


def test_declining_the_foul_keeps_the_return_touchdown() -> None:
    game, pending = pending_return_penalty(cell="OFF 15", reroll_cell="95")
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
    assert outcome.touchdown is True
    assert game.state.away_score == 6
    assert "TOUCHDOWN" in outcome.description


def test_same_type_rerolls_carry_the_larger_penalty_into_the_choice() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[11] = "50"  # Lands at the 15.
    receiver.kickoff_return.update({11: "OFF 15", 12: "OFF 20", 13: "25"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(11, 11, 12, 13)), \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        pending = game.kickoff(kicking_home=True)
        assert pending.pending_penalty_decision
        assert pending.penalty_choice.penalty_options[0].yards == 20
        game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert game.state.ball_position == 20  # 15 + 25 - 20


def test_offsetting_return_penalties_still_rekick_without_a_choice() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({11: "50", 14: "55"})
    receiver.kickoff_return.update({11: "OFF 15", 12: "DEF 10", 14: "25"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(11, 11, 12, 14, 14)) as dice, \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.kickoff(kicking_home=True)
    assert dice.call_count == 5
    assert outcome.pending_penalty_decision is False
    assert game.state.ball_position == 35  # Re-kick: lands at the 10, returned 25.


def test_end_zone_return_with_a_penalty_is_also_a_choice() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "74"  # Nine yards deep.
    receiver.kickoff_return.update({31: "OFF 15", 13: "30"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)), \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        pending = game.kickoff(kicking_home=True)
        assert pending.pending_penalty_decision is True
        assert "AWAY 21" in pending.penalty_choice.play_result_preview  # 30 - 9
        game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert game.state.ball_position == 6  # 21 - 15


def test_kick_chart_penalty_choice_is_marked_as_the_kick_phase() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({10: "OFF 5", 11: "65"})
    receiver.kickoff_return[31] = "20"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(10, 11, 31)), \
            patch("paydirt.game_engine.random.uniform", return_value=8):
        pending = game.kickoff(kicking_home=True)
    assert pending.pending_penalty_decision is True
    assert pending.penalty_choice.kick_phase == "kick"


class TestCpuDecisions:
    def test_cpu_kicking_team_accepts_a_receiving_team_foul(self) -> None:
        _, pending = pending_return_penalty(cell="OFF 15")
        # Human receives (is "offense" at a kickoff); the CPU kicker decides.
        assert cpu_should_accept_penalty(pending, is_human_offense=True, human_is_home=False) == (False, 0)

    def test_cpu_kicking_team_accepts_a_foul_that_negates_a_return_touchdown(self) -> None:
        _, pending = pending_return_penalty(cell="OFF 15", reroll_cell="95")
        assert cpu_should_accept_penalty(pending, is_human_offense=True, human_is_home=False) == (False, 0)

    def test_cpu_receiving_team_accepts_kicking_team_yards(self) -> None:
        _, pending = pending_return_penalty(cell="DEF 15")
        assert cpu_should_accept_penalty(pending, is_human_offense=False, human_is_home=True) == (False, 0)

    def test_cpu_receiving_team_keeps_its_return_touchdown(self) -> None:
        _, pending = pending_return_penalty(cell="DEF 15", reroll_cell="95")
        accept_play, _ = cpu_should_accept_penalty(pending, is_human_offense=False, human_is_home=True)
        assert accept_play is True

    def test_auto_game_resolves_the_kickoff_choice_for_the_offended_side(self) -> None:
        game, pending = pending_return_penalty(cell="OFF 15")
        home_ai = ComputerAI(aggression=0.5)
        away_ai = ComputerAI(aggression=0.5)
        with patch("paydirt.game_engine.random.uniform", return_value=8):
            outcome = _resolve_auto_penalties(game, pending, offense_home=False, home_ai=home_ai, away_ai=away_ai)
        assert outcome.pending_penalty_decision is False
        assert game.state.ball_position == 20
        assert game.state.is_home_possession is False

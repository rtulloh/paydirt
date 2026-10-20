"""Kickoff return-chart penalties and fumbles (RULE-013 corrected, RULE-014).

Rules: a penalty cell on a return chart means reroll for the return, then
assess the penalty automatically against the end of the return — backward for
OFF (the returning team's foul), forward for DEF — with half the distance both
ways and never a penalty touchdown. Possession is unaffected; there is no
accept/decline. A fumble cell is resolved with the returning team's recovery
roll. The one decision: when the reroll after a penalty is a fumble that the
other team recovers, that team may keep the recovery or take the penalty.
Public 2026 charts with explicit synthetic cells; recovery range (10, 27).
"""

from unittest.mock import patch

import pytest

from paydirt.computer_ai import cpu_should_accept_penalty
from tests.game_fixtures import make_sample_game


def kick_game(kicking_home: bool = True):
    game = make_sample_game()
    kicker = game.state.home_chart if kicking_home else game.state.away_chart
    receiver = game.state.away_chart if kicking_home else game.state.home_chart
    kicker.special_teams.kickoff.clear()
    receiver.special_teams.kickoff_return.clear()
    receiver.peripheral.fumble_recovered_range = (10, 27)
    game.state.is_home_possession = kicking_home
    return game, kicker.special_teams, receiver.special_teams


def rolls(*values):
    return [(value, f"Roll{value}") for value in values]


def kick(game, kicking_home, *dice):
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(*dice)) as mock,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.kickoff(kicking_home=kicking_home)
    assert mock.call_count == len(dice), "every listed roll is consumed and no other"
    return outcome


@pytest.mark.parametrize("kicking_home", [True, False])
def test_receiving_team_foul_is_assessed_from_the_end_of_the_return(kicking_home: bool) -> None:
    game, kicker, receiver = kick_game(kicking_home)
    kicker.kickoff[24] = "60"  # Lands at the 5.
    receiver.kickoff_return.update({31: "OFF 15", 13: "30"})
    outcome = kick(game, kicking_home, 24, 31, 13)
    assert outcome.pending_penalty_decision is False
    assert game.state.is_home_possession is not kicking_home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (20, 1, 10)  # 5 + 30 - 15
    assert outcome.penalty_applied is True
    assert outcome.yards_gained == 20
    assert "OFF 15" in outcome.description
    assert 'KO:24→"60"' in outcome.description
    assert 'RT:31→"OFF 15"' in outcome.description and 'RT reroll:13→"30"' in outcome.description
    receiver_stats = game.state.away_stats if kicking_home else game.state.home_stats
    assert (receiver_stats.penalties, receiver_stats.penalty_yards) == (1, 15)
    assert len(game.play_log) == 1


def test_kicking_team_foul_adds_yards_to_the_return() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({31: "DEF 15", 13: "30"})
    outcome = kick(game, True, 24, 31, 13)
    assert game.state.ball_position == 50
    assert game.state.is_home_possession is False
    assert outcome.penalty_applied is True
    assert (game.state.home_stats.penalties, game.state.home_stats.penalty_yards) == (1, 15)
    assert game.state.away_stats.penalties == 0


def test_kicking_team_foul_near_the_goal_is_half_the_distance() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({31: "DEF 15", 13: "90"})  # 5 + 90 = 95
    kick(game, True, 24, 31, 13)
    assert game.state.ball_position == 97
    assert game.state.home_score == game.state.away_score == 0


def test_receiving_team_foul_wipes_out_a_return_touchdown_from_the_goal_line() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({31: "OFF 15", 13: "95"})  # 5 + 95 = 100
    outcome = kick(game, True, 24, 31, 13)
    assert outcome.touchdown is False
    assert game.state.ball_position == 85  # Enforced backward from the end of the return.
    assert game.state.away_score == 0
    assert "nullified" in outcome.description.lower()


def test_kicking_team_foul_does_not_take_away_a_return_touchdown() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update({31: "DEF 15", 13: "95"})
    outcome = kick(game, True, 24, 31, 13)
    assert outcome.touchdown is True
    assert game.state.away_score == 6
    assert game.state.home_stats.penalties == 1


def test_same_type_rerolls_take_the_larger_penalty() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[11] = "50"  # Lands at the 15.
    receiver.kickoff_return.update({11: "OFF 15", 12: "OFF 20", 13: "25"})
    kick(game, True, 11, 11, 12, 13)
    assert game.state.ball_position == 20  # 15 + 25 - 20


def test_offsetting_return_penalties_rekick() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({11: "50", 14: "55"})
    receiver.kickoff_return.update({11: "OFF 15", 12: "DEF 10", 14: "25"})
    outcome = kick(game, True, 11, 11, 12, 14, 14)
    assert outcome.pending_penalty_decision is False
    assert game.state.ball_position == 35  # Re-kick: lands at the 10, returned 25.


def test_end_zone_return_penalty_is_assessed_too() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "74"  # Nine yards deep.
    receiver.kickoff_return.update({31: "OFF 15", 13: "30"})
    kick(game, True, 24, 31, 13)
    assert game.state.ball_position == 6  # (30 - 9) - 15


class TestReturnFumbles:
    def test_fumble_recovered_by_the_returner_keeps_the_ball_at_the_spot(self) -> None:
        game, kicker, receiver = kick_game()
        kicker.kickoff[24] = "60"
        receiver.kickoff_return[31] = "F + 17"
        outcome = kick(game, True, 24, 31, 20)  # Recovery roll 20 is in (10, 27).
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 22  # 5 + 17
        assert outcome.turnover is False
        assert "FUMBLE" in outcome.description.upper()
        assert 'R:20' in outcome.description
        assert game.state.away_stats.fumbles_lost == 0

    def test_fumble_lost_gives_the_kicking_team_the_ball_at_the_spot(self) -> None:
        game, kicker, receiver = kick_game()
        kicker.kickoff[24] = "60"
        receiver.kickoff_return[31] = "F + 17"
        outcome = kick(game, True, 24, 31, 30)  # Recovery roll 30 is lost.
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 78  # Kicking team at its own 78 = receiver's 22.
        assert (game.state.down, game.state.yards_to_go) == (1, 10)
        assert outcome.turnover is True
        assert game.state.away_stats.fumbles_lost == 1
        assert game.state.away_stats.turnovers == 1
        assert 'R:30' in outcome.description

    def test_fumble_after_a_penalty_recovered_by_the_returner_is_assessed(self) -> None:
        game, kicker, receiver = kick_game()
        kicker.kickoff[24] = "60"
        receiver.kickoff_return.update({31: "OFF 15", 13: "F + 17"})
        outcome = kick(game, True, 24, 31, 13, 20)  # Reroll fumble, recovered.
        assert outcome.pending_penalty_decision is False
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 7  # 5 + 17 - 15
        assert game.state.away_stats.penalties == 1

    def test_fumble_after_a_penalty_recovered_by_the_kicking_team_is_its_choice(self) -> None:
        game, kicker, receiver = kick_game()
        kicker.kickoff[24] = "60"
        receiver.kickoff_return.update({31: "OFF 15", 13: "F + 17"})
        pending = kick(game, True, 24, 31, 13, 30)  # Reroll fumble, lost.
        assert pending.pending_penalty_decision is True
        choice = pending.penalty_choice
        assert choice.kick_phase == "return_fumble"
        assert choice.offended_team == "defense", "the kicking team recovered and chooses"
        assert "HOME" in choice.play_result_preview and "22" in choice.play_result_preview
        assert "AWAY 7" in choice.penalty_options[0].result_preview
        assert game.state.is_home_possession is True  # Nothing applied yet.
        # Keep the recovery.
        with patch("paydirt.game_engine.random.uniform", return_value=8):
            outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 78
        assert outcome.turnover is True
        assert game.state.away_stats.fumbles_lost == 1
        assert game.state.away_stats.penalties == 0

    def test_kicking_team_may_take_the_penalty_instead_of_the_recovery(self) -> None:
        game, kicker, receiver = kick_game()
        kicker.kickoff[24] = "60"
        receiver.kickoff_return.update({31: "OFF 15", 13: "F + 17"})
        pending = kick(game, True, 24, 31, 13, 30)
        with patch("paydirt.game_engine.random.uniform", return_value=8):
            outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 7
        assert outcome.turnover is False
        assert game.state.away_stats.fumbles_lost == 0
        assert game.state.away_stats.penalties == 1

    def test_cpu_keeps_the_recovery(self) -> None:
        game, kicker, receiver = kick_game()
        kicker.kickoff[24] = "60"
        receiver.kickoff_return.update({31: "OFF 15", 13: "F + 17"})
        pending = kick(game, True, 24, 31, 13, 30)
        accept_play, _ = cpu_should_accept_penalty(pending, is_human_offense=True, human_is_home=False)
        assert accept_play is True


def test_kick_chart_penalty_choice_is_unchanged() -> None:
    game, kicker, receiver = kick_game()
    kicker.kickoff.update({10: "OFF 5", 11: "65"})
    receiver.kickoff_return[31] = "20"
    pending = kick(game, True, 10, 11, 31)
    assert pending.pending_penalty_decision is True
    assert pending.penalty_choice.kick_phase == "kick"

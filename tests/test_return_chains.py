"""Return chains: fumbles during returns, fumble returns, and live penalties.

Permutation matrix (R = return roll, FR = fumble return on the recovering
team's Int. Return chart after a recovery roll of 17–19 / 37–39):
  R1 yards | R1 OFF R2 yards | R1 DEF R2 yards | R1 OFF R2 DEF R3 | R1 OFF R2 TD |
  R1 DEF R2 TD | R1 OFF R2 OFF R3 | R1 DEF R2 DEF R3 | R1 DEF R2 fumble |
  R1 OFF R2 fumble + FR {yards | OFF/DEF + yards | OFF/DEF + TD | offsetting} |
  KR | KR,FR | FR,FR | IR | IR,FR | IR,FR,FR | KR,FR,FR.
A live penalty (its segment ended in a lost fumble) is assessed against the
fouling team when it ends up with the ball; when the other team ends up with
the ball, an OFF foul is that team's choice (kickoffs prompt; the CPU keeps the
recovery) and a DEF foul is always taken by the offended returner.
Kickoff from the 35, 60 yards → lands at the 5; AWAY returns, HOME kicked.
"""

from typing import Optional
from unittest.mock import patch

from paydirt.computer_ai import cpu_should_accept_penalty
from tests.test_kickoff_return_penalties import kick, kick_game
from tests.test_return_chart_rules import game_with_return_chart, interception, run


def chain_game(return_cells: dict, away_fr: Optional[dict] = None, home_fr: Optional[dict] = None):
    game, kicker, receiver = kick_game()
    kicker.kickoff[24] = "60"
    receiver.kickoff_return.update(return_cells)
    for chart, cells in ((game.state.away_chart, away_fr), (game.state.home_chart, home_fr)):
        chart.special_teams.interception_return.clear()
        chart.special_teams.interception_return.update(cells or {})
        chart.peripheral.fumble_recovered_range = (10, 27)
    return game


def test_two_def_fouls_take_the_larger_and_add_yards() -> None:
    game = chain_game({31: "DEF 10", 12: "DEF 15", 13: "30"})
    kick(game, True, 24, 31, 12, 13)
    assert game.state.ball_position == 50  # 5 + 30 + 15
    assert game.state.home_stats.penalty_yards == 15


def test_def_foul_then_fumble_recovered_by_the_returner_adds_yards_from_the_spot() -> None:
    game = chain_game({31: "DEF 15", 13: "F + 17"})
    outcome = kick(game, True, 24, 31, 13, 20)
    assert game.state.is_home_possession is False
    assert game.state.ball_position == 37  # 5 + 17 + 15
    assert outcome.turnover is False


def test_def_foul_then_fumble_lost_the_returner_takes_the_penalty() -> None:
    game = chain_game({31: "DEF 15", 13: "F + 17"})
    outcome = kick(game, True, 24, 31, 13, 30)
    assert outcome.pending_penalty_decision is False
    assert game.state.is_home_possession is False, "possession beats the recovery; the penalty is taken"
    assert game.state.ball_position == 37
    assert game.state.away_stats.fumbles_lost == 0
    assert game.state.home_stats.penalties == 1


class TestFumbleReturnsByTheReturner:
    """OFF 15 on the return, fumble at the 22, recovered on 17 → fumble return on AWAY's chart."""

    def test_fumble_return_yards_then_the_live_penalty(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, away_fr={14: "20"})
        outcome = kick(game, True, 24, 31, 13, 17, 14)
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 27  # 22 + 20 - 15
        assert 'FR:14→"20"' in outcome.description
        assert game.state.away_stats.penalties == 1

    def test_fumble_return_off_foul_is_assessed_then_the_live_penalty(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, away_fr={14: "OFF 10", 15: "20"})
        kick(game, True, 24, 31, 13, 17, 14, 15)
        assert game.state.ball_position == 17  # 22 + 20 - 10 - 15
        assert (game.state.away_stats.penalties, game.state.away_stats.penalty_yards) == (2, 25)

    def test_fumble_return_def_foul_adds_yards_then_the_live_penalty(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, away_fr={14: "DEF 10", 15: "20"})
        kick(game, True, 24, 31, 13, 17, 14, 15)
        assert game.state.ball_position == 37  # 22 + 20 + 10 - 15
        assert game.state.home_stats.penalties == 1 and game.state.away_stats.penalties == 1

    def test_fumble_return_touchdown_is_wiped_by_its_own_off_foul_and_the_live_penalty(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, away_fr={14: "OFF 10", 15: "TD"})
        outcome = kick(game, True, 24, 31, 13, 17, 14, 15)
        assert outcome.touchdown is False
        assert game.state.ball_position == 75  # 100 - 10 - 15

    def test_fumble_return_touchdown_with_a_def_foul_is_still_wiped_by_the_returners_earlier_foul(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, away_fr={14: "DEF 10", 15: "TD"})
        outcome = kick(game, True, 24, 31, 13, 17, 14, 15)
        assert outcome.touchdown is False
        assert game.state.away_score == 0
        assert game.state.ball_position == 85  # Scoring team's foul: enforced from the goal line.

    def test_offsetting_fouls_on_the_fumble_return_nullify_the_kick_and_rekick(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17", 12: "25"}, away_fr={14: "DEF 10", 15: "OFF 10"})
        game.state.home_chart.special_teams.kickoff[11] = "50"
        time_before = game.state.time_remaining
        outcome = kick(game, True, 24, 31, 13, 17, 14, 15, 11, 12)  # Nullified, then the re-kick.
        assert game.state.ball_position == 40  # Re-kick lands at the 15, returned 25.
        assert game.state.away_stats.penalties == 0 and game.state.away_stats.fumbles_lost == 0
        assert outcome.pending_penalty_decision is False
        assert round((time_before - game.state.time_remaining) * 60) == 18  # 10 nullified + 8 re-kick


class TestFumbleReturnsByTheKickingTeam:
    """OFF 15 on the return, fumble at AWAY 22 (= HOME 78), lost on 37 → HOME's fumble return."""

    def test_recovery_and_return_is_offered_against_the_live_penalty(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, home_fr={14: "20"})
        pending = kick(game, True, 24, 31, 13, 37, 14)
        assert pending.pending_penalty_decision is True
        choice = pending.penalty_choice
        assert choice.kick_phase == "return_fumble"
        assert "AWAY 2" in choice.play_result_preview  # HOME at 98 after the return.
        assert "AWAY 7" in choice.penalty_options[0].result_preview
        with patch("paydirt.game_engine.random.uniform", return_value=8):
            outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 98
        assert outcome.turnover is True
        assert 'FR:14→"20"' in outcome.description

    def test_fumble_return_touchdown_may_be_kept(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, home_fr={14: "TD"})
        pending = kick(game, True, 24, 31, 13, 37, 14)
        assert "TOUCHDOWN" in pending.penalty_choice.play_result_preview
        assert cpu_should_accept_penalty(pending, is_human_offense=True, human_is_home=False)[0] is True
        with patch("paydirt.game_engine.random.uniform", return_value=8):
            outcome = game.apply_kickoff_penalty_decision(pending, accept_penalty=False)
        assert outcome.touchdown is True
        assert game.state.home_score == 6

    def test_kr_fr_fr_back_to_the_returner_assesses_the_live_penalty(self) -> None:
        # HOME's fumble return fumbles at HOME 86 (= AWAY 14) and AWAY recovers (30).
        game = chain_game({31: "OFF 15", 13: "F + 17"}, home_fr={14: "F + 8"})
        outcome = kick(game, True, 24, 31, 13, 37, 14, 30)
        assert outcome.pending_penalty_decision is False
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 7  # Half the distance from the 14.
        assert game.state.away_stats.penalties == 1
        assert game.state.home_stats.fumbles_lost == 1 and game.state.away_stats.fumbles_lost == 1

    def test_kr_fr_fr_kept_by_the_kicking_team_is_still_its_choice(self) -> None:
        game = chain_game({31: "OFF 15", 13: "F + 17"}, home_fr={14: "F + 8"})
        pending = kick(game, True, 24, 31, 13, 37, 14, 20)  # HOME recovers its own fumble at 86.
        assert pending.pending_penalty_decision is True
        assert "AWAY 14" in pending.penalty_choice.play_result_preview


class TestInterceptionChains:
    def test_ir_fr(self) -> None:
        game = game_with_return_chart({35: "F + 29"}, returning_home=False)
        game.state.home_chart.special_teams.interception_return.clear()
        game.state.home_chart.special_teams.interception_return[14] = "20"
        game.state.ball_position = 80
        outcome = run(game, interception(), 35, 37, 14)  # AWAY fumbles at its 42 = HOME 58; +20.
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 78
        assert 'FR:14→"20"' in outcome.description
        assert game.state.away_stats.fumbles_lost == 1

    def test_ir_fr_fr(self) -> None:
        game = game_with_return_chart({35: "F + 29"}, returning_home=False)
        game.state.home_chart.special_teams.interception_return.clear()
        game.state.home_chart.special_teams.interception_return[14] = "F + 8"
        game.state.ball_position = 80
        run(game, interception(), 35, 37, 14, 30)  # HOME fumbles at 66 and loses it (30).
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 34
        assert game.state.home_stats.fumbles_lost == 1 and game.state.away_stats.fumbles_lost == 1

    def test_ir_off_foul_fumble_lost_fr_keeps_the_recovery_automatically(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "F + 29"}, returning_home=False)
        game.state.home_chart.special_teams.interception_return.clear()
        game.state.home_chart.special_teams.interception_return[14] = "20"
        game.state.ball_position = 80
        outcome = run(game, interception(), 35, 20, 37, 14)
        assert outcome.pending_penalty_decision is False
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 78
        assert "declined" in outcome.description.lower()

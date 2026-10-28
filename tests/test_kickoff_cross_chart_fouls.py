"""Kick/return fouls identify teams before offsetting or enforcing a foul."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from tests.game_fixtures import make_sample_game


def kickoff_game(kicking_home: bool, kick_foul: str, return_foul: str) -> PaydirtGameEngine:
    game = make_sample_game()
    kicker = game.state.home_chart if kicking_home else game.state.away_chart
    receiver = game.state.away_chart if kicking_home else game.state.home_chart
    kicker.special_teams.kickoff.update({10: kick_foul, 11: "60", 24: "60"})
    receiver.special_teams.kickoff_return.update({12: return_foul, 13: "20", 25: "20"})
    game.state.time_remaining = 8
    return game


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("kind", ["OFF", "DEF"])
@pytest.mark.parametrize("accept", [False, True])
def test_same_team_fouls_offer_rekick_or_resolved_return(
    kicking_home: bool, kind: str, accept: bool,
) -> None:
    game = kickoff_game(kicking_home, f"{kind} 10", f"{kind} 15")
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Kick"), (11, "Distance"), (12, "Return")]) as dice:
        pending = game.kickoff(kicking_home=kicking_home)
    assert dice.call_count == 3
    assert pending.pending_penalty_decision
    # Kickoff consumers consistently treat the receiving team as offense.
    assert pending.penalty_choice.offended_team == ("defense" if kind == "OFF" else "offense")
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert game.state.time_remaining == 8
    rolls = [(24, "Rekick"), (25, "Fresh return")] if accept else [(13, "Return reroll")]
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.apply_kickoff_penalty_decision(pending, accept)
    assert dice.call_count == len(rolls)
    assert not outcome.pending_penalty_decision
    assert game.state.is_home_possession is (not kicking_home)
    expected_spot = (15 if kind == "OFF" else 35) if accept else (10 if kind == "OFF" else 40)
    assert game.state.ball_position == expected_spot
    fouling_home = not kicking_home if kind == "OFF" else kicking_home
    stats = game.state.home_stats if fouling_home else game.state.away_stats
    other = game.state.away_stats if fouling_home else game.state.home_stats
    assert (stats.penalties, stats.penalty_yards) == (1, 10 if accept else 15)
    assert other.penalties == 0
    assert len(game.play_log) == 1
    assert not hasattr(game, "_pending_kickoff_penalty_state")
    assert 'KO:10→"' in outcome.description
    assert 'KO reroll:11→"60"' in outcome.description
    assert 'RT:12→"' in outcome.description
    assert "P:" not in outcome.description
    assert "R:" not in outcome.description


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("kick_kind,return_kind", [("OFF", "DEF"), ("DEF", "OFF")])
def test_opposite_team_cross_chart_fouls_actually_rekick(
    kicking_home: bool, kick_kind: str, return_kind: str,
) -> None:
    game = kickoff_game(kicking_home, f"{kick_kind} 10", f"{return_kind} 15")
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (10, "Kick"), (11, "Distance"), (12, "Return"), (24, "Rekick"), (25, "Fresh return"),
        ]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff(kicking_home=kicking_home)
    assert dice.call_count == 5
    assert not outcome.pending_penalty_decision
    assert game.state.is_home_possession is (not kicking_home)
    assert game.state.ball_position == 25
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert round((8 - game.state.time_remaining) * 60) == 18
    assert len(game.play_log) == 1
    assert "OFFSETTING" in outcome.description
    for trace in ('KO:10→"', 'KO reroll:11→"60"', 'RT:12→"', 'KO:24→"60"', 'RT:25→"20"'):
        assert trace in outcome.description
    assert "P:" not in outcome.description
    assert "R:" not in outcome.description
    assert outcome.field_position_after != "pending"


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("kick_kind,return_kind,spot", [("DEF", "OFF", 2), ("OFF", "DEF", 20)])
def test_opposite_team_five_vs_fifteen_retains_exception_and_counts_fouler(
    kicking_home: bool, kick_kind: str, return_kind: str, spot: int,
) -> None:
    game = kickoff_game(kicking_home, f"{kick_kind} 5", f"{return_kind} 15")
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Kick"), (11, "Distance"), (12, "Return")]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff(kicking_home=kicking_home)
    assert dice.call_count == 3
    assert game.state.is_home_possession is (not kicking_home)
    assert game.state.ball_position == spot
    fouling_home = not kicking_home if return_kind == "OFF" else kicking_home
    stats = game.state.home_stats if fouling_home else game.state.away_stats
    other = game.state.away_stats if fouling_home else game.state.home_stats
    assert (stats.penalties, stats.penalty_yards) == (1, 3 if return_kind == "OFF" else 15)
    assert other.penalties == 0
    assert outcome.penalty_applied
    assert "NFL Rule 14-5-1" in outcome.description
    assert 'KO:10→"' in outcome.description
    assert 'KO reroll:11→"60"' in outcome.description
    assert f'RT:12→"{return_kind} 15"' in outcome.description
    assert "P:" not in outcome.description
    assert "R:" not in outcome.description
    assert outcome.result.kickoff_return_dice == 12


@pytest.mark.parametrize("kind", ["OFF", "DEF"])
def test_same_team_five_vs_fifteen_does_not_trigger_opposite_team_exception(kind: str) -> None:
    game = kickoff_game(True, f"{kind} 5", f"{kind} 15")
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Kick"), (11, "Distance"), (12, "Return")]):
        outcome = game.kickoff()
    assert outcome.pending_penalty_decision
    assert "NFL Rule 14-5-1" not in outcome.description


def test_plain_kickoff_control() -> None:
    game = kickoff_game(True, "60", "20")
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Kick"), (12, "Return")]),
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff()
    assert not outcome.pending_penalty_decision
    assert not game.state.is_home_possession
    assert game.state.ball_position == 25


@pytest.mark.parametrize("cell,spot,td", [("TD", 85, False), ("F + 5", 5, False)])
def test_same_team_foul_decline_preserves_td_or_fumble_reroll(cell: str, spot: int, td: bool) -> None:
    game = kickoff_game(True, "OFF 10", "OFF 15")
    game.state.away_chart.special_teams.kickoff_return[13] = cell
    game.state.away_chart.peripheral.fumble_recovered_range = (10, 27)
    rolls = [(10, "Kick"), (11, "Distance"), (12, "Return"), (13, "Return reroll")]
    if cell.startswith("F"):
        rolls.append((20, "Retained recovery"))
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        pending = game.kickoff()
        outcome = game.apply_kickoff_penalty_decision(pending, False)
    assert dice.call_count == len(rolls)
    assert game.state.ball_position == spot
    assert outcome.touchdown is td
    assert game.state.away_stats.fumbles_lost == 0
    assert game.state.away_stats.penalties == 1
    assert 'RT reroll:13→"' in outcome.description
    if cell.startswith("F"):
        assert 'R:20→"recovered"' in outcome.description


def test_return_offset_after_same_team_kick_foul_retains_original_trace() -> None:
    game = kickoff_game(True, "OFF 10", "OFF 15")
    game.state.away_chart.special_teams.kickoff_return[13] = "DEF 10"
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (10, "Kick"), (11, "Distance"), (12, "Return"), (13, "Offset"), (24, "Rekick"), (25, "Fresh return"),
        ]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        pending = game.kickoff()
        outcome = game.apply_kickoff_penalty_decision(pending, False)
    assert dice.call_count == 6
    assert not game.state.is_home_possession
    assert game.state.ball_position == 25
    assert round((8 - game.state.time_remaining) * 60) == 18
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert 'KO:10→"OFF 10"' in outcome.description
    assert 'KO reroll:11→"60"' in outcome.description
    assert 'RT:12→"OFF 15"' in outcome.description
    assert 'RT reroll:13→"DEF 10"' in outcome.description
    assert "OFFSETTING" in outcome.description
    assert len(game.play_log) == 1


@pytest.mark.parametrize("kick_foul,return_foul,spot,fouling_home", [
    ("OFF 15", "DEF 5", 2, False), ("DEF 15", "OFF 5", 20, True),
])
def test_five_vs_fifteen_counts_kick_chart_fifteen_yard_foul(
    kick_foul: str, return_foul: str, spot: int, fouling_home: bool,
) -> None:
    game = kickoff_game(True, kick_foul, return_foul)
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Kick"), (11, "Distance"), (12, "Return")]),
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff()
    assert game.state.ball_position == spot
    assert not game.state.is_home_possession
    stats = game.state.home_stats if fouling_home else game.state.away_stats
    assert stats.penalties == 1
    assert stats.penalty_yards == abs(spot - 5)
    assert outcome.penalty_applied


def test_auto_first_down_kick_foul_does_not_disregard_opposite_five_yard_foul() -> None:
    game = kickoff_game(True, "DEF 15X", "OFF 5")
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (10, "Kick"), (11, "Distance"), (12, "Return"), (24, "Rekick"), (25, "Fresh return"),
        ]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff()
    assert dice.call_count == 5
    assert "OFFSETTING" in outcome.description
    assert game.state.ball_position == 25
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0


def test_auto_first_down_marker_on_kick_penalty_reroll_is_not_lost() -> None:
    game = kickoff_game(True, "OFF 5", "DEF 5")
    game.state.home_chart.special_teams.kickoff[11] = "OFF 15X"
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (10, "Kick"), (11, "Larger foul"), (24, "Distance"), (12, "Return"),
            (24, "Rekick"), (25, "Fresh return"),
        ]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff()
    assert dice.call_count == 6
    assert "OFFSETTING" in outcome.description
    assert 'KO reroll:11→"OFF 15X"' in outcome.description
    assert game.state.ball_position == 25
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0


def test_larger_kick_penalty_reroll_without_x_retains_five_vs_fifteen_exception() -> None:
    game = kickoff_game(True, "OFF 5", "DEF 5")
    game.state.home_chart.special_teams.kickoff[11] = "OFF 15"
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (10, "Kick"), (11, "Larger foul"), (24, "Distance"), (12, "Return"),
            (24, "Unexpected rekick"), (25, "Unexpected return"),
        ]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.kickoff()
    assert dice.call_count == 4
    assert "NFL Rule 14-5-1" in outcome.description
    assert game.state.ball_position == 2
    assert game.state.away_stats.penalties == 1
    assert game.state.away_stats.penalty_yards == 3

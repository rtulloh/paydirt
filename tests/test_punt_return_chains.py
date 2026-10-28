"""Punts use the same return-chart procedure as kickoffs and interceptions."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


def punt_game(cells: dict[int, str], kicking_home: bool = True, kick_foul: str = "") -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = kicking_home
    game.state.ball_position = 25
    game.state.down = 4
    game.state.yards_to_go = 10
    kicker = game.state.home_chart if kicking_home else game.state.away_chart
    receiver = game.state.away_chart if kicking_home else game.state.home_chart
    kicker.special_teams.punt.clear()
    kicker.special_teams.punt.update({24: kick_foul or "40", 25: "40"})
    receiver.special_teams.punt_return.clear()
    receiver.special_teams.punt_return.update(cells)
    for chart in (kicker, receiver):
        chart.peripheral.fumble_recovered_range = (10, 27)
        chart.special_teams.interception_return.clear()
        chart.special_teams.interception_return[15] = "2"
    return game


def punt(game: PaydirtGameEngine, *rolls: int) -> PlayOutcome:
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(roll, f"Roll {roll}") for roll in rolls]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=8),
    ):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert dice.call_count == len(rolls)
    return outcome


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("foul,cell,spot,td", [
    ("DEF 10", "60", 97, False),
    ("OFF 15", "TD", 85, False),
    ("DEF 10", "TD", 99, True),
    ("OFF 10", "10", 35, False),
])
def test_punt_return_penalty_rerolls_keep_special_cells(
    kicking_home: bool, foul: str, cell: str, spot: int, td: bool,
) -> None:
    game = punt_game({13: foul, 14: cell}, kicking_home)
    outcome = punt(game, 24, 13, 14)
    assert not outcome.pending_penalty_decision
    assert outcome.touchdown is td
    assert game.state.is_home_possession is (not kicking_home)
    assert game.state.ball_position == spot
    assert (game.state.away_score if kicking_home else game.state.home_score) == (6 if td else 0)
    assert "13" in outcome.description and "14" in outcome.description
    assert cell in outcome.description


@pytest.mark.parametrize("kicking_home", [False, True])
@pytest.mark.parametrize("recovery", [17, 20, 30, 37])
def test_punt_return_fumble_consumes_recovery_and_optional_return(kicking_home: bool, recovery: int) -> None:
    game = punt_game({13: "F + 5"}, kicking_home)
    rolls = [24, 13, recovery] + ([15] if recovery in (17, 37) else [])
    outcome = punt(game, *rolls)
    recovered = recovery < 28
    advance = 2 if recovery in (17, 37) else 0
    assert game.state.is_home_possession is (not kicking_home if recovered else kicking_home)
    assert game.state.ball_position == (40 if recovered else 60) + advance
    receiver_stats = game.state.away_stats if kicking_home else game.state.home_stats
    assert receiver_stats.fumbles_lost == (0 if recovered else 1)
    assert receiver_stats.turnovers == (0 if recovered else 1)
    assert f"R:{recovery}" in outcome.description
    assert not outcome.touchdown
    assert not outcome.safety


@pytest.mark.parametrize("recovery", [20, 30])
@pytest.mark.parametrize("cell", ["F + 65", "F - 40"])
def test_punt_return_end_zone_fumble_uses_shared_rules(recovery: int, cell: str) -> None:
    game = punt_game({13: cell})
    outcome = punt(game, 24, 13, recovery)
    own_end_zone = cell == "F - 40"
    assert outcome.touchdown is (recovery == 30 if own_end_zone else recovery == 20)
    assert outcome.safety is (own_end_zone and recovery == 20)
    assert "end zone" in outcome.description.lower()
    if not own_end_zone and recovery == 30:
        assert game.state.ball_position == 20
        assert "TOUCHBACK" in outcome.description


def test_keep_return_after_kick_chart_foul_cannot_award_penalty_touchdown() -> None:
    game = punt_game({13: "60"}, kick_foul="OFF 10")
    pending = punt(game, 24, 25, 13)
    assert pending.pending_penalty_decision
    assert game.state.home_score == game.state.away_score == 0
    assert "TOUCHDOWN" not in pending.penalty_choice.penalty_options[1].result_preview
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_punt_penalty_decision(pending, True, 1)
    assert not outcome.touchdown
    assert game.state.ball_position == 97
    assert game.state.home_stats.penalty_yards == 2


@pytest.mark.parametrize("accept", [False, True])
def test_kick_chart_decision_keeps_or_discards_resolved_return_chain(accept: bool) -> None:
    game = punt_game({13: "F + 5"}, kick_foul="DEF 5")
    pending = punt(game, 24, 25, 13, 20)
    assert pending.pending_penalty_decision
    assert game.state.is_home_possession
    assert game.state.ball_position == 25
    assert game.state.away_stats.fumbles_lost == 0
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("do not reroll a resolved return")):
        outcome = game.apply_punt_penalty_decision(pending, accept)
    assert not outcome.pending_penalty_decision
    assert game.state.is_home_possession is accept
    assert game.state.ball_position == (30 if accept else 40)
    assert game.state.away_stats.fumbles_lost == 0


def test_plain_punt_control() -> None:
    game = punt_game({13: "10"})
    outcome = punt(game, 24, 13)
    assert not outcome.touchdown
    assert not game.state.is_home_possession
    assert game.state.ball_position == 45


@pytest.mark.parametrize("foul,recovery,expected_spot,lost", [
    ("OFF 15", 20, 25, False), ("OFF 15", 30, 60, True),
    ("DEF 10", 20, 50, False), ("DEF 10", 30, 50, False),
])
def test_penalty_reroll_fumble_preserves_recovery_and_live_foul(
    foul: str, recovery: int, expected_spot: int, lost: bool,
) -> None:
    game = punt_game({13: foul, 14: "F + 5"})
    outcome = punt(game, 24, 13, 14, recovery)
    assert game.state.is_home_possession is lost
    assert game.state.ball_position == expected_spot
    assert game.state.away_stats.fumbles_lost == int(lost)
    assert f"R:{recovery}" in outcome.description
    assert "F + 5" in outcome.description
    assert len(game.play_log) == 1


def test_offsetting_return_fouls_rekick_with_ten_second_runoff() -> None:
    game = punt_game({13: "OFF 10", 14: "DEF 15", 16: "10"})
    game.state.time_remaining = 8
    outcome = punt(game, 24, 13, 14, 25, 16)
    assert not game.state.is_home_possession
    assert game.state.ball_position == 45
    assert round((8 - game.state.time_remaining) * 60) == 18
    assert "OFFSETTING" in outcome.description
    assert "13" in outcome.description and "14" in outcome.description
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert len(game.play_log) == 1


def test_nested_punt_fumble_returns_credit_each_lost_fumble() -> None:
    game = punt_game({13: "F + 5"})
    game.state.home_chart.special_teams.interception_return[15] = "F + 5"
    outcome = punt(game, 24, 13, 37, 15, 30)
    assert not game.state.is_home_possession
    assert game.state.ball_position == 35
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 1
    assert "R:37" in outcome.description and "R:30" in outcome.description
    assert len(game.play_log) == 1


def test_short_drop_negative_return_keeps_raw_chart_fact() -> None:
    game = punt_game({13: "-5"})
    game.state.ball_position = 3
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(24, "Punt"), (13, "Return")]):
        outcome = game._handle_punt(short_drop=True)
    assert game.state.ball_position == 57
    assert outcome.result.punt_return_result == "-5"
    assert 'Ret:13→"-5"' in outcome.description

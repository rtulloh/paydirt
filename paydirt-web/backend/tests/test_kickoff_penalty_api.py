"""Kickoff return penalties in the web API: assessed automatically; the recovered-fumble choice is offered."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


def _start(client: TestClient, human_is_home: bool, human_kicks: bool, reroll_cell: str = "30") -> tuple[str, dict]:
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads", "season": "2026", "play_as_home": human_is_home,
    })
    game_id = response.json()["game_id"]
    game = games[game_id]
    engine = game["engine"]
    game["is_kickoff"] = True
    game["human_is_home"] = human_is_home
    kicking_home = human_is_home if human_kicks else not human_is_home
    engine.state.is_home_possession = kicking_home
    kicker = engine.state.home_chart if kicking_home else engine.state.away_chart
    receiver = engine.state.away_chart if kicking_home else engine.state.home_chart
    kicker.special_teams.kickoff.clear()
    receiver.special_teams.kickoff_return.clear()
    receiver.peripheral.fumble_recovered_range = (10, 27)
    kicker.special_teams.kickoff[24] = "60"
    receiver.special_teams.kickoff_return.update({31: "OFF 15", 13: reroll_cell})
    return game_id, game


def rolls(*values):
    return [(value, f"Roll{value}") for value in values]


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("human_kicks", [True, False])
def test_return_penalty_is_assessed_without_a_prompt(human_is_home: bool, human_kicks: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_kicks)
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            assert kicked["result"]["pending_penalty_decision"] is False
            assert kicked["result"]["penalty_choice"] is None
            assert kicked["game_state"]["ball_position"] == 20
            assert kicked["game_state"]["is_kickoff"] is False
            kicking_home = human_is_home if human_kicks else not human_is_home
            assert engine.state.is_home_possession is not kicking_home
            assert kicked["game_state"]["player_offense"] is (not human_kicks)
        finally:
            client.delete(f"/api/game/{game_id}")


def test_human_kicker_chooses_after_recovering_the_reroll_fumble() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_kicks=True, reroll_cell="F + 17")
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13, 30)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            result = kicked["result"]
            assert result["pending_penalty_decision"] is True
            assert result["penalty_choice"]["kick_phase"] == "return_fumble"
            assert result["penalty_choice"]["offended_team"] == "defense"
            assert "22" in result["penalty_choice"]["play_result_preview"]
            assert "7" in result["penalty_choice"]["penalty_options"][0]["result_preview"]
            with patch("paydirt.game_engine.random.uniform", return_value=8):
                decided = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": False, "penalty_index": 0,
                }).json()
            assert decided["game_state"]["possession"] == "home"
            assert decided["game_state"]["ball_position"] == 78
            assert engine.state.is_home_possession is True
        finally:
            client.delete(f"/api/game/{game_id}")


def test_cpu_kicker_keeps_the_recovery_immediately() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_kicks=False, reroll_cell="F + 17")
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13, 30)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            assert kicked["result"]["pending_penalty_decision"] is False
            assert engine.state.is_home_possession is False  # The CPU kicker (away) keeps the ball.
            assert kicked["game_state"]["ball_position"] == 78
        finally:
            client.delete(f"/api/game/{game_id}")

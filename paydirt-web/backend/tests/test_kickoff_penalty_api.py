"""Kickoff return-chart penalties reach the browser as a decision (RULE-013)."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


def _start(client: TestClient, human_is_home: bool, human_kicks: bool) -> tuple[str, dict]:
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
    kicker.special_teams.kickoff[24] = "60"
    receiver.special_teams.kickoff_return.update({31: "OFF 15", 13: "30"})
    return game_id, game


def rolls(*values):
    return [(value, f"Roll{value}") for value in values]


@pytest.mark.parametrize("human_is_home", [True, False])
def test_human_kicker_gets_the_choice_and_may_accept(human_is_home: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_kicks=True)
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            result = kicked["result"]
            assert result["pending_penalty_decision"] is True
            assert result["penalty_choice"] is not None
            assert result["penalty_choice"]["offended_team"] == "defense"
            assert result["penalty_choice"]["penalty_options"][0]["penalty_type"] == "OFF"
            assert "20" in result["penalty_choice"]["penalty_options"][0]["result_preview"]
            assert "35" in result["penalty_choice"]["play_result_preview"]
            assert kicked["game_state"]["is_kickoff"] is False
            # Nothing applied yet.
            assert engine.state.is_home_possession is human_is_home
            with patch("paydirt.game_engine.random.uniform", return_value=8):
                decided = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": True, "penalty_index": 0,
                }).json()
            assert decided["result"]["pending_penalty_decision"] is False
            assert decided["game_state"]["ball_position"] == 20
            assert decided["game_state"]["possession"] == ("away" if human_is_home else "home")
            assert decided["game_state"]["is_kickoff"] is False
            assert decided["game_state"]["player_offense"] is False
        finally:
            client.delete(f"/api/game/{game_id}")


def test_human_kicker_may_decline() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_kicks=True)
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            assert kicked["result"]["pending_penalty_decision"] is True
            with patch("paydirt.game_engine.random.uniform", return_value=8):
                decided = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": False, "penalty_index": 0,
                }).json()
            assert decided["game_state"]["ball_position"] == 35
            assert decided["game_state"]["possession"] == "away"
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("human_is_home", [True, False])
def test_cpu_kicker_decides_immediately_when_the_human_receives(human_is_home: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_kicks=False)
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            result = kicked["result"]
            assert result["pending_penalty_decision"] is False
            assert result["penalty_choice"] is None
            assert kicked["game_state"]["ball_position"] == 20, "the CPU kicker accepts the receiving-team foul"
            assert engine.state.is_home_possession is human_is_home
            assert kicked["game_state"]["player_offense"] is True
            assert kicked["game_state"]["is_kickoff"] is False
            state = client.get(f"/api/game/state/{game_id}").json()
            assert state["ball_position"] == 20
        finally:
            client.delete(f"/api/game/{game_id}")

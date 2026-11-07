"""CPU punt decisions must preserve the chosen keep-return option through the API."""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


@pytest.mark.parametrize("kicking_home", [True, False])
@pytest.mark.parametrize("force_keep_choice", [True, False])
def test_cpu_receiver_takes_punt_at_own_six_via_execute(
    kicking_home: bool, force_keep_choice: bool,
) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": kicking_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            game = games[game_id]
            game["is_kickoff"] = False
            game["human_plays_offense"] = True
            engine = game["engine"]
            engine.state.is_home_possession = kicking_home
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 50, 4, 10
            engine.state.possession_team.special_teams.punt = {10: "OFF 5", 11: "49"}
            engine.state.defense_team.special_teams.punt_return = {20: "0"}
            choice = (patch("routes.cpu_should_accept_penalty", return_value=(False, 1))
                      if force_keep_choice else nullcontext())
            with choice, patch("paydirt.game_engine.roll_chart_dice", side_effect=[
                (10, "Roll10"), (11, "Roll11"), (20, "Roll20"),
            ]):
                response = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "P", "cpu_play": "A",
                })
            assert response.status_code == 200
            data = response.json()
            assert engine.state.is_home_possession is not kicking_home
            assert data["game_state"]["ball_position"] == 6
            assert not data["game_state"]["player_offense"]
            assert data["result"]["new_down"] == 1
            assert data["result"]["new_yards_to_go"] == 10
            assert not data["result"]["pending_penalty_decision"]
            assert "declines penalty" not in data["result"]["description"]
            assert not hasattr(engine, "_pending_punt_state")
            assert engine.state.defense_stats.penalties == 1
            assert engine.state.defense_stats.penalty_yards == 5
        finally:
            client.delete(f"/api/game/{game_id}")

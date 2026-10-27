"""Declining a kicking-team foul must keep the unpenalized punt and return."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games

from paydirt.play_resolver import PlayType


@pytest.mark.parametrize("kicking_is_home", [True, False])
@pytest.mark.parametrize("penalty_index", [0, 1])
def test_decline_offensive_punt_penalty_via_api(kicking_is_home: bool, penalty_index: int) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": not kicking_is_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            game = games[game_id]
            game["is_kickoff"] = False
            game["human_plays_offense"] = False
            game["human_is_home"] = not kicking_is_home
            engine = game["engine"]
            engine.state.is_home_possession = kicking_is_home
            engine.state.ball_position = 24
            engine.state.down = 4
            engine.state.yards_to_go = 1
            engine.state.possession_team.special_teams.punt.update({14: "OFF 10", 10: "34"})
            engine.state.defense_team.special_teams.punt_return[10] = "2"
            with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
                (14, "B1+W3+W0=14"), (10, "B1+W0+W0=10"), (10, "B1+W0+W0=10"),
            ]):
                outcome = engine.run_play(PlayType.PUNT, None)
            engine._last_play_outcome = outcome

            response = client.post("/api/game/penalty-decision", json={
                "game_id": game_id, "accept_penalty": False, "penalty_index": penalty_index,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["new_ball_position"] == 44
            assert data["result"]["new_down"] == 1
            assert data["result"]["new_yards_to_go"] == 10
            assert data["result"]["description"].startswith("Receiving team declines penalty.")
            assert data["game_state"]["player_offense"]
            assert engine.state.is_home_possession != kicking_is_home
            assert not hasattr(engine, "_pending_punt_state")
        finally:
            client.delete(f"/api/game/{game_id}")

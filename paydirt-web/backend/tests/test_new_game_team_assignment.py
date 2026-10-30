"""The requested player team keeps its identity on either side of a new game."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games


@pytest.mark.parametrize("play_as_home", [True, False])
@pytest.mark.parametrize("random_opponent", [True, False])
def test_new_game_keeps_player_and_cpu_team_assignments(
    play_as_home: bool, random_opponent: bool
) -> None:
    with TestClient(app) as client:
        request = {
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": play_as_home,
        }
        if not random_opponent:
            request["opponent_team"] = "Thunderhawks"

        def choose_random_opponent(options):
            if options == ["Thunderhawks"]:
                return "Thunderhawks"
            return True

        with patch("routes.random.choice", side_effect=choose_random_opponent):
            response = client.post("/api/game/new", json=request)

        assert response.status_code == 200
        data = response.json()
        state = data["game_state"]
        game_id = data["game_id"]
        try:
            expected_home = "Ironclads" if play_as_home else "Thunderhawks"
            expected_away = "Thunderhawks" if play_as_home else "Ironclads"
            assert state["home_team"]["id"] == expected_home
            assert state["away_team"]["id"] == expected_away
            assert state["human_team_id"] == "Ironclads"
            assert state["cpu_team_id"] == "Thunderhawks"
            assert state["human_is_home"] is play_as_home

            player_has_possession = state["possession"] == (
                "home" if play_as_home else "away"
            )
            assert state["player_offense"] is player_has_possession
        finally:
            client.delete(f"/api/game/{game_id}")

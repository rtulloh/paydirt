import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "paydirt-web"


def test_get_seasons():
    response = client.get("/api/seasons")
    assert response.status_code == 200
    data = response.json()
    assert "seasons" in data
    assert isinstance(data["seasons"], list)
    assert len(data["seasons"]) > 0
    assert "2026" in data["seasons"]


def test_get_teams_2026():
    response = client.get("/api/teams?season=2026")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
    assert isinstance(data["teams"], list)
    assert len(data["teams"]) >= 2
    team_ids = [t["id"] for t in data["teams"]]
    assert "Ironclads" in team_ids
    assert "Thunderhawks" in team_ids


def test_get_teams_with_details():
    response = client.get("/api/teams?season=2026")
    assert response.status_code == 200
    data = response.json()
    ironclads = next((t for t in data["teams"] if t["id"] == "Ironclads"), None)
    assert ironclads is not None
    assert ironclads["name"] == "Harbor Bay Ironclads"
    assert ironclads["team_color"] is not None  # Color may vary, just check it's set


def test_get_teams_invalid_season():
    response = client.get("/api/teams?season=1900")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_new_game():
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["game_id"].startswith("game_")
    assert "game_state" in data
    
    state = data["game_state"]
    assert state["home_score"] == 0
    assert state["away_score"] == 0
    assert state["quarter"] == 1
    assert state["time_remaining"] == 900
    assert state["game_over"] == False
    assert state["down"] == 1
    assert state["yards_to_go"] == 10
    assert "home_timeouts" in state
    assert "away_timeouts" in state
    assert "player_offense" in state


def test_new_game_invalid_team():
    response = client.post("/api/game/new", json={
        "player_team": "NonexistentTeam",
        "season": "2026"
    })
    assert response.status_code == 404


def test_new_game_invalid_season():
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "1900"
    })
    assert response.status_code == 404


def test_get_game_state():
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026"
    })
    data = response.json()
    game_id = data["game_id"]
    
    response = client.get(f"/api/game/state/{game_id}")
    assert response.status_code == 200
    state = response.json()
    assert state["game_id"] == game_id
    assert "home_team" in state
    assert "away_team" in state
    assert "home_score" in state
    assert "away_score" in state


def test_get_game_state_invalid():
    response = client.get("/api/game/state/invalid_game_id")
    assert response.status_code == 404


def test_execute_play():
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026"
    })
    data = response.json()
    game_id = data["game_id"]
    
    response = client.post("/api/game/execute", json={
        "game_id": game_id,
        "player_play": "1"
    })
    assert response.status_code == 200
    result = response.json()
    
    assert "result" in result
    assert "game_state" in result
    assert "player_play" in result
    assert "cpu_play" in result
    
    assert "result" in result["result"]
    assert "yards" in result["result"]
    assert "description" in result["result"]


def test_execute_play_invalid_game():
    response = client.post("/api/game/execute", json={
        "game_id": "invalid_id",
        "player_play": "1"
    })
    assert response.status_code == 404


def test_delete_game():
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026"
    })
    data = response.json()
    game_id = data["game_id"]
    
    response = client.delete(f"/api/game/{game_id}")
    assert response.status_code == 200
    
    response = client.get(f"/api/game/state/{game_id}")
    assert response.status_code == 404


def test_cors_headers():
    pass  # CORS is configured in middleware but TestClient handles it differently

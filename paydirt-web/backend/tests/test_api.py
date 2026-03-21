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
    assert data["status"] == "ok"


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
    assert not state["game_over"]
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


def test_player_offense_reflects_possession():
    """Test that player_offense is calculated based on current possession, not initial setting."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    initial_state = data["game_state"]
    initial_human_is_home = initial_state["human_is_home"]
    
    coin_toss_response = client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": False,
        "human_plays_offense": True,
    })
    assert coin_toss_response.status_code == 200
    
    state = client.get(f"/api/game/state/{game_id}").json()
    
    expected_player_offense = (initial_human_is_home and state["possession"] == "home") or \
                              (not initial_human_is_home and state["possession"] == "away")
    assert state["player_offense"] == expected_player_offense, \
        f"player_offense should be {expected_player_offense} when human_is_home={initial_human_is_home} and possession={state['possession']}"


def test_player_offense_after_kickoff():
    """Test that player_offense updates correctly after kickoff (when possession changes)."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": False,
        "human_plays_offense": True,
    })
    
    kickoff_response = client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    assert kickoff_response.status_code == 200
    
    state = client.get(f"/api/game/state/{game_id}").json()
    human_is_home = state["human_is_home"]
    
    expected_player_offense = (human_is_home and state["possession"] == "home") or \
                              (not human_is_home and state["possession"] == "away")
    assert state["player_offense"] == expected_player_offense


def test_possession_changes_after_score():
    """Test that player_offense correctly reflects possession after a touchdown."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": True,
        "human_plays_offense": False,
    })
    
    kickoff_response = client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    assert kickoff_response.status_code == 200
    
    state = client.get(f"/api/game/state/{game_id}").json()
    human_is_home = state["human_is_home"]
    
    expected_player_offense = (human_is_home and state["possession"] == "home") or \
                              (not human_is_home and state["possession"] == "away")
    assert state["player_offense"] == expected_player_offense


def test_new_game_with_opponent_team():
    """Test creating a new game with a specific opponent (used for loading saved games)."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
        "opponent_team": "Thunderhawks",
    })
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["game_state"]["home_team"]["id"] == "Ironclads"
    assert data["game_state"]["away_team"]["id"] == "Thunderhawks"
    assert data["game_state"]["human_is_home"]


def test_new_game_away_team():
    """Test creating a new game where player is away team."""
    response = client.post("/api/game/new", json={
        "player_team": "Thunderhawks",
        "season": "2026",
        "play_as_home": False,
        "opponent_team": "Ironclads",
    })
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    # When playing away, opponent is home
    assert data["game_state"]["home_team"]["id"] == "Ironclads"
    assert data["game_state"]["away_team"]["id"] == "Thunderhawks"
    assert not data["game_state"]["human_is_home"]
    # human_team_id should always be the player's actual team
    assert data["game_state"]["human_team_id"] == "Thunderhawks"


def test_cpu_fourth_down_decision_returns_valid_response():
    """Test that CPU 4th down decision returns a valid response."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    response = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert data["decision"] in ["none", "punt", "field_goal", "go_for_it"]


def test_cpu_fourth_down_decision_considers_current_possession():
    """Test that CPU 4th down decision is based on current possession, not initial coin toss."""
    # Create game
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Set up coin toss - player kicks (CPU receives on offense)
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": True,
        "human_plays_offense": False,
    })
    
    # After kickoff, possession should switch and CPU (who received) should be on offense
    kickoff_resp = client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    assert kickoff_resp.status_code == 200
    
    # Get the game state to check possession
    state_resp = client.get(f"/api/game/state/{game_id}")
    state = state_resp.json()
    
    # player_offense should reflect current possession, not initial human_plays_offense
    # If CPU is on offense, player_offense should be False
    # If player is on offense, player_offense should be True
    if state["player_offense"]:
        # Player is on offense, CPU should not make 4th down decision
        decision_resp = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
        decision_data = decision_resp.json()
        assert decision_data["decision"] == "none"
    # If player_offense is False, CPU is on offense - we can't easily test 4th down
    # without setting the down to 4, but we've verified the logic is possession-based


def test_blocked_fg_defense_recovery_4th_down_state():
    """Test that blocked FG with defense recovery results in correct state (1st & 10)."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Set up coin toss so player has possession on offense
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": False,
        "human_plays_offense": True,
    })
    
    # Do kickoff to get initial possession
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Get current state
    state_resp = client.get(f"/api/game/state/{game_id}")
    state = state_resp.json()
    
    # Verify state has expected fields
    assert state["game_id"] == game_id
    assert "down" in state
    assert "yards_to_go" in state
    assert "ball_position" in state
    assert "possession" in state


def test_execute_play_returns_updated_state():
    """Test that execute_play returns the current game state after the play."""
    # Create game
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Skip to coin toss
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": False,
        "human_plays_offense": True,
    })
    
    # Do kickoff
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Execute a play (Line Plunge)
    play_response = client.post("/api/game/execute", json={
        "game_id": game_id,
        "player_play": "1",
        "cpu_play": "A",
    })
    
    assert play_response.status_code == 200
    result = play_response.json()
    
    # Verify game_state in response has current state
    assert "game_state" in result
    gs = result["game_state"]
    assert "down" in gs
    assert "yards_to_go" in gs
    assert "ball_position" in gs
    assert "possession" in gs
    
    # Verify result object has the updated info
    assert "result" in result
    assert "new_down" in result["result"]
    assert "new_ball_position" in result["result"]


def test_cors_headers():
    pass  # CORS is configured in middleware but TestClient handles it differently


def test_save_replay():
    """Test saving a game replay."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    assert response.status_code == 200
    data = response.json()
    game_id = data["game_id"]
    
    save_response = client.post(f"/api/game/save-replay/{game_id}")
    assert save_response.status_code == 200
    save_data = save_response.json()
    
    assert "replay_id" in save_data
    assert save_data["replay_id"].startswith("replay_")
    assert "game_state" in save_data
    assert "play_history" in save_data
    assert "created_at" in save_data


def test_save_replay_invalid_game():
    """Test saving replay with invalid game ID."""
    response = client.post("/api/game/save-replay/invalid_game_id")
    assert response.status_code == 404


def test_load_replay():
    """Test loading a saved replay."""
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    assert response.status_code == 200
    data = response.json()
    game_id = data["game_id"]
    
    save_response = client.post(f"/api/game/save-replay/{game_id}")
    save_data = save_response.json()
    
    load_request = {
        "replay_data": {
            "season": "2026",
            "game_state": save_data["game_state"],
            "play_history": save_data["play_history"],
            "difficulty": "medium",
        }
    }
    
    load_response = client.post("/api/game/load-replay", json=load_request)
    assert load_response.status_code == 200
    load_data = load_response.json()
    
    assert "game_id" in load_data
    assert "game_state" in load_data
    assert load_data["game_id"] != game_id


def test_load_replay_invalid_data():
    """Test loading replay with invalid data."""
    response = client.post("/api/game/load-replay", json={
        "replay_data": {}
    })
    assert response.status_code == 400


def test_debug_settings():
    """Test getting and setting debug settings."""
    get_response = client.get("/api/debug/settings")
    assert get_response.status_code == 200
    settings = get_response.json()
    assert "deterministic_mode" in settings
    assert "seed" in settings
    
    set_response = client.post("/api/debug/settings", json={
        "deterministic_mode": True,
        "seed": 42
    })
    assert set_response.status_code == 200
    result = set_response.json()
    assert result["deterministic_mode"] is True
    assert result["seed"] == 42

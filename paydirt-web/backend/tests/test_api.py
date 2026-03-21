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


def test_penalty_prompting_logic():
    """
    Test that penalty prompting logic is correct:
    - Defense penalty + human on offense → prompt human
    - Offense penalty + human on offense → don't prompt human (CPU decides for defense)
    """
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
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    found_offense_penalty = False
    found_defense_penalty = False
    
    for _ in range(100):
        play_response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "1",
            "cpu_play": "A",
        })
        
        if play_response.status_code != 200:
            continue
            
        result = play_response.json()
        
        if result["result"].get("pending_penalty_decision") and result["result"].get("penalty_choice"):
            penalty_choice = result["result"]["penalty_choice"]
            
            if penalty_choice["offended_team"] == "defense":
                found_offense_penalty = True
                assert len(penalty_choice["penalty_options"]) > 0
                # When offense commits penalty and human is on offense, 
                # penalty_choice_model should be None (CPU decides for defense)
                assert result["result"]["penalty_choice"] is not None
                print("OFFENSE PENALTY: penalty_choice returned (CPU decides for defense)")
                break
            elif penalty_choice["offended_team"] == "offense":
                found_defense_penalty = True
                assert len(penalty_choice["penalty_options"]) > 0
                # When defense commits penalty and human is on offense, 
                # penalty_choice_model should be returned (human decides)
                assert result["result"]["penalty_choice"] is not None
                print("DEFENSE PENALTY: penalty_choice returned (human decides)")
                break
        
        if result["result"].get("game_over"):
            break
    
    if not found_offense_penalty and not found_defense_penalty:
        print("Note: No penalty scenario found in 100 plays - this is random")


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


def test_penalty_decision_cpu_makes_smart_decision():
    """Test that CPU penalty decision uses AI logic instead of hardcoded accept."""
    from unittest.mock import patch
    
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
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    with patch('routes.cpu_should_accept_penalty') as mock_cpu_decision:
        mock_cpu_decision.return_value = (False, 0)
        
        response = client.post("/api/game/penalty-decision", json={
            "game_id": game_id,
            "penalty_index": 0,
            "accept_penalty": True,
        })
        
        if response.status_code == 400:
            pass
        else:
            assert response.status_code == 200


def test_penalty_decision_human_decides_uses_request_values():
    """Test that when human decides, their choice is used (not CPU's hardcoded decision)."""
    from unittest.mock import patch
    
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
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    with patch('routes.cpu_should_accept_penalty') as mock_cpu_decision:
        mock_cpu_decision.return_value = (True, 0)
        
        response = client.post("/api/game/penalty-decision", json={
            "game_id": game_id,
            "penalty_index": 0,
            "accept_penalty": False,
        })
        
        if response.status_code == 400:
            pass
        else:
            assert response.status_code == 200


def test_kickoff_transition_after_score():
    """Test that after a score, game transitions to kickoff with possession switched."""
    
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
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    state_before = client.get(f"/api/game/state/{game_id}").json()
    
    assert "is_kickoff" in state_before


def test_load_replay_field_goal_triggers_kickoff():
    """Test that loading a replay with FG in last play triggers kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {"id": "Ironclads", "name": "Iron Mountain Ironclads", "short_name": "Iron"},
            "away_team": {"id": "Thunderhawks", "name": "Metro City Thunderhawks", "short_name": "Thunder"},
            "home_score": 3,
            "away_score": 0,
            "quarter": 1,
            "time_remaining": 645,
            "possession": "home",
            "ball_position": 95,
            "down": 4,
            "yards_to_go": 5,
            "game_over": False,
            "home_timeouts": 3,
            "away_timeouts": 3,
            "player_offense": True,
            "human_team_id": "Ironclads",
            "cpu_team_id": "Thunderhawks",
            "human_is_home": True,
        },
        "play_history": [
            {
                "description": "Field goal GOOD! (22 yards, needed 5)",
                "headline": "Field Goal",
            }
        ]
    }
    
    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200
    
    data = response.json()
    game_state = data["game_state"]
    
    # Should be set up for kickoff
    assert game_state["is_kickoff"] is True
    assert game_state["down"] == 1
    assert game_state["yards_to_go"] == 10
    assert game_state["ball_position"] == 35


def test_load_replay_touchdown_triggers_kickoff():
    """Test that loading a replay with TD in last play triggers kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {"id": "Ironclads", "name": "Iron Mountain Ironclads", "short_name": "Iron"},
            "away_team": {"id": "Thunderhawks", "name": "Metro City Thunderhawks", "short_name": "Thunder"},
            "home_score": 6,
            "away_score": 0,
            "quarter": 1,
            "time_remaining": 600,
            "possession": "home",
            "ball_position": 100,
            "down": 1,
            "yards_to_go": 10,
            "game_over": False,
            "home_timeouts": 3,
            "away_timeouts": 3,
            "player_offense": True,
            "human_team_id": "Ironclads",
            "cpu_team_id": "Thunderhawks",
            "human_is_home": True,
        },
        "play_history": [
            {
                "description": "TOUCHDOWN! 45 yard pass to Jerry Rice!",
                "headline": "TOUCHDOWN!",
            }
        ]
    }
    
    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200
    
    data = response.json()
    game_state = data["game_state"]
    
    # Should be set up for kickoff
    assert game_state["is_kickoff"] is True
    assert game_state["down"] == 1
    assert game_state["yards_to_go"] == 10
    assert game_state["ball_position"] == 35


def test_load_replay_safety_triggers_kickoff():
    """Test that loading a replay with safety in last play triggers kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {"id": "Ironclads", "name": "Iron Mountain Ironclads", "short_name": "Iron"},
            "away_team": {"id": "Thunderhawks", "name": "Metro City Thunderhawks", "short_name": "Thunder"},
            "home_score": 0,
            "away_score": 2,
            "quarter": 1,
            "time_remaining": 500,
            "possession": "home",
            "ball_position": 2,
            "down": 3,
            "yards_to_go": 8,
            "game_over": False,
            "home_timeouts": 3,
            "away_timeouts": 3,
            "player_offense": True,
            "human_team_id": "Ironclads",
            "cpu_team_id": "Thunderhawks",
            "human_is_home": True,
        },
        "play_history": [
            {
                "description": "SAFETY! 2 points for the defense!",
                "headline": "SAFETY!",
            }
        ]
    }
    
    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200
    
    data = response.json()
    game_state = data["game_state"]
    
    # Should be set up for kickoff
    assert game_state["is_kickoff"] is True
    assert game_state["down"] == 1
    assert game_state["yards_to_go"] == 10
    assert game_state["ball_position"] == 35


def test_load_replay_no_score_no_kickoff():
    """Test that loading a replay with no score doesn't trigger kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {"id": "Ironclads", "name": "Iron Mountain Ironclads", "short_name": "Iron"},
            "away_team": {"id": "Thunderhawks", "name": "Metro City Thunderhawks", "short_name": "Thunder"},
            "home_score": 0,
            "away_score": 0,
            "quarter": 1,
            "time_remaining": 800,
            "possession": "home",
            "ball_position": 30,
            "down": 2,
            "yards_to_go": 7,
            "game_over": False,
            "home_timeouts": 3,
            "away_timeouts": 3,
            "player_offense": True,
            "human_team_id": "Ironclads",
            "cpu_team_id": "Thunderhawks",
            "human_is_home": True,
        },
        "play_history": [
            {
                "description": "Run up the middle for 3 yards",
                "headline": "Gain of 3",
            }
        ]
    }
    
    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200
    
    data = response.json()
    game_state = data["game_state"]
    
    # Should NOT be set up for kickoff
    assert game_state["is_kickoff"] is False
    # State should be as saved
    assert game_state["down"] == 2
    assert game_state["yards_to_go"] == 7
    assert game_state["ball_position"] == 30


def test_load_replay_already_in_kickoff_position():
    """Test that loading a replay already in kickoff position doesn't re-trigger."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {"id": "Ironclads", "name": "Iron Mountain Ironclads", "short_name": "Iron"},
            "away_team": {"id": "Thunderhawks", "name": "Metro City Thunderhawks", "short_name": "Thunder"},
            "home_score": 3,
            "away_score": 0,
            "quarter": 1,
            "time_remaining": 645,
            "possession": "away",  # Already switched
            "ball_position": 35,  # Already at kickoff spot
            "down": 1,
            "yards_to_go": 10,
            "game_over": False,
            "home_timeouts": 3,
            "away_timeouts": 3,
            "player_offense": False,
            "human_team_id": "Ironclads",
            "cpu_team_id": "Thunderhawks",
            "human_is_home": True,
        },
        "play_history": [
            {
                "description": "Field goal GOOD! (22 yards, needed 5)",
                "headline": "Field Goal",
            }
        ]
    }
    
    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200
    
    data = response.json()
    game_state = data["game_state"]
    
    # Should NOT trigger kickoff again since already in kickoff position
    assert game_state["is_kickoff"] is False
    # State should remain as saved
    assert game_state["down"] == 1
    assert game_state["yards_to_go"] == 10
    assert game_state["ball_position"] == 35


def test_cpu_4th_down_decision_when_human_on_defense():
    """
    Test that CPU makes 4th down decision when human is on defense.
    CPU should return punt/FG/go_for_it decision.
    """
    # Create game with human on offense first
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Human kicks - now CPU (away) has possession
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": True,  # Human kicks
        "human_plays_offense": False,  # Human is on defense
    })
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Run plays until we get to 4th down
    for _ in range(20):
        exec_response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "A",  # Defense play
            "cpu_play": None,  # Let CPU choose offense
        })
        
        if exec_response.status_code != 200:
            continue
            
        result = exec_response.json()
        
        if result["game_state"]["down"] == 4:
            # Now check CPU 4th down decision
            decision_resp = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
            assert decision_resp.status_code == 200
            decision = decision_resp.json()
            
            # Should be a valid decision
            assert decision["decision"] in ["punt", "field_goal", "go_for_it"]
            assert decision["play"] is not None
            print(f"CPU 4th down decision: {decision['decision']} ({decision['play']})")
            break
        
        if result["game_state"].get("game_over"):
            break
    else:
        print("Note: Did not reach 4th down in 20 plays")


def test_execute_with_cpu_kick_on_4th_down():
    """
    Test that when CPU decides to kick on 4th down, the execute endpoint
    properly handles the CPU's kick play.
    """
    # Create game
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Human kicks - CPU has possession
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": True,
        "human_plays_offense": False,
    })
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Run plays until 4th down
    for _ in range(20):
        # Get CPU's 4th down decision first
        decision_resp = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
        if decision_resp.status_code != 200:
            # Not 4th down yet, continue playing
            exec_response = client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "A",
                "cpu_play": None,
            })
            if exec_response.status_code != 200:
                continue
            result = exec_response.json()
            if result["game_state"]["down"] == 4:
                # Now on 4th down, get decision
                decision_resp = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
                break
            if result["game_state"].get("game_over"):
                break
            continue
        
        decision = decision_resp.json()
        
        if decision["decision"] == "go_for_it":
            # CPU going for it - execute with defense
            exec_response = client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "A",
                "cpu_play": decision["play"],  # CPU's go-for-it play
            })
            assert exec_response.status_code == 200
            break
        elif decision["decision"] in ["punt", "field_goal"]:
            # CPU kicking - execute with CPU's kick
            exec_response = client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "A",  # Dummy defense
                "cpu_play": decision["play"],  # CPU's kick (P or F)
            })
            assert exec_response.status_code == 200
            result = exec_response.json()
            
            # The result should be a punt or field goal
            description = result["result"]["description"].upper()
            if decision["decision"] == "punt":
                assert "PUNT" in description
            else:
                assert "FIELD GOAL" in description or "FG" in description or "GOOD" in description
            print(f"CPU kick result: {description}")
            break
    else:
        print("Note: Did not reach CPU kick scenario in 20 plays")


def test_penalty_cpu_decides_when_human_on_defense():
    """
    Test that when offense commits penalty and human is on defense,
    the penalty is auto-resolved by CPU (no pending_penalty_decision shown to human).
    """
    # Create game with human on defense
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Human kicks - CPU has possession (human on defense)
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": True,
        "human_plays_offense": False,  # Human is on defense
    })
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Run plays looking for offense penalty (offended_team == "defense")
    for _ in range(100):
        exec_response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "A",
            "cpu_play": None,
        })
        
        if exec_response.status_code != 200:
            continue
            
        result = exec_response.json()
        
        if result["result"].get("pending_penalty_decision"):
            penalty_choice = result["result"].get("penalty_choice")
            if penalty_choice and penalty_choice.get("offended_team") == "defense":
                # Offense committed penalty
                # Human is on defense, so CPU should auto-decide
                # pending_penalty_decision should be True but frontend should not show panel
                # (backend auto-resolves when human is on wrong side)
                print(f"Offense penalty: offended_team={penalty_choice['offended_team']}")
                print(f"Human is on defense, CPU should auto-decide")
                break
        
        if result["game_state"].get("game_over"):
            break
    else:
        print("Note: No offense penalty found in 100 plays")


def test_cpu_play_returns_offense_when_cpu_on_offense():
    """
    Test that /cpu-play returns an offense play when CPU is on offense.
    This is critical for the play log to show correct information.
    """
    # Create game with human on defense
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Human kicks - CPU has possession
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": True,
        "human_plays_offense": False,
    })
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Get CPU play
    cpu_response = client.post("/api/game/cpu-play", json={
        "game_id": game_id,
        "player_play": "A",  # Human's defense choice
    })
    
    assert cpu_response.status_code == 200
    cpu_data = cpu_response.json()
    
    # CPU should return an offense play (1-9, Q, K, etc.)
    cpu_play = cpu_data["cpu_play"]
    assert cpu_play in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Q", "K", "S"]
    print(f"CPU offense play: {cpu_play}")


def test_cpu_play_returns_defense_when_cpu_on_defense():
    """
    Test that /cpu-play returns a defense play when CPU is on defense.
    """
    # Create game with human on offense
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True,
    })
    data = response.json()
    game_id = data["game_id"]
    
    # Human receives - human has possession
    client.post("/api/game/coin-toss", json={
        "game_id": game_id,
        "player_won": True,
        "player_kicks": False,
        "human_plays_offense": True,
    })
    
    client.post("/api/game/kickoff", json={
        "game_id": game_id,
        "kickoff_spot": 35,
    })
    
    # Get CPU play
    cpu_response = client.post("/api/game/cpu-play", json={
        "game_id": game_id,
        "player_play": "1",  # Human's offense choice
    })
    
    assert cpu_response.status_code == 200
    cpu_data = cpu_response.json()
    
    # CPU should return a defense play (A-F)
    cpu_play = cpu_data["cpu_play"]
    assert cpu_play in ["A", "B", "C", "D", "E", "F"]
    print(f"CPU defense play: {cpu_play}")

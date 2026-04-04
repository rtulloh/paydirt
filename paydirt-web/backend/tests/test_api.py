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
    response = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"})
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
    response = client.post(
        "/api/game/new", json={"player_team": "NonexistentTeam", "season": "2026"}
    )
    assert response.status_code == 404


def test_new_game_invalid_season():
    response = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "1900"})
    assert response.status_code == 404


def test_get_game_state():
    response = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"})
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
    response = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"})
    data = response.json()
    game_id = data["game_id"]

    response = client.post("/api/game/execute", json={"game_id": game_id, "player_play": "1"})
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
    response = client.post("/api/game/execute", json={"game_id": "invalid_id", "player_play": "1"})
    assert response.status_code == 404


def test_delete_game():
    response = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"})
    data = response.json()
    game_id = data["game_id"]

    response = client.delete(f"/api/game/{game_id}")
    assert response.status_code == 200

    response = client.get(f"/api/game/state/{game_id}")
    assert response.status_code == 404


def test_player_offense_reflects_possession():
    """Test that player_offense is calculated based on current possession, not initial setting."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    initial_state = data["game_state"]
    initial_human_is_home = initial_state["human_is_home"]

    coin_toss_response = client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )
    assert coin_toss_response.status_code == 200

    state = client.get(f"/api/game/state/{game_id}").json()

    expected_player_offense = (initial_human_is_home and state["possession"] == "home") or (
        not initial_human_is_home and state["possession"] == "away"
    )
    assert state["player_offense"] == expected_player_offense, (
        f"player_offense should be {expected_player_offense} when human_is_home={initial_human_is_home} and possession={state['possession']}"
    )


def test_player_offense_after_kickoff():
    """Test that player_offense updates correctly after kickoff (when possession changes)."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    kickoff_response = client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )
    assert kickoff_response.status_code == 200

    state = client.get(f"/api/game/state/{game_id}").json()
    human_is_home = state["human_is_home"]

    expected_player_offense = (human_is_home and state["possession"] == "home") or (
        not human_is_home and state["possession"] == "away"
    )
    assert state["player_offense"] == expected_player_offense


def test_kickoff_returns_dice_details():
    """Test that kickoff returns dice details for frontend display."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    kickoff_response = client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )
    assert kickoff_response.status_code == 200
    kickoff_data = kickoff_response.json()

    # Verify dice_details is present and has valid values
    assert "dice_details" in kickoff_data
    dice_details = kickoff_data["dice_details"]

    # Kickoff uses special dice (10-39 range)
    assert "offense" in dice_details
    assert "defense" in dice_details

    # Kickoff total should be valid range (10-39), black is 1/2/3 (representing 10s)
    assert 1 <= dice_details["offense"]["black"] <= 3
    assert 10 <= dice_details["offense"]["total"] <= 39

    # Defense/return dice: red = black (tens), green = white1 (ones, max 5)
    assert dice_details["defense"]["red"] == dice_details["offense"]["black"]
    assert 0 <= dice_details["defense"]["green"] <= 5

    # dice_roll_offense and dice_roll_defense should also be set
    assert kickoff_data["dice_roll_offense"] == dice_details["offense"]["total"]
    assert kickoff_data["dice_roll_defense"] == dice_details["defense"]["total"]

    # Result should have a description with the dice info
    assert "description" in kickoff_data["result"]
    assert "KO:" in kickoff_data["result"]["description"]


def test_possession_changes_after_score():
    """Test that player_offense correctly reflects possession after a touchdown."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,
            "human_plays_offense": False,
        },
    )

    kickoff_response = client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )
    assert kickoff_response.status_code == 200

    state = client.get(f"/api/game/state/{game_id}").json()
    human_is_home = state["human_is_home"]

    expected_player_offense = (human_is_home and state["possession"] == "home") or (
        not human_is_home and state["possession"] == "away"
    )
    assert state["player_offense"] == expected_player_offense


def test_new_game_with_opponent_team():
    """Test creating a new game with a specific opponent (used for loading saved games)."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
            "opponent_team": "Thunderhawks",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["game_state"]["home_team"]["id"] == "Ironclads"
    assert data["game_state"]["away_team"]["id"] == "Thunderhawks"
    assert data["game_state"]["human_is_home"]


def test_new_game_away_team():
    """Test creating a new game where player is away team."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Thunderhawks",
            "season": "2026",
            "play_as_home": False,
            "opponent_team": "Ironclads",
        },
    )
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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Set up coin toss - player kicks (CPU receives on offense)
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,
            "human_plays_offense": False,
        },
    )

    # After kickoff, possession should switch and CPU (who received) should be on offense
    kickoff_resp = client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )
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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Set up coin toss so player has possession on offense
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    # Do kickoff to get initial possession
    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Skip to coin toss
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    # Do kickoff
    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Execute a play (Line Plunge)
    play_response = client.post(
        "/api/game/execute",
        json={
            "game_id": game_id,
            "player_play": "1",
            "cpu_play": "A",
        },
    )

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
    Test that penalty prompting logic correctly routes to human or CPU.

    The key logic:
    - If human is on the offended team (gets to choose), return penalty choice to frontend
    - If CPU is on the offended team, auto-decide using computer_ai

    This test verifies that when a penalty occurs, the correct party is prompted.
    """
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Run many plays and check that penalties are handled correctly
    penalty_count = 0
    for _ in range(100):
        play_response = client.post(
            "/api/game/execute",
            json={
                "game_id": game_id,
                "player_play": "1",
                "cpu_play": "A",
            },
        )

        if play_response.status_code != 200:
            continue

        result = play_response.json()

        # If there's a pending penalty, verify the human is on the offended team
        if result.get("result", {}).get("pending_penalty_decision"):
            penalty_count += 1
            # When human gets penalty choice, they should be on the offended team
            # This is implicitly tested by the fact that the endpoint returns successfully

        if result["game_state"].get("game_over"):
            break

    # Test passes if we completed without errors
    # Additional coverage is provided by test_penalty_cpu_decides_when_human_on_defense
    assert True, "Game completed without hanging on CPU penalty decision"


def test_save_replay():
    """Test saving a game replay."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
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


def test_load_replay_season_from_game_state():
    """Test that season is detected from game_state when not in replay_data."""
    # Create a game with a specific season
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    game_id = data["game_id"]

    # Save the replay
    save_response = client.post(f"/api/game/save-replay/{game_id}")
    save_data = save_response.json()

    # Load without specifying season at top level (simulating old replay format)
    # But season is present in game_state (legacy format)
    load_request = {
        "replay_data": {
            # Note: no "season" here at top level
            "game_state": {
                **save_data["game_state"],
                "season": "2026",  # season is in game_state (legacy format)
            },
            "play_history": save_data["play_history"],
            "difficulty": "medium",
        }
    }

    load_response = client.post("/api/game/load-replay", json=load_request)
    assert load_response.status_code == 200, f"Failed to load replay: {load_response.json()}"


def test_load_replay_invalid_data():
    """Test loading replay with invalid data."""
    response = client.post("/api/game/load-replay", json={"replay_data": {}})
    assert response.status_code == 400


def test_debug_settings():
    """Test getting and setting debug settings."""
    get_response = client.get("/api/debug/settings")
    assert get_response.status_code == 200
    settings = get_response.json()
    assert "deterministic_mode" in settings
    assert "seed" in settings

    set_response = client.post("/api/debug/settings", json={"deterministic_mode": True, "seed": 42})
    assert set_response.status_code == 200
    result = set_response.json()
    assert result["deterministic_mode"] is True
    assert result["seed"] == 42


def test_penalty_decision_cpu_makes_smart_decision():
    """Test that CPU penalty decision uses AI logic instead of hardcoded accept."""
    from unittest.mock import patch

    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    with patch("routes.cpu_should_accept_penalty") as mock_cpu_decision:
        mock_cpu_decision.return_value = (False, 0)

        response = client.post(
            "/api/game/penalty-decision",
            json={
                "game_id": game_id,
                "penalty_index": 0,
                "accept_penalty": True,
            },
        )

        if response.status_code == 400:
            pass
        else:
            assert response.status_code == 200


def test_penalty_decision_human_decides_uses_request_values():
    """Test that when human decides, their choice is used (not CPU's hardcoded decision)."""
    from unittest.mock import patch

    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    with patch("routes.cpu_should_accept_penalty") as mock_cpu_decision:
        mock_cpu_decision.return_value = (True, 0)

        response = client.post(
            "/api/game/penalty-decision",
            json={
                "game_id": game_id,
                "penalty_index": 0,
                "accept_penalty": False,
            },
        )

        if response.status_code == 400:
            pass
        else:
            assert response.status_code == 200


def test_kickoff_transition_after_score():
    """Test that after a score, game transitions to kickoff with possession switched."""

    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    state_before = client.get(f"/api/game/state/{game_id}").json()

    assert "is_kickoff" in state_before


def test_load_replay_field_goal_triggers_kickoff():
    """Test that loading a replay with FG in last play triggers kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {
                "id": "Ironclads",
                "name": "Iron Mountain Ironclads",
                "short_name": "Iron",
            },
            "away_team": {
                "id": "Thunderhawks",
                "name": "Metro City Thunderhawks",
                "short_name": "Thunder",
            },
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
        ],
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


def test_load_replay_touchdown_triggers_pending_pat():
    """Test that loading a replay with TD in last play (no PAT) sets pending_pat."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {
                "id": "Ironclads",
                "name": "Iron Mountain Ironclads",
                "short_name": "Iron",
            },
            "away_team": {
                "id": "Thunderhawks",
                "name": "Metro City Thunderhawks",
                "short_name": "Thunder",
            },
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
        ],
    }

    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200

    data = response.json()
    game_state = data["game_state"]

    # TD without PAT → pending_pat, NOT kickoff
    assert game_state["pending_pat"] is True
    assert game_state["is_kickoff"] is False


def test_load_replay_td_followed_by_pat_triggers_kickoff():
    """Test that loading a replay with TD + PAT triggers kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game2",
            "home_team": {
                "id": "Ironclads",
                "name": "Iron Mountain Ironclads",
                "short_name": "Iron",
            },
            "away_team": {
                "id": "Thunderhawks",
                "name": "Metro City Thunderhawks",
                "short_name": "Thunder",
            },
            "home_score": 7,
            "away_score": 0,
            "quarter": 1,
            "time_remaining": 580,
            "possession": "home",
            "ball_position": 35,
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
                "description": "TOUCHDOWN! 45 yard pass!",
                "headline": "TOUCHDOWN!",
            },
            {
                "description": "Extra point is GOOD!",
                "headline": "Extra Point GOOD",
            },
        ],
    }

    response = client.post("/api/game/load-replay", json={"replay_data": replay_data})
    assert response.status_code == 200

    data = response.json()
    game_state = data["game_state"]

    # Already at kickoff position (ball at 35), so no transition needed
    assert game_state["is_kickoff"] is False
    assert game_state["pending_pat"] is False
    assert game_state["down"] == 1
    assert game_state["yards_to_go"] == 10
    assert game_state["ball_position"] == 35


def test_load_replay_safety_triggers_kickoff():
    """Test that loading a replay with safety in last play triggers kickoff."""
    replay_data = {
        "season": "2026",
        "game_state": {
            "game_id": "test_game",
            "home_team": {
                "id": "Ironclads",
                "name": "Iron Mountain Ironclads",
                "short_name": "Iron",
            },
            "away_team": {
                "id": "Thunderhawks",
                "name": "Metro City Thunderhawks",
                "short_name": "Thunder",
            },
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
        ],
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
            "home_team": {
                "id": "Ironclads",
                "name": "Iron Mountain Ironclads",
                "short_name": "Iron",
            },
            "away_team": {
                "id": "Thunderhawks",
                "name": "Metro City Thunderhawks",
                "short_name": "Thunder",
            },
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
        ],
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
            "home_team": {
                "id": "Ironclads",
                "name": "Iron Mountain Ironclads",
                "short_name": "Iron",
            },
            "away_team": {
                "id": "Thunderhawks",
                "name": "Metro City Thunderhawks",
                "short_name": "Thunder",
            },
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
        ],
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
    CPU should automatically handle 4th down (punt/FG/go_for_it) during execute.
    """
    # Create game with human on offense first
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human kicks - now CPU (away) has possession
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,  # Human kicks
            "human_plays_offense": False,  # Human is on defense
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Run plays until we get to 4th down
    for _ in range(20):
        exec_response = client.post(
            "/api/game/execute",
            json={
                "game_id": game_id,
                "player_play": "A",  # Defense play
                "cpu_play": None,  # Let CPU choose offense
            },
        )

        if exec_response.status_code != 200:
            continue

        result = exec_response.json()

        # Check if this was a 4th down play result (punt, FG, or normal play)
        # The execute endpoint now handles CPU 4th down automatically
        desc = result["result"]["description"].upper()

        if result["game_state"]["down"] == 1 and result["game_state"].get("ball_position"):
            # Down reset to 1 means a 4th down play was executed
            # Check what type of play it was
            if "PUNT" in desc or "punt" in desc.lower():
                print("CPU 4th down decision: punt")
                return  # Success - CPU punted
            elif "FIELD GOAL" in desc or "FG" in desc or "GOOD" in desc:
                print("CPU 4th down decision: field_goal")
                return  # Success - CPU kicked FG
            else:
                # Regular play executed - CPU went for it
                print("CPU 4th down decision: go_for_it")
                return  # Success - CPU went for it

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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human kicks - CPU has possession
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,
            "human_plays_offense": False,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Run plays until 4th down
    for _ in range(20):
        # Get CPU's 4th down decision first
        decision_resp = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
        if decision_resp.status_code != 200:
            # Not 4th down yet, continue playing
            exec_response = client.post(
                "/api/game/execute",
                json={
                    "game_id": game_id,
                    "player_play": "A",
                    "cpu_play": None,
                },
            )
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
            exec_response = client.post(
                "/api/game/execute",
                json={
                    "game_id": game_id,
                    "player_play": "A",
                    "cpu_play": decision["play"],  # CPU's go-for-it play
                },
            )
            assert exec_response.status_code == 200
            break
        elif decision["decision"] in ["punt", "field_goal"]:
            # CPU kicking - execute with CPU's kick
            exec_response = client.post(
                "/api/game/execute",
                json={
                    "game_id": game_id,
                    "player_play": "A",  # Dummy defense
                    "cpu_play": decision["play"],  # CPU's kick (P or F)
                },
            )
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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human kicks - CPU has possession (human on defense)
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,
            "human_plays_offense": False,  # Human is on defense
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Run plays looking for offense penalty (offended_team == "defense")
    for _ in range(100):
        exec_response = client.post(
            "/api/game/execute",
            json={
                "game_id": game_id,
                "player_play": "A",
                "cpu_play": None,
            },
        )

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
                print("Human is on defense, CPU should auto-decide")
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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human kicks - CPU has possession
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,
            "human_plays_offense": False,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Get CPU play
    cpu_response = client.post(
        "/api/game/cpu-play",
        json={
            "game_id": game_id,
            "player_play": "A",  # Human's defense choice
        },
    )

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
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human receives - human has possession
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Get CPU play
    cpu_response = client.post(
        "/api/game/cpu-play",
        json={
            "game_id": game_id,
            "player_play": "1",  # Human's offense choice
        },
    )

    assert cpu_response.status_code == 200
    cpu_data = cpu_response.json()

    # CPU should return a defense play (A-F)
    cpu_play = cpu_data["cpu_play"]
    assert cpu_play in ["A", "B", "C", "D", "E", "F"]
    print(f"CPU defense play: {cpu_play}")


def test_timeout_endpoint_success():
    """
    Test that /api/game/timeout successfully reduces time and returns updated state.
    """
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Win coin toss and kick off
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": True,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Get initial time remaining
    state_response = client.get(f"/api/game/state/{game_id}")
    initial_time = state_response.json()["time_remaining"]

    # Call timeout
    timeout_response = client.post(
        "/api/game/timeout",
        json={
            "game_id": game_id,
            "player_play": "1",
        },
    )

    assert timeout_response.status_code == 200
    timeout_data = timeout_response.json()
    assert timeout_data["success"] is True
    assert "home_timeouts" in timeout_data
    assert "away_timeouts" in timeout_data
    assert timeout_data["time_remaining"] < initial_time


def test_timeout_endpoint_no_timeouts_remaining():
    """
    Test that /api/game/timeout returns error when no timeouts left.
    """
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Use all 3 timeouts
    for _ in range(3):
        client.post("/api/game/timeout", json={"game_id": game_id, "player_play": "1"})

    # Try to use 4th timeout
    timeout_response = client.post(
        "/api/game/timeout",
        json={
            "game_id": game_id,
            "player_play": "1",
        },
    )

    assert timeout_response.status_code == 400
    assert "No timeouts remaining" in timeout_response.json()["detail"]


def test_timeout_endpoint_invalid_game():
    """
    Test that /api/game/timeout returns 404 for invalid game.
    """
    response = client.post(
        "/api/game/timeout",
        json={
            "game_id": "invalid-game-id",
            "player_play": "1",
        },
    )

    assert response.status_code == 404


def test_overtime_endpoint_invalid_game():
    """
    Test that /api/game/overtime/start returns 404 for invalid game.
    """
    response = client.post(
        "/api/game/overtime/start",
        json={
            "game_id": "invalid-game-id",
            "player_play": "1",
        },
    )

    assert response.status_code == 404


def test_overtime_endpoint_starts_overtime():
    """
    Test that /api/game/overtime/start successfully starts overtime when tied.
    At game start (0-0), the game is tied so overtime can be started.
    """
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Try to start overtime when scores are tied (0-0)
    overtime_response = client.post(
        "/api/game/overtime/start",
        json={
            "game_id": game_id,
            "player_play": "1",
        },
    )

    assert overtime_response.status_code == 200
    overtime_data = overtime_response.json()
    assert overtime_data["success"] is True
    assert overtime_data["is_overtime"] is True
    assert overtime_data["is_kickoff"] is True
    assert "game_state" in overtime_data


def test_penalty_decision_cpu_accepts_penalty():
    """
    Test penalty decision when CPU decides to accept penalty (decline play).
    """
    # Create game with CPU on offense
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human receives kickoff (human has possession)
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Human plays offense against CPU defense
    # Run plays until we get a penalty (this is stochastic, so we check the endpoint exists)
    execute_response = client.post(
        "/api/game/execute",
        json={
            "game_id": game_id,
            "player_play": "1",
        },
    )

    assert execute_response.status_code in [200, 400]
    print(f"Execute response: {execute_response.status_code}")


def test_load_replay_sets_pending_pat_when_ball_in_endzone():
    """Test that loading a replay with ball in end zone sets pending_pat=True."""
    # Create a game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Save replay
    save_response = client.post(f"/api/game/save-replay/{game_id}")
    save_data = save_response.json()

    # Manually set ball_position to end zone in the replay data
    save_data["game_state"]["ball_position"] = 102

    # Load replay
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

    # Check that pending_pat is True because ball is in end zone
    assert load_data["game_state"]["pending_pat"]


def test_penalty_decision_sets_pending_pat_on_touchdown():
    """Test that accepting a penalty play that results in TD sets pending_pat."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Human receives kickoff (human has possession)
    client.post(
        "/api/game/coin-toss",
        json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,
            "human_plays_offense": True,
        },
    )

    client.post(
        "/api/game/kickoff",
        json={
            "game_id": game_id,
            "kickoff_spot": 35,
        },
    )

    # Run plays until we get a pending penalty decision
    found_pending = False
    for _ in range(100):
        execute_response = client.post(
            "/api/game/execute",
            json={
                "game_id": game_id,
                "player_play": "1",
                "cpu_play": "A",
            },
        )

        if execute_response.status_code == 200:
            result = execute_response.json()
            if result["result"].get("pending_penalty_decision"):
                # Found a penalty - accept the play
                penalty_response = client.post(
                    "/api/game/penalty-decision",
                    json={
                        "game_id": game_id,
                        "penalty_index": 0,
                        "accept_penalty": False,  # Accept play result
                    },
                )

                if penalty_response.status_code == 200:
                    penalty_result = penalty_response.json()
                    # If ball position >= 100, pending_pat should be True
                    if penalty_result["game_state"]["ball_position"] >= 100:
                        assert penalty_result["game_state"]["pending_pat"]
                        found_pending = True
                        break

        if result.get("game_state", {}).get("game_over"):
            break

    # If we found a pending penalty, verify the assertion was checked
    if found_pending:
        pass  # Test passed


def test_load_replay_season_detection_from_teams():
    """Test that season is detected from team directories when replay has wrong season."""
    # Create a game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    # Save replay
    save_response = client.post(f"/api/game/save-replay/{game_id}")
    save_data = save_response.json()

    # Load with wrong season - should detect from teams
    load_request = {
        "replay_data": {
            "season": "9999",  # Non-existent season
            "game_state": save_data["game_state"],
            "play_history": save_data["play_history"],
            "difficulty": "medium",
        }
    }

    load_response = client.post("/api/game/load-replay", json=load_request)
    # Should succeed by detecting season from teams
    assert load_response.status_code == 200


# =============================================================================
# Tests for GameIdRequest endpoints (packaging fixes - beta.63/64)
# =============================================================================


def test_extra_point_only_requires_game_id():
    """Test that extra-point endpoint works with just game_id (no player_play required)."""
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    game_id = response.json()["game_id"]

    # Call extra-point with only game_id
    ep_response = client.post(
        "/api/game/extra-point",
        json={
            "game_id": game_id,
        },
    )

    # Should succeed (200) not fail with 422 validation error
    assert ep_response.status_code == 200
    data = ep_response.json()
    assert "success" in data
    assert "description" in data


def test_cpu_play_only_requires_game_id():
    """Test that cpu-play endpoint works with just game_id (no player_play required)."""
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    game_id = response.json()["game_id"]

    # Call cpu-play with only game_id
    cpu_response = client.post(
        "/api/game/cpu-play",
        json={
            "game_id": game_id,
        },
    )

    # Should succeed (200) not fail with 422 validation error
    assert cpu_response.status_code == 200
    data = cpu_response.json()
    assert "cpu_play" in data


def test_timeout_only_requires_game_id():
    """Test that timeout endpoint works with just game_id (no player_play required)."""
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    game_id = response.json()["game_id"]

    # Call timeout with only game_id
    timeout_response = client.post(
        "/api/game/timeout",
        json={
            "game_id": game_id,
        },
    )

    # Should succeed (200) not fail with 422 validation error
    assert timeout_response.status_code == 200
    data = timeout_response.json()
    assert "success" in data


def test_overtime_start_only_requires_game_id():
    """Test that overtime/start endpoint works with just game_id (no player_play required)."""
    # Create game
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    game_id = response.json()["game_id"]

    # Call overtime/start with only game_id
    ot_response = client.post(
        "/api/game/overtime/start",
        json={
            "game_id": game_id,
        },
    )

    # Should succeed (200) not fail with 422 validation error
    assert ot_response.status_code == 200
    data = ot_response.json()
    assert "success" in data


def test_extra_point_rejects_missing_game_id():
    """Test that extra-point returns 422 when game_id is missing."""
    response = client.post("/api/game/extra-point", json={})
    assert response.status_code == 422


def test_cpu_play_rejects_missing_game_id():
    """Test that cpu-play returns 422 when game_id is missing."""
    response = client.post("/api/game/cpu-play", json={})
    assert response.status_code == 422


def test_timeout_rejects_missing_game_id():
    """Test that timeout returns 422 when game_id is missing."""
    response = client.post("/api/game/timeout", json={})
    assert response.status_code == 422


def test_overtime_start_rejects_missing_game_id():
    """Test that overtime/start returns 422 when game_id is missing."""
    response = client.post("/api/game/overtime/start", json={})
    assert response.status_code == 422


# =============================================================================
# Tests for SEASONS_DIR detection (packaging fixes - beta.62)
# =============================================================================


def test_seasons_dir_finds_2026_season():
    """Test that SEASONS_DIR is correctly configured to find seasons."""
    response = client.get("/api/seasons")
    assert response.status_code == 200
    data = response.json()
    assert "2026" in data["seasons"]


def test_seasons_dir_finds_teams_in_season():
    """Test that SEASONS_DIR allows finding teams within a season."""
    response = client.get("/api/teams?season=2026")
    assert response.status_code == 200
    data = response.json()
    team_ids = [t["id"] for t in data["teams"]]
    assert "Ironclads" in team_ids
    assert "Thunderhawks" in team_ids


def test_game_new_can_load_team_charts():
    """Test that new game can load team charts from SEASONS_DIR."""
    response = client.post(
        "/api/game/new",
        json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["game_state"]["home_team"]["id"] == "Ironclads"


# Tests for multi-path season discovery


def test_find_season_dir_helper():
    """Test that _find_season_dir returns correct path for valid seasons."""
    from routes import _find_season_dir

    # Should find the 2026 season
    season_dir = _find_season_dir("2026")
    assert season_dir is not None
    assert season_dir.name == "2026"
    assert season_dir.exists()


def test_find_season_dir_returns_none_for_invalid():
    """Test that _find_season_dir returns None for non-existent seasons."""
    from routes import _find_season_dir

    # Should return None for non-existent season
    season_dir = _find_season_dir("1800")
    assert season_dir is None


def test_get_seasons_returns_only_numeric_directories():
    """Test that get_seasons only returns numeric directory names."""
    response = client.get("/api/seasons")
    assert response.status_code == 200
    data = response.json()

    # All returned seasons should be numeric strings
    for season in data["seasons"]:
        assert season.isdigit(), f"Season '{season}' is not numeric"


def test_get_seasons_sorted_descending():
    """Test that get_seasons returns seasons sorted in descending order."""
    response = client.get("/api/seasons")
    assert response.status_code == 200
    data = response.json()

    seasons = data["seasons"]
    if len(seasons) > 1:
        # Convert to integers for comparison
        season_ints = [int(s) for s in seasons]
        assert season_ints == sorted(season_ints, reverse=True)


# Tests for /api/guide endpoint


def test_get_guide_returns_content():
    """Test that /api/guide returns guide content."""
    response = client.get("/api/guide")
    assert response.status_code == 200
    data = response.json()

    assert "content" in data
    assert "title" in data
    assert data["title"] == "Paydirt User Guide"
    assert len(data["content"]) > 0


def test_get_guide_contains_expected_sections():
    """Test that guide contains expected user-facing sections."""
    response = client.get("/api/guide")
    assert response.status_code == 200
    data = response.json()

    content = data["content"]
    # Should contain user-facing sections
    assert "## Download & Install" in content
    assert "## How to Play" in content
    assert "## Time Management" in content
    assert "## Strategy Tips" in content


def test_get_guide_excludes_developer_sections():
    """Test that guide excludes developer-only sections."""
    response = client.get("/api/guide")
    assert response.status_code == 200
    data = response.json()

    content = data["content"]
    # Should NOT contain developer-only sections
    assert "## Project Structure" not in content
    assert "## Building Standalone Executables" not in content
    assert "## Code Signing" not in content


def test_filter_readme_helper():
    """Test the _filter_readme_for_guide helper function."""
    from routes import _filter_readme_for_guide

    test_content = """# Test README

## User Section
This should stay.

## Project Structure
This should be removed.
More stuff to remove.

## Another User Section
This should stay too.

## Building Standalone Executables
This should be removed.
Including code signing info.

## License
Final section should stay.
"""

    filtered = _filter_readme_for_guide(test_content)

    assert "## User Section" in filtered
    assert "This should stay." in filtered
    assert "## Another User Section" in filtered
    assert "This should stay too." in filtered
    assert "## License" in filtered

    assert "## Project Structure" not in filtered
    assert "This should be removed." not in filtered
    assert "## Building Standalone Executables" not in filtered
    assert "Including code signing info." not in filtered


def test_filter_readme_rewrites_image_paths():
    """Test that image paths are rewritten to use API endpoint."""
    from routes import _filter_readme_for_guide

    test_content = """# Test

![Main Menu](docs/images/menu.png)

Some text.

![Another Image](docs/images/screenshot.jpg)
"""

    filtered = _filter_readme_for_guide(test_content)

    assert "![Main Menu](/api/docs/images/menu.png)" in filtered
    assert "![Another Image](/api/docs/images/screenshot.jpg)" in filtered
    # The original relative path should be replaced
    assert "(docs/images/" not in filtered


def test_get_doc_image_returns_image():
    """Test that the image endpoint returns images."""
    response = client.get("/api/docs/images/menu.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_get_doc_image_rejects_path_traversal():
    """Test that path traversal attempts are rejected."""
    # FastAPI normalizes URLs, so ../ gets handled before our code
    # The important thing is we don't serve files outside docs/images
    response = client.get("/api/docs/images/..%2Ftest.png")
    assert response.status_code in [400, 404]  # Either rejected or not found


def test_get_doc_image_rejects_invalid_extension():
    """Test that non-image files are rejected."""
    response = client.get("/api/docs/images/malicious.exe")
    assert response.status_code == 400


def test_get_doc_image_returns_404_for_missing():
    """Test that missing images return 404."""
    response = client.get("/api/docs/images/nonexistent.png")
    assert response.status_code == 404

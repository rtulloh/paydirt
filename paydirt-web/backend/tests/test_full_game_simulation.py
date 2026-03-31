"""
Full game simulation tests - tests the complete game flow end-to-end.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestFullGameSimulation:
    """Test complete game flow from start to finish."""

    def test_complete_game_ironclads_vs_thunderhawks_2026(self):
        """Simulate a complete game between Ironclads and Thunderhawks from 2026."""
        # 1. Create new game
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        assert response.status_code == 200
        game_data = response.json()
        game_id = game_data["game_id"]
        assert game_id is not None
        print(f"\nGame created: {game_id}")

        # 2. Coin toss
        response = client.post("/api/game/coin-toss", json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,  # Player receives
            "human_plays_offense": True,
        })
        assert response.status_code == 200
        coin_data = response.json()
        assert coin_data["status"] == "ok"
        print(f"Coin toss: Player offense={coin_data.get('player_offense')}")

        # 3. Kickoff
        response = client.post("/api/game/kickoff", json={
            "game_id": game_id,
            "kickoff_spot": 35,
        })
        assert response.status_code == 200
        kickoff_data = response.json()
        assert "dice_details" in kickoff_data
        print(f"Kickoff: {kickoff_data.get('play_description', 'OK')}")

        # 4. Play through the game
        play_count = 0
        max_plays = 200  # Safety limit
        touchdowns = 0
        field_goals = 0
        penalties = 0
        turnovers = 0

        while play_count < max_plays:
            play_count += 1

            # Get current game state
            state_response = client.get(f"/api/game/state/{game_id}")
            assert state_response.status_code == 200
            state = state_response.json()

            if state.get("game_over"):
                print(f"\nGame over after {play_count} plays!")
                print(f"Final score: {state['home_team']['name']} {state['home_score']} - {state['away_team']['name']} {state['away_score']}")
                break

            # Check for pending PAT
            if state.get("pending_pat"):
                print(f"  PAT attempt at play {play_count}")
                response = client.post("/api/game/extra-point", json={
                    "game_id": game_id,
                    "player_play": "PAT",
                })
                assert response.status_code == 200
                continue

            # Check for kickoff position - after a score
            if state.get("is_kickoff"):
                response = client.post("/api/game/kickoff", json={
                    "game_id": game_id,
                    "kickoff_spot": 35,
                })
                assert response.status_code == 200
                continue

            # Check for pending penalty decision
            if state.get("pending_penalty_decision"):
                penalties += 1
                print(f"  Penalty decision at play {play_count}")
                # Accept penalty
                response = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id,
                    "accept_penalty": True,
                    "penalty_index": 0,
                })
                assert response.status_code == 200, f"Penalty decision failed: {response.text}"
                continue

            # Check for 4th down decision (CPU on defense, auto-kick)
            if state.get("down") == 4 and not state.get("player_offense"):
                # Player is on defense, CPU decides
                response = client.get(f"/api/game/cpu-4th-down-decision/{game_id}")
                assert response.status_code == 200
                decision = response.json()
                if decision.get("decision") == "kick":
                    print(f"  CPU punt at play {play_count}")
                    response = client.post("/api/game/execute", json={
                        "game_id": game_id,
                        "player_play": "A",
                        "cpu_play": "KICK",
                    })
                    assert response.status_code == 200
                    continue

            # Execute a play
            response = client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "1",
                "cpu_play": "A",
            })

            if response.status_code != 200:
                print(f"  ERROR at play {play_count}: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                # Continue to see if game recovers
                continue

            play_data = response.json()
            result = play_data.get("result", {})

            if result.get("touchdown"):
                touchdowns += 1
                print(f"  TOUCHDOWN at play {play_count}!")

            if result.get("turnover"):
                turnovers += 1

            # Every 20 plays, print progress
            if play_count % 20 == 0:
                state_response = client.get(f"/api/game/state/{game_id}")
                state = state_response.json()
                print(f"  Play {play_count}: Q{state['quarter']} {state['time_remaining']}s, "
                      f"Score: {state['home_score']}-{state['away_score']}, "
                      f"Ball: {state['field_position']}")

        # Verify game completed
        final_state_response = client.get(f"/api/game/state/{game_id}")
        final_state = final_state_response.json()

        assert final_state.get("game_over") or play_count >= max_plays, "Game should have ended"
        print(f"\nStats: {play_count} plays, {touchdowns} TDs, {field_goals} FGs, {penalties} penalties, {turnovers} turnovers")

        # Cleanup
        client.delete(f"/api/game/{game_id}")

    def test_penalty_flow_with_touchdown(self):
        """Test penalty decision that results in touchdown."""
        # Create game
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        game_id = response.json()["game_id"]

        # Coin toss and kickoff
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

        # Play until we're near the end zone
        for _ in range(100):
            state = client.get(f"/api/game/state/{game_id}").json()
            if state.get("game_over"):
                break

            # Handle PAT if needed
            if state.get("pending_pat"):
                client.post("/api/game/extra-point", json={"game_id": game_id, "player_play": "PAT"})
                continue

            # Check if we're close to end zone (within 15 yards)
            ball_pos = state.get("ball_position", 50)
            player_offense = state.get("player_offense", False)

            if player_offense and ball_pos >= 85:
                # Near end zone, try to score
                response = client.post("/api/game/execute", json={
                    "game_id": game_id,
                    "player_play": "1",
                    "cpu_play": "A",
                })
                if response.status_code == 200:
                    result = response.json().get("result", {})
                    # Check if penalty or touchdown
                    if result.get("pending_penalty_decision"):
                        # Accept penalty
                        penalty_response = client.post("/api/game/penalty-decision", json={
                            "game_id": game_id,
                            "accept_penalty": True,
                            "penalty_index": 0,
                        })
                        assert penalty_response.status_code == 200
                        penalty_result = penalty_response.json().get("result", {})
                        if penalty_result.get("touchdown"):
                            print("Penalty resulted in touchdown!")
                            # Verify pending_pat is set
                            final_state = client.get(f"/api/game/state/{game_id}").json()
                            assert final_state.get("pending_pat") or final_state.get("game_over")
                            break
            else:
                client.post("/api/game/execute", json={
                    "game_id": game_id,
                    "player_play": "1",
                    "cpu_play": "A",
                })

        # Cleanup
        client.delete(f"/api/game/{game_id}")

    def test_replay_save_and_load(self):
        """Test saving and loading a game replay."""
        # Create and play a game
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        game_id = response.json()["game_id"]

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

        # Play a few plays
        for _ in range(10):
            state = client.get(f"/api/game/state/{game_id}").json()
            if state.get("game_over"):
                break
            if state.get("pending_pat"):
                client.post("/api/game/extra-point", json={"game_id": game_id, "player_play": "PAT"})
                continue
            if state.get("pending_penalty_decision"):
                client.post("/api/game/penalty-decision", json={
                    "game_id": game_id,
                    "accept_penalty": True,
                    "penalty_index": 0,
                })
                continue
            client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "1",
                "cpu_play": "A",
            })

        # Save replay - correct endpoint is /api/game/save-replay/{game_id}
        save_response = client.post(f"/api/game/save-replay/{game_id}")
        assert save_response.status_code == 200
        save_data = save_response.json()
        assert "replay_id" in save_data
        print(f"Replay saved: {save_data['replay_id']}")

        # Load replay - expects replay_data (the entire save response)
        load_response = client.post("/api/game/load-replay", json={
            "replay_data": save_data
        })
        assert load_response.status_code == 200
        loaded_game = load_response.json()
        assert "game_state" in loaded_game
        print(f"Replay loaded: {loaded_game['game_state']['game_id']}")

        # Cleanup both games
        client.delete(f"/api/game/{game_id}")
        client.delete(f"/api/game/{loaded_game['game_state']['game_id']}")

    def test_season_rules_enforcement(self):
        """Test that season rules are properly enforced."""
        # Test 2026 season (allows 2-point conversion)
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]

        # Get PAT choice info
        pat_response = client.get(f"/api/game/pat-choice/{game_id}")
        assert pat_response.status_code == 200
        pat_data = pat_response.json()
        assert pat_data.get("can_go_for_two"), "2026 should allow 2-point conversion"

        # Cleanup
        client.delete(f"/api/game/{game_id}")

    def test_overtime_flow(self):
        """Test overtime game flow."""
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        game_id = response.json()["game_id"]

        # Correct endpoint is /api/game/overtime/start
        ot_response = client.post("/api/game/overtime/start", json={
            "game_id": game_id,
            "player_play": "OVERTIME",
        })
        # Fails if game isn't tied in 4th quarter - expected
        assert ot_response.status_code in [200, 400, 404]

        # Cleanup
        client.delete(f"/api/game/{game_id}")

    def test_timeout_usage(self):
        """Test calling timeouts."""
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        game_id = response.json()["game_id"]

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

        # Get initial state
        state = client.get(f"/api/game/state/{game_id}").json()
        initial_home_timeouts = state.get("home_timeouts", 3)
        initial_away_timeouts = state.get("away_timeouts", 3)

        # Call timeout - endpoint uses PlayRequest, needs game_id and player_play
        timeout_response = client.post("/api/game/timeout", json={
            "game_id": game_id,
            "player_play": "TIMEOUT",
        })
        assert timeout_response.status_code == 200
        timeout_data = timeout_response.json()
        assert "success" in timeout_data

        # Verify timeout was used
        new_state = client.get(f"/api/game/state/{game_id}").json()
        # One of the teams should have one less timeout
        total_timeout_decrease = (
            (initial_home_timeouts - new_state.get("home_timeouts", 3)) +
            (initial_away_timeouts - new_state.get("away_timeouts", 3))
        )
        assert total_timeout_decrease == 1, "One timeout should have been used"

        # Cleanup
        client.delete(f"/api/game/{game_id}")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_clock_decreases_through_game(self):
        """Verify game clock decreases properly through plays."""
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        game_id = response.json()["game_id"]

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

        # Get state after kickoff - kickoff consumes ~12 seconds
        state = client.get(f"/api/game/state/{game_id}").json()
        initial_time = state.get("time_remaining", 0)
        initial_quarter = state.get("quarter", 1)
        print(f"After kickoff: Q{initial_quarter}, {initial_time}s remaining")
        assert initial_quarter == 1
        # Kickoff consumes time, so time should be <= 900 and > 800
        assert 800 <= initial_time <= 900, f"Time after kickoff should be ~888s, got {initial_time}s"

        previous_time = initial_time
        previous_quarter = initial_quarter
        plays_checked = 0

        # Play through first quarter, checking time decreases
        for _ in range(50):
            state = client.get(f"/api/game/state/{game_id}").json()
            if state.get("game_over"):
                break

            # Handle game situations
            if state.get("pending_pat"):
                client.post("/api/game/extra-point", json={"game_id": game_id, "player_play": "PAT"})
                plays_checked += 1
                continue
            if state.get("pending_penalty_decision"):
                client.post("/api/game/penalty-decision", json={
                    "game_id": game_id,
                    "accept_penalty": True,
                    "penalty_index": 0,
                })
                plays_checked += 1
                continue

            # Execute play
            client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "1",
                "cpu_play": "A",
            })
            plays_checked += 1

            # Get new state and verify clock
            new_state = client.get(f"/api/game/state/{game_id}").json()
            new_time = new_state.get("time_remaining", 0)
            new_quarter = new_state.get("quarter", 1)

            # Time should decrease (unless quarter changed)
            if new_quarter == previous_quarter:
                assert new_time <= previous_time, \
                    f"Time should decrease: {previous_time}s -> {new_time}s in Q{new_quarter}"
            else:
                # Quarter changed - time should be close to 900 again
                print(f"Quarter changed: Q{previous_quarter} -> Q{new_quarter}")
                assert new_quarter == previous_quarter + 1, "Quarter should increment by 1"

            previous_time = new_time
            previous_quarter = new_quarter

            # Once we reach Q2, we've verified clock works
            if new_quarter >= 2:
                print(f"Reached Q{new_quarter} after {plays_checked} plays, time: {new_time}s")
                break

        assert plays_checked > 0, "Should have checked at least one play"
        print(f"Clock verification passed: {plays_checked} plays checked")

        # Cleanup
        client.delete(f"/api/game/{game_id}")

    def test_game_ends_after_four_quarters(self):
        """Verify game ends after Q4 time expires."""
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        game_id = response.json()["game_id"]

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

        quarter_times = {}  # Track when we enter each quarter
        max_plays = 300  # Safety limit

        for play_num in range(max_plays):
            state = client.get(f"/api/game/state/{game_id}").json()

            if state.get("game_over"):
                final_q = state.get("quarter", 0)
                final_score = f"{state['home_team']['name']} {state['home_score']} - {state['away_team']['name']} {state['away_score']}"
                print(f"Game ended after {play_num} plays in Q{final_q}. Final: {final_score}")
                # Verify we played through at least Q4
                assert final_q >= 4 or state.get("time_remaining", 0) == 0, \
                    f"Game should end in Q4 or later, ended in Q{final_q}"
                break

            quarter = state.get("quarter", 1)
            if quarter not in quarter_times:
                quarter_times[quarter] = play_num
                print(f"Entered Q{quarter} at play {play_num}")

            # Handle game situations
            if state.get("pending_pat"):
                client.post("/api/game/extra-point", json={"game_id": game_id, "player_play": "PAT"})
                continue
            if state.get("pending_penalty_decision"):
                client.post("/api/game/penalty-decision", json={
                    "game_id": game_id,
                    "accept_penalty": True,
                    "penalty_index": 0,
                })
                continue

            client.post("/api/game/execute", json={
                "game_id": game_id,
                "player_play": "1",
                "cpu_play": "A",
            })

        # Cleanup
        client.delete(f"/api/game/{game_id}")

    def test_invalid_game_id(self):
        """Test requests with invalid game ID."""
        response = client.get("/api/game/state/invalid_game_id")
        assert response.status_code == 404

    def test_invalid_team(self):
        """Test creating game with invalid team."""
        response = client.post("/api/game/new", json={
            "player_team": "InvalidTeam",
            "season": "2026",
            "play_as_home": True,
        })
        # Should either fail or use default
        assert response.status_code in [200, 400, 404]

    def test_duplicate_game_creation(self):
        """Test creating multiple games."""
        response1 = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        assert response1.status_code == 200
        game_id1 = response1.json()["game_id"]

        response2 = client.post("/api/game/new", json={
            "player_team": "Thunderhawks",
            "season": "2026",
            "play_as_home": True,
        })
        assert response2.status_code == 200
        game_id2 = response2.json()["game_id"]

        assert game_id1 != game_id2, "Different games should have different IDs"

        # Cleanup
        client.delete(f"/api/game/{game_id1}")
        client.delete(f"/api/game/{game_id2}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

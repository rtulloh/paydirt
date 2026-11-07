"""
Tests for play modifiers functionality: suffix parsing and modifier handling.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from routes import games, parse_play_with_modifiers

from paydirt.play_resolver import PlayType


class TestParsePlayWithModifiers:
    """Unit tests for parse_play_with_modifiers function."""
    
    def test_simple_play_no_modifiers(self):
        """Test parsing a simple play with no modifiers."""
        play_type, modifiers = parse_play_with_modifiers("7")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is False
        assert modifiers['call_timeout'] is False
        assert modifiers['out_of_bounds'] is False
        assert modifiers['in_bounds'] is False
    
    def test_play_with_spike_modifier(self):
        """Test parsing play with spike modifier."""
        play_type, modifiers = parse_play_with_modifiers("7S")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is True
        assert modifiers['call_timeout'] is False
        assert modifiers['out_of_bounds'] is False
        assert modifiers['in_bounds'] is False
    
    def test_play_with_timeout_modifier(self):
        """Test parsing play with timeout modifier."""
        play_type, modifiers = parse_play_with_modifiers("7T")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is False
        assert modifiers['call_timeout'] is True
        assert modifiers['out_of_bounds'] is False
        assert modifiers['in_bounds'] is False
    
    def test_play_with_out_of_bounds_modifier(self):
        """Test parsing play with out-of-bounds modifier."""
        play_type, modifiers = parse_play_with_modifiers("7+")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is False
        assert modifiers['call_timeout'] is False
        assert modifiers['out_of_bounds'] is True
        assert modifiers['in_bounds'] is False
    
    def test_play_with_in_bounds_modifier(self):
        """Test parsing play with in-bounds modifier."""
        play_type, modifiers = parse_play_with_modifiers("7-")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is False
        assert modifiers['call_timeout'] is False
        assert modifiers['out_of_bounds'] is False
        assert modifiers['in_bounds'] is True
    
    def test_play_with_multiple_modifiers(self):
        """Test parsing play with multiple modifiers (should handle all)."""
        play_type, modifiers = parse_play_with_modifiers("7ST")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is True
        assert modifiers['call_timeout'] is True
        assert modifiers['out_of_bounds'] is False
        assert modifiers['in_bounds'] is False
    
    def test_play_with_all_modifiers(self):
        """Test parsing play with all possible modifiers."""
        play_type, modifiers = parse_play_with_modifiers("7+ST-")
        assert play_type == PlayType.MEDIUM_PASS
        assert modifiers['call_spike'] is True
        assert modifiers['call_timeout'] is True
        assert modifiers['out_of_bounds'] is True
        assert modifiers['in_bounds'] is True
    
    def test_standalone_spike(self):
        """Test parsing standalone spike play."""
        play_type, modifiers = parse_play_with_modifiers("S")
        assert play_type == PlayType.SPIKE_BALL
        # Standalone spike should not have spike modifier
        assert modifiers['call_spike'] is False
        assert modifiers['call_timeout'] is False
        assert modifiers['out_of_bounds'] is False
        assert modifiers['in_bounds'] is False
    
    def test_different_play_types(self):
        """Test parsing various play types."""
        plays = [
            ("1", PlayType.LINE_PLUNGE),
            ("2", PlayType.OFF_TACKLE),
            ("3", PlayType.END_RUN),
            ("4", PlayType.DRAW),
            ("5", PlayType.SCREEN),
            ("6", PlayType.SHORT_PASS),
            ("7", PlayType.MEDIUM_PASS),
            ("8", PlayType.LONG_PASS),
            ("9", PlayType.TE_SHORT_LONG),
            ("Q", PlayType.QB_SNEAK),
            ("K", PlayType.QB_KNEEL),
            ("P", PlayType.PUNT),
            ("F", PlayType.FIELD_GOAL),
        ]
        for play_char, expected_type in plays:
            play_type, _modifiers = parse_play_with_modifiers(play_char)
            assert play_type == expected_type, f"Play {play_char} should map to {expected_type}"
    
    def test_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Play string cannot be empty"):
            parse_play_with_modifiers("")
    
    def test_case_insensitivity(self):
        """Test that parsing is case-insensitive."""
        play_type1, _ = parse_play_with_modifiers("7s")
        play_type2, _ = parse_play_with_modifiers("7S")
        assert play_type1 == play_type2 == PlayType.MEDIUM_PASS
    
    def test_modifier_order_irrelevant(self):
        """Test that modifier order doesn't matter."""
        play_type1, mods1 = parse_play_with_modifiers("7ST")
        play_type2, mods2 = parse_play_with_modifiers("7TS")
        assert play_type1 == play_type2
        assert mods1 == mods2


class TestModifierEdgeCases:
    """Edge case tests for modifiers."""
    
    def test_spike_on_fourth_down_backend(self):
        """Backend should allow spike on any down (UI may restrict)."""
        # This tests that backend doesn't reject spike on 4th down
        # The engine will handle the turnover if needed
        _play_type, modifiers = parse_play_with_modifiers("7S")
        assert modifiers['call_spike'] is True
    
    def test_timeout_without_timeouts_backend(self):
        """Backend should allow timeout modifier even if no timeouts left."""
        # The engine will handle whether timeout succeeds
        _play_type, modifiers = parse_play_with_modifiers("7T")
        assert modifiers['call_timeout'] is True
    
    def test_out_of_bounds_with_in_bounds(self):
        """Both out-of-bounds and in-bounds modifiers can be set."""
        # This is technically possible but UI should prevent it
        _play_type, modifiers = parse_play_with_modifiers("7+-")
        assert modifiers['out_of_bounds'] is True
        assert modifiers['in_bounds'] is True


class TestModifierIntegration:
    """Integration tests for modifier execution via API."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def game_with_human_on_offense(self, client):
        """Create a game where human is guaranteed to be on offense."""
        # Create game
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads",
            "season": "2026",
            "play_as_home": True,
        })
        assert response.status_code == 200
        game_data = response.json()
        game_id = game_data["game_id"]
        
        # Coin toss - ensure human receives and plays offense
        response = client.post("/api/game/coin-toss", json={
            "game_id": game_id,
            "player_won": True,
            "player_kicks": False,  # Human receives
            "human_plays_offense": True,
        })
        assert response.status_code == 200
        
        # Keep this modifier fixture deterministic: a random return turnover or
        # pending kickoff foul does not establish the required offensive state.
        with patch("paydirt.game_engine.roll_chart_dice", return_value=(24, "Fixture kickoff")):
            response = client.post("/api/game/kickoff", json={
                "game_id": game_id,
                "kickoff_spot": 35,
            })
        assert response.status_code == 200
        
        # Verify human is on offense
        response = client.get(f"/api/game/state/{game_id}")
        assert response.status_code == 200
        game_state = response.json()
        assert game_state["player_offense"] is True
        
        return game_id
    
    def test_execute_simple_play(self, client, game_with_human_on_offense):
        """Test executing a simple play without modifiers."""
        game_id = game_with_human_on_offense
        
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "7",  # Medium pass
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "game_state" in data
    
    def test_execute_play_with_spike_modifier(self, client, game_with_human_on_offense):
        """Test executing a play with spike modifier."""
        game_id = game_with_human_on_offense
        
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "7S",  # Medium pass with spike
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        # The result should indicate spike was applied (if beneficial)
        # or skipped (if not beneficial). We just ensure no error.
    
    def test_execute_play_with_timeout_modifier(self, client, game_with_human_on_offense):
        """Test executing a play with timeout modifier."""
        game_id = game_with_human_on_offense
        
        # Get initial timeouts
        response = client.get(f"/api/game/state/{game_id}")
        initial_state = response.json()
        _initial_timeouts = initial_state["home_timeouts"] if initial_state["human_is_home"] else initial_state["away_timeouts"]
        
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "7T",  # Medium pass with timeout
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check if timeout was used (depends on play outcome)
        # At least ensure no error and game state updated
        assert "result" in data
        assert "game_state" in data
    
    def test_execute_play_with_out_of_bounds_modifier(self, client, game_with_human_on_offense):
        """Test executing a play with out-of-bounds modifier."""
        game_id = game_with_human_on_offense
        
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "7+",  # Medium pass with out-of-bounds
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
    
    def test_execute_play_with_no_huddle(self, client, game_with_human_on_offense):
        """Test executing a play with no_huddle flag."""
        game_id = game_with_human_on_offense
        
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "7",
            "no_huddle": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
    
    def test_execute_play_with_combined_modifiers(self, client, game_with_human_on_offense):
        """Test executing a play with multiple modifiers."""
        game_id = game_with_human_on_offense
        
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "7ST",  # Spike + timeout
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
    
    def test_execute_play_special_teams_with_modifiers(self, client, game_with_human_on_offense):
        """Test that modifiers work with special teams plays."""
        game_id = game_with_human_on_offense
        
        # Punt with timeout (should work, though not typical)
        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "PT",  # Punt with timeout
        })
        # Should not error, but engine may ignore modifier for special teams
        assert response.status_code == 200
    
    def test_invalid_play_string(self, client, game_with_human_on_offense):
        """An unknown call must not silently become a line plunge."""
        game_id = game_with_human_on_offense

        response = client.post("/api/game/execute", json={
            "game_id": game_id,
            "player_play": "X",
        })
        assert response.status_code == 400
        assert "play" in response.json()["detail"].lower()
    
    def test_no_huddle_persistence_across_plays(self, client: TestClient) -> None:
        """Each play receives its own no-huddle request without inheriting it."""
        game_id = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": True,
        }).json()["game_id"]
        game = games[game_id]
        engine, state = game["engine"], game["engine"].state
        game["is_kickoff"] = False
        state.is_home_possession = True
        state.ball_position, state.down, state.yards_to_go = 50, 1, 10
        state.defense_team.defense.modifiers = {}
        state.possession_team.offense.medium_pass = {26: "5"}
        try:
            # Keep both real plays on offense: a random turnover/penalty makes
            # a second execute request invalid for reasons unrelated to huddle.
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Pass26")),
                  patch.object(engine, "run_play_with_penalty_procedure",
                               wraps=engine.run_play_with_penalty_procedure) as execute):
                first = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "7", "cpu_play": "A", "no_huddle": True,
                })
                second = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "7", "cpu_play": "A",
                })
            assert first.status_code == second.status_code == 200
            assert [call.kwargs["no_huddle"] for call in execute.call_args_list] == [True, False]
            assert state.ball_position == 60
            assert len(engine.play_log) == 2
        finally:
            client.delete(f"/api/game/{game_id}")

"""The API must expose enforced FG penalties, not the discarded kick's result."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games
from paydirt.play_resolver import DefenseType, PlayType


@pytest.mark.parametrize("kicking_is_home", [True, False])
@pytest.mark.parametrize("reroll", ["F - 7", "40"])
def test_accept_fg_penalty_via_api(kicking_is_home: bool, reroll: str) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": kicking_is_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            game = games[game_id]
            game["is_kickoff"] = False
            game["human_plays_offense"] = True
            game["human_is_home"] = kicking_is_home
            engine = game["engine"]
            engine.state.is_home_possession = kicking_is_home
            engine.state.ball_position = 70
            engine.state.down = 4
            engine.state.yards_to_go = 8
            engine.state.possession_team.special_teams.field_goal.update({22: "DEF 5", 21: reroll})
            with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[
                (22, "Roll22"), (21, "Roll21"),
            ]):
                outcome = engine.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
            engine._last_play_outcome = outcome
            response = client.post("/api/game/penalty-decision", json={
                "game_id": game_id, "accept_penalty": True, "penalty_index": 0,
            })
            assert response.status_code == 200
            data = response.json()
            result = data["result"]
            assert result["new_ball_position"] == 75
            assert result["new_down"] == 4
            assert result["new_yards_to_go"] == 3
            assert not result["scoring"]
            assert not result["turnover"]
            assert not result["possession_changed"]
            assert "4th & 3" in result["description"]
            assert data["game_state"]["player_offense"]
            assert not game["pending_pat"]
            assert not engine.state.scoring_plays
        finally:
            client.delete(f"/api/game/{game_id}")

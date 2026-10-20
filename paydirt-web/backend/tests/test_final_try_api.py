"""A clock-expiring touchdown still offers its try through the web API."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("pat_good", [True, False])
def test_final_play_touchdown_offers_the_pat(human_is_home: bool, pat_good: bool) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": human_is_home,
        })
        game_id = response.json()["game_id"]
        game = games[game_id]
        engine = game["engine"]
        try:
            game["is_kickoff"] = False
            game["human_plays_offense"] = True
            game["human_is_home"] = human_is_home
            engine.state.is_home_possession = human_is_home
            engine.state.quarter, engine.state.time_remaining = 4, 10 / 60
            engine.state.two_minute_warning_called = True
            engine.state.home_score, engine.state.away_score = (14, 21) if human_is_home else (21, 14)
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 94, 2, 6
            engine.state.possession_team.offense.line_plunge[26] = "9"
            engine.state.defense_team.defense.modifiers = {}
            engine.state.possession_team.special_teams.extra_point_no_good = [] if pat_good else [26]
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Roll26")),
                  patch("paydirt.game_engine.random.uniform", return_value=30)):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                })
            assert executed.status_code == 200
            data = executed.json()
            assert data["result"]["touchdown"] is True
            assert data["game_state"]["pending_pat"] is True, "The try must be offered at 0:00"
            assert engine.state.time_remaining == 0
            with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
                tried = client.post("/api/game/extra-point", json={"game_id": game_id})
            assert tried.status_code == 200
            tried_data = tried.json()
            assert tried_data["success"] is pat_good
            scorer = tried_data["new_score_home"] if human_is_home else tried_data["new_score_away"]
            assert scorer == (21 if pat_good else 20)
            assert tried_data["game_state"]["game_over"] is (not pat_good)
            # A game-ending try arms no kickoff; a tying try leads to overtime handling.
            assert tried_data["is_kickoff"] is pat_good
            assert tried_data["game_state"]["is_kickoff"] is pat_good
            state = client.get(f"/api/game/state/{game_id}").json()
            assert state["is_kickoff"] is pat_good and state["game_over"] is (not pat_good)
        finally:
            client.delete(f"/api/game/{game_id}")

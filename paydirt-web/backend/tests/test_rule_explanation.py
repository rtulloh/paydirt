"""API regression coverage for engine-authored special-rule explanations."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


@pytest.mark.parametrize("home_possession", [True, False])
@pytest.mark.parametrize("chart_value", ["OFF 10", "0"])
def test_execute_passes_through_sneak_rule_explanation(home_possession: bool, chart_value: str) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": True,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            game = games[game_id]
            game["is_kickoff"] = False
            engine = game["engine"]
            engine.state.is_home_possession = home_possession
            engine.state.ball_position = 86
            engine.state.down = 4
            engine.state.yards_to_go = 1
            engine.state.possession_team.offense.line_plunge[10] = chart_value
            request = {
                "game_id": game_id,
                "player_play": "Q" if home_possession else "A",
                "cpu_play": "A" if home_possession else "Q",
            }
            with patch("paydirt.game_engine.roll_chart_dice", return_value=(10, "B1+W0+W0=10")) as dice:
                response = client.post("/api/game/execute", json=request)
            assert response.status_code == 200
            dice.assert_called_once()
            result = response.json()["result"]
            expected = (
                'QB sneak rule: "OFF 10" is treated as no gain. '
                "No penalty is enforced; no re-roll is required."
            ) if chart_value == "OFF 10" else None
            assert result["rule_explanation"] == expected
            assert result["yards"] == 0
            assert not result["pending_penalty_decision"]
            assert engine.state.is_home_possession != home_possession
        finally:
            client.delete(f"/api/game/{game_id}")

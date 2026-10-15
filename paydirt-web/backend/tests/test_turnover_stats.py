"""The API exposes engine turnover counts without recalculating football stats."""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from routes import games
from paydirt.play_resolver import DefenseType, PlayType


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("raw,component", [("INT 10", "interceptions_thrown"), ("F +2", "fumbles_lost")])
def test_api_returns_real_engine_turnovers(home: bool, raw: str, component: str) -> None:
    client = TestClient(app)
    response = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"})
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    try:
        engine = games[game_id]["engine"]
        state = engine.state
        state.is_home_possession = home
        state.ball_position = 50
        state.defense_team.defense.modifiers.clear()
        state.possession_team.offense.medium_pass[16] = raw
        state.possession_team.peripheral.fumble_recovered_range = (10, 19)
        state.defense_team.special_teams.interception_return[22] = "0"
        with (
            patch("paydirt.play_resolver.roll_chart_dice", side_effect=[
                (16, "synthetic"), (22, "synthetic recovery"),
            ]),
            patch("paydirt.game_engine.roll_chart_dice", return_value=(22, "synthetic")),
            patch("paydirt.play_resolver.random.choice", side_effect=lambda choices: choices[0]),
        ):
            engine.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
        stats = state.home_stats if home else state.away_stats
        assert getattr(stats, component) == 1
        response = client.get(f"/api/game/state/{game_id}")
        assert response.status_code == 200
        payload = response.json()
        key, other = ("home_stats", "away_stats") if home else ("away_stats", "home_stats")
        assert payload[key]["turnovers"] == 1
        assert stats.turnovers == 1
        assert payload[other]["turnovers"] == 0
    finally:
        client.delete(f"/api/game/{game_id}")

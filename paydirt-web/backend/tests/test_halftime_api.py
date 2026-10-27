"""Halftime after a quarter-ending score or decision in the web API."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


def _start(client: TestClient, human_is_home: bool) -> tuple[str, dict]:
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads", "season": "2026", "play_as_home": human_is_home,
    })
    game_id = response.json()["game_id"]
    game = games[game_id]
    engine = game["engine"]
    game["is_kickoff"] = False
    game["human_plays_offense"] = True
    game["human_is_home"] = human_is_home
    engine.state.opening_kicking_home = human_is_home  # The human kicked to open.
    engine.state.is_home_possession = human_is_home
    engine.state.quarter, engine.state.time_remaining = 2, 20 / 60
    engine.state.two_minute_warning_called = True
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 94, 2, 6
    engine.state.defense_team.defense.modifiers = {}
    engine.state.possession_team.special_teams.extra_point_no_good = []
    return game_id, game


@pytest.mark.parametrize("human_is_home", [True, False])
def test_touchdown_that_ends_the_half_waits_for_halftime_and_the_other_kicker(human_is_home: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home)
        engine = game["engine"]
        try:
            engine.state.possession_team.offense.line_plunge[26] = "9"
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Roll26")),
                  patch("paydirt.game_engine.random.uniform", return_value=30)):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                }).json()
            assert executed["result"]["touchdown"] is True
            assert executed["game_state"]["pending_pat"] is True
            assert executed["game_state"]["quarter"] == 3
            with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
                tried = client.post("/api/game/extra-point", json={"game_id": game_id}).json()
            assert tried["game_state"]["halftime_pending"] is True
            assert tried["game_state"]["is_kickoff"] is True
            # The second-half kicker is the opening receiver, not the scoring team.
            assert tried["game_state"]["possession"] == ("away" if human_is_home else "home")
            with patch("paydirt.game_engine.random.uniform", return_value=8):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            assert kicked["game_state"]["halftime_pending"] is False
            assert engine.state.is_home_possession is human_is_home, "the scoring team receives the second half"
            assert engine.state.quarter == 3
        finally:
            client.delete(f"/api/game/{game_id}")


def test_penalty_decision_that_ends_the_half_reports_halftime() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True)
        engine = game["engine"]
        try:
            engine.state.ball_position = 50
            engine.state.possession_team.offense.line_plunge.update({26: "DEF 5", 27: "4"})
            with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(26, "Roll26"), (27, "Roll27")]):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                }).json()
            assert executed["result"]["pending_penalty_decision"] is True
            assert executed["game_state"]["halftime_pending"] is False
            with patch("paydirt.game_engine.random.uniform", return_value=30):
                decided = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": False, "penalty_index": 0,
                }).json()
            assert decided["result"]["half_changed"] is True
            assert decided["game_state"]["halftime_pending"] is True
            assert decided["game_state"]["quarter"] == 3
        finally:
            client.delete(f"/api/game/{game_id}")

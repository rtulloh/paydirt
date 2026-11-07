"""API forwards the engine's penalty previews and applies the selected choice."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games

from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType


@pytest.mark.parametrize("human_home", [True, False])
@pytest.mark.parametrize("accept_penalty", [True, False])
def test_incomplete_preview_and_decision_match(human_home: bool, accept_penalty: bool) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks",
            "season": "2026", "play_as_home": human_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            record = games[game_id]
            record["is_kickoff"] = False
            state = record["engine"].state
            state.is_home_possession = not human_home
            state.quarter, state.time_remaining = 3, 10
            state.ball_position, state.down, state.yards_to_go = 77, 3, 9
            before = deepcopy(state)
            choice = PenaltyChoice(
                PlayResult(ResultType.INCOMPLETE, description="Incomplete pass"),
                [PenaltyOption("OFF", "OFF 5", 5, "Offensive penalty, 5 yards")],
                offended_team="defense",
            )
            with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
                response = client.post("/api/game/execute", json={"game_id": game_id, "player_play": "A", "cpu_play": "6"})
            assert response.status_code == 200
            assert state == before
            previews = response.json()["result"]["penalty_choice"]
            assert choice.play_result_preview is None
            assert previews["play_result_preview"].startswith("Incomplete pass — 4th & 9 at ")
            assert previews["penalty_options"][0]["result_preview"].startswith("3rd & 14 at ")
            response = client.post("/api/game/penalty-decision", json={"game_id": game_id, "accept_penalty": accept_penalty, "penalty_index": 0})
            assert response.status_code == 200
            result = response.json()["game_state"]
            expected = (72, 3, 14) if accept_penalty else (77, 4, 9)
            assert (result["ball_position"], result["down"], result["yards_to_go"]) == expected
        finally:
            client.delete(f"/api/game/{game_id}")

"""Every displayed defensive formation must execute for either controller."""

import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games, get_defense_type_from_key

from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, ResultType


@pytest.mark.parametrize("key,expected", [
    ("A", DefenseType.STANDARD), ("B", DefenseType.SHORT_YARDAGE),
    ("C", DefenseType.SPREAD), ("D", DefenseType.SHORT_PASS),
    ("E", DefenseType.LONG_PASS), ("F", DefenseType.BLITZ),
])
@pytest.mark.parametrize("lowercase", [False, True])
def test_all_defensive_keys_are_supported(key: str, expected: DefenseType, lowercase: bool) -> None:
    assert get_defense_type_from_key(key.lower() if lowercase else key) == expected


@pytest.mark.parametrize("human_home", [True, False])
@pytest.mark.parametrize("key,formation", [
    ("A", DefenseType.STANDARD), ("B", DefenseType.SHORT_YARDAGE),
    ("C", DefenseType.SPREAD), ("D", DefenseType.SHORT_PASS),
    ("E", DefenseType.LONG_PASS), ("F", DefenseType.BLITZ),
])
def test_cpu_preview_preserves_selected_formation(human_home: bool, key: str, formation: DefenseType) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks",
            "season": "2026", "play_as_home": human_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            game = games[game_id]
            game["engine"].state.is_home_possession = human_home
            with patch.object(game["ai"], "select_defense", return_value=formation):
                response = client.post("/api/game/cpu-play", json={"game_id": game_id})
            assert response.status_code == 200
            assert response.json() == {"cpu_play": key}
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("human_home", [True, False])
@pytest.mark.parametrize("human_offense", [True, False])
@pytest.mark.parametrize("key", ["F", "f", "G"])
def test_execute_blitz_or_reject_unknown_without_advancing(
    human_home: bool, human_offense: bool, key: str,
) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks",
            "season": "2026", "play_as_home": human_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            game = games[game_id]
            game["is_kickoff"] = False
            engine = game["engine"]
            engine.state.is_home_possession = human_home == human_offense
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 1, 1, 10
            before = deepcopy(engine.state)
            with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
                PlayResult(ResultType.YARDS, yards=3),
            )) as resolve:
                response = client.post("/api/game/execute", json={
                    "game_id": game_id,
                    "player_play": "1" if human_offense else key,
                    "cpu_play": key if human_offense else "1",
                })
            if key == "G":
                assert response.status_code == 400
                assert response.json()["detail"] == "Invalid defensive play: 'G'"
                resolve.assert_not_called()
                assert engine.state == before
                assert not engine.play_log
            else:
                assert response.status_code == 200
                assert resolve.call_args.args[3] == DefenseType.BLITZ
                assert engine.state.ball_position == 4
                assert engine.state.down == 2
                assert len(engine.play_log) == 1
                assert response.json()["game_state"]["ball_position"] == 4
        finally:
            client.delete(f"/api/game/{game_id}")

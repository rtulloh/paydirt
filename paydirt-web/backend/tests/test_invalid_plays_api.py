"""Reject malformed play calls before advancing a public-sample game."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games, get_defense_type_from_key, parse_play_with_modifiers

from paydirt.play_resolver import DefenseType, PlayType


@pytest.fixture
def game():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads", "opponent_team": "Thunderhawks",
        "season": "2026", "play_as_home": True,
    })
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    game = games[game_id]
    game["engine"].state.ball_position = 35
    yield client, game_id, game
    games.pop(game_id, None)


@pytest.mark.parametrize("human_offense,player_play,cpu_play", [
    (True, "", "A"), (True, "X", "A"), (True, "7X", "A"),
    (True, "77", "A"), (True, "7 ", "A"), (True, "7", ""),
    (True, "7", "Z"), (True, "7", "AA"),
    (False, "", "1"), (False, "Z", "1"), (False, "A+", "1"),
    (False, "A", ""), (False, "A", "X"), (False, "A", "7T"),
    (False, "Z", None),
])
def test_invalid_execute_calls_do_not_change_state(game, human_offense, player_play, cpu_play):
    client, game_id, record = game
    record["engine"].state.is_home_possession = human_offense
    before = deepcopy(record["engine"].state)
    history = deepcopy(record["engine"].offensive_call_history)
    with patch.object(record["ai"], "select_offense", wraps=record["ai"].select_offense) as select:
        response = client.post("/api/game/execute", json={
            "game_id": game_id, "player_play": player_play, "cpu_play": cpu_play,
        })
    assert response.status_code == 400
    assert "play" in response.json()["detail"].lower()
    assert record["engine"].state == before
    assert record["engine"].offensive_call_history == history
    assert not record.get("play_history")
    select.assert_not_called()


@pytest.mark.parametrize("offense,defense", [
    ("", "A"), ("X", "A"), ("1S", "A"), ("1", ""),
    ("1", "Z"), ("1", "AA"),
])
def test_invalid_two_point_calls_do_not_change_state(game, offense, defense):
    client, game_id, record = game
    before = deepcopy(record["engine"].state)
    response = client.post("/api/game/two-point", json={
        "game_id": game_id, "offense_play": offense, "defense_play": defense,
    })
    assert response.status_code == 400
    assert "play" in response.json()["detail"].lower()
    assert record["engine"].state == before
    assert not record.get("is_kickoff", False)


def test_invalid_fourth_down_defense_does_not_request_cpu_selection(game):
    client, game_id, record = game
    state = record["engine"].state
    state.is_home_possession = False
    state.down = 4
    before = deepcopy(state)
    with patch.object(record["ai"], "select_offense_with_clock_management") as select:
        response = client.post("/api/game/execute", json={
            "game_id": game_id, "player_play": "Z",
        })
    assert response.status_code == 400
    assert state == before
    select.assert_not_called()


@pytest.mark.parametrize("key,expected", [
    ("1", PlayType.LINE_PLUNGE), ("2", PlayType.OFF_TACKLE),
    ("3", PlayType.END_RUN), ("4", PlayType.DRAW), ("5", PlayType.SCREEN),
    ("6", PlayType.SHORT_PASS), ("7", PlayType.MEDIUM_PASS),
    ("8", PlayType.LONG_PASS), ("9", PlayType.TE_SHORT_LONG),
    ("q", PlayType.QB_SNEAK), ("k", PlayType.QB_KNEEL),
    ("p", PlayType.PUNT), ("f", PlayType.FIELD_GOAL), ("s", PlayType.SPIKE_BALL),
])
def test_valid_offensive_calls_remain_available(game, key, expected):
    play, _ = parse_play_with_modifiers(key)
    assert play == expected
    client, game_id, record = game
    record["engine"].state.is_home_possession = True
    engine = record["engine"]
    with patch.object(engine, "run_play_with_penalty_procedure", wraps=engine.run_play_with_penalty_procedure) as run:
        response = client.post("/api/game/execute", json={
            "game_id": game_id, "player_play": key, "cpu_play": "A",
        })
    assert response.status_code == 200
    assert run.call_args.args[0] == expected


@pytest.mark.parametrize("key,expected", [
    ("a", DefenseType.STANDARD), ("b", DefenseType.SHORT_YARDAGE),
    ("c", DefenseType.SPREAD), ("d", DefenseType.SHORT_PASS),
    ("e", DefenseType.LONG_PASS),
])
def test_valid_defensive_calls_remain_available(game, key, expected):
    assert get_defense_type_from_key(key) == expected
    client, game_id, record = game
    record["engine"].state.is_home_possession = False
    engine = record["engine"]
    with patch.object(engine, "run_play_with_penalty_procedure", wraps=engine.run_play_with_penalty_procedure) as run:
        response = client.post("/api/game/execute", json={
            "game_id": game_id, "player_play": key, "cpu_play": "7",
        })
    assert response.status_code == 200
    assert run.call_args.args[:2] == (PlayType.MEDIUM_PASS, expected)


@pytest.mark.parametrize("play", ["7", "7sT", "7+S", "7+ST-", "pT"])
def test_valid_execute_calls_and_modifier_combinations(game, play):
    client, game_id, record = game
    record["engine"].state.is_home_possession = True
    response = client.post("/api/game/execute", json={
        "game_id": game_id, "player_play": play, "cpu_play": "a",
    })
    assert response.status_code == 200
    assert response.json()["player_play"] == play.upper()


def test_valid_two_point_calls_are_accepted(game):
    client, game_id, record = game
    record["pending_pat"] = True
    record["engine"].state.ball_position = 98
    response = client.post("/api/game/two-point", json={
        "game_id": game_id, "offense_play": "q", "defense_play": "a",
    })
    assert response.status_code == 200

"""Conversion endpoints only accept a try owed after a touchdown."""

from collections.abc import Iterator
from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games


@pytest.fixture
def game() -> Iterator[tuple[TestClient, str, dict[str, Any]]]:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads",
        "opponent_team": "Thunderhawks",
        "season": "2026",
        "play_as_home": True,
    })
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    record = games[game_id]
    yield client, game_id, record
    games.pop(game_id, None)


def _request_conversion(client: TestClient, game_id: str, conversion: str) -> Any:
    if conversion == "extra_point":
        return client.post("/api/game/extra-point", json={"game_id": game_id})
    return client.post("/api/game/two-point", json={
        "game_id": game_id,
        "offense_play": "q",
        "defense_play": "a",
    })


def _conversion_state(record: dict[str, Any]) -> dict[str, Any]:
    engine = record["engine"]
    return deepcopy({
        "state": engine.state,
        "play_log": engine.play_log,
        "offensive_call_history": engine.offensive_call_history,
        "play_history": record.get("play_history", []),
        "pending_pat": record.get("pending_pat", False),
        "is_kickoff": record.get("is_kickoff", False),
    })


@pytest.mark.parametrize("conversion", ["extra_point", "two_point"])
@pytest.mark.parametrize("game_over", [False, True])
def test_conversion_without_pending_try_is_rejected_without_mutation(
    game: tuple[TestClient, str, dict[str, Any]], conversion: str, game_over: bool
) -> None:
    client, game_id, record = game
    record["engine"].state.game_over = game_over
    before = _conversion_state(record)

    response = _request_conversion(client, game_id, conversion)

    assert response.status_code == 400
    assert "pending" in response.json()["detail"].lower()
    assert _conversion_state(record) == before


@pytest.mark.parametrize(
    "conversion,game_over",
    [("extra_point", False), ("two_point", False), ("two_point", True)],
)
def test_pending_conversion_is_single_use_and_allowed_when_game_is_over(
    game: tuple[TestClient, str, dict[str, Any]], conversion: str, game_over: bool
) -> None:
    client, game_id, record = game
    record["pending_pat"] = True
    record["engine"].state.game_over = game_over

    response = _request_conversion(client, game_id, conversion)
    assert response.status_code == 200
    assert record["pending_pat"] is False

    after_first_try = _conversion_state(record)
    duplicate = _request_conversion(client, game_id, conversion)

    assert duplicate.status_code == 400
    assert "pending" in duplicate.json()["detail"].lower()
    assert _conversion_state(record) == after_first_try


def test_two_point_try_is_rejected_when_season_disallows_it(
    game: tuple[TestClient, str, dict[str, Any]],
) -> None:
    client, game_id, record = game
    record["pending_pat"] = True
    record["engine"].season_rules.two_point_conversion = False
    before = _conversion_state(record)

    response = _request_conversion(client, game_id, "two_point")

    assert response.status_code == 400
    assert "two-point" in response.json()["detail"].lower()
    assert _conversion_state(record) == before
    assert record["pending_pat"] is True


def test_extra_point_remains_available_when_two_point_conversion_is_disallowed(
    game: tuple[TestClient, str, dict[str, Any]],
) -> None:
    client, game_id, record = game
    record["pending_pat"] = True
    record["engine"].season_rules.two_point_conversion = False

    response = _request_conversion(client, game_id, "extra_point")

    assert response.status_code == 200
    assert record["pending_pat"] is False

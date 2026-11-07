"""FLOW-013: web defensive timeout requests use the existing engine procedure."""

from collections.abc import Iterator
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games

from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType


@pytest.fixture(params=[True, False], ids=["human-home", "human-away"])
def game(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, str, dict]]:
    """Use public teams with a deterministic synthetic play and clock."""
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks",
            "season": "2026", "play_as_home": request.param,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        record = games[game_id]
        record["is_kickoff"] = False
        state = record["engine"].state
        state.is_home_possession = not request.param
        state.ball_position, state.down, state.yards_to_go = 40, 1, 10
        state.quarter, state.time_remaining = 4, 2
        state.two_minute_warning_called = True
        monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: 30)
        yield client, game_id, record
        games.pop(game_id, None)


@pytest.mark.parametrize("case", ["eligible", "incomplete", "oob", "empty", "unrequested"])
def test_defensive_timeout_ownership_and_eligibility(
    game: tuple[TestClient, str, dict], monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    client, game_id, record = game
    engine = record["engine"]
    result = PlayResult(ResultType.INCOMPLETE if case == "incomplete" else ResultType.YARDS, yards=4)
    result.out_of_bounds = case == "oob"
    if case == "empty":
        engine.state.home_timeouts = engine.state.away_timeouts = 0
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(result))
    response = client.post("/api/game/execute", json={
        "game_id": game_id, "player_play": "A", "cpu_play": "6",
        "call_defensive_timeout": case != "unrequested",
    })
    assert response.status_code == 200
    data = response.json()
    used = case == "eligible"
    assert engine.state.defense_timeouts == (0 if case == "empty" else 3 - int(used))
    assert engine.state.offense_timeouts == (0 if case == "empty" else 3)
    assert data["result"].get("defensive_timeout_used", False) is used
    assert ("Defensive timeout: clock stopped." in data["result"]["description"]) is used
    if used:
        assert engine.state.time_remaining == pytest.approx(2 - 10 / 60, abs=.001)
    elif case in ("empty", "unrequested"):
        assert engine.state.time_remaining == pytest.approx(1.5)
    assert engine.state.down == 2
    assert len(engine.play_log) == 1


@pytest.mark.parametrize("accept_penalty", [True, False])
def test_defensive_timeout_waits_for_penalty_choice(
    game: tuple[TestClient, str, dict], monkeypatch: pytest.MonkeyPatch, accept_penalty: bool,
) -> None:
    client, game_id, record = game
    engine = record["engine"]
    choice = PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4),
        penalty_options=[PenaltyOption("OFF", "OFF 5", 5, "Synthetic offensive foul")],
        offended_team="defense",
    )
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    executed = client.post("/api/game/execute", json={
        "game_id": game_id, "player_play": "A", "cpu_play": "6",
        "call_defensive_timeout": True,
    })
    assert executed.status_code == 200
    assert executed.json()["result"]["pending_penalty_decision"] is True
    assert engine.state.defense_timeouts == 3
    assert engine.state.time_remaining == 2
    assert engine._last_play_outcome.defensive_timeout_context is not None
    response = client.post("/api/game/penalty-decision", json={
        "game_id": game_id, "accept_penalty": accept_penalty, "penalty_index": 0,
    })
    assert response.status_code == 200
    # Either choice stops the clock for the foul; neither needs a timeout.
    assert engine.state.defense_timeouts == 3
    assert engine.state.offense_timeouts == 3
    assert response.json()["result"].get("defensive_timeout_used", False) is False
    assert len(engine.play_log) == 1


def test_offensive_caller_cannot_spend_opponents_timeout(game: tuple[TestClient, str, dict]) -> None:
    client, game_id, record = game
    engine = record["engine"]
    engine.state.is_home_possession = not engine.state.is_home_possession
    before = deepcopy(engine.state)
    response = client.post("/api/game/execute", json={
        "game_id": game_id, "player_play": "6", "cpu_play": "A",
        "call_defensive_timeout": True,
    })
    assert response.status_code == 400
    assert engine.state == before
    assert not engine.play_log

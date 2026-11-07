"""The web controller must retain engine/AI clock requests for the selected call."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games

from paydirt.play_resolver import PenaltyChoice, PlayResult, PlayType, ResultType


@pytest.fixture(params=[True, False], ids=["human-home", "human-away"])
def cpu_game(request):
    with TestClient(app) as client:
        human_home = request.param
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks",
            "season": "2026", "play_as_home": human_home,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        record = games[game_id]
        record["is_kickoff"] = False
        state = record["engine"].state
        state.is_home_possession = not human_home
        state.home_score = 16 if human_home else 0
        state.away_score = 0 if human_home else 16
        state.quarter, state.time_remaining = 2, 41 / 60
        state.ball_position, state.down, state.yards_to_go = 42, 1, 10
        state.two_minute_warning_called = True
        yield client, game_id, record
        client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("down,endpoint", [(1, "cpu-play"), (4, "cpu-4th-down-decision")])
@pytest.mark.parametrize("flags", [(True, True, False, 0, True), (False, False, False, 0, False)])
def test_preview_retains_one_plan_and_passes_every_option(cpu_game, down, endpoint, flags):
    client, game_id, record = cpu_game
    engine, ai = record["engine"], record["ai"]
    engine.state.down = down
    before = deepcopy(engine.state)
    plan = (PlayType.SCREEN, *flags)
    with patch.object(ai, "select_offense_with_clock_management", return_value=plan) as select:
        for _ in range(2):
            response = (client.post(f"/api/game/{endpoint}", json={"game_id": game_id})
                        if endpoint == "cpu-play" else client.get(f"/api/game/{endpoint}/{game_id}"))
            assert response.status_code == 200
            assert response.json().get("cpu_play", response.json().get("play")) == "5"
        assert engine.state == before
        with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(PlayResult(ResultType.YARDS, yards=1))), patch.object(engine, "run_play_with_penalty_procedure", wraps=engine.run_play_with_penalty_procedure) as run:
            response = client.post("/api/game/execute", json={
                "game_id": game_id, "player_play": "A", "cpu_play": "5",
            })
        assert response.status_code == 200
        assert run.call_args.kwargs["out_of_bounds_designation"] is flags[0]
        assert run.call_args.kwargs["no_huddle"] is flags[1]
        assert run.call_args.kwargs["call_spike"] is flags[4]
        assert run.call_args.kwargs["call_timeout"] is True
        assert select.call_count == 1


@pytest.mark.parametrize("preview", [False, True])
def test_last_minute_completion_keeps_time_and_uses_cpu_timeout(cpu_game, preview):
    client, game_id, record = cpu_game
    engine, ai = record["engine"], record["ai"]
    cpu_home = engine.state.is_home_possession
    with patch.object(ai, "select_offense_with_clock_management", return_value=(PlayType.SCREEN, False, True, False, 0, False)):
        if preview:
            assert client.post("/api/game/cpu-play", json={"game_id": game_id}).status_code == 200
        with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(PlayResult(ResultType.YARDS, yards=13))), patch("paydirt.game_engine.random.uniform", return_value=40):
            response = client.post("/api/game/execute", json={
                "game_id": game_id, "player_play": "E", **({"cpu_play": "5"} if preview else {}),
            })
    assert response.status_code == 200
    assert engine.state.quarter == 2
    # The existing timeout procedure uses 0.167 minutes (10.02 seconds).
    assert engine.state.time_remaining == pytest.approx(41 / 60 - 0.167)
    assert (engine.state.home_timeouts if cpu_home else engine.state.away_timeouts) == 2
    assert (engine.state.away_timeouts if cpu_home else engine.state.home_timeouts) == 3
    assert engine.state.ball_position == 55
    assert len(engine.play_log) == 1


def test_stale_preview_does_not_reuse_old_modifiers(cpu_game):
    client, game_id, record = cpu_game
    engine, ai = record["engine"], record["ai"]
    with patch.object(ai, "select_offense_with_clock_management", return_value=(PlayType.SCREEN, True, True, False, 0, True)):
        assert client.post("/api/game/cpu-play", json={"game_id": game_id}).status_code == 200
    engine.state.quarter, engine.state.time_remaining = 3, 10
    with patch.object(engine, "run_play_with_penalty_procedure", wraps=engine.run_play_with_penalty_procedure) as run:
        response = client.post("/api/game/execute", json={"game_id": game_id, "player_play": "A", "cpu_play": "5"})
    assert response.status_code == 200
    assert run.call_args.kwargs["out_of_bounds_designation"] is False
    assert run.call_args.kwargs["no_huddle"] is False
    assert run.call_args.kwargs["call_spike"] is False
    assert run.call_args.kwargs["call_timeout"] is False


@pytest.mark.parametrize("result_type", [ResultType.YARDS, ResultType.INCOMPLETE])
def test_cpu_defense_requests_useful_timeout_only(cpu_game, result_type):
    client, game_id, record = cpu_game
    engine = record["engine"]
    # Give the leading human the ball; the trailing CPU wants it back.
    engine.state.is_home_possession = not engine.state.is_home_possession
    cpu_home = not engine.state.is_home_possession
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(PlayResult(result_type, yards=3 if result_type == ResultType.YARDS else 0))), patch("paydirt.game_engine.random.uniform", return_value=40):
        response = client.post("/api/game/execute", json={"game_id": game_id, "player_play": "6", "cpu_play": "A"})
    assert response.status_code == 200
    assert engine.state.quarter == 2
    expected_time, expected_budget = (41 / 60 - 0.167, 2) if result_type == ResultType.YARDS else (36 / 60, 3)
    assert engine.state.time_remaining == pytest.approx(expected_time)
    assert (engine.state.home_timeouts if cpu_home else engine.state.away_timeouts) == expected_budget


def test_cpu_punt_keeps_selected_punt_options(cpu_game):
    client, game_id, record = cpu_game
    engine, ai = record["engine"], record["ai"]
    engine.state.down = 4
    with patch.object(ai, "select_offense_with_clock_management", return_value=(PlayType.PUNT, False, False, True, 10, False)):
        assert client.get(f"/api/game/cpu-4th-down-decision/{game_id}").json() == {"decision": "punt", "play": "P"}
    with patch.object(engine, "run_play_with_penalty_procedure", wraps=engine.run_play_with_penalty_procedure) as run:
        response = client.post("/api/game/execute", json={"game_id": game_id, "player_play": "A", "cpu_play": "P"})
    assert response.status_code == 200
    assert run.call_args.kwargs["punt_short_drop"] is True
    assert run.call_args.kwargs["punt_coffin_corner_yards"] == 10


def test_last_chance_call_does_not_silently_become_a_run(cpu_game):
    client, game_id, record = cpu_game
    engine, ai = record["engine"], record["ai"]
    engine.state.time_remaining = 5 / 60
    with patch.object(ai, "select_offense_with_clock_management", return_value=(PlayType.HAIL_MARY, False, True, False, 0, False)):
        response = client.post("/api/game/cpu-play", json={"game_id": game_id})
        assert response.status_code == 200
        assert response.json()["cpu_play"] == "H"
        with patch.object(engine, "run_play_with_penalty_procedure", wraps=engine.run_play_with_penalty_procedure) as run:
            response = client.post("/api/game/execute", json={"game_id": game_id, "player_play": "E", "cpu_play": "H"})
    assert response.status_code == 200
    assert run.call_args.args[0] == PlayType.HAIL_MARY

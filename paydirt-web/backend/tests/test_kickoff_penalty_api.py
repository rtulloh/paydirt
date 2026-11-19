"""Kickoff return penalties in the web API: assessed automatically; the recovered-fumble choice is offered."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


def _start(client: TestClient, human_is_home: bool, human_kicks: bool, reroll_cell: str = "30") -> tuple[str, dict]:
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads", "season": "2026", "play_as_home": human_is_home,
    })
    game_id = response.json()["game_id"]
    game = games[game_id]
    engine = game["engine"]
    game["is_kickoff"] = True
    game["human_is_home"] = human_is_home
    kicking_home = human_is_home if human_kicks else not human_is_home
    engine.state.is_home_possession = kicking_home
    kicker = engine.state.home_chart if kicking_home else engine.state.away_chart
    receiver = engine.state.away_chart if kicking_home else engine.state.home_chart
    kicker.special_teams.kickoff.clear()
    receiver.special_teams.kickoff_return.clear()
    receiver.peripheral.fumble_recovered_range = (10, 27)
    kicker.special_teams.kickoff[24] = "60"
    receiver.special_teams.kickoff_return.update({31: "OFF 15", 13: reroll_cell})
    return game_id, game


def rolls(*values):
    return [(value, f"Roll{value}") for value in values]


def test_safety_free_kick_uses_the_own_20_not_the_request_default() -> None:
    with TestClient(app) as client:
        created = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": True,
        }).json()
        game_id = created["game_id"]
        game = games[game_id]
        engine = game["engine"]
        try:
            game["is_kickoff"] = True
            game["safety_free_kick"] = True
            engine.state.ball_position = 20  # setup_for_kickoff(from_safety=True)
            engine.state.is_home_possession = True
            with patch.object(engine, "kickoff", wraps=engine.kickoff) as kick:
                response = client.post(
                    "/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}
                )
            assert response.status_code == 200
            assert kick.call_args.kwargs["kickoff_spot"] == 20
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("human_kicks", [True, False])
def test_return_penalty_is_assessed_without_a_prompt(human_is_home: bool, human_kicks: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_kicks)
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            assert kicked["result"]["pending_penalty_decision"] is False
            assert kicked["result"]["penalty_choice"] is None
            assert kicked["game_state"]["ball_position"] == 20
            assert kicked["game_state"]["is_kickoff"] is False
            kicking_home = human_is_home if human_kicks else not human_is_home
            assert engine.state.is_home_possession is not kicking_home
            assert kicked["game_state"]["player_offense"] is (not human_kicks)
        finally:
            client.delete(f"/api/game/{game_id}")


def test_human_kicker_chooses_after_recovering_the_reroll_fumble() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_kicks=True, reroll_cell="F + 17")
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13, 30)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            result = kicked["result"]
            assert result["pending_penalty_decision"] is True
            assert result["penalty_choice"]["kick_phase"] == "return_fumble"
            assert result["penalty_choice"]["offended_team"] == "defense"
            assert "22" in result["penalty_choice"]["play_result_preview"]
            assert result["penalty_choice"]["penalty_options"][0]["result_preview"] == "1st and 10 at MCT 11"
            with patch("paydirt.game_engine.random.uniform", return_value=8):
                decided = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": False, "penalty_index": 0,
                }).json()
            assert decided["game_state"]["possession"] == "home"
            assert decided["game_state"]["ball_position"] == 78
            assert engine.state.is_home_possession is True
        finally:
            client.delete(f"/api/game/{game_id}")


def test_cpu_kicker_keeps_the_recovery_immediately() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_kicks=False, reroll_cell="F + 17")
        engine = game["engine"]
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, 13, 30)),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id, "kickoff_spot": 35}).json()
            assert kicked["result"]["pending_penalty_decision"] is False
            assert engine.state.is_home_possession is False  # The CPU kicker (away) keeps the ball.
            assert kicked["game_state"]["ball_position"] == 78
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("return_cell, touchdown", [("110", True), ("F", True), ("12", False)])
@pytest.mark.parametrize("human_scores", [True, False])
def test_finalized_kickoff_publishes_owed_try_and_restores_it(human_is_home, return_cell, touchdown, human_scores):
    """The kickoff route must publish the same engine follow-up as a scrimmage TD."""
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_kicks=(return_cell == "F") == human_scores)
        restored_id = None
        engine = game["engine"]
        kicking_home = human_is_home if (return_cell == "F") == human_scores else not human_is_home
        kicker = engine.state.home_chart if kicking_home else engine.state.away_chart
        receiver = engine.state.away_chart if kicking_home else engine.state.home_chart
        kicker.special_teams.kickoff[24] = "66"
        receiver.special_teams.kickoff_return[31] = return_cell
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, *([37] if return_cell == "F" else []))),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                response = client.post("/api/game/kickoff", json={"game_id": game_id})
            assert response.status_code == 200
            kicked = response.json()
            assert kicked["result"]["touchdown"] is touchdown
            assert kicked["game_state"]["pending_pat"] is touchdown
            assert kicked["game_state"]["is_kickoff"] is False
            assert kicked["game_state"]["player_offense"] is human_scores
            before_score = (engine.state.home_score, engine.state.away_score)
            assert sum(before_score) == (6 if touchdown else 0)
            saved = client.post(f"/api/game/checkpoint/{game_id}")
            assert saved.status_code == 200
            restored = client.post("/api/game/restore", json=saved.json())
            assert restored.status_code == 200
            restored = restored.json()
            restored_id = restored["game_id"]
            assert restored["game_state"]["pending_pat"] is touchdown
            assert restored["game_state"]["player_offense"] is human_scores
            assert (restored["game_state"]["home_score"], restored["game_state"]["away_score"]) == before_score
            if touchdown:
                tried = client.post("/api/game/extra-point", json={"game_id": restored_id})
                assert tried.status_code == 200
                assert tried.json()["game_state"]["pending_pat"] is False
                assert tried.json()["game_state"]["is_kickoff"] is True
                repeated = client.post("/api/game/extra-point", json={"game_id": restored_id})
                assert repeated.status_code == 400
        finally:
            client.delete(f"/api/game/{game_id}")
            if restored_id:
                client.delete(f"/api/game/{restored_id}")


@pytest.mark.parametrize("touchdown,saved_pending_pat", [(True, False), (True, True), (False, False)])
def test_restore_repairs_only_an_engine_owed_try(touchdown, saved_pending_pat):
    """Recover the canonical checkpoint emitted by the pre-FLOW037 kickoff route."""
    from dataclasses import asdict

    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_kicks=True)
        engine = game["engine"]
        engine.state.quarter = 2
        engine.state.time_remaining = 141 / 60
        engine.state.home_chart.special_teams.kickoff[24] = "66"
        engine.state.away_chart.special_teams.kickoff_return[31] = "F" if touchdown else "12"
        restored_id = None
        try:
            with (patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(24, 31, *([37] if touchdown else []))),
                  patch("paydirt.game_engine.random.uniform", return_value=8)):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id})
            assert kicked.status_code == 200
            assert kicked.json()["result"]["touchdown"] is touchdown
            game["pending_pat"] = saved_pending_pat
            if touchdown and not saved_pending_pat:
                engine.state.ball_position = 99  # Exact old route: TD credited, PAT setup omitted.
            before = {key: getattr(engine.state, key) for key in (
                "quarter", "time_remaining", "is_home_possession", "home_score", "away_score")}
            stats = [asdict(engine.state.home_stats), asdict(engine.state.away_stats)]
            checkpoint = client.post(f"/api/game/checkpoint/{game_id}")
            assert checkpoint.status_code == 200
            response = client.post("/api/game/restore", json=checkpoint.json())
            assert response.status_code == 200
            restored_id = response.json()["game_id"]
            restored = games[restored_id]["engine"]
            assert response.json()["game_state"]["pending_pat"] is touchdown
            assert response.json()["game_state"]["is_kickoff"] is False
            assert {key: getattr(restored.state, key) for key in before} == before
            assert [asdict(restored.state.home_stats), asdict(restored.state.away_stats)] == stats
            if touchdown:
                assert restored.state.ball_position == 98
                assert restored.pending_post_score_action() == "try"
                tried = client.post("/api/game/extra-point", json={"game_id": restored_id})
                assert tried.status_code == 200
                assert tried.json()["game_state"]["pending_pat"] is False
                score = (restored.state.home_score, restored.state.away_score)
                assert client.post("/api/game/extra-point", json={"game_id": restored_id}).status_code == 400
                assert (restored.state.home_score, restored.state.away_score) == score
            else:
                assert restored.pending_post_score_action() is None
                assert client.post("/api/game/extra-point", json={"game_id": restored_id}).status_code == 400
        finally:
            client.delete(f"/api/game/{game_id}")
            if restored_id:
                client.delete(f"/api/game/{restored_id}")

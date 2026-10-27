"""Pending penalty outcomes must not move the ball or arm scoring before the choice.

Synthetic chart cells on public 2026 teams; dice are patched. The engine owns
every spot/score change; the API may only react to finalized outcomes.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


def _start(client: TestClient, human_is_home: bool, human_offense: bool) -> tuple[str, dict]:
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads", "season": "2026", "play_as_home": human_is_home,
    })
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    game = games[game_id]
    game["is_kickoff"] = False
    game["human_plays_offense"] = human_offense
    game["human_is_home"] = human_is_home
    engine = game["engine"]
    engine.state.is_home_possession = human_is_home == human_offense
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 90, 1, 10
    engine.state.defense_team.defense.modifiers = {}
    return game_id, game


def _defensive_chart_penalty(engine) -> None:
    engine.state.defense_team.defense.modifiers = {
        (letter, row): {column: "DEF 5" for column in range(1, 10)}
        for letter in "ABCDEF" for row in range(1, 6)
    }


def _assert_untouched(game, response_json: dict) -> None:
    engine = game["engine"]
    result = response_json["result"]
    assert result["pending_penalty_decision"] is True
    assert result["touchdown"] is False
    assert result["scoring"] is False
    assert response_json["game_state"]["pending_pat"] is False
    assert not game.get("pending_pat")
    assert (engine.state.ball_position, engine.state.down, engine.state.yards_to_go) == (90, 1, 10)
    assert engine.state.home_score == engine.state.away_score == 0
    assert not engine.state.scoring_plays


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("accept_penalty", [True, False])
def test_human_offense_goal_crossing_gain_with_defensive_flag(human_is_home: bool, accept_penalty: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_offense=True)
        engine = game["engine"]
        try:
            engine.state.possession_team.offense.line_plunge[26] = "12"
            _defensive_chart_penalty(engine)
            with patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Roll26")):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                })
            assert executed.status_code == 200
            _assert_untouched(game, executed.json())

            decided = client.post("/api/game/penalty-decision", json={
                "game_id": game_id, "accept_penalty": accept_penalty, "penalty_index": 0,
            })
            assert decided.status_code == 200
            data = decided.json()
            result = data["result"]
            scorer = engine.state.home_stats if human_is_home else engine.state.away_stats
            if accept_penalty:
                assert result["new_ball_position"] == 95  # Half the distance from the 90.
                assert (result["new_down"], result["new_yards_to_go"]) == (1, 5)
                assert result["touchdown"] is False and result["scoring"] is False
                assert data["game_state"]["pending_pat"] is False
                assert engine.state.home_score == engine.state.away_score == 0
                assert scorer.rushing_yards == 0
            else:
                assert result["touchdown"] is True and result["scoring"] is True
                assert data["game_state"]["pending_pat"] is True
                assert "for 2 yards" not in result["description"]
                assert scorer.rushing_yards == 10
                assert [play.play_type for play in engine.state.scoring_plays] == ["TD"]
                assert (engine.state.home_score if human_is_home else engine.state.away_score) == 6
                assert engine.state.ball_position == 98  # PAT setup only after finalization.
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("accept_penalty", [True, False])
def test_human_defense_decides_on_provisional_touchdown_cell(human_is_home: bool, accept_penalty: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_offense=False)
        engine = game["engine"]
        try:
            engine.state.possession_team.offense.line_plunge.update({26: "OFF 10", 27: "TD"})
            with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(26, "Roll26"), (27, "Roll27")]):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "A", "cpu_play": "1",
                })
            assert executed.status_code == 200
            _assert_untouched(game, executed.json())

            decided = client.post("/api/game/penalty-decision", json={
                "game_id": game_id, "accept_penalty": accept_penalty, "penalty_index": 0,
            })
            assert decided.status_code == 200
            data = decided.json()
            result = data["result"]
            if accept_penalty:
                assert result["new_ball_position"] == 80
                assert (result["new_down"], result["new_yards_to_go"]) == (1, 20)
                assert result["touchdown"] is False
                assert data["game_state"]["pending_pat"] is False
                assert not engine.state.scoring_plays
            else:
                assert result["touchdown"] is True
                assert data["game_state"]["pending_pat"] is True
                assert len(engine.state.scoring_plays) == 1
                assert engine.state.ball_position == 98
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("human_is_home", [True, False])
@pytest.mark.parametrize("cpu_offense", [True, False])
def test_cpu_decision_is_applied_before_any_scoring_setup(human_is_home: bool, cpu_offense: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home, human_offense=not cpu_offense)
        engine = game["engine"]
        try:
            if cpu_offense:
                # Human defense committed the foul (offense-chart DEF cell, reroll TD):
                # the CPU offense keeps its touchdown. A defensive-chart foul with a
                # symbolic offensive result is tracked separately as RULE-003.
                engine.state.possession_team.offense.line_plunge.update({26: "DEF 5", 27: "TD"})
                rolls = [(26, "Roll26"), (27, "Roll27")]
                body = {"game_id": game_id, "player_play": "A", "cpu_play": "1"}
            else:
                # Human offense committed the foul: CPU defense erases the touchdown.
                engine.state.possession_team.offense.line_plunge.update({26: "OFF 10", 27: "TD"})
                rolls = [(26, "Roll26"), (27, "Roll27")]
                body = {"game_id": game_id, "player_play": "1", "cpu_play": "A"}
            with patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls):
                executed = client.post("/api/game/execute", json=body)
            assert executed.status_code == 200
            data = executed.json()
            result = data["result"]
            assert result["pending_penalty_decision"] is False
            if cpu_offense:
                assert result["touchdown"] is True
                assert data["game_state"]["pending_pat"] is True
                assert len(engine.state.scoring_plays) == 1
                assert engine.state.ball_position == 98
            else:
                assert result["touchdown"] is False
                assert data["game_state"]["pending_pat"] is False
                assert not engine.state.scoring_plays
                assert (engine.state.ball_position, engine.state.down, engine.state.yards_to_go) == (80, 1, 20)
        finally:
            client.delete(f"/api/game/{game_id}")


def test_finalized_non_scoring_outcome_at_goal_line_is_not_relabeled() -> None:
    """The backend must not infer a touchdown from the spot after a decision."""
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_offense=True)
        engine = game["engine"]
        try:
            engine.state.ball_position, engine.state.yards_to_go = 99, 1
            engine.state.possession_team.offense.line_plunge.update({26: "OFF 10", 27: "0"})
            game["human_plays_offense"] = False  # Defense (human side flag) decides.
            with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(26, "Roll26"), (27, "Roll27")]):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                })
            assert executed.status_code == 200
            with patch("routes.cpu_should_accept_penalty", return_value=(True, 0)):
                decided = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": False, "penalty_index": 0,
                })
            assert decided.status_code == 200
            result = decided.json()["result"]
            assert result["touchdown"] is False
            assert engine.state.ball_position == 99
            assert not engine.state.scoring_plays
        finally:
            client.delete(f"/api/game/{game_id}")


def test_no_penalty_touchdown_and_field_goal_still_arm_follow_up_states() -> None:
    with TestClient(app) as client:
        game_id, game = _start(client, human_is_home=True, human_offense=True)
        engine = game["engine"]
        try:
            engine.state.possession_team.offense.line_plunge[26] = "12"
            with patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Roll26")):
                executed = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                })
            data = executed.json()
            assert data["result"]["touchdown"] is True
            assert data["game_state"]["pending_pat"] is True
            assert engine.state.ball_position == 98
        finally:
            client.delete(f"/api/game/{game_id}")

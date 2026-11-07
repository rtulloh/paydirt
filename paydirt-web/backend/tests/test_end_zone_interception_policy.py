"""New-game preferences and replay persistence use public 2026 teams."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
from main import app
from routes import games


@pytest.mark.parametrize("player_home", [True, False])
@pytest.mark.parametrize("player_attempt,opponent_attempt", [(True, False), (False, True), (True, True), (False, False)])
def test_new_game_maps_team_preferences_and_replay_round_trip(player_home: bool, player_attempt: bool,
                                                             opponent_attempt: bool) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks", "season": "2026",
            "play_as_home": player_home,
            "player_attempt_end_zone_interception_returns": player_attempt,
            "opponent_attempt_end_zone_interception_returns": opponent_attempt,
        })
        assert response.status_code == 200
        created = response.json()
        game_id = created["game_id"]
        loaded_id = None
        try:
            expected_home = player_attempt if player_home else opponent_attempt
            expected_away = opponent_attempt if player_home else player_attempt
            for state in (created["game_state"], client.get(f"/api/game/state/{game_id}").json()):
                assert state["home_end_zone_interception_return"] is expected_home
                assert state["away_end_zone_interception_return"] is expected_away
            replay = client.post(f"/api/game/save-replay/{game_id}").json()
            loaded = client.post("/api/game/load-replay", json={"replay_data": replay})
            assert loaded.status_code == 200
            restored = loaded.json()
            loaded_id = restored["game_id"]
            assert restored["game_state"]["home_end_zone_interception_return"] is expected_home
            assert restored["game_state"]["away_end_zone_interception_return"] is expected_away
            # Use the restored policy through actual engine-owned resolution.
            engine = games[loaded_id]["engine"]
            engine.state.is_home_possession = not player_home
            engine.state.ball_position = 90
            engine.state.defense_team.special_teams.interception_return = {26: "15"}
            from paydirt.play_resolver import PlayResult, ResultType
            result = PlayResult(result_type=ResultType.INTERCEPTION, yards=14, turnover=True, raw_result="INT 14")
            with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "return")) as dice:
                engine._handle_interception(result, 90, 14)
            assert engine.state.ball_position == (11 if player_attempt else 20)
            assert dice.call_count == int(player_attempt)
        finally:
            games.pop(game_id, None)
            if loaded_id:
                games.pop(loaded_id, None)


def test_legacy_web_save_defaults_each_team_to_automatic_touchback() -> None:
    with TestClient(app) as client:
        created = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"}).json()
        game_id = created["game_id"]
        replay = client.post(f"/api/game/save-replay/{game_id}").json()
        for key in ("home_end_zone_interception_return", "away_end_zone_interception_return"):
            replay["game_state"].pop(key, None)
        loaded = client.post("/api/game/load-replay", json={"replay_data": replay})
        loaded_id = loaded.json()["game_id"]
        try:
            assert loaded.status_code == 200
            assert loaded.json()["game_state"].get("home_end_zone_interception_return", False) is False
            assert loaded.json()["game_state"].get("away_end_zone_interception_return", False) is False
        finally:
            games.pop(game_id, None)
            games.pop(loaded_id, None)


def test_pending_cached_return_serializes_and_live_retention_survives_replay_save() -> None:
    from copy import deepcopy

    from paydirt.game_engine import ReturnChain
    from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType

    with TestClient(app) as client:
        created = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks", "season": "2026",
            "player_attempt_end_zone_interception_returns": True,
        }).json()
        game_id = created["game_id"]
        loaded_id = None
        try:
            engine = games[game_id]["engine"]
            engine.state.is_home_possession = False  # Human home defense gets the OFF-foul choice.
            engine.state.ball_position = 90
            engine.state.defense_team.peripheral.fumble_recovered_range = (10, 29)
            engine.state.defense_team.special_teams.interception_return = {26: "OFF 5", 27: "12"}
            result = PlayResult(result_type=ResultType.INTERCEPTION, yards=14, turnover=True, raw_result="INT 14")
            original = deepcopy(engine.state)
            with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(26, "foul"), (27, "return")]):
                engine._handle_interception(result, 90, 14)
            engine.state = original
            assert isinstance(result.int_return_chain, ReturnChain)
            choice = PenaltyChoice(
                play_result=result, offended_team="defense",
                penalty_options=[PenaltyOption("OFF", "OFF 5", 5, "Offensive foul")])
            with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
                pending = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "A", "cpu_play": "6"})
            assert pending.status_code == 200
            assert pending.json()["result"]["pending_penalty_decision"]
            # Existing replay files save the visible state, not unresolved choices.
            pending_save = client.post(f"/api/game/save-replay/{game_id}")
            assert pending_save.status_code == 200
            assert isinstance(engine._last_play_outcome.result.int_return_chain, ReturnChain)
            with patch("paydirt.game_engine.roll_chart_dice", side_effect=AssertionError("cached chain rerolled")):
                retained = client.post("/api/game/penalty-decision", json={
                    "game_id": game_id, "accept_penalty": False, "penalty_index": 0})
            assert retained.status_code == 200
            assert retained.json()["game_state"]["ball_position"] == 4
            assert engine.state.home_stats.penalties == 1
            saved = client.post(f"/api/game/save-replay/{game_id}")
            assert saved.status_code == 200
            loaded = client.post("/api/game/load-replay", json={"replay_data": saved.json()})
            assert loaded.status_code == 200
            loaded_id = loaded.json()["game_id"]
            assert loaded.json()["game_state"]["ball_position"] == 4
            assert loaded.json()["game_state"]["home_end_zone_interception_return"] is True
        finally:
            games.pop(game_id, None)
            if loaded_id:
                games.pop(loaded_id, None)

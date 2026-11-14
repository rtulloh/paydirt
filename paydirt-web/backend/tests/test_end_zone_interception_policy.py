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


def test_new_game_policy_pauses_end_zone_interception_until_decision() -> None:
    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType

    with TestClient(app) as client:
        created = client.post("/api/game/new", json={
            "player_team": "Thunderhawks", "opponent_team": "Ironclads", "season": "2026",
            "play_as_home": True,
            "player_end_zone_interception_policy": "ask",
            "opponent_end_zone_interception_policy": "auto",
        })
        assert created.status_code == 200
        game_id = created.json()["game_id"]
        try:
            state = created.json()["game_state"]
            assert state["human_is_home"] is True
            assert state["home_end_zone_interception_policy"] == "ask"
            assert state["away_end_zone_interception_policy"] == "auto"

            engine = games[game_id]["engine"]
            assert engine.state.is_home_possession is False  # Away offense, human home defense.
            engine.state.ball_position = 90
            result = PlayResult(
                result_type=ResultType.INTERCEPTION, yards=14, turnover=True,
                raw_result="INT 14",
            )
            with patch(
                "paydirt.game_engine.resolve_play_with_penalties",
                return_value=PenaltyChoice(play_result=result),
            ):
                response = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "A", "cpu_play": "6",
                })
            assert response.status_code == 200
            pending = response.json()["result"]
            assert pending["pending_end_zone_interception_return_decision"] is True
            assert pending["int_catch_depth"] == 4
            assert pending["int_catch_field_position"] == "own 4-yard line"
            assert "Q" in pending["interception_return_situation"]
            # Nothing scored, no possession change and no return dice yet.
            assert pending["turnover"] is False
            assert engine.state.is_home_possession is False
            assert engine.state.ball_position == 90

            decided = client.post("/api/game/end-zone-interception-decision", json={
                "game_id": game_id, "attempt_return": False,
            })
            assert decided.status_code == 200
            final = decided.json()
            assert final["result"]["pending_end_zone_interception_return_decision"] is False
            assert final["result"]["turnover"] is True
            assert final["game_state"]["ball_position"] == 20
            assert final["game_state"]["possession"] == "home"
            # Resolving again must not duplicate the turnover.
            again = client.post("/api/game/end-zone-interception-decision", json={
                "game_id": game_id, "attempt_return": False,
            })
            assert again.status_code == 400
            assert engine.state.away_stats.interceptions_thrown == 1
        finally:
            games.pop(game_id, None)


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


def test_execute_while_return_choice_is_pending_is_rejected() -> None:
    """FLOW-026: the API refuses a new snap before the pending choice is resolved."""
    from copy import deepcopy

    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType

    with TestClient(app) as client:
        created = client.post("/api/game/new", json={
            "player_team": "Thunderhawks", "opponent_team": "Ironclads", "season": "2026",
            "play_as_home": True,
            "player_end_zone_interception_policy": "ask",
            "opponent_end_zone_interception_policy": "auto",
        })
        assert created.status_code == 200
        game_id = created.json()["game_id"]
        try:
            engine = games[game_id]["engine"]
            engine.state.ball_position = 90
            result = PlayResult(
                result_type=ResultType.INTERCEPTION, yards=14, turnover=True, raw_result="INT 14",
            )
            with patch(
                "paydirt.game_engine.resolve_play_with_penalties",
                return_value=PenaltyChoice(play_result=result),
            ):
                pending = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "A", "cpu_play": "6",
                })
            assert pending.status_code == 200
            assert pending.json()["result"]["pending_end_zone_interception_return_decision"] is True

            state_before = deepcopy(engine.state)
            log_before = len(engine.play_log)
            blocked = client.post("/api/game/execute", json={
                "game_id": game_id, "player_play": "A", "cpu_play": "6",
            })
            assert blocked.status_code == 409
            assert "end-zone interception" in blocked.json()["detail"]
            assert engine.state == state_before
            assert len(engine.play_log) == log_before

            decided = client.post("/api/game/end-zone-interception-decision", json={
                "game_id": game_id, "attempt_return": False,
            })
            assert decided.status_code == 200
            assert engine.has_pending_end_zone_interception is False
        finally:
            games.pop(game_id, None)


def _pending_end_zone_game(client: TestClient) -> str:
    """Create a web game paused on an ask-policy end-zone interception."""
    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType

    created = client.post("/api/game/new", json={
        "player_team": "Thunderhawks", "opponent_team": "Ironclads", "season": "2026",
        "play_as_home": True,
        "player_end_zone_interception_policy": "ask",
        "opponent_end_zone_interception_policy": "auto",
    })
    assert created.status_code == 200
    game_id = created.json()["game_id"]
    engine = games[game_id]["engine"]
    engine.state.ball_position = 90
    result = PlayResult(
        result_type=ResultType.INTERCEPTION, yards=14, turnover=True, raw_result="INT 14",
    )
    with patch(
        "paydirt.game_engine.resolve_play_with_penalties",
        return_value=PenaltyChoice(play_result=result),
    ):
        pending = client.post("/api/game/execute", json={
            "game_id": game_id, "player_play": "A", "cpu_play": "6",
        })
    assert pending.status_code == 200
    assert pending.json()["result"]["pending_end_zone_interception_return_decision"] is True
    assert engine.has_pending_end_zone_interception is True
    return game_id


def _set_tied_game(state) -> None:
    """Make the overtime precondition reachable without touching prior flags."""
    state.home_score = state.away_score = 0


@pytest.mark.parametrize(
    ("path", "payload", "prepare"),
    [
        ("/api/game/kickoff", {"kickoff_spot": 35}, None),
        (
            "/api/game/kickoff",
            {"kickoff_spot": 35},
            lambda game: game.__setitem__("safety_free_kick", True),
        ),
        (
            "/api/game/extra-point",
            {"player_play": "XP"},
            lambda game: game.__setitem__("pending_pat", True),
        ),
        (
            "/api/game/two-point",
            {"offense_play": "1", "defense_play": "A"},
            lambda game: game.__setitem__("pending_pat", True),
        ),
        ("/api/game/timeout", {}, None),
        (
            "/api/game/penalty-decision",
            {"penalty_index": 0, "accept_penalty": False},
            None,
        ),
        (
            "/api/game/overtime/start",
            {},
            lambda game: _set_tied_game(game["engine"].state),
        ),
    ],
    ids=[
        "kickoff",
        "safety-free-kick",
        "extra-point",
        "two-point",
        "timeout",
        "penalty-decision",
        "overtime-start",
    ],
)
def test_other_game_actions_are_rejected_while_return_choice_is_pending(
    path: str, payload: dict, prepare
) -> None:
    """FLOW-026: every state-changing route honors the pending choice."""
    from copy import deepcopy

    with TestClient(app) as client:
        game_id = _pending_end_zone_game(client)
        try:
            game = games[game_id]
            if prepare is not None:
                prepare(game)
            engine = game["engine"]
            state_before = deepcopy(engine.state)
            log_before = list(engine.play_log)
            flags_before = {
                key: deepcopy(value)
                for key, value in game.items()
                if key not in {"engine", "ai", "home_team", "away_team"}
            }
            blocked = client.post(path, json={"game_id": game_id, **payload})
            assert blocked.status_code == 409, blocked.text
            assert "end-zone interception" in blocked.json()["detail"]
            assert engine.state == state_before
            assert engine.play_log == log_before
            assert engine.has_pending_end_zone_interception
            assert {
                key: value
                for key, value in game.items()
                if key not in {"engine", "ai", "home_team", "away_team"}
            } == flags_before
        finally:
            games.pop(game_id, None)

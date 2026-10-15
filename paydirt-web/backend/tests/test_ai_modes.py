"""Web AI configuration and learning use only public sample teams."""

from pathlib import Path
import sys
from typing import Any, Iterator
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app
import routes
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType, parse_result_string


@pytest.fixture
def client() -> Iterator[TestClient]:
    existing = set(routes.games)
    with TestClient(app) as api:
        yield api
    for game_id in set(routes.games) - existing:
        del routes.games[game_id]


def new_game(client: TestClient, difficulty: str, is_home: bool) -> dict:
    response = client.post("/api/game/new", json={
        "player_team": "Ironclads", "opponent_team": "Thunderhawks",
        "season": "2026", "play_as_home": is_home, "difficulty": difficulty,
    })
    assert response.status_code == 200, response.text
    return routes.games[response.json()["game_id"]]


@pytest.mark.parametrize("replay", [False, True], ids=["new", "replay"])
@pytest.mark.parametrize("is_home", [False, True])
@pytest.mark.parametrize("difficulty,aggression", [("easy", .3), ("medium", .5), ("hard", .7)])
def test_web_difficulty_configuration(
    client: TestClient, replay: bool, is_home: bool, difficulty: str, aggression: float,
) -> None:
    game = new_game(client, difficulty, is_home)
    if replay:
        saved = client.post(f"/api/game/save-replay/{game['game_id']}")
        assert saved.status_code == 200
        response = client.post("/api/game/load-replay", json={"replay_data": {
            "season": "2026", "game_state": saved.json()["game_state"],
            "play_history": [], "difficulty": difficulty,
        }})
        assert response.status_code == 200, response.text
        game = routes.games[response.json()["game_id"]]
    ai = game["ai"]
    assert ai.aggression == aggression
    assert ai.ai_behavior is game["engine"].season_rules.ai_behavior
    assert ai.use_analysis is (difficulty == "hard")
    assert (ai.opponent_model is not None) is (difficulty == "hard")
    if difficulty == "hard":
        expected = game["engine"].state.away_chart if is_home else game["engine"].state.home_chart
        assert ai.team_analyzer.team_chart is expected
    else:
        assert ai.team_analyzer is None


@pytest.mark.parametrize("is_home", [False, True])
@pytest.mark.parametrize("human_offense", [False, True])
@pytest.mark.parametrize("transition", ["first-down", "turnover", "unchanged"])
def test_web_learns_only_human_preplay_situation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, is_home: bool,
    human_offense: bool, transition: str,
) -> None:
    game = new_game(client, "hard", is_home)
    engine = game["engine"]
    engine.state.is_home_possession = is_home if human_offense else not is_home
    engine.state.down, engine.state.yards_to_go = 3, 7
    game["is_kickoff"] = False

    def execute(*args: Any, **kwargs: Any) -> PlayOutcome:
        if transition != "unchanged":
            engine.state.down, engine.state.yards_to_go = 1, 10
        if transition == "turnover":
            engine.state.is_home_possession = not engine.state.is_home_possession
        return PlayOutcome(PlayType.SHORT_PASS, DefenseType.STANDARD,
                           parse_result_string("8"), yards_gained=8, down_before=3,
                           turnover=transition == "turnover")

    monkeypatch.setattr(engine, "run_play_with_penalty_procedure", execute)
    response = client.post("/api/game/execute", json={
        "game_id": game["game_id"], "player_play": "6" if human_offense else "A",
        "cpu_play": "A" if human_offense else "6",
    })
    assert response.status_code == 200, response.text
    assert game["ai"].opponent_model is not None
    tracker = game["ai"].opponent_model.tracker
    assert tracker.get_tendency(3, 7).pass_plays == int(human_offense)
    assert tracker.get_tendency(1, 10).total_plays == 0
    assert sum(len(plays) for plays in tracker.situation_plays.values()) == int(human_offense)

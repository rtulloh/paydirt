"""Request paths stay within configured synthetic season roots."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
import routes
from main import app


@pytest.fixture
def roots(tmp_path, monkeypatch):
    root = tmp_path / "seasons"
    root.mkdir()
    (root / "2026").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "team.yaml").write_text("team_name: Outside secret")
    monkeypatch.setattr(routes, "get_all_season_paths", lambda: [root])
    return root, outside


def test_valid_configured_season(roots):
    root, _ = roots
    assert routes._find_season_dir("2026") == root / "2026"


@pytest.mark.parametrize("kind", ["absolute", "relative", "symlink"])
def test_season_escape_rejected(roots, kind):
    root, outside = roots
    value = str(outside) if kind == "absolute" else "../outside"
    if kind == "symlink":
        (root / "linked").symlink_to(outside, target_is_directory=True)
        value = "linked"
    assert routes._find_season_dir(value) is None
    assert TestClient(app).get("/api/teams", params={"season": value}).status_code == 404


def test_team_symlink_is_not_listed_or_loaded(roots):
    root, outside = roots
    (root / "2026" / "linked").symlink_to(outside, target_is_directory=True)
    client = TestClient(app)
    assert client.get("/api/teams", params={"season": "2026"}).json() == {"teams": []}
    response = client.post("/api/game/new", json={"season": "2026", "player_team": "linked"})
    assert response.status_code == 404


def test_replay_rejects_outside_team_before_loading(roots, monkeypatch):
    _, outside = roots
    def forbidden(*args):
        pytest.fail("outside chart was loaded")
    monkeypatch.setattr(routes, "load_team_chart", forbidden)
    response = TestClient(app).post("/api/game/load-replay", json={"replay_data": {
        "season": "2026", "game_state": {"home_team": {"id": str(outside)}, "away_team": {"id": str(outside)}}}})
    assert response.status_code == 400


def test_team_asset_symlink_is_not_listed(roots):
    root, outside = roots
    team = root / "2026" / "Safe"
    team.mkdir()
    (team / "team.yaml").symlink_to(outside / "team.yaml")
    assert TestClient(app).get("/api/teams", params={"season": "2026"}).json() == {"teams": []}


@pytest.mark.parametrize("identifier", [None, 3, [], {}, "", ".", "..", "bad\\name", "bad\x00name"])
def test_malformed_season_is_not_a_path(roots, identifier):
    assert routes._find_season_dir(identifier) is None


def test_season_asset_symlink_is_rejected_before_read(roots):
    root, outside = roots
    (root / "2026" / "2026.yaml").symlink_to(outside / "team.yaml")
    assert routes._find_season_dir("2026") is None


@pytest.mark.parametrize("team", ["missing", 3, [], {"id": []}, {"id": "../outside"}])
def test_replay_malformed_team_returns_client_error(roots, team):
    response = TestClient(app).post("/api/game/load-replay", json={"replay_data": {
        "game_state": {"home_team": team, "away_team": {"id": "missing"}}}})
    assert response.status_code == 400

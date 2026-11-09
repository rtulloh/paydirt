"""Public/synthetic regressions for published application acceptance."""
import hashlib
import importlib.util
from pathlib import Path

import pytest


def smoke_module():
    path = Path(__file__).resolve().parents[1] / "scripts/smoke_published_app.py"
    assert path.is_file(), "Published-asset smoke implementation is required"
    spec = importlib.util.spec_from_file_location("published_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asset_identity_rejects_changed_bytes(tmp_path):
    smoke = smoke_module()
    artifact = tmp_path / "published.bin"
    artifact.write_bytes(b"reviewed public artifact")
    metadata = {"size": artifact.stat().st_size, "digest": "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()}
    smoke.verify_asset(artifact, metadata)
    artifact.write_bytes(b"changed public artifact!")
    with pytest.raises(ValueError, match="identity"):
        smoke.verify_asset(artifact, metadata)


def api_responses():
    return {
        "/openapi.json": {"info": {"version": "1.10.3"}},
        "/api/seasons": {"seasons": ["2026", "2024", "1983"]},
        **{f"/api/teams?season={year}": {"teams": [{"id": str(i)} for i in range(count)]}
           for year, count in [(1983, 28), (2024, 32), (2026, 2)]},
        "/api/game/new": {"game_id": "game_public", "game_state": {"quarter": 1, "home_score": 0, "away_score": 0, "time_remaining": 900}},
        **{f"/api/game/charts/game_public?side={side}": {key: {"rows": [{}], "columns": [{}]} for key in ["offense", "defense", "special_teams"]}
           for side in ["home", "away"]},
    }


@pytest.mark.parametrize("failure", [None, "version", "teams", "game", "charts", "empty-charts"])
def test_packaged_api_acceptance_checks_all_required_results(monkeypatch, failure):
    smoke = smoke_module()
    responses = api_responses()
    if failure == "version": responses["/openapi.json"]["info"]["version"] = "1.10.2"
    if failure == "teams": responses["/api/teams?season=2024"]["teams"].pop()
    if failure == "game": responses["/api/game/new"]["game_state"]["quarter"] = 2
    if failure == "charts": responses["/api/game/charts/game_public?side=away"].pop("offense")
    if failure == "empty-charts": responses["/api/game/charts/game_public?side=away"]["offense"]["rows"] = []
    calls = []
    def request(base, path, payload=None):
        calls.append((path, payload))
        return responses[path]
    monkeypatch.setattr(smoke, "request_json", request)
    if failure:
        with pytest.raises(ValueError): smoke.check_api("http://synthetic", "1.10.3")
    else:
        result = smoke.check_api("http://synthetic", "1.10.3")
        assert result["team_counts"] == {"1983": 28, "2024": 32, "2026": 2}
        assert result["game_id"] == "game_public"
        assert calls[-1][0].endswith("side=away")
        payload = next(payload for path, payload in calls if path == "/api/game/new")
        assert payload["player_team"] == "Ironclads"
        assert payload["opponent_team"] == "Thunderhawks"


def test_shutdown_rejects_http_error_from_surviving_server(monkeypatch):
    from unittest.mock import Mock
    from urllib.error import HTTPError
    smoke = smoke_module()
    process = Mock()
    process.poll.return_value = 0
    def responding(*args):
        raise HTTPError("http://synthetic", 500, "still alive", {}, None)
    monkeypatch.setattr(smoke, "request_json", responding)
    monkeypatch.setattr(smoke.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="remained"):
        smoke.stop(process, "http://synthetic")

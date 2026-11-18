"""The static browser transport uses the same registered game operations."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
import routes


def dispatch(method: str, path: str, body=None) -> dict:
    from browser_bridge import dispatch_json

    request = {"method": method, "path": path}
    if body is not None:
        request["body"] = body
    return json.loads(asyncio.run(dispatch_json(json.dumps(request))))


def test_import_without_fastapi() -> None:
    backend = Path(__file__).resolve().parents[1]
    code = """
import sys
class BlockFastAPI:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'fastapi' or fullname.startswith('fastapi.'):
            raise ImportError('FastAPI forbidden in browser')
sys.meta_path.insert(0, BlockFastAPI())
import browser_bridge
import routes
assert routes.registry.operations
"""
    subprocess.run([sys.executable, "-c", code], cwd=backend, check=True)


def test_health_and_unknown_operation() -> None:
    assert dispatch("GET", "/api/health") == {"status": 200, "body": {"status": "ok"}}
    assert dispatch("POST", "/api/not-an-operation")["status"] == 404


@pytest.mark.parametrize("raw", ["bad json", "[]", '{"method":"GET"}'])
def test_invalid_envelope(raw: str) -> None:
    from browser_bridge import dispatch_json

    assert json.loads(asyncio.run(dispatch_json(raw)))["status"] == 400


def test_body_and_query_validation() -> None:
    assert dispatch("POST", "/api/game/new", {})["status"] == 422
    assert dispatch("GET", "/api/game/charts/missing?side=invalid")["status"] == 422
    assert dispatch("GET", "/api/teams")["status"] == 422
    assert dispatch("GET", "/api/game/state/missing")["status"] == 404


def test_public_sample_game_and_response_models() -> None:
    teams = dispatch("GET", "/api/teams/2026")
    assert teams["status"] == 200
    ids = [team["id"] for team in teams["body"]["teams"]]
    request = {"season": "2026", "player_team": ids[0], "opponent_team": ids[1]}
    created = dispatch("POST", "/api/game/new", request)
    assert created["status"] == 200, created
    game_id = created["body"]["game_id"]
    try:
        assert game_id in routes.games
        charts = dispatch("GET", f"/api/game/charts/{game_id}?side=away")
        assert charts["status"] == 200
        state = dispatch("GET", f"/api/game/state/{game_id}")
        assert state["body"] == created["body"]["game_state"]
        assert dispatch("GET", "/api/guide")["status"] == 200
        assert dispatch("POST", f"/api/game/save-replay/{game_id}")["status"] == 200
    finally:
        routes.games.pop(game_id, None)


def test_unexpected_failure_is_safe(monkeypatch) -> None:
    async def fail():
        raise RuntimeError("private filesystem secret")

    operation = next(op for op in routes.registry.operations if op.path == "/api/health")
    monkeypatch.setattr(operation, "handler", fail)
    assert dispatch("GET", "/api/health") == {
        "status": 500, "body": {"detail": "Operation failed"}
    }


def test_fetch_body_string_and_invalid_json() -> None:
    response = dispatch("POST", "/api/game/cpu-play", '{"game_id":"missing"}')
    assert response == {"status": 404, "body": {"detail": "Game not found"}}
    assert dispatch("POST", "/api/game/cpu-play", "{")["status"] == 400


def test_browser_image_asset_and_external_path_rejection(tmp_path, monkeypatch) -> None:
    import base64

    (tmp_path / "images").mkdir()
    image = b"synthetic image bytes"
    (tmp_path / "images/test.png").write_bytes(image)
    monkeypatch.setattr(routes, "_get_docs_path", lambda: tmp_path)
    result = dispatch("GET", "/api/docs/images/test.png")
    assert result == {
        "status": 200, "body": base64.b64encode(image).decode("ascii"),
        "media_type": "image/png", "encoding": "base64",
    }
    assert dispatch("GET", "https://example.com/api/health")["status"] == 400


def test_operations_are_serialized(monkeypatch) -> None:
    import browser_bridge

    active = 0
    peak = 0

    async def delayed():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return {"items": [1, 2]}

    operation = next(op for op in routes.registry.operations if op.path == "/api/health")
    monkeypatch.setattr(operation, "handler", delayed)

    async def run():
        monkeypatch.setattr(browser_bridge, "_lock", asyncio.Lock())
        return await asyncio.gather(*[
            browser_bridge.dispatch_json('{"method":"GET","path":"/api/health"}')
            for _ in range(3)
        ])

    results = asyncio.run(run())
    assert peak == 1
    assert all(json.loads(result)["body"] == {"items": [1, 2]} for result in results)

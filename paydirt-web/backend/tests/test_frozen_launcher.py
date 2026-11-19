"""Exercise the real launcher using PyInstaller's nested data-file layout."""
import shutil
import sys
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient
from pydantic import BaseModel

from paydirt import __main__ as launcher


@pytest.mark.parametrize("frozen,mode", [(True, "explicit"), (True, "default"),
    (True, "environment"), (False, "environment"), (False, "explicit"), (False, "disabled")])
def test_launcher_resolves_models_and_starts_game(tmp_path, monkeypatch, frozen, mode):
    repository = Path(__file__).resolve().parents[3]
    backend = tmp_path / "paydirt-web" / "backend"
    (backend / "routes.py").mkdir(parents=True)
    shutil.copy2(repository / "paydirt-web/backend/routes.py", backend / "routes.py/routes.py")
    shutil.copy2(repository / "paydirt-web/backend/chart_viewer.py", backend / "chart_viewer.py")
    shutil.copytree(repository / "seasons/2026", tmp_path / "seasons/2026")
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setitem(sys.modules, "routes", None)
    monkeypatch.delitem(sys.modules, "routes")
    monkeypatch.setattr(sys, "path", list(sys.path))
    from paydirt import packaging
    monkeypatch.setattr(packaging, "get_all_season_paths", lambda: [tmp_path / "seasons"])
    monkeypatch.setattr(launcher, "get_all_season_paths", lambda: [tmp_path / "seasons"])
    captured = {}

    class ImmediateThread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    class Server:
        def __init__(self, config):
            captured["app"] = config.app

        def run(self):
            pass

    real_thread = launcher.threading.Thread
    monkeypatch.setattr(launcher.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(launcher.time, "sleep", lambda _: None)
    monkeypatch.setattr(uvicorn, "Server", Server)
    monkeypatch.setattr(packaging, "get_user_data_path", lambda: tmp_path / "user-data")
    monkeypatch.delenv("PAYDIRT_NATIVE_USER_DATA_DIR", raising=False)
    if mode in {"environment", "explicit"}:
        monkeypatch.setenv("PAYDIRT_NATIVE_USER_DATA_DIR", str(tmp_path / "env-data"))
    launcher.start_web_server(open_browser=False, user_data_dir=tmp_path / "user-data" if mode == "explicit" else None)
    monkeypatch.setattr(launcher.threading, "Thread", real_thread)
    async def loopback_app(scope, receive, send):
        if scope["type"] == "http":
            scope = {**scope, "client": ("127.0.0.1", 12345)}
        await captured["app"](scope, receive, send)

    client = TestClient(loopback_app, raise_server_exceptions=False)
    response = client.get("/api/teams", params={"season": "2026"})
    assert response.status_code == 200, response.text
    assert len(response.json()["teams"]) == 2
    assert "routes" in sys.modules
    module = sys.modules["routes"]
    models = [value for value in vars(module).values()
              if isinstance(value, type) and issubclass(value, BaseModel)
              and value is not BaseModel]
    assert models and all(model.__pydantic_complete__ for model in models)
    response = client.post("/api/game/new", json={"season": "2026", "player_team": "Ironclads", "opponent_team": "Thunderhawks"})
    assert response.status_code == 200, response.text
    assert response.json()["game_state"]["quarter"] == 1
    enabled = mode != "disabled"
    assert client.get("/api/library/status").json() == {"enabled": enabled}
    if enabled:
        expected_dir = tmp_path / ("env-data" if mode == "environment" else "user-data")
        assert module.native_library_path == expected_dir / "library.sqlite3"
        assert client.post("/api/game/new", json={"season": "2026", "player_team": "Ironclads"},
            headers={"Origin": "http://localhost:8000"}).status_code == 403
        async def remote_app(scope, receive, send):
            if scope["type"] == "http":
                scope = {**scope, "client": ("203.0.113.8", 12345)}
            await captured["app"](scope, receive, send)
        remote = TestClient(remote_app)
        assert remote.get("/api/library/status").status_code == 403
    else:
        assert getattr(module, "native_library_path", None) is None
        assert not (tmp_path / "user-data").exists()
        assert not (tmp_path / "env-data").exists()
    assert client.get("/api/teams/2026").status_code == 200
    assert client.get("/api/teams", params={"season": str(tmp_path)}).status_code == 404


@pytest.mark.parametrize("frozen", [False, True])
@pytest.mark.parametrize("flag", [None, "--web", "-w"])
def test_main_web_dispatch_uses_requested_port_and_browser_flag(monkeypatch, frozen, flag):
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(sys, "argv", ["paydirt"] + ([flag, "--port", "18470", "--no-browser"] if flag else []))
    calls = []
    monkeypatch.setattr(launcher, "start_web_server", lambda **kwargs: calls.append(kwargs))
    def stop_waiting(_seconds):
        raise KeyboardInterrupt
    monkeypatch.setattr(launcher.time, "sleep", stop_waiting)
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("Web mode entered the football CLI"))
    launcher.main()
    assert calls == [{"port": 18470 if flag else 8000, "open_browser": flag is None}]

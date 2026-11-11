"""Exercise the real launcher using PyInstaller's nested data-file layout."""
import shutil
import sys
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient
from pydantic import BaseModel

from paydirt import __main__ as launcher


def test_frozen_launcher_resolves_models_and_starts_game(tmp_path, monkeypatch):
    repository = Path(__file__).resolve().parents[3]
    backend = tmp_path / "paydirt-web" / "backend"
    (backend / "routes.py").mkdir(parents=True)
    shutil.copy2(repository / "paydirt-web/backend/routes.py", backend / "routes.py/routes.py")
    shutil.copy2(repository / "paydirt-web/backend/chart_viewer.py", backend / "chart_viewer.py")
    shutil.copytree(repository / "seasons/2026", tmp_path / "seasons/2026")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
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
    launcher.start_web_server(open_browser=False)
    monkeypatch.setattr(launcher.threading, "Thread", real_thread)
    client = TestClient(captured["app"], raise_server_exceptions=False)
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
    assert client.get("/api/teams/2026").status_code == 200
    assert client.get("/api/teams", params={"season": str(tmp_path)}).status_code == 404

"""Explicit native storage preserves portable records across real process exits."""
import json
import os
import sqlite3
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest
import routes  # Initializes the project import path.


def library(path):
    return import_module("native_library").NativeLibrary(path)


def game(identity="g", revision=1):
    return {"id": identity, "name": "Synthetic", "checkpoint": "opaque validated elsewhere",
            "metadata": {}, "revision": revision, "savedAt": "2026-11-18T00:00:00Z"}


def campaign():
    from paydirt.campaigns import create_campaign
    return create_campaign("Synthetic", [{"season": "2026", "team_id": name, "name": name}
        for name in ["Ironclads", "Thunderhawks"]], "2026")


def test_games_cas_and_true_process_restart(tmp_path):
    path = tmp_path / "library.sqlite3"
    repo = library(path)
    saved = repo.command({"store": "games", "action": "put", "record": game(), "expectedRevision": 0})
    assert saved["revision"] == 1
    script = "from native_library import NativeLibrary; import json,sys; print(json.dumps(NativeLibrary(sys.argv[1]).command({'store':'games','action':'get','id':'g'})))"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    output = subprocess.check_output([sys.executable, "-c", script, str(path)], env=env, text=True)
    assert json.loads(output) == saved
    with pytest.raises(ValueError, match="another|revision"):
        repo.command({"store": "games", "action": "put", "record": game(), "expectedRevision": 0})
    assert repo.command({"store": "games", "action": "list"}) == [saved]
    with pytest.raises(ValueError):
        repo.command({"store": "games", "action": "remove", "id": "g", "expectedRevision": 0})
    repo.command({"store": "games", "action": "remove", "id": "g", "expectedRevision": 1})
    assert repo.command({"store": "games", "action": "get", "id": "g"}) is None


def test_campaign_linked_write_rolls_back_on_game_conflict(tmp_path):
    repo = library(tmp_path / "library.sqlite3"); c = campaign()
    repo.command({"store": "games", "action": "put", "record": game(), "expectedRevision": 0})
    with pytest.raises(ValueError):
        repo.command({"store": "campaigns", "action": "put", "campaign": c, "expectedRevision": 0,
                      "gameRecord": game(), "expectedGameRevision": 0})
    assert repo.command({"store": "campaigns", "action": "list"}) == []
    record = repo.command({"store": "campaigns", "action": "put", "campaign": c, "expectedRevision": 0})
    with pytest.raises(ValueError):
        repo.command({"store": "campaigns", "action": "remove", "record": {**record, "revision": 0}})
    assert repo.command({"store": "campaigns", "action": "get", "id": c["id"]}) == record


def test_campaign_bundle_atomic_import_export_delete(tmp_path):
    from paydirt.campaigns import start_fixture
    repo = library(tmp_path / "library.sqlite3"); c = campaign()
    c = start_fixture(c, c["fixtures"][0]["id"], "g")
    g = game(); g["metadata"] = {"campaignId": c["id"], "fixtureId": c["fixtures"][0]["id"], "gameId": "g"}
    record = repo.command({"store": "campaigns", "action": "importBundle", "campaign": c, "games": [g]})
    assert repo.command({"store": "campaigns", "action": "exportBundle", "record": record}) == {
        "format": "paydirt-campaign", "version": 1, "campaign": c, "games": [g]}
    with pytest.raises(ValueError):
        repo.command({"store": "campaigns", "action": "importBundle", "campaign": c, "games": [g]})
    repo.command({"store": "campaigns", "action": "remove", "record": record})
    assert repo.command({"store": "games", "action": "list"}) == []
    assert repo.command({"store": "campaigns", "action": "list"}) == []


def test_corrupt_database_and_rows_reject_without_replacement(tmp_path):
    path = tmp_path / "broken.sqlite3"; path.write_bytes(b"corrupted original")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        library(path).command({"store": "games", "action": "list"})
    assert path.read_bytes() == b"corrupted original"
    path = tmp_path / "rows.sqlite3"; repo = library(path)
    repo.command({"store": "games", "action": "put", "record": game(), "expectedRevision": 0})
    with sqlite3.connect(path) as db:
        db.execute("UPDATE records SET document = ?", ("{broken",))
    with pytest.raises(ValueError, match="corrupt|Corrupt|JSON"):
        repo.command({"store": "games", "action": "list"})


@pytest.mark.parametrize("command", [{"store": "../../x", "action": "list"},
    {"store": "games", "action": "put", "record": game(), "expectedRevision": True},
    {"store": "games", "action": "unknown"}])
def test_invalid_commands_rejected(tmp_path, command):
    with pytest.raises(ValueError):
        library(tmp_path / "library.sqlite3").command(command)


def test_native_transport_disabled_unless_explicit_config(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.delenv("PAYDIRT_NATIVE_USER_DATA_DIR", raising=False)
    monkeypatch.setattr(routes, "native_library_path", None, raising=False)
    with TestClient(address_app(app)) as client:
        assert client.get("/api/library/status").json() == {"enabled": False}
        assert client.post("/api/library/command", json={"store": "games", "action": "list"}).status_code == 404
        monkeypatch.setattr(routes, "native_library_path", tmp_path / "library.sqlite3")
        assert client.get("/api/library/status").json() == {"enabled": True}
        assert client.post("/api/library/command", json={"store": "games", "action": "list"}).json() == []


def test_native_http_checkpoint_survives_repository_reopen(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.setattr(routes, "native_library_path", tmp_path / "library.sqlite3", raising=False)
    before = set(routes.games)
    try:
        with TestClient(address_app(app)) as client:
            created = client.post("/api/game/new", json={"season": "2026", "player_team": "Ironclads", "opponent_team": "Thunderhawks"}).json()
            checkpoint = client.post(f"/api/game/checkpoint/{created['game_id']}").json()["checkpoint"]
            record = {**game(), "checkpoint": checkpoint}
            put = client.post("/api/library/command", json={"store": "games", "action": "put", "record": record, "expectedRevision": 0})
            assert put.status_code == 200, put.text
            stale = client.post("/api/library/command", json={"store": "games", "action": "put", "record": record, "expectedRevision": 0})
            assert stale.status_code == 409
            assert "Reopen" in stale.json()["detail"]
            routes.games.pop(created["game_id"])
            script = "from native_library import NativeLibrary; import json,sys; print(json.dumps(NativeLibrary(sys.argv[1]).command({'store':'games','action':'get','id':'g'})))"
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
            stored = json.loads(subprocess.check_output([sys.executable, "-c", script,
                str(tmp_path / "library.sqlite3")], env=env, text=True))
            restored = client.post("/api/game/restore", json={"checkpoint": stored["checkpoint"]})
            assert restored.status_code == 200, restored.text
            bad = {**record, "checkpoint": "corrupt"}
            rejected = client.post("/api/library/command", json={"store": "games", "action": "put", "record": bad, "expectedRevision": 1})
            assert rejected.status_code == 422
            assert library(tmp_path / "library.sqlite3").command({"store": "games", "action": "get", "id": "g"}) == stored
    finally:
        for identity in set(routes.games) - before:
            routes.games.pop(identity)


def test_games_put_accepts_autosave_input_without_storage_envelope(tmp_path):
    repo = library(tmp_path / "library.sqlite3")
    raw = {key: value for key, value in game().items() if key not in {"revision", "savedAt"}}
    saved = repo.command({"store": "games", "action": "put", "record": raw, "expectedRevision": 0})
    assert saved["revision"] == 1 and saved["savedAt"]
    assert saved["checkpoint"] == raw["checkpoint"]


def test_failed_sqlite_campaign_write_rolls_back_already_written_game(tmp_path):
    path = tmp_path / "library.sqlite3"; repo = library(path); c = campaign()
    g = repo.command({"store": "games", "action": "put", "record": game(), "expectedRevision": 0})
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER reject_campaign BEFORE INSERT ON records WHEN NEW.store = 'campaigns' BEGIN SELECT RAISE(ABORT, 'synthetic disk failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="synthetic"):
        repo.command({"store": "campaigns", "action": "put", "campaign": c, "expectedRevision": 0,
            "gameRecord": {**g, "revision": 2, "name": "Must roll back"}, "expectedGameRevision": 1})
    assert repo.command({"store": "games", "action": "get", "id": "g"}) == g
    assert repo.command({"store": "campaigns", "action": "list"}) == []


def test_native_environment_opt_in_and_unknown_schema_preserve_original(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from native_library_operations import _path
    monkeypatch.setenv("PAYDIRT_NATIVE_USER_DATA_DIR", str(tmp_path))
    assert _path(SimpleNamespace()) == tmp_path / "library.sqlite3"
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=999")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        library(path).command({"store": "games", "action": "list"})
    assert path.read_bytes() == before


def test_native_http_campaign_bundle_validates_and_commits_linked_saves_atomically(tmp_path, monkeypatch):
    import random

    from fastapi.testclient import TestClient
    from main import app

    monkeypatch.setattr(routes, "native_library_path", tmp_path / "library.sqlite3", raising=False)
    before = set(routes.games)
    try:
        with TestClient(address_app(app)) as client:
            c = campaign()
            started = client.post("/api/campaign/start", json={"campaign": c, "fixture_id": c["fixtures"][0]["id"]})
            assert started.status_code == 200, started.text
            started = started.json(); identity = started["game_id"]
            checkpoint = client.post(f"/api/game/checkpoint/{identity}").json()["checkpoint"]
            record = {**game(identity), "checkpoint": checkpoint, "metadata": {"campaignId": c["id"],
                "fixtureId": c["fixtures"][0]["id"], "gameId": identity}}
            rng, inventory = random.getstate(), set(routes.games)
            stored = client.post("/api/library/command", json={"store": "campaigns", "action": "put",
                "campaign": started["campaign"], "expectedRevision": 0, "gameRecord": record, "expectedGameRevision": 0})
            assert stored.status_code == 200, stored.text
            assert random.getstate() == rng and set(routes.games) == inventory
            exported = client.post("/api/library/command", json={"store": "campaigns", "action": "exportBundle", "record": stored.json()})
            assert exported.status_code == 200, exported.text
            imported = client.post("/api/campaign/import", json={"text": json.dumps(exported.json())})
            assert imported.status_code == 200, imported.text
            bundle = imported.json()
            saved = client.post("/api/library/command", json={"store": "campaigns", "action": "importBundle", **bundle})
            assert saved.status_code == 200, saved.text
            assert saved.json()["id"] != c["id"]
            wrong = {**record, "metadata": {**record["metadata"], "fixtureId": "wrong"}}
            failed = client.post("/api/library/command", json={"store": "campaigns", "action": "put",
                "campaign": started["campaign"], "expectedRevision": 1, "gameRecord": {**wrong, "revision": 2}, "expectedGameRevision": 1})
            assert failed.status_code == 422
            assert random.getstate() == rng and set(routes.games) == inventory
            current = client.post("/api/library/command", json={"store": "campaigns", "action": "get", "id": c["id"]})
            assert current.json() == stored.json()
    finally:
        for identity in set(routes.games) - before:
            routes.games.pop(identity)


def test_mismatched_sqlite_row_identity_is_corruption(tmp_path):
    path = tmp_path / "library.sqlite3"; repo = library(path)
    saved = repo.command({"store": "games", "action": "put", "record": game(), "expectedRevision": 0})
    with sqlite3.connect(path) as db:
        db.execute("UPDATE records SET document = ? WHERE id = 'g'", (json.dumps({**saved, "id": "other"}),))
    with pytest.raises(ValueError, match="Corrupt"):
        repo.command({"store": "games", "action": "get", "id": "g"})


def test_native_api_owner_is_exclusive_and_crash_releases_lock(tmp_path):
    script = "from native_library_operations import claim_native_library; from types import SimpleNamespace; from pathlib import Path; import sys,time; claim_native_library(SimpleNamespace(native_library_path=Path(sys.argv[1]))); print('ready',flush=True); time.sleep(60)"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    path = tmp_path / "library.sqlite3"
    owner = subprocess.Popen([sys.executable, "-c", script, str(path)], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert owner.stdout.readline().strip() == "ready"
        rival = subprocess.run([sys.executable, "-c", script.replace("time.sleep(60)", ""), str(path)], env=env, text=True, capture_output=True, timeout=10, check=False)
        assert rival.returncode != 0 and "already open" in rival.stderr
    finally:
        owner.kill(); owner.wait(timeout=10)
    replacement = subprocess.run([sys.executable, "-c", script.replace("time.sleep(60)", ""), str(path)], env=env, text=True, capture_output=True, timeout=10, check=False)
    assert replacement.returncode == 0 and replacement.stdout.strip() == "ready", replacement.stderr


@pytest.mark.parametrize("headers", [
    {"Origin": "http://localhost:18465"},
    {"Referer": "http://localhost:18465/game"},
    {"Origin": "null"},
    {"Origin": "http://127.0.0.1:18465", "Referer": "http://localhost:18465/game"},
])
def test_native_guard_rejects_other_browser_origin_before_engine_mutation(tmp_path, monkeypatch, headers):
    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.setattr(routes, "native_library_path", tmp_path / "library.sqlite3", raising=False)
    monkeypatch.setattr(routes, "native_library_origin", "http://127.0.0.1:18465", raising=False)
    before = set(routes.games)
    with TestClient(address_app(app)) as client:
        request = {"season": "2026", "player_team": "Ironclads", "opponent_team": "Thunderhawks"}
        rejected = client.post("/api/game/new", json=request, headers=headers)
        assert rejected.status_code == 403
        assert set(routes.games) == before
        assert client.post("/api/library/command", json={"store": "games", "action": "list"}, headers=headers).status_code == 403
        assert client.post("/api/campaign/simulate", json={}, headers=headers).status_code == 403
        accepted = client.post("/api/game/new", json=request, headers={"Origin": "http://127.0.0.1:18465"})
        assert accepted.status_code == 200, accepted.text
        routes.games.pop(accepted.json()["game_id"])


def address_app(app, host="127.0.0.1"):
    async def addressed(scope, receive, send):
        if scope["type"] == "http":
            scope = {**scope, "client": (host, 12345) if host is not None else None}
        await app(scope, receive, send)
    return addressed


@pytest.mark.parametrize("headers", [{}, {"Origin": "http://127.0.0.1:18465"},
    {"Origin": "http://127.0.0.1:18465", "X-Forwarded-For": "127.0.0.1"}])
@pytest.mark.parametrize("peer", ["203.0.113.7", "testclient", None])
def test_native_api_rejects_remote_peer_before_read_or_mutation(tmp_path, monkeypatch, headers, peer):
    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.setattr(routes, "native_library_path", tmp_path / "library.sqlite3", raising=False)
    monkeypatch.setattr(routes, "native_library_origin", "http://127.0.0.1:18465", raising=False)
    before = set(routes.games)
    with TestClient(address_app(app, peer)) as client:
        assert client.get("/api/library/status", headers=headers).status_code == 403
        assert client.post("/api/library/command", json={"store": "games", "action": "list"}, headers=headers).status_code == 403
        assert client.post("/api/game/new", json={"season": "2026", "player_team": "Ironclads", "opponent_team": "Thunderhawks"}, headers=headers).status_code == 403
    assert set(routes.games) == before
    assert not (tmp_path / "library.sqlite3").exists()


@pytest.mark.parametrize("peer", ["127.0.0.1", "::1", "::ffff:127.0.0.1"])
def test_native_loopback_peer_can_read_without_browser_headers(tmp_path, monkeypatch, peer):
    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.setattr(routes, "native_library_path", tmp_path / "library.sqlite3", raising=False)
    with TestClient(address_app(app, peer)) as client:
        assert client.get("/api/library/status").json() == {"enabled": True}
        assert client.post("/api/library/command", json={"store": "games", "action": "list"}).json() == []


def test_native_library_saves_real_punt_and_restores_receiving_offense(tmp_path, monkeypatch):
    import random

    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.setattr(routes, 'native_library_path', tmp_path / 'library.sqlite3', raising=False)
    before = set(routes.games)
    try:
        with TestClient(address_app(app)) as client:
            created = client.post('/api/game/new', json={
                'season': '2026', 'player_team': 'Ironclads',
                'opponent_team': 'Thunderhawks'}).json()
            identity = created['game_id']
            state = routes.games[identity]['engine'].state
            state.is_home_possession = False
            state.ball_position, state.down, state.yards_to_go = 11, 4, 7
            prior_random = random.getstate()
            try:
                random.seed(8306)
                played = client.post('/api/game/execute', json={
                    'game_id': identity, 'player_play': 'A', 'cpu_play': 'P'})
            finally:
                random.setstate(prior_random)
            assert played.status_code == 200, played.text
            assert played.json()['game_state']['player_offense'] is True
            checkpoint = client.post(f'/api/game/checkpoint/{identity}').json()['checkpoint']
            record = {**game(), 'checkpoint': checkpoint}
            saved = client.post('/api/library/command', json={
                'store':'games', 'action':'put', 'record':record, 'expectedRevision':0})
            assert saved.status_code == 200, saved.text
            stored = library(tmp_path / 'library.sqlite3').command({'store':'games','action':'get','id':'g'})
            routes.games.pop(identity)
            restored = client.post('/api/game/restore', json={'checkpoint':stored['checkpoint']})
            assert restored.status_code == 200, restored.text
            assert restored.json()['game_state']['player_offense'] is True
            assert restored.json()['game_state']['down'] == 1
            assert restored.json()['game_state']['ball_position'] == played.json()['game_state']['ball_position']
    finally:
        for identity in set(routes.games) - before:
            routes.games.pop(identity, None)

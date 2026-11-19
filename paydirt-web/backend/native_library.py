"""Opt-in native library: portable JSON records, atomic linked writes, SQLite CAS.

The HTTP host supplies a private user-data path. The shared hosted/worker runtime
never enables this repository implicitly and accepts no client filesystem paths.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_DOCUMENT = 32 * 1024 * 1024


class LibraryConflictError(ValueError):
    """A stale writer cannot replace the currently committed record."""


def _json(value: Any) -> str:
    text = json.dumps(value, allow_nan=False, separators=(",", ":"))
    if len(text.encode("utf-8")) > MAX_DOCUMENT:
        raise ValueError("Library document is oversized")
    return text


def _revision(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("An expected revision is required")
    return value


def _game(record: Any) -> dict:
    if not isinstance(record, dict):
        raise TypeError("Invalid saved game record")
    for field in ("id", "name", "checkpoint", "savedAt"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"Invalid saved game {field}")
    if len(record["id"]) > 200 or len(record["name"]) > 200 or len(record["checkpoint"]) > 16 * 1024 * 1024:
        raise ValueError("Oversized saved game")
    if not isinstance(record.get("metadata", {}), dict) or _revision(record.get("revision")) < 1:
        raise ValueError("Invalid saved game metadata or revision")
    _json(record)
    return record


def _campaign(value: Any) -> dict:
    from paydirt.campaigns import validate_campaign
    return validate_campaign(value)


def _links(campaign: dict, games: list) -> None:
    if not isinstance(games, list):
        raise TypeError("Invalid checkpoint bundle")
    fixtures = [f for f in campaign["fixtures"] if f["status"] == "in_progress"]
    if len(games) != len(fixtures) or len({g.get("id") for g in games if isinstance(g, dict)}) != len(games):
        raise ValueError("Every active fixture needs one unique checkpoint")
    for game in games:
        _game(game)
        meta = game.get("metadata", {})
        if meta.get("campaignId") != campaign["id"] or len([f for f in fixtures
                if f["id"] == meta.get("fixtureId") and f["game_id"] == meta.get("gameId")]) != 1:
            raise ValueError("Checkpoint does not match active campaign fixture")
    if len({g["metadata"]["fixtureId"] for g in games}) != len(fixtures):
        raise ValueError("Duplicate fixture checkpoints")


class NativeLibrary:
    """One configured local user's durable library; commands never own live engines."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def command(self, request: dict) -> Any:
        """Apply one repository transaction with all preconditions before commit."""
        if not isinstance(request, dict) or request.get("store") not in {"games", "campaigns"}:
            raise ValueError("Invalid library store")
        if request.get("action") not in {"list", "get", "put", "remove", "importBundle", "exportBundle"}:
            raise ValueError("Invalid library action")
        _json(request)
        with sqlite3.connect(self.path, timeout=5) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Unsupported native library schema; existing data retained")
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS records (store TEXT NOT NULL, id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(store,id))")
            if version == 0:
                db.execute("PRAGMA user_version = 1")
            result = self._apply(db, request)
        self.path.chmod(0o600)
        return result

    @staticmethod
    def _read(db: sqlite3.Connection, store: str, identity: str | None = None) -> list:
        rows = db.execute("SELECT id, document FROM records WHERE store = ?" + (" AND id = ?" if identity is not None else ""),
                          (store, identity) if identity is not None else (store,)).fetchall()
        values = []
        for row in rows:
            try:
                value = json.loads(row[1])
                if not isinstance(value, dict) or value.get("id") != row[0]:
                    raise ValueError("Record identity differs from index")
                if store == "games":
                    _game(value)
                else:
                    _campaign(value["campaign"])
                    if value["id"] != value["campaign"]["id"] or _revision(value["revision"]) < 1 or not isinstance(value["savedAt"], str):
                        raise ValueError("Invalid campaign envelope")
                values.append(value)
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError("Corrupt native library record; original data retained") from error
        return values

    @classmethod
    def _existing(cls, db: sqlite3.Connection, store: str, identity: str, revision: Any) -> dict | None:
        expected = _revision(revision)
        rows = cls._read(db, store, identity)
        current = rows[0] if rows else None
        if (current["revision"] if current else 0) != expected:
            raise LibraryConflictError("This record changed in another tab; reload before continuing")
        return current

    @staticmethod
    def _write(db: sqlite3.Connection, store: str, value: dict) -> dict:
        db.execute("INSERT OR REPLACE INTO records VALUES (?,?,?)", (store, value["id"], _json(value)))
        return value

    def _apply(self, db: sqlite3.Connection, r: dict) -> Any:
        store, action = r["store"], r["action"]
        if action == "list":
            return sorted(self._read(db, store), key=lambda x: x["savedAt"], reverse=True)
        if action == "get":
            identity = r.get("id")
            if not isinstance(identity, str) or not identity:
                raise ValueError("Invalid record identity")
            rows = self._read(db, store, identity)
            return rows[0] if rows else None
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if store == "games":
            if action == "put":
                raw = r.get("record")
                if not isinstance(raw, dict):
                    raise TypeError("Invalid saved game record")
                expected = _revision(r.get("expectedRevision"))
                value = _game({**raw, "revision": expected + 1, "savedAt": now})
                self._existing(db, store, value["id"], r.get("expectedRevision"))
                saved = {**value, "name": value["name"].strip(), "revision": r["expectedRevision"] + 1, "savedAt": now}
                return self._write(db, store, saved)
            if action == "remove":
                self._existing(db, store, r.get("id"), r.get("expectedRevision"))
                db.execute("DELETE FROM records WHERE store = ? AND id = ?", (store, r.get("id")))
                return None
            raise ValueError("Unsupported game library action")
        if action in {"remove", "exportBundle"}:
            record = r.get("record", {})
            current = self._existing(db, store, record.get("id"), record.get("revision"))
            if current is None:
                raise ValueError("Campaign no longer exists")
            linked = [g for g in self._read(db, "games") if g.get("metadata", {}).get("campaignId") == current["id"]]
            if action == "remove":
                for game in linked:
                    db.execute("DELETE FROM records WHERE store = 'games' AND id = ?", (game["id"],))
                db.execute("DELETE FROM records WHERE store = 'campaigns' AND id = ?", (current["id"],))
                return None
            campaign = current["campaign"]
            games = [g for g in linked if any(f["status"] == "in_progress" and f["id"] == g["metadata"].get("fixtureId")
                and f["game_id"] == g["metadata"].get("gameId") for f in campaign["fixtures"])]
            _links(campaign, games)
            return {"format": "paydirt-campaign", "version": 1, "campaign": campaign, "games": games}
        campaign = _campaign(r.get("campaign"))
        revision = 0 if action == "importBundle" else r.get("expectedRevision")
        self._existing(db, store, campaign["id"], revision)
        if action == "importBundle":
            games = r.get("games")
            _links(campaign, games)
            for game in games:
                if game["revision"] != 1:
                    raise ValueError("Imported game must have initial revision")
                self._existing(db, "games", game["id"], 0)
            for game in games:
                self._write(db, "games", game)
        elif action == "put":
            game = r.get("gameRecord")
            if game is not None:
                _game(game)
                expected = _revision(r.get("expectedGameRevision"))
                if game["revision"] != expected + 1:
                    raise ValueError("Invalid linked game revision")
                self._existing(db, "games", game["id"], expected)
                self._write(db, "games", game)
        else:
            raise ValueError("Unsupported campaign library action")
        return self._write(db, store, {"id": campaign["id"], "campaign": campaign,
            "revision": revision + 1, "savedAt": now})

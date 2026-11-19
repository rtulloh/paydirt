"""Native-only durable library operations; absent configuration means no disk writes."""
from __future__ import annotations

import os
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from operations import OperationError
from pydantic import BaseModel, ConfigDict


class LibraryCommandRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    store: str
    action: str


def configure_native_library(context: Any, user_data_dir: str | Path) -> None:
    """Enable only for an explicitly selected local user-data directory."""
    context.native_library_path = Path(user_data_dir).expanduser() / "library.sqlite3"
    claim_native_library(context)


def _path(context: Any) -> Path | None:
    configured = getattr(context, "native_library_path", None)
    if configured is not None:
        return Path(configured)
    directory = os.environ.get("PAYDIRT_NATIVE_USER_DATA_DIR")
    return Path(directory).expanduser() / "library.sqlite3" if directory else None


_owner_connections: dict[str, tuple[int, Any]] = {}


def claim_native_library(context: Any) -> None:
    """Keep an OS-released SQLite lock for this native host's process lifetime."""
    path = _path(context)
    if path is None:
        return
    import sqlite3

    directory = path.parent.resolve()
    key = str(directory)
    existing = _owner_connections.get(key)
    if existing is not None and existing[0] == os.getpid():
        return
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = sqlite3.connect(directory / "library-owner.sqlite3", timeout=0,
                                 isolation_level=None, check_same_thread=False)
    try:
        connection.execute("BEGIN EXCLUSIVE")
    except sqlite3.Error as error:
        connection.close()
        raise RuntimeError("Native library is already open in another process; close that application first") from error
    _owner_connections[key] = (os.getpid(), connection)


def _origin(value: str) -> tuple[str, str, int]:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Invalid native frontend origin")
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def install_native_library_guard(app: Any, context: Any, origin: str | None = None) -> None:
    """Pin browser writers before any mutation; absent Origin is a local CLI API.

    A process lease prevents two app hosts from serving one user's library.
    Browser WebLocks coordinate writers inside the single pinned frontend origin.
    This is local application ownership, not hosted authentication.
    """
    from fastapi.responses import JSONResponse

    if origin is not None:
        context.native_library_origin = origin

    def startup() -> None:
        if _path(context) is not None:
            _origin(getattr(context, "native_library_origin", None)
                    or os.environ.get("PAYDIRT_NATIVE_FRONTEND_ORIGIN", "http://127.0.0.1:8000"))
            claim_native_library(context)

    app.add_event_handler("startup", startup)

    @app.middleware("http")
    async def guard(request, call_next):
        if _path(context) is not None and request.url.path.startswith("/api/"):
            try:
                peer = ip_address(request.client.host) if request.client else None
                loopback = peer is not None and (peer.is_loopback
                    or bool(getattr(peer, "ipv4_mapped", None) and peer.ipv4_mapped.is_loopback))
            except ValueError:
                loopback = False
            if not loopback:
                return JSONResponse({"detail": "Native user-data API accepts only loopback clients."}, status_code=403)
            try:
                claim_native_library(context)
            except (OSError, RuntimeError):
                return JSONResponse({"detail": "Native library is unavailable or already open in another process."}, status_code=503)
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                try:
                    allowed = _origin(getattr(context, "native_library_origin", None)
                        or os.environ.get("PAYDIRT_NATIVE_FRONTEND_ORIGIN", "http://127.0.0.1:8000"))
                    for header in ("origin", "referer"):
                        value = request.headers.get(header)
                        if value is not None and _origin(value) != allowed:
                            raise ValueError("Browser origin differs")
                except ValueError:
                    return JSONResponse({"detail": "Use the configured native application origin before changing games or saves."}, status_code=403)
        return await call_next(request)


async def _validate_checkpoints(command: dict, context: Any) -> None:
    """Reject incompatible engine saves before replacing durable records."""
    records = []
    if command["store"] == "games" and command["action"] == "put":
        records = [command.get("record")]
    elif command["store"] == "campaigns":
        if command["action"] == "put" and command.get("gameRecord") is not None:
            records = [command["gameRecord"]]
        elif command["action"] == "importBundle":
            records = command.get("games", [])
    if not isinstance(records, list):
        raise TypeError("Invalid saved game bundle")
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("checkpoint"), str):
            raise TypeError("Invalid engine checkpoint")
        restored = await context.restore_game_checkpoint(context.RestoreCheckpointRequest(checkpoint=record["checkpoint"]))
        identity = restored["game_id"]
        try:
            game = context.games[identity]
            metadata = record.get("metadata", {})
            for metadata_key, session_key in (("campaignId", "campaign_id"), ("fixtureId", "fixture_id")):
                if metadata.get(metadata_key) != game.get(session_key):
                    raise ValueError("Checkpoint campaign linkage differs from library metadata")
            campaign = command.get("campaign")
            if campaign is not None:
                from campaign_operations import _linked_game
                _linked_game(context, campaign, metadata.get("fixtureId"), identity)
        finally:
            context.games.pop(identity, None)


def register_native_library_operations(registry: Any, context: Any) -> None:
    @registry.get("/api/library/status")
    async def status() -> dict:
        claim_native_library(context)
        return {"enabled": _path(context) is not None}

    @registry.post("/api/library/command")
    async def command(request: LibraryCommandRequest) -> Any:
        path = _path(context)
        if path is None:
            raise OperationError(404, "Native user-data storage is not enabled")
        claim_native_library(context)
        # Import sqlite only in a configured native host, never when bundling the
        # stateless browser-worker operation registry.
        import sqlite3

        from native_library import LibraryConflictError, NativeLibrary
        try:
            body = request.model_dump()
            await _validate_checkpoints(body, context)
            return NativeLibrary(path).command(body)
        except LibraryConflictError as error:
            raise OperationError(409, "This save changed in another tab. Reopen it before continuing.") from error
        except (ValueError, TypeError, KeyError, OSError, OperationError, sqlite3.Error) as error:
            # Codec and disk failures leave the previous committed transaction
            # intact. Public errors omit configured private filesystem paths.
            raise OperationError(422, "Native library command failed; prior save retained") from error

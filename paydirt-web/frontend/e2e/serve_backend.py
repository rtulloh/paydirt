"""Isolated real API for browser tests; never run this as a production server."""

from collections.abc import Awaitable, Callable
from pathlib import Path
import random
import shutil
import sys
from tempfile import TemporaryDirectory

from fastapi import Request
from starlette.responses import Response
import uvicorn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "paydirt-web" / "backend"))

from main import app  # noqa: E402
import routes  # noqa: E402


@app.middleware("http")
async def seed_new_game(
    request: Request, call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Seed only at game creation; all plays use the normal engine and RNG."""
    if request.url.path == "/api/game/new" and request.method == "POST":
        random.seed(int(request.headers.get("x-paydirt-test-seed", "20261017")))
    return await call_next(request)


if __name__ == "__main__":
    with TemporaryDirectory(prefix="paydirt-browser-") as directory:
        seasons = Path(directory) / "seasons"
        shutil.copytree(ROOT / "seasons" / "2026", seasons / "2026")
        # Exclude both ignored historical data and user-installed seasons.
        routes.get_all_season_paths = lambda: [seasons]
        routes.SEASONS_DIR = seasons
        uvicorn.run(app, host="localhost", port=8000, log_level="warning")

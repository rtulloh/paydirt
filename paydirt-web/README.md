# Paydirt Web Development

For playing the game, see the [browser walkthrough](../docs/web-interface.md).
This page covers running the React frontend and FastAPI backend from source.
See also the [documentation index](../docs/README.md) and [development guide](../docs/development.md).

## Requirements

- Node.js 24.22.1 or a newer patched 24.x release; release builds and browser CI use Node.js 24.22.1.
- A Python version compatible with the pinned backend requirements. Python 3.12 is a practical development choice;
  the release workflow uses Python 3.10. Newer Python versions may lack wheels for pinned dependencies.
- The repository checkout, including the public `seasons/2026/` data and `docs/`.

## Install Dependencies

From the repository root (macOS/Linux):

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r paydirt-web/backend/requirements.txt
python -m pip install pytest httpx pytest-cov
```

On Windows, use your compatible Python launcher to create the environment and activate it with
`.venv\Scripts\Activate.ps1`. Keep using that environment for backend commands.

In a separate terminal, from the repository root:

```sh
cd paydirt-web/frontend
npm ci
```

## Run Development Services

**Terminal 1**, from the repository root with the Python environment active:

```sh
cd paydirt-web/backend
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2**, from the repository root:

```sh
cd paydirt-web/frontend
npm run dev
```

Open **http://localhost:5173**. The Vite development server proxies API requests to port 8000.
These instructions run the services separately so the selected Python environment is explicit.
Convenience launchers `start.sh` and `start.bat` also live in `paydirt-web/`; review their environment assumptions before use.

## Tests and Build

From `paydirt-web/backend/` in the Python environment:

```sh
python -m pytest tests/ -q -o addopts= --tb=short
```

From `paydirt-web/frontend/`:

```sh
npm test -- --run
npm run build
```

The required [full-game browser regression](frontend/e2e/README.md) starts isolated services and needs Chromium.
Stop development services on ports 8000 and 5173 before running it.
Follow [AGENTS.md](../AGENTS.md#required-full-regression-before-any-push) for the complete pre-push checklist;
these local commands alone are not full regression validation.

## Structure and API

- `backend/main.py`: app startup; `backend/routes.py`: engine adapter and API routes.
- `frontend/src/components/`: UI; `frontend/src/store/`: Zustand state.
- The core engine decides game rules, results, descriptions, scoring, and timing; the UI displays them.
- Player guides under `docs/` are assembled into `GET /api/guide` for offline help. Images use `/api/docs/images/{name}`.

Useful endpoints include `GET /api/health`, `GET /api/seasons`, `GET /api/teams?season=2026`,
`POST /api/game/new`, and `GET /api/game/state/{game_id}`.
The running backend's **http://localhost:8000/docs** provides its API schema.

`POST /api/game/execute` accepts offensive play keys `1`–`9`, `Q`, `K`, `P`,
`F`, and `S`, with optional `+`, `-`, `T`, and `S` suffixes; defensive keys are
`A`–`E`. Calls are case-insensitive. Omit `cpu_play` (or send `null`) to let
the CPU choose. `/api/game/two-point` accepts the same keys without suffixes.
Invalid calls return HTTP 400 without advancing the game.

Browser saved replays are not resumable CLI games or deterministic engine-log replay.
See [saved games](../docs/saved-games-and-standings.md) and the separately labeled
[replay design notes](../docs/dev-notes/replayable-game-logs.md).

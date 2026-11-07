# Paydirt Web Development

For playing the game, see the [browser walkthrough](../docs/web-interface.md).
This page covers running the React frontend and FastAPI backend from source.
See also the [documentation index](../docs/README.md) and [development guide](../docs/development.md).

## Requirements

- Node.js 24.22.1 or a newer patched 24.x release; release builds and browser CI use Node.js 24.22.1.
- A Python version compatible with the pinned backend requirements. Python 3.12 is a practical development choice;
  the release workflow uses Python 3.10. Newer Python versions may lack wheels for pinned dependencies.
- The repository checkout, including the generated 1983 and 2024 charts, the public `seasons/2026/` sample, and `docs/`.

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

`POST /api/game/new` accepts
`player_attempt_end_zone_interception_returns` and
`opponent_attempt_end_zone_interception_returns` (booleans, default `false`).
They follow the human/CPU roles regardless of `play_as_home`. The engine stores
the mapped choices as `home_end_zone_interception_return` and
`away_end_zone_interception_return`; game-state responses and saved replays
include those keys. Missing keys in older saves restore automatic touchbacks.
Direct engine callers can set each team's preference before play with
`engine.set_end_zone_interception_return(home=True, attempt_return=True)`.
The core resolves the return and all subsequent fumbles, fouls and scores.
Completed blocked kicks use the engine result class `blocked_kick`, including a
retained blocked punt completed after a declined kick foul. Display the core
result description and state supplied with the response.

Vite proxies relative `/api` requests, including offline guide images, to
`127.0.0.1:8000` to match Uvicorn's default IPv4 listener. This avoids a local
proxy failure on systems where Node resolves `localhost` to IPv6 first.

`GET /api/game/charts/{game_id}?side=home` returns the active home team's
offense, defense, auxiliary B/QT/fumble, and special-teams tables; use
`side=away` for the visitor. Each table supplies column/row groups and cell
labels, colors, and descriptions for the browser's **CHARTS** viewer. The
endpoint serializes engine-loaded charts without reading arbitrary paths or
advancing play. Result labels retain the loaded symbols; cell fills are
reconstructed from those symbols because CSV files do not preserve spreadsheet
formatting. `backend/chart_viewer.py` owns this display metadata, and the frontend
only renders it. Public-team browser coverage lives in `frontend/e2e/charts.spec.js`.

The chart viewer can also open a standalone reference at
`/?charts=<game_id>&side=home&view=offense`. It shares the modal's display
component without mounting game controls or using the game store. The URL
preserves the selected side and section when opening or reloading a tab/window;
all chart requests remain read-only. Unknown/expired games offer a retry, and
invalid links do not send requests. The desktop layout fits all 30 rows with
the legend collapsed; narrow screens retain scrolling.

Offense renders the loaded Special Plays table beside its main grid at viewport
widths of 1200px and above, aligning the 30 roll rows. Narrower screens stack
the strip below Offense. Special Plays uses a 272px table with a 32px roll
column on the right. Navigation offers Offense, Defense and Special Teams;
Special Plays is included only in Offense. Older `view=special_plays` links
open combined Offense with the selected side preserved. The strip shares the
table renderer and supplied cell labels/colors, without extra chart requests.

`POST /api/game/execute` accepts offensive play keys `1`–`9`, `Q`, `K`, `P`,
`F`, and `S`, with optional `+`, `-`, `T`, and `S` suffixes; defensive keys are
`A`–`E`. Calls are case-insensitive. Omit `cpu_play` (or send `null`) to let
the CPU choose. `/api/game/two-point` accepts the same keys without suffixes.
Invalid calls return HTTP 400 without advancing the game.

When the human is defending, `/api/game/execute` also accepts
`call_defensive_timeout: true` alongside the unchanged formation key.
The engine determines whether to charge the timeout after resolving the
play and any pending penalty decision. Sending this flag while the human
is on offense returns HTTP 400 without advancing the game. Execute and
penalty-decision results expose the engine's `defensive_timeout_used` flag.

Browser saved replays are not resumable CLI games or deterministic engine-log replay.
See [saved games](../docs/saved-games-and-standings.md) and the separately labeled
[replay design notes](../docs/dev-notes/replayable-game-logs.md).

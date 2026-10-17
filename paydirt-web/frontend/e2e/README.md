# Full-game browser regression

From `paydirt-web/frontend`:

```sh
python3 -m pip install -r ../backend/requirements.txt
npm ci
npx playwright install chromium
npm run test:e2e
```

On Linux, use `npx playwright install --with-deps chromium`.
Stop development servers on ports **8000** and **5173** first. Playwright starts
and stops its own backend and Vite server; it refuses to reuse running services.
The GitHub Actions `browser-games` job runs this suite on pushes and PRs.

## What it tests

One browser session completes **two real, full-length games**, first as home
(receiving) and then as away (kicking), against Hard CPU. It selects teams,
performs coin tosses, calls runs/passes/FGs/punts, resolves penalty choices,
handles PATs and kickoffs, continues halftime, and reaches the final screen.

Assertions require all four quarters, exactly one halftime with an untouched
third-quarter clock, a populated play log, API success, no browser errors, and
final scores matching a fresh backend state query. A play/action limit is a
**failure**, never an acceptable substitute for reaching game over. NEW GAME
must clear the log, scores, final/PAT flags, clock, and prior game ID before the
second game proceeds.

All game-changing actions are rendered UI clicks. The test reads (never writes)
the Zustand store for progress and log assertions. No API responses are mocked,
no engine state is injected, and no quarters are shortened. The test-only server
copies only public `seasons/2026/` data into a temporary directory and excludes
user-installed/historical seasons. It seeds the normal Python RNG at game
creation; it does not replace dice rolls. Browser-only timers are accelerated,
and the UI coin toss is fixed to heads so receive/kick choices are reproducible.

This is a smoke/regression suite, not exhaustive coverage of overtime, safety,
all penalty decisions, or all rule eras. Small mocked component tests remain the
right place to cover rare UI branches without changing the engine rules.

Failures retain a screenshot and Playwright trace under `test-results/`:

```sh
npx playwright show-trace test-results/<failed-test>/trace.zip
```

Completed games attach their final API state and action list to the test result.
The suite deletes its in-memory games and never saves standings or replays.

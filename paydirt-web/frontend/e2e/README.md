# Full-game browser regression

From `paydirt-web/frontend`:

```sh
python3 -m pip install -r ../backend/requirements.txt
npm ci
npx playwright install chromium
npm run test:e2e
```

On Linux, use `npx playwright install --with-deps chromium`.
The defaults are backend **8000** and frontend **5173**. If either is occupied,
choose free isolated ports instead of stopping an installed application:

```sh
PAYDIRT_E2E_BACKEND_PORT=18000 PAYDIRT_E2E_FRONTEND_PORT=15173 npm run test:e2e
```

Both overrides must be distinct integer ports from 1 to 65535. They consistently
configure the test backend listener, Vite HTTP/WebSocket proxies, browser URL and
direct test API requests. Playwright starts and stops only its own services and
refuses to reuse an occupied chosen port (`--strictPort` remains enabled). The
public-2026 isolation, full-length games, timeouts and gameplay assertions are
unchanged. Browser fixtures also block requests to unrelated loopback ports, so a
missed URL cannot fall back to a separately installed local app.
The GitHub Actions `browser-games` job runs this suite on pushes and PRs.

`season-recovery.spec.js` uses public 2026 teams and real IndexedDB. It removes
the original backend session, reloads the page, resumes through Saved games, and
checks that an exported/imported active campaign has separate linked identities.
Setup uses the application runtime; restore uses the rendered UI. This supplements
the full-game checks and must run in a real browser to qualify restart recovery.

## Attach to an isolated Chrome for launch diagnostics

If agent-launched Chromium fails before a page opens, you can start a separate
Chrome instance yourself and attach the same tests over CDP. On macOS, run:

```sh
open -n -a "Google Chrome" --args --remote-debugging-address=127.0.0.1 --remote-debugging-port=19333 --user-data-dir=/tmp/paydirt-browser-test --no-first-run --no-default-browser-check about:blank
```

Use a dedicated test profile, then run either suite:

```sh
PAYDIRT_E2E_CDP_URL=http://127.0.0.1:19333 npm run test:e2e
```

```sh
npm run build:browser
PAYDIRT_E2E_CDP_URL=http://127.0.0.1:19333 npm run test:e2e:browser
```

The shared fixture attaches only when `PAYDIRT_E2E_CDP_URL` is set. Otherwise,
Playwright launches Chromium as before. Tests create their own isolated contexts,
retain their request interception and service-port checks, and close only those
test contexts. At teardown, Playwright disconnects from externally started Chrome;
your manually opened Chrome and its original tabs remain open. You can quit that
isolated Chrome when finished. The normal suite still owns its test backend and
frontend; the browser-only suite serves its built static files without a backend.

[CDP attachment](https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp)
has lower fidelity than Playwright's normal connection, so record when you use
this diagnostic route and verify the default launcher separately when available.
[Connected-browser close semantics](https://playwright.dev/docs/api/class-browser#browser-close)
differ from closing a browser launched by Playwright.

## What it tests

The chart viewer test opens all three sections for the public 2026 teams, switches
teams, checks the original-style grids and cell fills, and verifies narrow-screen
scrolling, dialog focus, Escape, and unchanged engine state while browsing. Its
offense/defense screenshots stay in ignored `test-results/`. Additional chart
checks verify that every sheet fits at 1366×768, 1280×900, 1440×1100 and
1920×1080 with text at least 12px, no grid or dialog scrolling, and closed help.
Both new-tab and separate-window launches retain the chosen team/sheet, survive
reload, allow independent chart navigation, and leave the parent game playable.
Browsing must leave engine state unchanged; each launch test then performs a
real kickoff in the parent. Expired links show recovery controls without game
setup or gameplay requests.

The Offense checks also require the compact Special Plays strip beside the
main grid with aligned roll rows, all loaded auxiliary values preserved,
a strip no wider than 300px, and a roll column no wider than 36px on the right.
The phone check verifies that the strip stacks below Offense and fits without
horizontal scrolling; detached charts retain the combined view too. There is
no separate Special Plays control or screen, and older Special Plays links
open combined Offense while preserving the selected team.

One browser session completes **two real, full-length games**, first as home
(receiving) and then as away (kicking), against Hard CPU. It selects teams,
performs coin tosses, calls runs/passes/FGs/punts, resolves penalty choices,
handles PATs and kickoffs, continues halftime, and reaches the final screen.
Both games request defensive timeouts through the modifier panel and must
record at least one engine-confirmed timeout for the human team. The suite
checks the returned timeout budget and description, exhausted controls,
the absence of offense-only modifiers on defense, and cleared selections
after submissions, including pending penalty choices. A response may also report
a defensive timeout the request never asked for: the API forwards the CPU
defence's own timeout decision, so an unrequested timeout must belong to the
CPU side and leave the human budget unchanged (FLOW-029).
Both games also execute every defensive formation A–F and check that each
ordinary request carries the exact selected key. CPU punt/field-goal confirmations
use the existing A placeholder. Each game verifies SAVE GAME's visible success
status and the stored game ID, clock and field position in its isolated browser
storage.

Separate phone-viewport checks load synthetic saved positions using the public
2026 teams and real load API. They verify minutes:seconds log labels, offensive
and defensive modifier names/tooltips, and save confirmation remaining inside
the viewport after scrolling back to the top. They also require both teams'
labeled timeout budgets to fit inside the phone viewport. These focused checks use synthetic
history; the two full-game tests retain normal game lengths and actual histories.

Assertions require all four quarters, exactly one halftime with an untouched
third-quarter clock, a populated play log, API success, no browser errors, and
final scores matching a fresh backend state query. A play/action limit is a
**failure**, never an acceptable substitute for reaching game over. NEW GAME
must clear the log, scores, final/PAT flags, clock, and prior game ID before the
second game proceeds.

The two-game test has a six-minute total budget (three minutes per full game),
allowing slower hosted runners to finish both games in the same browser
session. Other tests keep the default three-minute timeout. Progress checks
still time out after five seconds, each game still has a 450-action limit,
and the hosted browser job retains its ten-minute limit; expiry is a failure.
Each action must produce its API response or reveal its required confirmation
within five seconds. The driver follows a late CPU kick confirmation instead
of waiting for an execution that the first defense click did not request.

In the full-game regression, all game-changing actions are rendered UI clicks. The test reads (never writes)
the Zustand store for progress and log assertions. No API responses are mocked,
no engine state is injected, and no quarters are shortened. The test-only server
copies only public `seasons/2026/` data into a temporary directory and excludes
user-installed/historical seasons. It seeds the normal Python RNG at game
creation; it does not replace dice rolls. Browser-only timers are accelerated,
and the UI coin toss is fixed to heads so receive/kick choices are reproducible.
The first genuine CPU fourth-down response is held until an early defense click,
then forwarded unchanged. This forces the asynchronous decision-panel handoff;
the first completed game must record that follow-up confirmation. It also checks
that a late decision cannot revive a kick panel after possession changes.

`season-desk-acceptance.spec.js` exercises rendered custom season creation, schedule
editing, followed-team standings, engine simulation, statistics/leaders, playoffs,
keyboard focus, mobile table scrolling and persistent-profile Chromium restart.
`checkpoint-recovery.spec.js` uses synthetic engine situations installed only in the
isolated test service to reach a pending penalty, end-zone choice, halftime and an
expired touchdown with a try owed. Recovery then uses the real checkpoint APIs and
rendered Saved games controls; each pending action must resolve exactly once.
`result-review.spec.js` uses trusted synthetic final checkpoints to verify rendered
cancel/confirm, idempotence, correction revisions, statistics recomputation and
temporary-engine cleanup. Its setup endpoints exist only in the isolated test service.

This is a smoke/regression suite, not exhaustive coverage of overtime, safety,
all penalty decisions, or all rule eras. Small mocked component tests remain the
right place to cover rare UI branches without changing the engine rules.

Failures retain a screenshot and Playwright trace under `test-results/`:

```sh
npx playwright show-trace test-results/<failed-test>/trace.zip
```

Completed games attach their final API state and action list to the test result.
The suite uses isolated in-memory games, browser contexts and temporary profiles;
season tests persist their own campaign results there, without changing a player's library.

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
after submissions, including pending penalty choices.
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

All game-changing actions are rendered UI clicks. The test reads (never writes)
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

This is a smoke/regression suite, not exhaustive coverage of overtime, safety,
all penalty decisions, or all rule eras. Small mocked component tests remain the
right place to cover rare UI branches without changing the engine rules.

Failures retain a screenshot and Playwright trace under `test-results/`:

```sh
npx playwright show-trace test-results/<failed-test>/trace.zip
```

Completed games attach their final API state and action list to the test result.
The suite deletes its in-memory games and never saves standings or replays.

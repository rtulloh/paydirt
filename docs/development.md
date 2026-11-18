# Development, Testing, and Packaging

[Documentation index](README.md) · [Project home](../README.md)

## Development Setup

The core CLI requires Python 3.10+ and PyYAML. Install test tools in your virtual environment:

```sh
python -m pip install pyyaml pytest pytest-cov ruff
python -m pytest tests/ -q -o addopts= --tb=short
```

For browser development, follow the [web setup guide](../paydirt-web/README.md).
Backend dependencies are separate from core dependencies. The release workflow currently uses Python 3.10 and Node.js 24.22.1;
use a Python version compatible with the pinned backend packages and available wheels.

Run `ruff check paydirt/ tests/ paydirt-web/backend/` for Python lint checks.
The [generated chart release gate](chart-validation.md) must pass for both public
generated cohorts before release builds. It also runs in pull-request CI and
retains failed JSON evidence.
Runtime-inspected API annotations retain Python 3.9-compatible typing for the
existing local checks; this does not lower the declared Python 3.10+ requirement.
Optional-operation fallback failures emit traceback diagnostics at DEBUG level
without enabling debug logging by default or changing their existing fallback.

## Building the browser-only prototype

The FLOW-033 spike runs the existing Python engine and shared Python application
operations inside one dedicated Pyodide Web Worker behind the React interface.
The HTTP application remains available. Enable the worker transport only with
`VITE_PAYDIRT_BROWSER=1`; the regular `npm run build` continues to use HTTP.
JavaScript handles transport, loading, image blobs and chart snapshots, while
Python owns gameplay and AI decisions.

With frontend dependencies installed and Python 3 available, run:

```sh
cd paydirt-web/frontend
npm run build:browser
npm run test:e2e:browser
```

`build:browser` writes `dist-browser/` with the `/paydirt/` deployment prefix and
stages an allowlisted Python archive and manifest under `dist-browser/browser/`.
The staging receipt lives in ignored `.ai-audits/browser-spike/staging/`. The
archive contains only reviewed application files, public 2026 sample teams and
bundled guide content; it must never include private charts, source inventories,
audits, standings or saved games. The worker verifies the archive's SHA-256 and
size before mounting it at `/app` and importing `browser_bridge`.

The browser must support module Web Workers and WebAssembly. Startup downloads
pinned **Pyodide 0.27.7**, Pydantic and PyYAML from
`https://cdn.jsdelivr.net/pyodide/v0.27.7/full/`; network or policy failures must
surface through the loading/error screen. No service worker or offline guarantee
is implemented. Game sessions are temporary; checkpoint export/import, autosave,
historical seasons and custom chart import remain outside this spike. Detached
chart tabs use a bounded read-only snapshot of the current public chart books,
not a second engine session.

`test:e2e:browser` serves the built static directory on port **18733** and runs the
separate Chromium suite in `e2e-browser/` with no game backend. Build first and
install Playwright Chromium as described in the
[browser regression setup](../paydirt-web/frontend/e2e/README.md). The regular
`npm run test:e2e` still tests the HTTP-backed application and remains mandatory;
the browser-only suite supplements it. The browser-only implementation and test
commands do not establish that deployment, complete games, offline behavior or
cross-browser compatibility have been verified. Record actual outcomes and
remaining gaps in the [1.11.0 plan](dev-notes/release-1.11.0-plan.md).

For a local manual check after building, run:

```sh
npx vite preview --host 127.0.0.1 --port 18733 --strictPort --outDir dist-browser --base /paydirt/
```

Open `http://127.0.0.1:18733/paydirt/`. This preview serves static files only;
Python gameplay executes inside the browser. Publishing a static artifact still
requires all project pre-push gates and separate verification of the actual
published site. No published-site URL is claimed by these instructions.

For a separate engine-only WebAssembly check, run from the repository root:

```sh
npm install --prefix /tmp/paydirt-spike-runtime pyodide@0.27.7
node scripts/audit_browser_spike_runtime.mjs --pyodide-module /tmp/paydirt-spike-runtime/node_modules/pyodide/pyodide.mjs
```

This checks the built archive and completes two sample games. It writes an ignored
receipt under `.ai-audits/browser-spike/`; `--bundle` and `--output` override those
paths. Node execution does not exercise React or Web Workers and cannot replace
either required browser suite.
## Architecture and Project Structure

The core engine is authoritative for game rules, state, scoring, descriptions, and timing.
The CLI and web frontend display engine decisions rather than reconstructing outcomes or implementing their own rules.

| Location | Purpose |
|----------|---------|
| `paydirt/game_engine.py` | Core rules and game flow |
| `paydirt/play_resolver.py`, `priority_chart.py`, `penalty_handler.py` | Play, priority, and penalty resolution |
| `paydirt/chart_loader.py` | CSV chart loading |
| `paydirt/season_rules.py`, `overtime_rules.py` | Season configuration and overtime |
| `paydirt/computer_ai.py`, `ai_analysis.py` | CPU decisions and chart coaching |
| `paydirt/interactive_game.py` | CLI presentation and user choices |
| `paydirt/commentary.py` | Play-by-play presentation |
| `paydirt/save_game.py`, `standings.py` | CLI persistence and results |
| `paydirt-web/backend/` | FastAPI adapter around the core engine |
| `paydirt-web/frontend/` | React browser UI |
| `seasons/1983/` | Public generated 1983 charts |
| `seasons/2024/` | Public generated 2024 charts |
| `seasons/2026/` | Public fictional sample data |
| `extract_charts.py` | [Excel-to-CSV chart generator](chart-generator.md) |
| `tests/` | Core unit tests and standalone integration runners |

## Test-First Changes

For behavior changes, add self-contained regressions first, demonstrate their intended failures,
then fix the implementation and rerun focused and relevant broader suites.
Use synthetic data or public 2026 teams only in unit tests. Private charts must not become hidden test dependencies.
Documentation-only changes do not require invented behavior failures; documentation-loading changes do.

[AGENTS.md](../AGENTS.md) is authoritative for agent workflow and the full mandatory pre-push checklist.
Run **all** of its listed checks before every push, including release/tag pushes, and disclose existing skips and warnings.
Do not treat the quick unit-test command above as full release validation.

- Core and backend pytest suites, frontend tests, production build, and Ruff.
- [Browser regression](../paydirt-web/frontend/e2e/README.md): two complete real-engine games, including clean new-game state.
- `tests/run_all_games.py`: standalone game integration checks.
- [Historical season runner](historical-seasons.md): selected-year actual calendar, simulated or historical-replay postseason, generated-chart support and optional local reproductions.
- `tests/run_ai_audit.py`: full generated Hard-vs-Hard seasons and legacy balanced comparisons; review [play-selection/balance evidence](ai-auditing.md), not just final scores.
- Clean tracked-files-only unit tests from the candidate work tree, so ignored local data cannot mask CI failures: `python3 scripts/run_full_regression.py --clean-checkout` exports the files on disk, including uncommitted tracked edits and new non-ignored files, and refuses to run outside a Git work tree.

The historical calendar audit uses the public `seasons/1983` and `seasons/2024`
charts. Routine regression does not require developer or escrow charts; the
separate opt-in private reproduction runner remains local-only for preserved
archival data and is invoked with
`python3 tests/run_full_season.py --generated-regression`. Default 1983 validation requires all 224 actual regular fixtures and nine
postseason games; selected 2024 validation requires 272 and thirteen. Regular-season ties are
allowed by source-year rules; tied playoff finals fail. Official NFL tiebreak qualification remains
unverified. The old rotating calendar is an explicit additional regression only.

## Building Standalone Applications

Use [.github/workflows/release.yml](../.github/workflows/release.yml) as the current build recipe,
not an assumed list of platform/signing tools. It builds the frontend, copies it to backend `web_static/`,
installs PyInstaller and backend dependencies, then runs:

```sh
pyinstaller paydirt.spec --clean
```

Prepare the frontend assets and Python dependencies first, following the workflow.
The spec includes the runtime-loaded routes and their local chart viewer helper.
Keep these helper modules directly in the bundled backend import directory,
and declare their core dependencies as hidden imports when the entry point does not import them.
Do not add `--onefile` when using the spec file; the spec defines executable packaging.
Platform packaging uses NSIS for the Windows installer, `create-dmg` and
`packaging/macos/create_app.sh` on macOS, and `packaging/linux/create_appimage.sh` on Linux.
Build on the target platform. The workflow does not currently implement the certificate-secret signing recipe
previously shown in the README; do not assume a build is signed.

The specs bundle generated 1983 and 2024 charts, the public 2026 sample, the chart attribution,
Markdown guides, and documentation images. Source and release builds use the same
numeric season directories: `1977`, `1983`, `2024`, and `2026`.
The backend assembles the offline User Guide from the canonical player files in `docs/`.
Relative links between those player guides become in-app anchors; contributor-only documents link to GitHub.
No separately maintained copy of the player manual is needed.

## Releases

The workflow builds releases on `v*` tags and also supports manual dispatch.
Tags are immutable: always choose a new, increasing version; never delete and recreate a failed release tag.
Before creating or pushing a release, follow all [required validation](../AGENTS.md#required-full-regression-before-any-push)
and the project's versioning instructions. [Release notes](../RELEASE_NOTES.md) remain separate from the user manual.

## Project Background

Paydirt was published by Avalon Hill, with team charts designed by mathematician Dr. Thomas R. Nicely.
This implementation models chart/priority resolution, Full Feature Method penalties, the offensive and defensive dice,
special teams, variable-yardage entries, and clock-management procedures.
It is a fan-made project; the original game's names and trademarks belong to their respective owners.

## Pending penalty outcomes

`run_play_with_penalty_procedure` returns a provisional `PlayOutcome` with
`pending_penalty_decision=True` while the offended team chooses. Nothing has been
applied: the spot, down, score, statistics, and `touchdown` flag are unchanged, and
`touchdown` stays `False`. `PlayOutcome.projected_touchdown` estimates whether
accepting the play would score, for CPU decisions and audits only. UI layers must
not place the ball for a try or kickoff, change `pending_pat`, or infer a score
until `apply_*_penalty_decision` returns a finalized outcome.

`PlayOutcome.retained_play_situation` and `PlayOutcome.penalty_situations` are
engine-projected coaching observations: the situation accepting the play would
produce and the situation each eligible enforcement would produce. They are
computed on a shallow state copy with the same `advance_ball`, `next_down`,
`resolve_penalty` and `resolve_pass_interference` routines the applied decision
uses, without changing live state, statistics, call logs or dice. Ordinary
retained first downs are projected for the offense, and ordinary scrimmage
retained plays with an offensive foul are projected for the defense; scores,
safeties, turnovers, fumbles, return chains and requested spikes are not
projected. Consumers treat them as optional hints, never as applied game state.

While an own-end-zone interception choice is pending, every public engine action
that would start or resolve another play—snaps, kickoffs, onside and safety free
kicks, tries, defensive timeouts, penalty decisions and overtime setup—raises
`ValueError`. The matching web action routes answer 409 before changing game
bookkeeping: the deferred play has not changed possession, statistics or the
clock, so any action started first would be recorded out of order. Resolve the
choice before the next action; the engine guard is the authority and the UI only
withdraws its controls.

The deferred play keeps its originating timing. Ordinary scrimmage interceptions
resolve with the 25-45 second scrimmage range, Hail Mary interceptions with the
5-15 second Hail Mary range, and the engine stores that range with the pending
choice (`play_seconds_range`) so a save/load resume charges the same clock as
the uninterrupted game. Legacy saves without the field derive the default from
their saved `play_type`, so an older Hail Mary save also resolves with Hail Mary
timing. A saved range must be two finite numbers of seconds, each within
`0..900` and in order; anything else raises `ValueError` instead of reaching
the game clock.

## Period and try queries after a score

The engine records the period in which each scoring-capable action began
(scrimmage plays, penalty procedures, kickoffs, onside kicks, safety free kicks;
tries preserve it). `can_kickoff_after_play()` and `should_kickoff_after_score()`
default to that recorded period, so UI layers must not pass the live quarter after
`_use_time` has advanced it. `can_attempt_conversion_after_touchdown()` decides
whether a try is still owed: regulation tries are played even when the clock has
expired and the game is provisionally over; both try methods recompute
`game_over` afterwards.

Two-point attempts resolve the chart and return sequence on an isolated
conversion state. Only a two-point scoring entry and the untimed clock trace
reach the live game; ordinary statistics, possession, periods and play/call
histories stay intact. The try scoring entry uses the preceding touchdown's
explicit period and timestamp. The `/api/game/two-point` result supplies
`conversion_success` and `defense_points`; the frontend displays those fields
without parsing scoring prose. Its returned `game_state` owns `pending_pat`,
`can_go_for_two`, and `is_kickoff`, including final tries at 0:00.

## Halftime and the second-half kicker

The engine records which team kicked to open the game (`GameState.opening_kicking_home`,
persisted in saves) and exposes `halftime_pending()` (first half over, second-half
kickoff still owed) and `second_half_kicking_home()`. `prepare_second_half_kickoff()`
hands the ball to that kicker at the kickoff spot. UI layers must use these queries
rather than inferring halftime from one API path or guessing the kicker from
possession; the web API reports `halftime_pending` in every game state.

## OpenCode project permissions

`opencode.json` adapts the Bowl Bound project template to native OpenCode V2
permissions. It allows the named pytest, Ruff, frontend test/build, Playwright,
and standalone game/AI-audit commands used above, including
`python3 tests/run_ai_audit.py` with arguments. Run frontend commands from
`paydirt-web/frontend` and backend pytest from `paydirt-web/backend`.

Read-only tracked-file inspection with `git ls-files` and remote-reference
inspection with `git ls-remote` (with or without arguments) are allowed.
`git checkout-index` (with or without arguments) is also allowed for exporting
staged-only validation snapshots. `git remote` still requires approval.
GitHub CLI (`gh`) commands are explicitly
denied because `gh` is not installed; use GitHub HTTP APIs or web pages instead.
These command permissions do not replace explicit approval
for pushes, tags, releases, or destructive actions. Other shell commands
require approval. The `git push` rule still asks; reset, rebase, checkout,
and `rm` remain denied. Unlike the source template, this file
does not blanket-allow arbitrary `python3` scripts or retain Bowl Bound-specific
frontend paths/environment variables. These permissions are convenience rules,
not a sandbox or a replacement for the required pre-push validation.

The hosted test jobs pin Ubuntu 24.04 and test Python 3.10, 3.11 and 3.12,
matching the package's declared supported minor versions. Matrix failures do not
cancel the other versions. Browser backend, npm, and Chromium/system dependency
installs have separate required steps so setup failures are identifiable even
from the job summary. Local macOS success does not prove hosted Linux setup.

## GitHub Actions runtimes

Both workflows use reviewed Node 24-native action releases: checkout 7.0.1,
setup-python/setup-node 7.1.0, upload-artifact 7.0.2, download-artifact 8.0.2,
and action-gh-release 3.0.3. Codecov 7.1.1 is a composite action whose nested
github-script v8 uses Node 24; its coverage input is now `files`.
These action runtimes are separate from the pinned application build runtime,
Node.js 24.22.1. Node 24 actions require runner 2.327.1 or newer; checkout
authenticated Git operations inside Docker actions require 2.329.0 or newer.
The current workflows use GitHub-hosted runners, not Docker actions.

Checkout retains its default credential handling (now stored under RUNNER_TEMP);
neither workflow uses privileged fork-checkout triggers. Browser npm caching
keeps its explicit frontend lockfile; standalone builds explicitly disable new
automatic package-manager caching to retain their previous behavior. Artifact
uploads retain the default zipped format and named download directories, keeping
release asset paths unchanged. Manual dispatch with `release_tag` can build and publish an existing immutable
version tag after the same exact-commit successful Tests gate as a tag push. Verify upstream tests and all four
standalone platform builds before any release. These runtime upgrades do not
remediate frontend dependency vulnerabilities.

## Required hosted validation

The Tests workflow runs backend pytest as a separate required job, makes Ruff
blocking across core, tests, and backend, and runs the full public 2026 AI audit
with the legacy-balanced comparison. The public audit needs no private charts;
private historical integrations remain local-only. Backend CI installs its pinned
runtime requirements plus pytest and `httpx<0.28`: the pinned FastAPI/Starlette
TestClient uses the older httpx `app` argument. This is a test-only compatibility
bound, not a runtime dependency upgrade or vulnerability remediation. Local
pre-push validation is still mandatory even when hosted checks are green.

Personal standings directories and backups matching `standings_data*/` are
ignored. Keep those files local; never force-add them or include them in release
artifacts. This does not remove existing standings or change persistence behavior.

### Hosted Python test coverage

The Tests workflow runs the complete core suite once with coverage on Python 3.10,
the standalone release build interpreter. Python 3.11 and 3.12 run compatibility
checks covering game setup, save/load, season rules, chart loading and the CLI;
these smaller checks do not establish full-suite coverage on those interpreters.
Backend, browser, public AI and chart-quality jobs remain required separately.
A newer push cancels an older Tests run for the same branch or pull request.


Visual content, selection and collector regressions share session-generated
synthetic chart templates, copying fresh files into each mutation test. They
never share mutable evidence dictionaries or a test's candidate directory.
The hosted full coverage run records its 30 slowest cases to expose remaining
costs; coverage, assertions and full-suite execution remain enabled.

Before publication, the release job rechecks that the existing version tag still
resolves to the exact tested/build commit. It then omits `target_commitish` from
the release API request: GitHub can require workflow-write permission for an
explicit older target whose workflows differ from the default branch, and the
automatic GITHUB_TOKEN cannot obtain that permission. The verified existing tag
still determines released source. Platform builds and chart checks remain pinned
to its SHA; no token scope expansion or tag recreation is needed.

# Web seasons, cross-era games, and durable saves

Owner-approved preview and six-slice direction · 2026-11-18 · **IMPLEMENTED AND RELEASED — v1.12.2; QUALIFICATION AND LIMITATIONS RECORDED**

Tracked in [FLOW-036](https://github.com/rtulloh/paydirt/issues/156). Documentation approval is not implementation or release completion.

The original proposal below is retained as design evidence; dated implementation and
acceptance-audit notes follow it. FLOW-036 is closed from actual acceptance and
[verified v1.12.2 publication](release-1.12.2-readiness.md). Earlier progress statements do not
override missing acceptance criteria identified by the later requirement-by-requirement audit.
The [interactive preview](season-ui-preview.html) uses invented demonstration results;
it neither reads nor modifies games, charts, standings, or the issue tracker.

## Recommended experience

Add a dedicated **Seasons** page alongside **Exhibition**, **Saved games**, and the existing User Guide.
A chart year is an input catalog; a campaign is a separately named, persistent competition.
Two campaigns can both use 1983 without sharing results. Always show the year on mixed-era teams.

The Seasons page has a campaign selector, New season, Import, Export, an explicit save status,
a next-fixture/resume card, and Overview, Schedule, Standings, Team statistics, and Leaders tabs.
Overview highlights the followed team, current week, division race, and recent results.
Schedule distinguishes not started, in progress, completed, simulated, and score-only entries.
Standings offer division/conference/league views. Statistics offer totals and per-game offense/defense.
Empty campaigns show zero records and no fabricated leaders. Mobile tables scroll within their panels.
Use accessible labeled controls, keyboard-operable tabs/dialogs, and visible loading/error states.

Creation has three conceptual steps: template and name; participants/structure/schedule;
rules, control preference, and review. The compact preview combines them in one dialog.

- **Historical replay:** use the actual supported calendar and membership, beginning with 1983
  (28 teams, 224 regular fixtures over 16 weeks), original divisions, home/away assignments,
  and source-year rules. Actual historical scores do not populate played results.
  Show a template only when its entire chart, membership, rule, and fixture inventory is available.
  Preserve byes; do not invent replacement fixtures if inputs are missing.
- **Custom season:** select team editions across available chart years; organize divisions;
  generate single/double round robin or enter fixtures manually, with validation and a review step.
  Allow the same franchise in different years; reject duplicate exact editions initially.
  Validate no self-matchups, unknown teams, or duplicate team appearances in a week; handle odd-team byes.
  Generated schedules can be edited before play. Lock membership, rules, and completed fixture identities
  once play begins; offer Duplicate season to experiment without corrupting an active competition.
- **Multiple campaigns:** independent names, IDs, progress, saves, results, and aggregates.
  Renaming a campaign changes only its label. Archive completed seasons; confirm destructive deletion.

Users can play either side of a fixture, follow a chosen team, and explicitly simulate other fixtures
using the same engine. Simulation is on request, reports progress/cancellation, retains each completed
fixture transactionally, and never overwrites a played/in-progress fixture. Failed games remain uncompleted.
Exhibitions stay out of season standings unless deliberately attached to a compatible, unplayed fixture;
initial scope can omit attachment of older exhibitions altogether.

## What-if games and governing rules

Use independent **Away: chart year + team** and **Home: chart year + team** pickers, plus Swap sides.
Search by name within year with an optional all-year search. The human control side is a separate choice.
Identity is `(chart_year, team_id)`, never a display name, abbreviation, or basename alone.
The picker, game header, save card, box score, season participant, and export retain both values.
Reject catalog IDs outside trusted available teams; never resolve imported arbitrary filesystem paths.

Bowl Bound provides the model: its `frontend/src/components/TeamPicker.jsx` has year-scoped search,
and `frontend/e2e/crossSeason.spec.js` checks independent identities, swap, home-year rules,
and save/load round trips. Paydirt currently accepts one `season` in `NewGameRequest` and
validates both teams against that directory (`paydirt-web/backend/routes.py`).
Cross-era support therefore needs an API/runtime change, not just two dropdowns.

**Proposed rule policy:** exhibition defaults to the home edition’s year, displayed before kickoff;
swapping sides updates that preview. A custom season chooses one fixed rules year for all fixtures,
so swapping venues does not change overtime or two-point availability. Historical campaigns use
their template year. The core receives and enforces the selected rules; the UI displays its summary.
The existing engine derives rules from the home chart directory; a fixed campaign rules policy needs
an explicit, tested core configuration seam. Confirm this policy before implementation.
Cross-era charts are used as supplied; no era-strength normalization is claimed.

## Results, statistics, and leaders

Keep a canonical completed-game ledger, not manually incremented W/L counters. A fixture has one
accepted final result revision. Commit only when the engine declares a legal final and all follow-up
scoring procedures are resolved. Commit fixture completion, final box, and aggregate invalidation in one
transaction. Retrying after reload, double-clicks, worker timeouts, and re-import cannot count it twice.
Aggregate W/L/T, PF/PA, division/conference/home/away records and team statistics in the shared Python
season service. Frontend tables render those values without implementing standings or game rules.
Regular-season and postseason statistics remain distinct. Rank tied records using a documented policy;
never label existing regression ordering as full official NFL tiebreaking.

Start with team categories supported by authoritative counters: scoring offense/defense, total offense,
rushing offense, net passing offense, and giveaways; derive defensive allowed totals from opponent boxes.
Define formulas against engine counters before implementation, especially gross/net passing and sacks.
`paydirt/game_state.py:TeamStats` supplies total/rushing/gross-passing yards, first downs, giveaways,
penalties, sacks and components. `paydirt/models.py` also has a different older TeamStats definition;
the implementation must use the active engine model. The current API exposes only a subset.
Do not promise third-down rates, completion percentages, time of possession, or player leaders from
missing counters. Additional engine measurement is a separate reviewed feature.

**Owner decision, 2026-11-18:** team statistics and team leader categories only. Individual player
statistics and leaderboards are out of scope; the owner considers player attribution cosmetic.
Do not create a player-statistics milestone or make it a dependency of season support.
Show GP and denominators beside leader rates; tied leaders share ranks. Missing stats are unknown,
not zero. If score-only manual/imported results are supported, they affect W/L/PF/PA but not box-score
leader denominators. Mark incomplete coverage and keep those results visibly distinct.

For result correction, retain the previous revision and provenance, replace the accepted result, and
recompute standings/statistics. Reopening a finished fixture or replacing its result must be explicit.
After postseason seeding, freeze feeding results or invalidate dependent brackets with clear confirmation.

## Persistence and save/load foundation

Browser-only currently runs Python in a worker and explicitly hides/disables saving
(`App.jsx`, `runtime/gameFetch.js`, `MenuPhase.jsx`, `PlayingPhase.jsx`).
`utils/saveGame.js` stores a display-oriented localStorage snapshot; that is not a durable engine save.
The replay route reconstructs state from a web payload and searches for both teams in one year.
Neither should be adopted unchanged as the canonical cross-era save format.

1. Extract a versioned in-memory serializer/restorer from the existing CLI save behavior in
   `paydirt/save_game.py`, retaining legacy CLI compatibility through file adapters. Audit field completeness
   against engine and web wrapper state before reusing it. Capture AI context, control side/difficulty,
   both chart editions, governing rules, phase, pending choices, clock/OT/halftime/post-score obligations,
   stats, history, and linked campaign/fixture IDs. Preserve necessary RNG state for pending decisions;
   do not claim deterministic future replay unless explicitly tested. Save catalogs use portable IDs and
   chart/rule content identities, not machine paths. Missing/changed charts produce an explicit compatibility
   error; never silently substitute another year. Validate imports before constructing an engine.
2. Expose identical export/restore operations through the shared operation registry for HTTP and Python-worker
   transports. Native/hosted runtime ownership and game-local RNG isolation need implementation verification;
   the browser bridge currently serializes dispatch, which alone does not guarantee multiple-game RNG isolation.
3. In browser-only play, store versioned campaign records, fixture results, and engine checkpoints in
   **IndexedDB** transactions. Keep only lightweight preferences in localStorage. Autosave after each
   acknowledged engine action, including a pending choice, and before leaving a game. Restore only the last
   committed checkpoint; do not retry an uncertain timed-out action automatically. Show Saving/Saved/Failed,
   the timestamp of the recoverable save, and a downloadable backup option. Do not clear a usable save on
   failed migration, quota error, or rejected import. Multiple tabs use revision checks and a single-writer
   lease per game/campaign; stale tabs must reload before acting.
4. For native/local backend play, use a durable user-data repository (stdlib SQLite is the proposed adapter)
   rather than the source checkout or in-memory `games` dictionary. Keep the domain contract shared with the
   browser adapter. Do not add account/cloud storage in this scope. A shared hosted server would require
   explicit user ownership/authentication before it could store private campaigns; browser-local ownership
   avoids that issue for the static browser distribution.
5. Export/import named games and entire campaigns, with schema/version, IDs, fixtures, results, completeness
   flags, chart identities, and active checkpoints. Do not embed private charts or raw chart source material.
   Import defaults to a new campaign identity, rewriting fixture/game references consistently; replacement
   requires explicit review. Reject duplicate result revisions and malformed/oversized input atomically.
   Existing web snapshots can be offered as best-effort legacy imports only where completeness is proven;
   do not call a partial reconstructed display snapshot a fully resumed game.

Persistence survives normal refresh and browser restart on the same origin/profile. Clearing site data,
private browsing, changing devices, and changing origin are different boundaries. Explain this next to
Export, request persistent browser storage where available, and offer backups. Offline engine installation
and cross-device sync are separate features; a durable save alone does not promise offline loading.
Preview persistence is only a tiny isolated demo store, not this proposed production implementation.

## Proposed delivery slices / future issue drafts

Create issues only after design agreement; each numbered item can be independently reviewed.

1. **Canonical game checkpoints and browser save/load.** Shared serializer, safe restore, named saves,
   autosave, import/export, error UX, and legacy compatibility. Verify actual browser restart and native
   process restart, plus pending penalty, PAT, kickoff/free kick, halftime, interception decision, OT, and
   untimed down restoration. Preserve the prior recoverable checkpoint on write/migration failure.
2. **Cross-year exhibition setup.** Independent pickers, composite identities, swap, control side,
   visible home-year rules, path confinement, and round-trip saves. Same franchise/different years succeeds;
   duplicate exact edition is rejected. Keep same-year API clients working with an explicit migration path.
3. **Persistent season domain and result ledger.** Campaign/participant/fixture/result schemas, repositories,
   historical 1983 template adapter, completeness flags, exactly-once result commits, corrections/recompute,
   import/export and revision conflicts. Domain service remains separate from audit scripts/CLI filesystem UI.
4. **Seasons page and historical play loop.** Campaign CRUD/selector, dashboard/tabs, fixture launch/resume,
   engine-owned standings and full supported team statistics/leader categories. Same-year campaigns remain
   isolated; reloading a finished game does not duplicate its result. Real full-calendar sources are runtime
   packaged assets, not dependent on a development-only path.
5. **Custom and mixed-era seasons.** Participant picker reused from exhibitions, structure and schedule review,
   fixed campaign rules seam, byes, validation, duplicates, locked active definitions, and portable exports.
6. **Remaining-game simulation and postseason.** Cancellable engine-driven simulation, legal finals,
   resumable progress, supported playoff format, and explicit tiebreak policy. Original historical playoff
   participants must not be forced into a replay whose results changed. If postseason is required at first
   release, include this slice in that release and resolve the ranking policy first.

Dependencies: 1 precedes durable season play; 2 precedes mixed-era campaigns; 3 precedes 4;
1–4 precede 5–6. Scope can ship incrementally while keeping incomplete features clearly unavailable.

## Validation and release

Use test-first synthetic/public-2026 fixtures for every behavior change; demonstrate baseline failures
and passing controls. Historical data belongs in separate integration checks, never collected unit tests.
Measure coverage for changed Python modules and report gaps. Test pure domain logic once in the core,
transport parity in backend/worker tests, and real browser flows with actual IndexedDB/restarts/imports.
Exercise duplicate finalization, result revision, partial data, quotas, two tabs, broken/migrated imports,
missing chart identity, interrupted simulation, and multiple same-year campaigns. Include narrow/mobile
and keyboard checks. Do not infer save correctness merely from a scoreboard screenshot.

Before every push run all root AGENTS.md regression gates, including clean tracked-file checkout,
full historical season, AI audits, browser full games, and released-chart identity checks. Packaging must
include supported template assets and migrations. Update the user guide and offline guide bundle.
After release, validate downloaded native artifacts and their season/save flows. A feature flag can disable
new entry points; retain data and backward-readable exports for rollback. Schema upgrades need backups
and must not destructively mutate the only copy. No pushes or release changes are part of this design task.

## Decisions for owner review

- **RESOLVED — leader scope:** owner explicitly excluded individual player statistics on 2026-11-18.
  Team statistics and team leader categories are the agreed scope.
- **IMPORTANT — mixed-era rules:** approve home-year exhibition defaults and one explicit fixed rules year
  per custom season, or choose another policy before the core configuration contract is implemented.
- **IMPORTANT — season completion:** should first release include simulating remaining games and playoffs?
  Recommended: both belong in the eventual season experience, with transparent initial ranking policy;
  official historical tiebreak qualification is a separate scope decision, not an existing capability.
- **IMPORTANT — manual results:** recommendation is engine-played/simulated games first; if manual score
  entry is required, include the partial-statistics rules above rather than inventing box scores.

## Grilling Notes

**Assumptions verified:** 6/8 implementation assumptions: one-year web selection, worker browser transport,
disabled browser saves, existing CLI serialization, historical 1983 fixture infrastructure, and Bowl Bound
identity/swap tests are verified in the source paths cited above. Serializer completeness across all web
phases and native storage/runtime ownership remain unverified and are explicit slice-1 investigations.

**Open Questions:** 6 -> 4 (removed 2, added 0, sharpened 4). Whether schedule data already exists is
answered by `config/season-schedules/1983.json` and `paydirt/historical_season.py`; whether existing web saves
already solve restart recovery is answered negatively by the browser guards and save/replay paths above.
The remaining four are product scope choices, not requests for information already present in code.

**Status changed:** No: QUESTIONS_PENDING. The design is reviewable; rule policy and release scope need
agreement before converting it into implementation-ready tickets.

**Key revision:** fixed rules per mixed-era campaign, an idempotent canonical result ledger, and team-only
initial leaders prevent venue-dependent rules, double-counted games, and unsupported player statistics.

Review also rejected treating localStorage display snapshots as engine saves, assuming all historical
seasons are valid templates, counting unknown statistics as zero, and treating regression seed ordering as
official NFL tiebreaking. Simpler browser-local persistence is sufficient for the static deployment;
cloud accounts/sync are deferred. Native persistence uses an adapter rather than a second season rules engine.

## Preview verification — 2026-11-18

`python3 -m pytest tests/test_documentation.py -q -o addopts= --tb=short`: 1 passed.
`git diff --check`: passed. A standalone jsdom check passed all five tabs, campaign switching,
custom creation with isolated localStorage persistence, independent exhibition year selectors,
complete selection swap, rules banner updates, and saved-game navigation.

Actual desktop/mobile browser inspection and screenshots remain **UNVERIFIED**. Playwright Chromium
failed to launch with macOS MachPort permission errors, including an escalated retry; launching the
Chrome application through macOS failed because its executable was unavailable. No browser visual,
layout, native restart, or actual game recovery success is claimed. The preview has no engine connection;
its play/resume/simulate/box-score buttons explain the intended transition. Campaign creation only stores
preview metadata; schedule types, divisions, and simulation preferences illustrate future setup controls.
No production behavior or existing test expectations changed, and no full release regression was run.

Local preview while its server is running:
<http://127.0.0.1:18463/season-ui-preview.html>.
To reopen later, run `python3 -m http.server 18463 --bind 127.0.0.1 --directory docs/dev-notes`
from the repository root. The self-contained HTML can also be opened directly, although local-file
storage behavior varies by browser. These files are local uncommitted proposals, not remotely preserved.

## Owner approval and execution workflow — 2026-11-18

The owner approved the mockup and six-slice delivery approach, requested a tracking issue, and asked
for subagents and goals to support completion. The owner subsequently explicitly excluded individual
player statistics. The remaining rules, release-boundary, and manual-entry choices above remain open;
the earlier Grilling Notes describe the initial review before these owner responses.
No product implementation, release target, push, or publication is claimed by this documentation task.

### Subagent assignments and sequencing

Use an integrator plus at most three concurrent specialist agents, with exclusive ownership of shared
files and bounded assignments. An independent subagent reviewed this decomposition during issue creation.

| Role | Assignment | Dependency / handoff |
| --- | --- | --- |
| Integrator | Freeze operation/schema contracts, assign file ownership, integrate, maintain issue evidence, run final gates | Owns cross-cutting files until explicitly handed off; accepts each slice only after validation |
| Persistence/domain agent | Slice 1 checkpoints and persistence, then slice 3 campaigns and result ledger | Establish portable team IDs and versioned contracts first; return baseline failures, patch, focused coverage, and known gaps |
| UI agent | Slice 2 exhibition selectors, then slice 4 Seasons page, then slice 5 custom setup | Production integration waits for accepted identity/API/domain contracts; isolated mockups may proceed earlier |
| Verification agent | Independent acceptance/failure review, separately owned integration tests, restart and browser evidence | Coordinate test ownership; do not duplicate the implementer's tests or edit the same files concurrently |

Assign slice 6 simulation/postseason after stable campaign/result contracts and policy agreement.
Reassign a freed specialist slot rather than keeping an agent idle. Do not concurrently edit the same
route module, game store, serialization schema, or migration. Use isolated worktrees for overlapping
changes where useful, with explicit integration ownership. A shared interface change goes through the
integrator before downstream agents implement against it.

### Goals and evidence

Create an explicit, bounded goal when the owner authorizes a slice for implementation; this request
explicitly authorizes goal-based execution planning. Each delegated task names its parent issue/slice,
objective, owned files, prerequisites, acceptance tests, scope exclusions, and integration handoff.
The agent tracks a goal for that assigned objective; avoid a vague autonomous goal to “finish everything.”
Do not infer authorization to publish or make destructive changes from a goal.

Each goal's completion record contains:

- the test-first baseline failures and passing controls;
- the implementation and any changed existing test expectations, with reasons;
- focused regression, changed-module coverage and intentional gaps;
- applicable guide updates, independent review findings and their disposition;
- actual runtime/browser or native evidence required for that slice, including remaining failures.

The integrator accepts completion only when the integrated result meets the slice criteria. A finished
agent response or exhausted token budget is not completion evidence. Reassign bounded follow-up work
for review defects; keep incomplete goals active with truthful progress, applying tool-specific blocked
and paused rules. Do not mark the umbrella achieved until all agreed slices and required integration,
full regression, and play-test evidence are complete. Follow tracker semantics: resolved requires a tested
committed fix; closed requires the specified play-test confirmation. Documentation-only goal completion
does not change any feature ticket to resolved or closed.

### Permissions and preservation

No permission-model change is needed to record this issue or prepare local reversible work. Existing
sandbox and consequential-action approval rules still apply. For future implementation, prefer scoped
capabilities for required validation over blanket permission changes. Keep prompts focused on actual
access restrictions or unresolved product policy; do not ask again for ordinary already-authorized work.
Important uncommitted implementation and ignored evidence must be remotely preserved and verified before
the machine reset under root AGENTS.md. No push bypasses regression gates; private evidence belongs in
private Drive, never the public repository. These planning files remain local until an authorized,
qualified preservation step is performed.

## Implementation integration — 2026-11-18

The owner's subsequent “proceed” authorized implementation of the six slices. The initial
open choices above were resolved for this implementation using the recommended defaults:
home-year exhibition rules; a selected fixed rules year for every custom-campaign fixture;
engine-played/simulated results only; remaining-game simulation and postseason included.
These are implementation defaults, not a claim of official historical NFL tiebreak qualification.
Individual player statistics remain excluded. The earlier review/preview sections are retained
as dated design evidence rather than descriptions of the current source tree.

The implementation uses one typed, chart-bound JSON checkpoint codec shared by HTTP and the
browser worker. Campaigns and checkpoints live in IndexedDB with revision checks and atomic
linked writes. Imported seasons receive fresh campaign/participant/fixture/game identities.
Exports contain game state and chart fingerprints, never chart contents. Simulation uses the
core engine and commits one final at a time; cancel takes effect between games. The current
checkpoint schema has no older-schema migration; unknown versions are rejected while keeping
the existing durable records. Restore preserves deferred decisions and captured decision RNG;
it does not promise identical future random outcomes across independent sessions.

The canonical player guides are [seasons](../seasons.md),
[saves](../saved-games-and-standings.md), and [web interface](../web-interface.md).
Independent review identified and prompted regression fixes for incomplete active-game exports,
stale campaign views, rules-year defaults, readable box scores, fixture editing and keyboard
modal behavior. Integration review additionally requires pending-choice restoration, coin-toss
failure handling and actual edition/rules validation before accepting a season result.

Validation is in progress. Full frontend suite at this point: 479 passed. Full backend suite:
522 passed with existing deprecation warnings. These counts precede the final recovery fixes.
Actual browser and native restart/focus/mobile validation remain unverified; Chromium launch
fails during macOS process registration. Node/Pyodide checks supplement, never replace, the
required full real-browser regression. No commit, push, release, remote backup or completed
umbrella goal is claimed by this progress record. FLOW-036 remains open.

Actual Node/Pyodide checks passed on public bundle `ae5fea7fe8986c864cee654ee012973140fa4f33562a13bdd0f7ae77b6875967`:
eight complete games, 224-fixture historical template, cross-year checkpoint equality,
fixed-2026 mixed-era rules, active season bundle import/remap/resume, real simulation, and
corrupted chart-binding rejection. Ignored receipts: `.ai-audits/season-ui/node-wasm.json`
and `.ai-audits/season-ui/campaign-node-wasm.json`. This is runtime evidence, not a
claim of rendered-browser restart or visual acceptance.

Final backend regression after recovery/completeness corrections: **529 passed**, with
371 existing httpx/Pydantic deprecation warnings. Focused core domain/simulation/auto suites:
152 passed; campaigns 93%, simulation wrapper 100%, auto-game 77% branch-inclusive coverage.
The remaining auto-game paths are older display/rare gameplay branches; this is not a
claim of complete engine coverage. Campaign gaps include defensive rejection branches.
Checkpoint coverage is 90%, campaign operations 87%, production routes 91%; the frozen
launcher loads a separate copied routes module and must not be mistaken for production
routes coverage. Unknown legacy turnover components now remain unknown in both played and
simulated results. Restore transports an engine-derived pending_result for unresolved
penalty and own-end-zone interception choices, hydrated before automatic UI effects.

Frontend integration at this checkpoint: 490 passed; production build passed. Documentation,
tracker and explicit browser-bundle packaging tests: 489 passed. Existing Browserslist age
and Vite mixed static/dynamic import warnings remain visible. Frontend focused coverage:
checkpoint/library/session 100% statements, selector 98.64%, Seasons page 81.47%, SavedGames
100%, App 64.47%, PlayingPhase 73.53%, store 65.94%. Older replay/menu/gameplay branches
outside the focused suites account for the latter gaps; actual browser acceptance is separate.

After the last recovery review, the full frontend suite passes **494 tests** and the production
build passes. CPU PAT/fourth-down effects wait while a save failure is outstanding and retry
after a successful save without repeating acknowledged actions. Restored penalty decisions
suppress conflicting PAT/kickoff controls. The restore test's halftime phase expectation is
`playing`: this uses the existing PlayingPhase halftime overlay once; routing to `halftime`
showed both the App halftime screen and that overlay. A full App regression demonstrated the
duplicate prompt before the fix. No game clock/score or engine kickoff obligation changes.
Focused PlayingPhase coverage after these fixes is 76.99% statements / 78.09% branches;
store 65.86% / 75.92%.

Final browser build also passes: public Python archive SHA-256
`f305a77c478fde9dab3e05b2aafbc551dcf3e695f59ecbb7988746996ccf7e97`.
The campaign Node/Pyodide audit passed all 17 transport/runtime checks on this archive;
its receipt above now describes this final hash. The earlier eight-full-game audit retains
its earlier hash and is not represented as rerun on the final archive.
The new public-2026 `e2e/season-recovery.spec.js` parses, but actual execution failed
before its test body: Chromium MachPortRendezvous bootstrap_check_in permission denied
(1100), SIGTRAP. No real IndexedDB/restart assertions, mobile/focus inspection or native
restart acceptance are claimed. The isolated failure trace is in ignored frontend
`test-results/season-recovery-season-fix-aa56d--as-an-independent-campaign/trace.zip`.

Full-regression progress: core **11,740 passed**, backend **529 passed** (375 warning
instances in that run), frontend **494 passed**, build/lint pass, fourteen-game runner
passes, historical 1983 **224 regular + 9 playoff games pass**, public AI **32/32** and
1983 AI **448/448** complete, and released 1983/2024 chart audits pass. Clean candidate
checkout testing is still running. The first runner browser step encountered an occupied
port; a separate retry on fresh isolated ports 58374/58375 started both services correctly
but all 21 browser tests failed at Chromium launch before assertions. The failure remains
MachPort registration permission denied, not a browser pass. Full output is retained in
ignored `.ai-audits/season-ui/final-browser.log`. The full runner is therefore unqualified
for push regardless of the remaining clean-checkout result.

The final regulation-TD obligation review found an additional reachable integration bug:
the engine can publish game_over while a permitted PAT remains owed. Four failing frontend
regressions and a real public-2026 backend continuation now cover this. Durable final metadata
and restore presentation defer campaign finalization/final display while pending_pat or an
authoritative pending choice remains. The raw engine state stays unchanged. The checkpoint
retains the try, duplicate execution is rejected, and the result commits idempotently after
the try. Latest complete suites: **499 frontend**, **530 backend** (374 existing deprecation
warnings). Browser build passes; archive hash remains identical to the final Wasm audit above.
The current-permission recovery retry on isolated ports 58499/58500 also fails before a page
opens with the same MachPort error; `.ai-audits/season-ui/full-access-recovery-browser.log`
retains that evidence. No additional permission request is needed or pending.

An isolated source UI is available for owner review while its processes run at
<http://127.0.0.1:18466/> (backend 18465). HTTP checks confirm the app, health route and
both complete historical templates respond successfully. This is the implemented UI,
distinct from the original HTML mockup; it has not been visually inspected by the agent.
To recreate it from the repository, run the backend's `main:app` through Uvicorn on
127.0.0.1:18465 with the project virtualenv, then run Vite with
`PAYDIRT_E2E_BACKEND_PORT=18465 PAYDIRT_E2E_FRONTEND_PORT=18466 VITE_API_BASE=http://127.0.0.1:18466`
and `--host 127.0.0.1 --port 18466 --strictPort`. Use free alternative ports if occupied;
saves belong to the chosen browser origin.

### Final local validation status — 2026-11-18 12:01

The clean candidate checkout passes **11,740 tests**, matching the working-tree core run.
The complete runner finishes **12 passed / 1 failed / 0 skipped**. Its receipt is
`.ai-audits/full-regression/20261118T173530Z/summary.json` (plus summary.md and per-step logs).
Browser is the sole failed gate; the fresh-port full-suite and current-permission targeted
retries described above establish the unresolved macOS Chromium launch failure. Subsequent
final-PAT regressions bring the final separately rerun frontend/backend suites to 499/530;
both final normal/browser builds pass. No production core changes followed its successful
working-tree and clean-checkout runs.

Independent AI review reconciles both reports and every CSV situation field. Public totals:
32 games, 4,896 calls, 219 situations; historical: 448 games, 65,793 calls, 3,181 situations.
The two balanced-coach concentration advisories repeat AI-008's reviewed third-and-long
observations; no Hard warning or new questionable selection finding emerged. Recorded a
timestamped AI-008 comment. Historical replay confirms 233 finals with no accounting errors,
pending untimed downs or playoff ties. The resolved-ticket inventory yields no justified
new closures without its required targeted evidence.

FLOW-036 stays open. Browser restart/visual/focus/mobile acceptance and native restart
qualification remain incomplete. The root implementation goal is not marked achieved.
No commit, push, release, verified remote copy or reset backup is claimed; all changes and
ignored receipts remain local. A fresh fully passing required regression remains mandatory
before any future push.


### Final continuation runtime checks (2026-11-18 12:33)

The normal `python -m paydirt --web --port … --no-browser` command now reaches
web mode in source and frozen-dispatch regressions. Native path precedence is
explicit argument, nonempty environment setting, then frozen platform default;
unconfigured source mode stays browser-owned. Every enabled native launcher
installs ownership/origin/peer guards. Test-first dispatch baseline: four expected
failures/eight controls; final backend suite: 574 passed, existing deprecations.
Focused launcher coverage is 28%; the newly changed dispatch/configuration paths
are exercised, while old CLI flows remain outside that focused measurement.

The actual normal-launcher audit passes ten checks, including native HTTP/frontend
transport, CAS/import, ownership, noncanonical origin rejection, loopback binding,
crash release and restore after restarting on a different port. Receipt:
`.ai-audits/season-ui/native-launcher.json`. A rejected rival exposes no API but its
launcher main loop can remain alive after its server thread fails; clean failure
exit is not claimed. The final guide-bound browser archive SHA-256 is
`2d10a17bde00e7216f3c2aad0949f9d0f4733445f778cd8f892b5e65621be738`;
`.ai-audits/season-ui/campaign-node-wasm.json` passes all 18 checks on that archive.
The browser registry loads native operation capability stubs without loading SQLite.

Final frontend suite: 538 tests in 69 files, production build passed. Existing
Browserslist age and mixed static/dynamic import warnings remain. The final actual
browser retry used ports checked on IPv4 and IPv6; services started, but Chromium
failed before assertions with MachPort bootstrap permission denied (1100), SIGTRAP.
Receipt: `.ai-audits/season-ui/final-candidate-browser.log`. Required browser game,
recovery, real IndexedDB/Web Locks, focus, mobile and visual acceptance remain
unverified. The fresh full runner is still completing its clean candidate check;
no push or release is qualified. The acceptance matrix is the current scope audit.


### Fresh full regression outcome (2026-11-18 12:40)

`.ai-audits/full-regression/20261118T181701Z/summary.json` records 12 passing
steps, one failed browser step and zero skips. Both core runs (working tree and
tracked-only candidate export) pass 11,745 tests; frontend 538 and backend 568
at their run points. The later narrow launcher dispatch fix is covered by the
574-test backend run and normal-entrypoint audit above. All nonbrowser runner
gates pass, including the fourteen-game, 224-plus-nine season, AI and released
chart checks. This is not a single immutable final-candidate qualification;
subsequent launcher/docs work has its separate evidence, and required browser
acceptance has not passed. No push is permitted from this receipt.

The runner browser failure is an existing localhost port conflict. The separate
final-candidate retry verified free IPv4/IPv6 ports, started both services, and
failed at Chromium launch before any assertion with MachPort permission denied
(1100), SIGTRAP. Preserve both receipts rather than treating either as a skip or
as successful gameplay. The umbrella remains open and the root goal unachieved.
Do not repeat broad regressions without changed source or new evidence: the
remaining actual-browser acceptance requires a functioning browser environment.

## Local implementation acceptance complete — 2026-11-18

All six slices now have local implementation and actual browser acceptance evidence.
The canonical [acceptance record](season-ui-acceptance.md) preserves original failures,
test-first fixes, focused coverage, final command provenance and remaining publication
limits. Final HTTP suite: 28 passing tests; built-Wasm suite: five passing tests,
including eight full games across all four public years without an HTTP backend.
Native restart/Web Locks and built-browser persistence receipts each pass eight checks.
Team statistics only; individual player statistics remain excluded.

The current interactive implementation preview is <http://127.0.0.1:18785/> while
its isolated process runs. The original illustrative HTML preview remains design
evidence. Implementation is uncommitted and unpublished; FLOW-036 stays open for
review/integration. Ignored evidence and preview libraries have no verified remote
backup; do not confuse local acceptance with preservation or released-artifact health.

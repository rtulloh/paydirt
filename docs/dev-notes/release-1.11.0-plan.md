# v1.11.0 plan: play Paydirt directly in the browser

**Status: proposed; ready for a bounded feasibility spike, not production qualification.**
**Owner scope:** FLOW-033 is the sole feature for v1.11.0 (2026-11-17).
No browser prototype, performance benchmark or human comparison has run for this plan.

[Ticket](issues/FLOW/FLOW-033.md) · [Developer notes](README.md)

## Player outcome and recommendation

Open a link, choose teams and coach difficulty, and play the existing Paydirt game
without installing Python, downloading a native app or starting a local server.
Returning players should find a clear Continue action and retain a portable save.
Keep the familiar charts, play choices, descriptions and full game flow.

Lead candidate: the existing React/Vite interface with the existing Python engine
running in one dedicated Pyodide Web Worker. Preserve the CLI, FastAPI web app and
native distributions. Players see one Play entry point; runtime selection belongs
to the build, not a player settings screen.

This is a distribution and continuity feature. Its enjoyment hypothesis is fewer
interruptions and easier return visits, while preserving the existing board-game
experience. It does not imply that WebAssembly changes football strategy or makes
the underlying game more fun. Actual players must validate the hypothesis.

## Approaches to compare

These are predictions from source review, not scored experimental results.

| Approach | Expected player benefit | Main cost or risk | Role |
|---|---|---|---|
| Current native/local web application | Familiar complete interface; established native runtime | Download, installation and launch friction | Measured baseline |
| Existing React + Pyodide worker | Link-to-play with familiar controls and local execution | Initial download, runtime compatibility and durable saves | Preferred prototype |
| Minimal PyScript page, using Python | Small experiment to learn bootstrap complexity | Rebuilding the current interface would consume scope | Maximum two-hour technical comparison |
| New lightweight Vite interface | Potentially simpler UI | Recreates charts, coaching controls and pending-choice handling | Defer unless reuse fails |
| Hosted existing FastAPI + React | Link-to-play using native Python | Hosting, server sessions, privacy/operations and network dependence; not browser-only | Documented fallback, requires a separate scope decision |
| Rewrite engine in JavaScript | Browser-native execution | Second rules engine and extensive parity risk | Reject for this release |

PyScript can also use workers; do not compare an intentionally blocked main-thread
prototype with a worker implementation and conclude the wrapper determines quality.
Use the same engine, assets and scenario. Cap the comparison rather than building two products.

## Findings that change the earlier ticket plan

- The frontend has scattered direct HTTP calls in
  [App.jsx](../../paydirt-web/frontend/src/App.jsx),
  [PlayingPhase.jsx](../../paydirt-web/frontend/src/components/Game/PlayingPhase.jsx)
  and hooks. There is no already-complete transport boundary to swap.
- [routes.py](../../paydirt-web/backend/routes.py) owns session bookkeeping,
  response models, CPU operations and pending-action handling. Extract narrowly
  scoped application operations; importing FastAPI into the worker is not the plan.
  Revision/idempotency protection must be added and tested, not described as existing.
- Current web replay restoration reconstructs state from display fields/history.
  [save_game.py](../../paydirt/save_game.py) is a different path-based codec, with
  AI state potentially stored separately. Neither proves a complete portable browser
  checkpoint. Inventory every required engine, AI, RNG and application-session field.
- Separate chart windows and the assembled User Guide also use backend resources.
  Include their data, images and lifecycle in transport/asset qualification.
- The package declares PyYAML in [pyproject.toml](../../pyproject.toml); a
  standard-library-only runtime assumption would be wrong.
- The earlier Pyodide 0.27.7 pin is a compatibility control, not an automatically
  approved shipping runtime. Record exact Python/package versions and hashes;
  review maintained-runtime suitability before selecting the release pin.
- [1977 acceptance](../released-chart-regression.md#exact-1977-statistical-acceptance)
  binds source and runtime identity. Wasm execution and extracted service code cannot
  inherit its native Python proof. Establish the applicable qualification route
  explicitly; do not broaden the old metadata exception or silently drop a season.

## Scope boundary

Include the shared application operations needed by current supported gameplay,
worker transport, reviewed static assets, loading/error recovery, genuine game
continuation, portable export/import, and versioned offline/update behavior.
Preserve all existing player choices and engine-generated descriptions.

Exclude new AI behavior, new charts/seasons, multiplayer, AI spectator mode,
season-management UI, general interface redesign, custom-chart authoring and a
shared cross-game runtime framework. Existing native/CLI standings remain supported;
adding missing web standings features is separate work. Related defects may be fixed
only where they directly block browser parity or safe continuation, with explicit tests.

Target desktop Chromium, Firefox and Safari first. Browser automation WebKit is
additional evidence, not proof of real Safari or physical mobile support. Do not
advertise mobile support without device usability and performance evidence.

## Stage 1: bounded technical spike

Budget: 16 engineering hours, including a maximum two-hour PyScript comparison.
Use only synthetic fixtures and the public 2026 sample teams. Keep exploratory code
isolated from release paths. The spike may discover that a gate fails; record that
result and stop rather than quietly extending the experiment.

1. Freeze scenarios, measurement schema, runtime candidates and reference desktop/
   network/browser versions. Record current native/local startup and play latency.
   Inventory imports, filesystem assumptions, locks, optional dependencies, AI model
   writes and save completeness. Test the pinned Python 3.12-compatible control first.
2. Load the actual engine and sample charts in a worker with PyYAML. Exercise kickoff,
   scrimmage, CPU choice, pending decision, scoring transition, save and continuation.
   Use a minimal fixed-operation harness before extracting the full HTTP service.
3. Compare seeded native and worker execution for the vertical-slice commands: legal
   choices, score, possession, clock, statistics, traces, commentary and AI decisions.
   Snapshot/restore RNG explicitly. A complete synthetic game and rare-branch matrix
   are stretch work here and mandatory later; do not turn them into hidden prerequisites
   for completing a 16-hour investigation.
4. Measure the same small scenario through a minimal PyScript implementation. Record
   integration and dependency differences; full UI parity is not expected in two hours.
5. Probe save-text transport, AI sidecars, large JSON integers and path remapping.
   Inventory missing checkpoint fields and estimate the work; full portable-save
   migration and exhaustive storage/crash testing belong to implementation.
6. Produce a go/no-go receipt, import/operation inventory, measured budgets, known
   gaps, runtime rationale and revised estimate. A go requires real engine imports,
   sample loading, a working slice and credible solutions for continuation blockers.
   Missing import/play proof or failed measured budgets means investigate or defer.
   Untested release cases remain explicit qualification work, never assumed passes.

Carry forward the ticket's proposed budgets; freeze them before measurements.
Apply latency/transfer limits to the measured spike slice; the memory, recovery and
full parity requirements must all be qualified on the eventual release candidate:

| Measurement | Gate and reporting |
|---|---|
| Sample runtime + two-team cold transfer | At most 25 MiB compressed; include all required requests |
| Cold runtime-ready p95 | At most 30 s on declared 10 Mbit/s desktop profile |
| Warm runtime-ready p95 | At most 5 s |
| Ordinary command p95 after loading | At most 200 ms; report expensive AI separately |
| Main-thread heartbeat gap during simulation | At most 100 ms |
| Memory/retention | Report peak and ten-game trend; investigate monotonic retention |
| Correctness/recovery | No duplicate mutation, silent state loss or mixed-version assets |

Measure at least 20 independent cold/warm loads per tested desktop profile, with
caches explicitly controlled; retain raw samples and actual tail results. Record
time to first playable decision separately from runtime readiness. Sample-team
numbers do not qualify the larger final season payload: remeasure the release build.

## Stage 2: decide with player evidence

A technical pass authorizes a playable comparison, not a claim that users prefer it.
Build a narrow end-to-end slice in the existing React interface, with complete
gameplay for the sample teams. Compare it with the current native/local application;
compare a PyScript UI only if it has comparable player features.

Recruit the owner plus approximately four players, including newcomers and returning
players. If fewer participate, disclose the actual count and limit the conclusion.
Counterbalance order, use the same teams/difficulty and comparable scripted situations.
Run first-use and return sessions; observe without coaching except to record assistance.

Tasks: reach the first kickoff from the normal entry point; play offense and defense;
consult charts alongside play; use a timeout, resolve a penalty and a conversion;
save, close and return; export/import in a fresh session; finish a game and start
another. Include offline return after explicit caching and interrupted-update recovery.
Use synthetic prepared situations for rare branches so every participant sees them;
do not depend on random occurrence in a short playtest.

Record time, assistance, abandonment, misclicks, unexplained waits, duplicated actions,
and whether players can explain where their progress is saved. Ask for 1–7 ratings
of startup ease, return ease, responsiveness, enjoyment and confidence in saved progress.
Ask which version they prefer and why, and whether they want to play another drive.
Do not use satisfaction ratings as correctness evidence.

Correctness, complete gameplay and reliable continuation are pass/fail prerequisites.
For eligible approaches, use ease of starting/returning 35%, uninterrupted/enjoyable
play 35%, responsiveness 20%, maintainability/release cost 10%. Define score anchors
before the trial and retain individual observations; technical reviewers score the
maintenance criterion. No invented planning scores or statistical claims from a small
sample. Prefer the worker option only if observed access improves, enjoyment is
preserved or improved, and no progress-loss/duplicate-action problem remains.
Mixed results trigger a focused revision/retest, not automatic approval by weighted average.

## Stage 3: implementation after both decision gates

Each behavior change follows test-first development: add failing synthetic/public-2026
cases, demonstrate expected baseline failures and passing controls, implement, then
run focused suites with changed-module coverage. Keep changes separately reviewable.

1. Define framework-free Python operations and a complete session checkpoint contract.
   Characterize existing HTTP behavior before extraction. Keep decisions in the core
   engine and coaching code; transport adapters handle requests/errors only.
2. Introduce frontend transport access and remove active raw HTTP dependencies from
   gameplay, setup, chart windows and help. Retain HTTP mode and its existing tests.
3. Add one worker/session command queue with fixed versioned operations, request IDs,
   expected revision and session generation. Reject stale actions and ignore stale
   responses. Duplicate requests return the recorded result rather than roll again.
   Serialize saves/loads with commands. Never blindly retry an uncertain mutation.
4. Stage an explicit public asset allowlist with hashes, attribution and licenses.
   Use existing Python loaders against the virtual filesystem; lazy-load reviewed
   season/team packs. No recursive copy of local seasons, audits or source bundles.
5. Add validated portable checkpoints and explicit export/import first, then
   transactional IndexedDB continuation. Preserve raw text across JS/Python boundaries.
   Resolve native path/AI-sidecar compatibility in Python; require continuation parity
   where compatibility is promised. Validate native-to-browser-to-native round trips
   with complete AI/session context. Retain legacy replay viewing separately without
   calling its lossy reconstruction an exact resume. Chart windows read immutable
   assets or use an explicit connection to the main tab; they never start another
   independent game engine. Test reload, blocked popups and main-tab closure.
6. Acknowledge saves only after durable transaction completion. On persistence failure,
   keep the live session, clearly offer export/retry and retain the last valid checkpoint.
   Recover crashes from the last acknowledged revision without automatically replaying
   an uncertain action, and disclose any unpersisted action. Define second-tab
   ownership so two tabs cannot overwrite a save.
7. Add versioned offline assets and explicit readiness for downloaded content. New
   sessions can adopt an update; an active game stays on its asset/runtime generation.
   Validate a complete new cache before switching, retain compatible checkpoints and
   test interrupted updates, eviction, quota failures and blocked storage. Preserve
   the previous readable checkpoint until migration and its new write succeed.
8. Qualify the final reviewed public season inventory, full-game browser journeys,
   native/browser compatibility, static build/release process and player guides.

## Release qualification and rollback

Keep the complete root AGENTS.md regression, tracked-files-only clean test export,
released-chart checks, AI/play-selection review, per-issue audit and any applicable
1977 policy gate. Existing HTTP real-engine browser games remain mandatory; add static
browser full games in both human home/receiving and away/kicking orientations, with
no backend process or API dependence. Test targeted rare branches through real Python.

Exercise Chromium, Firefox and WebKit automation plus real supported Safari. Cover
pending decisions, halftime, overtime, final score/box score, charts in another window,
guide images, checkpoint reload and corrupt/missing/version-mismatched assets.
Inspect network requests to prove the browser path does not require FastAPI.

Test the actual downloadable static release artifact and deployed immutable build,
not only Vite development output. Verify hashes, route/base-path behavior, complete
season/team inventories, game/chart loading, offline return and error logs.
Retain existing downloaded native-artifact verification for every supported target.
An uploaded asset or green build alone is insufficient.

Rollback: retain the last verified immutable static build and native downloads;
stop offering a bad browser build to new sessions, preserve saves and explicitly
reject incompatible checkpoints. Never mutate immutable tags, downgrade a live
session in place, or erase IndexedDB as a repair. Older cached clients need a tested
version boundary; changing the landing page alone is not sufficient rollback.

## Work allocation and estimates

Use bounded subagent tasks with one integrator controlling contracts and shared files:

- Runtime reviewer: real Wasm import/parity/latency evidence and runtime maintenance.
- Player-experience reviewer: player journeys, chart access, loading and return sessions.
- Persistence/release reviewer: checkpoint inventory, failure injection, cache lifecycle,
  public asset inventory and release-policy constraints.
- Integrator: freeze scenarios/contracts, reconcile findings, conduct owner playtests,
  choose an approach and review changes. Agents can independently review evidence;
  they cannot substitute for human preference testing.

Parallelize independent research and later tests. Do not have multiple agents
independently design conflicting session formats or edit the same central files.

Planning range: 16-hour spike, then approximately 3–6 engineering weeks including
integration, player revisions and platform qualification. This is a provisional
judgment, not measured velocity or a promised release date. Re-estimate after the
spike; missing persistence parity or release-policy resolution can extend it.

The December 4 machine reset is a separate hard preservation constraint. Before any
work could be lost, preserve tracked/uncommitted planning and prototype work remotely
after required push gates, and private evidence in private Drive with actual destination
and verification. This planning session does not claim remote preservation or perform
a push; a local plan alone is not a verified backup.

## Open decisions and readiness

Ready to start the isolated spike; production architecture remains conditional.

- Select and justify a shipping runtime after compatibility/maintenance review.
- Establish the complete checkpoint contract and exact legacy/native interoperability
  that can be proven; no silent loss of AI context or pending procedures.
- Resolve applicable 1977 source/runtime acceptance before promising all released
  seasons in Wasm. Neither old metadata allowances nor native results grant it.
- Freeze supported desktop versions, real-device test access and static hosting origin.
  Host deployment/publishing is a later explicit action, not part of this planning task.
- Run the owner/player comparison before declaring the easiest or most fun approach.

## Grilling Notes

**Assumptions verified:** 4/4 concrete source assumptions checked: scattered HTTP
calls, incomplete portable saves, backend-dependent chart windows and runtime-bound
1977 acceptance. Runtime performance and preference remain explicitly unverified.

**Open Questions:** five decision groups retained and sharpened above; none removed
without evidence. Runtime selection, checkpoint compatibility and 1977 qualification
block production commitment; device/hosting choices must be frozen for qualification.

**Status changed:** READY for the isolated spike; QUESTIONS_PENDING for production.

**Key revision:** keep the 16-hour spike to import/vertical-slice and save-feasibility
evidence, then qualify complete continuation and gameplay separately. Independent
adversarial review also added chart-window ownership, uncertain-action recovery and
checkpoint-aware rollback. PyScript's small technical comparison cannot establish a
player-experience ranking against a complete React interface.

## References

Repository evidence is linked above. External capabilities do not establish Paydirt
compatibility or performance:

- [Pyodide worker execution](https://pyodide.org/en/0.27.7/usage/webworker.html):
  execution can be separated from the UI thread; message transport is still required.
- [Pyodide 0.27.7 changelog](https://pyodide.org/en/0.27.7/project/changelog.html)
  and [current changelog](https://pyodide.org/en/stable/project/changelog.html):
  pin and qualify a release rather than assuming the old control is current.
- [Browser storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria):
  persistent browser storage is not a substitute for portable save exports.

## Executed spike decomposition — November 17, 2026

The owner subsequently authorized implementation and publication of a playable
GitHub-hosted spike. This supersedes the planning-only publication boundary above;
it does not declare the full v1.11.0 feature complete.

The work was divided among three agents and an integrator:

| Owner | Deliverable | Acceptance evidence |
| --- | --- | --- |
| Architecture agent | Neutral operation registry, native HTTP adapter and JSON browser bridge | Existing HTTP suites plus bridge tests; actual Pyodide import and engine execution |
| Player experience agent | Existing React controls through one worker, startup/failure feedback, charts and guide | Frontend tests and full browser games; owner preference test still required |
| Review/bundle agent | Deterministic public-only archive, inventory and independent review | Synthetic boundary tests, byte hashes and review findings |
| Integrator | Static build, GitHub Pages workflow, browser game driver, full regression and publication | Required local gates, deployed-site checks and a verified playable URL |

The local spike uses pinned Pyodide 0.27.7, a single serialized worker and the
existing React interface. The archive includes only the two public 2026 sample
teams. Browser sessions are temporary; save/resume and replay controls are disabled.
The native application keeps its existing HTTP transport. No core engine file was
changed for this spike.

Actual Node-hosted WebAssembly execution loaded Python 3.12.7, Pydantic 2.10.5 and
PyYAML 6.0.2 without FastAPI. The latest rebuilt-archive run dispatched 397 successful
operations and completed home/receiving and away/kicking games, with all four
quarters and one halftime each (scores 28–12 and 30–28). The local receipt is
`.ai-audits/browser-spike/node-wasm.json`; it binds archive SHA-256
`60e13f70b45a46b1713ea5bba1f585726c9e1768f569e88e8070fcf871ac1a71`.
This proves engine execution in Wasm, not the React UI or browser worker.

Browser validation remains open: Chromium currently aborts during macOS Mach-port
registration before loading the page, including after the access settings changed.
The checked-in browser driver requires both full games with no HTTP API backend.
All unconditional full-regression and browser gates remain required before pushing.
The separate 1977 acceptance gate is not applicable to this sample-only deployment:
the verified static inventory includes only public 2026 teams, and this change makes
no native-release, tag or 1977 compatibility claim. This is an applicability decision,
not a passing acceptance receipt or waived requirement. Missing pinned historical
evidence remains a blocker for future qualification that includes 1977.

The usability comparison remains a human task: measure first launch through kickoff,
a complete offensive and defensive series, chart consultation and error recovery;
record confusion, responsiveness and enjoyment against the native interface using
the scenarios above. A successful technical spike alone cannot determine which
approach is most fun. Publication and the owner playtest are still pending.

### Validation checkpoint

The owner confirmed the local Chrome build launched and reached kickoff without
issue. This is the first human browser startup result; complete human games and
preference scoring remain unverified.

The current frontend run passes 407 tests in 49 files. Backend passes 474 tests;
both native and browser production builds pass, as do the public-only builder's
19 tests and 461 documentation/tracker checks. The full 1983 season completes
224 regular-season and nine postseason games. Both AI audit schedules and both
released-chart audits pass. Known existing warnings are accepted per the owner.
Core and clean-checkout test runs are still in progress at this checkpoint.

Failure handling was tightened during review: unstructured worker failures and
internal operation errors end the temporary session rather than permitting another
potentially uncertain action. The internal-error regression first failed because a
500 response resolved normally (five passing controls), then passed after the fix.
The focused transport/startup suite passes 13 tests; `gameFetch.js` has 100% line,
statement and function coverage and 88.09% branch coverage. Remaining branches are
defensive late-reply, missing-method and image/JSON alternatives. No existing test
expectations were weakened.

Optional `PAYDIRT_E2E_CDP_URL` attaches both browser suites to an isolated Chrome
started from the owner's Terminal when agent process registration fails. The
fixture's four tests pass with 100% line and branch coverage; default launching and
loopback request guards remain in place. This connection option does not itself
constitute a browser-game pass.

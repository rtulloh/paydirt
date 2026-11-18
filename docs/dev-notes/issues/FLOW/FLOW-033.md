---
id: FLOW-033
title: Evaluate browser-only Paydirt using Pyodide/PyScript and WebAssembly
status: open
priority: Low
target-release: v1.11.0
created-at: 2026-11-14
resolved-at:
closed-at:
tags:
  - investigating
links:
commits:
---

## Description

Evaluate the proposal to offer a browser-only Paydirt distribution that runs the existing Python core game logic, rules and chart parsing client-side through Pyodide or PyScript instead of requiring a local Python backend. The initial proposal notes two possible paths: a static PyScript prototype embedded in HTML, and a Pyodide runtime in a Web Worker behind the existing frontend or a lightweight Vite bundle. It also raises expected trade-offs that need measured evidence: first-load WebAssembly/runtime size and caching, browser startup and simulation performance, virtual filesystem and save persistence, static chart/season asset loading, browser compatibility, offline behavior, and the effect on the current CLI, web backend, packaging and release process.

## Resolution / verification

- Follow the [v1.11.0 approach and evaluation plan](../../release-1.11.0-plan.md); FLOW-033 is the release's sole feature. The latest planning update below supersedes the earlier v1.10.7 scheduling and unverified architecture assumptions.
- Run a time-boxed feasibility spike that loads the existing core engine under Pyodide or PyScript in an isolated browser context, using only public sample teams under seasons/2026, and record startup, package size and basic play-path results.
- Inventory runtime assumptions that may block or complicate browser execution: Python version, standard-library use, path and filesystem access, process/environment dependencies, subprocess use, native or optional packages, chart/season asset layout, save/load and standings persistence, and any browser-incompatible code.
- Compare the static PyScript prototype with a Pyodide plus Web Worker/React or Vite architecture. Cover load time, memory, UI responsiveness, caching/offline behavior, browser support, debugging, automated testing and maintainability; do not assume zero rewrites or a weekend delivery until the spike proves it.
- Define how public charts, season rules, rosters, saves and standings would be packaged or persisted in the browser, including IndexedDB or browser filesystem options, and explicitly keep private chart/source material out of any static publication.
- Document what a browser-only build would preserve or lose compared with the current CLI, Python-backed web app, desktop packaging and required full-regression/release verification. Produce a recommendation, effort estimate and follow-up tickets, or record why the approach is not worth pursuing.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-17 18:30 ---
Targeted for the v1.10.7 follow-up release. This remains an exploratory,
time-boxed feasibility investigation and does not block v1.10.6.

Recommendation: run a bounded two-engineering-day spike using one dedicated
Pyodide Web Worker behind the existing React/Vite frontend. Keep the Python
engine, rules, chart parsing, AI/coaching, commentary, save codec and standings
logic authoritative. Treat a small PyScript page only as a capped comparison;
retain the CLI, FastAPI application and native packages regardless of the spike
outcome. This recommendation is based on source inspection and published runtime
documentation, not an executed browser prototype or compatibility proof.

The current transport seam is the frontend API layer, but the FastAPI routes also
own session registration, revision checks, validation, error mapping and view
serialization. A production browser path should first extract those operations
into a framework-free Python application service shared by HTTP and worker
transports. JavaScript should handle transport, loading and storage only. Expose
fixed, versioned operations with request IDs; serialize mutations and save/load;
do not provide arbitrary Python evaluation or blindly retry an action after a
worker timeout.

Stage an exact browser allowlist of public engine code, season rules, team charts,
rosters, provenance and licenses into the virtual filesystem with reviewed hashes.
Use only the fictional public sample teams for the initial spike. Never publish
private charts, raw sources, narrative logs, audits or player saves. Load through
the existing Python loaders rather than creating a second JavaScript chart parser.

Begin persistence with opaque save-text download/upload through the existing save
validation. Test native Python 3.12 to browser to native continuation before adding
optional IndexedDB autosave. Browser storage can be quota-limited or evicted, so
acknowledge an autosave only after its transaction commits and keep explicit save
exports as the portable backup. Campaign persistence must reuse engine-backed
standings and duplicate-final protections; it is outside the initial demo.

Pin the initial compatibility candidate exactly to Pyodide 0.27.7, which documents
Python 3.12.7 and includes PyYAML 6.0.2, then record `sys.version_info` and runtime
hashes. Verify real path-based loaders, SHA-256, random-state round trips, reentrant
locks, save validation and replay in Wasm. Do not float to `latest`; any runtime
upgrade requires a separate compatibility decision. Worker execution is preferred
to keep synchronous Python away from the UI thread. Offline service-worker caching
is a later static-site concern and requires HTTPS or a trusted local origin.

The spike stops after 16 hours with a go/no-go report. Day 1 imports the real
execution graph, hydrates both sample teams and exercises kickoff, scrimmage,
pending choices, save/load and continuation. Day 2 runs deterministic parity and
failure cases, compares a minimal PyScript path for at most two hours, and measures
cold/warm startup, command responsiveness, memory and a small persistence/offline
experiment. Do not publish the prototype or extend the time box into a UI rewrite
or custom Wasm runtime.

Proposed acceptance gates, to freeze before implementation:

- exact Python 3.12 runtime imports the engine and PyYAML without FastAPI,
  subprocesses or Python thread creation;
- scripted commands match native state, legal choices, scores, possession, clock,
  statistics, traces, commentary and AI decisions after every step, including a
  complete synthetic regulation game and continuation cases;
- native/browser save round trips preserve raw large-integer JSON text and reject
  changed charts, invalid/oversized saves and stale revisions without mutating the
  active session;
- two-sample cold transfer is at most 25 MiB compressed, cold p95 at most 30 seconds
  on a declared 10 Mbit/s desktop profile, warm p95 at most 5 seconds, and ordinary
  command p95 at most 200 ms after load;
- main-thread heartbeat gaps remain at most 100 ms during worker simulations;
- memory and ten-game retention are measured, with monotonic growth investigated;
- offline reload, missing/hash-mismatched assets, blocked/quota-limited storage,
  corrupt checkpoints, worker crash and interrupted update fail clearly without
  silently mixing asset versions;
- Playwright Chromium, Firefox and WebKit run, with real Safari and physical mobile
  devices recorded as required evidence if mobile support is proposed.

Recommend deferral if import or replay requires game-rule changes, a custom Python
build, relaxed save validation, unreviewed assets, an unresolved runtime maintenance
risk, or materially misses the agreed usability budgets. A partial proof is a
recorded investigation result, not completion of browser support.

If the spike passes, deliver separately reviewable work in this order: record an
ADR and measurements; extract the shared framework-free application service; add
the worker transport and exact asset manifest; add transactional save persistence
and versioned offline caching; qualify browser/native parity and failure recovery;
then document and verify the downloaded static release. Planning estimate is
13-22 engineering days including the spike, roughly 3-6 calendar weeks for one
developer with review and platform access. This is a judgment from inspected seams,
not measured implementation velocity or a release date.

Share the benchmark schema, runtime and asset pinning, worker lifecycle experiments,
storage-failure matrix and license checks with the related Bowl Bound investigation.
Do not share either game's rules, stores, chart formats, private assets, save schema,
season fallbacks or replay repair. Consider a small bootstrap/transport helper only
after both spikes demonstrate the same need and its licensing is reviewed.

Official references reviewed for this plan: Pyodide 0.27.7 worker, changelog,
package and filesystem documentation; the current Pyodide threading FAQ; PyScript
worker and `sync_main_only` configuration documentation; and MDN documentation for
storage quotas, worker termination and service-worker deployment. These references
establish candidate capabilities, not measured Paydirt compatibility.

--- 2026-11-17 18:34 ---
Owner scheduled FLOW-033 as the sole feature for v1.11.0. See the
[canonical approach and evaluation plan](../../release-1.11.0-plan.md), informed by
independent architecture, player-experience and adversarial subagent reviews.

Preferred candidate remains the existing React interface plus a dedicated Pyodide
worker. Begin with a bounded 16-hour import/vertical-slice investigation, including
at most two hours of PyScript comparison; complete service extraction and save
migration are later work. Follow with a comparable playable prototype and observed
owner/player first-use and return sessions before choosing production delivery.
Judge ease, enjoyment and responsiveness from observed tasks, not framework labels.

Corrections to the earlier comment: direct HTTP calls are scattered; revision and
idempotency protection are new work; native path-based saves and web replay
reconstruction do not provide an already-proven portable checkpoint. Keep engine,
AI, RNG and pending-session state explicit. Reassess the shipping runtime and resolve
1977 source/runtime qualification without expanding its historical allowance.

No production code, browser prototype or human playtest was run in this planning
change. This ticket remains open; targeting v1.11.0 is not evidence of delivery.

--- 2026-11-17 18:51 ---
Owner authorized implementation and publication of the playable GitHub spike.
Three agents divided runtime extraction, player interface and public bundle/review;
the integrator owns static hosting and final qualification. See the executed
breakdown in the canonical v1.11.0 plan.

Local implementation loads the unchanged core through Pyodide in one worker,
uses the existing React controls and includes only the public 2026 sample teams.
Sessions are explicitly temporary; save/replay controls are disabled in this spike.
Actual Node-hosted Wasm completed two full games, including both human roles and
halftime. Backend and frontend tests pass. The owner reports the local Chrome
build launched successfully and reached kickoff without issue. This is direct
human startup evidence, not confirmation of complete browser games or enjoyment.

Agent-launched Chromium aborts before loading pages during macOS process
registration. Full browser games, final regression/push gates and deployed-site
verification remain pending; no GitHub playable URL or completed feature is claimed.
Known release warnings are accepted per the owner's instruction; genuine failures
and missing acceptance evidence remain separately recorded. Ticket stays open.

--- 2026-11-17 19:16 ---
Pre-publication spike gates now pass: core and clean checkout each 11,559 tests,
474 backend tests, 407 frontend tests, both builds, lint, gameplay/season/AI and
released-chart gates. The owner launched isolated Chrome for automation; all 20
HTTP browser tests and the static browser's two complete games pass. The latter
verified both human roles, halftime, finals and fresh new-game state without an
HTTP game backend. Corrected a driver wait for UI-only CONTINUE transitions;
full-game and isolation assertions were retained. Fixed native helper packaging
and strengthened its transitive-import regression. Core gameplay and charts remain
unchanged. The 1977 gate is not applicable to the verified sample-only deployment
inventory; this is not a historical-season qualification claim.

See the canonical plan's validation checkpoint for retained evidence. Publishing
and deployed-origin verification are next. Ticket remains open for production
scope beyond the playable sample spike; no v1.11.0 release/tag is being cut.

--- 2026-11-17 19:30 ---

Browser run `44214569238` failed after the UI allowed a second CPU punt while a
human penalty decision was pending. Trace review confirmed two execute responses
without an intervening decision. Added failing regressions before fixing pending
choice guards and an independently reproduced kickoff chooser-ownership bug.
Frontend now passes 420 tests; full regression and both complete browser games
are being repeated before pushing. Core rules and charts remain unchanged.
FLOW-033 stays open pending deployed-origin proof and remaining feature evaluation.

--- 2026-11-17 19:53 ---
The penalty correction now passes full regression: core and clean checkout each
11,559 tests, backend 474, frontend 420, all twenty native browser tests, both
complete static browser games, season/AI/chart/lint/build gates. The malformed
audit-comment timestamps caught by an earlier run are corrected and the full core
rerun passes. The native browser CI job budget is twenty minutes after cold browser
installation consumed 7m19s of its prior ten-minute limit; per-test limits remain.
Corrective push follows; deployed-origin proof and GitHub reruns are still pending.

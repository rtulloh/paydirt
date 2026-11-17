---
id: FLOW-033
title: Evaluate browser-only Paydirt using Pyodide/PyScript and WebAssembly
status: open
priority: Low
target-release: v1.10.7
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

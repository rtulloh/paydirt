---
id: FLOW-033
title: Evaluate browser-only Paydirt using Pyodide/PyScript and WebAssembly
status: open
priority: Low
target-release:
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

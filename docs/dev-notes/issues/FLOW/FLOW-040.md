---
id: FLOW-040
title: Pin native release runtime dependencies to the tested backend requirements
status: open
priority: High
target-release: v1.12.1
created-at: 2026-11-19
resolved-at:
closed-at:
tags:
  - packaging
  - regression
links:
commits:
---

## Description

Actual downloaded v1.12.0 native packages fail before registering the game API.
The application logs report `AttributeError: 'FastAPI' object has no attribute
'add_event_handler'` while installing the native library startup guard. Both Mac
architectures and both Windows package forms reproduced the same failure. Keep
that release/tag and its failed receipts immutable; qualify a new v1.12.1 repair.

The release build installed unbounded FastAPI, Pydantic and Uvicorn independently
of the backend requirements used by source qualification. The checked-in runtime
requires FastAPI 0.109.0, Pydantic 2.5.0 and Uvicorn 0.27.0. An independently
resolved package environment therefore did not match the tested runtime.

## Resolution / verification

- Install the backend requirements in every native matrix build, without separate
  unbounded overrides of its runtime packages. Run `python -m pip check` before
  building and preserve the resolved dependency list with the build artifacts.
- Demonstrate a workflow regression against the original recipe, retaining the
  exact-commit release gate, all five package forms and downloaded-native checks.
- Build and launch a local frozen candidate using the corrected dependency recipe
  before another publication. Complete full regression and exact-commit CI.
- After publishing the new immutable version, verify actual downloads on all five
  native targets. Keep first-launch security evidence separate from functional
  runtime checks. Close only after all required package proofs pass.

## Comments

--- 2026-11-19 19:57 ---
The new workflow dependency regression failed because the original recipe did not
install the backend runtime requirements; twenty-one existing and pin controls
passed. The narrow repair uses the checked-in requirements, checks installed
compatibility and retains a dependency freeze receipt. Native guard and game
rules remain unchanged. Local packaged acceptance, complete regression and new
published-package verification remain pending; this issue is not closed by the
workflow unit test alone.

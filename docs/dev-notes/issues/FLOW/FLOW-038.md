---
id: FLOW-038
title: Allow browser season simulations to refresh views between fixtures
status: closed
priority: High
target-release: v1.12.0
created-at: 2026-11-19
resolved-at: 2026-11-19
closed-at: 2026-11-19
tags:
  - bug
links:
commits:
---

## Description

During a real browser demonstration, simulating the first week saved a legal game then stopped with an action-already-in-progress error. Campaign view refreshes use a read-only POST but the worker transport classified every POST as a game mutation, so the refresh could block the next fixture. Previously committed finals stayed intact; the fourteen-game demo was completed by retrying only unplayed fixtures.

## Resolution / verification

- Test-first transport cases must allow read-only campaign views to coexist with simulation requests while continuing to reject concurrent game mutations. Confirm a real browser worker can simulate more than one fixture in a single UI batch, retain legal finals and complete team statistics, and restore the campaign after reload. Run applicable frontend and full release qualification.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 16:22 ---
Transport regression first failed in two expected cases, with six passing controls. The fix classifies only the exact campaign-view POST as a read-only query; the worker still processes requests serially, and concurrent actual game mutations remain rejected. Thirty-nine focused runtime cases pass, with gameFetch 89.92% line/86.36% branch coverage and all changed classification branches covered. A real browser-worker batch/reload regression and the full browser game suite are in progress. The screenshot demonstration completed all fourteen first-week games through rendered controls and verified all twenty-eight teams played exactly once; that deployed-version workaround is not acceptance of the fix.

--- 2026-11-19 16:32 ---
Verified the fix in the actual browser worker: a single rendered batch simulated two public-2026 fixtures, retained both legal finals, and preserved the exact campaign after a reload into a new worker. All six browser-only cases passed (90-team inventory, eight full games and the two-fixture batch), with no HTTP game backend. Runtime focused tests: 39 passed; gameFetch 89.92% lines/86.36% branches. The worker queue remains serial and true concurrent mutations remain rejected. Full release regression and exact-commit CI remain publication gates.

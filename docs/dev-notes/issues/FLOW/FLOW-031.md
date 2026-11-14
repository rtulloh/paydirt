---
id: FLOW-031
title: Hail Mary defensive timeout request raises while end-zone interception choice is pending
status: resolved
priority: High
target-release: v1.10.6
created-at: 2026-11-14
resolved-at: 2026-11-14
closed-at:
tags:
  - code-review
links:
commits:
---

## Description

Found in the 2026-11-14 review of the FLOW-028 Hail Mary deferral fix. run_play_with_penalty_procedure delegates special plays to run_play. The special-play wrapper only retains defensive-timeout context when the result has a pending penalty decision; a newly pending own-end-zone interception therefore reaches the defensive-timeout application path, whose pending-action guard raises ValueError. The interception remains unresolved instead of returning the pending outcome normally. Verified with run_play_with_penalty_procedure(HAIL_MARY, STANDARD, call_defensive_timeout=True): it raises with has_pending_end_zone_interception true.

## Resolution / verification

- Add failing-first public/synthetic regressions for a Hail Mary own-end-zone interception with a defensive-timeout request under the ask policy. Preserve the defensive-timeout context on the pending outcome, resolve the choice once, and verify the timeout is applied or skipped according to the existing engine policy without changing possession, score or clock before resolution. Run focused interception/timeout suites and update this ticket with evidence.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-14 17:05 ---
Fixed the special-play wrapper in `run_play_with_penalty_procedure`. When a Hail
Mary interception is deferred, the wrapper now retains the defensive-timeout
request on the pending outcome and in the engine's pending follow-up state
instead of applying it immediately through the pending-action guard.

Tests first: the two new Hail Mary cases (running-clock and out-of-bounds)
failed against the unchanged engine with the expected `ValueError`. They now
confirm the call returns the pending choice, game state and play log remain
unchanged, the timeout context is retained, and resolution completes once. A
save/load case verifies the request survives serialization and restoration.
The existing timeout policy conserves the timeout for the finalized turnover;
the test asserts the request remains available without claiming it is charged.
Focused interception/timeout/resume suites passed: 217 tests; Ruff passed. No
existing expectation was weakened. Full regression and browser E2E were not run
for this ticket.

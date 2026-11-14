---
id: FLOW-030
title: Guard every game-changing action while an end-zone interception choice is pending
status: resolved
priority: High
target-release: v1.10.6
created-at: 2026-11-14
resolved-at: 2026-11-14
closed-at:
tags:
links:
  - FLOW-026
commits:
---

## Description

Code review of FLOW-026 found that the initial guard covered only run_play, run_play_with_penalty_procedure, /api/game/execute, and the main play controls. kickoff, onside kick, safety free kick, extra point, two point, defensive timeout, overtime start, and the scrimmage, punt, kickoff and field-goal penalty decisions could still run while has_pending_end_zone_interception was true. The matching web routes had no 409 guard, and the browser could still expose kickoff, try, timeout, punt, CPU-decision and penalty controls. FLOW-027 shows that try and kickoff steps can follow these interceptions, so the gap is reachable. The deferred interception has not changed possession, statistics or the clock; starting another action first records it out of order and lets resolution apply from a stale spot.

## Resolution / verification

- Make every public engine action that changes game state reject while the end-zone return choice is pending, before play-start bookkeeping or dice; keep apply_end_zone_interception_return_decision as the only resolution path and clear the flag before follow-ups.
- Return HTTP 409 before mutation or route bookkeeping from the matching web action routes: execute, kickoff including safety free kick, extra point, two point, timeout, overtime start and penalty decision.
- Withdraw or disable kickoff, try, timeout, punt, CPU-decision and penalty controls while the choice is open, and guard their handlers plus the CPU fourth-down effect.
- Add synthetic/public-2026 regressions for every engine action and route, asserting unchanged state, play log, call history and route flags; add frontend tests for the kickoff, try, timeout and save controls.
- Update docs/development.md and FLOW-026 verification, record baseline test failures, and complete a play-test or e2e audit before closing.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-14 14:58 ---
Code review follow-up from FLOW-026. The working tree now expands the guard to
`kickoff`, `onside_kick`, `safety_free_kick`, `attempt_extra_point`,
`attempt_two_point`, `apply_defensive_timeout`, `start_overtime`, and the
scrimmage, punt, kickoff and field-goal penalty decisions. The matching action
routes return 409 before mutation, and the browser withdraws or guards the
kickoff, try, timeout, punt, CPU-decision and penalty controls. Tests were added
in `tests/test_end_zone_interception_decision.py`,
`paydirt-web/backend/tests/test_end_zone_interception_policy.py`, and the new
`paydirt-web/frontend/src/components/Game/PlayingPhaseEndZoneGuard.test.jsx`.
Focused runs passed: 43 core tests, 19 backend tests, 24 frontend guard/panel
tests, and the documentation check. Baseline failures were observed before the
fixes. Nothing is committed yet. A play-test or e2e audit remains required
before this ticket can close.

--- 2026-11-14 15:15 ---
Owner reports the regression passed. The fix, tests, documentation and both
linked tickets are committed together in v1.10.6. This ticket is resolved
awaiting the play-test audit; no test expectation was weakened or skipped.

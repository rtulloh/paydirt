---
id: FLOW-026
title: A new play can execute while an own-end-zone interception return decision is pending
status: resolved
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at: 2026-11-14
closed-at:
tags:
links:
  - FLOW-023
  - FLOW-030
commits:
---

## Description

Found in the 2026-11-13 review of cedf6117..HEAD. Only `_apply_play_result` defers an own-end-zone interception (paydirt/game_engine.py, the INTERCEPTION branch). While that choice is pending, nothing else rejects a snap: `run_play_with_penalty_procedure` checks only `state.game_over`, the web `execute_play` route has no pending-decision guard, and the frontend can offer a play. Reachable in the browser: the frontend clears `localExecuting` when it receives `pending_end_zone_interception_return_decision` (paydirt-web/frontend/src/components/Game/PlayingPhase.jsx, the executePlay response branch), but the CPU fourth-down effect in the same component does not check `localShowEndZoneChoice`, so a CPU fourth-down interception can surface the CPU punt/field-goal panel. Executing it records a second play while the interception is unresolved; resolving the interception afterwards then changes possession from the stale pre-interception state, corrupting play chronology and statistics. Reproduced with the public 2026 sample teams by deferring an end-zone interception, executing a three-yard pass, then resolving the original interception.

## Resolution / verification

- Add a failing synthetic regression (public 2026 sample teams) showing the engine rejects a snap while has_pending_end_zone_interception is true, and a backend test that the execute route returns an explicit conflict instead of resolving a new play.
- Make the frontend fourth-down effect and defense selection respect the pending end-zone state so no play control is offered before the choice is resolved.
- Verify in a browser play test that a CPU fourth-down end-zone interception cannot be followed by another snap, and record the result in the ticket.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-14 17:20 ---
Fixed in the engine, API and browser UI.

Engine: `_reject_pending_end_zone_snap()` refuses `run_play`,
`run_play_with_penalty_procedure`, `kickoff`, `onside_kick`,
`safety_free_kick`, `attempt_extra_point`, `attempt_two_point`,
`apply_defensive_timeout`, `start_overtime`, and the scrimmage, punt, kickoff
and field-goal penalty decisions while `has_pending_end_zone_interception` is
true. The guards run before play-start bookkeeping or dice, so no play,
statistic, clock charge or log entry can precede the choice. The guard is cleared
only when `apply_end_zone_interception_return_decision` resolves the deferred
play; that method then applies its saved timeout/spike follow-ups from the
original stored state.

API: the action routes for execute, kickoff (including safety free kicks),
extra point, two point, timeout, overtime start and penalty decision return HTTP
409 with an explicit pending-choice detail before touching engine state or route
bookkeeping such as `is_kickoff`, `safety_free_kick` or `pending_pat`.

Browser: the CPU fourth-down effect returns early while `localShowEndZoneChoice`
is set (and lists it as a dependency), `executePlay`, `handleOffensePlay` and
`handleDefensePlay` ignore clicks while the panel is open, the kickoff banner and
PAT/two-point panel are withdrawn, and kickoff, try, punt-options, CPU-PAT and
timeout handlers also refuse to start. CPU-decision, punt-options, PAT and
penalty panels are withdrawn, and save replay/save game remain disabled with
their handlers guarded. No coaching query, kick panel or submitted play starts
before the choice.

Tests first: the new core test failed with `DID NOT RAISE` (a second snap
executed and appended to the log), the backend test failed with 200 instead of
409, and the new
`PlayingPhaseEndZoneGuard.test.jsx` failed with two fourth-down decision requests
(one issued after the panel appeared) and with kickoff/try controls remaining
visible over the choice. All pass with the change. The engine table test covers
each public action and asserts unchanged state, log and call history; the backend
table test covers each action route and asserts the 409 leaves state, log and
game flags untouched. The original guard test still confirms the next snap works
after resolution.

The new backend table test initially failed with 200 for kickoff, safety free
kick, extra point, two point, timeout and overtime start, and 400 for penalty
decision; the new frontend control tests initially failed because the kickoff and
PAT panels stayed mounted. Those are the baseline failures for the expanded
scope. Existing tests were not weakened.

Evidence: core focused suites 512 passed (end-zone decision/returns, untimed
downs, penalty procedure, spike/timeout priority, computer AI, AI-002 defence,
flagged timing); backend 454 passed with the one pre-existing
`test_frozen_launcher` environment failure; frontend Game components 185 passed
with the same 12 pre-existing local `localStorage` environment failures; both
complete real-engine browser games passed (4.3m, isolated ports 18012/15185).

No existing test expectation was weakened. `docs/development.md` records the
pending-outcome guard. Closure needs the owner's next play-test audit of the
resolved-panel flow.

--- 2026-11-14 15:00 ---
The code-review expansion beyond the first play/execute guard is tracked as
[FLOW-030](FLOW-030.md): every game-changing engine action, matching web route,
and kickoff/try/timeout/penalty browser control is now covered by the pending
choice, with its own regression tests and closure evidence. Nothing is committed
yet; FLOW-030 remains open pending the play-test or e2e audit.

---
id: FLOW-026
title: A new play can execute while an own-end-zone interception return decision is pending
status: open
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at:
closed-at:
tags:
links:
  - FLOW-023
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

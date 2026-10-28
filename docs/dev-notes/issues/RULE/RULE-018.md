---
id: RULE-018
title: Return-chain fumbles in or beyond an end zone are clamped to the 1 with no touchdown, touchback or safety
status: open
priority: High
created-at: 2026-10-27
resolved-at:
closed-at:
tags:
  - reproduced
links:
  - RULE-014
commits:
---

## Description

The fumble branch of `_resolve_return_chain` computes `spot = max(1, min(99, start + yards))` (`paydirt/game_engine.py:816`) and never consults `end_rule`, which only the non-fumble branch applies (`:849-850`). Synthetic reproductions with public fixtures: a kickoff caught 9 yards deep with return cell `F + 3` ends with the returner's team at **its own 1** when it recovers (roll 20) and with the kicking team holding the ball at the opponent's 1 with **no touchdown** when it recovers (roll 30); the same kick with a plain `5` cell is a touchback. An interception at the defender's 3 with cell `F -5` is clamped to the 1 (returner) or to the opponent's 1 with no touchdown (original offense) while the plain `-5` cell correctly yields a touchback. The description also places the fumble "at AWAY 1" although it occurred in the end zone. No test covers end-zone return fumbles.

## Resolution / verification

- Failing regressions for kickoff, punt (once migrated), interception and fumble-advance returns fumbling inside or beyond either end zone, for each recovering side: touchback/safety/touchdown per the rulebook, correct description, recovery roll preserved in the trace.
- Apply the same end-zone rule to the fumble branch as to the yardage branch; do not clamp live-ball spots to the field.

## Comments

--- 2026-10-27 18:00 ---
Found during the Bowl Bound 2026-10-27 full review cross-check; reproduced in Paydirt with public 2026 sample fixtures and synthetic chart cells only. No private charts or logs were used.

--- 2026-10-27 22:23 ---
Shared-resolver fix implemented locally, not committed or pushed. Test-first
baseline: 136 expected failures, two field-recovery controls passing. Raw
end-zone spots were incorrectly clamped to 1/99 and 17/37 could start another
return from that fabricated spot. Retain the raw spot until recovery, apply
the original kick/interception touchback rule only for a retained recovery,
stop end-zone recovery chains, and preserve beyond-end-line white-dice depth
in the trace (recovery roll first, consistent with the scrimmage procedure).
Merge nested touchback flags and propagate safety scoring/outcome flags through
scrimmage, kickoff, blocked punt/FG, and fumbled-snap returns. Additional
test-first checks caught two nested-safety flag failures (144 controls passing),
then five blocked-kick/snap safety flag failures (146 controls passing).
All 151 new cases now pass; no existing test expectations changed or skips added.
597 focused cases passed before the final roll-order cleanup; full post-cleanup
core 5,814 passed / eight existing skips, backend 218 / existing Pydantic warnings,
Ruff, offline guide browser check, standalone games, historical 12/12, generated
224/224 (14 OT, five valid ties), and playoffs 9/9 (no ties) passed. Public/local
AI audits: 32/32 and 448/448; totals reconcile, no Hard concentration warning.
Player guidance updated. Keep open while uncommitted and while the ordinary
punt-return branch still bypasses this resolver (RULE-019). Issue-specific
full-game confirmation is still needed for eventual closure.

Follow-up observation: a chain with two possession changes can return the ball
to the original offense at its own 20 (touchback) yet retain its original series
in the outer fumble handler. The new nested test verifies spot, recovery trace,
scoring and lost-fumble stats, not that series-reset behavior. Track separately
from this end-zone-location fix; do not assume ordinary own-recovery down logic
is sufficient after intervening possession changes.

--- 2026-10-27 22:24 ---
Shared-resolver implementation, 151 new regression cases, and player guidance
are included in the current local fix commit. Keep open until RULE-019 adds
ordinary punt-return integration and its regression coverage. Nothing pushed.

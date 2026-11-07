---
id: RULE-028
title: Returner fouls can exceed half the distance and overstate assessed yardage
status: closed
priority: High
created-at: 2026-11-06
resolved-at: 2026-11-06
closed-at: 2026-11-06
tags:
  - reproduced
  - chart-audit
links:
  - RULE-027
---

## Description

The shared returner's-foul helper reduces a penalty only when it would cross
the goal line. A fifteen-yard foul at the 27 therefore moves to the 12 instead
of the 14. At the one it charges a penalty yard without physical movement.
Kickoff, punt, interception and fumble returns share this helper. The new
five-versus-fifteen enforcement exposes this independently in two complete
development games; that exception's earlier coordinate/metadata fix alone
does not correct the half-distance bug.

## Resolution / verification

Write synthetic/public boundary and passing controls first. Respect the
original rule VI-4-C-ii and rounding toward midfield (VI-4-C-vii), preserve
nominal foul size independently of effective assessed yards, retain possession,
score/fumble decisions and period rights, and verify current full-game receipts.
Record every existing expectation corrected for over-assessment. Do not close
from unit tests alone.

## Comments

--- 2026-11-06 03:03 ---
The baseline has 24 expected failures and 602 passing new/existing controls.
Boundary checks cover both actual directions, odd/even distances, five/fifteen/
forty-yard fouls, the one-yard line and touchdown controls. The shared helper
now caps the assessment at half the offender's distance. The first affected
return suite exposes 17 existing expectation failures, with 1,041 passing.
The old fixtures had demanded fifteen yards from the 21, 22 or 23. Corrected
positions are respectively 11, 11 and 12, with actual assessments 10 or 11;
the accepted/recovery/turnover assertions remain in place. A separate gate
mutant first passes incorrectly, motivating a stronger catch-at-the-27 control.
Full-game confirmation is being refreshed; keep this issue open.

--- 2026-11-06 03:06 ---
Fresh full-game review at runtime 52d48a1f… completes all 224/272 games and
confirms both naturally exposed catch spots. The receiver's 27 becomes 14
with 13 yards assessed; the 26 becomes 13 with 13 assessed. Both have exactly
one actual-team penalty and correct possession/down, with no retained canceled
return. There are no remaining findings in the scoped exception checks.

All 1,059 affected return checks pass, including the strengthened gate mutant.
One backend preview expectation also encoded the old seven-yard spot after a
return ending at 22; it now asserts the exact core preview at the 11. The
recovery/possession assertions remain. Backend passes 322 with 21 existing
Pydantic warnings; documentation/tracker checks pass 333. The complete core
checkpoint is active, so final regression is not yet claimed.

--- 2026-11-06 03:19 ---
The first complete core checkpoint reports 8,768 passed, eight failed and eight
existing data-dependent skips. All eight failures are prior full-distance
expectations, now independently reconciled: a return ending at 25 moves to 13
with 12 assessed (two home/away kickoff controls); the kickoff-fumble CLI preview
and acceptance from 22 move to 11; a punt return ending at 29 assesses 14 rather
than 15 (two possession sides); the two combined box-score controls consequently
reduce the away total from 110 to 109, including its display assertion. No
possession, recovery, scoring or accounting identity assertion is removed.
All 196 affected checks pass after those corrections. The refreshed full core
checkpoint remains active. Local integration passes 14/14 standalone games,
16/16 retained historical games, 224/224 generated regular-season games and all
nine playoffs. A separately verified supplement preserves the two mandatory
actual untimed downs; see the historical seed-drift note. Keep open until the
complete core checkpoint is recorded.

--- 2026-11-06 03:34 ---
The complete current `f0cfc25a…` core checkpoint passes 8,873 tests with eight
existing data-dependent skips and 83% coverage. Current full-game review05
again confirms the natural 27-to-14 and 26-to-13 assessments, with correct
actual-team penalty totals and fresh series. All 496 development games finish;
the separate 14-game, sixteen historical, 224-game generated season and nine
playoff checks pass. The two frozen mandatory untimed-down reproductions each
award and consume the extra down. Close on this issue-specific play-test evidence,
not unit results alone. The fix and evidence remain local and uncommitted;
closure grants no commit, publication or release approval. RULE-027 retains its
separate legacy-policy scope.

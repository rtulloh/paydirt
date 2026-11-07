---
id: STAT-003
title: Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception…
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - reproduced
links:
  - RULE-001
  - STAT-001
  - FLOW-018
---

## Description

Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception counts).

## Resolution / verification

Fixed by RULE-001; add accounting assertions to its regressions. STAT-001 remains separately open.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (reproduced)).

--- 2026-10-20 17:35 ---
Priority changed from High to Medium with RULE-001: this accounting defect is limited to two-point conversion attempts, which are not a current product priority. Keep its assertions with the eventual RULE-001 fix.

--- 2026-11-06 14:20 ---
Uncommitted test-first repair and validation are in progress. See
[conversion completion evidence](../../two-point-conversion-completion.md) for
expected RED controls, implementation boundaries, and the disclosed retained-
fumble test expectation change. Keep open until the scoped fix is committed;
closure additionally needs actual engine/API/browser play-test evidence.

--- 2026-11-06 14:35 ---
Actual chart regressions snapshot all ordinary state fields and preserve the
live statistics objects across successful, failed, intercepted and fumbled
tries. API and compiled-browser cases additionally confirm zero ordinary
statistics/log/call-history changes, including Q4 0:00. The former conversion
log expectation is explicitly corrected and disclosed in the completion note;
the retained-incompletion resolver subtype assertions remain. Keep open pending
the scoped commit; mandatory chart source gates remain failed prerequisites.

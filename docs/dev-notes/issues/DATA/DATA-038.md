---
id: DATA-038
title: Aborted field-goal labels omit snap fumbles and distinct statistical actors
status: open
priority: High
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - source-coverage
links:
  - DATA-030
  - DATA-036
---

## Description

Four historical source rows labeled as unsuccessful field goals are reviewed
bad snaps without a kick. The previous attempt/box reconciliation retained four
unknown-mechanism conflicts but consumed these rows before the fumble inventory.
The complete source census therefore omitted four snap origins. Three reviewed
zero-yard rushing credits belong to recovering players rather than the centers
who fumbled. One individual credited gain remains unknown; physical movement
remains unknown in all four. A halftime attribution was corrected in the final
official table, demonstrating why final field-specific review is required.

## Resolution / verification

The generic schema-4 reviewed fact path preserves these no-kick events, separate
actors and nullable gains. It clears the explained attempt-label conflicts
without changing official attempt targets. Every snap retains an explicit
unsupported projection entry: the current engine field-goal F path forces an
opponent recovery and does not model arbitrary snap credit/movement. Do not map
own recoveries to that cell or silently resample these as designed rushing plays.
Keep open until a reviewed projection and fresh complete-source/candidate
qualification demonstrate the remaining model behavior.

## Comments

--- 2026-11-06 13:55 ---
Seven capability failures, one missing-secondary-team metadata failure and one
receipt-denominator failure precede implementation. Public/synthetic controls
also preserve actual kick attempts and reject contradictory facts, stale source
identity, unsupported classes and nullified actions. The expanded focused source
run passes 478 tests; no assertions or skips are weakened. The first corrected
224-game census contains 727 events: 494 projected, 233 unsupported, zero
unexplained field-goal conflicts. It includes two separately tested directional
scramble grammar corrections. These are source-development counts, not complete
source acceptance, final chart fit or play-test evidence. Ignored receipts remain
under `gsis-1983-reconciliation/recovery-source-01/` and census revision 04.

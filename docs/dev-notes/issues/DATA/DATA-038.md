---
id: DATA-038
title: Aborted field-goal labels omit snap fumbles and distinct statistical actors
status: open
priority: Low
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

The reviewed fact path preserves these no-kick events, separate statistical
actors and nullable gains without changing official field-goal attempt targets.
Subsequent implementation supports three reviewed zero-credit aborted-field-goal
plays, preserving recovery ownership, consuming a rushing snap and recording no
field-goal attempt. The original all-four-unsupported limitation below is
superseded by that implementation.

One reviewed Chicago aborted field goal still has unknown individual credited
yardage and remains explicitly excluded rather than assigned an invented gain.
This narrow source-data gap is optional future work, not a release blocker. Its
impact on aggregate simulation outcomes has not been measured; the user accepts
the remaining omission as negligible for current gameplay and it may remain
unaddressed indefinitely. Keep open at Low priority to retain the limitation and
its provenance; no gameplay or source-projection change is authorized here.

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

--- 2026-11-08 17:06 ---
Lowered High to Low at the user's request. Three of the four reviewed aborted
field-goal cases gained support after this ticket was written; only the unknown-
credit Chicago event remains excluded. The user considers this residual gap
negligible for the game and accepts that it may never be addressed. Updated the
current resolution description while retaining the original investigation below.

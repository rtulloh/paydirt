---
id: DATA-016
title: Sparse empirical event allocation can choose a worse physical probability
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - chart-audit
---

## Description

A final empirical column can omit a 0.5% interception target even though an
available mass-2 row is closer to its target of 1.08/216 than zero mass. The
selector rounds requested mass before searching subsets. This is a small real
quantization defect, separate from BB's large finite-row allocation jump.

Reproduction and independent final-output checks are in
[the allocation audit](../../generated-event-allocation-audit.md). The automated
allocation gate rejects three sparse contexts, one per deterministic seed.
Production generator and published chart data remain unchanged.

## Resolution / verification

Add a failing generator regression using synthetic mixed outcomes, preserve
already allocated event types, and select the closest attainable mass against
the unrounded target. Cover ties, saturation and minimum-one repair separately.
Rerun generator/source regeneration and the complete generated-chart release
gate; do not weaken the independent probability oracle.

## Comments

--- 2026-11-05 16:35 ---
Opened from the user-requested generated-chart accuracy and release-gate audit.
The gate records the defect; no production/chart-data correction or push occurred.

--- 2026-11-05 18:42 ---
Test-first correction implemented locally under the chart-confidence charter.
Combined new regressions: 20 expected baseline failures, 17 passing controls;
438 focused tests now pass, including recovery/penalty and allocator mutants.
See [implementation evidence](../../chart-confidence-implementation.md).
Keep open pending regenerated candidate, required full-game/audit evidence and review.

--- 2026-11-05 20:30 ---
Further finite-row controls expose separate QT/QT* rounding and avoidable variant
loss. They now share one selected pressure mass, and equal-mass choices reserve
rows. The sparse 5/1000 fixture now has a closer 1/216 row available; its former
2/216 result was conditional on earlier allocation consuming that row. The
isolated mass-2-only oracle remains unchanged. Source foul-variant preservation
is strengthened; unrepresented rare variants are disclosed, never forced.
Final play/audit verification remains pending.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Unrounded-target finite-mass selection and QT/QT* allocation controls are committed; final regenerated play/audit confirmation remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

---
id: RULE-026
title: Selected offensive fumble priority is misclassified as defensive interception
status: open
priority: High
created-at: 2026-11-05
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-audit
---

## Description

apply_priority_chart("F + 2", "INT 5") selects a two-yard offensive fumble,
but resolve_play_with_penalties can classify the play as INTERCEPTION because
its result-type branch searches either raw input for INT instead of respecting
the selected priority result. Its description can still say FUMBLE. This is a
reachable collision between valid offense fumble and defense interception
cells, affecting turnover/recovery semantics and calibration measurements.

The generated-defense audit adds a gate check for the mismatch, separate from
CSV uniqueness or BB's zero-profile issue. Production resolver remains unchanged.

## Resolution / verification

Write direct synthetic priority/resolver and full-engine regressions before the
core fix. Preserve fumble recovery choices, own/lost recovery and penalty reroll
controls, and test offensive/defensive symbol priority collisions. Classify
from selected priority semantics, then rerun the generated-chart gate and all
required rule/full-game/AI regression checks. No chart retuning can substitute
for correcting outcome classification.

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

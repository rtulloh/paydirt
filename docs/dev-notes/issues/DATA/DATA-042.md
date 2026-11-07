---
id: DATA-042
title: Updated season simulations still inflate scoring and offensive play counts
status: open
priority: Medium
created-at: 2026-11-07
resolved-at:
closed-at:
tags:
  - investigating
  - season-audit
links:
  - DATA-018
  - AI-030
---

## Description

The updated 2024 candidate completed 256 seasons and 72,960 games. Aggregate
scoring is 25.60 points per team/game versus 22.91 historically, despite improving
from 28.12 with the old charts. Offensive play counts are approximately 7.2%
above the normalized source count. The analysis does not establish whether pace,
possessions, field position, turnovers, special teams or accounting causes the gap.

Kansas City's allowed rushing/passing YPA nearly match their source targets,
while allowed scoring remains above historical scoring. Its lower simulated
playoff rate alone is not evidence of an engine defect or grounds for team tuning.
Historical outcomes are diagnostics, not required results.

## Resolution / verification

Reconcile play/possession denominators first. Measure drives, plays per drive,
clock use, starting field position, scoring opportunities and scoring efficiency
under a frozen runtime/chart/policy identity. Separate chart effects from the
1983 campaign's concurrent typed-field-goal runtime changes. Add synthetic/public
regressions before fixing any demonstrated defect. Verify a fix through paired
season diagnostics without forcing historical standings or weakening fit bounds.

## Comments

--- 2026-11-07 15:53 ---
Opened from the completed release investigation. Ignored evidence is under
`.ai-audits/season-frequencies-updated-20261107/analysis.md` and its reconciled
aggregate JSON/CSV files. The updated 1983 campaign is recorded separately under
`.ai-audits/season-frequencies-1983-modeled-20261107/`. No causal fix is established.

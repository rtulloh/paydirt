---
id: DATA-020
title: Calibration observer credits nullified offsetting-penalty plays
status: closed
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at: 2026-11-08
tags:
  - reproduced
  - regression-test
links:
  - DATA-031
---

## Description

After correcting QT-fumble classification, the full generated-cohort replay
still had offensive-play counts exceeding pass attempts + rush attempts + core
sacks by 32 events in 1983 and 24 in 2024. First mismatches in both seasons were
nullified offsetting penalties, not safeties. Core replays the down and records
no play/sack, but its final outcome retains a provisional result with:

- penalty_choice.offsetting=True
- penalty_applied=False
- result.replay_down=False

The observer checked only the latter two flags, credited the provisional play,
and biased calibration rates. Voided numeric passes/runs can preserve the count
identity while still biasing the report. The actual core outcome is already
available; no description parsing or core rule change is needed.

## Resolution / verification

Skip authoritative offsetting choices before crediting any measurement counter.
Synthetic core and observer regressions cover ordinary completions, runs, sacks
and QT fumbles, with retained and other replay controls. The release measurement
gate now checks all four no-play branches in addition to its QT controls.
Do not relax denominator invariants. Rerun complete source-schedule evidence
with a fresh fingerprint after the observer-only correction. Keep open while
uncommitted; previous sampled metrics remain provisional until renewed.

## Comments

--- 2026-11-05 16:49 ---
Opened from the audit's strict per-team/league count reconciliation. Source,
allocation and priority findings remain independent. See the
[combined audit](../../generated-chart-release-audit.md) and
[cross-project note](../../college-chart-tactics-cross-project-findings.md).

--- 2026-11-05 16:52 ---
Observer-only fix is verified and frozen. Baseline had six expected failures
and twenty-nine passing controls; focused tests then pass. The exact previously
mismatched generated games (seeds 21328712 and 31476026) each now have zero
count mismatches. Full-core synthetic cases verify voided numeric pass/run,
sack and QT fumble contribute no official counts or yardage; retained declined
completion remains credited. The full 64-schedule evidence is being renewed.
Keep open while the code is uncommitted.

--- 2026-11-05 16:54 ---
Final renewed evidence completed 31,744 full games across both public generated
cohorts. Eight stateful observer controls and every per-team/league play identity
pass with the corrected measurement code. Chart accuracy/source/priority blockers
remain separate. This fix is verified but uncommitted; keep open.

--- 2026-11-08 16:36 ---
Completed-work reconciliation: The offsetting-penalty observer exclusion shipped in 8c0bb8b. November 5 exact previously failing game replays and the renewed 31,744-game campaign confirm reconciled accounting. Current real-engine/observer regressions pass. Broader nullified fumble-return handling remains under DATA-031.

The earlier keep-open/uncommitted wording records its original checkpoint;
it is superseded by this closure. See the [full review](../../open-issue-reconciliation-2026-11-08.md)
and [published verification](../../release-1.10.2-scope.md#published-release-verification).
Closure uses the recorded issue-specific gameplay/integration evidence plus
committed-source review, not unit tests alone. No new full regression was run.

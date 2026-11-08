---
id: DATA-019
title: Calibration observer counts QT fumbles as completed passes instead of sacks or rushing
status: closed
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at: 2026-11-08
tags:
  - reproduced
  - regression-test
links:
  - DATA-018
---

## Description

Release-gate review found that EngineCalibrationObserver classified every fumble
on a selected pass as a pass attempt and completion. The authoritative engine
records QT fumbles at/behind the line as sacks and positive QT fumbles as rushing.
This double-counted negative QT fumbles in sack/pass denominators and labeled
positive ones completed passes, biasing calibration metrics. Ordinary completed
pass fumbles must keep their pass category.

## Resolution / verification

The locally implemented observer correction uses original QT-fumble loss yards
for sack classification, preserving recovery advance semantics. Negative ordinary
QB scrambles follow the final credited gain as the core does. Fourteen synthetic
cases compare observer counters with authoritative core box handling. Baseline:
six expected failures and thirteen passing controls; focused checks then pass.
No core gameplay rule or chart data changed. Keep open while uncommitted.

The automated gate also compares four controlled real-engine events with the
observer and rejects corrupted measurement. Report validation enforces each
team's and league's offensive_plays = pass_attempts + rushing_attempts + sacks,
plus completion/interception count bounds. Engine fingerprints invalidate the
older evidence; final full-cohort calibration must be regenerated after the fix.

## Comments

--- 2026-11-05 16:42 ---
Opened from independent release-gate review. The correction is verified locally
but uncommitted. Earlier November 5 calibration values are provisional and are
being replaced by a complete corrected-observer run. See the
[combined audit](../../generated-chart-release-audit.md).

--- 2026-11-05 16:54 ---
Final renewed evidence completed 31,744 full games across both public generated
cohorts. Eight stateful observer controls and every per-team/league play identity
pass with the corrected measurement code. Chart accuracy/source/priority blockers
remain separate. This fix is verified but uncommitted; keep open.

--- 2026-11-08 16:36 ---
Completed-work reconciliation: The corrected QT-fumble observer shipped in 8c0bb8b. The November 5 renewed 31,744-game campaign reconciled every team/league play identity with the corrected counters. Current observer tests pass. This closes the measurement classification defect, not historical chart-fit or source-model acceptance.

The earlier keep-open/uncommitted wording records its original checkpoint;
it is superseded by this closure. See the [full review](../../open-issue-reconciliation-2026-11-08.md)
and [published verification](../../release-1.10.2-scope.md#published-release-verification).
Closure uses the recorded issue-specific gameplay/integration evidence plus
committed-source review, not unit tests alone. No new full regression was run.

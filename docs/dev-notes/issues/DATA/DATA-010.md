---
id: DATA-010
title: Generated breakaway triggers and B yardage are not reconstructed from play by play
status: closed
priority: Medium
created-at: 2026-11-01
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - chart-generator
  - play-by-play
  - calibration
links:
  - DATA-006
  - DATA-009
  - DATA-011
---

## Description

Play-by-play generation currently preserves every observed rushing gain as a numeric result.
That avoids converting a long run into a field-independent touchdown, but it leaves the
Paydirt two-stage breakaway mechanism unused in empirical run columns. The separate `B` chart
is still estimated from aggregate rushing efficiency rather than the observed distribution of
long runs.

The generator should separate ordinary long gains from exceptional breakaways. Direct run
results may extend through the longest value observed in the developer charts, while more
extreme gains determine `B` trigger frequency. The B column should use the broader observed
long-run distribution because the engine uses its result as the complete play yardage.
Out-of-bounds and fumble semantics must be preserved.

## Resolution / verification

Compare candidate fixed and data-derived thresholds against the developer-based 1983 charts,
including dice-weighted B trigger mass and B-column yardage distribution. Add synthetic tests for
threshold boundaries, no double counting, out-of-bounds markers, and fumbles. Regenerate 1983 and
2024, then repeat engine calibration and multi-season standings/playoff assessment before
selecting a model.

## Comments

--- 2026-11-01 22:12 ---
Recorded during DATA-009 validation. The current 256-season touchdown-fix assessment intentionally
retains the existing B behavior so its before/after result isolates field-position-aware scoring.

--- 2026-11-01 22:18 ---
The developer-based 1983 charts confirm the structural split. Maximum direct numeric results are
13 yards for Line Plunge, 10 for Off Tackle, 18 for End Run, and 9 for Draw, while the B column
reaches 85 yards. The current generated charts instead reach 55, 49, 59, and 17 yards directly,
with a B-column maximum of only 43. This is strong evidence that empirical explosive gains should
move from primary run columns into B trigger mass and the conditional Breakaway distribution.

--- 2026-11-01 23:08 ---
A synthetic boundary regression demonstrated that the initial 10-yard trigger was too broad.
The revised generator leaves gains through 18 yards direct, converts gains of 19 yards or more
to `B`, and builds the B result chart from every observed gain of at least 10 yards. On the 1983
set, average B cells are now 1.11 Line Plunge, 1.46 Off Tackle, and 1.39 End Run, compared with
1.79, 2.82, and 3.54 direct 10-plus-yard cells in the previous generated charts. The corrected
primary columns have no result above 18 yards.

--- 2026-11-01 23:31 ---
A second boundary regression found that an aggregate fallback column could still emit a direct
19-yard gain even when empirical columns were correct. Aggregate run generation now applies the
same 18-yard direct cap. Regenerated 1983 and 2024 charts have no direct numeric run result above
18 yards.

--- 2026-11-02 10:50 ---
Prepared for commit with the documented source/profile regeneration, test-first
regressions and full-game evidence. The November 2 completed manual audit
confirms the relevant generated-chart mechanisms: no field-independent run
TDs, ordinary breakaway resolution, no concentrated interception recurrence,
and both kick and return fouls. Close this specific transformation/coverage
issue on that evidence; statistical fit and coaching limitations remain
documented. The new engine timing changes do not establish a fresh 64/256-season
fit; DATA-011 explicitly distinguishes the earlier fitting evidence.

---
id: DATA-009
title: Play-by-play rushing scores become field-independent touchdown chart results
status: closed
priority: High
created-at: 2026-11-01
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - reproduced
  - play-test
links:
  - DATA-007
  - DATA-010
  - DATA-011
---

## Description

A manual game using the generated 1983 Cowboys against the generated Eagles exposed
three Dallas offensive chart touchdowns in 34 calls by early Q3: End Run roll 17
scored from 73 yards, and Line Plunge roll 15 scored from both 44 and 60 yards. Dallas's
other touchdown was a defensive interception return.

The result is not only game variance. Both play-by-play adapters replace every scoring
rush or completed pass with the literal `TD` result. That discards observed yardage and
the original field position. A short goal-line score therefore becomes an automatic
touchdown from any point on the field when quantized onto an offense chart.

Dallas's generated Line Plunge has two touchdown rows with 5.093% dice mass, and its
End Run has two with 3.241%. Across the generated 1983 set, Line Plunge, Off Tackle,
and End Run average 3.009%, 2.827%, and 2.877% touchdown mass. Every generated team has
rushing touchdown mass. The local developer-based 1983 charts have no rushing `TD`
result in any of those four columns for all 28 teams; their explicit touchdown mass is
concentrated mainly in Long Pass at a 1.687% league average. The generated 2024 charts
show the same field-position loss.

## Resolution / verification

Preserve observed rushing yardage for scoring runs and let the engine determine whether that gain
reaches the goal line from the current field position. Preserve the developer-chart conventions
for the other scoring families: completed-pass touchdowns and interception-return pick-sixes use
literal `TD`, while kickoff and punt return scores use numeric yardage. Add failing synthetic
classifications for each convention in both PFR and nflverse adapters. Regenerate 1983 and 2024,
compare dice-weighted touchdown and explosive-yard mass against the developer-based 1983 charts
and source play lengths, then repeat multi-seed engine assessment. Confirm with a manual game
before closing and before publishing the generated seasons.

## Comments

--- 2026-11-01 21:40 ---
Recorded from `/tmp/pd.log` during the pre-push manual play test. Two Line Plunge
roll-15 results in four Dallas Line Plunge calls are individually unlikely (0.446%
for at least two roll-15 results), but the repeated roll only made the underlying
field-position encoding defect obvious. No generator or chart files were changed while
the game was in progress.
--- 2026-11-01 22:05 ---
Added failing synthetic PFR and nflverse regressions showing that a two-yard rushing
touchdown and a 35-yard completed-pass touchdown were classified as literal `TD` results.
Both adapters now preserve observed scrimmage yardage while the return-touchdown controls remain
symbolic. A generator-level failing regression then exposed aggregate `TD` cells in the
`T/E S/L` fallback. Empirical generation now builds that column from observed short, medium,
and long pass outcomes and applies the ordinary pass-event calibration. Focused coverage passes
43 tests. Regenerated 1983 and 2024 contain zero literal scrimmage `TD` cells across 60 teams.
The ticket remains open for multi-season simulation results and a fresh manual play test.


--- 2026-11-01 23:35 ---
Audited all 28 developer-created special-teams charts and the offensive result columns. Run and
Breakaway columns contain no `TD`. Pass columns contain 27 `TD` cells. Kickoff Return and Punt
Return contain no `TD` or `B`; Interception Return contains 17 `TD` cells and no `B`. Updated both
source adapters and failing regressions to use numeric rushing/kickoff/punt results, literal pass
TDs, and literal pick-sixes. Numeric interception returns remain eligible to score through normal
engine field-position resolution.

--- 2026-11-01 23:58 ---
A deeper audit supersedes the provisional direct pass-TD and pick-six mapping noted above.
Developer pass columns contain very large numeric gains alongside only 27 literal `TD` cells, and
the lone Colts Short Pass `TD` is not explained by the highest inferred short-pass touchdown rate.
Both adapters now preserve numeric yardage for every scoring play. DATA-011 will add sparse
symbolic touchdown mass as a reproducible second-pass engine calibration rather than source
classification.

--- 2026-11-02 10:50 ---
Prepared for commit with the documented source/profile regeneration, test-first
regressions and full-game evidence. The November 2 completed manual audit
confirms the relevant generated-chart mechanisms: no field-independent run
TDs, ordinary breakaway resolution, no concentrated interception recurrence,
and both kick and return fouls. Close this specific transformation/coverage
issue on that evidence; statistical fit and coaching limitations remain
documented. The new engine timing changes do not establish a fresh 64/256-season
fit; DATA-011 explicitly distinguishes the earlier fitting evidence.

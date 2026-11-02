---
id: DATA-013
title: Generated charts omit special-teams penalty results
status: closed
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - chart-generator
  - penalties
  - calibration
  - reproduced
links:
  - DATA-014
---

## Description

A manual generated-chart Eagles-Cowboys game displayed six penalty procedures containing seven
penalty chart cells. Only two penalties were accepted, one against each team for five yards, so the
final statistics showed one penalty for five yards per team and concealed the four procedures where
the offended team retained the play result.

The game contained 131 ordinary scrimmage calls and 29 kickoff, return, punt, punt-return, and
field-goal chart events. Weighting each observed call by the physical offensive-dice distribution,
the generated charts expect 7.45 initial penalty triggers. The local developer charts expect 15.13
for the same call mix. Six or fewer initial triggers has a 37.85% probability under the generated
charts and a 0.49% probability under the developer charts.

Replaying the same initial offensive and special-teams rolls produces six generated-chart penalty
cells and 17 developer-chart penalty cells: 14 on scrimmage calls and three on special teams. This
is a primary-chart comparison only; alternate penalty results would consume additional dice and
change later game state, so it does not claim an alternate final score.

The scrimmage-call expectations are 7.45 generated versus 13.11 developer. Generated offense
columns use a fixed 5.5% penalty target, while the corresponding developer columns commonly carry
more penalty mass. The generated Eagles and Cowboys special-teams charts contain no penalty cells;
the developer special-teams charts contribute 2.02 expected triggers for the 29 events in this game.
Including penalty rerolls, the chart expectations are approximately 7.91 generated penalty cells
versus 17.03 developer penalty cells.

## Resolution / verification

The generator now assigns deterministic fallback penalty mass to kickoff, kickoff return, punt,
punt return, interception return, and field-goal columns. Empirical generation retains observed
accepted and declined non-offsetting special-teams fouls. If a resolved empirical sample has no
foul, it retains at least one fallback result instead of reducing the chart's foul probability to
zero. Field-goal accuracy is recalibrated across numeric cells because the engine rerolls penalty
results.

The PFR and nflverse adapters classify kick and return fouls on the chart that produced them. They
also preserve the offensive interception result when a foul occurs during its return and classify
that foul on the return team's interception-return chart. The published 1983 and 2024 chart sets
were regenerated from the existing regular-season sources and calibration profiles. The fictional
2026 sample charts received the same fallback coverage.

This ticket is limited to the missing special-teams result families. The broader question of the
proper scrimmage penalty frequency remains an engine-calibration question and is not answered by
adding these cells.

## Comments

--- 2026-11-02 07:00 ---
Added failing regressions for aggregate generation, empirical fallback retention, PFR and nflverse
special-teams classification, interception-return fouls, and the public 2026 sample charts. The
regressions failed against the prior implementation because every generated special-teams column
lacked a penalty result or the source foul was converted to an ordinary outcome.

--- 2026-11-02 07:01 ---
Regenerated 1983 from 224 regular-season games through December 19 and 2024 from all 272
regular-season games. Audits found 568 special-teams penalty cells in 1983 and 604 in 2024; all
teams have coverage in all six families. The two public sample teams contain 29 cells.

--- 2026-11-02 07:02 ---
Focused validation passed 344 generator, source-adapter, special-teams engine, return, and
sample-data tests. Ruff passed for all touched Python files. The issue remains open until the fix
is committed.

--- 2026-11-02 07:08 ---
The complete core suite passed: 6,364 tests with eight existing skips for unavailable 1972 or other
optional local test data. A paired 32-game public sample run also completed (one valid regular-season
tie). Its traces exercised special-teams penalty rerolls and accept/decline handling. Two prior test
expectations were corrected: field-goal calibration and sample-team strength comparisons now use
numeric-cell conditional averages because penalty cells are rerolled rather than treated as kick
values.

--- 2026-11-02 08:50 ---
The broader DATA-014 audit verified coverage in all six special-teams penalty families for every
1983 and 2024 generated team, alongside kick/return attribution and nominal foul-yardage fixes.
The final charts contain 538 and 683 special-teams penalty cells respectively; the counts changed
as source classification and quantization were corrected. Coverage remains complete for every team.
The final 1983 generated-schedule engine audit completed all 448 games and included 113 scoring
penalty-choice checks, 258 finalized punt penalty calls, and 23 finalized field-goal penalty calls;
both historical-schedule postseason sanity runs also completed. The complete
core suite passes 6,394 tests with eight existing skips. Keep open until these changes are committed.

--- 2026-11-02 10:15 ---
Latest manual game exercises two special-teams penalty families: an assessed kickoff-return foul at halftime and a kicking-chart foul accepted for a re-kick. The prior complete omission of special-teams foul cells does not recur in this game. Separate STAT-005 records an unexplained extra fifteen-yard charge in the final home penalty total, and AUD-026 records the false kickoff-menu touchdown preview; neither establishes missing generated penalty cells. Keep open pending commit; see ../../game-audit-2026-11-02.md.

--- 2026-11-02 10:50 ---
Prepared for commit with the documented source/profile regeneration, test-first
regressions and full-game evidence. The November 2 completed manual audit
confirms the relevant generated-chart mechanisms: no field-independent run
TDs, ordinary breakaway resolution, no concentrated interception recurrence,
and both kick and return fouls. Close this specific transformation/coverage
issue on that evidence; statistical fit and coaching limitations remain
documented. The new engine timing changes do not establish a fresh 64/256-season
fit; DATA-011 explicitly distinguishes the earlier fitting evidence.

---
id: DATA-004
title: Aggregate chart generation compresses distinct teams into coarse defensive templates
status: closed
priority: Medium
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: 2026-11-01
tags:
  - reproduced
  - play-tested
---

## Description

The generated 2024 Hard-vs-Hard replay materially mis-ranked several teams. A
read-only generator audit ruled out season length: the input model has no games
played field, and doubling every counting statistic while preserving all rates
produces byte-identical offense, defense, and special-teams charts.

Defense generation is too coarse for season calibration. It rounds rushing and
passing efficiency into integer template shifts and changes only a small number
of interception and sack cells at fixed thresholds. The 32 generated 2024 teams
therefore produced only 13 distinct defense files; one group contained ten teams
and another contained seven. The generated 1983 comparison set has the same
structural issue, with only ten distinct defenses among 28 teams. This can erase
meaningful team strength before Hard AI analyzes the charts.

The 1983 aggregate generator was not previously established as team-accurate:
its initial paired audit matched only five of 14 winner orientations while
roughly matching cohort averages. The 2024 replay therefore exposed an existing
generator limitation rather than a demonstrated 16-game versus 17-game defect.

## Resolution / verification

Add synthetic/public-team failing tests before changing generation behavior.
Measure generated chart strength against source offensive and defensive rates,
points, turnovers, and multi-seed game distributions. Replace coarse defense
rounding with a weighted calibration that preserves continuous team differences
without discarding formation structure. Review whether scoring, field-goal
accuracy, red-zone performance, and play-volume information need explicit input
fields. Validate aggregate and empirical modes separately and keep historical
source charts and replay artifacts local and ignored.

## Comments

--- 2026-11-01 00:00 ---
Opened from the generated 2024 season replay investigation. Kansas City's
simulated last-place finish prompted the audit, but the duplicate-defense and
count-scaling checks establish a generator-wide cause rather than a team-specific
data correction.

--- 2026-11-01 14:30 ---
The archived Data Driven Football design-process page confirms that its chart
workflow parsed every official regular-season play-by-play record, manually
reviewed every database record, watched video of every play to verify gamebooks
and capture defensive alignments, mapped probabilities with both software and
manual judgment, and simulated at least 100 seasons for quality assurance:
https://web.archive.org/web/20250524072210/http://www.datadrivenfootball.com/designprocess.html
The current 2024 generator uses aggregate mode and only enriches selected totals
from play-by-play, so it does not reproduce that methodology.

--- 2026-11-01 16:30 ---
Added a failing synthetic regression for two defenses separated by only 0.2 rushing
yards per attempt and 0.4 passing yards per attempt. Before the production change,
both teams generated the same defense chart. Added a separate control that doubles
all counting totals while preserving rates; the generated charts remain identical,
confirming that season length itself is not an input.

Replaced integer-rounded defense shifts with continuous targets. Whole shifts still
apply across the tactical template, while fractional shifts are assigned to eligible
sub-rows using the actual defensive dice probability mass. Centralized the red/green
defensive dice faces and their sub-row weights in `play_resolver.py` so game resolution
and chart calibration share one distribution. The 2024 set now has 32 distinct defense
files for 32 teams, up from 13. Focused generator tests pass, including the new close-
efficiency regression and rate-scaling control.

--- 2026-11-01 17:10 ---
Replayed the same 2024 schedule with Hard-vs-Hard, base seed 202422. The structural
fix did not improve this season sample: win MAE changed from 3.47 to 3.72, RMSE from
4.43 to 4.44, win correlation from 0.07 to 0.09, and actual playoff-team overlap from
7/14 to 6/14. Kansas City remained 7-10. The champion changed from Miami to Baltimore.

DATA-004 remains open. The duplicate-defense defect is fixed, but the ticket's season-
calibration acceptance criteria are not met. The next useful generator change is a
classified play-by-play path with multi-seed evaluation, matching the documented Data
Driven Football process more closely. Further tuning against this single replay would
fit random season variance rather than establish chart quality.

--- 2026-11-01 18:20 ---
The defense-only five-seed comparison confirmed that unique defense files alone did
not improve calibration. Average win MAE worsened from 3.71 to 4.03 and win
correlation remained near zero. Reviewing the generated offense distributions then
found a second compression defect: `_replace_rate()` selected from every row on each
call, so later touchdown, pressure, or penalty placement could overwrite previously
assigned incompletions and interceptions. Its greedy dice-mass search also missed
closer combinations. A new synthetic regression failed because a requested 27%
incompletion rate survived as only 13.9%, and some requested outcome classes vanished.

Updated symbolic allocation to use only remaining numeric rows and replaced the greedy
selector with a bounded subset-sum search over the 216 offensive dice combinations.
The regression now verifies incompletion, interception, touchdown, pressure, and penalty
rates independently. All 11 generator tests pass. Play-resolver and penalty focused
suites also pass, preserving defensive dice metadata and penalty behavior.

--- 2026-11-01 19:00 ---
Ran five paired 2024 Hard-vs-Hard seasons on identical schedules and seeds (202422,
212422, 222422, 232422, and 242422), totaling 1,360 regular-season games per chart
set plus postseasons. Compared with the original generator, the final DATA-004 build
reduced average win MAE from 3.71 to 2.39 and RMSE from 4.57 to 3.01. Win correlation
improved from 0.03 to 0.62, average actual playoff-team overlap from 6.0/14 to 9.4/14,
points-for correlation from -0.03 to 0.93, points-against correlation from 0.50 to
0.68, and point-differential correlation from 0.30 to 0.90. Kansas City improved from
5.6 to 9.2 average wins, though it remains below its actual 15-2 record.

Regenerated all local 2024 charts with the final allocator. The original requested
seed 202422 now produces Buffalo as champion, Kansas City at 10-7, a 2.28 win MAE,
0.65 win correlation, and 10/14 actual playoff teams. DATA-004 is resolved because
the chart-compression defects have failing regressions, the structural uniqueness
check passes, and paired play testing demonstrates a material calibration improvement.
Empirical play-by-play classification remains separate follow-up work rather than a
condition for this aggregate-generator defect.

--- 2026-11-01 20:00 ---
Replayed the final charts Medium-vs-Medium on the same five schedules and seeds used
for Hard. Medium produced a 2.38 average win MAE, 2.93 RMSE, 0.63 win correlation,
and 10.0/14 average playoff-team overlap. Hard produced 2.39, 3.01, 0.62, and
9.4/14 respectively. Medium had stronger allowed-points correlation (0.75 versus
0.68), while Hard had stronger points-for (0.93 versus 0.89) and point-differential
correlation (0.90 versus 0.88). Kansas City averaged 9.8 wins on Medium and 9.2 on
Hard; Philadelphia averaged 12.8 and 11.0.

This additional play test confirms that DATA-004's improvement is not specific to
Hard AI. Medium and Hard are effectively tied on record accuracy in this five-seed
sample, with small tradeoffs in scoring and playoff-field fidelity. The resolved
status remains supported.

--- 2026-11-01 20:30 ---
Repeated all five Hard-vs-Hard seasons from the regenerated `seasons/2024` directory
using the same seeds. Every result matched the prior fixed-chart JSON exactly, including
standings, postseason games, scores, and champions (Buffalo, Baltimore, LA Chargers,
Philadelphia, and Tampa Bay). The rerun retained a 2.39 average win MAE, 3.01 RMSE,
0.62 win correlation, 9.4/14 playoff-team overlap, 0.93 points-for correlation, 0.68
points-against correlation, and 0.90 point-differential correlation. This confirms the
reported DATA-004 comparison is reproducible from the current generated season files.

--- 2026-11-01 21:00 ---
Ran five Easy-vs-Easy seasons on the same schedules and seeds. Easy disables Hard
chart analysis and Medium's team-strength run/pass bias, but still uses generic
situational, clock, field-position, and fourth-down logic. It produced a 2.39 average
win MAE, 3.03 RMSE, 0.59 win correlation, 9.6/14 playoff-team overlap, 0.88
points-for correlation, 0.62 points-against correlation, and 0.85 point-differential
correlation. Kansas City averaged 8.8 wins and Philadelphia 11.0. Baltimore won four
of the five postseasons; Philadelphia won the fifth.

Easy retained a strong chart-derived scoring signal but did not improve fidelity over
Medium or Hard. The weaker correlations and concentrated Baltimore championships show
that generic play selection does not isolate chart quality as cleanly as expected. A
truly strategy-neutral test would need a dedicated fixed play-distribution caller rather
than an existing gameplay difficulty. DATA-004 remains resolved.

--- 2026-11-01 22:00 ---
Added and play-tested the developer-only `none` coaching baseline requested for chart
calibration. Five None-vs-None replays completed 1,360 regular-season games and 65
postseason games. The neutral policy retained meaningful chart signal but trailed the
coached modes: 2.61 win MAE, 3.22 RMSE, 0.54 mean per-season win correlation, and
8.4/14 average actual playoff-team overlap. Kansas City averaged 7.8 wins and
Philadelphia 11.0; champions were Arizona, Denver, Denver, Baltimore, and Baltimore.

The result confirms that the repaired charts remain differentiated without team-aware or
situational coaching, while also showing that realistic play policy improves historical
fit. Together with 32/32 distinct defenses, disjoint symbolic offense allocation, focused
regressions, and the Hard/Medium/Easy paired replays, this supplies the required play-test
confirmation. DATA-004 is closed.

--- 2026-11-01 15:04 ---
Pending-change review (local CST timestamp) reconciled the saved five-seed reports
and confirmed that this closure applies to defense compression and symbolic
allocation, not full historical calibration. The scoring correlations are of
five-seed team means; Hard still averages 19.98 points per team-game versus 22.91
historically. Follow-up empirical marker loss and calibration gaps are recorded
in DATA-005 and DATA-006. No additional resolved ticket has sufficient new
play-level confirmation from these summaries to close. See the review section
in the statistical chart generator development note.

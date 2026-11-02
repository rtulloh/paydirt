---
id: DATA-007
title: Modern season chart generation bypasses available play-by-play data
status: closed
priority: High
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: 2026-11-01
tags:
  - reproduced
  - play-tested
links:
  - DATA-006
  - DATA-008
  - DATA-009
---

## Description

The 2024 chart workflow used normalized aggregate season totals even though complete
regular-season nflverse play-by-play was available locally. That bypasses the
empirical path established for historical chart generation and discards play
families, observed result distributions, opponent context, accepted penalties,
out-of-bounds markers, field-goal distance results, and fumble-loss events.

The aggregate path remains useful when no suitable play-by-play source exists, but
it must be an explicit fallback. Seasons with complete play-by-play should use a
source adapter that produces the same normalized empirical outcomes consumed by
the opponent-adjusted chart generator.

## Resolution / verification

Add a tested nflverse adapter and generator command. Generate all 2024 charts from
regular-season play-by-play plus normalized aggregate totals, retain local audit
CSVs and a source manifest, then replay the season through the engine. Compare the
same scoring, volume, efficiency, record, playoff, and Super Bowl metrics against
the prior aggregate charts and actual 2024 results. Keep downloaded data and replay
artifacts ignored.

## Comments

--- 2026-11-01 21:45 ---
Added failing synthetic coverage before implementation. The missing generator
command failed with `ModuleNotFoundError`. The implemented nflverse classifier and
command now pass focused tests and lint. A first full-source classification found
272 regular-season games and complete opponent attribution across all 32 teams;
season generation and engine replay remain pending.

--- 2026-11-01 22:35 ---
Generated all 32 local 2024 teams from nflverse play-by-play with opponent adjustment. The
manifest records 272 games, 47,274 source rows, 47,351 normalized outcomes, 1,115 field-goal
attempts, 504 fumbles, and the selected engine calibration. Only the sparse draw column fell back
to aggregate generation, once per team.

The 256-season Hard replay completed 69,632 regular-season and 3,328 postseason games without a
failure. Versus the prior aggregate charts, mean win MAE improved from 2.366 to 2.325, team-mean
win correlation from .760 to .795, points-for correlation from .925 to .938, points-against
correlation from .661 to .678, and playoff overlap from 9.25 to 9.70 of 14. Completion, passing
yards per attempt, sacks, turnovers, and play volume also moved closer to actual. Scoring remains
0.94 points per team-game high and yardage 18.31 yards high. The run produced 66 Super Bowl pairs
and 18 champions; Kansas City–Philadelphia occurred 3/256 and Philadelphia won 38 championships.
The source-path defect is resolved. Remaining engine/coaching calibration should use a separate
ticket if pursued.

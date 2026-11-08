---
id: DATA-045
title: Evaluate pre-1977 historical seasons with incomplete play-by-play, starting with 1972
status: open
priority: Low
created-at: 2026-11-08
resolved-at:
closed-at:
tags:
  - deferred
---

## Description

The owner would like to add one historical season per release to attract players
interested in particular seasons. The 1972 season is a candidate, but this research
has not established a complete regular-season play-by-play source. Schedules,
results and aggregate team/player statistics are available. Aggregate totals cannot
recover team-specific screen/short/long passing tendencies or gain distributions.
The existing generator supports aggregate fallback, with explicit modeled inputs.

On 2026-11-08 the owner deferred this work because source reconstruction, modeling
and validation could consume substantial analysis time and tokens. Prefer a newer
season with available play-by-play for the next season addition. No release target
or implementation campaign is authorized by this ticket.

## Resolution / verification

When explicitly prioritized, first perform a bounded source-coverage check for
1972 gamebooks/play-by-play. Document missing fields and modeled assumptions.
Pilot contrasting teams before generating the whole league. Validate play-specific
outcome support (including interception locations), offense/defense/special teams,
era rules, and historical schedules. Calibrate and independently validate scoring,
yardage, turnovers, sacks and team performance; do not force historical qualifiers
or champions. Describe aggregate-derived charts as modeled historical charts,
without claiming reconstruction of original board-game charts.

For the next season addition, first confirm complete usable play-by-play coverage
and compatibility with an existing source adapter. Reuse cached inputs and the
established generation/audit pipeline. Agree on a bounded scope before starting
expensive tuning or repeated-season campaigns; no such campaign started here.

References:

- [1972 schedule and results](https://www.pro-football-reference.com/years/1972/games.htm)
- [PFR announcement of coverage back to 1977](https://www.sports-reference.com/blog/2026/08/1977-play-by-play-and-associated-stats-added-to-pro-football-reference/)
- [Existing generator and aggregate fallback](../../../chart-generator.md)

## Comments

--- 2026-11-08 16:10 ---
Deferred at the owner's request. Prioritize a newer season with available
play-by-play to reduce generation cost. No chart changes or simulations run.

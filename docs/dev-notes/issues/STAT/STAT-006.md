---
id: STAT-006
title: Track cumulative team statistics and performance throughout a season
status: open
priority: Low
created-at: 2026-11-07
resolved-at:
closed-at:
tags:
  - feature-request
---

## Description

Players want to watch how teams perform over the course of a season, rather
than viewing each game's statistics in isolation. Add a player-facing season
statistics view built from the authoritative game results and statistics.

The initial scope is team performance: standings and win/loss/tie records,
points scored and allowed, cumulative offensive and defensive statistics,
and per-game averages. Include rushing and passing production, turnovers,
and sacks where the engine records them. A team detail view should show
game-by-game results so players can follow progress through the schedule.
Individual player season statistics can be considered separately.

## Resolution / verification

Future backlog feature; not an additional requirement for release 1.10.2.
Before implementation, review existing season, standings, game-statistics,
and save/load support to reuse authoritative records and define the supported
season workflow.

Acceptance criteria:

- Players can view season standings, cumulative team totals, and per-game
  averages, then inspect a team's completed-game results.
- Totals reconcile with the contributing completed games, including ties
  and overtime. Scheduled or unfinished games do not count as completed games.
- Saving, loading, and reopening a completed game do not duplicate its
  contribution. Season and team identities keep different campaigns separate.
- Season progress and statistics persist across application restarts.
- Aggregation belongs in the core season/statistics layer; interfaces display
  the returned values. Rates use underlying totals rather than averaging
  individual-game percentages.
- Verification uses synthetic or public sample teams and covers multiple
  games, reconciliation, persistence, duplicate prevention, and the player view.
  Update the relevant player guide when the feature is implemented.

## Comments

--- 2026-11-07 00:00 ---
Requested by the user so players can follow team performance over a season.
This ticket records the feature request; no implementation is included yet.

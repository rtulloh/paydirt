---
id: STAT-006
title: Track cumulative team statistics and performance throughout a season
status: closed
priority: Low
created-at: 2026-11-07
resolved-at: 2026-11-19
closed-at: 2026-11-19
tags:
  - feature-request
links:
  - FLOW-036
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
Individual player statistics are excluded by owner instruction.

## Resolution / verification

Implemented for v1.12.0 using canonical campaign results and engine team statistics.
The acceptance criteria below were reviewed against the November 19 evidence.

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

--- 2026-11-18 11:17 ---
Coordinated by [FLOW-036](../FLOW/FLOW-036.md), the owner-approved web seasons
umbrella and six-slice design. Retain this issue's acceptance/evidence requirements;
no fix or closure is claimed. Team statistics only; individual player statistics
are explicitly excluded by the owner.

--- 2026-11-18 13:56 ---
Canonical team totals, rates, per-counter coverage/Partial labels and team leader categories are implemented; rendered statistics and revision recomputation pass actual Chromium acceptance. Individual player statistics are excluded.
See [FLOW-036 acceptance](../../season-ui-acceptance.md) for final-source receipts,
coverage and retained original failures. Work remains uncommitted; this issue stays
open for review/integration rather than claiming a published fix.

--- 2026-11-18 16:30 ---
Owner-requested season refinements are implemented locally: default conference/division standings (NFC before AFC; responsive columns), distinct Offense/Defense/Kicking categories, defensive interceptions/fumble recoveries/sacks, FG distance bands, passing/rushing attempts and weighted team efficiency including NFL passer rating. The final stable-source actual Chromium run passed all 12 selected checks: both complete games (38–24, 41–34), real-engine season simulations and team-stat reconciliation, pending-decision recovery, single final recording, persistent browser restart and desktop/phone layouts. Reviewed this issue against that play-test evidence; retain open for review/integration, with no published fix/commit claimed. Coverage and original interrupted/failed receipts remain in [acceptance notes](../../season-ui-acceptance.md) and ignored `.ai-audits/season-ui/standings-kicking/`. Broad final core test run remains in progress; no complete pre-push qualification claimed.

2026-11-18 final validation: complete stable-source core suite 11,839 passed; backend 657 passed (480 existing deprecation warnings), frontend 572 passed, all 12 selected real Chromium checks passed, including complete games and requested team-stat displays. Ruff/docs pass. Detailed coverage and original interrupted evidence retained in acceptance notes. Current requested refinements are complete locally; status remains open for review/integration, with required pre-push gates still applicable.

--- 2026-11-18 21:40 ---
Implemented sortable season-table headers, keyboard/direction announcements, raw numeric sorting and unknown-last behavior. Zero coverage now reads Not recorded rather than Partial. All 574 frontend tests/four rendered season checks pass; focused SeasonDesk coverage 89.72% lines/87.13% branches. Also recovered missing kicking/offensive attempt counters for the owner’s specific completed legacy game from fully aligned structured history, with all existing yardage/sack/INT counters reconciling, normal result correction/history retention and atomic CAS. Actual UI verifies both teams’ offense/defense/kicking fields populated. Private receipts remain ignored; score 21–20 and single result preserved. See acceptance notes for tests/baselines and repair boundaries. Issue remains open for integration; no push/release claimed.

--- 2026-11-19 12:25 ---
Closed after actual c0b4292 packaged-app acceptance: all thirteen team-statistics categories have complete 2/2-game counter coverage, rendered sortable compact tables and identical campaign exports after process/browser restart. Domain regressions verify totals, weighted rates, MAX values, paired turnover coverage, ties/overtime and duplicate/revision recomputation. Retained-play capture covers punts, kicks, attempts/completions, rushing/receiving, first downs and defense; test-first final correction preserves inside-20 credit when a later fumble recovery scores. Browser-only all 90 inventory plus eight complete games pass. Legacy unavailable counters remain explicitly unknown; no individual player statistics. Release-wide gates/publication remain FLOW-036.

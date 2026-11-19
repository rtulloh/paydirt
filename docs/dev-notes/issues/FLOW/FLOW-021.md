---
id: FLOW-021
title: Web UI cannot record completed games to season standings or show season progress
status: closed
priority: Medium
created-at: 2026-11-08
resolved-at: 2026-11-19
closed-at: 2026-11-19
tags:
  - requested
links:
  - FLOW-036
  - FLOW-022
---

## Description

Players can complete games in the web UI, but final scores are not recorded in season standings. The CLI already offers this through the shared standings module. This prevents players from continuing an existing season entirely in the browser.

## Resolution / verification

The approved campaign/fixture workflow below is implemented in v1.12.0; it supersedes the original post-game picker and shared-module prescription retained in the historical checklist. See the November 19 verification comment for the explicit reconciliation.
- Offer an explicit action after a completed web game to record its final result to a selected season and week.
- Reuse the shared standings implementation and authoritative engine final score; retain existing CLI standings and save compatibility.
- Show current standings and completed games so players can identify the next unplayed matchup.
- Prevent duplicate recording, confirm success, and preserve the game if persistence fails.
- Validate the selected historical week instead of deriving it from the count of completed games; an existing local season has a Week 6 matchup recorded as week 80.
- Cover both human home/away, ties, replay/restored completed games, duplicate clicks, and persistence failure with synthetic/public-team tests.

Keep aggregate season statistics as a related follow-up; this request specifically covers completed results and standings. Do not gate the ongoing AI-026 simulation-fidelity experiment on this UI feature.

## Comments

--- 2026-11-08 14:24 ---
Requested by the owner. Moved from mistakenly created GitHub issue #1 to the
repository tracker; implementation remains pending. GitHub is not the tracker for
this request. No release commitment or gameplay change accompanies this ticket.

--- 2026-11-18 11:17 ---
Coordinated by [FLOW-036](../FLOW/FLOW-036.md), the owner-approved web seasons
umbrella and six-slice design. Retain this issue's acceptance/evidence requirements;
no fix or closure is claimed. Team statistics only; individual player statistics
are explicitly excluded by the owner.

--- 2026-11-18 13:56 ---
The rendered season desk, result recording/revisions, standings, simulation/postseason and restart recovery pass actual Chromium acceptance.
See [FLOW-036 acceptance](../../season-ui-acceptance.md) for final-source receipts,
coverage and retained original failures. Work remains uncommitted; this issue stays
open for review/integration rather than claiming a published fix.

--- 2026-11-19 12:25 ---
Closed after actual native/browser season acceptance. The owner-approved six-slice workflow supersedes the original post-game season/week picker: select a campaign fixture before play, then atomically record the authoritative legal final into its known week. Campaign standings reuse the canonical campaign result ledger, rather than modifying the separate CLI standings storage. Tests cover historical fixture/week validation, ties, both human roles, replay/final idempotency, persistence failure safety and retained revisions. Actual packaged two-game campaigns, mixed-edition standings and identical exports after application/browser restart confirm persistence and single contributions. Existing CLI saves/standings remain covered by passing core suites. No claim that the superseded literal UI/module prescription was delivered. Release qualification remains FLOW-036.

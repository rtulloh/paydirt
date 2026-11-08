---
id: FLOW-021
title: Web UI cannot record completed games to season standings or show season progress
status: open
priority: Medium
created-at: 2026-11-08
resolved-at:
closed-at:
tags:
  - requested
links:
  - FLOW-022
---

## Description

Players can complete games in the web UI, but final scores are not recorded in season standings. The CLI already offers this through the shared standings module. This prevents players from continuing an existing season entirely in the browser.

## Resolution / verification
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

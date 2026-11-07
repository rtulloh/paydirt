---
id: FLOW-020
title: Allow web players to select opposing teams from different seasons
status: open
priority: Low
created-at: 2026-11-07
resolved-at:
closed-at:
tags:
  - feature-request
---

## Description

Players should be able to play a matchup between teams from different seasons
through the web UI. The current team-selection screen has one shared SEASON
selector; changing it clears both selections, and game creation submits one
season for both teams. This prevents choosing each team's year independently.

Provide independent season/team selections for the player and opponent, while
keeping ordinary same-season matchups easy to start. Show each selected team's
year clearly, including when the same franchise is selected from different years.

## Resolution / verification

Future backlog feature; not an additional release 1.10.2 requirement.

- Review existing engine and API cross-season support before implementation;
  preserve each team's complete season-qualified identity through creation,
  display, charts, and save/load.
- Changing one side's season must not clear the other side's valid selection.
  Reject missing teams or stale season/team combinations explicitly.
- Use the core engine's existing home-team-season rule selection, subject to
  verification, and explain the governing rules in setup. Changing home/away
  must produce consistent rules; the frontend must not implement era rules.
- Verify same-season and mixed-season games, both player home/away choices,
  same-franchise/different-year identities, chart loading, and save/load.
  Write failing synthetic/public-only regressions before behavior changes.
- Update setup/player guidance and include browser confirmation of the flow.

## Comments

--- 2026-11-07 00:00 ---
Requested after a Facebook question about selecting different years. Current
season buttons appear above the team grid on the SELECT TEAMS screen; this
ticket extends that shared selector to independent cross-season matchups.

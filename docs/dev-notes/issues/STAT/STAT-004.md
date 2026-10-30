---
id: STAT-004
title: Standings game numbers target the wrong record after out-of-order weeks
status: open
priority: High
created-at: 2026-10-30
resolved-at:
closed-at:
tags:
  - reproduced
---

## Description

`paydirt/standings.py:display_games` groups and sorts by week, then assigns
sequential display numbers. `main` edits or deletes `season.games[number - 1]`
in insertion order. In a temporary synthetic season, add Bills-Jets in week 2
followed by Bears-Lions in week 1. `games` displays Bears-Lions as game 1;
`edit 2026 1 --home-score 31` instead changes the Bills-Jets score. `delete`
has the same index mismatch (its confirmation does show the different game).
Editing a week can also reorder the display. The player guide tells users to
use the numbers from `games` for these commands.

## Resolution / verification

Use a consistent record identifier or mapping for display, edit and delete.
Add temporary-directory CLI regressions for out-of-order and equal-week games,
week edits, deletion confirmation, and an already ordered control. Verify that
the selected record alone changes and no existing standings are used.

## Comments

--- 2026-10-30 15:09 ---
Reproduced the incorrect edit against a temporary standings directory; no user
standings were read or modified.

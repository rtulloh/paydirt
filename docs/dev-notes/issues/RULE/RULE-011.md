---
id: RULE-011
title: Kickoff spot is a constant 35 (kickoff(kickoff_spot=35), web KickoffRequest.kickoff_spot=35) and the touchback…
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - decided
---

## Description

Kickoff spot is a constant 35 (`kickoff(kickoff_spot=35)`, web `KickoffRequest.kickoff_spot=35`) and the touchback shortcut `ko_yards >= 75` is hard-wired to it. Decision 2026-10-19: follow the **actual season rules**, not the booklet's 30. NFL kickoff spot by era: 40 (through 1973), 35 (1974–1993), 30 (1994–2010), 35 (2011–). The current constant is correct for 1983 and 2026 but wrong for 1994–2010 and pre-1974 seasons.

## Resolution / verification

Add `kickoff_spot` to the season YAML (required field like `two_point_conversion`, scaffold default by year per the table), load it in `SeasonRules`, use it in `kickoff()`/web/auto/CLI, derive touchback and end-line logic from the spot instead of the `>= 75` constant, and expose it in `get_season_rules()`. Safety free kicks remain at the 20. Add season-rule tests for each era and a loader test that rejects a missing field.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (decided)).

---
id: RULE-008
title: Spikes, kneels, and fourth-down offensive fumble recoveries that exhaust downs set turnover=True as well as…
status: open
priority: Low
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

Spikes, kneels, and fourth-down offensive fumble recoveries that exhaust downs set `turnover=True` as well as `turnover_on_downs`, contrary to the documented separation; UI shows a turnover marker.

## Resolution / verification

Set `turnover=False, turnover_on_downs=True` on all downs-exhausted paths; keep statistical turnovers unchanged.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

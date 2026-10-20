---
id: RULE-005
title: Apply_fg_penalty_decision extends the half for an accepted offensive foul (time_remaining <= 0.5 heuristic) but…
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

`apply_fg_penalty_decision` extends the half for an accepted offensive foul (`time_remaining <= 0.5` heuristic) but not for a defensive one, and FG offsetting omits `defensive_penalty=True`; inverse of the untimed-down rule used elsewhere.

## Resolution / verification

Drop the OFF extension, pass `defensive_penalty` to `_use_time`, then `check_untimed_down_for_defensive_penalty`.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

---
id: FLOW-002
title: Both CLI loops free-kicked after a half-ending safety (burning Q3 clock and flipping possession), then kicked off…
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at:
commits:
  - 2e37986
---

## Description

Both CLI loops free-kicked after a half-ending safety (burning Q3 clock and flipping possession), then kicked off again at halftime; `auto_game` already checked `should_kickoff_after_score`.

## Resolution / verification

Both loops now ask `should_kickoff_after_score()` before the free kick. Full-loop regressions: Q2-expiring safety → no free kick, halftime kickoff only, clock/possession intact; Q1-expiry and time-remaining controls still free-kick from the 20. Committed in `2e37986`; no release contains this fix yet.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

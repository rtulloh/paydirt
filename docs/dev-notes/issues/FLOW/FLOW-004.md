---
id: FLOW-004
title: CheckPendingPat fallback references the deleted isHomeScoring
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-20
closed-at:
tags:
  - reproduced
---

## Description

`checkPendingPat` fallback references the deleted `isHomeScoring`; a missing/null `player_offense` throws `ReferenceError` in the TD flow.

## Resolution / verification

Removed the stale UI fallback: `player_offense === true` is the sole engine-owned indicator that the player scored. Added a regression for a pending PAT response without `player_offense`; it must not throw and must not offer the player a PAT choice. Focused and complete frontend test suites plus production build pass. Await a browser play-test of the missing/null response path before closing.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (reproduced)).

--- 2026-10-20 17:45 ---
Resolved with frontend regression coverage. The prior `isHomeScoring` fallback caused a `ReferenceError` when `player_offense` was missing or null. The UI now safely defaults to the CPU path until the authoritative engine flag is present.

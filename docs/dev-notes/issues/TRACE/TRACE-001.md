---
id: TRACE-001
title: Secondary QB-time rolls/results are not visible consistently, especially QB-time fumbles and transaction-based…
status: open
priority: Medium
created-at: 2026-10-18
resolved-at: 
closed-at:
links:
  - TRACE-007
---

## Description

Secondary QB-time rolls/results are not visible consistently, especially QB-time fumbles and transaction-based compact output.

## Resolution / verification

Existing resolvers already retain `qb_scramble_dice` and yardage. Audit all render paths and expose the captured secondary result in compact and normal output without rerolling, parsing commentary, changing RNG consumption, or altering gameplay. Cover sacks/safeties, scrambles, fumbles, and non-QT controls. This is the narrow next-round item in the replay note.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

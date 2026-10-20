---
id: FLOW-004
title: CheckPendingPat fallback references the deleted isHomeScoring
status: open
priority: High
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - reproduced
---

## Description

`checkPendingPat` fallback references the deleted `isHomeScoring`; a missing/null `player_offense` throws `ReferenceError` in the TD flow.

## Resolution / verification

Remove the fallback (engine flag is authoritative) and add a unit test.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (reproduced)).

---
id: SPIKE-002
title: Offense 7S is processed before a defensive AT, so execution order blocks the agreed defensive-timeout priority
status: open
priority: Medium
created-at: 2026-10-18
resolved-at: 
closed-at:
links:
  - AI-005
  - RULE-006
---

## Description

Offense `7S` is processed before a defensive `AT`, so execution order blocks the agreed defensive-timeout priority.

## Resolution / verification

Resolve penalty decisions, then an applicable defensive timeout, then any remaining spike request. Charge a useful available defensive timeout, cancel the planned spike, and charge no spike-related down. An unavailable timeout cannot cancel the spike; incompletions charge neither. Log the winning procedure.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

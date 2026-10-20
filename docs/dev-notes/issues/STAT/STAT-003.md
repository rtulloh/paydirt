---
id: STAT-003
title: Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception…
status: open
priority: High
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - reproduced
links:
  - RULE-001
  - STAT-001
---

## Description

Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception counts).

## Resolution / verification

Fixed by RULE-001; add accounting assertions to its regressions. STAT-001 remains separately open.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (reproduced)).

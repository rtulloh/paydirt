---
id: STAT-003
title: Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception…
status: open
priority: Medium
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

--- 2026-10-20 17:35 ---
Priority changed from High to Medium with RULE-001: this accounting defect is limited to two-point conversion attempts, which are not a current product priority. Keep its assertions with the eventual RULE-001 fix.

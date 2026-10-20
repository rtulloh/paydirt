---
id: TRACE-006
title: Compact punt-return penalty output lacked its reroll and enforcement details
status: resolved
priority: Medium
created-at: 2026-10-17
resolved-at: 2026-10-17
closed-at:
links:
  - TRACE-004
commits:
  - c155864
---

## Description

Compact punt-return penalty output lacked its reroll and enforcement details.

## Resolution / verification

`c155864` preserves and displays return reroll/enforcement information with focused tests. The latest audit contains the expected return-penalty details. Broader double-foul trace coverage remains TRACE-004.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

--- 2026-10-20 12:00 ---
The single-file tracker recorded this row on 2026-10-18, after the fix had already shipped (2026-10-17); created-at uses the fix date so the dates stay ordered.

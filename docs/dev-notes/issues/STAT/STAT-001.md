---
id: STAT-001
title: Enforced 15-yard punt double-foul penalty moves the ball but is absent from penalty count/yardage stats
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
links:
  - STAT-003
---

## Description

Enforced 15-yard punt double-foul penalty moves the ball but is absent from penalty count/yardage stats.

## Resolution / verification

Confirmed with synthetic public charts: the early-return path changes possession/spot without recording the enforced penalty. Fix with test-first accounting regressions separately; enforcement-rule interpretation is not validated by this finding.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

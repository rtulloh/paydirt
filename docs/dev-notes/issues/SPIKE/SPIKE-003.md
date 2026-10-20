---
id: SPIKE-003
title: A completion could leave time, then its spike reduce the clock to zero without processing period/game expiration
status: resolved
priority: High
created-at: 2026-10-18
resolved-at: 2026-10-18
closed-at:
links:
  - SPIKE-001
---

## Description

A completion could leave time, then its spike reduce the clock to zero without processing period/game expiration.

## Resolution / verification

v1.8.1: exposed by generated-season validation, then fixed with eight failing synthetic home/away direct/integrated regressions plus clock-preserved, tied-game, and untimed-down controls. Newly expired spike clocks delegate to existing `_use_time(0)` period/OT handling. No base timing, spike down charging, or defensive-timeout arbitration changes; SPIKE-001/002 remain open. Final 224-game season and nine playoffs passed.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

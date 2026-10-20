---
id: TRACE-002
title: Fumble traces show unknown defensive rows and placeholder-looking zero return rolls
status: open
priority: Low
created-at: 2026-10-18
resolved-at: 
closed-at:
links:
  - TRACE-007
---

## Description

Fumble traces show unknown defensive rows and placeholder-looking zero return rolls.

## Resolution / verification

Preserve actual defensive-row metadata; distinguish no return roll from an actual zero-yard return. Do not fabricate a `Ret:0` die roll. Reconfirmed in the latest audit.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

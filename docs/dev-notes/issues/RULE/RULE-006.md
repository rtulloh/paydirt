---
id: RULE-006
title: Offensive T/S modifiers are dropped whenever a penalty decision intervenes
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - reproduced
links:
  - SPIKE-002
---

## Description

Offensive `T`/`S` modifiers are dropped whenever a penalty decision intervenes; `apply_penalty_decision` cannot re-apply them, contrary to the documented order (decision, timeout, spike).

## Resolution / verification

`7T` with a flag and accepted play: no timeout, full play time charged. Persist the requests and pre-snap clock/timeout snapshot on the pending outcome and apply them after an accepted play. Related to SPIKE-002.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (reproduced)).

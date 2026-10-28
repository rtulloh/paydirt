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

--- 2026-10-28 08:58 ---
SPIKE-001 repairs the S-only request across a scrimmage penalty choice: retain
the pre-play clock/quarter, offense and down until a final play is retained;
then apply an eligible spike, including its down cost. Enforcing the penalty
or offsetting fouls does not spike. Offensive T (and the T/S precedence path)
still needs its full timeout snapshot and remains open here. This partial S
fix does not close RULE-006 or change defensive AT priority (SPIKE-002).

--- 2026-10-28 11:45 ---
SPIKE-002 now also preserves a defensive AT request and its pre-snap budgets
across a scrimmage foul. A retained eligible play resolves defensive AT
before S; enforcing a penalty or offsetting fouls charges neither. Offensive
T/T+S snapshot handling remains outside the fix and this ticket stays open.

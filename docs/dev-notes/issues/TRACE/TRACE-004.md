---
id: TRACE-004
title: Offsetting/double-foul procedures can omit initial rolls and rerolls, including previously observed empty…
status: open
priority: Medium
created-at: 2026-10-18
resolved-at: 
closed-at:
links:
  - TRACE-006
  - AI-015
  - AUD-020
  - RULE-019
  - RULE-020
---

## Description

Offsetting/double-foul procedures can omit initial rolls and rerolls, including previously observed empty punt-return details.

## Resolution / verification

Retain the actual event sequence even when the down is replayed. Prior finding; not independently reproduced for punt returns in the latest game.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

--- 2026-10-20 15:00 ---
Play-test reproduction: the penalty-decision screen showed `P:31→"OFF 5" | R:39→"15"`, but the completed result line only showed `(Roll: 31 → "OFF 5")`; the return roll was dropped after the decision. Linked to AI-015 and AUD-020.

--- 2026-10-28 12:40 ---
New supplied-game occurrence: a late-first-half long-pass call resolves
as offsetting penalties, replays the same down at the same spot and
uses ten seconds, but prints no offense/defense dice or foul/reroll
sequence (local lines 577-584). This confirms the ordinary-scrimmage
trace-loss branch, not a new punt-return reproduction. Keep open and
retain actual captured rolls in any future fix; do not reconstruct them.

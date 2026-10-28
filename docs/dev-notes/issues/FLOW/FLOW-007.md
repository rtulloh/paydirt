---
id: FLOW-007
title: Resume_game never passes the human/CPU spike modifier and prints no skipped-modifier messages
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

`resume_game` never passes the human/CPU spike modifier and prints no skipped-modifier messages; other divergences from the new-game loop: OT banner, safety punt option, CPU offensive-timeout helper, hard-coded quarter advance with `time_remaining = 15.0`.

## Resolution / verification

Extract one shared per-down routine used by both loops; regression matrix across new/resumed.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

--- 2026-10-28 11:45 ---
SPIKE-002 wires both human/CPU S and defensive AT requests through the core
for new and resumed CLI games. The resumed loop no longer discards the S
flag; real-engine synthetic/public regressions cover both control sides.
Keep FLOW-007 open for skipped-modifier messages and the remaining loop
divergences/shared-per-down refactor; this does not claim they are fixed.

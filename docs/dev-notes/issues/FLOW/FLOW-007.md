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

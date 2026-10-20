---
id: RULE-004
title: Run_play and _apply_play_result disagree on the −5 designation (floor at 0 vs negative), sack distance…
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

`run_play` and `_apply_play_result` disagree on the −5 designation (floor at 0 vs negative), sack distance (`yards_to_go` not updated), and interception `yards_gained`. `run_play` still serves tries, `simulate_week`, `game.py`, and `cli_charts`.

## Resolution / verification

Delegate the scrimmage branch of `run_play` to `_apply_play_result` or align the three rules with tests on identical inputs.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

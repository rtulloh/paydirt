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

--- 2026-10-30 15:09 ---
The separate `simulate_week.simulate_game` loop also misses current full-game
flow handling. With public 2026 charts and Python RNG seeds 25, 32 and 33,
instrumentation observed a kickoff called after `game_over`. It always kicks
after scoring without the engine's half/game boundary query, and exits its
500-play limit by returning the current score without reporting an incomplete
game; `simulate_week` then records that score in standings. The simulation
tests mock the game as already over rather than exercising a real full loop.
Consider delegating this path to the maintained auto-game loop; add public or
synthetic full-flow regressions for final scores, halftime, pending decisions,
overtime and action-limit failure, without touching real standings.

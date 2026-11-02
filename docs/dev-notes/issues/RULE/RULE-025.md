---
id: RULE-025
title: CLI discards a playable final second and prints FINAL before the engine ends the game
status: resolved
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at:
tags:
  - reproduced
---

## Description

The full-season regression exposed a mismatch between engine and CLI clock
boundaries. Both CLI entry points treated fewer than 0.0167 minutes as zero,
discarding a genuine second. A complete local game reached 1.0016277568 seconds
on the engine clock, then printed FINAL with `game_over` still false. The
engine already normalizes subsecond residuals and preserves a full second.

## Resolution / verification

The engine supplies `is_period_expired()`; new and resumed CLI games query it
without rewriting the clock. Six public/synthetic cases cover both entry
points at zero, one second and the observed fractional value. Baseline: four
expected failures and two passing expired-game controls. All six now pass.
The full local regression completes fifteen historical games, 224 regular
games and nine playoffs with engine final-state checks intact. Retain the
issue until commit, then await an issue-specific full-game final-second
observation before closing; ordinary complete games alone are insufficient.

## Comments

--- 2026-11-02 10:50 ---
Found while validating RULE-022. The original failure used an intermediate
twenty-second foul policy, which has been superseded by the supplied rules'
action-time policy. The captured boundary remains reproduced independently
with public fixtures; no historical charts or narrative logs are attached.

--- 2026-11-02 10:50 ---
Prepared for commit with all six final-second CLI cases passing and all full-season games complete. Keep resolved pending observation of this specific late-clock condition in a full game.

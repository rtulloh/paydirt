---
id: RULE-031
title: Deferred end-zone interception reapplies the in-bounds/out-of-bounds modifier and lands at the wrong spot
status: open
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at:
closed-at:
tags:
links:
  - FLOW-023
commits:
---

## Description

Found in the 2026-11-13 review of cedf6117..HEAD. `_apply_play_result` adjusts the interception result for the requested in-bounds or out-of-bounds designation before the own-end-zone deferral check (paydirt/game_engine.py). The defender then sees catch depth derived from the adjusted yards, and `apply_end_zone_interception_return_decision` re-runs `_apply_play_result` with the same stored designations. The second application is skipped for in-bounds because the stored result has already had `out_of_bounds` cleared, so the outcome depends on which modifier was chosen and can differ from the depth presented in the panel. Reproduced with public 2026 sample teams: an interception presented as four yards deep with a 15-yard return and an in-bounds designation placed the ball at the returning team's 6 instead of the 11.

## Resolution / verification

- Add a failing regression that presents the same catch depth with out-of-bounds, in-bounds and no designation and asserts each final return spot matches the published mechanics and the depth shown to the chooser.
- Apply each modifier exactly once across deferral, without mutating the stored result before the decision.
- Check the CLI and browser panels report the same depth the engine finally uses.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

---
id: FLOW-028
title: Hail Mary and direct run_play interceptions bypass the end-zone return choice
status: open
priority: Medium
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

Found in the 2026-11-13 review of cedf6117..HEAD. The in-play end-zone interception choice is implemented only in `_apply_play_result` (paydirt/game_engine.py). `_handle_hail_mary` calls `_handle_interception` directly for a Hail Mary interception caught in the intercepting team's own end zone, and a direct `run_play` call has its own resolution path. With the defender's policy set to `ask`, those paths resolve the return immediately using the automatic situation policy instead of prompting, so the same catch produces a choice or no choice depending on the play type and entry point.

## Resolution / verification

- Add failing regressions for an end-zone Hail Mary interception and a direct run_play interception under the ask policy, then make every interception entry point honor the same deferral or document and test the deliberate exclusion.
- Verify the CLI and browser both present the choice for a Hail Mary interception when the policy is ask.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

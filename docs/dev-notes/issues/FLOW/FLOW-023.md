---
id: FLOW-023
title: Choose end-zone interception returns during play
status: open
priority: Medium
target-release: v1.10.6
created-at: 2026-11-11
resolved-at:
closed-at:
tags:
links:
commits:
---

## Description

The pre-game end-zone interception preference is too coarse for situational coaching. A human should decide after the engine establishes the interception catch location, with score and time visible, but before any return dice are rolled or return outcome is revealed. A catch at the goal line or one yard deep while trailing may warrant a different choice from a deep catch while protecting a lead. Implement the same core-engine pending decision in CLI and web; the CPU should decide using catch depth and game situation.

## Resolution / verification

- Write failing synthetic/public-2026 regressions before production changes, including goal-line, one-yard-deep and deep catches, leading/trailing situations, and unaffected field-interception controls.
- Default human behavior is Ask each time. Present Touchback and Attempt return after catch location is known and before return dice; show engine-provided catch depth, score and clock.
- Keep all rules and pending-decision state in the core engine. CLI and web display and submit the same decision; resolving it once cannot duplicate rolls, turnovers, clock changes or statistics.
- CPU decisions use catch depth and game situation without advance knowledge of return dice; add meaningful tests for the policy.
- Saving and loading preserves an unresolved interception decision and its random state. Define backward-compatible handling of existing saved preferences; retain Always take touchbacks as an optional convenience.
- Preserve existing board-game touchback/depth mechanics and legal return eligibility. Update CLI/web player guides, API documentation and affected browser tests; complete required full regression and actual play-test confirmation.

## Comments

--- 2026-11-11 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

---
id: FLOW-024
title: Safety free-kick kickoff penalty strands the conceding team on offense
status: closed
priority: Medium
target-release: v1.10.6
created-at: 2026-11-13
resolved-at: 2026-11-13
closed-at: 2026-11-13
tags:
  - reproduced
  - play-tested
links:
  - FLOW-025
commits:
---

## Description

The CLI safety free-kick block printed a pending kickoff penalty but never called the penalty-decision handler. The engine therefore never switched possession to the receiving team and the next prompt showed the conceding team still on offense at its own 20. The web path also sent the normal 35-yard kickoff spot for a safety free kick instead of the engine's own 20.

## Resolution / verification

- Resolve a pending safety-free-kick penalty before the next snap in both CLI loops; possession must switch to the receiving team for either accept or decline. The web safety free kick must use the own-20 spot. Add failing-first CLI wiring and API spot regressions and rerun focused kickoff/safety suites.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-13 20:20 ---
Reproduced from the CHI/DET CLI log: after a Q4 safety, CHI's free kick
returned a kick-chart DEF 5 pending choice. The CLI printed the choice text but
continued to the next snap, leaving CHI (the conceding/kicking team) on offense
at its own 20. The engine was correct; the safety block skipped
`handle_penalty_decision`.

Implementation candidate (uncommitted, awaiting owner review): both CLI loops
would use `handle_safety_free_kick`, which prints the kick, resolves any pending
kickoff penalty with the receiving team as the offended "offense", and only then
runs `_complete_touchdown_sequence`. The web kickoff route would carry an
explicit `safety_free_kick` flag set by `_arm_kickoff` and use the own-20 spot
instead of the browser's normal 35-yard request.

Failing-first regressions prepared: `tests/test_safety_free_kick_cli.py` failed
on the missing helper and now covers a human-receiver pending choice and the
no-penalty control; the backend safety-spot case failed with 35 and now requires
20. Focused results: 89 core CLI/kickoff/safety tests passed, 7 backend kickoff
API tests passed, and ruff passed. The working tree has not been committed.

--- 2026-11-13 20:35 ---
Process correction: the candidate changes were prepared before owner review.
FLOW-024 is back to open/review-pending with resolved-at cleared. Review the
diff and decide whether to keep, revise or revert before any commit. No push has
been made.

--- 2026-11-13 21:15 ---
Owner play-test confirmed on the synthetic continuation (exact Q4 score/clock/
spot, forced safety and DEF 5 free kick): the free kick offered the penalty
choice; after the choice the receiving team (DET) took possession and the game
continued to completion. FLOW-025 separately records the duplicate/contradictory
menu labels; they did not change the choice or possession outcome. This closes
the issue-specific play-test confirmation.

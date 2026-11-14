---
id: FLOW-027
title: Resumed saved end-zone interception prints its return but skips the try/kickoff or safety free kick
status: resolved
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at: 2026-11-14
closed-at:
tags:
links:
  - FLOW-023
  - FLOW-007
commits:
---

## Description

Found in the 2026-11-13 review of cedf6117..HEAD. `resume_game` resolves a restored pending own-end-zone interception decision (paydirt/interactive_game.py, the `game.has_pending_end_zone_interception` block before the main loop), prints the description, and then enters the snap loop. It never processes the resulting outcome the way the in-game path does: a return touchdown does not run the try and kickoff sequence, and a return safety does not run the safety free kick, so the resumed game asks for a snap from the wrong state. The ordinary loop handles those cases through the touchdown and safety branches after `display_play_result`. README documents resumed saves preserving the pending decision, so this path is reachable whenever a player saves during the choice and reloads.

## Resolution / verification

- Add a failing regression that restores a saved pending decision whose chosen return is a touchdown (and a second whose return is a safety) and asserts the try/kickoff or free kick follows the ordinary sequence, using synthetic public-2026 fixtures and no real extra dice.
- Route the resumed outcome through the same scoring-sequence handling as the in-game loop instead of only printing and continuing.
- Confirm with a CLI play test that saving during the choice, reloading, and choosing a return touchdown resumes into the try and kickoff.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-14 15:40 ---
Fixed the resumed end-zone interception branch in `resume_game`. After the
choice is resolved, a return touchdown now uses `_complete_touchdown_sequence`
and a return safety uses `handle_safety_free_kick`, matching the live loop
instead of printing the return and entering the snap loop.

Tests first: the new `tests/test_resume_pending_end_zone_flow.py` saved a real
pending decision on public 2026 charts, loaded it, and restored synthetic return
cells. Both tests failed against the unchanged implementation because the
resumed branch skipped the try and kickoff after a return touchdown and skipped
the free kick after a return safety. Both pass with the shared follow-up path.
No existing expectation was weakened. Focused adjacent suites passed: 221 tests.

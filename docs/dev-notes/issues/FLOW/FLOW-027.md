---
id: FLOW-027
title: Resumed saved end-zone interception prints its return but skips the try/kickoff or safety free kick
status: open
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at:
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

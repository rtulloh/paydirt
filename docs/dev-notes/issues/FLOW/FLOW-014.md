---
id: FLOW-014
title: Save game gives no visible success or failure feedback
status: closed
priority: Medium
created-at: 2026-11-06
resolved-at: 2026-11-06
closed-at: 2026-11-06
tags:
  - reproduced
  - play-test-reproduced
---

## Description

SAVE GAME calls the browser store but ignores its boolean result. Both a
successful save and a storage failure leave the screen unchanged. The owner
reported that the button did not respond; read-only inspection confirmed the
current position and all 27 displayed history entries were actually saved.

## Resolution / verification

The playing screen now shows an accessible success status or failure alert
using the store's actual result. A successful retry replaces the failure.
Storage behavior and game state are unchanged.

Two mounted regressions failed for the expected absent messages before the
production change; their preceding assertions confirmed that real storage
success/failure already worked. Both pass after the fix, including exact
position/history persistence, retained open game and a successful retry after
storage throws. The full frontend suite passes 308 tests, no skips; the build
passes with the existing stale Browserslist warning. Documentation describes
the messages and browser-local scope of the save.

## Comments

--- 2026-11-06 12:56 ---
Independent Chromium play-test on the updated isolated review service (8154)
executed a real Blitz play, saved its resulting position and two displayed
history entries, and observed the success status with zero page errors.
Raw local reports are ignored under `.ai-audits/release-readiness/`.
The owner's existing game/service on 8152 was not restarted or modified.
This local fix remains uncommitted and unreleased.

The two complete browser games also verify the rendered success status and
the exact stored game ID, clock and field position. Both pass, including
all six defensive formations, halftime and final-score screens. Storage
failure/retry remains covered by the dedicated synthetic browser-storage test.

--- 2026-11-06 13:38 ---
The owner independently confirmed the save message after its placement was
corrected. New phone-viewport regressions first failed on both offense and
defense because the existing message fell below the visible window; both now
pass with the status fixed inside the viewport after scrolling to the top.
A separate real Chromium check of the built service on 8156 confirms the save
message is inside a 900px viewport, the checkpoint is actually written, and
there are no page errors. Close on this issue-specific browser and owner
confirmation, not unit tests alone. The local fix remains uncommitted and
unreleased. This ticket addresses feedback; complete engine-state restoration
is not asserted by browser checkpoint persistence.

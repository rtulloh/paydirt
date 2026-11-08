---
id: FLOW-015
title: Browser play log shows raw seconds and attributes half-ending plays to the next period
status: resolved
priority: Medium
created-at: 2026-11-06
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - play-test-reproduced
---

## Description

The log displays raw seconds such as `Q2 41"` and `Q3 900"`. Its normal-play
entry mixes starting down/position with the post-play clock, so a play exhausting
the first half appears to start in the third quarter at 15:00.

## Resolution / verification

Render recorded seconds as minutes:seconds, including zero and absent values.
For new scrimmage entries, copy the starting clock from the same server-supplied
state used for starting down and position. Keep the updated scoreboard clock and
new position from the result. Saved history is reformatted without inventing
unrecorded starting times.

## Comments

--- 2026-11-06 13:23 ---
Six formatting and four mounted execution regressions failed before production
changes, with eight passing display controls. All pass after the local fix,
including either controller and both ordinary plays and halftime transitions.
Modifier help also spells out Timeout and Out of bounds, spaces keyboard hints,
and provides effect/cost/shortcut tooltips. Four new help regressions failed
before the change; existing selector expectations were updated only for the
requested text changes, retaining selection, budgets, disabled controls and
request-payload assertions. No gameplay rule or stored history is rewritten.
Keep open until browser confirmation of the updated display. The development
review banner was removed from the owner's current page without a reload.

--- 2026-11-08 16:36 ---
Completed-work reconciliation: Clock formatting/start-state changes exist, but the ticket requires issue-specific browser confirmation of half-ending log attribution. Generic passing browser games do not assert that display detail.
See the [full review](../../open-issue-reconciliation-2026-11-08.md). No status or acceptance criterion changed.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Clock formatting and preplay-clock attribution are committed; issue-specific half-ending log browser confirmation remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

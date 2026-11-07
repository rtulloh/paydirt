---
id: FLOW-015
title: Browser play log shows raw seconds and attributes half-ending plays to the next period
status: open
priority: Medium
created-at: 2026-11-06
resolved-at:
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

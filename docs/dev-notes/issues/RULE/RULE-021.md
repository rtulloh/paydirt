---
id: RULE-021
title: Matching second-possession field goal incorrectly ends modified sudden-death overtime tied
status: closed
priority: High
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: 2026-11-01
tags:
  - reproduced
  - regression-test
links:
  - DATA-006
---

## Description

During the regenerated 2024 Hard replay at base seed `232422`, Denver answered
Kansas City's first-possession overtime field goal in an AFC Wild Card game. The
score became 19–19 with 1:54 remaining, but `check_overtime_score()` ended the
playoff game immediately. The replay correctly rejected the tied final.

In modified sudden death, the matching response field goal completes each team's
initial possession and moves the game into true sudden death. It does not end a
tied game. The implementation treated every score after the first possession as
a winner without checking whether the score created a lead.

## Resolution / verification

After both teams have possessed the ball, end overtime only when the score is no
longer tied. Preserve first-possession touchdown and ordinary winning-score
behavior. Confirm with the focused unit regression and the exact failed 2024
playoff seed before closure.

## Comments

--- 2026-11-01 17:55 ---
Added a failing regression for a 19–19 matching response field goal, then changed
`check_overtime_score()` to continue while tied. The focused overtime and auto-game
flow suites pass. Awaiting the exact replay confirmation.

--- 2026-11-01 18:05 ---
The exact failed Hard replay (`232422`, playoff game seed `232694`) now continues
past the matching field goal and completes all 272 regular-season and 13 postseason
games with Baltimore champion. No playoff final is tied. This is the requested
issue-specific engine play-test confirmation, so the ticket is closed.

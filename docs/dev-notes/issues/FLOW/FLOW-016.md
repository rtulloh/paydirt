---
id: FLOW-016
title: Penalty dialog invents midfield and incorrect enforcement previews
status: open
priority: High
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - play-test-reproduced
---

## Description

The owner saw an incomplete pass from the opponent's 23, third-and-nine,
offered as "No gain → OWN 50" when declining an offensive five-yard foul.
The acceptance preview incorrectly showed fourth-and-four. The frontend
falls back to a missing line-of-scrimmage value of 50 and independently
calculates enforcement/down/distance. Its offended-team subheading is also
inverted. These are display defects: the core's existing decline leaves
fourth-and-nine at the original spot; acceptance replays third-and-fourteen
five yards back.

## Resolution / verification

The engine now projects ordinary scrimmage results using shared state and
penalty helpers. Existing API fields already carry the resulting text.
The dialog displays those previews and removes guessed field positions,
down/distance, and touchdown calculations. Legacy responses without previews
use their retained description and penalty-option descriptions instead.
No new dice, clock, statistics, or enforced rule change is introduced.

## Comments

--- 2026-11-06 13:30 ---
Twenty public-fixture engine preview regressions failed before the change,
with two passing controls confirming that actual incomplete-pass enforcement
was already correct. Preview tests compare both choices with actual engine
decisions for either possession, incompletions, gains, losses, first downs,
and turnover on downs, while rejecting any preview dice use or state mutation.
Two mounted UI regressions failed alongside 27 passing controls; they reject
fabricated midfield, stale third-down text and the inverted offended heading.
Existing UI expectations that inferred a touchdown without engine confirmation
were corrected; yardage fixtures now supply their engine descriptions/previews
instead of relying on frontend rules. The owner's pending decision was not
submitted or changed during investigation. Keep open pending updated-service
play-test confirmation.

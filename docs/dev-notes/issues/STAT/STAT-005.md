---
id: STAT-005
title: Latest game reports one more accepted penalty and fifteen more yards than its narrated enforcements
status: open
priority: Medium
created-at: 2026-11-02
resolved-at:
closed-at:
tags:
  - investigating
  - audit-evidence
---

## Description

The latest completed manual game reports four accepted home-team penalties
for 45 yards. The visible enforcements account for three penalties for 30:
one ten-yard scrimmage foul, one fifteen-yard kickoff-return foul at the
second-half kickoff, and one five-yard kicking-team foul followed by a
re-kick. The away team's three accepted penalties for 22 effective yards
reconcile, including both half-distance assessments. Two declined scrimmage
fouls correctly appear separately from accepted totals.

The extra home-team fifteen-yard charge is unexplained. This is evidence
of an accounting-versus-narration discrepancy, not yet proof of duplicate
statistics, a particular offending function, or a missing live foul.

## Resolution / verification

Inspect per-event penalty-stat deltas through the actual interactive lifecycle,
including halftime, return chains, pending decisions, and re-kicks. Preserve
the original local log unchanged. No captured complete RNG state/build exists,
so do not invent missing rolls or claim an exact full-game replay.

A read-only public/synthetic replay of the visible return foul alone charges
one penalty for fifteen yards and produces the correct receiving spot.
A separate kick-chart/re-kick reproduction charges one penalty for five
yards. Neither isolated case reproduces the unexplained extra fifteen yards.
Write a failing self-contained regression once the faulty lifecycle or lost
evidence is established, before making a production fix.

## Comments

--- 2026-11-02 10:15 ---
Final and halftime tables, all displayed scrimmage decisions, and all
kickoff/return traces were inspected. The halftime home total is one for
ten; the visible second-half additions are fifteen and five. Other principal
yardage, sack, first-down, turnover, and score totals reconcile independently.
Keep this discrepancy separate from the older punt-double-foul omission.

--- 2026-11-02 10:50 ---
Two passing public lifecycle controls include the first-half scrimmage foul,
halftime return foul, later accepted kickoff foul/re-kick and repeated stale
decision. They reconcile to three accepted fouls for thirty yards on either
side. A separate 64-game public audit reconciles 576 narrated scrimmage
penalty increments; it is not an exact replay or complete special-teams
accounting oracle. The uncaptured manual game's extra fifteen yards remains
unexplained. No statistics mutation is changed without a causal failing
regression. Keep open; do not report this investigation as a fix.

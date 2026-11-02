---
id: DATA-015
title: Assess whether sparse symbolic passing touchdowns improve calibrated generated charts
status: open
priority: Low
created-at: 2026-11-02
resolved-at:
closed-at:
tags:
  - deferred
  - calibration
links:
  - DATA-011
---

## Description

Generated charts preserve observed scoring yardage. Original developer charts
also contain sparse symbolic passing touchdowns, whose placement is not
explained by a source touchdown-rate threshold. Adding guaranteed scores
without evidence risks restoring the field-position error fixed by DATA-009.

## Resolution / verification

Separate this optional modeling experiment from the implemented DATA-011
tuning tool. Compare bounded sparse passing-TD candidates against numeric-only
charts using matched training and held-out schedules, seeds and coaching
policies. Require a measured improvement in engine scoring and efficiency
without introducing field-independent rushing TDs or hidden source assumptions.
No symbolic-TD adjustment is part of the current profile or release claim.

## Comments

--- 2026-11-02 10:50 ---
Recorded the intentionally deferred experiment already described in DATA-011
and the generation workflow. This is not a newly demonstrated gameplay bug.

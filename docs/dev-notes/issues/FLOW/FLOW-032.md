---
id: FLOW-032
title: Hail Mary end-zone interception deferral uses ordinary scrimmage timing
status: open
priority: Medium
target-release: v1.10.6
created-at: 2026-11-14
resolved-at:
closed-at:
tags:
  - code-review
links:
commits:
---

## Description

Found in the 2026-11-14 review of the FLOW-028 Hail Mary deferral fix. A Hail Mary own-end-zone interception that is deferred for the ask choice finalizes through _apply_play_result, which uses ordinary scrimmage timing of 25-45 seconds. Immediate Hail Mary resolution uses 5-15 seconds in _handle_hail_mary. Merely changing the policy from touchback to ask, then choosing touchback, can therefore consume extra time and incorrectly end a half or game. Verified with identical synthetic interceptions: the deferred path requests random.uniform(5,15) versus random.uniform(25,45).

## Resolution / verification

- Add failing-first public/synthetic regressions comparing immediate and deferred Hail Mary interception timing under identical synthetic dice. Preserve the originating play's timing semantics across deferral, including touchback and return resolution, while retaining one-time clock, possession, scoring and statistic application. Run focused Hail Mary/interception/clock suites and update this ticket with evidence.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

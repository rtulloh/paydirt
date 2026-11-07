---
id: DATA-043
title: Audit play-specific interception spot support in generated passing charts
status: closed
priority: Medium
created-at: 2026-11-07
resolved-at: 2026-11-07
closed-at: 2026-11-07
tags:
  - investigating
  - cross-project
---

## Description

The owner reports a confirmed Bowl Bound generator defect: an OSU offense Screen
cell yields INT 44 because interception distances were pooled across passing
plays without sufficient play-specific constraints. That separate project's
finding is user-reported here, not independently reproduced in Paydirt.

A read-only scan of all 60 shipped Paydirt offense charts finds no INT 44 Screen
cell. Interception spot labels in the Screen column range from 5 to 12 for
1983 and are 5 for 2024. These are cell-label observations, not complete weighted
or terminal-outcome validation, and do not establish sensible support by themselves.

Paydirt has a related modeling risk: the aggregate baseline passing generator
uses the same INT 5/12/20 choices across passing columns. Empirical calibration
prefers baseline interception labels when present. Defense uses fixed
call-specific interception spots. Source reproducibility and aggregate INT-rate
fit therefore do not establish play-specific interception-spot fidelity.

## Resolution / verification

Audit offense and defense interception spots across every team, pass type and
formation, including reachable priority outcomes and physical probability mass.
Distinguish interception location from subsequent return distance. Trace emitted
labels to source-supported play types, explicit modeled fallback and calibration.
Check source classification and sparse/absent interception samples before
assuming cross-play pooling is the cause. Do not impose an arbitrary universal
Screen cap or silently alter rates, event mass or outcomes.

If a Paydirt defect is demonstrated, add synthetic/public-2026 regressions first
for mismatched play types, sparse samples, preservation of valid source evidence
and separate return yardage. Fix the demonstrated allocation path, disclose any
modeled support, and compare final chart distributions and engine behavior.
No production change or chart regeneration is authorized by this investigation.

## Comments

--- 2026-11-07 16:02 ---
Opened after the owner's Facebook cross-project report. Read-only inspection of
chart_generator.py, its empirical calibration and both shipped offense cohorts
establishes the narrower Paydirt observations above. No claim that Bowl Bound
and Paydirt share code or the exact same defect; no new acceptance bound adopted.

--- 2026-11-07 16:25 ---
Completed the all-60-team weighted offense/defense and reachable-priority
census for all five pass calls and six formations. Screen support is 5/12 for
1983 and 5 for 2024; no reachable INT44 Screen exists. Returns remain separately
measured. Synthetic controls preserve a deliberately supplied INT44 (no arbitrary
cap), independent long-pass evidence, competing shorter INT, penalty precedence,
team identity and exact physical mass. Both public cohort/decoder audits pass.
Source review finds per-event pass classification before grouping in both
adapters, not a shared cross-play depth pool. Aggregate INT5/12/20 and defensive
5/5/12/18/8 are modeled; calibration can prefer baseline depths over empirical
ones. This limitation is now explicit in the maintained guide and reusable
`structure.interception_spots` report. No demonstrated impossible-support defect
justifies altering spots/rates or regenerating charts in this release. Close the
bounded audit with that outcome, not a claim of empirical depth fidelity or a
Bowl Bound fix. See ../../release-1.10.2-scope.md for source trace, complete support
sets and unchanged chart/mechanics scope.

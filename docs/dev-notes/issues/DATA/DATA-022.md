---
id: DATA-022
title: Generated defense interception floor overwhelms low-risk quarterback inputs
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
links:
  - DATA-040
---

## Description

The neutral defensive template contributes 17/560 (3.0357%) joint interceptions
per selected primary passing call under the declared normal reference mix. The
offense generator subtracts only a .006 defense allowance. INT cells on physical
subrows three/four survive the row-five-only strength removal, creating a floor
that global offensive INT offsets cannot reduce. Existing empirical profiles
clamp offensive INT mass to zero, erasing meaningful quarterback risk variation.
The official interception denominator is counted pass attempts, which is a
separate engine measurement; the joint primary-call probability is not that rate.

## Resolution / verification

Two new synthetic controls fail against the old generator: neutral template
mass exceeds its offense allowance, and interceptions occupy high-mass subrows.
Normalize neutral interceptions to rare row-five Short Pass/Long Pass benefits,
retain coverage as BLACK where turnover mass is removed, and preserve ordered
defensive strength with low-mass additions/removals. Independent low/neutral/high
QB controls against the same defense reject a calibration that erases risk.
Complete protected Screen overrides remain explicitly disclosed controls.

One existing expectation changes: strong Short Pass interception mass was 4/36,
including a hidden 3/36 template floor. It now requires 1/36 and retains all
strength-order and maximum-increment assertions. This is an intended model
allocation correction, not a source claim about historical formation rates.
Verify final all-team fit, tactics, stateful controls and policy stress before
review; keep open while uncommitted and unconfirmed by final play testing.

## Comments

--- 2026-11-05 19:13 ---
Found during source-cleared 2024 calibration under the chart-confidence charter.
Official targets and fixed league/team tolerances remain unchanged. The old
negative INT offset cannot repair a defense-origin floor; tuning continues only
in ignored candidates, with held-out master 20361108 unopened.

--- 2026-11-05 20:31 ---
Training-only exact diagnostics separate denominators. Across 2024 defenses,
canonical numeric-offense INT contribution ranges .01827–.03573 per selected
primary passing call before correction, versus 0–.008075 in trial02. With actual
offenses against a uniform cohort defense mixture, joint INT ranges .02580–.02631
(old, nearly erased QB spread) versus .001995–.02784 (trial02). Dividing by
potential pre-state attempts gives .02982–.03358 versus .002438–.03268; that
denominator excludes pending penalties/QT and is not final credited attempts.
Observed engine INT/credited-attempt ranges are .01925–.04234 versus
.002615–.04367, with different finite training samples, not a confidence claim.
Fumbles, protected overrides and state/penalty choices qualify any floor.
Detailed local report: `.ai-audits/chart-confidence/int-pressure-diagnostics.json`.

--- 2026-11-06 06:59 ---
The parent-requested all-60 formation-risk census finds no BB-style repeated risk
template across A–F. Exact priority/B/QT controls cover 6,480 distributions; every
passing team/call has 3–6 distinct risk vectors against constant-10 offense and
4–6 against the same-team actual offense, alongside numeric tradeoffs. Real-engine
controls complete 97,200 weighted branches across three field positions and first/
fourth down; all 3,240 midfield kind comparisons reconcile and 34 separate observer
branch checks pass. See [formation risk census](../../formation-risk-census.md).
Actual-chart penalties/recoveries/returns remain explicit pending probability,
not certified terminal risks. This does not establish historical formation truth,
final fit or closure of the interception-floor issue. No chart/model/bound change.

--- 2026-11-06 19:32 ---

The owner's broader repeated-row request is now audited in the [generated defense
pattern census](../../generated-defense-pattern-census.md): all 270 cells of each
team across 209 separately identified cohorts, 6,210 team artifacts and 319 unique
defenses. Independent CSV/hash verification passes all 1,676,700 cells and 6,416
bindings. Old 1983 Short Pass row-five INT5 occurs in all six formations for 23/28
teams; the newer 1983 candidate removes that stripe but has an all-formation
Screen INT5 stripe for Cardinals, Chiefs, Redskins and Steelers. Current modern
candidate02 has neither stripe. All INT cells in both newer candidates remain
on the 1/36 subrow; fixed depth support and broader template repetition remain.
Real-resolver ordinary-10 controls retain 5–6 full formation distributions in all
319 unique defenses. This does not contradict earlier full-risk contrast: one
shared interception component can repeat while other outcomes differ. No chart,
source target, tolerance or policy changes; final fit/play-test closure remains
pending. The resolved tracker was reviewed without new closure evidence.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Neutral interception-floor correction and low-mass strength ordering are committed; final fit/stress confirmation remains pending, with depth/stripe model limits retained.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

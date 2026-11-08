---
id: DATA-043
title: Prevent cross-play interception spot allocation in generated passing charts
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

The owner reported a Screen INT44 defect in Bowl Bound and requested preventive
play-specific semantics in Paydirt. Paydirt's PFR heuristic also reproduces the
allocation defect: a known 44-yard interception is placed in Screen in 56/1,000
seeds because catch depth uses completion/YAC weights. Aggregate passing models
also share INT5/12/20 labels across calls, calibration prefers those baseline
labels, and missing locations use an unrelated INT10 default. The initial
absence of INT44 in the shipped Screen charts did not establish correctness.

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
The owner explicitly authorizes a preventive generator fix, synthetic regressions
and reviewed regeneration of affected public generated charts. Release remains
blocked until the semantic allocation defect is fixed and validated.

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

--- 2026-11-07 16:43 ---
Reopened after owner clarification: the prior audit-only closure did not meet the
requested preventive behavior. A synthetic unknown-call pass intercepted 44 yards
downfield is assigned to Screen in 56 of 1,000 seeds by the PFR completion/YAC
classifier. A known interception spot is air depth, not completion net gain.
Regression-first work now constrains inferred calls using the existing nflverse
depth taxonomy, removes the pooled aggregate INT5/12/20 labels, adds per-call
missing-depth/calibration support, and enforces final generator support. Explicit
source-supported call/depth combinations remain distinct from inferred support.
The earlier absence of INT44 in shipped Screen cells was insufficient evidence.

--- 2026-11-07 16:51 ---
Implemented preventive constraints after 32 failing behavioral regressions and
five passing controls; all 37 new and 218 existing generator/source tests pass.
Known inferred INT depths use the shared air-depth taxonomy (<=0 Screen, 1–9
Short, 10–19 Medium, >=20 Long), preserving explicit Screen source evidence and
completion YAC. Missing/aggregate support is call-specific 5/5/12/20/8; sparse
positive calibration preserves INT event mass. Final offense/defense generation
rejects newly pooled support outside that call's modeled or declared source set.

Both frozen-gain source replays preserve source games/rows/FG/fumble totals.
Full requantization produced small unrelated event-mass drift, so it was not
adopted. The released reviewed output instead applies a deterministic INT-only
migration: 151 cells/28 teams in 1983, 108 cells/30 teams in 2024. Every physical
row, event probability and non-INT cell stays identical; defense/special/team
files and reviewed gain factors remain unchanged. Compact public manifests bind
the baseline source proof and migration receipt without exporting private data.

All 60 teams pass structure, exact-mechanics and decoder checks; all five calls
and six formations pass source/model support and weighted reachable census.
Final reachable sets: Screen5, Short5, Medium12, Long18/20 (plus24 modern),
TE8 (plus24/25 modern). Thirty complete real-engine games cover every team with
valid scoring, termination and selected-call accounting. This closes the
preventive allocation defect, not historical catch-depth fidelity or every rare
source-supported observation. Evidence remains ignored under
.ai-audits/release-readiness/v1.10.2/data043/; maintained semantics are in
../../../chart-validation.md and ../../release-1.10.2-scope.md.

--- 2026-11-07 17:12 ---
Follow-up caller review found the physical-allocation audit still invoked the
new call-specific pass model without naming its synthetic 15-yard Medium profile.
A new public-only regression fails on the unchanged caller and verifies all five
modeled profiles through the real allocation audit. The named-profile fix passes
all 49 allocation/policy cases in 13.40s. A clean tracked-only snapshot
also passes all 444 allocation/policy/documentation/tracker cases in 14.34s. This corrects the validation caller,
without changing generated charts or gameplay; the running hosted coverage job
is retained until completion before the corrective push.

--- 2026-11-07 18:08 ---
The preserved hosted baseline completes with 10,875 passes and five failures:
four allocation-audit callers missing the new profile argument, plus one old
layout fixture injecting INT5/INT12 into every aggregate passing baseline.
The latter violates the new contract and is correctly rejected; production does
not emit that combination. Its intended mixed-token layout case now enters via
explicit synthetic empirical call attribution and real quantization. A boundary
spy captures pre-allocation cells; every existing exact full-token mass, protected
auxiliary/BLACK and cost assertion remains unchanged, with an added assertion
that both source variants reach every call. A new passing control proves the old
undeclared aggregate injection remains rejected. Baseline reproduction: the old
case fails as expected and the guard control passes; no invariant is relaxed.

Corrected primary/allocation/policy/cache checks: 105 pass in 81.96s;
documentation/tracker: 395 pass. Clean tracked-only failing-case/caller/cache/
documentation coverage: 418 pass in 13.46s. Ruff passes. No existing assertion
is weakened and no production change is needed for this source-fixture correction.

--- 2026-11-07 19:22 ---
Release verification: v1.10.2 is published from 10d7130, with all 10,893 core
regressions and both committed-chart cohort checks passing. The prior four
allocation-audit failures shared one caller missing the required profile name.
All five release assets match successful platform builds and API hashes; see
../../release-1.10.2-scope.md for identities and retained limitations.

# Generated chart accuracy and release audit

Investigation and locally implemented gate, 2026-11-05. **Current generated
cohorts fail.** No chart data, generator algorithm or gameplay engine rule was
changed to make this audit pass. Nothing was pushed or released.

The subsequent owner-authorized correction and validation work is governed by
the [chart confidence agent charter](chart-confidence-agent-charter.md).

## Scope and outcome

All 60 promoted public-generated teams were examined: 28 in `1983-generated`
and 32 in `2024`. Public 2026/synthetic fixtures supply unit controls. Imported
private historical charts were excluded. This extends the
[initial similarity audit](generated-defense-similarity-audit.md), which
established uniqueness but could not establish weighted tactical accuracy.

Four independent checks now form a [release gate](../chart-validation.md):
source consistency, weighted tactics and stateful controls, allocation fidelity,
and fresh full-engine calibration. Both CI workflows run the gate; release
builds depend on it. Missing/failed components, stale engine evidence and short
samples cannot certify a release. Negative tests deliberately inject defects,
including differently arranged charts with identical weighted distributions.

## Confirmed blockers

1. **Sparse empirical allocation is not always nearest attainable.** A 0.5%
   interception target can become zero even when a mass-2 physical row is closer.
   The independent oracle rejects final output at all three tested seeds.
   [Allocation evidence](generated-event-allocation-audit.md),
   [DATA-016](issues/DATA/DATA-016.md).
2. **Classified source events disagree with official totals.** 1983 extraction
   has 629 interceptions versus 620, 1,207 sacks versus 1,215, and 775 field-goal
   attempts versus 771. 2024 has 1,306 sacks versus 1,314. Reconciliation has not
   been established. [Source evidence](generated-source-consistency-audit.md),
   [DATA-017](issues/DATA/DATA-017.md).
3. **Selected fumble priority can be overwritten during result classification.**
   Priority selects `F + 2` over defensive `INT 5`, but the resolver can classify
   the selected fumble as an interception because a raw cell contains `INT`.
   [RULE-026](issues/RULE/RULE-026.md). Calibration must be rerun after its fix.
4. **Current full-engine accuracy misses source tolerances.**
   [DATA-018](issues/DATA/DATA-018.md) tracks this separately from playable games
   and reproducible chart files.

The owner's subsequent visual review triggered a focused
[Dolphins offense black-cell trace](generated-offense-black-cell-audit.md).
It reproduces the displayed data exactly, separates visible row counts from
physical probabilities, and traces modeled event rates and large conditional
gains. This does not certify the generated chart as more faithful than the
developer reference.

## Fresh full-engine evidence

Two observer defects were corrected test-first before the final run:
[QT-fumble classification](issues/DATA/DATA-019.md) and
[nullified offsetting plays](issues/DATA/DATA-020.md). Eight stateful controls
now pass, including retained-play controls. All per-team and league denominator
identities reconcile over the final complete samples. Earlier affected reports
were archived as stale and cannot certify a release. The table below uses only
the final corrected-observer evidence.

The explicit chart-focused policy ran 64 actual regular-season schedules per
cohort, independently seeded: **31,744 completed games** in total. Every 1983
team has 1,024 team-games; every 2024 team has 1,088. Engine/policy and chart
fingerprints, complete team samples, raw-total reconciliation, schedule and
finite derived metrics are checked before calibration can pass.

| Cohort / metric | Observed | Source target | Absolute tolerance | Result |
| --- | ---: | ---: | ---: | --- |
| 1983 completion | 53.58% | 56.90% | 1.5 percentage points | Fail |
| 1983 interception | 4.28% | 4.41% | 1 percentage points | Pass |
| 1983 sack | 7.60% | 7.96% | 1 percentage points | Pass |
| 1983 passing yards/attempt | 7.84 | 7.18 | 0.25 | Fail |
| 1983 rushing yards/attempt | 4.07 | 4.09 | 0.15 | Pass |
| 2024 completion | 61.95% | 65.29% | 1.5 percentage points | Fail |
| 2024 interception | 3.26% | 2.17% | 1 percentage points | Fail |
| 2024 sack | 7.15% | 6.87% | 1 percentage points | Pass |
| 2024 passing yards/attempt | 7.95 | 7.13 | 0.25 | Fail |
| 2024 rushing yards/attempt | 4.40 | 4.44 | 0.15 | Pass |

The tolerances were reused from the existing calibration criteria before these
measurements, not selected to fit them. Masters are 20261106 (1983) and 30261106
(2024); the runner adds 1,000,003 per repetition and 1,009 per scheduled game.
Aggregate evidence remains in ignored `.ai-audits/chart-release-audit/`.

The previous ignored batch helper defined `ChartFocusedAI` but instantiated
`ComputerAI` in its factory. Its old policy label therefore does not establish
that the declared fixed mix was used. The new tracked runner actually
instantiates the explicit policy, with Hard available as separate diagnostics.
Changes in policy and engine prevent attributing the new deltas to one cause.

## What is supported and what remains uncertain

Independent source regeneration reproduced **180/180 CSVs byte for byte**.
That supports reproducibility, not correctness of source extraction or modeling.
The manifests disclose heuristic 1983 pass-depth classification, unclassified
plays, missing annotations and modeled event rates. Reviewed contracts retain
public aggregate facts, source/CSV hashes, schedules, profiles and attribution;
they contain no raw PBP or imported private charts.

Paydirt has a nonzero defensive template and its controlled engine results show
real formation tradeoffs. It does not reproduce BB's universal neutral-profile
failure in those controls. Uniform appearance still reflects a shared limited
model; exact chart-resolution tests cannot establish historical coverage tactics,
special-team accuracy, scoring/pace fit or realism of missing-source defaults.
Conditional known-gain comparisons keep interceptions, touchdowns and unknown
branches separate. Complete games alone cannot substitute for those distinctions.

Review and fix the recorded blockers test-first, then regenerate and rerun the
gate. Resolved-ticket review found no new scenario-specific play-test evidence
for unrelated closures. DATA-004 remains closed for its original compression
defect; DATA-011 retains its current-engine calibration caveat. This audit does
not replace the mandatory full pre-push regression or private integration suite.

## Final validation

Both complete gate commands exit 1 as intended. Source fails with seven findings
in 1983 (three league discrepancies plus four team FG discrepancies) and one
in 2024. Allocation fails three sparse controls; priority resolution fails nine
controls. All 60 team tactical controls and the synthetic strength-order controls
pass; current-engine calibration fails two metrics in 1983 and three in 2024.
The gate preserves those independent findings rather than replacing them with a
single generic failure.

The full core suite passes **6,915 tests**, with **eight existing skips**, all
conditioned on missing 1972 data (roster 1, team discovery 2, season rules 3,
legacy extra-point encoding 2). No skip was added. These legacy fixture
dependencies are tracked in [VAL-010](issues/VAL/VAL-010.md), a cleanup item under the synthetic/public-only unit policy.
Ruff, documentation/tracker checks and whitespace checks pass. No push or full
private integration/AI regression was performed; the new gate is deliberately
blocking current release acceptance.

Test-first baselines cover ignored component failures, missing evidence,
weighted-equivalent formations, erased strength, allocation corruption, stale
reports, impossible denominators and phantom offsetting plays. The corrected
observer leaves all gameplay rules and chart bytes unchanged. Confirmed findings
and game-specific BB feedback are maintained in the
[cross-project note](college-chart-tactics-cross-project-findings.md).

Final engine/policy fingerprint: `e6559e10f102c1e973b4d0b94f6c3c35b4271cf2d7a7d0a421ac0ecb09e5e671`.

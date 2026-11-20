---
id: DATA-051
title: Add team field-goal distance-band calibration and qualification to chart generation
status: open
priority: Low
target-release:
created-at: 2026-11-19
resolved-at:
closed-at:
tags:
  - chart-review
links:
commits:
---

## Description

Owner-observed game: Philadelphia away CPU on Hard leads San Francisco 16–10, Q4 05:17, fourth-and-15 at the San Francisco 22, under 1983 rules. The CPU chooses a punt. A read-only reproduction with public 1983 charts and the normal Hard AI factory confirms the call. The engine gives the Eagles a field-goal make probability of 1/3 at 22 yards from the line of scrimmage to the goal line (a statistical 39-yard attempt). This falls below the AI's 0.35 worth-taking threshold. The owner accepts the AI's decision on those game-chart odds and requests investigation of the chart probability instead; no AI change is requested and no chart defect is yet established.

The existing discrete chart maps LOS distance 20 (statistical 37 yards) to approximately 0.502564, while LOS distances 21–24 (statistical 38–41 yards) each map to 1/3. These are exact chart-weighted engine probabilities, not historical distance-band percentages.

The [official Eagles 1983 statistics](https://media.eagles.1rmg.com/wp-content/uploads/2020/03/28183857/1983_statistics.pdf) lists Tony Franklin at 15/26 overall (57.7%): 6/9 from 30–39 yards, 2/8 from 40–49 and 1/3 from 50+. The 30–39 band contains only nine attempts and cannot establish his true probability specifically at 39 yards. A difference between that small observed band and the discrete game chart is a review question, not automatic evidence of a generation bug or a reason to hand-tune the Eagles.

The core's 1983 ordinary unreturned, unblocked missed kick from this spot gives the opponent its own 22; a punt touchback gives its own 20. A made field goal increases the lead to 19–10. Actual punt placement, returns, blocks and fouls can differ. This context does not establish an optimal decision or a measured win-probability gain.

Keep this neutral chart investigation separate from AI policy defects. DATA-046 concerns a different, 1977 interception/scoring qualification issue and is not evidence for this 1983 kicking question.

## Proposed calibration stage — owner direction, 2026-11-20

This is now a chart-generation/calibration improvement, extending the completed
probability audit below. The owner withdraws the fixed-distance coaching proposal:
keep the AI probability-based, with its existing situational policy. Do not add an
inside-the-25 override or tune charts to force the reported punt into a kick.
This proposal is not implemented and does not change the verified v1.12.2 release.

### Inputs and targets

- Reconcile team-season field-goal makes/attempts for **1–19, 20–29, 30–39,
  40–49 and 50+ statistical kick yards**, including all kickers who contributed.
  Individual-player statistics remain outside the game UI scope.
- Preserve source identity, counts, distance convention, era and accounting of
  blocked kicks, penalties/no-plays and aborted snaps. Reconcile band sums to
  official team totals. An aborted snap without an official attempt is not an FGA.
- Prefer verified exact attempt distances within each band when available. With
  band-only sources, disclose the unknown distance mix and use an explicitly
  reviewed modeling/uncertainty policy; do not silently spread attempts uniformly
  or equate the band's observed percentage with every distance in that band.
- For sparse or zero-attempt bands, use a reproducible, declared era-appropriate
  pooling/prior policy and label the evidence limitation. Zero attempts is not 0%
  ability, and a perfect small sample is not certain success. Treat 50+ as an
  open-ended range with an explicit extrapolation policy; longest made alone does
  not establish zero probability beyond that distance. Mark distances the engine
  cannot represent separately rather than inventing coverage.

### Fit, realize and measure

1. Fit a coherent distance-dependent curve against the team's band targets and
   available exact-distance evidence. Preserve nonincreasing underlying success
   probability, allow era/team differences and avoid arbitrary band-edge cliffs.
   Statistical uncertainty and discrete chart resolution may prevent exact fits;
   retain and explain residuals rather than forcing historical game outcomes.
2. Generate the actual field-goal chart, then independently compute its realized
   engine-weighted probability at every supported distance. Qualification must
   measure the quantized chart, not just the smooth pre-chart target. Verify
   distance conversion, penalty rerolls, block/snap-event accounting and attempt
   denominators against the core resolver.
3. Produce a per-team/per-band report: sourced M/A and percentage, model target,
   realized expected makes/rate over the historical attempt-distance mix, error,
   sample/uncertainty, fallback/pooling, quantization residual and verdict. When
   exact distances are unavailable, report bounds or declared model assumptions;
   do not present a broad feasible envelope as proof of calibration. Include the
   exact-distance curve, boundary jumps, range support and overall reconciliation.
4. Add kicking as an explicit generation qualification stage alongside existing
   offensive/defensive calibration. Define reviewed sample rules, band/overall
   error criteria and uncertainty/quantization allowances before implementation
   experiments. Bind policy, sources, generator/profile, engine and chart hashes
   in the manifest/validation contract. Missing required evidence is insufficient
   qualification, not a pass; exceptions must be visible and reviewed.
5. Use controlled engine checks independent of coaching attempt selection to
   establish kicking ability. Then run full games/AI audits to assess interactions
   and termination. AI-selected attempts are a biased distance mix and cannot be
   the only calibration measure. Separate source-fit evidence used to fit the
   model from independent implementation/held-out validation where available.

## Resolution / verification

- Implement the proposed explicit team kicking calibration stage and report;
  preserve the probability-based AI. The earlier inside-the-25 suggestion is
  superseded, not a second implementation requirement.
- Use test-first synthetic/public-2026 fixtures for fitting, band reconciliation,
  sparse/empty/perfect samples, conflicting noisy bands, 50+ extrapolation,
  boundaries, distance conversion, protected event accounting and chart
  quantization. Demonstrate expected failures before production changes; include
  controls proving AI policy remains unchanged. Historical qualification remains
  standalone integration evidence, not collected unit fixtures.
- Retain the completed 1983/2024 Eagles investigation as a baseline and qualify
  the complete season cohort, not a hand-tuned Eagles exception. Publish remaining
  evidence limitations and actual failed bounds; choose no new numerical
  tolerances merely to make an existing chart pass.
- Preserve the unchanged released-chart regression route while chart bytes are
  unchanged. Regenerated charts require strict source/reproduction, applicable
  minimum-sample fit and full regression under the reviewed changed-chart policy.
  Existing 1977 rules/explicit exceptions remain in force; this new stage grants
  no waiver and does not overwrite immutable releases.
- Update generator/calibration/workflow and validation guides with implementation.
  Close only after test, independent realized-probability, cohort qualification and
  actual gameplay/audit evidence meet the agreed criteria.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 20:58 ---
Owner requested a tracked investigation after clarifying that the AI decision is acceptable if the game-chart chance is one-third. Current probabilities and the primary historical source were reviewed read-only; no released chart, policy, tolerance or production source was changed.

--- 2026-11-19 21:15 ---
The owner proposed a simplifying coaching policy: generally attempt a field goal
inside the opponent’s 25-yard line because a miss still leaves a long field.
Evaluate this as an alternative to changing chart data, not proof the existing
chart is defective. In the reported 1983 situation, an ordinary miss gives the
opponent its own 22 and a punt touchback its own 20; a punt can also pin deeper.
The policy should use the governing era’s missed-kick placement and preserve
situational decisions, including needing a touchdown late, clock/score, blocked
or returned kicks and other nonordinary outcomes. Define the exact 25-yard
boundary and exceptions before implementing; use test-first synthetic/public
fixtures and compare representative decisions. This is an owner-proposed
follow-up for review, not a change to this release’s AI or charts.

--- 2026-11-19 21:17 ---
The owner also requests a chart-generation calibration sanity check against the
actual season kicker’s field-goal record. Compare generated success probability
across distance bands with observed makes/attempts and retain the sample counts.
Use a loose, explicitly reviewed discrepancy policy that accounts for small
samples, chart discretization and distance mix; a band’s observed percentage is
not the probability at every exact distance. Flag material mismatches for review
with reproducible probability calculations and sourced historical summaries.
Check chart probabilities separately from AI attempt selection so playing style
does not mask a generation mismatch. Define the review threshold and source-bound
policy before implementation; do not silently change existing qualification
bounds or regenerate immutable released charts. Record any accepted exceptions.
This follow-up does not change this release’s charts or calibration acceptance.

--- 2026-11-19 22:49 ---
Completed a bounded, read-only review of the public Eagles charts for 1983 and
2024. All 198 LOS-distance queries match an independent successful-cell sum over
the 216 weighted dice combinations. Statistical distance is LOS-to-goal distance
plus 17 yards (10-yard end zone and seven-yard hold). Penalty rows are excluded
and renormalized; blocks/snap fumbles remain misses. This conditional chart
probability does not model full foul enforcement or AI decision quality.

The [official 1983 Eagles statistics](https://media.eagles.1rmg.com/wp-content/uploads/2020/03/28183857/1983_statistics.pdf),
page 1, reconciles Franklin's 15/26: 1/1, 5/5, 6/9, 2/8 and 1/3 in the
1–19, 20–29, 30–39, 40–49 and 50+ bands. The exact chart curve is:

| Physical kick distance | Make probability |
| --- | ---: |
| 18–33 | 191/195 (97.949%) |
| 34–37 | 98/195 (50.256%) |
| 38–47 | 65/195 (33.333%) |
| 48–52 | 48/195 (24.615%) |
| 53+ | 0% |

SF22 correctly means a 39-yard kick at one-third. The historical 6/9 covers the
whole 30–39 band, where this chart varies sharply; it is not nine 39-yard kicks.
No distance-conversion or probability-lookup error was found. Unknown exact
attempt distances permit a broad 10.85–18.10 expected-makes envelope for those
26 attempts; observed 15 lies inside. That does not prove calibration correct.

The [official 2024 Eagles statistics](https://media.eagles.1rmg.com/wp-content/uploads/2023/12/24145411/Statistics-2024-14.pdf),
page 2, reconciles Elliott's 28/36: 0/0, 9/9, 10/11, 8/9 and 1/7 in those bands.
Its chart gives 96.923% at 18–38 yards, 83.590% at 39–43, 80.513% at 44–50 and
zero at 51+. Its possible band-mix expected-makes envelope is 25.16–32.54, also
too broad to establish a defect. A band average is not an exact-distance chance.

Longest-made support was checked separately: [Franklin's official game log](https://www.nfl.com/players/tony-franklin-2/stats/logs/1983/)
records a 52-yard make at Washington on November 27; the [official Elliott career table](https://www.philadelphiaeagles.com/team/players-roster/jake-elliott/)
gives 2024 LNG 50. Both season-long makes are supported by their chart caps.
Both team PDFs reconcile the named kicker with the complete team total, so no
backup kicker is omitted. This does not establish a real-world zero chance one
yard beyond the cap. Current generator inspection finds monotonic pooling and
weighted row quantization that can create boundaries; this is not independent
reproduction of the released charts. Existing manifest exceptions concern 1983
completion rates and 2024 Ravens rushing YPA, not FG calibration.

Actionable follow-up remains in this ticket:

1. Reconcile a source-bound, all-kicker exact-distance ledger, including blocked
   and aborted attempts, before computing expected makes on the historical mix.
2. Report exact curves, breakpoint jumps and extrapolation policy with small-sample
   uncertainty and explicitly reviewed loose review flags. Avoid uniform-distance
   band averages or calibration inferred from AI-selected game attempts.
3. Keep the owner's inside-the-25 coaching proposal separate. No AI or chart bug
   is established by these two teams; no league-wide conclusion is warranted.
4. Preserve released chart bytes and current tolerances. Any confirmed generator
   defect requires failing synthetic/public-2026 regressions and strict changed-chart
   qualification; review flags are not new acceptance waivers.

Ignored reproducibility evidence: `.ai-audits/data-051-fg-calibration/` contains the
standalone script, hashed-code/primary-source receipt, all-query CSV and official
PDFs. No historical collected unit fixtures, chart/AI edits or threshold changes.
Keep DATA-051 open for the source-ledger/calibration-report follow-up.

--- 2026-11-20 06:21 ---
Owner directs a calibration-stage change using team 1–19/20–29/30–39/40–49/50+
field-goal ability, rather than a fixed-distance AI rule. Promoted this ticket
from a neutral probability investigation to the proposed generation/qualification
work above; historical findings remain unchanged. The generator already accepts
`field_goal_by_distance` and constructs a nonincreasing curve in
`paydirt/chart_generator.py`; `paydirt/chart_calibration.py` currently exposes
aggregate FGA/FGM/rate rather than this proposed band qualification. The new work
must assess the realized chart by band and carry evidence/uncertainty into the
qualification report. No production code, AI, chart data, thresholds or release
artifacts changed in this planning update. Keep open for implementation.

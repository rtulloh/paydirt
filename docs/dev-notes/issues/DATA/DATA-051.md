---
id: DATA-051
title: Review 1983 Eagles field-goal chart probability near a 39-yard attempt
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

## Resolution / verification

- Review the source-to-chart mapping, exact weighted kick resolution, distance convention and discrete boundary around the observed spot. Distinguish source/sample limitations, intentional modeling choices and actual implementation errors; retain provenance and denominators.
- Do not alter AI policy or unchanged released charts merely to change this call. Establish any concrete implementation defect with synthetic/public-2026-only failing regressions before production changes; historical chart checks remain separate integration evidence.
- Preserve the unchanged released-1983 regression route while chart bytes are unchanged. Any changed or regenerated charts must pass the strict source/reproduction and applicable minimum-sample fit qualification for new or changed charts, plus required full regression. Do not weaken tolerances, exclusions or mechanics checks, or relabel unchanged-chart identity as new source-fit qualification.
- Record findings and remaining uncertainty before proposing a correction. No calibration run, chart edit, AI edit or release-blocking defect is implied by this ticket.

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

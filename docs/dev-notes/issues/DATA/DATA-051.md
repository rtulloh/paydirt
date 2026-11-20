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

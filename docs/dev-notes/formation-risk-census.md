# Generated formation risk census

Status: bounded diagnostic, 2026-11-06. Current source/fit/readiness acceptance
remains incomplete and release is held. This investigates the parent's BB repeated
risk-template finding without transferring BB rules or assuming printed similarity
establishes Paydirt behavior. No chart, profile, tolerance or AI policy changes.

## Scope and exact evidence

Ignored scripts and reports are under
`.ai-audits/chart-confidence/formation-risk-01/`. `prestate.json` contains 6,480
exact distributions: all 60 current candidate defenses, nine primary calls and
six formations, against both a synthetic constant-10 offense and the same team's
actual offense. It uses the real priority/B/QT resolver with 216 offense and 36
defense physical weights and independent secondary conditioning. Same-team pairing
is a control, not historical opponent or schedule weighting.

The result categories distinguish incompletions, determined numeric gains,
interceptions, sacks, scrambles, touchdowns, pending fumbles and pending penalties.
Numeric diagnostics report known mass/contribution/conditional mean and negative
and explosive tails separately. They do not turn unresolved branches into zeros
or label conditional means whole-play yards per attempt.

| Cohort and offense | Passing team/call cases | Distinct formation risk vectors | Distinct numeric vectors |
| --- | ---: | --- | --- |
| 1983 constant 10 | 140 | 3:20, 4:64, 5:54, 6:2 | 5:28, 6:112 |
| 1983 same-team offense | 140 | 4:56, 5:80, 6:4 | 5:28, 6:112 |
| 2024 constant 10 | 160 | 3:32, 4:64, 5:64 | 5:32, 6:128 |
| 2024 same-team offense | 160 | 4:64, 5:96 | 5:32, 6:128 |

For example, `3:20` means twenty team/call cases have three distinct risk vectors
across A–F. Every passing case has formation contrast; some pairs legitimately
share risk while retaining numeric differences. The BB finding of identical risk
mass across all six formations is absent in these controls. This is a mechanism
finding, not historical tactical accuracy or adequate Hard coaching evidence.

## Terminal engine checks and limitations

`terminal-controls.json` executes 97,200 real-engine branches, yielding 19,440
exact weighted distributions across own 2, own 40 and opponent 5, first/fourth
down, all nine calls and A–F for all 60 defenses. The offense is explicitly
synthetic 2026, with primary 10, B25, QT-minus-six, 100% yardage factors and zero
returns. Independent constant-table dice are conditioned analytically; all five
defense subrows are weighted. These are not historical-era team matchups.

No recovery or pending-penalty branch occurs in that numeric control population;
assertions fail if one appears. The kind distributions retain exactly the same
3–6 passing contrasts in every position/down context. Full event distributions
also include first downs, touchdowns, safeties, turnover and possession changes;
they have 4–6 distinct formation vectors. All 3,240 own40/first-down result-kind
comparisons match the resolver census. The existing real-engine observer control
suite separately passes all 34 checks, including retained/nullified and recovery
branches. It is branch conformance, not integration of those probabilities into
the actual-chart matrix.

Every actual-offense matrix entry has some pending penalty/fumble mass. The
pre-state helper does not resolve penalty rerolls/choices, recovery, return chains,
end-zone clipping or all state contexts. Accordingly **full terminal risks for
actual chart matchups remain uncertified**. Exact endpoint probabilities require
an explicitly declared penalty/return/state policy and further branch conditioning;
no inference from numeric controls fills those unknowns.

## Concrete tradeoffs and validation boundary

For the public generated 2024 Broncos defense against constant-10 Short Pass,
Standard has incompletion mass 5/18 and known-yard contribution 47/9. Short Pass
formation D raises incompletion mass to 5/12 and lowers the contribution to 43/12;
Long Pass E has 1/9 incompletion and contribution 28/3. On Long Pass, E has 5/12
incompletion, 1/36 interception and 1/4 sack mass; Blitz F has 1/4 incompletion
and 5/12 sack mass, with a separate 1/36 touchdown override. Those selected
priority effects establish coverage/pressure costs and benefits beyond a printed
cell permutation. Contributions excluding unknown touchdown gain are not total
expected yards.

The existing gate rejects equal weighted full-outcome distributions despite
visibly different arrangements; its synthetic mutant already exercises row1 mass
12 versus rows2+5 mass 11+1. Protected offense is an explicit passing control.
Do not invent a requirement that every formation have a different risk vector
for every call, or that historical formations have known frequencies. A future
risk-only rejection rule needs a declared model role and supported contrast first;
no new universal risk threshold or cosmetic shuffle is introduced here.

Both candidate fingerprints remain unchanged: 1983 `dbebc716…f30a68`, 2024
`16f3eee3…ca931a` (full hashes in `component.json`). The pre-state run binds broad
runtime `9c472dbf…d8088`; the terminal run binds `12774fb8…ede52f`, after an import
spacing-only source-bundle cleanup. Each run checks its own inputs before/after;
these are versioned component results, not a final frozen-candidate certificate.
No new defect ticket is warranted from the absent repeated-template mechanism;
[DATA-022](issues/DATA/DATA-022.md) records the diagnostic alongside its distinct
interception-floor verification. All 31 resolved tickets were checked for new
issue-specific play-test confirmation; this stationary audit supplies none, so
no ticket is closed.

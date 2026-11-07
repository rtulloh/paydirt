---
id: DATA-040
title: Generated defenses repeat interception stripes and fixed depth patterns across formations and teams
status: open
priority: Medium
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - investigating
  - chart-generation
links:
  - DATA-022
  - DATA-039
---

## Description

The owner requested a complete generated-defense pattern audit after observing
an all-formation interception row in Bowl Bound. Paydirt has related repeatable
patterns caused by its shared tactical template and ordered interception-cell
allocation. The [full census](../../generated-defense-pattern-census.md) covers
every defensive cell of maintained teams and newer candidates separately,
alongside manifested archives: 209 cohorts, 6,210 team artifacts, 1,676,700 cells
and 319 distinct defensive contents. Copied artifacts are not independent data.

- Older 1983: 23/28 teams have Short Pass row-five `INT 5` in all six formations.
- Older 2024: 2/32 teams have that same stripe.
- Newer 1983 candidate 03: the Short Pass stripe is gone, but Cardinals, Chiefs,
  Redskins and Steelers have Screen row-five `INT 5` in all six formations.
  Seven teams also have INT across all five passing calls in formation D's
  fifth row, with depths `5, 5, 12, 18, 8`.
- Newer 2024 diagnostic 02 has neither all-formation stripe. Broader template
  repetition remains: 261/270 positions share one result mechanism across teams.
- The inspected corpus uses only `INT 5`, `INT 12`, `INT 18` and `INT 8` for
  defensive interception depth. Numeric bands, replacement cells and QT also
  have repeated runs documented in the census.

The real resolver confirms the newer Cardinals Screen stripe contributes an
interception at depth five with probability 1/36 in every formation against the
ordinary-10 control. All six full outcome distributions still differ. Across
all 319 distinct defenses, every ordinary-10 defense/call comparison retains
five or six full formation distributions. This ticket concerns repeated event
components and unsupported template/depth assumptions; it does not assert that
formations are identical or that a visual run alone proves incorrect balance.

Related DATA-022 addresses the older excessive interception floor. Its row-five
correction does not eliminate these remaining stripes. DATA-039 addresses
primary offense dispersion; defense has different weights and dependencies.

## Resolution / verification

1. Classify the audited repeated patterns as intentional supported model
   structure or unintended allocation artifacts. Record the justification and
   source limitations for each retained pattern, including fixed catch depths;
   uniqueness and overall formation contrast alone are insufficient evidence.
2. Before any behavior change, add failing synthetic/public-2026 regressions
   for unintended stripes and passing neutral/low/high-strength controls. Cover
   other result families so the fix does not merely relocate the next cluster.
3. Preserve exact conditional weighted outcomes for a layout-only change. Any
   change to formation/call event mass or depth support is an explicit model
   change requiring source and tactical validation. Defensive row weights are
   12/11/9/3/1 out of 36; arbitrary shuffling and universal run caps are invalid.
4. Regenerate and census all 60 final candidate teams, keeping older previews
   and experiments distinct. Verify chart/API identities and engine priority,
   tactical tradeoffs, recovery/return effects and AI behavior. Retain unknown
   conditional source quantities as unknown. The parent agent performs this
   qualification; the human owner's review is cursory visual/play review.
5. Run the required full regression before any upstream push. Record each
   changed test expectation. Resolve only after a tested fix or explicit
   reviewed disposition is committed; close after issue-specific play-test
   confirmation under the tracker's normal rules.

## Comments

--- 2026-11-06 19:39 ---

Created at the owner's explicit request. Evidence remains ignored in
`.ai-audits/release-readiness/defense-pattern-census-01/`: `report.json` SHA-256
`359c35b3635fbf95e1ac254108906428e159e1f6999e1b62b8d788246e99d53b`, independent
raw-CSV/geometry verification of all cells and 6,416 chart/manifest bindings,
and a synthetic current-allocator reproduction of the all-six Screen stripe.
No chart/model/source/policy changes or issue closure resulted from the census.

--- 2026-11-06 19:43 ---

RCA: confirmed deterministic allocation structure. `_generate_defense` starts
from one shared tactical template (or the shared neutral pressure map), then
changes numeric efficiency and disruption strength. The interception allocator
uses the same ordered formation/call list for every team, always on subrow five;
higher rates fill more of that list. Its final six positions are Screen for
formations A through F, so sufficiently strong inputs create the all-formation
Screen stripe. A fixed call-to-token map supplies INT5/12/18/8 rather than a
team-specific depth distribution. The synthetic .06 reproduction confirms this
mechanism. Quantized strength changes over shared structure also explain why
different teams can retain nearly identical charts.

The earlier interception-floor correction intentionally restricted INT to the
1/36 subrow, but retained ordered placement and fixed depth support. Previous
uniqueness, weighted-outcome and tactical-contrast evidence can pass while one
component repeats across formations; that is the detection gap addressed by this
census. The causal mechanism is confirmed. Whether each repeated component is
unacceptable, and the source-supported replacement policy, remain qualification
questions under this ticket. Avoid changing frequencies merely to hide a stripe.

--- 2026-11-06 19:51 ---

A dedicated correction lane has added synthetic test-first regressions: five
intended failures and fourteen passing controls against unchanged production.
They reproduce the Screen stripe and lost B/C/F parenthesized counterplay, while
holding rare-event budgets, nested strength and other result families. The
[bounded correction proposal](../../defense-allocation-correction.md) moves three
Screen allocations to existing BLACK coverage cells within the same formations,
retaining each formation's physical interception budget at every strength tier.
An ignored in-process trial passes all nineteen new tests and existing tactical
contracts for 101 synthetic rates. It changes normal-policy call exposure and
therefore requires explicit model review and renewed candidate fit. Production
allocation is unchanged pending parent review; no charts, source targets,
tolerances, releases or issue status changed. Receipts remain ignored under
`.ai-audits/release-readiness/data040-defense-fix-01/`.

--- 2026-11-06 19:58 ---

Parent model review approved the narrower three-entry correction; it is now
implemented. B/Screen→B/Short, C/Screen→C/Short and F/Screen→F/Medium preserve each
formation's interception units while restoring parenthesized Screen costs. New
pressure integration first fails on the .035 source sack-rate QT collision at
F/row-five/Medium and the .04 source case's lost Screen result; the corrected
queue automatically reserves these cells before relocation. All twenty-one new
cases pass; existing expectations and skips are unchanged. The combined focused
run has 286 passes and one independently reproduced offense-layout failure,
reported to DATA-039's owner. Additional source CLI/PFR and source-audit suites
pass 78 and 56 cases; owned lint passes. The local sixty-team raw-stat projection
diagnostic verifies tactical contracts and absence of all-six INT stripes, but
is explicitly not a calibrated final-candidate census. Fresh source/pressure
binding, all-sixty final candidates, fit and full play-test qualification remain.
The [correction note](../../defense-allocation-correction.md) records retained
numeric/QT/replacement/depth model limits and exact normal-policy exposure delta.
This uncommitted change does not resolve or close DATA-040.


--- 2026-11-06 20:24 ---

The actual calibrated current-source-command sixty-team candidate has now been frozen and reproduced exactly from its bound prepared inputs: 180 chart CSVs, 240 rendered tables and 52,200 raw-label comparisons. DATA-040 changes 52 defensive cells in twelve historical teams, zero modern cells; all four all-formation Screen interception stripes are removed. Seven formation-D fifth-row passing INT bands and fixed depth support remain explicit model constraints. The fresh-parser historical Bengals run-cell difference is separately bound, not substituted from archived inputs. All per-formation interception budgets, tactical controls, other families and protected tables pass the bounded checks. This is model-provisional candidate evidence, not source-fit or season/AI qualification. A separately identified primary-offense QT allocation constraint is tracked in DATA-041; DATA-040 does not claim that all chart clustering is fixed. No commit, release or closure.

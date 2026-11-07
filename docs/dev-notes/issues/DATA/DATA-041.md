---
id: DATA-041
title: Empirical variant allocation locks primary QT into low-weight rows that layout cannot disperse
status: open
priority: Medium
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-generation
  - chart-layout
links:
  - DATA-039
---

## Description

The owner found a retained QT pattern in the current 2024 Bears offense during cursory chart review. The frozen CSV and actual chart API agree: Screen, Short, Medium, Long and T/E S/L have QT or QT* at the same twelve rows, 10–13, 16–20, 28–29 and 39. That creates two large cross-column blocks and a five-row run. Each call has 37/216 physical QT-trigger mass; this is a primary lookup probability, not a sack rate or a policy-weighted game result.

All rows of physical weights one through five are QT triggers in each passing column, and none of the other weights are. Thus no equal-weight QT/non-QT swap exists, even before BLACK protection. The DATA-039 v2 layout correctly includes the QT family, but its per-weight invariant freezes this family mask. It improves exact QT versus QT* and sideline placement while leaving the pooled QT blocks intact: family cost 11250, 32 two-by-two blocks and 48 horizontal pairs remain unchanged. A detected cluster being immovable under this invariant does not prove that a different probability-preserving allocation is impossible.

The upstream empirical allocator's variant-preservation stage prefers subsets with the smallest maximum row weight. This can pack a mixed QT/QT* family's entire mass into every low-weight row. The resulting allocation constraint is an implementation choice, not a demonstrated football requirement. The protected supplemental QB Time column is a separate lookup of gains, sacks and fumbles; this finding concerns the primary QT triggers.

The owner's required scope extends beyond QT: **B, QT, BLACK, INT, yellow cells, and unusually repetitive green/red cells** must be checked for avoidable clustering and row repetition. Inspect exact tokens, normalized outcome families and actual rendered colors separately. Look for consecutive runs, two-dimensional blocks, matching rows across play calls or defensive formations, and repeated patterns across teams. Cover all four displayed tables while distinguishing primary triggers from dependent supplemental, recovery and special-team lookups.

## Resolution / verification

1. Preserve the frozen review candidate and bind the actual CSV/API, allocation input, before/after family masks and weight saturation proof. Extend the primary census to all result families with zero family-changing equal-weight swaps; do not infer that every such family is wrong.
2. Add test-first synthetic/public-2026 regressions for avoidable clustering and row repetition across B, QT, BLACK, INT, yellow and green/red outcomes, with frequent/uniform-result and protected-lookup controls. Tests must demonstrate the actual placement defect, not merely missing evidence fields. Evaluate alternative row allocation within the existing generator, retaining calibrated full-token/flag probability mass and dependent lookup semantics. Any unavoidable quantization or modeled distribution change must be explicit and reviewed; arbitrary unequal-weight swaps are not a fix.
3. Review every listed category independently, including actual green/red/yellow unions as well as individual symbols. Prevent the correction from shifting clusters to another outcome type, column, row or team. Regenerate and re-audit the complete sixty-team candidate across all four tables, reporting printed counts, dice-weighted frequencies, runs, blocks and aligned/repeated rows; then verify actual API bytes and relevant gameplay. Document each retained suspicious pattern with its frequency, source/model or dependency constraint and explicit disposition or follow-up ticket. A lower aggregate score, passing uniqueness check or zero available equal-weight swaps does not by itself clear a pattern. Avoid universal run caps that would distort genuinely frequent results; do not relax an audit threshold or silently reclassify a pattern as accepted.
4. Keep DATA-039's component result distinct from this allocator limitation. No production allocator or candidate chart was changed by the finding; source, football fit and full regression remain separate requirements.

## Comments

--- 2026-11-06 20:24 ---

Parent and DATA-040 worker independently confirmed the actual twelve-row QT union, all five matching passing columns, 37/216 mass and zero legal family-changing equal-weight swaps. The current sixty-team census records this retained pattern; a good aggregate layout score does not establish that it is acceptable. Detailed generated evidence stays in ignored `.ai-audits/release-readiness/current-review-candidate-01/verification/` and the targeted follow-up handoff. Source-provisional status is unchanged; no release approval or ticket closure.

--- 2026-11-06 20:35 ---

Local correction preserves the original quantizer's exact complete-token/flag
physical distribution, then searches bounded equal-total-mass multirow exchanges
in primary offense only. BLACK positions and all dependent tables remain fixed;
the subsequent v3 layout retains its existing per-weight invariant against that
corrected allocation and explicitly scores actual viewer color unions. Details,
test-expectation changes and limits are in the
[allocation note](../../exact-mass-primary-allocation.md). The unchanged-production
baseline reproduces all three seeded QT geometry failures with probability and
dependency controls passing. Six additional missing-metadata failures establish
metadata only. An explicitly labeled no-allocation-stage control separately
fails six actual B/QT/INT/yellow/green/red geometry witnesses; uniform controls
retain long runs without universal caps.

The bounded verifier independently enumerates physical dice weights, replays
every accepted exchange and checks exact token masses, BLACK maps, protected
columns and objective arithmetic for six category/color witnesses, three
empirical seeds, both public teams and the frozen Bears witness. Frozen candidate
files remain unchanged. The witness's pooled QT run improves five to two, blocks
32 to zero and aligned pairs 48 to five, with each passing call still exactly
37/216. Requested major-category measures improve or hold there. Two numeric-band
aligned-pair increases remain explicit, seven to nine for gains 1–4 and zero to
one for gains 20-plus; parent disposition is pending. No all-team regeneration,
source/fit campaign, live API replacement, gameplay qualification or release
approval occurred. DATA-041 remains open. Durable evidence/handoff:
ignored `.ai-audits/release-readiness/data041-allocation-fix-01/`.

--- 2026-11-06 20:42 ---

The final local objective includes aligned rows across every primary-call pair,
not just adjacent calls. A retained pre-extension baseline fails five actual
nonadjacent repetition cases, with yellow and the 27-green-cell/run-fourteen
protected-BLACK control passing. All six feasible B/QT/INT/yellow/green/red
witnesses now have five distinct passing-call masks. The final focused
generator/allocation/layout/pressure/CLI/defense/documentation/tracker check has
559 passes, no skips or warnings; backend chart-reference checks have 28 passes.
Owned Ruff and the allocation/layout module's type check pass. Nine existing
generator type diagnostics reproduce exactly on a reconstructed source matching
its pre-edit SHA. Three fresh processes with different hash seeds produce
identical public fixture charts and stage receipts.

The refreshed all-call witness supersedes the initial adjacency-only checkpoint:
QT run five to two, blocks 32 to zero, adjacent aligned pairs 48 to six and
all-call aligned pairs 120 to thirteen, still exactly 37/216 per passing call.
BLACK stays fixed. Red run one to two is retained explicitly: 27 printed cells,
151 summed physical units across nine columns, zero red blocks, adjacent pairs
two to one and all-call pairs seven to four. Gains 5–9 acquire three adjacent
pairs; exact twelve acquires one. These need parent disposition, not aggregate
clearance. Synthetic majority-zero raw alignments rise with printed population,
while excess over their population-derived alignment lower bound falls ninety
to six–twelve at unchanged physical mass. The final bounded verifier records all
features and tradeoffs; its classification labels are shared with production,
while dice enumeration, exchange replay, probability and cost arithmetic are
independently calculated. DATA-041 remains open pending the complete candidate,
all-table/all-team dispositions, actual API identity and gameplay qualification.


--- 2026-11-06 20:58 ---

The complete sixty-team downstream replay and independent audit are now finished.
The independent verifier checks all 180 CSVs, 540 primary columns, 240 displayed
tables and 52,200 exact labels and actual viewer colors. It independently replays
all 3,711 recorded exchanges and objective deltas: original quantization, exact
complete-token/flag physical masses, final BLACK positions and protected lookup,
defense and special-team data pass. This is probability and placement evidence,
not renewed source-fit or football qualification. The five Bears passing columns
retain each QT/QT* variant's original physical mass and their pooled 37/216;
family masks are distinct, maximum run is two and the former blocks are gone.

Root retains the following findings under this open ticket rather than accepting
them from an improved aggregate objective. The ignored independent disposition
packet binds every affected row/call, printed count, physical mass, population
context and an old-candidate same-mass/BLACK feasible witness: two QT grids,
two yellow grids, 27 green grids and 20 red grids have at least one worsened
measure. In particular, the 1983 49ers acquire one yellow 2x2 block despite
all-call yellow alignment falling from 23 to 15; Chiefs/Packers QT retain small
local adjacency tradeoffs. Cross-team B alignment excess over a count-only
population lower bound rises from 356 to 392. That bound does not prove physical
weight feasibility, and the increase is not cleared. All 299 feature-grid and
602 per-column increases remain inventoried; they overlap and are not separate
proven defects. Root has resumed the allocator agent for a bounded read-only
investigation of the B increase and the rare QT/yellow cases, including whether
the objective omits a term or its search neighborhood prevents an improvement.
No release disposition or additional production correction is implied.

A separate frozen provisional review service now serves candidate 688ab5ec2e39
on local port 8160. Actual HTTP checks cover all sixty chart books and their
labels/colors, served assets, four season/role mechanics cases, save/load
controls and twelve standalone-spike edges. The current runtime includes the
2-point, play-log timing, timeout and standalone-spike corrections. Backend full
suite: 423 passes and 18 existing Pydantic deprecation warnings. Full core
coverage regression is still running; browser/E2E is unpassed because Chromium
failed before opening a page. The source candidate's legacy-1983 and frozen
measured-2024 policies are unchanged. Source/fit, retained-pattern disposition
and the required complete regression remain open; no push, promotion or closure.
Durable ignored evidence: `data041-independent-review-01/HANDOFF.md` and
`current-ui-review-03/HANDOFF.md` under `.ai-audits/release-readiness/`.

--- 2026-11-06 21:28 ---

The owner has now spot-checked six charts and reports satisfaction with their
appearance. This satisfies cursory owner visual review; it does not close the
remaining automated source, placement or football-fit work.

A separate current-source modern diagnostic has generated all 32 teams using
fresh, explicitly declared end-zone-return-policy exposure measurements and
source-primary recovery ranges, with the frozen five-field profile unchanged.
Independent checks cover all 96 CSVs, 128 displayed tables and 27,840 labels and
actual viewer colors. All primary offense and defense cells, plus dependent
breakaway and quarterback-time columns, are identical to the reviewed candidate.
Fifteen recovery ranges change with the corrected primary counts; six shared
return columns change with fresh measured exposures. These are explicit model
changes, not probability-preserving layout changes or a replacement of port 8160.

The all-table comparison retains six additional special-team color tradeoffs:
green for Buccaneers/Rams/Steelers and red for Chargers/Rams/Steelers. Printed
population and physical probability changes are reported separately. The other
62 overlapping feature-grid increases remain inventoried, not 62 proven defects.
No new primary B/QT/BLACK/INT/yellow/green/red pattern change occurred, so the
previous 51 primary category-grid findings and cross-team B concern remain open.
Contiguous recovery R/L cells follow the selected physical recovery range and are
not shuffled. Shared-return conditional source targets and final fit remain
unaccepted. A 16-schedule development measurement is running; this is below the
64-schedule qualification requirement and cannot certify release readiness.
Ignored evidence: `.ai-audits/release-readiness/modern-policy-source-01/`.

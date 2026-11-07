# Primary chart dispersion procedure

Implementation design under the [chart-confidence charter](chart-confidence-agent-charter.md).
The procedure below is now implemented locally after its failing baseline. It is
a secondary placement objective, not a claim that current charts are accurate or
a change to outcome frequency. Release remains held.

The later [DATA-041 allocation correction](exact-mass-primary-allocation.md)
runs before this layout invariant. It preserves exact full-token probability
while changing feasible weight-group inventories. Its v3 layout also adds actual
viewer color unions; the v2 checkpoint below remains historical evidence.

## Scope and engine dependency

Paydirt selects the offensive column before rolling. Its primary offense roll
and defense roll are independent; B/QT resolution uses fresh rolls. The current
engine has no Razzle-Dazzle select-after-roll rule. Sneaks consume Line Plunge
values, including flags, so preserving that column's whole-token distribution
also preserves its input distribution. A primary cell's row number is not used
as a recovery/return roll.

Only the nine primary offense columns may move. Keep every B/QT supplemental,
recovery range/row, special column, defense cell, dice label and metadata fixed.
Recovery rolls select additional return/automatic-TD branches and must not move.
No private reference cells or patterns enter this procedure.

## Exact invariant of the layout stage

Within each primary column, permute whole raw tokens only among rows with exactly
the same physical dice weight. Preserve the token multiset separately for every
weight group, not merely a mean, resolved result class or rounded probability.
This retains numeric values, BLACK, B/QT, fouls, fumbles, color/OOB markers and
every rare token with precisely its prior physical mass. It also preserves the
joint distribution with any independent defense and fresh supplemental lookup.
Use an independent invariant checker before writing charts. Existing exact maps
can erase OOB flags and cannot serve as the only proof.

The 30 printed rows have only 2–6 interchangeable rows in most groups, and five
singleton groups cannot move. Large BLACK shares and these fixed positions can
make contiguous regions unavoidable. No incidence adjustment or unequal-weight
swap is permitted to improve appearance. Changing the generation seed is not
equivalent: quantile assignment can change weighted gains across seeds.

## Objective and deterministic search

The first stage retains the earlier BLACK-only objective. It measures the
printed 30-by-9 primary grid in ascending dice-row order and canonical play-column
order, minimizing this lexicographic tuple:

1. Longest vertical run of BLACK cells in any column.
2. Number of all-BLACK adjacent 2-by-2 blocks.
3. Sum of squared vertical BLACK-run lengths across columns.
4. Number of horizontally adjacent BLACK pairs.

At each step, examine every unequal-token pair of equal-weight rows within a
column. Apply the swap with the lowest strictly improved tuple; break ties by
canonical column and ascending row pair. Stop when no permitted swap improves
the tuple. Retain the original layout if no improvement exists. This terminates
because each accepted swap strictly decreases a bounded integer tuple. It is a
local optimum, not a claim of global aesthetic optimality. The procedure needs
no random seed and never changes allocation.

Record method/version, before/after metrics, accepted swap count and exact
invariant result in the generation manifest. Layout evidence is separate from
empirical fit. A new engine dependency on shared/selected rolls would require
reviewing this proof before reusing the method.

## Test-first evidence and review

Before implementation, require a synthetic clustered chart to improve, a fixed
or already minimal chart to remain unchanged, deterministic repeatability and
idempotence, and preservation of complete per-weight token inventories. Negative
controls must reject OOB-marker loss, unequal-weight swaps, rare-token changes,
modified supplemental/recovery data, row changes and column changes. Include
public-2026 controls through both resolver routes and fresh supplemental rolls.
Check B/QT/fumble/penalty/INT/numeric tokens without substituting a future rule.

After generation, require exact invariants for all 60 teams, report feasibility
limits and before/after clump measures, then repeat the existing exact/current-
engine acceptance campaigns on the frozen candidate. The stable private-corpus
comparison and compact owner review remain separate charter requirements.

## Local checkpoint

Fourteen new synthetic/generator cases fail before production changes; fourteen
finite-allocation controls pass. After implementation, 77 placement/allocation/
generator tests pass. Two further root-command tests fail before the PFR and
nflverse manifests retain placement evidence. Public-2026 distribution controls
exercise both resolver routes, every defense and three representative primary
calls, retaining typed flags and fresh secondary/recovery results. The integrated
checkpoint is recorded in the implementation note after completion. No public
chart CSV has been replaced; all-team candidate evidence and owner review remain.

## Owner review service checkpoint — 2026-11-06

The main development service was still loading the earlier generated CSVs, whose
generation manifests contain no primary-layout receipt. The owner observed BLACK
pyramids in the 2024 49ers, Broncos, Bears and Browns charts. This was a stale
serving-data problem: the implemented placement pass had not been applied to those
files. It did not demonstrate a failure of the new placement procedure.

A separate local review service now uses layout-only copies of all 60 existing
generated teams. The source CSVs and original development service remain intact.
The review copy changes only primary offense placements through the procedure
above, and retains per-team source/output hashes and exact invariant receipts in
ignored `.ai-audits/chart-layout-review/owner-scattered-01/`. Every team's weighted
whole-token inventory, supplemental columns, peripheral data, defense and special
teams passed the preservation checks. All 60 layouts changed. The 79 focused
layout, finite-allocation and generator tests pass.

For the four reported teams, longest consecutive BLACK runs change as follows:

| 2024 team | Earlier layout | Review layout | All-BLACK 2×2 blocks, before → after |
| --- | ---: | ---: | ---: |
| 49ers | 17 | 3 | 32 → 0 |
| Broncos | 9 | 3 | 26 → 0 |
| Bears | 9 | 2 | 33 → 1 |
| Browns | 10 | 3 | 33 → 0 |

Across the 60-team review copy the largest vertical BLACK run is reduced from 22
to 6. Equal-weight constraints and a team's actual incomplete-pass mass can still
limit dispersion. This is a placement review of existing statistical outputs,
not the pending source-corrected candidate or evidence of historical accuracy.
The service identifies itself as an updated layout development review. Its
preloaded chart links refer to new engine instances using the copied charts;
previously open games retain their originally loaded chart objects.

After viewing the updated review service, the owner reported: “that looks much
better!” Retain this as positive feedback on the displayed placement, not an
exhaustive visual review of all 60 teams or statistical acceptance. Carry this
placement procedure into the next source-corrected candidate with the exact
probability-preservation checks and remaining charter evidence intact.



## General placement limitation — 2026-11-06

The BLACK-only objective left reducible clusters in penalties, sideline markers,
numeric bands and other result families. The [general placement audit](general-chart-placement-audit.md)
records the census that motivated DATA-039. Its individual improving swap
witnesses preserve BLACK geometry and whole-token physical mass; they were not
a jointly optimized or qualified candidate.

## General outcome placement v2 — local implementation, 2026-11-06

`equal-weight-primary-outcome-dispersion-v2` retains the BLACK stage above, then
freezes every resulting BLACK position. The second stage considers all other
whole-token equal-weight swaps together. Features include exact raw token,
lexical result family, the penalty and turnover-risk groups, sideline and
parenthesis/bracket replacement flags, and numeric sign/magnitude bands. These
are placement features, not new historical source facts or rate targets.

For each feature, let `n` be its printed-cell population across the nine primary
columns. Its coefficient is `max(1, 2700 // n)`. The cost is that coefficient times
the sum of `run_length * (run_length - 1)` over vertical runs, horizontal pairs,
and adjacent 2-by-2 blocks. At each step choose the strictly greatest integer
cost reduction, breaking ties by canonical column and ascending row pair. Stop
at a local optimum. Frequent or unavoidable features receive less weight; there
is no universal run cap, global-optimum claim, or promise that each feature's
individual metric improves. BLACK geometry cannot be traded away in this stage.

Both frequency normalization and neighboring-column costs depend on the whole
grid. Updating an empirical Short Pass distribution can therefore change Line
Plunge's printed positions. Allocation remains column specific: the exact
pre-layout defaults and each column's complete per-weight token inventory stay
fixed, except for directly supplied empirical columns and the existing pooled
TE Short/Long fallback. The source/default allocation and resolved behavior are
the guarantees; unchanged row positions are not a guarantee. Supplements,
recovery thresholds, defense and special teams retain their original scope.

The interrupted implementation's original unchanged-production failing log was
not recovered. A retained in-process control explicitly disables only the v2
outcome stage: all six non-BLACK family regressions fail and 17 controls pass.
This demonstrates the BLACK-only limitation without mislabeling the control as
a recovered baseline. Current v2 passes those tests. The previous empirical
regression's post-layout Line Plunge row-identity assertion was replaced with
exact pre-layout allocation checks, full-token/per-weight inventories, unchanged
protected tables and resolved-distribution comparisons for both resolver routes.
The original Short Pass BLACK-rate and mean assertions remain. TE pooling was
verified and remains unchanged. Public-2026 controls now cover all nine primary
calls plus QB Sneak, all defense types, typed result fields and fresh secondary
rolls. See ignored `data039-primary-resume-01` for the bounded verification receipt.

This local implementation does not replace the review service's loaded charts.
The parent implementation agent owns candidate regeneration, all-team invariants,
mechanics, source/model qualification and full regression. DATA-039 remains open
until the candidate evidence confirms the issue is resolved. The owner receives
a compact visual/usability review and release decision; exhaustive qualification
is not delegated to the human owner.

# Shared source-constrained neutral pressure proposal

Development design under the [chart-confidence charter](chart-confidence-agent-charter.md).
Proposed before implementation and now implemented locally; release remains held. This addresses DATA-023's
defensive QT floor, not DATA-030's unresolved physical/credited gain definitions.

## Constraint and scope

The corrected conditional QT population leaves two 1983 teams below the current
shared neutral-defense floor. A nonnegative offensive QT probability cannot
cancel defensive QT. Clamping the requested rate or restoring misclassified QB
runs would conceal the defect. Formation-specific historical pressure incidence
is unavailable; the defense template is a declared model allocation.

Prepare every cohort team's normalized/calibrated stats and selected empirical
outcomes before generating any team. Quantize its conditional QT column using the
same seed/recipe as final generation. For every supported pass column derive the
largest shared neutral defensive QT probability compatible with zero primary QT,
using the unchanged official sack rate, actual conditional sack share, penalty
mass and primary F protection. Take the minimum of these source constraints.
Keep both the unrounded ceiling and all contributing numerical inputs in the
manifest. Names, season, observed trial error and fit bounds are not parameters.

Resolve one common neutral template for the entire cohort, then use precisely
that template for offensive overlap allocation and defensive generation. This
avoids using a team's own defense as its average opponent. Keep existing
source-supported interception allocation, efficiency shifts and stronger/weaker
pressure adjustments. Verify those strength differences with synthetic controls.

## Bounded physical allocation

Start with the current neutral interception allocation. Relocate an existing QT
cell to a strictly lower-probability subrow in the same formation and pass column,
swapping with an ordinary unparenthesized numeric result or BLACK. Keep every
formation/column's complete token multiset, all run columns, and all INT, TD,
foul, fumble and parenthesized cells fixed. Reserve all cells used by interception
strength changes and explicit pressure-strength adjustments. The unequal-weight
swap intentionally changes pressure incidence; this is a model correction, not
the behavior-preserving visual dispersion procedure.

Choose deterministic progress: if one eligible swap can meet the ceiling, take
the smallest sufficient reduction; otherwise take the largest reduction. Break
ties by stable formation/column/subrow coordinates. Recompute actual weighted
pressure after each swap. Lower row weight strictly decreases, so the search
terminates. If no allowed swap can satisfy the source ceiling, fail explicitly.
Do not erase QT cells, overwrite protected results or invent a fallback target.
This bounded search need not find every globally feasible arrangement; disclose
that limitation and report remaining infeasibility rather than claiming a proof
that no model could work.

The recipe uses the declared normal policy's exact formation/call weights and
physical defense subrow weights. Record the resolved cells, moves, requested and
attained neutral mass, algorithm version and source constraints in reproducible
generation receipts. Standalone/aggregate generation without cohort evidence
retains its explicitly documented default; source-cohort commands must supply
the shared resolved model instead of silently reverting to it.

## Test-first acceptance and limits

Synthetic failing controls must first show a low-sack cohort below the old floor,
cohort propagation through both root commands and a matching overlap model.
Passing controls cover already-feasible cohorts, missing QT data, no sack support,
deliberately infeasible protected layouts, exact token/protected-cell preservation,
determinism, team renaming/order invariance and retained strong/weak defense
contrast. Confirm every cohort team's continuous pressure solve before emitting
charts, then regenerate independently and require all source/mechanics/fit gates.

This supports feasible allocation under a declared policy; it does not promise
finite 216-row exact incidence, historical formation truth, stateful fit, or
insensitivity to Hard/balanced/repeated-call policies. Those still require the
charter's fixed tests and campaigns. No official target or acceptance threshold
changes, and no reserved seed or private reference is used to choose the recipe.

## Ignored feasibility prototype

A separate process applies the proposed algorithm to the reviewed public-source
1983 inputs without changing production files. The source-derived ceiling is
.0443977889; one eligible same-formation/column swap reduces neutral QT mass to
.0400992063. All 28 teams then solve all five supported pass families continuously.
The process explicitly patches its local in-memory template and its report is
labeled exploratory, never runtime-attested acceptance evidence. No campaign,
reserved seed, private chart or source target is used. Test-first production
propagation and full candidate evidence remain required.

## Shared pressure implementation checkpoint

Eight new capability regressions fail with 49 existing generator controls passing;
two strengthened root-command tests independently fail on absent shared-model
propagation. No existing assertion is removed or weakened. The new replay test's
initial enum import is corrected from the unrelated model enum to the resolver's
public enum. A subsequent semantic mutant (`F+2` versus `F + 2`) fails with its
spaced control passing, motivating one shared QT sack-mass parser instead of
duplicate spelling-sensitive classification. The integrated suite then passes
284 tests with lint, and the separate runtime/tactics suite passes 95 tests.

The bounded procedure above is implemented in the existing generator; both root
commands prepare the cohort before generation, pass the same resolved model to
every team and retain its versioned source constraints/cells/moves in the manifest.
Missing QT observations disclose their unconstrained default, while unsupported
sack populations and protected layouts still fail. Strong/weak defense controls
and exact low-sack replay pass. This implements allocation feasibility, not fit.

Fresh neutral-profile 1983 generation completes all 28 teams/224 games. Its shared
source ceiling is .0443977889 and the one-relocation template attains .0400992063.
Fresh 2024 trial07 uses the unchanged trial03 profile: its .0584379882 ceiling
already permits the default .0505753968 neutral mass, so no relocation occurs.
Separate generations reproduce all 84 and 96 CSVs byte for byte. The independent
source components pass with 265 and 35 bound input files respectively. Historical
source/model limitations and the 2024 punt-exposure warnings remain disclosed.
No promoted charts, target facts, fit thresholds or reserved families change.
Four-repetition training-only baselines are being collected for each cohort;
these are below the final 64-repetition/1,000-team-game requirement.

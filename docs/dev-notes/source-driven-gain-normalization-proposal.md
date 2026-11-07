# Proposed source-driven gain normalization

Proposal for parent review under the [chart-confidence charter](chart-confidence-agent-charter.md).
**The complete fitting procedure is not implemented or accepted.** Pure cohort
math and ordinary-gain transformation components are implemented and remain
unwired, as described below. The engine-baseline alternative remains the current
procedure proposal; the earlier exact-initial method has unmet assumptions.
No real normalization coefficients or normalized candidates have been derived.
Prospective 2023 data and final seed families remain unopened.

## Earlier diagnostic, superseded by the measured constraint below

After selected-priority, allocation, source and conditional-pressure corrections,
a uniform 2024 profile passes all five league bounds across sixteen training
source schedules (4,352 legal games, 272 team-games). Every team passes completion,
INT and sack bounds. Five yard metrics remain outside fixed bounds: Denver,
Kansas City and Miami passing high; Baltimore passing and rushing low. The
between-repetition SEs are attached in the ignored report. Smaller-sample misses
that disappeared are not grounds for adding club-specific knobs.

Exact source-schedule-weighted normal-policy initial passing YPA also has these
opposing residuals, before state clipping and recovery movement. Heuristic
family labels partly encode observed gain rather than independently observed
route intent; applying one reference call mix can therefore distort the aggregate
source strength represented by those conditional families. Matching a developer
chart is not an objective. No claim of route-specific historical truth follows.

The preceding conversion-population correction must be regenerated and measured
before deciding whether this proposal is still necessary.

## Same procedure for any supported source cohort

1. Reconcile complete credited source counts, definitions and source coverage.
   Use ordinary attempts, excluding conversions. Team rushing credit includes
   documented lateral yards without inventing another attempt. Preserve unknowns.
2. Generate the baseline with the existing shared calibration controls. Freeze
   normal call/defense weights and source-schedule opponent exposure. The method
   uses no developer charts and no team/year identifier as a fitting feature.
3. Compute exact pre-state modeled passing initial-yard numerator and potential
   attempt denominator. Exclude QT sacks/scrambles and pending penalties from
   potential passing attempts; include known initial primary-fumble yards while
   explicitly leaving recovery movement pending. Unknown touchdown-distance
   branches prevent an exact yard-normalization claim and require a coverage
   failure rather than an invented gain.
4. Compute modeled rushing mean with the full declared normal mixture: primary
   rushing calls plus nonnegative numeric QT scrambles and positive QT fumbles
   on selected passes. QT F0/nonpositive fumbles are sacks, not rushing attempts.
   Report the remaining state/penalty/clock differences from official totals.
5. For each supported yard metric, let t be the official team target, p the
   pre-state modeled mean and n its source attempt count. Let r=log(t/p), and
   let the common anchor be the n-weighted cohort mean of r. Set
   z = n/(n+200) * (r-anchor), clamped to [log(.8), log(1.25)], and multiplier
   exp(z). These constants are proposed **before** testing the procedure.
   This is the bounded solution to n*(z-(r-anchor))^2 + 200*z^2. The common
   anchor reserves overall engine/state calibration for the existing shared
   profile instead of trying to fit every team's raw mean independently.
6. Apply exactly one derivation pass. Scale numeric/initial-fumble yards within
   the corresponding existing primary gain families; scale run Breakaway gains
   consistently. Keep all symbolic family probabilities, B/QT trigger mass,
   recovery ranges, flags, defense and special teams unchanged. Preserve the
   18-yard direct-run cap and document its saturation effect. Do not move a
   numeric outcome across zero or change a fumble's sack/rush classification.
   QT conditional gains are source-supported mechanisms and remain unchanged.
7. Recompute exact summaries and disclose the achieved residual, clamping,
   quantile/tail changes, finite rounding and unresolved branches. The derivation
   is a model allocation, not an empirical route-distribution accuracy pass.
   Existing five source metrics and all fixed team bounds still decide fit.

Zero/sparse/unsupported denominators, nonpositive means, unknown required gains,
invalid population flags and infeasible targets must diagnose unsupported input.
They may not silently choose a favorable scale. Store the versioned procedure,
input fingerprints, n/t/p/anchor/z, bounds and actual before/after distributions
in each generated profile. The public source inputs and the frozen procedure
must reproduce the result without local developer data.

## Required test-first and review evidence

- Unseen synthetic teams with identical inputs but renamed IDs derive the same
  adjustment when the probability inputs are held fixed; no name/year lookup.
  Separately quantify existing seed/finite-row approximation effects.
- Flat, strong/weak, mobile/pocket, sparse/zero and rare-event grids; support
  failures are explicit, with no fabricated negative QT cells.
- Independent closed-form objective/bound controls and perturbation controls;
  increasing one supported source target moves that metric's adjustment in the
  expected direction under a held-fixed cohort anchor.
- Exact symbolic/priority event mass and recovery invariance; monotone gain
  quantiles within a family; bounds, run cap, rounding and saturation disclosed.
  A deliberately warped tail or changed event class must fail the controls.
- No performance promise from unit tests alone. Repeat larger training with all
  team errors, source aggregate/tail diagnostics, call/pace/score sensitivity,
  and the complete final source-validation contract after a candidate freeze.
- Use the full private 1983 reference comparison to review method consequences,
  with honest retrospective team partitions and no copied reference cells.
  Freeze the whole automated recipe before prospective 2023 source-only
  evaluation under the [transfer protocol](chart-reference-comparison-protocol.md).

The parent must review the objective, constants, unsupported cases and evidence
before production implementation. If uniform controls or a general source/model
correction suffice, do not add this extension merely because it is available.

## New measured constraint and proposed engine-baseline alternative

The preceding exact-initial-gain method is not ready to implement. After the
source, adjustment, zero-sack, QB-class and pressure corrections, all 60 teams
reproduce and pass source/mechanics/allocation components. Sixteen fresh 2024
training schedules complete 4,352 games/272 appearances per team. League metrics
and every team's completion/INT/sack checks pass, but four yard checks remain:
Packers passing 7.457652/8.223382, Ravens passing 7.899740/8.781971 and rushing
5.185344/5.756318, Vikings passing 7.212748/7.990876 (model/source).

Source-schedule opponent weighting exposes why a target/initial-mean scale is
insufficient. Ravens' normal pre-state rushing mean is already 5.742534 against
source 5.756318, whereas the full-game mean is 5.185344. In the retained decision
inventory, normal rushing averages 5.697427 net (5,169 calls), clock-killing
5.099157 (3,086), red-zone 4.592771 (830), goal-line 2.027027 (333), and victory
formation -2 (95). Pending passing TD distance also leaves an initial-mean
interval, rather than the single exact value required by the original proposal.
These diagnostics identify policy/state effects; they do not prove a defect in
any one call, or establish that all target differences come from state clipping.

For parent review, replace steps 2–4 with a deterministic **engine-baseline**
measurement: generate the unnormalized cohort from reviewed source inputs and a
declared shared profile, then play exactly sixteen complete source schedules
under the fixed chart-focused policy, master 20261108 and its existing seed
derivation. Require valid complete games, authoritative credited box totals,
ordered decision reconciliation and current source/runtime identities. Baseline
games are development data, never an untouched acceptance family. Reproduce this
stage from inputs and record its charts/report hashes in the generated recipe.

Use each team's measured passing/rushing YPA as p in the existing step-5 formula;
keep source t, source-attempt n, weighted log anchor, pseudo-count 200, bounds
[.8, 1.25] and one derivation pass unchanged. The reference engine resolves TD
distance, clock choices and state clipping instead of assigning invented gains.
Source n is shrinkage support, not simulation precision. Do not claim that the
weighted log anchor conserves arithmetic league means or that t/p is the exact
response when only some gain families change.

For this alternative, scale only ordinary numeric primary gains and rushing B
gains. Keep primary F gains, every QT gain, all event probabilities, B/QT trigger
mass, recovery ranges, flags, defense and special teams fixed. Preserve signs,
zeroes, the direct-run cap, ordering and physical quantization. This deliberately
avoids changing the unresolved physical/credited F representation (DATA-030).
That uncertainty remains a disclosed model limitation, not a claim that F gains
are independently verified or removed from the empirical target. Quantify actual
response and remaining uncertainty before any accuracy verdict.

An ignored arithmetic preview from the measured baseline derives every team's
multiplier without name/year knobs. It transforms no charts and is not a fit
prediction. Implementation requires parent review and synthetic failing tests,
then fresh whole-engine measurement with unchanged league/team bounds, tails, caps and policy checks. If the one-pass procedure misses, retain the failure and
investigate its mechanism; do not hand-edit a team's multiplier or select a
favorable seed. Freeze the complete reusable procedure before reserved validation
or prospective 2023 data. The exact-initial alternative above remains available
only after its currently unmet coverage/state assumptions are resolved.

## Renewed runtime and shared-control evidence

After the replay-statistics and auto-learning corrections, a fresh sixteen-schedule
2024 run reproduces the same four yard misses above. It completes 4,352 games
under the current runtime; no reserved family is used. Auto learning changes
Hard's policy, while the chart-focused reference policy disables that analysis.

A separate 1983 shared-control diagnostic uses existing generator settings only:
completion +.045, interception/pressure zero, passing-yard multiplier 1.3 and
rushing multiplier 1.0. All 84 CSVs reproduce; actual source/statistics checks
pass for 28 teams/266 inputs. Source, exact mechanics/tactics and allocation
components pass. Sixteen training schedules complete 3,584 games/256 team-games.
All league bounds pass (completion .565466/.569018, INT .040616/.044138,
sack .080881/.079609, pass 6.972331/7.184595, rush 4.001820/4.089930).
Six team checks still fail: Bears and Packers passing YPA, Falcons completion,
and Colts/Saints/Steelers INT. Maximum errors are .031001 completion, .012798
INT, .008597 sack, 1.186222 passing YPA and .315607 rushing YPA. These are
development diagnostics below the final exposure requirement, not acceptance.

Shared controls are still being investigated before implementing this proposal.
A linearized screen of the current team means gives opposing gain constraints:
1983 pass needs a relative factor at least 1.05646 for Packers but at most
1.05391 for Jets; 2024 rush needs at least 1.03297 for Ravens but at most
1.01025 for Rams. These are arithmetic screens, not proof of infeasibility:
integer allocation, changed game paths, clipping and sampling prevent a linear
response assumption. An additional declared 1983 shared-control trial uses
completion +.049, INT +.003, pressure zero, pass 1.37 and rush 1.0. It tests the
available global controls without a team table or new production behavior.
No manually chosen diagnostic profile is claimed as the frozen transferable
calibration procedure. That procedure, any gain extension and fresh acceptance
evidence still require their stated review and validation.

The second shared-profile 1983 diagnostic completes all 3,584 games, passes all
league and team completion/sack/rushing bounds, and retains four failures:
Bills passing 6.935204/6.021016, Jets 7.542445/6.694097, Packers passing
8.053816/8.912548 and Saints INT .048550/.058824. Maximum passing error is
.914188; the maximum INT error is .010273, just outside the unchanged .01 bound.
It remains training evidence below final exposure, with source byte reproduction
and actual-input checks passing. These results do not establish that a gain-only
extension will satisfy every event-rate check; fresh whole-engine acceptance
and the stated parent review are still required.

## Full-exposure training follow-up (2026-11-06)

The third shared 1983 profile keeps completion +.049, pressure zero, pass 1.37
and rush 1.0, increasing the common INT adjustment from +.003 to +.004. All
source inputs and 84 CSVs reproduce. Sixty-four training schedules now finish
14,336 games/1,024 appearances per team. Every league bound and team event-rate
bound passes, with remaining Cowboys rushing 3.673698/4.078998, Jets passing
7.542358/6.694097 and Packers passing 7.967789/8.912548. Maximum errors are
.944759 passing and .405300 rushing. The sixteen-schedule near-boundary Bills
and Rams misses do not persist as the full-exposure failing set; do not select
or discard a sample because it happens to pass.

The unchanged 2024 shared profile also reaches 64 schedules: 17,408 games/1,088
appearances per team. League means and every team's completion/INT/sack pass,
but passing misses remain for 49ers 7.487650/8.300188, Packers
7.457809/8.223382 and Ravens 7.866283/8.781971, plus Ravens rushing
5.204515/5.756318. Maximum pass/rush errors are .915687/.551802. These are
current training observations under unchanged bounds, not held-out acceptance
or proof of the proposed correction's response. They do not change the proposed
sixteen-schedule derivation, constants or one-pass scope. The gain extension
remains unimplemented pending the stated parent review.

The complete training review also attaches between-repetition standard errors to
each remaining point-bound failure. In 1983, Cowboys rushing exceeds the error
bound by .005300 (SE .024939), Jets passing by .098261 (SE .057723), and Packers
passing by .194759 (SE .057748). In 2024, 49ers passing exceeds it by .062537
(SE .059910), Packers passing by .015573 (SE .054860), Ravens passing by .165687
(SE .065842), and Ravens rushing by .151802 (SE .033229). These are sampling
variability summaries, not replacement confidence-interval acceptance rules; all
seven point failures remain. The arithmetic uniform-scale screen at full
exposure gives opposing 1983 pass requirements (at least 1.024443 from Packers,
at most .986972 from Jets), 2024 pass requirements (1.021063 Ravens versus
1.018804 Dolphins), and 2024 rush requirements (1.029167 Ravens versus 1.005242
Rams). This screen assumes a linear response and does not prove engine
infeasibility; it makes no prediction of the proposed one-pass method's response.

The current shared profiles are development choices, not the prospective
transfer procedure. Existing `tune_charts.py` can select shared controls, but it
automatically runs its configured validation command afterward and assesses
league targets only. Do not use it to open a charter-reserved family during
calibration. The complete frozen procedure still needs a declared automatic
shared-profile selection step, stopping/selection rules and training-only seed
history alongside any approved gain extension before prospective 2023 evaluation.

## Proposed complete training recipe for parent review

This section closes the previously unspecified shared-profile selection step.
It is a proposed version-1 procedure, not a declaration that the current manually
selected profiles implement it. The full-exposure measurements above belong to
earlier recorded runtimes; the latest special-teams corrections require fresh
measurements. No reserved or prospective outcomes informed the following rules.

Start every cohort from `CalibrationProfile()` defaults. Use only reconciled
public inputs, the source schedule, the fixed chart-focused policy and sixteen
training repetitions derived from master 20261108. Every evaluated candidate must
pass source reproduction, exact mechanics, allocation and receipt reconciliation
before its statistical objective can be considered. Missing support or a failed
game stops the procedure with a recorded failure; neither becomes an omitted
candidate. Cache only identical complete input/runtime/profile identities.

Use the existing deterministic calibration order: completion, interception,
pressure/sack rate, passing YPA, rushing YPA. Proposed common search bounds and
steps are:

| Shared control | Inclusive bounds | Step |
| --- | --- | --- |
| Completion adjustment | -.08 to .08 | .005 |
| Interception adjustment | -.02 to .02 | .001 |
| Pressure adjustment | -.04 to .04 | .002 |
| Passing-yard multiplier | .70 to 1.60 | .05 |
| Rushing-yard multiplier | .70 to 1.30 | .025 |

For the first league metric outside its unchanged tolerance, move its associated
control one step toward the target, as `propose_next_profile` does. Clamp to the
bounds using exact decimal ticks. Record the proposed profile before evaluation.
Stop at the first evaluated profile that meets all five league tolerances, or
after at most 32 distinct evaluated profiles including the initial profile.
A duplicate proposal, a saturated required move or exhaustion stops as a failure;
do not fall back to a manually selected profile or automatically open validation.
If several already evaluated passing profiles exist because of a resumed run,
select the earliest in the recorded deterministic sequence. There is no
team-name/year table, manual restart, arbitrary best-seed choice or unrecorded
change of objective. All team errors and distribution diagnostics are retained;
league success at this stage is only eligibility for the next step.

Use the first eligible profile and its sixteen-repetition measurements as the
single engine baseline for the bounded team gain derivation above. If every
league/team target already passes, retain that unnormalized candidate. Otherwise,
provided the independent source/credit review is complete, derive the proposed
one-pass ordinary-gain multipliers with pseudo-count 200 and bounds [.8, 1.25].
Primary F/QT and all protected event families remain fixed. Do not rerun the
shared-control search after this derivation or repeatedly fit the residuals.
Regenerate and measure the resulting candidate on all 64 training repetitions.
Every fixed league and team bound, supported tail requirement and exact gate
must pass. Failure is an explicit unsuccessful procedure result, not permission
to change constants, rerun until favorable, or enter reserved validation.

The release gate must receive the entire ordered training history, stopping
reason, derived parameters, input/chart/runtime/report hashes and protected-family
comparisons. Synthetic tests must reject skipped candidates, altered order,
reserved seeds, a 33rd evaluation, repeated profiles, missing receipts and a
bad individual team hidden by a passing league. Renaming an otherwise identical
synthetic cohort must preserve the recipe. Review the finite-row response,
quantiles, cap saturation and unsupported physical/credited fumble assumptions
before interpreting a successful point fit. Only after a complete freeze and
parent announcement may the existing reference, held-out and prospective transfer
protocols run. This proposal changes no acceptance bounds. The full recipe
remains unimplemented; the isolated components below do not perform it.

## Implemented isolated components (2026-11-06)

`paydirt/gain_normalization.py` implements only the complete-cohort arithmetic
and deterministic offense transformation described above. It has no caller in
chart generation, the engine, the API or a review service. It cannot establish
source support, eligibility of a baseline, the ordered shared-profile search or
statistical acceptance. No real-team coefficients have been derived.

`GainBaseline` carries explicit source support and positive integer credited
numerators/attempts for both metrics. The derivation rejects missing, extra or
duplicate cohort members, missing metrics, unsupported records and nonphysical
means. It reports every input, weighted anchor, unconstrained adjustment, clamp
and multiplier. Computation uses binary64 log/exp, sorted `math.fsum` terms,
pseudo-count 200 and bounds [.8, 1.25]. Renaming or reordering identities leaves
the corresponding results unchanged.

The transformation accepts a complete eleven-column allocated offense and
returns a fresh copy. Only ordinary numeric primary gains and numeric rushing
breakaway gains change. It preserves symbols, flags, numeric signs/zeroes,
primary F/F INC/QT and the whole QB-time column. Defense, special teams and
recovery ranges are outside its input. Binary64 multiplication uses nearest
integer, ties to even, with the existing positive direct-run cap of 18 and
other numeric limits of [-99, 99]. Every rounding/cap effect is recorded.
Per-column reports retain full physical dice-weighted token masses and numeric
means, zero/loss shares, 20+/40+ tails and quantiles. Conditional numeric means
are not whole-game credited YPA.

Synthetic tests cover the formula, complete membership, support and input
validation, permutation/renaming, identity controls, positive/negative rounding
ties, caps, flags and protected families. Independent physical-face expansion
checks weighted distributions, and altered-tail/protected-token mutants must
fail those checks. Both clamped optima are compared with 1,001 feasible log
adjustments. No private or historical input is used in unit tests.

The test-first baseline had 44 expected missing-component failures and two
passing fixture controls. Two later behavior regressions first demonstrated
four missing physical-mean rejections and an enormous-integer factor raising
OverflowError instead of ValueError; their controls passed. Two synthetic
fixtures were corrected without changing assertions: 39 became 49 to cross
the intended 40-yard tail after scaling, and impossible means of 100 became
10/.1 while preserving the reciprocal ratio and clamp expectation. The final
focused component and relevant allocation/calibration suites pass 133 tests.
Ignored local receipts retain all failing baselines and subsequent runs.

The complete recipe above remains unimplemented. In particular, a manually
selected profile outside the proposed automatic bounds cannot be relabeled as
its first eligible baseline, and a 64-schedule diagnostic cannot substitute for
the specified sixteen-schedule pooled derivation. Current modern source/fit
diagnostics and historical unsupported events retain their existing limits.
No held-out or prospective family has been opened. A future integration still
requires eligible complete source/baseline receipts, the ordered training
history, protected/distribution checks, fresh whole-engine validation and review.
Adding this ordinary module also changes the broad engine fingerprint; earlier
reports retain their original runtime identity.

This work changes no player controls, API behavior or installed workflow, so
no player-guide update is required.

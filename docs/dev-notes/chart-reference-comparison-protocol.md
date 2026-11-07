# Stable-candidate comparison with developer reference charts

Owner-requested extension to the [chart-confidence assignment](chart-confidence-agent-charter.md),
2026-11-05. This is a planned local benchmark, not evidence of completed comparison
or release readiness.

## Timing and purpose

After source/mechanics/allocation corrections and a stable training candidate,
freeze the engine, candidate inputs, profiles, chart files and comparison policy.
Compare against the available developer reference corpus before the final owner
review. Prefer completing this benchmark before opening the reserved final
source-validation seeds. Any subsequent production/profile change invalidates
affected evidence and requires a new freeze; opened validation families cannot
be reused as untouched validation.

The reference charts provide an independent behavioral benchmark, not an
instruction to copy their cells or reproduce every authored assumption. Measure
both sets against supported historical targets. Explain where generated charts
improve source fit, lose fidelity, reflect deliberate model choices or remain
unverified. A different seeded layout or a different count of colored cells does
not by itself establish a behavioral error.

## Corpus and privacy

- Paydirt: census the complete local 1983 developer corpus and match all 28 teams
  to the generated 1983 candidate. Verify mappings, season rules, all chart
  sections and the actual inventory; report any absent or unreadable reference
  rather than silently omitting it.
- Bowl Bound: the owning BB session should use its local 2007 and 2008 Mayfield
  charts as reference corpora, census matched generated/reference teams by year,
  and disclose any unavailable generated counterparts or data support. BB owns
  its implementation and interpretation under its own rules.
- Never modify original charts to improve the benchmark. Hash local references
  for reproducibility in ignored reports. Record engine/decoder versions and
  flag unsupported legacy symbols or fallback behavior, which limit what an
  engine-based comparison can establish about the authored game.
- All reference cells, extracts, hashes, per-team comparisons, simulation logs,
  charts and rendered reference screenshots remain local in ignored
  `.ai-audits/chart-reference-comparison/`. Do not commit, publish or transfer
  private charts, workbooks or reference-derived artifacts between projects.
  Share methodology and appropriate high-level findings through the existing
  authorized exchange. Unit tests use synthetic/public-2026 fixtures; the
  historical corpus runs only in explicit standalone local integration tools.

## Comparison layers

1. **Physical weighted chart behavior:** compare all offense calls, formations,
   B/QT/recovery mechanisms and special teams using the real dice weights.
   Report incompletion, interception, fumble/recovery, pressure, penalty,
   touchdown and out-of-bounds masses; conditional and unconditional yield;
   losses, zero gains, first-down opportunities and explosive-gain tails.
   Keep pending/unknown branches visible. Include special-team distributions
   and field-goal distance curves where supported. Raw cell-match percentage is
   descriptive only, never the accuracy score.
2. **Offense/defense interactions:** use matched, controlled contexts to compare
   reference offense/reference defense, generated offense/reference defense,
   reference offense/generated defense and generated offense/generated defense.
   This distinguishes offense changes, defense changes and priority interactions.
   Include ordinary field position, backed-up and goal-line contexts; apply
   field clipping, recovery and scoring through the authoritative engine.
   Check strength ordering, formation costs/benefits and repeated-call exploits.
3. **Paired full-engine games:** use the same actual schedule, independently
   seeded game pairs, source-year rules and declared measurement policy for
   pure-reference and pure-generated cohorts. Keep normal call policy fixed for
   the main comparison; assess chart-aware AI as a separate sensitivity study.
   Identical initial seeds do not imply identical later dice or calls once game
   paths diverge. Every game must finish and reconcile authoritative totals.
4. **Source and team-level comparison:** show both sets against the same supported
   historical targets, league and individual-team errors, rankings and worst
   deviations. Include score/pace and distributional diagnostics while stating
   the limits of available source targets and coaching assumptions. Do not
   substitute reference agreement for source fidelity or claim route-level
   truth from gain-based family inference.
5. **Visual review:** provide local side-by-side offense/auxiliary, defense and
   special-team views, with weighted summaries explaining large color blocks.
   Select Dolphins 1983 plus the largest behavioral deviations and representative
   strong/weak teams. The full corpus is checked automatically; the owner needs
   only a compact visual review set.

For Paydirt's main full-engine reference-policy comparison, use 64 complete
1983 source-schedule repetitions per chart set (14,336 games per set, 1,024
team-games per team). Reserve separate comparison master **20461108**, with
documented independent game/repetition derivation. This is distinct from the
final source-validation family. Smaller diagnostic samples must be labeled
insufficient for the final reference benchmark. BB should declare comparable
exposure and uncertainty appropriate to its available cohorts and schedules.

## Validate the generation method beyond the reference corpus

The owner explicitly emphasized transfer to seasons without developer charts.
The baseline is therefore a valuable development and validation dataset for the
generation scripts, not merely a final visual comparison. Add the following
evidence before claiming confidence in that transfer:

- Separate three kinds of validation: fresh game seeds test simulation estimates;
  withheld teams test whether the same procedure works beyond known teams; and
  an additional season tests transfer across a new input population/rules/schema.
  Passing one is not evidence that the other two were performed.
- Declare team partitions before inspecting their reference comparisons. Use
  stable identifiers and a documented split, not favorable selections. If earlier
  investigations already inspected those teams or seasons, label the exercise
  retrospective cross-validation rather than an untouched holdout. Use all 28
  teams for the final private report, with partition and prior-use history visible.
- Freeze the versioned generator, adapters, automated calibration procedure,
  hyperparameters, bounds and validation definitions before transfer evaluation.
  Baseline findings may motivate general source/model corrections; they must not
  become copied cells, team-ID lookups or hand-authored season/team overrides.
  A team-specific parameter is acceptable only when the same documented,
  reproducible procedure derives it from that team's available source inputs.
  Generated profiles must record those inputs and the derivation.
- Reserve **2023** as Paydirt's prospective additional public-source season.
  No named 2023 artifacts or season directory were present when this was chosen.
  Do not inspect its generated outcomes until the procedure is frozen. The
  production procedure may use its source statistics, as it would for any new
  season, including any already-frozen automatic calibration step. It may not
  receive manual adjustments based on transfer-test results or reference charts.
- Generate the complete available 2023 cohort in ignored staging with the correct
  year rules, source provenance and normal schema/capability checks. Run with
  private reference inputs unavailable to prove they are not a runtime dependency.
  Apply the same league and team source-supported limits, exact behavior checks
  and source/accounting requirements. Use final transfer master **20561108** and
  64 complete source-schedule repetitions, with at least 1,000 team-games per team.
  Do not promote this extra season into the release merely because it was tested.
- If the transfer test exposes a defect that changes the procedure, keep the
  failed result, classify 2023 as development evidence, and reserve a different
  untouched season before the next prospective transfer claim. Do not repeatedly
  tune to one validation season and continue to call it unseen. Missing source
  support or an unavailable independent target is a disclosed coverage failure,
  not a fabricated pass or a reason to select a conveniently passing cohort.
- Exercise synthetic grids and metamorphic controls for sparse/zero counts,
  mobile/pocket QB mixtures, extreme strengths, rare events, missing annotations,
  physical quantization and format/rule changes. Supported changes must preserve
  expected risk/strength directions; unsupported or infeasible inputs must fail
  clearly. Names may affect the declared seed/layout, never select hidden fitted
  behavior. The generator must diagnose unsupported data before publication.
- BB should apply the same separation to its own 2007/2008 Mayfield references
  and prospective seasons under BB rules. Its owning session currently reports
  two normalized reference teams per year, four total; census raw workbooks as
  well as normalized charts before claiming complete available coverage. Report
  this sample limitation explicitly. BB evidence does not substitute for Paydirt
  validation, or vice versa.

Passing these checks supports transfer within the tested source/rule capabilities;
it cannot guarantee every historical era or missing-data regime. Each subsequently
generated season must run the same source and behavior gate and declare its
support limits. A one-off good chart set is not the end state.

## Required handoff and interpretation

Produce a private machine-readable report and a concise owner-facing explanation
of corpus coverage, fingerprints, weighted deltas, paired estimates/uncertainty,
team outliers, source-fit differences, special teams, fallback/coverage limits
and a few local visual comparisons. Use paired game/season sampling for
uncertainty rather than treating all plays as independent. Keep precise
denominators and sample sizes attached to every rate.

Classify material discrepancies as confirmed defect, supported improvement,
declared modeling choice, source uncertainty or unresolved behavior. Investigate
unexplained large effects; record issues and retain the release hold for
unresolved serious behavior. There is no invented universal "must match the
developer chart within X%" criterion. Existing source-accuracy limits and all
other acceptance requirements remain unchanged.

The benchmark is complete only when the full available corpus was included,
counts and games reconcile, material outliers have been reviewed, and the
candidate's limitations and source-fit verdict are clear. It supplements the
source/behavioral release gate and final independent review; it cannot replace
them.

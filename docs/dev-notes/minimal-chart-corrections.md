# Proposed Best Practice: Minimal Team Chart Corrections

Discussed with the owner November 9, 2026. This is a proposed calibration
fallback, not an implemented automatic correction or proof of historical accuracy.

## Purpose and When to Use

A single team may not fit a shared season calibration profile. After the bounded
global calibration search, consider a minimal, reproducible team-specific chart
correction rather than repeatedly adjusting the entire cohort. Use measured
source-to-engine residuals, not desired wins, standings or playoff qualifiers.
See the [active calibration/release goal](1977-calibration-release-goal.md) and
[calibration reference](../chart-calibration.md).

Prefer an explicit generator override or deterministic post-generation
transformation over an untracked hand edit. Retain the original chart and source
facts, identify the transformation in generation provenance, and reproduce the
final output independently. A correction changes the model, not the historical
source record.

## First Check: Independent Seeds Before Any Team Edit

The owner proposed this additional step before changing an individual chart.
Freeze the selected chart bytes, calibration profile, policy and schedule, inventory
previously used seeds, and predeclare one genuinely unused seed batch. For the
current 1977 diagnostic, use 16 independent repetitions (3,136 games), without
changing coefficients or regenerating charts.

Compare the outlier's counts, rate and replication uncertainty, plus the other
teams' metrics, against the preserved original evidence. A changed seed can
produce different trajectories and apparent boundary crossings; investigate
whether the difference is compatible with sampling/context variation before
attributing it to a chart defect. A small independent batch cannot prove the
absence of bias or replace the larger failed qualification report.

Retain both results, including failures. Do not try seed after seed, select the
most favorable batch, or erase an earlier miss because the new batch passes.
Any aggregation needs compatible methods and an explicitly stated analysis;
no repeated sample extensions merely to reach compliance. This robustness
check precedes a team edit, not an open-ended additional calibration search.

### Evidence Threshold: Persistent Bias, Not a Test-Run Patch

The owner clarified that the last-resort correction requires evidence that it
would improve the model, not merely make a particular simulation run pass.
Repeated same-direction residuals for the same team and metric across independent
seed batches strengthen the case for a systematic problem. They do not alone
prove the chart is responsible: stable policy, opponent exposure, source coverage
or accounting effects also need consideration.

If failing teams move around, residuals reverse, or boundary crossings are
consistent with the measured sampling variability, do not edit charts to chase
those runs. Retaining the existing candidate with honest uncertainty and any
explicitly authorized statistical exception may be the appropriate outcome.
There is no requirement to make every finite dice sample match history.

Compare effect sizes, directions, attempt counts and replication uncertainty,
not just pass/fail labels. Only propose a correction after identifying a plausible
chart mechanism and an expected benefit that can be checked on independent
samples. Preserve all prior failures. This criterion overrides any interpretation
of the swap procedure as an automatic repair for a failing test.

## Suggested First Choice: Within-Column Swaps

For an excessive interception rate, first examine swapping an INT result with an
ordinary incompletion in the **same passing-play column**, moving the INT to a
lower-probability row. For a low rate, examine the reverse direction. This changes
interception/incompletion mass without directly exchanging completion, yardage,
penalty, fumble or quarterback-time outcomes.

Keep the original play-appropriate INT distance. Do not move a screen INT into
another play family or introduce an implausible catch distance. Generated charts
use `BLACK` as the ordinary incompletion token, so it is an eligible donor; keep
that token rather than substituting a differently interpreted symbol. Its combined
priority behavior must still be checked. Avoid numeric completions, QT, penalties,
fumbles and compound retained-fumble incompletions (`F INC`) when an ordinary
incompletion swap can achieve the purpose. Preserve complete tokens and modifiers;
a swap is not permission to simplify an unrelated outcome.

**Adjacency alone does not determine impact.** Use the actual row weights from
[`chart_roll_weights()`](../../paydirt/play_resolver.py). Adjacent rows can have
equal weights and produce no probability change. Across-column swaps change
play families and are not the preferred correction.

### Hypothetical Probability Example

Offense chart rolls have 216 equally likely underlying dice combinations:

| Row | Weight | Hypothetical original | After swap |
| --- | ---: | --- | --- |
| 12 | 4/216 | Ordinary incompletion | INT |
| 13 | 5/216 | INT | Ordinary incompletion |

The raw offense-column interception lookup probability falls by
`(5 - 4) / 216 = 1/216`, approximately **0.463 percentage points**.
This is a hypothetical arrangement, not a claim that these two cells are valid
donors in the current Washington chart.

For a swap from INT row A to ordinary-incompletion row B, the raw change is
`(weight[B] - weight[A]) / 216`. Equal weights mean zero raw change. The minimum
nonzero difference available in this dice system is one combination; a suitable
legal donor pair may require a larger difference.

This is **not** an equal-sized change to season interception rate. Call share,
defensive contributions, priority resolution, attempt denominators, legal
situations and changed game trajectories affect the realized rate. Use exact
combined mechanics and simulations to establish the actual effect.

## Least-Impact Selection Procedure

1. Freeze the candidate, target, observed residual and sample evidence. Confirm
   the remaining problem is persistent enough to justify a team-specific model
   correction rather than small-pilot variation or an engine/selection defect.
2. Enumerate valid same-column INT/incompletion swaps. Rank by smallest useful
   absolute weight difference, affected scope and expected combined effect.
   Do not choose a row merely because it is nearby or visually convenient.
3. Recompute exact combined offense/defense distributions for affected plays and
   formations, using the actual dice and priority rules. Report unrelated changes
   too; a raw token swap does not prove every resolved category is unchanged.
4. Choose the smallest justified correction. Preserve distance constraints,
   source totals, protected outcomes and all other teams' chart bytes. Avoid a
   broad search over bespoke team edits.
5. Implement a deterministic, hash-bound correction. Add synthetic/public-team
   test-first controls for the transform, expected weighted change, unchanged
   tokens and rejection of an unexpected source chart; obtain medium-reasoning
   Codex review. Independently reproduce final chart bytes.
6. Validate on unused seeds and inspect the corrected team's other metrics,
   all affected play/defense combinations, league impact, scoring and ordering.
   Do not claim a successful correction solely from the sample used to select it.
7. Retain the original and corrected evidence. If no small correction is
   justified or it harms other behavior, report that result and use only an
   explicitly approved, disclosed statistical exception where applicable.

If the remaining discrepancy is another metric, an INT/incompletion swap is not
automatically appropriate. Choose a transformation matched to that mechanism
and establish its protected quantities separately.

## Season Notes and Provenance

If applied, create a public `NOTES.md` in the generated season directory and bind
the transform in the generation manifest or an equivalent reviewed recipe.
Record:

- Season/team, affected column and original/new rows and complete cell tokens.
- Historical target, original measured rate, tolerance, sample counts and reason.
- Original/new dice weights, expected raw change and exact combined-mechanics
  effect, with assumptions and limitations.
- Original and final chart SHA-256 values, transform identifier/version and
  reproducible invocation or recipe.
- Protected token/event checks, source/reproduction evidence, independent
  validation seeds and measured before/after results.
- Review evidence, remaining failures and whether release acceptance uses an
  explicitly authorized statistical exception.

Keep raw PBP, private narratives and large diagnostic reports in ignored audit
storage. Public season notes should contain reviewed methodology and aggregate
results, not private source material. Update the calibration reference when a
corrected season is released, so its profile alone is not mistaken for the
complete reproduction recipe.

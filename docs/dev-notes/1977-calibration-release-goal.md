# Goal: Finish 1977 Calibration and Release v1.10.4

Owner-authorized November 9, 2026. This is an active development/release goal,
not a statement that charts or installers have passed validation.

## Objective and Budget

Try approximately five adaptive global interception-calibration values. Stop early
when a candidate meets all applicable pilot bounds. If none passes within the
budget, select the best evidenced value and ship with its statistical limitations
explicitly disclosed, after canonical generation, required regression and native
acceptance of the actual published downloads.

Count the running candidate-07 midpoint (`0.00275`) as trial one of at most five.
Prior endpoints candidate-05 (`0.004`) and candidate-06 (`0.0015`) inform the
search but do not consume additional trials here. No token budget was specified;
the trial cap bounds the numerical search.

## Fixed Comparison and Adaptive Decisions

- Use the same 16-repetition, 3,136-game schedule and seed `24261120` for each
  screening trial. Preserve inputs, engine identity, previous charts and reports.
- Vary only the shared `pass_interception_adjustment`. Keep completion `0.049`,
  pressure `0.0`, pass gain `1.44`, run gain `1.15`, and the frozen candidate-05
  cohort gain recipe fixed for these diagnostic comparisons.
- Record each next value and rationale before running it. Move up or down from
  whole-cohort evidence, not Washington alone. No team-specific edits during the
  global search, changed targets, loosened tolerances or favorable-seed selection.
- Prefer candidates passing all league bounds, then compare number of failed
  team metrics, maximum normalized error and summed normalized errors. Report
  counts and scoring alongside the ranking. Retain failures and uncertainty.
- Stop after at most five trials or earlier if all pilot bounds pass. Do not add
  coefficient sweeps or repeatedly extend samples to obtain a favorable result.

The frozen-recipe wrapper remains explicitly noncanonical and nonqualifying.
Matching all 84 CSVs through it establishes diagnostic repeatability, not canonical
source-bundle reproduction. Retain exact recipe/hash/guard-exception disclosures.

## Last Resort: A Documented Single-Team Correction

See the [proposed minimal-correction procedure](minimal-chart-corrections.md) for
weighted within-column swaps, safeguards, validation and season-note contents.

The owner subsequently authorized a single-team chart correction as a last resort
when one team does not fit the global calibration pattern. Complete the bounded
global search first and compare the existing candidate-05/06 references too; do
not replace stronger prior evidence with a favorable small pilot.

Before any individual chart edit, run one predeclared independent seed batch
against the frozen selected candidate (currently 16 repetitions / 3,136 games).
Preserve and compare the original evidence and replication uncertainty; do not
replace the larger failed report with a favorable small batch or search seeds.
This is a robustness diagnostic, not another coefficient trial or automatic
qualification. See the minimal-correction procedure for interpretation limits.

A team-specific correction is justified only by persistent, same-direction
team/metric bias across independent samples and a plausible chart mechanism.
Moving failures or changes consistent with sampling variability are reasons not
to edit charts. Never apply a correction merely to make a particular run pass;
retain uncertainty and the owner's disclosed-exception route when appropriate.

If one persistent outlier remains, prefer a minimal reproducible generator override
or exact post-generation transformation over an untracked CSV edit. Record the
team, affected event/play families, historical target, reason, original and adjusted
weighted probabilities, unchanged interception-distance constraints, transformation
identity, chart hashes and validation results in the published season's `NOTES.md`
and generation provenance. Do not change raw source facts or force wins/playoff
qualification. Keep source narratives and detailed private reports ignored.

Use unused validation seeds and inspect the team's other metrics, all affected
formations and league impact. A correction must not merely fit the same pilot
used to choose it. Scope and tests should protect unrelated outcomes; actual
medium-reasoning review remains required. This is not permission for a broad
set of bespoke team edits or another unbounded parameter search. If the correction
is not justified or still misses, the documented ship-best statistical exception
below remains available.

## Canonical Candidate and Release Acceptance

After selection, regenerate through the canonical source adapter, including its
normal cohort-recipe training, then independently reproduce the charts. Disclose
and evaluate changed derived gain factors; diagnostic results need not transfer
unchanged. Preserve source provenance, reviewed exclusions, strict diagnostics
and screen-interception constraints.

Run an appropriate predeclared final sample against unchanged statistical bounds.
For the current 14-game chart-focused component gate, 72 repetitions provide the
minimum 1,008 team-games per team. Distinguish this characterization from held-out,
tactical and other release requirements.

The owner explicitly authorizes shipping the best finite-search candidate with
documented statistical misses if none passes. This is a narrow release acceptance
exception, not permission to mark failing accuracy results PASS. Bind it to the
selected chart/profile identities; list measured values, targets, tolerances and
limitations; preserve failed reports. No blanket exception for future charts.

This does **not** waive source/provenance checks, functional correctness, decoder
checks, interception-distance safety, game completion, required integration
regression or native published-installer acceptance. Fix those failures or report
a concrete blocker; the statistical exception does not excuse them.

Complete the [release plan](release-1.10.4-plan.md), including VAL-023 Windows
normal-shutdown verification. Use the authorized unchanged-released-chart
regression distinction for existing 1983/2024 charts. Follow AGENTS.md for
pushes, immutable tags and acceptance of actual release-page downloads across
all required platforms/package forms. Preserve the owner's running game.

## Ownership, Evidence and Handoff

- `/root/release103_fixes`: adaptive trials, comparisons, receipts, selection.
- `/root/release_1_10_3_finish`: canonical generation, integration, documented
  exception if needed, full regression, publication and native asset acceptance.
- Root: oversight, consequential decisions, documentation and final status.

The active goal was created in the calibration agent's thread. The root thread's
older blocked AI-026 goal was not falsely marked complete or overwritten.

Keep raw sources/reports ignored under `.ai-audits/chart-generation/1977-reviewed/`.
Update the [1977 record](1977-season-feasibility.md),
[DATA-046](issues/DATA/DATA-046.md) and [calibration reference](../chart-calibration.md)
with selected values, actual results and release status.

Routine checkpoints do not end the assignment or require the owner to restart it.
Stop at a verified release or an actual consequential blocker. Final handoff must
give the release URL, commit/tag, tested packages, known limitations and a clear
announcement-readiness status. Implementation uses low reasoning; code reviews
use medium reasoning.

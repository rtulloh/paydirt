# Chart Calibration: Process and Reference Profiles

[Documentation index](README.md) · [Generation workflow](chart-generation-workflow.md) · [Generator reference](chart-generator.md)

Calibration changes generator settings, regenerates fixed charts, and measures them through the
game engine. It does not adjust a player's outcomes during a game. This guide records practical
experiment controls and verified starting values. The linked generation workflow, applicable
versioned validation contract, and [AGENTS.md](../AGENTS.md) govern qualification and release.

## Controls and Units

Both source adapters accept `--calibration-profile PATH`, loading JSON through
[`CalibrationProfile`](../paydirt/chart_tuning.py). Explicit adjustment flags override profile
values. The manifest records the effective `calibration_profile`.

| JSON field | Neutral | Meaning |
| --- | ---: | --- |
| `pass_completion_adjustment` | `0.0` | Additive empirical completion-probability adjustment. |
| `pass_interception_adjustment` | `0.0` | Additive empirical interception-probability adjustment. |
| `pass_pressure_adjustment` | `0.0` | Adjustment to the pass-event pressure model. |
| `pass_yard_multiplier` | `1.0` | Scale resolved passing gains during generation. |
| `run_yard_multiplier` | `1.0` | Scale eligible primary rushing gains during generation. |

Probability adjustments use fractions: `0.004` means **0.4 percentage points**. Reducing it by
0.25 percentage points gives `0.0015`. This is not a relative percentage change. The realized
season-rate change need not equal the adjustment: allocation, QB Time, attempt denominators,
opponents and call selection intervene.

Inspect family coverage before interpreting a coefficient. The run control covers empirical
primary runs and, after the fallback correction, aggregate primary run columns lacking empirical
input, without scaling empirical columns twice. It does not scale QB Time or the shared
breakaway column. QB Time includes sacks and scrambles. The interception offset currently
adjusts empirical pass families; it is not a general aggregate-fallback pass control. All five
primary pass families have empirical input for all 28 reviewed 1977 teams.

## Released Starting Profiles

Verified against manifests and contracts at **v1.10.3**, commit
`1467b11e151fe9981177890e2a7a6b805402b3f0`:

| Setting | Released 1983 | Released 2024 |
| --- | ---: | ---: |
| `pass_completion_adjustment` | `0.049` | `0.085` |
| `pass_interception_adjustment` | `0.004` | `0.006` |
| `pass_pressure_adjustment` | `0.0` | `0.0` |
| `pass_yard_multiplier` | `1.37` | `1.10` |
| `run_yard_multiplier` | `1.0` | `1.01` |
| Generator seed | `8306` | `8306` |
| Opponent-effect shrinkage | `24.0` | `24.0` |

Authoritative records:

- **1983:** [generation manifest](../seasons/1983/generation-manifest.json),
  [validation contract](../config/chart-validation/1983.json).
- **2024:** [generation manifest](../seasons/2024/generation-manifest.json),
  [validation contract](../config/chart-validation/2024.json).

The manifest calls these values `calibration_profile`; the contract calls them `generation_profile`.
These are the released values, rather than older profiles in dated development summaries.
They are starting hypotheses for a new season, not universal defaults or proof of accuracy.

A profile alone cannot reproduce a release. Bind source bytes, generator/runtime version,
policies, source scope, normalization and post-generation transformations too. Both released
sets include an **INT-location-only migration**, recorded under `post_generation_transforms`,
which preserves event masses. Reusing the profile without that migration does not establish
identical released chart bytes. Public sanitized manifests retain original-manifest hashes while
omitting private input inventories.

Known released exceptions remain explicit: 1983 San Francisco/Atlanta completion and 2024
Baltimore rushing. Copying those coefficients does not waive a new candidate's bounds. See
[unchanged released-chart regression](released-chart-regression.md) for the separate regression
route; new or changed charts still require candidate qualification.

## Bounded Calibration Cycle

1. **Freeze the evidence and question.** Record source/chart hashes, source policies and
   exclusions, engine/generator identity, profile, schedule, AI policy, seeds, sample size,
   targets and tolerances. Preserve prior candidates and failed results in ignored `.ai-audits/`.
2. **Measure the neutral baseline.** Check source coverage, decoder/loadability, accounting,
   gross/net passing and sack denominators before adjusting coefficients. Compare any transferred
   historical profile against this baseline.
3. **Run a paired screening pilot.** Hold schedule, seed family and policy fixed. Four repetitions
   offer inexpensive screening; the documented 16-season pilot gives a stronger comparison.
   Neither qualifies a release. Fixed seeds do not force identical game paths after chart changes.
4. **Explain the residual.** Inspect league/team metrics, counts, replication variability, family
   coverage, fallbacks, defenses and call mix. Fixed-context comparisons help distinguish chart
   effects from selection effects. Review scoring, pace, field goals and team ordering too.
5. **Change one justified component.** A historical/observed YPA ratio can suggest a gain factor,
   but rounding, caps and protected outcomes make it approximate. Fix missing calibration coverage
   before increasing factors. Avoid hand-selected team factors, forced winners, blind sweeps or
   tuning away an engine/AI defect.
6. **Regenerate and compare the complete cohort.** Check new low-side failures as well as
   improvements, event masses, protected outcomes and screen-interception constraints. Independently
   reproduce output. Implementation changes require test-first regressions and code review.
7. **Qualify a frozen candidate.** Apply the contract's samples and unused validation seeds,
   complete its calendar/postseason, then the full release regression. New profile/source changes
   invalidate relevant previous evidence. A passing pilot is insufficient.

Predeclare a finite experiment and sample budget. Justify any extension from measured uncertainty
before running it and retain prior replications; do not keep extending or selecting seeds until
a failure turns favorable. The standard training/held-out plan in the generation workflow remains
distinct from these screening experiments.

### Schedule Length and Samples

The chart-focused component gate requires at least 64 repetitions **and** 1,000 team-games per
team: `max(64, ceil(1000 / games_per_team))`.

| Games/team/season | Minimum repetitions | Team-games/team |
| --- | ---: | ---: |
| 14 | 72 | 1,008 |
| 16 | 64 | 1,024 |
| 17 | 64 | 1,088 |

For 1977, 4 × 196 regular-season games = 784 games, 16 repetitions = 3,136, and 72 = 14,112.
More samples improve precision; they do not fix systematic bias or replace source, tactical,
held-out, gameplay and packaged-release acceptance.

## Whole-Cohort Gain Recipe

The optional `--gain-normalization-contract` procedure is separate from the five global controls.
It uses source-only targets, 16 complete-cohort training repetitions, source-attempt weighted
centering, shrinkage `200`, and derived gain factors bounded to `[0.8, 1.25]`. It accepts no
hand-edited team factors. See [the exact recipe](chart-generator.md#optional-source-driven-gain-normalization)
for scope, hashes and protected outcomes.

Canonical generation reruns the recipe for a new profile; there is currently no frozen-recipe CLI.
Changing an interception adjustment can therefore change training trajectories and derived gain
factors too. Record this coupling rather than claiming only one component changed.

A local diagnostic wrapper may hold the previous recipe fixed to isolate a coefficient, but its
receipt must identify the wrapper, frozen recipe and **noncanonical, nonqualifying** status.
Any proposed release candidate still needs canonical generation, reproduction and qualification.
Never present a wrapper experiment as canonical source-bundle reproduction.

## 1977 Experimental Reference

Recorded 2026-11-09; these are development references, **not released profiles**:

| Stage | Completion | INT | Pressure | Pass gain | Run gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| Neutral candidate-01 | `0.0` | `0.0` | `0.0` | `1.0` | `1.0` |
| 1983 transfer, candidate-02 | `0.049` | `0.004` | `0.0` | `1.37` | `1.0` |
| Gain correction, candidate-03/04 | `0.049` | `0.004` | `0.0` | `1.44` | `1.15` |
| Cohort-normalized candidate-05 | `0.049` | `0.004` | `0.0` | `1.44` | `1.15` |
| Requested candidate-06 diagnostic | `0.049` | `0.0015` | `0.0` | `1.44` | `1.15` |

Candidate-04 corrects Draw fallback coverage with candidate-03's profile. Candidate-05 adds
the cohort recipe. Its 144-repetition run completed 28,224 games: all five league metrics and
139/140 team metrics pass, but Washington interceptions remain outside tolerance and scoring
remains elevated. Candidate-06 is an authorized experiment, not a validated result at this checkpoint.

The [1977 experiment record](dev-notes/1977-season-feasibility.md) and
[DATA-046](dev-notes/issues/DATA/DATA-046.md) track current findings. Exact inputs, profiles,
recipes, seeds, sample counts and receipts remain in ignored
`.ai-audits/chart-generation/1977-reviewed/`. Update released values from the final manifest
and immutable release identity when a new season is published; retain failures in the development record.

# Release 1.10.3: controlled simulation improvement

Status: approved direction; first two offense candidates rejected in development.
Recorded November 7, 2026. Begin after release 1.10.2 is completed and verified.
This is a developer plan, not a description of shipped behavior.

## Goal

Improve simulation fidelity through demonstrated football mechanisms, working
one issue and one bounded change at a time. Start with
[AI-026](issues/AI/AI-026.md): Hard AI does not adequately respond to its own
defensive strengths or the opponent's offensive/defensive chart strengths.
Demonstrate incremental improvement in controlled season simulations before
expanding to another mechanism or ticket. Do not tune teams to force historical
playoff participants, records, or champions.

## Scope and order

1. Finish 1.10.2, including exact-commit upstream qualification, release
   publication, and artifact verification. Freeze that released baseline.
2. Reconcile AI-026 against the released implementation and reproduce its
   controlled synthetic/public chart-response failures and passing controls.
3. Review the experimental design and a bounded first mechanism before rollout
   or an expensive season campaign. The agent's current proposal is ordinary
   Hard offense responding to opponent defense; defense remains unchanged.
4. Add meaningful failing tests, implement the reviewed mechanism, then verify
   focused correctness and actual gameplay before paired season comparisons.
5. Review the measured result. Retain only a supported improvement, or revise
   the mechanism and repeat transparently. Treat the defensive portion of
   AI-026 as separate work; a successful offensive phase does not close it.
6. Select the next issue only after reviewing this phase. AI-019, DATA-042,
   AI-024, and late-game coaching tickets are candidates, not approved additions
   to this release's implementation scope.

## Experimental discipline

Use [AI-030](issues/AI/AI-030.md) to control policy-comparison confounders and
[DATA-042](issues/DATA/DATA-042.md) to monitor existing scoring/pace discrepancies.
Neither reference authorizes unrelated fixes in this phase.

- Bind baseline and candidate chart hashes, gameplay code, rules, source
  identities, accounting definitions, calendars, postseason specification,
  return preferences, and deterministic seed lists. Change only the declared
  coaching mechanism. Record unavoidable differences explicitly.
- Compare actual-calendar 1983 and 2024 seasons with corresponding seeds and
  settings. Separate development seeds from held-out evaluation seeds; choose
  exposure, stopping rules, thresholds, and statistical methods before observing
  candidate results. Repeated reruns of the same seed add no independent evidence.
- Review the proposed formation prior and treatment of unresolved outcome mass;
  a uniform six-formation prior is a proposal, not an accepted historical model.
  Preserve legal information boundaries: no pending opponent call or future dice.
- Benchmark cost first. The agent's proposed 8 development plus 16 held-out
  paired seeds per year imply 24,864 games; this exposure is not yet approved.
  Retain compact summaries and compressed evidence rather than redundant
  dependency trees or giant intermediate reports.

## Exit criteria

Before evaluation, declare concrete improvement and non-regression thresholds.
Assess the candidate against these criteria rather than selecting favorable
metrics after observing results.

1. Synthetic/public controls show the intended chart response on both home and
   away paths, with passing controls for unchanged behavior and no hidden
   information use. Use the repository's test-first workflow.
2. Every evaluated game completes legally; scoring, possession, statistics and
   selected-action counts reconcile. Failed games remain failures and cannot
   silently disappear from season summaries.
3. Paired held-out results demonstrate credible improvement in the predeclared
   source-efficiency measures, with uncertainty and team/year breakdowns. The
   proposed primary measure is macro source-efficiency error normalized by
   existing fixed tolerances; its precise definition requires review first.
4. Scoring, pace, turnovers, sacks, call diversity, and material team-level
   regressions meet the predeclared guardrails. Never widen existing accuracy
   bounds or suppress adverse findings to obtain a pass.
5. Report win distributions, playoff and Super Bowl frequencies, and historical
   qualifier overlap for each cohort. Explain whether historical resemblance
   improves, worsens, or remains inconclusive. A familiar playoff bracket alone
   is not proof of a better model; historical outcomes remain diagnostics.
6. Unit passes alone do not establish completion. Require gameplay evidence,
   paired-season analysis, review, appropriate documentation, and the applicable
   repository regression/release checks before publication.

If evidence is neutral, adverse, or too uncertain, report that outcome and keep
the work open. Do not claim incremental progress without measured support.

## Handoff and reporting

The existing release subagent owns preparation and implementation after 1.10.2.
Send the baseline/design and proposed mechanism for review before broad rollout.
After each coherent phase, report the problem, production change, failing-test
baseline, verification, paired outcomes, affected teams, limitations, and whether
exit criteria were met. Update issue evidence/status only as justified.

Keep private historical inputs and detailed logs in ignored local audit storage.
This plan and public-safe conclusions belong in the repository; supported
behavior belongs in the canonical player/developer guides when implemented.

The newly requested season-statistics feature (STAT-006) and mixed-season UI
selection (FLOW-020) remain separate backlog items, not implicit requirements
for this simulation-improvement phase.

## First design review

The first offense-only mechanism is approved for work after verified 1.10.2
delivery. A uniform prior across six formations is an explicit neutral modeling
assumption for this experiment, not a claim about historical defensive usage.
Do not consult the opponent's selected formation. Keep unresolved mass explicit,
with neutral utility and no renormalization; verify that missing coverage cannot
masquerade as evidence of safety. Keep all defensive policy unchanged.

Before candidate evaluation, freeze a machine-readable protocol containing the
five metric definitions, denominators, tolerances, aggregation, seeds, statistical
method, and numerical guardrails. The held-out paired 95% interval for candidate
minus baseline normalized source-efficiency error must lie below zero. Report
each cohort separately; pooled improvement cannot conceal a materially worse
cohort. Derive scoring/pace non-regression limits from source gaps and baseline
variation before seeing candidate outcomes. Also verify intended improvement
against actual resolver matchup utility: closer source averages alone do not
prove better coaching.

Benchmark one paired development season per year before committing to the full
proposed exposure. At sixteen held-out seasons per year, qualification frequencies
move in increments of 1/16 and remain coarse diagnostics, not precise estimates
of an individual team's playoff chances. Record uncertainty and reserve stronger
team-specific claims for sufficient independent exposure.

### Protocol review and unresolved outcomes

The initial protocol specifies eight paired development and sixteen paired
held-out seasons per cohort, conditional on the pilot's cost limits and verified
1.10.2 delivery. Baseline-only development variation locks numerical scoring
and pace budgets before any candidate outcomes are observed. Retain all failure
seeds and do not expand or replace held-out samples after seeing efficacy.

Review identified that neutral unknown utility zero can outrank known adverse
utility. The reviewed candidate therefore preserves the neutral full-mass
estimate for disclosure but ranks unresolved mass conservatively at the existing
ordinary utility floor of -1.5. This is a declared modeling assumption, not an
assertion that unknown results are interceptions or that the neutral estimate
proves safety. Show coverage and a utility interval under the declared range
[-1.5, 1.8]. Known incompletions and BLACK outcomes must not be relabeled as
unsupported. Add controls proving that replacing known interception/fumble mass
with unsupported outcomes cannot improve selection weight. Record this explicit
change to the earlier neutral-ranking proposal in the frozen protocol before
production implementation or candidate evaluation.

## First offense experiment: rejected in development

Release 1.10.2 is published and its five assets are verified. The first AI-026
candidate remains isolated and unshipped: baseline `10d7130`, candidate `f64b3c2`,
reviewed protocol v3 SHA256
`b371b9827ffc643aaf2c7d85cc6d6b7dc163f5368e7b5a804e36b159eedbafff`.
The candidate combines physical offense/defense dice mass through actual priority
semantics under the declared uniform six-formation prior. Existing defensive,
special-situation, clock, utility-coefficient and repetition policies are fixed.

The unchanged baseline produced 28 expected offense failures and 12 controls.
The implementation passed 48 phase checks, 691 focused AI/resolver regressions,
and 148 adapter/auto/documentation checks (one existing backend deprecation
warning). Two existing fixture assumptions required correction: equal synthetic
offense now uses neutral synthetic defense, and selector-weight comparisons
include the actual public opponent defense. Existing assertions were retained;
a new real-resolver control proves public defense breaks offense-only equality.

All eight development seasons per cohort/policy completed: 32 seasons, 8,288 games,
zero game/accounting errors, both physical interception-return settings fixed true,
and all postseason games included. Baseline-only variation locked .25 points and
.50 plays per team-game nonregression budgets before any candidate outcomes.
These development comparisons use paired season bootstrap intervals, not independent
team/game samples. They are diagnostics rather than held-out acceptance.

| Team-macro normalized source error | Baseline | Candidate | Paired change, 95% interval |
| --- | ---: | ---: | --- |
| 1983 | .8457 | 1.0567 | +.2110 [.1677, .2594] |
| 2024 | 1.1222 | .7660 | -.3562 [-.3954, -.3146] |
| Equal-cohort mean change | | | -.0726 [-.1081, -.0352] |

The pooled decrease does not qualify. In 1983, completion-error change is +.6848
normalized units and sack-error change is +.4355; both exceed the fixed individual
metric guardrail. Plays per team-game fall 65.232 to 61.720 against source 65.788:
the absolute source-gap worsening is +3.512 [3.336, 3.667], exceeding .50.
In 2024, sack-error change is +.2074 with upper interval .2845, also exceeding
the .25 metric guardrail. Scoring source gaps improve in both cohorts.

Reject candidate v1 for promotion. No held-out season has been run or opened;
no coefficient, tolerance, chart, seed or team-specific adjustment is made to
rescue these results. AI-026 remains open, including its defensive remainder.
A revised general mechanism requires a new reviewed protocol before another
production experiment or season campaign.

Mode-stratified selected-call evidence localizes the large change to the emitted
ordinary (`normal`) coaching label: run share moves 31.72% to 43.34% in 1983
and 26.31% to 39.56% in 2024, with increases in Screen and Draw. Comparable
special-mode run shares remain close. This is a mechanism hypothesis; changed
calls also change later state and clock exposure. Full-mass modeled coverage
remains explicit rather than renormalized. The compact callbacks retain emitted
mode and distance band, but do not retain exact distance or a full branch trace.

Ignored compact evidence is retained under
`.ai-audits/release-readiness/v1.10.3/ai026-preparation/`:
`baseline-variance-budget-lock.json`, `frozen-candidate-context.json`,
`development-analysis-08.json.gz`, `development-mode-coverage-08.json.gz`, and
all 32 immutable compressed season receipts. Original historical diagnostic
`source_accepted=false` and `release_certified=false` flags remain in receipts;
they do not replace or contradict the separately verified published-release gate.

## Reviewed second experiment: ordinary third downs only

The next reviewed candidate retains the released own-offense/history mixture
on first and second downs and applies the unchanged full matchup model only
on ordinary third downs. Goal-line, red-zone, fourth-down, hurry-up, conversion,
clock and defensive policies remain fixed. Third down's full line-to-gain
objective directly values continuation; the early-down half/70%-distance
surrogates omit remaining downs and clock. This is a narrower capability
experiment, without a fitted blend, distance cutoff or team/era adjustment.

Static calendar-weighted, empty-history estimates support the diagnosis, without
establishing a causal season decomposition. At first-and-10, 1983 pass weight
moves 69.81% (legacy own chart), 66.71% (core semantics with neutral defense),
then 56.16% (actual opponent chart under the uniform formation prior). The
2024 values are 75.08%, 74.15%, and 60.07%. Most of the modeled shift comes
from the opponent-priority adjustment, rather than secondary-column
interpretation alone.

Candidate v2 is isolated at `2ac517d`, protocol v4 SHA256
`9fa767be8fc70ed47b0e72ccece9d613a5596820b72196479ebbd9fbb1d3627b`.
Four first/second-down home/away regressions fail against v1 while 48 existing
phase controls pass; after the scope correction, 695 focused regressions and
148 adapter/auto/documentation checks pass. Existing third-down true-resolver
utility, full-mass/unknown, fallback, physical-side and special controls remain.

Both cohorts retain every original source-efficiency/scoring/pace gate and
seed. An explicit compatibility receipt reuses immutable released-baseline v3
receipts and the pre-candidate variance budgets; their stored identities are
not rewritten to v4. Candidate v2 has separate snapshot, runtime and outcome
paths. Early-down and defensive capability remain unfinished under AI-026.
No promotion or improvement is claimed before outcome validation.

### Second experiment outcome: improved accuracy, pace gate failed

All eight v2 development seasons per cohort complete without game/accounting
errors. Team-macro normalized source error improves: 1983 -.03368
[-.06123, -.00387], 2024 -.05759 [-.10278, -.01181], equal-cohort mean
-.04563 [-.06870, -.02462]. Every individual metric guardrail passes.

The complete gate still fails. 1983 plays per team-game fall 65.2316 to
64.5876 against source 65.7879. Absolute source-gap worsening is +.64397
[.46903, .82840], exceeding the fixed .50 budget. Scoring gaps improve in
both cohorts; 2024 pace improves. Reject v2 without sample expansion,
changed limits or opening any held-out seed.

Normal third-down run share rises 30.90% to 41.32% in 1983 and 24.17% to
37.65% in 2024; incompletions fall 25.90% to 18.80% and 27.58% to 18.95%.
Core incompletions consume five seconds versus a normal in-bounds uniform
25–45 seconds. This supports a clock mechanism, without exact causal
attribution or conversion/drive conclusions from distance bands.

Eligible third-down modeled coverage is 98.6274% in 1983 and 99.0132% in
2024. Remaining mass is defensive-penalty effect, retained unresolved.
The unchanged model's coverage catalog has explicit source-byte compatibility.
Ignored `development-v2-analysis-08.json.gz`, `development-v2-coverage-08.json.gz`
and `candidate-v2-rejection.json` retain identities and raw receipt hashes.
Statistical/pace eligibility is explicitly separate from final promotion,
which also requires resolver utility, coverage, new-team-bound review and
complete release qualification.

# Release 1.10.3: controlled simulation improvement

Status: approved direction, implementation and experimental details pending.
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

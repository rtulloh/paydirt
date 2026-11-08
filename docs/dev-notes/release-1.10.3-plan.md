# Release 1.10.3: controlled simulation improvement

Status: approved direction; two rejected candidates, third continuation experiment under evaluation.
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

## Reviewed third experiment: continuation objective

The reviewed v3 hypothesis changes ordinary third-down numeric utility to one
for reaching the line to gain and zero otherwise. The prior fractional-gain
utility can prefer a certain 14 yards on third-and-15 (.3733) to a 20% conversion
and 80% incompletion alternative (.28). This is an explicit continuation
objective, not expected points or optimal coaching: it omits punt field position
and the value of a later fourth-down choice. It adds no clock/incompletion bonus.
TD 1.8, INT -1.5, fumble -1, offensive penalty -.3, unknown range [-1.5, 1.8],
uniform formation prior, physical mass, selection temperature/history, and all
early-down/special/defensive policies remain fixed. Every outcome gate is fixed.

Source `32e9218` and protocol v6 SHA256
`02b09b332e2931ca1ae08af8ceadb292e6a38b5b04457a95a67f44cc81a48ab7`
are frozen before candidate historical outcomes. Hashed v5 remains preserved;
v6 only clarifies that original baseline-v3 receipts and new candidate-v6
receipts retain separate identities. Metrics, samples, seeds and budgets match.

Test first: 20 expected failures and 202 controls precede the objective change.
The independent numerical oracle now uses binary continuation; physical-mass,
priority, fallback, unknown-risk, special and early-down assertions remain.
The third-and-6 variety fixture previously gave certain 8 versus certain 6;
these now have equal continuation value. It now gives alternatives real
nonconversion mass while retaining the exact original frequency, all-nine-call
and repetition assertions. Dice-weighting winning gains now reach the requested
distance. The v1/v2 numerical oracles remain in immutable source snapshots.
After implementation, 698 focused regressions, 148 adapter/auto/docs checks and
55 final phase checks pass; one existing backend deprecation warning remains.

An external proof invokes the actual released and candidate selectors in separate
frozen processes, with the same synthetic fixture and independent real-resolver
physical mass. The analytic 1/5 example is supplemented by reachable 43/216
(19.91%) chart mass. Weighted continuation utility rises .0183103 to .0324224
on both physical sides. This establishes the intended synthetic capability,
without qualifying historical source/scoring/pace outcomes. Proof is retained
as `v3-released-weight-utility-proof.json` in the ignored preparation directory.
The early-down and defensive AI-026 remainders remain open.
### Third experiment outcome: continuation improves, pace still fails

All eight v3 development seasons per cohort complete without game/accounting
errors. Team-macro normalized source error improves in both cohorts: 1983
-.06745 [-.10051, -.02832], 2024 -.06728 [-.09451, -.03920], equal-cohort
mean -.06737 [-.08697, -.04629]. All individual metric and scoring guards pass.
The synthetic real-resolver continuation proof also passes.

The unchanged 1983 pace guard still fails. Plays per team-game fall 65.2316 to
64.5756 against source 65.7879: absolute source-gap worsening is +.65597
[.57115, .77094], above .50. The 2024 pace source gap improves .83387.
Reject v3; held-out seeds remain unopened. The binary continuation change does
not establish acceptable whole-season behavior, and its near-identical 1983
pace effect to v2 warrants further mechanism diagnosis rather than a fitted
clock bonus, blend, distance cutoff, changed budget or expanded sample.

Eligible ordinary-third-down supported mass is 98.6355% in 1983 and 98.9783%
in 2024; remaining defensive-penalty mass stays unresolved and receives the
declared conservative ranking floor. Separate coverage artifacts identify the
released baseline's counterfactual model coverage and candidate's actual model
coverage. Source/chart/runtime/protocol hashes and all paired receipts remain
in ignored `development-v3-analysis-08.json.gz`,
`development-v3-coverage-08.json.gz` and `candidate-v3-rejection.json`.
The next diagnostic compares the neutral uniform formation assumption with
released Hard defense's observable-situation policy mixture; it must not read
the selected defense or future dice. No fourth candidate is yet authorized or
implemented. AI-026 remains open, including early-down and defensive response.

## Reviewed fourth experiment: learn from revealed formations

The fourth bounded candidate replaces the fixed uniform formation prior with
p(f) = (N_f + 1) / (N + 6), using only earlier revealed primary-snap formations
in the current game. Counters belong to each physical offensive side, start
cold for a new game, and are published once at the engine's first public outcome,
including a pending or voided foul. Penalty adjudication cannot count a snap
twice. Preview, failed validation/application, conversions and special plays do
not add observations. Normal CLI and opaque web save/replay transport preserve
counts; legacy saves with no field start balanced. No UI computes coaching.
All third-down continuation/risk/unknown values and early/special/defensive
policies remain fixed, as do every source/scoring/pace gate, budget and seed.

Past-only, untuned prequential formation forecasts improve Brier score from
uniform .83333 to .61755/.54711 for released 1983/2024 development games.
This supports a general observable forecast, without proving better coaching.
Contrary static evidence is retained: at third-and-10, weighting observed
baseline formations rather than uniform lowers empty-history pass weight
.61744 to .58740 in 1983 and .64294 to .61540 in 2024. Learning is not presented
as a pace rescue; only the unchanged paired outcome gates can qualify it.

Test-first observation/selection controls fail before production: 42 expected
core/CLI/auto failures and six passing controls, four web failures and two
frontend save-transport failures. The earlier 33-failure/12-control receipt is
preserved as the initial test revision. Direct-play penalty labels in that first
matrix are ordinary direct-resolution controls; procedure cases exercise actual
pending, offsetting, accepted and declined foul paths. Actual conversion clones,
physical-side credit, save/legacy continuity, nonuniform full mass, unknown
substitution and prior-cache changes are covered. No v4 existing expectation is
weakened. The broader run exposed a public AI audit observer that still recorded
old own-offense weights; an actual RNG-distribution regression fails before
selector/observer share the same pure weight query. Existing probability and
accounting assertions stay intact. The original historical experiment adapter
and released-baseline identities are unchanged.

Candidate source `853f915` and protocol v7 SHA256
`2796a1e721eb5edaa019014076e96766025ab195ce91cfcd74238a4839f77b24`
are frozen before historical candidate outcomes. 1,837 focused AI/resolver/
priority/history/conversion/save/auto/docs checks, 431 backend checks, all 352
frontend tests and the frontend build pass. Existing backend deprecation and
Browserslist warnings remain; this is not a full release regression claim.

An external proof executes actual released, rejected-v3 and frozen-v4 selectors
in separate processes after real synthetic chart snaps reveal past formations.
Independent true-resolver continuation utility rises .55556 to .86873 in a
matching pass-favoring regime and .44444 to .80900 in a matching run-favoring
regime, on both physical sides. Misleading history lowers utility by .31318 and
.36456 respectively. Changing only the future oracle formation leaves selection
weights unchanged; a cold game retains v3 parity. This establishes the intended
learning response and its limitation, not whole-season acceptance. Ignored
`v4-released-weight-utility-proof.json`, `frozen-candidate-v4-context.json`,
`v7-baseline-compatibility.json` and prior diagnostics retain reproducible hashes.
Pilot cost/correctness must pass before the remaining development runs; held-out
stays closed until every development gate passes. AI-026's early-down and
full defensive-strength remainders remain open.

### Fourth experiment process exception: pilot cost receipt

The pilot completed both cohorts without game/accounting errors. Its immutable
cost receipt was written after the remaining development workers launched,
contrary to the required ordering: the first receipt writer used the wrong
selected-call key, and orchestration continued after that command failed.
The corrected receipt explicitly records this chronology; independent review
recomputes 2,852.67 projected sequential seconds and 67,730,328 retained bytes,
within the unchanged eight-hour/1.5-GiB limits. This uses pilot cost measurements
only, without outcome-based selection. Preserve the running evidence rather
than rerun to conceal the omission. All dependent commands now require an
explicit successful exit before launching the next step. This process exception
remains part of qualification review; it is not described as a prelaunch gate.
Ignored `paired-v4-pilot-cost-gate.json` and
`root-v4-postlaunch-cost-review.json` preserve the calculation and chronology.

### Fourth experiment outcome: learning capability, pace still fails

All eight v4 development seasons per cohort complete without game/accounting
errors. Both cohorts' five-metric source error improves: 1983 -.08768
[-.10029, -.07099], 2024 -.05614 [-.08524, -.02879], equal-cohort mean
-.07191 [-.09014, -.05186]. All individual metric and scoring guards pass.
The actual-selector learning proof and public real-game observation
reconstruction also pass, including five voided primary snaps.

The unchanged 1983 pace guard fails: plays per team-game fall 65.2316 to
64.7026 against source 65.7879, worsening the absolute source gap +.52902
[.36523, .69448], above .50. The 2024 pace gap improves .84076. Reject v4;
closeness to the budget is not a reason to relax it or open held-out seeds.
No candidate is promoted, and no fifth production experiment is authorized by
these results. All rejected snapshots and reports remain immutable.

Dynamic coverage integrates each formation's physical mass using the actual
predecision Laplace prior reconstructed from earlier primary callbacks, with
the current formation added afterward. All selected calls, including specials,
reconcile separately from observed primary snaps. Defensive-penalty effects
remain unresolved; no mass is renormalized away. Utilities in this coverage
report use a declared reference third-and-15 because compact receipts retain
distance band rather than exact target. Ignored
`development-v4-analysis-08.json.gz`, `development-v4-coverage-08.json.gz`,
`v4-revealed-reconstruction-proof.json` and `candidate-v4-rejection.json`
retain identities, receipt hashes and the cost-receipt process exception.
AI-026 remains open, including early-down and defensive chart response.

## Defensive diagnostics after rejected offense experiments

Diagnostics restart from released `10d7130`, preserving its offense. A public
synthetic case confirms C is still selected when C changes from preventing
every conversion to allowing every conversion, while five alternatives prevent
them under all nine incoming calls. This establishes a chart-response blind
spot without knowing the pending offensive call.

Conservative per-call interval dominance yields no eligible replacement across
all 788 calendar chart pairings, six formations and fixed third-down distances
1, 3, 6, 7, 10 and 15. Even neutral point dominance is absent through distance
10 and rare at 15. Real call tradeoffs, beyond unresolved-interval overlap,
prevent a meaningful incremental correction. No near-no-op is implemented.

Past-only nine-call forecasts retain negative results. Uniform Brier score on
released ordinary third downs is .888889. Untuned game-global Laplace one per
call scores .896677 in 1983 (worse), .883780 in 2024 (better). The reviewed
same-down diagnostic tests early-down confounding with the same estimator:
.904959 and .895340, both worse. These are forecast diagnostics, not candidate
historical outcomes. No observation schema or production forecast is added;
no further window/pseudocount search is justified. Compact bands cannot
reconstruct the existing exact tendency key at the 6/7 boundary.

Ignored `defensive-dominance-diagnostic.json.gz`,
`defense-call-forecast-diagnostic.json` and
`defense-same-down-call-forecast-diagnostic.json` retain identities, per-team
results and contrary evidence. Root reviewed a static minimax-regret diagnostic
next, without call probabilities or current-call access. This is an upper bound
under declared coaching utility intervals, not exact football regret, expected
points or guaranteed improvement. Production remains unapproved. Better
modeled stops can worsen existing efficiency deficits; all original historical
gates and AI-026's remaining capabilities remain required.

The regret diagnostic is not ready for production. Its endogenous reference
`min_g L(g, p)` can worsen competitors' regret when one formation gains unknown
mass, thereby improving that opaque formation's selection. An exact synthetic
counterexample replaces 10% known fumble mass with unknown: the original
formation's worst regret stays 1.12 while its competitor rises 1.10 to 1.15.
Retain this negative control; do not disguise it with fitted blending or relax
unknown-substitution requirements.

Root reviewed a distinct static worst-case objective next: `W(f) = max_p H(f,p)`,
minimized across formations, preserving the released recommendation on exact
ties and then using fixed enum order. No endogenous competitor benchmark or
call probabilities enter. Replacing adverse mass with unknown raises only its
own upper bound, so its maximum cannot decrease while competitors and fixed
tie rules remain unchanged. Six thousand exact synthetic substitutions across
six baseline tie contexts confirm this monotonicity. These are objective
controls, not an actual selector or historical acceptance. Ignored
`defense-objective-unknown-controls.json` preserves both the rejected-regret
counterexample and worst-case proof. A full static effect diagnostic precedes
any production proposal.

The worst-case static audit is nontrivial: conditional on released C at
third-and-10, it changes 75.22%/100% of calendar-weighted chart pairings
(1983/2024), reducing the declared bound .04102/.12139 on average. Conditional
on D, changes are 31.70%/84.74%, reduction .00841/.08260. Per-team reports
cover all 28/32 defenders. This is not actual branch exposure or a season
outcome, and large modern changes strengthen the need for outcome validation.

An independent actual released-resolver synthetic diagnostic covers both
physical sides and all nine primary calls. Six own-defense/opponent-strength
contrasts reduce true worst conversion utility 1 to 0; two retained-choice
controls stay 0. State and engine RNG remain unchanged. The external diagnostic
selector is not production implementation. Ignored
`defensive-minimax-upper-diagnostic.json.gz`,
`defensive-minimax-upper-team-summary.json.gz` and
`defense-upper-resolver-proof.json` preserve the exact mass and identities.

A concrete defense-only production proposal is awaiting review: start from
released source; scope ordinary third downs outside red zone, conversion and
existing late/special branches; preserve released offense and model/RNG update
order. Use pure content-cached chart analysis and exact ties, with no learned
observations, save schema or UI change. Require a fresh test-first baseline,
source/protocol freeze and unchanged paired historical gates before promotion.
No production work is authorized by the diagnostic alone.

### Defensive candidate implementation review (2026-11-08 UTC)

Root subsequently approved the bounded defense-only proposal for an isolated
experiment, not promotion. Frozen protocol v8 has SHA-256
`cd31b2d7874cf49ad37193cac3c483fcfd3f6580201a5c59f612d2ff7298f6d5`;
historical metrics, seeds, scoring/pace budgets and held-out restrictions stay
unchanged. Released offense remains intact. No v5 historical outcomes have
been evaluated at this checkpoint.

Initial test receipts require qualification: the reported 28 failures and 38
controls included pending-penalty fixture errors, so the count does not prove
28 intended behavior failures. The first implementation produced 62 passes
and four failures: two pending-log assumptions and two unreachable breakaway
fallback controls. Preserve those receipts and correct the fixtures against
the actual resolver before claiming a clean failing baseline. Missing-row
controls use physical chart roll keys, and the QT fallback control uses a
reachable five-yard target.

The pending fixture exposed a real exclusion gap: the core returns an
unresolved primary outcome before appending to the play log. A narrow,
engine-owned transient handle is authorized by the ignored immutable
`pending-primary-scope-addendum-v8.json`. It must identify the actual pending
outcome, clear only after successful adjudication of that outcome, and survive
no-op, unrelated or failed adjudication. Existing untimed-down and special
procedures remain unchanged. Backend reload already cannot reconstruct pending
outcomes; this experiment adds no save schema or pending-save continuity claim.
Independent tests against the unchanged engine yield seven expected missing-
handle failures and one passing control, without setup exceptions.

Independent review also confirms 221 existing resolver/priority tests pass and
1,521 constant synthetic primary-cell cases match actual resolver utility
across all nine calls, with complete deterministic secondary columns. These
checks do not establish missing-secondary fallback correctness, full selector
qualification or historical improvement. Ignored `root-v5-*-review.json`,
`root-v5-core-resolver-check.json` and
`root-v5-synthetic-core-crosscheck.json` retain the detailed evidence. Corrected
test-first checks, actual-selector proof, source freeze and cost gate remain
required before the paired development campaign; held-out seeds remain closed.

The corrected released-source baseline subsequently produces 35 intended
failures and 39 passing controls, with no fixture exceptions. Independent
review confirms the B/QT fallback oracle assertions pass before the expected
released-selector mismatch. After the narrow pending-handle implementation,
all 74 focused selector/lifecycle tests pass; another 83 existing save and
penalty regressions pass. Runtime attestation includes `matchup_analysis.py`.
These results clear the identified fixture/lifecycle problems only. Broader
model and adapter checks, frozen source identity, actual-selector proof and
paired historical acceptance remain outstanding. Ignored
`root-v5-corrected-red-review.json`, `root-v5-pending-green-review.json`,
`root-v5-save-penalty-regressions.json` and
`root-v5-current-runtime-review.json` retain exact commands, hashes and limits.

## Fifth experiment frozen before historical outcomes

Root approved the distinct defense-only worst-upper-utility experiment from
released `10d7130`. Source `d531935` and protocol v8 SHA256
`cd31b2d7874cf49ad37193cac3c483fcfd3f6580201a5c59f612d2ff7298f6d5`
are frozen before candidate seasons. The strict v3/v8 bridge reuses original
released baseline receipts, seed arrays and variance budgets without rebinding
identities. No rejected offensive policy is stacked. Source/AST comparison
confirms released offense is unchanged apart from constructing a pure defensive
analysis field; all other existing offensive methods and strategy bytes match.

Test-first disclosure: the early reported 28 failures included two pending-log
IndexErrors and two unreachable B-fallback assumptions; they were not all
expected behavior failures. The 111-row fixture was also replaced by an actual
physical roll, with explicit removal assertions. QT fallback is -5 through 10,
so the missing-table target was corrected from 15 to 5. Final controls use primary
B/QT with reachable priority, enumerate actual resolver fallback supports and
retain exact expected utility. No assertion is weakened or skipped. Corrected
released-source import origins prove 35 expected failures and 39 controls.
The corrected rerun uses the unchanged release after the first isolated AI
implementation; the seven new absent-handle lifecycle failures precede engine
instrumentation. All
earlier receipts remain retained with this correction.

The accepted pending exclusion required a narrow transient engine handle,
because unresolved primary outcomes return before logging. Immutable
`pending-primary-scope-addendum-v8.json` was reviewed before engine edits.
The actual pending outcome installs the handle; only successful matching
accept-play/accept-penalty resolution clears it. No-op, failure and unrelated
resolution retain it. Existing penalty-index fallback remains. No result,
clock, RNG, log event, save schema or UI transport is changed. Existing reload
cannot reconstruct pending outcomes; this is documented without claiming new
pending-save continuity. Legitimate untimed downs remain distinct.

1,805 relevant core regressions pass, followed by 84 focused mass/cache/lifecycle/
real CLI/auto controls and 431 backend checks; 21 existing backend warnings
remain. The new web cases exercise actual preview and execution for fresh and
replayed games on both physical sides. The complete synthetic auto game
exercises both defenders. Exact secondary-cache mutation and bounded-target
controls pass. Final focused/docs count is 85. Ruff passes; this is not a full
release regression claim. No existing test expectation changes were required.

The actual frozen released and candidate selectors run separately against
identical public synthetic inputs and an independent real-resolver oracle.
Six contrasts reduce true worst numeric conversion utility 1 to 0; two
retained-choice controls stay 0, covering both physical sides and all nine calls.
This establishes the stated robust capability rather than historical acceptance.
Ignored `v5-released-selector-utility-proof.json`,
`frozen-candidate-v5-context.json`, `v8-baseline-compatibility.json` and
`v5-offense-source-identity.json` bind source, charts, runtime, protocol and
inputs. Pilot correctness and an explicit successful cost receipt must precede
remaining development launches. Every original historical gate remains fixed,
held-out remains closed, and AI-026's wider capabilities remain open.


## Fifth experiment resumed with gated pilot reuse

The explicit user pause stopped new work after the two pilot reports had
completed. No remainder or analysis ran during the pause. On resume, those
unchanged outputs are reused: 233 games for 1983 and 285 for 2024, with zero
reported errors. Independent root review and the resumed verifier reconcile
all 1,036 paired baseline/candidate game receipts, including postseason,
physical return settings, scoring and call totals, raw aggregates, frozen
identities and declared seeds. Original baseline receipts use their original
index/seed schema; candidate receipts additionally carry phase/index fields.
A verifier setup assumption about those original phase fields was corrected
before any remaining season launched.

Immutable `protocol-v8-defensive-scope-clarification.json` records the conflict
between inherited offensive utility wording and v8's already-approved distinct
defensive scope. Frozen protocol bytes and every numerical acceptance gate
remain unchanged. The fifth candidate must demonstrate the approved robust
defensive resolver capability separately from source-fit acceptance; full
AI-026 completion is not implied. Coverage includes full static call/formation
support, unresolved categories, known-zero mass and utility bounds, plus a
clearly labeled selected-call/formation counterfactual census. Compact offense
mode/band records cannot establish exact defensive eligibility exposure.

`paired-v5-pilot-cost-gate.json` passes before the remaining 14 development
seasons launch. Its conservative sequential projection is 3,034.41 seconds
and 68,052,240 compressed bytes, with 23.92 GB free at verification, within
the unchanged limits. The receipt binds both existing candidate pilot hashes,
frozen context and scope clarification. Launcher preflight rejects a missing
or unsuccessful receipt and altered pilot bytes. Development remainder uses
four workers; held-out remains closed pending all development gates.

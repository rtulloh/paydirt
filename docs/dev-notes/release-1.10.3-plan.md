# Release 1.10.3: controlled simulation improvement

Status: seven candidates rejected in development; eighth frozen candidate passed the paired pilot and is running the remaining development seasons. Held-out evaluation and promotion remain gated.
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


## Fifth experiment outcome: robust capability, historical gates fail

The frozen defense-only candidate `d531935` is rejected before held-out.
All 16 candidate development seasons and their 16 retained baseline pairs
complete: 8,288 games total, with no reported game errors. The predeclared
analysis and independent root recomputation agree:

| Measure | Paired change | 95% paired interval | Frozen requirement |
| --- | ---: | --- | --- |
| 1983 normalized source error | -.042174 | [-.066710, -.016930] | Mean <= 0; upper <= .05: passes |
| 2024 normalized source error | +.012622 | [-.023434, +.049646] | Mean <= 0: fails |
| Equal-cohort source error | -.014776 | [-.036091, +.009825] | Upper < 0: fails |
| 1983 points absolute source gap | +.020647 | [-.362737, +.495815] | Upper <= locked .25: fails |

The positive 2024 mean does not establish a statistically certain worsening;
it fails the already-frozen nonpositive-mean rule. The 1983 scoring mean is
nearly unchanged, but its uncertainty exceeds the fixed allowance. Neither
justifies opening held-out or increasing the development sample. All ten
individual metric guards and both pace guards pass. 2024 scoring improves
25.31664 to 24.33824 points per team-game, toward source 22.91176; this does
not override the failed guards.

Signed errors retain the efficiency tradeoff. 2024 team-macro completion
bias is -.07662 to -.07967 and passing-YPA bias -.20106 to -.40176; their
absolute errors worsen .076785 to .079698 and .405328 to .489062. Sack-rate
absolute error improves .017626 to .014251. Descriptive REG third-down
records whose emitted offense mode is normal shift heavily toward formations
A/E and away from C/D. These records cannot establish actual defensive
eligibility or causal effects; no claim ties the improvement to blitz F.
A plausible limitation is the minimax objective's worst-call hedge versus
actual unadapted offensive call tradeoffs. This remains a hypothesis requiring
a diagnostic, rather than a reason to add a fitted blend or weaken bounds.

The direct frozen compiler census covers all 788 ordered calendar matchups,
all nine legal calls and six formations: 42,552 exact coverage cells, with
U0/L/H at six declared static targets. The selected-call/formation
counterfactual census reconciles all 1,217,422 REG callbacks: 1,082,899 primary
and 134,523 special calls. Weighted unresolved mass changes .01373923 to
.01384712 for 1983 and .00895019 to .00896005 for 2024; all is classified as
unmodeled defensive-penalty utility. Known-zero and category mass reconcile.
These are all-primary counterfactual coverage values, including excluded
branches; exact actual eligibility exposure remains unverified. The initial
census draft confused receipt enum names with catalog enum values. Root
caught this before execution; the corrected separate census normalizes via
the authoritative resolver enum, rejects unknown names, preserves raw-name
counts and checks every actual lookup. A preliminary import of the distinct
legacy model enum also fails before emitting evidence and is corrected.
The frozen static compiler/catalog remains unchanged.

Every newly crossed team bound remains in the private review: 104 team/metric
pairs in 1983 and 90 in 2024 cross at least one paired seed, including nine
new mean-error crossings per cohort. These counts are not numbers of teams
or proven causal defects. Exact numerators, denominators, fixed targets and
tolerances, eight paired errors and uncertainty are retained for all entries;
none is dismissed as an outlier or used for team-specific tuning.

Ignored `candidate-v5-rejection.json` binds the frozen protocol/context,
compatibility and scope clarification, prelaunch cost receipt, actual-selector
resolver proof, aggregate analysis, full static coverage, corrected census
and new-team-bound review. This is a fifth honest rejection despite demonstrated
synthetic robust chart-response capability. No held-out seeds, promotion,
source/tolerance changes or sample expansion follow. Released offense and
main production source remain unchanged; AI-026's wider offensive/defensive
capabilities remain open. Review a general mechanism before any sixth
candidate or protocol change.


## Fifth defensive objective: static binding-call tradeoffs

The approved post-rejection diagnostic retains exact all-nine-call signed
utility/bound changes for every ordered calendar matchup, six declared static
targets and all six hypothetical released tie baselines. At target 10 with
released C, 2024 worst-upper utility improves .121386, but neutral offensive
utility increases .24356 for Screen, .17293 for Short Pass and .15950 for
Draw, while decreasing .24699 for Long Pass and .10774 for Medium Pass.
The original C bound is driven by Medium/Long Pass in 58.82%/41.18% of
calendar-weighted pairs. For hypothetical released D, Long Pass binds 94.12%;
reducing its hedge increases Screen .13280 and Short Pass .19745.
These are explicit static conditional tradeoffs, not observed offensive
probabilities, actual eligibility, expected points or causal season effects.
Exact ties retain the hypothetical released recommendation, then enum order.
Ignored `defense-v5-binding-tradeoffs.json.gz` preserves every signed interval,
full-source catalog identity and calendar weights; no production follows.

Review also confirms no retained campaign isolates only own offensive B/QT
secondary information. The earlier neutral-defense ablation simultaneously
changed primary priority semantics, secondary resolution and unknown-floor
ranking. Released ordinary offense explicitly assigns neutral full mass to
B/QT despite available secondary columns. An approved next diagnostic will
isolate that information from released source while retaining every original
ordinary target/progress/risk/weight/history parameter and all defensive,
special-phase and conversion policies. Actual-core synthetic controls precede
the 60-team static comparison. No sixth production candidate or season campaign
is authorized by this diagnostic; wider AI-026 remains open.


## Own-secondary diagnostic: a distinct missing-information case

The released Hard selector is insensitive to changing only its own B/QT
secondary tables in public synthetic charts, on both physical sides.
Independent root actual-factory checks retain the same scores, weights and
seeded selection. An isolated diagnostic resolves only primary B/QT mass;
all other primary interpretation, ordinary down targets, numeric progress,
risks, temperature, competitive gap and repetition handling stay released.
This differs from the earlier combined neutral-defense ablation.

Forty-four final controls pass against the actual released resolver. They
cover favorable/adverse and zero secondary gains, both sides, physical
secondary dice mass, partial/missing/unparseable fallback tables, and QT
secondary fumbles. B-column fumble notation currently yields numeric
Breakaway yards in the core; that asymmetry is preserved. Secondary F INC
is explicitly rejected by both core and diagnostic, not treated as fallback.
Non-B/QT primary scores across all four downs, chart/RNG purity, repetition
factors and conversion scores remain unchanged. Root caught an invalid
mocked defensive-dice tuple in an earlier control revision; that receipt is
retained as unaccepted evidence. Final controls use physical (1, 0, 1).
An earlier metadata enum/name tooling error also precedes accepted evidence.

The static comparison covers all 60 teams and 16 fixed down/distance
contexts, with original frozen chart/runtime identities checked before and
after execution. Calendar-weighted empty-history pass weight shares are:

| Cohort/context | Released | Own secondary only |
| --- | ---: | ---: |
| 1983 first-and-10 | .698138 | .665916 |
| 1983 third-and-10 | .778439 | .752198 |
| 2024 first-and-10 | .750775 | .734858 |
| 2024 third-and-10 | .851435 | .812157 |

All teams change. B/QT accounts for roughly 7.4%/8.8% of primary mass in
passing calls for the two cohorts; run calls contain less. Existing generated
secondary tables require no fallback in this inventory. Other neutral primary
mass remains untouched with full probability mass. These are conditional
own-chart utility estimates, not defense-adjusted probabilities or historical
acceptance. The runward shift is contrary evidence given earlier pace failures;
no favorable season result is implied.

Wiring requires care before any candidate: released hurry-up weights reuse
`OffensiveStrategy.weights`. A global score change would therefore alter an
excluded phase. A concrete sixth proposal must opt in only ordinary Hard
selection, retain default/hurry/conversion behavior, and keep the audit observer
on the exact same ordinary distribution. No production change or sixth
historical campaign follows from this diagnostic. Ignored
`own-secondary-core-controls.json`, `own-secondary-static-diagnostic.json.gz`,
`own-secondary-static-identity-verification.json`,
`own-secondary-static-summary.json` and
`own-secondary-isolation-history-review.json` retain inputs, identities,
controls and all per-call effects. All original outcome gates remain fixed.


## Sixth experiment frozen: ordinary own-secondary information

Root approved isolated own-secondary information and explicitly retained original
neutral primary behavior. Source `9f52f77` starts from released `10d7130`, without
stacking rejected policies. Only ordinary Hard selection opts in. Default calls,
hurry-up, fourth downs, other special phases, conversions and every defense stay
released. A shared pure ordinary-weight helper keeps selector/observer vectors
identical. Targets, progress, risks, temperature, gap, history and RNG namespaces
remain fixed. A separate 100-context cache invalidates on relevant own primary/
secondary contents and returns independent mappings. Only referenced tables are
parsed. Core fallback constants preserve the same RNG calls/distributions.

Released test-first evidence expands from 44 intended failures/28 controls to
49 failures/57 controls; no missing-API or setup failures establish the behavior.
After initial implementation, four additional actual-core tests expose the new
path incorrectly resolving lowercase b/qt. They fail before a narrow raw-category
support gate corrects that introduced edge. Other primary semantics, including
BLACK* and F INC, remain released. Prior test/golden bytes remain preserved.

The complete-auto test initially assumes .5/.5 despite executed call history.
Its corrected independent oracle retains original numeric admission, temperature,
distance bands, history decay/floor and both-side secondary contrasts. A missing
import during correction is retained as a setup failure. No existing regression
expectation changes. Golden vector floats use absolute 1e-12, relative zero, for
platform libm rounding; plays, mode, RNG states and within-platform full high/low
records remain exact.

Final checks pass: 128 phase/CLI/complete-auto/docs, 1,727 existing core AI/resolver/
save/auto tests, and 435 backend tests with 22 existing warnings. Eight backend
cases cover fresh/replayed preview and actual execution, both sides/B/QT. Ruff
passes. The same 128 checks pass in the tracked-only archive. These are focused
checks, not full release regression. Independent review verifies 8,640 candidate
and 8,640 default score cells, history vectors, cache adversarial controls and
320 secondary resolver cases with identical post-call RNG across both sources.

Separate frozen actual-factory processes use identical public synthetic inputs
and actual-core physical-mass oracles. Twenty-four favorable/adverse contrasts
across both sides/first-second-third downs strictly improve weighted ordinary
utility (minimum .0574664); four zero controls keep identical vectors/utility.
Inputs, oracle scores and RNG consumption match; preview leaves engine/history/
global RNG unchanged. This proves conditional own-information capability at
neutral defense, not actual-opponent performance or historical acceptance.

Protocol v9 SHA256
`f2c7bfe119abe89bd64361a22c6a042c5ad6c515671a2c92f77b0eb7cfc26e6b`
and context SHA256
`770691e8df80c7f5b1d1cbfbedd6a94509992eedaf7e9d766d2e1f71f4158871`
bind source, original charts/adapter and published v1.10.2 verification. The
strict v3/v9 bridge preserves every comparative section, seed and numerical
budget. Ignored `v6-released-selector-utility-proof.json`,
`frozen-candidate-v6-context.json`, `v9-baseline-compatibility.json` and independent
`root-v6-*-review.json` retain detailed proof. The tracked-only snapshot adds
about 11 MB without a redundant retained archive or node_modules.

No sixth historical outcome exists at this lock. Final root identity review
precedes the two-seed pilot. A successful pilot cost/correctness receipt must
precede the remaining fourteen development seasons. Launcher regression first reproduces seven failures with two passing controls.
Twelve synthetic subprocess checks now pass: invalid/duplicate/out-of-range
indices, unexpected cohorts and changed protocol identity are rejected before
workers; at most four active submissions drain existing receipts and halt new
work on the first failed worker or exception. No historical worker runs in these
checks. Every original
source/scoring/pace/team-review gate stays fixed; held-out remains closed and
AI-026's wider offensive matchup/defensive capabilities remain open.


## Sixth experiment outcome: source-error gains fail scoring and pace

Candidate `9f52f77` is rejected before held-out. The two pilots passed full
1,036-game paired correctness/identity accounting; their cost receipt preceded
all fourteen remaining development launches. The bounded launcher completed
those fourteen with zero failures in 52.77 seconds. All 16 candidate seasons
and reused released-baseline seasons complete 8,288 paired games. The original
cohort targets, tolerances, variance budgets, seeds and analysis remain frozen.
Independent raw-count/bootstrap review matches all 17 reported means/intervals
and all 32 input hashes exactly.

| Normalized five-metric source-error change | Mean | Paired 95% interval |
| --- | ---: | ---: |
| 1983 | −.057796 | [−.095399, −.016814] |
| 2024 | −.047137 | [−.083015, −.021631] |
| Equal-cohort pooled | −.052466 | [−.079377, −.024452] |

Both cohort primary estimates improve; all ten individual metric nonregression
guards pass. Those gains do not override two failed 1983 guardrails:

| 1983 absolute source-gap change | Mean | Paired 95% interval | Frozen limit |
| --- | ---: | ---: | ---: |
| Plays per team/game | +.723214 | [.488281, .919364] | .50 |
| Points per team/game | +.055525 | [−.362165, .491071] | .25 |

The 1983 mean plays move 65.231585 → 64.508371 against source 65.787946;
the candidate moves farther below the source. Mean points move 23.900112 →
23.955636 against source 21.828125; scoring uncertainty exceeds the locked
limit. Both 2024 scoring/pace guards pass. These are outcome tradeoffs, not
unit-test failures or grounds to relax a bound, add seeds or tune teams.

Coverage checks all 60 teams, 16 fixed contexts and candidate/default score
cells against the reviewed static atlas. Exact disjoint primary mass reconciles
without renormalization. All 1,210,309 REG callbacks reconcile to 1,077,580
primaries plus 132,729 specials. Across selected primaries, conditional own
secondary mass is 5.388% → 5.282% for 1983 and 6.619% → 6.568% for 2024;
known secondary fallback mass is zero. Retained other-neutral primary mass is
reported separately (about 1.39%/.90% for the candidate). This all-primary
counterfactual census includes excluded phases; compact records cannot prove
actual ordinary opt-in exposure or defense-adjusted secondary reachability.

All 94/86 newly crossed team/metric pairs are retained with raw numerators,
denominators, fixed targets/tolerances and eight paired season intervals.
Thirteen/five newly cross a mean bound; these counts are team/metric pairs,
not numbers of teams. No breach is dismissed as an outlier or tuned away.
Ignored `candidate-v6-rejection.json`, `development-v6-analysis-08.json.gz`,
`development-v6-coverage-08.json.gz`,
`development-v6-new-team-bounds-review.json.gz` and independent review receipts
retain identities, full results and adverse evidence compactly.

No held-out report exists, no promotion is permitted and AI-026 remains open.
The narrower secondary-information capability and credible development source
improvement are preserved as findings; they do not satisfy the full acceptance
goal. A subsequent proposal requires a general, source-backed pace mechanism
and review, without stacking rejected policies or fitting a pace coefficient.


## Post-sixth diagnostic: strategic family mass and tactical information

Read-only retained-receipt/atlas analysis finds a broad runward shift in the
sixth candidate. For REG primaries with emitted offense mode `normal`, run
shares on first/second/third downs rise about 2.8/3.0/3.1 percentage points in
1983 and 1.55/2.06/2.95 in 2024. The compact mode does not establish exact
ordinary eligibility. Independent raw decomposition finds 1983 runs per team/
game +.8867, pass attempts −1.4944, incompletions −1.0717 and sacks −.1155.
This supports a clock hypothesis without per-play clock or causal mediation.

One declared diagnostic separates released run/pass mass from within-family
secondary information. It freezes the released globally admitted support and
history-derived group mass, then tilts existing call weights by
`exp((corrected_score - released_score)/.45)` within each group. The run group
is Line Plunge/Off Tackle/End Run/Draw; the other five chart calls form the pass
group. Empty, zero, singleton and constant-delta groups retain original weights.
No family-local admission occurs: that alternative changes calls even without
new information. Previously excluded strong calls and zero-family blindness
remain explicit limitations. Identical-state family probability preservation
does not guarantee season mix, pace or source fit after trajectories diverge.

Eighty-eight actual-core controls cover both sides/B/QT, history, physical mass
and independent hand weighting. Forty-eight extreme favorable/adverse contrasts
improve conditional utility; 24 zero controls retain vectors. Twelve zero/
singleton limitations and four contrary weaker-secondary cases remain recorded.
A still weaker B3 versus numeric4 gains probability and lowers expected utility:
finite-temperature information correction is not universal utility maximization.
An initial zero-group fixture used −8, still admitted at global gap .84; its
corrected −20 fixture is excluded at gap .92. The original unaccepted source/log
are retained as a fixture error, without a production change.

All 960 static team-context vectors agree with independent review. There are
303 adverse conditional utility changes (136 historical/167 modern), including
calendar-weighted first-and-3 losses −.000126184/−.000157173. Third-and-10 gains
are only +.000169815/+.000170954, with total variation .003817/.003291; first-
and-10 total variation is .005443/.005644. These are tiny identical-state weight
changes, not historical benefit. Maximum family-mass error is 1.11e−16.
Fifteen modern contexts retain a zero family; one retains an excluded corrected-
best call within a positive family. Full support/opportunity rows remain stored.

Ignored `own-secondary-family-controls.json`,
`own-secondary-family-static-diagnostic.json.gz`,
`own-secondary-family-support-review.json.gz` and independent root receipts retain
all positive/adverse evidence compactly. The related proposed production scope
is marked **not selected**: these findings do not justify narrowing the wider
goal into a tiny compatibility-only candidate. No seventh production policy,
campaign, cutoff, coefficient adjustment or held-out access follows. A distinct
chart-conditioned defensive threat-prior concept requires analysis and review
of prior overlap, observability, ignorance and unknown-mass behavior first.


## Defensive threat-prior analysis: conditional prediction and ignorance

A distinct unimplemented concept weights each defensive formation's full-mass
upper utility by the opposing offense's released ordinary chart/state/history
weights. Released offense stays unchanged. This differs from the fifth
candidate's maximum-over-calls objective and from negative frequency forecasts;
none of the six historical candidates used this defensive point threat model.
It is an explicit conditional coaching assumption, not human probabilities or
worst-case robustness over offensive calls.

Independent public controls verify the prior before actual selection against
48 ordinary Hard factory distributions, both sides/down/distance/history. Its
inputs can be public charts, exact situation and existing engine call history;
no selected call, opposing AI object/mode, hidden RNG or future dice is needed.
Released history holds 96 primary calls total, not all-game memory. CLI saves
it; released web replay omits it and both own coaching/prior would use the same
reset engine history. This cannot be described as full continuity. Defensive
ordinary eligibility also does not prove offensive ordinary eligibility: hurry,
clock-killing and other helper boundaries differ and require explicit review.

A separate approved public synthetic diagnostic retains a coupled-input limit.
With Screen TD/Short 10 and other calls excluded, actual released prior is
.708660825/.291339175. A stops Short, B stops Screen; weighted upper utility
chooses B, with actual conditional utility .291339175. Replacing Screen with
unsupported primary makes the actual released policy choose only Short; the
weighted choice becomes A, with actual conditional utility zero. The switch
follows a changed actual opponent policy; it is not a same-policy prediction
failure or historical improvement. Screen has full unresolved interval mass
and upper 1.8, but zero prior weight: arbitrary human behavior remains outside
that conservative claim.

Separate baseline/model processes have identical four physical inputs,
actual-core matrices, factory vectors and RNG records. Independent review
recomputes exact weighted bounds/ties: 204 known cells match actual utility,
12 unknown cells contain actual utility, and 216 fixed-prior own-defense
opacity substitutions cannot lower that formation's weighted upper or make a
previously unselected opaque formation win. Fixed-prior monotonicity does not
establish robustness when the opposing chart changes the prior itself.

Ignored `defense-threat-prior-coupled-input-review.json`, baseline/model receipts,
independent review and `defense-chart-threat-prior-analysis-proposal.md` retain
all evidence and limitations. The completed static census covers all 788 ordered
calendar pairs at six fixed third-down distances, retaining all nine calls,
zero-weight threats and per-team effects. Independent review exactly matches
113,472 weighted utility/coverage values and 28,368 tie decisions. These are
conditional model comparisons, not actual branch exposure or historical gains.

Unresolved mass is common across formations in all 2,040 historical and 2,688
modern pair-contexts, so the upper-bound ranking equals neutral-utility ranking
on these charts. Zero-weight calls occur in 6/168 and 26/192 unique opponent/
distance priors, affecting 73/364 pair-contexts respectively. Their payoffs remain
reported. Baseline completion and gross passing yards per attempt already fall
below historical sources; stronger modeled defensive stops may worsen that fit.

Root reviewed the concrete production proposal against released offensive and
defensive branch ordering. Isolated protocol freezing and actual-behavior
failing tests preceded the implementation approval recorded below. The public-state guard must exclude
victory, end-of-half kicks, last-chance touchdown attempts, hurry-up, clock-kill,
red-zone and goal-line offense, including overtime's effective fourth-quarter
semantics. Existing defensive raw-quarter semantics and prediction/pressure RNG
order remain unchanged. Fresh pending-primary lifecycle tests precede any core
instrumentation; no new save or UI schema is proposed.

The ignored `root-defense-threat-production-scope-review.json` binds the reviewed
proposal and released source. Test-first review is now complete: the combined
116 public/synthetic cases produce 55 intended assertion failures and 61 passing
controls against unchanged released source, independently reproduced by root.
Four test files, 63 production Python files and six evidence logs are hash-bound.
The tests distinguish the proposed weighted objective from both uniform-call and
maximum-call objectives, validate history-sensitive priors, same-instance B/QT
mutations, zero-weight threats, actual-core utility, exact phase boundaries,
model-update order and RNG behavior on both physical sides.

An initial hand-computed floating expectation caused two fixture precision
failures; their source/log remain preserved and they do not count as behavioral
RED evidence. Only that hand calculation uses absolute 1e-12/relative-zero
comparison. Actual factory vectors remain exact, and rational priors use actual
released computational floats. Pending-handle lifecycle tests fail initially at
the absent marker; later success/no-op/exception assertions still require green
execution and are not claimed as baseline evidence.

Root authorized isolated implementation within the frozen proposal/protocol v10
scope, bound by `root-chart-threat-implementation-approval.json` and
`chart-threat-combined-red-receipt-r1.json`. Independent public baseline oracles
retain 900 offensive phase classifications and exact defensive choice/RNG records
for 724 excluded situations. Candidate checks must preserve those records. Root
reviews implementation and frozen identities before a pilot. No historical
campaign or held-out access is authorized. All original outcome gates and wider
AI-026 work remain open.

## Seventh experiment: frozen chart-conditioned defensive response

Isolated source `c6ecfcef56f93f9494c502f9a7f5ebac020e77cf` implements the reviewed
ordinary-third-down point-prior objective from released `10d7130`; offense and
other defensive branches remain released. Protocol v10 SHA
`a360028b48d6707d1420c30a1df7502a4bc98f027e50c97c84ae21e1a5999191`
keeps all original comparative sections and outcome limits. The frozen context
SHA `f1ffe86b64c8f1a9c9e4e8345ae4de9205fde253894f0fd930ef393c1af1c59c`
binds the exact source/runtime, unchanged chart/adapter identities, original
baseline and variance budget, and verified 1.10.2 asset receipt. Root independently
verified every tracked archive file and both freshly loaded cohort identities.

All 116 reviewed RED/control cases pass unchanged, including the previously
blocked pending adjudication/no-op/exception assertions. Additional actual-core
controls exposed a reused compiler issue: it parsed invalid B/QT tables even when
no priority path reached them. Four expected failures and nine controls preceded
a narrow lazy-parsing correction. Reachable invalid secondary tokens still raise
the core error; unused tables create no error. Source/test/log revisions remain
retained. Final phase/cache/CLI/auto checks pass 132 cases; the selected existing
AI/core/save/penalty suite plus these checks and documentation passes 2,224.
Backend checks pass 431 with 20 existing deprecation warnings; lint and documentation
checks pass. Root independently runs the 132 candidate/cache/adapter checks in a
fresh tracked-only archive without historical data; all pass. The copied per-call cache oracle now uses actual per-call resolver
utility instead of the changed aggregate weighting. Auto adapter exposure excludes
actual clock-killing offense, preserving the new explicit ordinary scope; no old
assertion was weakened or skipped.

The frozen actual shared-factory proof runs released and candidate policies in
separate processes on 24 public/synthetic contrasts, with identical released raw
call vectors and 1,296 exact physical per-call payoff cells per policy. Candidate
true point-prior utility improves in 20 cases and ties in four; state, history and
RNG remain unchanged. It covers both physical sides, own/opponent chart reversals,
weighted versus uniform/max-call distinctions, repeated history, B/QT content
changes and exact ties. This establishes only the declared conditional mechanism.
It is not human calibration, worst-call robustness or historical fitness. The
ignored `candidate-v7-frozen-factory-utility-proof.json` SHA
`e5ea937c93141f28ade71f56fdebd164a0d3d03afa822ec87dc8fc3912901385`
binds all inputs and complete payoff matrices.

Pre-outcome status: no seventh-candidate historical season or held-out report
exists. The versioned launcher retains unique/range-checked seeds, at most four
active workers, halt-on-first-failure with running evidence preserved, verified
source/context/release prerequisites and cost receipt before the remainder.
Twelve synthetic launcher checks pass. Pilot authorization still requires root
review of source/capability identities and this durable lock; the original
scoring .25, pace .50, five-metric, cohort, correctness and cost gates stay fixed.
Already understated completion/passing efficiency may worsen with more modeled
stops. All adverse prior experiments remain rejected, and wider AI-026 work is open.

## Seventh outcome: defensive gains fail modern completion fit

Reject source `c6ecfc` at development. All 16 candidate seasons and retained
16 baseline seasons complete: 8,288 paired games, with every raw game's scoring,
box, periods, selected-action accounting, physical return settings, playoff
completion and regular aggregates revalidated. The pilot cost receipt preceded
the remaining 14 seasons; bounded workers finish without failures. Root independently
recomputes all 17 primary/cohort/metric/scoring/pace means and paired-bootstrap
95% intervals exactly, with identical 32 input receipt hashes.

Normalized source-error changes (candidate minus baseline; lower is better) are:

| Scope | Mean | Paired 95% interval |
|---|---:|---:|
| 1983 cohort | −.031862 | [−.067999, +.005272] |
| 2024 cohort | +.060015 | [+.027169, +.086322] |
| Equal-cohort pooled | +.014076 | [−.005262, +.034911] |

The 2024 cohort worsens and fails its mean/upper-bound requirements; pooled
upper uncertainty also fails improvement. Modern completion-rate normalized
MAE rises +.349063, 95% [.254871, .417920], exceeding the fixed .25 guard.
The 1983 points absolute-gap change is −.053013, but its upper uncertainty
.361607 exceeds the fixed .25 scoring limit. The other nine individual metric
guards and both pace guards pass. These passing checks cannot override the
failed gates. Conditional synthetic defensive utility improvements do not
establish historical outcome improvement, consistent with the previously
declared risk that stronger modeled stops worsen understated passing fit.

The current native compiler's 788-pair, 42,552 call/formation-cell inventory
exactly matches the previously reviewed physical distributions and all six
static-target utility intervals. The selected-call/formation counterfactual
census reconciles all 1,219,215 REG callbacks, including primary and special
calls, enum names and policy-specific identities. Unresolved defensive-penalty
mass remains explicit: historical .013739→.013775 and modern .008950→.008915.
This census includes branches outside the candidate and does not infer actual
defensive eligibility/exposure or per-snap utility from compact offense mode/bands.

An independent root verifier, without importing the campaign harness or candidate,
recounts all 32 raw reports and reproduces every selected call/formation count,
special count, raw formation-enum count, exact rational coverage total and
per-defending-team aggregate. The 1,219,215 REG callbacks split into 1,082,849
primaries and 136,366 specials. Ignored
`root-v7-coverage-independent-review.json` binds the input catalog/report hashes
and verifier; this corroborates accounting, not actual candidate branch exposure.

All newly crossed team bounds remain recorded with targets/tolerances, eight
paired raw numerators/denominators/source errors and original intervals:
106 historical and 90 modern team-metric pairs, including 11/13 newly exceeded
mean bounds. No crossing is dismissed as an outlier or used for team tuning.
Development playoff frequencies remain coarse diagnostics at 1/8 increments.

Ignored `candidate-v7-rejection.json` SHA
`6ec633fa694f7aa8d3981c46f788e207caa399baa27b99829798e25df915b216`
binds integrity, analysis, independent agreement, full coverage, team review,
pre-outcome lock and source/protocol identities. No held-out season was run,
no limit/sample changed, and the candidate is not promoted. Wider AI-026 remains
open. The next authorized work is read-only hypothesis comparison of strategic
run/pass mass versus tactical full-matchup call choice; it is distinct from the
rejected fixed-support own-secondary family tilt. It has no production or
season-campaign authorization.

## Post-seventh public mechanism controls

The next read-only comparison separates released run/pass probability mass from
full-matchup choice within each family. It compares absolute matchup utility
with released scores plus matchup utility minus same-own-chart neutral-defense
utility. The latter cancels added secondary information when defense changes
nothing; it is a coaching estimate, not a causal or conservative bound. Both
matchup and neutral calculations use the original offensive attainment/progress/
negative-yard utility, rather than the seventh defensive experiment's binary
numeric conversion utility. No policy or formation prior is selected.

The first eight public actual-core cases cover both physical sides with all six
formation effects equal. Four neutral B/QT controls retain the exact released
weight mapping, while absolute utility changes it. Two material controls admit
a formerly excluded Screen into a positive-mass pass family, improving modeled
utility .08 → .94 while preserving run/pass probability .5/.5; a run family
with no globally admitted corrected call retains its released conditional mix.
Two adverse controls retain the loss when Screen 0 gains a defensive +3 but
remains weaker than Short 4: modeled utility .149621 → .147965. Information
correction with finite-temperature weighting is not universal maximization.

Root independently resolves all 864 constant-column physical payoff cells and
reconstructs the score differences, global admission, projected weights, family
masses and utility changes. Ignored `full-matchup-family-public-controls-r1.json`
and `root-full-matchup-controls-r1-review.json` bind the fixtures and verifier.
These empty-history, fully supported examples establish neither hidden-formation
prediction, unknown-mass safety nor season pace/accuracy. History, zero-family,
opaque-mass and support limitations still require review. No production change,
historical sweep, eighth protocol or season campaign is authorized by these
diagnostics; the original acceptance gates remain unchanged.

Review of the next public-control draft finds a scoring distinction that must
be fixed before it can support a policy: the tactical audit marks fumble
recovery pending, while released coaching deliberately assigns known fumble
risk utility −1 irrespective of recovery. An independent synthetic all-`F + 3`
offense against neutral defense confirms full pending-fumble mass but released
utility −1 (up to floating accumulation). Treating every pending outcome as
unknown neutral utility would silently change that declared score. The ignored
`root-full-matchup-fumble-semantics-review.json` retains the control and initial
floating-equality fixture correction. Offensive penalty risk and unresolved
defensive penalty choices also require separate review; a blanket pending flag
does not establish which coaching utility is unknown.

The bounded diagnostic correction passes 14 risk controls after six expected
failures and eight passing controls against its unchanged helper. It preserves
primary/QT fumble risk, the actual B-column numeric treatment of `F + 3`, and
own-chart OFF risk. Defensive, mixed/offsetting and defense-chart penalty
procedures remain unresolved. The helper explicitly requires constant defensive
rows per call; this is not a generic compiler fix. A separate frozen inventory
finds no OFF/DEF/PI cells in the 60 defensive CSVs, so the defense-chart penalty
limitation does not alter the rejected seventh campaign's evidence.

The next 66 public cases complete with neutral B/QT identity on all three downs,
positive/adverse secondary values, both physical sides and released repetition
history; new admission with empty-family fallback; zero-family blindness and
new admission beyond singleton released support. Unknown outcomes remain visible:
replacing a known adverse defensive result with an unresolved result can increase
its play's probability under neutral-point correction. Lower-estimate correction
does not exhibit that increase in these controls, but subtracting two marginal
lower estimates still does not bound the true effect. Identical opaque charts
can cancel their point scores while retaining full unresolved physical mass;
the uncoupled marginal difference interval is a loose outer bound, not a sharp
claim about identical-event uncertainty.

Root independently reproduces all 1,188 actual-core physical distributions,
7,128 formation/call matrix entries, exact intervals, original scores, history
weights, global admission and family projection. Ignored
`full-matchup-family-public-controls-r2.json` SHA
`4acfbbabfa91bf2fcab0e8e7548c3cca8c601fdb57ba5ca6cc48f8446673a3ed`
and `root-full-matchup-r2-independent-review.json` bind the complete evidence.
No uncertainty estimator or formation assumption is selected from these cases;
general matchup ranking, independent prior justification and production test-first
scope remain required before a new frozen campaign.

A fixed-input algebra review additionally establishes a limited projection
property: lowering one corrected call score cannot increase that call's
probability when every other score, original family mass and repetition factor
is fixed. A falling global maximum can admit competitors; an empty-family
fallback changes a sole admitted call's conditional probability from one to at
most one. Zero original families remain zero. All 21,384 finite controls agree,
including history, global support changes and empty/zero families. Ignored
`root-family-projection-fixed-input-opacity-review.json` binds the argument and
script. This supports investigating lower-estimate ranking when one call becomes
opaque with its own-chart reference fixed; simultaneous opacity changes across
calls, changes to the own-chart reference, true utility and historical outcomes
remain outside the claim. No formation objective is chosen by this property.

## Selected public objective and distinct-formation evidence

Before distinct-formation controls, root accepts the recommendation in
[full-matchup policy comparison](ai026-full-matchup-policy-comparison.md):
`released_score(p) + min_f L(match(p,f)) - L(neutral(p))`, followed by released
global admission/repetition and preserved released run/pass masses. This is an
explicit pessimistic per-call ranking under formation ignorance, not a forecast,
causal bound, equilibrium or guaranteed improvement of a sampled mixture.
Uniform-six averaging remains an explanatory alternative, not another candidate
to select by historical results. No current defense or hidden AI/RNG input is used.

All 28 exact public input tables are frozen before resolution (input SHA
`60bc7119ecebeac260e7c1ff269396ad364969ed267608b9064c6a8edcc37318`).
Both-side/history controls confirm material new support: previously excluded
Screen enters a positive pass family with mass .5; utility improves .08 → .74
against its least favorable formation and .94 elsewhere. Neutral B/QT identity,
empty/zero families, singleton support expansion and single-call opacity controls
also pass. Root independently reconstructs all 3,024 physical distributions,
minimum/mean/worst-formation identities, scores, history, admission, projection,
weighted utilities and intervals. Ignored
`full-matchup-distinct-formation-controls-r3.json` SHA
`b4bb7c4c7f1498428635a6954266ffa9b77710b30c2bb063cce3a79fb1ab8f2a`
and `root-distinct-formation-r3-independent-review.json` retain full evidence.

A contrary frozen table retains the objective's cost: min-ranking utility is
.146009 in every formation, versus released .585383 in A–E and −.298724 in F.
Uniform ranking instead yields 1.212359 in A–E and −.933346 in F. No formation
probabilities are inferred and neither gain nor loss is hidden. Root's separate
108-cell actual-core control matches the empty-history result on both sides.

Next authorized work is a concrete isolated implementation proposal and public/
synthetic failing tests from released `10d7130`, observing actual ordinary Hard
factory vectors on all three downs and retaining special-phase/RNG controls.
Generic penalty-source classification, full physical mass, lazy secondary parsing
and bounded content-aware caches require explicit tests. Production edits require
that review and meaningful RED evidence first. No historical sweep, eighth
candidate campaign or held-out access is authorized by these capability controls;
all original source-fit, correctness, scoring, pace and cost limits remain fixed.

## Eighth test-first preparation

The [concrete implementation proposal](ai026-full-matchup-production-proposal.md)
is reviewed for isolated test authoring from released `10d7130`. It keeps the
selected objective and existing special-branch ordering; parser-None B/QT tokens
must use the core's uniform fallback, whereas parser-raised errors remain errors
only when reached. A narrow pending-primary identity handle is separately within
the test-first scope, without save/UI/history transport. Production edits still
require review of the complete meaningful RED/control evidence.

The first immutable public batch independently reproduces six expected actual
factory assertion failures and 18 passing controls, with zero errors/skips.
Across both physical sides and all three downs, released selection keeps
Line Plunge/Short at .5/.5, while the declared matchup oracle requires Line
Plunge/Screen at .5/.5. Reverse-favored Short and neutral B/QT controls pass.
Root verifies all 63 production Python hashes remain released and the production
diff is empty. Ignored `full-matchup-first-batch-red-receipt-r1.json` SHA
`84e3c5628de513c82562c127be40d76e06c6ae03ee0461b85188232542560b50`
and `root-full-matchup-first-red-independent-review.json` bind this evidence.
This first batch does not prove the remaining generic compiler, cache, pending
lifecycle, special-phase, adapter or source-fit requirements.

A separate root hash-seed control refutes an initial review concern about the
diagnostic's population order: its ordered raw mappings produce identical
populations, probabilities and 100 sampled calls under all six tested hash seeds.
The failed prediction is retained in
`root-family-projection-hashseed-order-review.json`. Ordered production sums and
populations remain a reproducibility convention, not a claimed diagnosed
sampling defect or a new release blocker.

Before production edits, root also freezes 4,866 actual released neutral-defense
phase records: 654 ordinary and 4,212 special-phase calls across both sides,
all three downs, Q2/Q4/overtime, exact clock/score/field boundaries, plus six
legitimate first-quarter zero-clock untimed-down cases. Each retains the actual
selected tuple, mode, choice vector and global/offense/defense RNG state hashes.
The neutral reference means candidate identity should match every record, not
only special branches. Ignored
`root-full-matchup-released-phase-oracle.json.gz` SHA
`42b6433cbe2fd67b4a953b5883c4c5edd6bd76300762919fe1542232f5781500`
binds fixture, baseline context and source; this is a pre-change public oracle,
not evidence that any unimplemented candidate already preserves those records.
Root independently reruns the broadened unchanged-source batch: 82 expected
baseline failures and 114 passing controls in 5.74 seconds, with no setup errors.
All 63 production hashes still match released source. Coverage now includes
actual factory vectors, history and family projection, penalty-source risks,
reachable B/QT physical fallback mass, lazy parser errors, live chart mutation,
preview purity, cache limits and exact excluded-phase/RNG records. Earlier
secondary/punt fixture mistakes are retained separately and are not counted as
behavior evidence. Seven pending lifecycle cases currently stop at the absent
identity handle; their downstream assertions remain an implementation gate.
Ignored `root-full-matchup-combined-red-review-r1.json` binds the complete test,
fixture and production hashes and terminal log. Actual audit-observer parity
coverage and the boundary between ordinary caches and unchanged default/hurry
caches require clarification before production authorization. No season campaign
or historical source-fit claim follows from this baseline evidence.

## Eighth isolated implementation authorization

The remaining cache scope is clarified: the new ordinary model owns separate,
bounded, content-aware estimates; the existing default/hurry strategy and its
cache behavior remain unchanged. A primed 123-context default-cache preservation
control passes. A complete public-2026 auto-game control also confirms that the
existing audit observer records the actual ordinary selector vectors after
history. Root independently reproduces the revised state/observer batch's nine
expected behavior failures and three passing controls, with all 63 released
production hashes unchanged. This clarifies which cache is bounded; it does not
weaken a behavior expectation.

Root's explicit-checkout phase comparator additionally reproduces the immutable
4,866-row released oracle exactly, including all selected tuples, weight vectors,
modes and global/offense/defense RNG hashes. This baseline self-control validates
the comparator before candidate use; candidate preservation remains unverified.

Production implementation is now authorized **only in the eighth isolated
checkout**, following the selected full-matchup lower/min objective, original
family masses and phase boundaries, generic lazy physical compiler, separate
ordinary caches, shared audit weights and narrowly scoped transient pending
identity handle. Ignored `root-full-matchup-production-scope-approval-r1.json`
SHA `11e1b4e75fe34c8878941521555f975b8282c602e8133dfe27c75cf1ff36d351`
binds the reviewed proposal, full test/fixture hashes, released production hashes
and independent evidence. All original failing assertions must pass without
weakening; source review and focused/clean-checkout checks precede runtime freeze.
No historical sweep, pilot, campaign, held-out access, merge or push is approved
by this implementation authorization. Original acceptance gates remain fixed.

For independent compiler review, root freezes a complementary nonconstant-row
public synthetic oracle before candidate comparison. It enumerates all 8,100
actual resolver cells (nine calls, six formations, 30 offensive physical rows,
five defensive rows), retaining exact physical outcome mass and original utility
at targets 1, 3, 7, 10 and 29. Inputs vary numeric gains/losses, BLACK,
interception, fumble, touchdown and terminal passing-fumble/incompletion cells;
this oracle deliberately excludes penalties and B/QT, covered by separate tests.
Ignored `root-full-matchup-varied-physical-core-oracle.json` SHA
`e6bc1da0b08df32d5e75b72f071d2047e3daeedcc621707e6190bcd246e41d5c`
binds the actual resolver and exact inputs/results. Initial serialization used
an incorrect defensive metadata attribute; that setup failure and its correction
are retained separately and are not evidence of a production defect. No candidate
comparison or historical improvement is yet established by this frozen oracle.

## Initial eighth implementation and independent review

The final test-only baseline receipt records 82 expected behavior failures and
116 controls, zero errors/skips, across seven modules and two public fixtures.
Root verifies the complete frozen hashes/log and reviews the lint-only changes;
assertions remain intact. The initial implementation then passes all 198 focused
cases, including the downstream pending lifecycle assertions and actual audit
observer parity. The separate ordinary model leaves the default strategy source
unchanged. Shared fallback constants and the narrow pending identity lifecycle
reuse the previously reviewed seventh-experiment core diffs.

An additional actual-core oracle revision explicitly includes `TD` and defensive
`(TD)` outcomes: the first oracle's offensive `(TD)` token did not itself produce
a touchdown. Both inputs/results remain immutable; this is a fixture coverage
clarification, not a gameplay finding. Ignored
`root-full-matchup-varied-physical-core-oracle-r2.json` SHA
`2d6834b2d588c2529dcc380ed1f65892f93f1481a3a9440a8c6cb6996764c1ed`
binds 8,100 core cells. Root independently compares all 54 compiled physical
distributions and 270 exact original-utility estimates: zero mismatches against
the initial model. The oracle binds the shared-constants resolver source; no
penalty or B/QT claim follows from this complementary numeric/risk check.

Independent review nevertheless finds a missing availability edge: an offensive
column with no physical rows is absent from released selectable calls, but the
new compiler still traverses its defensive QT branch and can raise on an invalid
secondary token. Merely old-threshold-excluded populated calls must remain in
scope for new admission. The ignored
`root-unavailable-call-lazy-secondary-probe.json` retains the reproduction. The
agent confirms the finding and is adding empty/nonphysical-column regressions
before the fix, retaining populated full/sparse-column controls that must raise
for genuinely reachable invalid secondary data. This stays within the declared
availability/lazy compiler contract; it does not change the selected policy.

The initial candidate also matches all 4,866 phase records exactly. That result
is provisional: its first comparator binds only the main AI source and predates
the availability correction. The final comparison will use the separate revised
verifier, which binds all production source files before imports and requires
those bytes to remain unchanged through comparison. Stable-source qualification,
existing regressions and the frozen paired-season gates remain outstanding.

The availability correction follows four expected failing regressions and four
passing reachable-error controls before the fix; all eight then pass. Root
independently reproduces both groups. Empty/nonphysical-only columns retain full
unavailable bookkeeping mass and skip secondary parsing; populated full/sparse
columns remain analyzed even outside released competitive support. No existing
assertion is weakened. The combined focused suite passes 206 cases in 6.92 seconds.

Stable model SHA
`a7119a503f313a2facd8eba98f682d0456abddca706902e63f7a1c886eef9e77`
passes root's repeated independent 54-distribution/270-utility comparison and all
4,866 frozen phase records, with zero mismatches. The revised phase verifier binds
all 64 production source hashes before imports and verifies unchanged bytes after
execution. Ignored `root-full-matchup-phase-stable-candidate-review-r1.json` SHA
`b8ca75cb79de208f46149f7125269239dd2535c4e9ddfdd98827b7aaa49ef6da`
and `root-full-matchup-varied-physical-compiler-review-r2.json` retain these checks.
Existing focused regressions, adapter paths, clean tracked-source validation and
runtime freeze/pilot review remain required before a paired historical campaign.
The seventh experiment remains rejected; the eighth is not yet historically
qualified and no held-out outcomes have been opened.

The broader 37-file existing regression run finishes with 2,135 passes and 54
failures, all confined to two offense-only ranking/variety suites. Those fixtures
replace own offense but retain nonneutral public sample defensive charts, so their
old exact own-only selector expectations no longer express the intended premise.
The approved repair supplies explicit complete neutral defenses on both physical
sides in those two fixture locations. Root reviews the exact diff and AST-verifies
all 61 assertions and all parametrization remain unchanged; no threshold or sample
size is reduced. Both complete corrected files then pass all 167 cases in 13.97
seconds. Initial failing output, original fixture sources and the independent
`root-full-matchup-neutral-fixture-review-r2.json` remain local and ignored.
Actual opposing-defense effects and adverse conditional utility are still covered
by the separate full-matchup regressions. Production policy is unchanged by this
fixture correction. Adapter and clean tracked-source validation remain pending
before the frozen runtime/protocol and bounded historical pilot can be reviewed.

Concrete adapter validation now passes: the CLI both-side controls and complete
synthetic auto game pass three cases. The auto callback independently reconstructs
original numeric utility, global competitive admission, repetition history and
family projection at actual ordinary decisions, with at least three materially
changed calls on each offense and real game completion. Root separately verifies
both CLI dispatch cases.

Fresh and loaded-replay web cases preview three times without state/global-RNG/
history mutation, then execute the newly admitted Screen on both physical sides.
The complete web AI-mode file passes 36 cases; root independently reproduces the
four new cases (one existing Starlette deprecation warning). The full backend
suite passes 431 cases in 6.69 seconds, with 20 existing Starlette/Pydantic
deprecation warnings and no reported skips. Root rechecks all 64 production hashes
against the stable phase receipt; no production bytes changed. Ignored
`root-full-matchup-adapter-review-r1.json` binds reviewed adapter sources, terminal
logs and the complete production identity. No further adapter expansion is needed
for this implementation scope. Clean tracked-source focused validation and the
source commit/receipt precede frozen protocol and historical pilot review.

The eighth candidate is committed locally as
`e58d1238191942ee8ca00df2eaf2d9d4ab22527c` (`v1.10.3: Separate strategic mix
from matchup call selection`). Root reviews the bounded 20-file change and
accurate experimental-policy documentation; all 64 production hashes still match
the independent compiler/phase review.

A tracked-files-only archive of that commit passes all 2,193 selected focused
regressions in 33.25 seconds, with no errors or skips. Root verifies all 1,068
tracked paths are present, all 64 production hashes match, no external symlinks
exist, and fresh-process core and fixture imports resolve inside the archive.
Ignored `root-full-matchup-clean-archive-source-review-r2.json` binds the archive
source review and terminal log. This is the declared pre-freeze focused check,
not a claim that the entire pre-push full-regression checklist has run.

The implementation is ready for frozen protocol/identity review. The agent is
preparing the eighth experiment's versioned protocol and baseline compatibility
bridge; root must verify original seeds, metric/scoring/pace/correctness gates
and cost limits before authorizing a bounded first-seed historical pilot. No
historical outcome from this candidate has yet been generated or inspected.


## Eighth experiment frozen source and pre-outcome capability proof

Candidate source `e58d1238191942ee8ca00df2eaf2d9d4ab22527c` is frozen in a
tracked-only snapshot after 2,193 focused passes, 431 backend passes (20 existing
deprecation warnings), CLI/complete-auto controls and physical-side web replay
checks. The retained initial 54 existing failures are repaired only by explicitly
neutralizing defenses in two own-only test fixtures; every assertion, threshold,
parameter and sample size remains unchanged. The 4,866 released phase records and
independent nonconstant physical resolver oracle still match the stable source.
The public coaching/audit guides describe this as an experimental, unqualified
policy and retain the strategic-mass, uncertainty and finite-temperature limits.

The original protocol's five comparative sections and four numerical outcome
guard sections, all seeds, variance budgets and cost limits remain unchanged.
The first eighth-candidate protocol v11 accidentally inherited two execution-order
strings referring to the seventh defensive candidate. Because its first context
already existed, both files remain immutable; metadata-only protocol v12
(`de7443a2da3ae33009cce88f5e938128db50d9078d3431939ef085d1853e4705`)
corrects those strings before any outcomes. The final context is
`frozen-candidate-v8-context-r2.json` SHA
`7e2ef43f12f677118ea8b505b2298925a24d24d68959f8f806eb90de6244a57a`.
It binds the same source, exact original baseline charts/adapter and freshly
attested loaded runtime. The v12 compatibility bridge retains the original
released baseline's identity rather than relabeling its existing receipts.

Ignored `candidate-v8-frozen-factory-utility-proof.json` SHA
`07a237ac2d4c04d6c382d05a23dcd21cef0ad4ee4a6387e774badf975ff11b85`
binds separate actual baseline and candidate processes to 36 frozen public tables:
the retained 28 distinct-formation tables plus eight first/second-down material
admission/history controls. Each policy evaluates 1,944 matchup and 1,944 neutral
formation/call distributions with full physical mass and original offensive
utility. Actual factory vectors match the independent centered-score, global
admission, repetition and family projection oracle; both policies preserve state,
history/global RNG and consume the same single namespace draw in these controls.

Of 216 formation comparisons, 102 supported comparisons improve, 50 worsen and
60 remain unchanged; four have weighted unknown mass and cannot be treated as
true expected-utility comparisons. Every one of the 72 material-support
comparisons improves by .66 to .86. The contrary-formation losses (minimum
-.439375), neutral identity, zero-family limitations and uncertainty are retained,
not averaged away to claim universal improvement. This proves the declared
conditional coaching capability, not historical acceptance or an optimal mixture.

The eighth launcher, worker, pilot verifier and analyzer preserve the reviewed
fail-halt/identity/accounting/statistical logic with version/path substitutions.
Twelve synthetic launcher controls pass, including invalid indices and stopping
new submissions after failure. Root source/context/proof review, a committed
pre-outcome lock and explicit first-seed pilot authorization remain required.
A successful paired pilot correctness/cost receipt must precede the remaining
14 development seasons; all development gates must pass before held-out review.
No eighth historical outcomes or held-out seeds have been executed, and AI-026's
wider capabilities remain open.

## Eighth pilot integrity and cost gate

Root independently verifies the complete first-seed pilot before authorizing
remaining development work. Both candidate seasons pass (1983: 233 games,
2024: 285 games), and all 1,036 candidate-plus-retained-baseline game receipts
reconcile identity, physical return settings, REG/postseason inventory, scores,
play/call accounting and raw aggregates. Pilot workers finish in 102.74 and
126.05 seconds; the conservative sequential full-campaign projection is
5,946.05 seconds and 67,785,888 compressed bytes, within all original cost limits.
Measured free disk is 23,922,556,928 bytes.

Ignored `paired-v8-pilot-cost-gate.json` SHA
`124efa5bcc24bb278d1ead305b66bdf5bbae829974a1d108332f51e7f4d74872`
is written before any remainder launch. Independent
`root-v8-pilot-cost-review.json` and
`root-v8-development-remainder-authorization.json` authorize exactly indices
1 through 7 in each cohort, using the frozen source/protocol/context, max four
workers and the reviewed stop-submitting-on-failure behavior. All failures must
remain; no seed replacement or overwrite. No pilot efficacy aggregate is used
to select, tune or accept this policy.

The complete eight-seed development set must first pass integrity against the
original 16 baseline reports, then every unchanged primary, individual-metric,
scoring and pace gate is evaluated. Held-out seasons, promotion, merge and push
remain unauthorized. Source artifacts and the committed pre-outcome lock remain
immutable; this paragraph records only the subsequent pilot/remainder state.

## Eighth outcome: modern source gains do not qualify both cohorts

All 16 candidate development seasons complete successfully. The paired integrity
verifier rechecks all 32 candidate/baseline reports and 8,288 games, including
postseason inventories, score/period/box/call accounting, physical return controls,
raw aggregates and strict original policy-specific identities. No game failures,
seed replacements or held-out outcomes occur. The complete frozen analyzer and
root's independent raw-total/20,000 paired-bootstrap calculation agree exactly
on all 17 means/intervals and all 32 input hashes.

The eighth candidate is rejected. Primary normalized source-error changes are:

| Cohort | Candidate minus baseline | Paired 95% interval |
| --- | ---: | --- |
| 1983 | +.002497742 | [-.051642913, +.050782838] |
| 2024 | -.049463213 | [-.081803527, -.011009074] |
| Equal-cohort pooled | -.023482735 | [-.061211168, +.013719298] |

The 1983 mean is above zero and its upper endpoint exceeds .05; the pooled upper
endpoint is not below zero. The 1983 scoring absolute-source-gap change is
+.155691964 with interval [-.117473493, +.424114118]; its upper endpoint exceeds
the original .25 budget. Both pace guards, all ten individual-metric guards and
2024 scoring pass. These passes do not override the failed joint acceptance
conditions. No sample expansion, seed change, bound relaxation, promotion, merge,
push or held-out campaign follows from the modern-cohort improvement.

Signed gaps retain contrary source evidence: completion already falls below
historical targets in both released cohorts; the candidate narrows that gap in
2024 but widens it in 1983. Rushing efficiency already exceeds both sources, and
its league gap and team-macro absolute error increase. Sack rates remain below
sources. These are descriptive results, not causal explanations or permission to
fit team coefficients. Improving declared coaching utility and improving source
fidelity remain separate claims.

The frozen generic compiler's native coverage catalog retains all 788 ordered
calendar matchups, 42,552 call/formation cells and six explicitly static utility
targets, plus all 60 same-own-chart neutral references. Each physical mass and
unknown-category sum reconciles. The census independently validates all 32 input
identities/aggregates and accounts for 1,215,523 REG callbacks: 1,081,351 primary
calls plus 134,172 specials. Selected-call/formation counterfactual unresolved
mass is 1.3739% to 1.3538% (1983 baseline/candidate) and .8950% to .9082% (2024).
Only defensive-penalty uncertainty occurs in these charts. Compact mode/distance
bands do not establish actual ordinary-branch exposure or exact per-snap targets.
Neutral-reference uncertainty is retained; lower subtraction is not presented as
a conservative causal bound.

All newly exceeded team bounds remain reported with denominators, paired errors
and intervals: 118/93 new pairwise-or-mean team/metric crossings, including 13/7
new mean crossings (1983/2024). No team is tuned or dismissed as an outlier.
Ignored `development-v8-new-team-bounds-review.json.gz`,
`development-v8-coverage-08.json.gz` and the native catalog preserve complete
rows. The final local rejection receipt is `candidate-v8-rejection-complete.json`;
the original rejection, source, pre-outcome lock, negative tests and every season
receipt remain immutable. AI-026 and the release objective remain open.

Eight rejected experiments now show that a resolved chart response or improved
synthetic coaching objective does not establish historical fidelity. Another
small utility/prior variation is not selected. The next work is a proposal and
public test design for a structural football mechanism, explicitly separating
remaining-down/first-down planning and strategic counterplay from historical
source calibration. No ninth implementation or campaign is authorized.

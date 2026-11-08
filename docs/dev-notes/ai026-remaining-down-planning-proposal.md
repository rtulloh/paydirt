# AI-026: remaining-down planning after eight rejected experiments

Status: structural proposal and public test design only. No ninth production
implementation, protocol, historical sweep or campaign is authorized. The
[eighth outcome](release-1.10.3-plan.md#eighth-outcome-modern-source-gains-do-not-qualify-both-cohorts)
remains rejected, and every held-out seed remains unopened.

## What the experiments establish

The released coach's missing chart response is real, but correcting information
or increasing a declared utility has not established historical fidelity.

| Experiment | Mechanism | Decisive development limitation |
| --- | --- | --- |
| 1 | Full matchup, all ordinary offensive downs | Historical completion/sack/pace losses; modern sack guard fails |
| 2 | Third-down matchup only | Historical pace guard fails |
| 3 | Third-down binary continuation utility | Historical pace guard still fails |
| 4 | Revealed-formation prior | Historical pace guard still fails |
| 5 | Defensive upper minimax | Modern primary, pooled evidence and historical scoring fail |
| 6 | Own B/QT resolution only | Historical pace and scoring fail despite primary gains |
| 7 | Defensive released-chart threat prior | Modern completion/primary, pooled evidence and historical scoring fail |
| 8 | Matchup correction within released strategic family masses | Historical primary, pooled evidence and historical scoring fail; modern primary improves |

These results reject another small prior, coefficient, cutoff or finite-utility
variation selected to pass the same development seeds. The eighth experiment
also shows that preserving same-state run/pass mass does not establish source
fidelity. All original guards remain binding.

Three structural questions remain: valuing the remaining downs rather than one
snap, choosing strategic mixtures rather than treating them as fixed, and
accounting for opponent counterplay without seeing the selected call. The next
bounded diagnostic isolates the first. It does not simultaneously redesign
mixing, learning or defensive policy.

## Proposed diagnostic objective

Measure the probability that the original offensive team earns a new first down
or touchdown before reaching fourth down or losing possession. This is a bounded
series-continuation objective, not expected points, win probability, an optimal
full drive, or a model of historical coaching. Stop immediately at that first
success: a down reset must not begin another series inside the same value.

Evaluate all nine legal primary calls using actual full physical resolver
probabilities. For known legal transitions, a finite remaining-down oracle uses
terminal values success=1 and failure=0 and propagates the next-down value.
It must use authoritative engine transition semantics rather than inventing
penalty, first-down or possession rules. The first public witness has identical
neutral effects in all six formations, so no empirical/uniform/robust prior is
chosen to manufacture its result.

At this initial diagnostic stage no production sampling formula is selected. In particular, replacing a
scalar score while retaining a temperature would introduce another finite-mixture
tradeoff; proving the best-action oracle does not prove the actual sampled
coach's value. The diagnostic must calculate the actual released mixture's
finite-series value as well as first-action values under optimal continuation.

## Frozen public witness and read-only actual-core proof

Use public 2026 teams with synthetic replacement charts, Q1, ten minutes left,
first-and-ten at own 40, no pending procedure or conversion, on both physical
sides. Every formation/subrow is neutral. SHORT_PASS gains four on every physical
row. LONG_PASS gains ten on black-three rows 30–39 (108/216 physical mass) and zero
otherwise. Every other primary call gains -20; retain its full mass and include
it in the oracle rather than silently deleting legal calls. No secondary table
or unsupported token influences this initial numeric witness.

The released own-chart first-down scorer gives SHORT_PASS .32 and LONG_PASS .9.
Under the explicit three-attempt oracle, initial SHORT_PASS followed by optimal
continuation succeeds with probability one; initial LONG_PASS succeeds with
probability 7/8. Two certain four-yard gains create third-and-two. Root's retained
`root-remaining-down-numeric-witness.json` SHA
`3bea1ffda66e4a9d884c9dd81cfbaec9dcb0e44954737ab86605c63b1bafb2de`
proves only this arithmetic and released scoring, not actual resolver/factory
behavior or the released mixture's complete success probability.

The next read-only proof must freeze exact input tables before execution, resolve
all 9 × 6 physical distributions through the released core, observe actual
factory population/weights/RNG on both sides, and calculate full finite-series
values from legal transitions. Preserve raw matrices, histories and state/RNG
identities so an independent verifier can reconstruct every value. Verify that
unselected current calls and future dice cannot affect the result. No seasons.

The bounded read-only prototype now passes on both physical sides. Ignored
`remaining-down-public-proof-r3.json` SHA
`657b2411b6df6a592fa12ea3c1a1d8830a48c588f348dab3bec7ab932d2d7b62`
binds 16,200 actual physical core cells, all nine calls/six neutral formations,
actual factory vectors and core-applied continuation states. Optimal whole-series
success is one; the actual released finite-temperature policy succeeds with
probability .7981686716503044.

A necessary contrary result changes the interpretation: under **released future
calls**, initial SHORT_PASS succeeds with probability .7478002608, less than
initial LONG_PASS's .8120490376. Thus changing only the first call to the safe
one would worsen that policy. Values one and 7/8 assume optimal continuation;
they must not be substituted for the sampled policy's future. This is a
whole-series planning opportunity, not proof that the isolated released first
choice is dominated. At that initial stage no candidate sampling rule had been tested; the later read-only mixed-policy demonstration below is separate.

Core zero/negative gains, first-down reset, goal-to-go touchdown, original-offense
interception/safety attribution and an unreachable eighty-yard target pass.
Projection records calls through the existing core history hook. Memoization by
down/distance/field is justified **only** for this fixed Q1 numeric episode:
no score/phase change before terminal, clock above five minutes, distinct
advancing downs and no pending/replay branches. Every released cache hit checks
actual factory weights again under its recorded history. This is not a generic
factory-state cache or legal-series planner.

Outside that explicit numeric scope the preview is unsupported. Independent
clones produce identical released selected calls, final state/history and global
and both namespace RNG records with/without that unsupported preview. The
selector itself may consume RNG or change special state; no purity assertion is
imposed on those existing branches. A future production planner still needs its
own complete phase identity controls.

The first prototype revision reached the touchdown edge then used a nonexistent
`PlayOutcome.is_home_team` attribute. The second used an invalid requirement that
released special selectors themselves be pure. Both scripts/inputs/failing logs
remain retained. Revision three attributes touchdowns using original-offense
scoreboard changes and compares special execution from identical clones; these
are evidence-tool corrections, not gameplay findings.

## Why this differs from the third-down binary candidate

The earlier binary candidate changed only the utility of the current third-down
play. It could recognize that fourteen yards on third-and-fifteen fails, but it
could not value a first-down four-yard gain through the resulting second-and-six
and third-and-two. In this witness the missing decision is already on first and
second down. Neutral defense makes the eighth centered correction exactly zero;
a different formation prior or secondary parser also cannot repair it.

A planner must therefore represent legal continuation states, rather than merely
use another current-snap reward or down restriction. Whether and how that value
should affect the existing competitive mixture requires a separate reviewed
production proposal after the diagnostic, including equal-value variety and
history behavior. The best-action oracle alone does not authorize an argmax
selector or probability rescaling.

## Required boundary and negative controls

- First down and touchdown end the original series immediately; preserve actual
  goal-to-go/field boundaries and do not count a defensive return score as success.
- Known interceptions and possession-losing outcomes terminate at zero, even if
  their spot or return distance exceeds the original line to gain.
- Zero and negative gains retain full probability and advance only as the engine
  specifies. No progress reward substitutes for eventual conversion probability.
- Very long distance beyond every remaining legal gain has probability zero;
  already-invalid distance/state inputs must follow authoritative validation,
  not a hidden clipping or season-specific lookup.
- Down-three terminal values, down/line-to-gain reset, physical home/away swaps
  and mixed gain/loss distributions must reconcile with actual engine results.
- Missing/unsupported, penalty and unresolved-fumble branches are not
  renormalized away or assigned invented transition probabilities. Initially
  retain their mass as an explicit [0,1] continuation interval and report
  coverage; do not claim a generic production planner handles them.
- Planning previews must leave state, history and every RNG untouched. If a
  later implementation is approved, default/hurry, fourth-down, conversions,
  victory, clock-killing, goal-line/red-zone, end-half/OT and pending-procedure
  paths require exact released population/selection/RNG controls. No UI logic.

## Coaching correctness and fidelity are different exit criteria

The witness supports a football reason to prefer a plan: exploit remaining downs
to secure a first down. It supplies no reason that historical completion, rush
YPA, sacks, pace or scoring must improve. More conversions can increase scoring
and offensive snaps, worsening existing source gaps. Released completion is
already below both sources, rushing efficiency is above both, and sacks are
below both; none is an invitation to fit a scoring bonus or team coefficient.

The eight rejections also expose a calibration boundary: charts and historical
source targets do not themselves specify a historically calibrated coaching
policy. A rational coaching improvement can move aggregates away from those
targets. A new planning capability would still need the original independent
source-fit/scoring/pace validation, and could fail honestly. No source outcome,
season/team identity, prior candidate's seed result or historical qualifier may
enter its payoff, eligibility, cache, mixture or parameter choices.

Before a ninth implementation, review the actual-core diagnostic, legal-state
coverage and unresolved-transition limits, then decide whether a bounded planner
and operational mixture are justified. Do not launch a campaign simply because
the arithmetic oracle is better. The defensive and broader chart-strength
capabilities of AI-026 remain open throughout.

## Operational rule proposed for one read-only mixed-policy demonstration

Fix the released same-state raw weights as prior b, including its global
admission and history. Keep that positive support; do not admit zero-prior calls
or preserve separate run/pass masses. First-down value is independent of call
family, while the prior retains excluded-call and zero-family limitations. No
variant or development outcome chooses this rule.

Work backward over legal remaining downs. Compute Q_pi using the continuation
value of the same tilted policy, then set pi proportional to
b * exp((Q_pi - max Q_pi)/.45), with the existing .45 temperature and ordered
calls. Equal Q values return exact released weights. This inherited preference
scale is not a calibrated football constant. No additional gap or threshold.

In a fully known acyclic series, weighting monotonically with Q gives
E_pi[Q_pi] >= E_b[Q_pi]. Backward induction with improved future values then
gives V_pi >= V_b. Verify actual computational mixed values state by state;
optimal-max continuation is a separate oracle. Initial safe-call probability
need not increase. This is not an optimal mixture or historical-fidelity proof.

Abstain to exact released weights if any positive-prior transition or its future
policy is unresolved, cyclic, unsupported or outside known field/phase/clock
semantics. Never renormalize unknown mass away. Future special branches must use
the retained policy or explicit uncertainty, never assumed continued planning.
For the frozen witness, the first-down line is own 50: nonterminal gains remain
below it, losses remain ordinary until safety, and the three Q1 snaps stay above
five minutes. Those bounds and history/actual-vector checks justify this case's
closure only; no generic distance-only cache or phase claim follows.

Fallback can raise a call's probability relative to a previous supported tilt;
this is not universal opacity-monotonic safety. Unknown zero-prior calls remain
unselected. Real charts contain penalty/DEF mass, so this scope may yield little
or no usable exposure. Before production, demonstrate material transition
coverage or review authoritative resolution of those branches; do not implement
a near-no-op or silently replace unknown enforcement with heuristic risk.
Better conversions may worsen scoring/pace. Only the fixed public mixed-policy
demonstration is approved, not a ninth production policy or historical campaign.

## Fixed mixed-policy result and real-chart applicability limit

The single rule above was frozen before execution on the same public table.
Ignored `remaining-down-mixed-inputs-r1.json` SHA
`70114e0dc3efbbd9b8371c7857903e20910a45148e174411f34e5e0f1365031f`
binds the proposal, source, exact table and formula.
`remaining-down-mixed-proof-r1.json` SHA
`c6570a71fcafaab3b6cdf0772fce3279f5dce0ab1ff6a8f5992106b680146ec1`
reconstructs all 16,200 actual physical cells on both sides. Actual released
series success .7981686716503044 increases to .837995829443849 under the
self-consistent sampled continuation, a gain of .03982715779354462. Every
reached-state action value, prior, tilted vector and monotonicity certificate
is retained; root's independent reconstruction agrees exactly. Optimal value
one remains a separate oracle. This does not establish historical fidelity,
new-support capability, opponent-defense response or generic phase/clock closure.

The pre-execution proposal is preserved byte-for-byte in ignored evidence.
An immutable clarification corrects inherited proof labels saying "no candidate
sampling formula": one read-only formula was explicitly demonstrated, while no
production policy was selected or deployed. Numerical/source bytes are unchanged.

The fixed applicability census then checks all 788 ordered calendar matchups,
downs 1–3, distances 1/3/6/7/10/15 and empty/repeated own history: 28,368 explicit
ordinary counterfactual contexts. **Zero** have all released positive-support
calls utility-supported across all six formations, even under that optimistic
necessary condition. The stricter count additionally treating fumble recovery
and offensive-penalty transition as unmodeled is also zero. The cohorts contain
12,240/16,128 contexts (1983/2024), or 16,128/19,584 calendar-weighted contexts.
Every row retains full prior/mass and all runtime/chart identities reconcile.
Root's independent reconstruction agrees. Ignored
`remaining-down-support-availability-r1.json.gz` SHA
`9f058a1e3f37559b7aa51c5265c07d910bd789de8eaa0af66f3bf4c54d324d90`
contains complete rows.

These are current-result necessary conditions, not future-state closure or
actual eligible-snap frequencies. Utility support is insufficient for planning:
fumble risk -1 can be known while recovery/possession is not; offensive-foul
risk -.3 does not specify adjudication. Clock/phase/legal procedures require
further modeling even in a clean row. The exact-only fallback rule is therefore
impractical here and is **not** proposed for production. No near-no-op rollout,
unknown-mass renormalization, ninth implementation or season campaign follows.

The next approved public evidence task considers a single uncertainty-aware
baseline-policy advantage certificate. It must keep actual Q-baseline bounds,
proper-process assumptions and unresolved replay/pending states explicit;
endpoint algebra alone cannot establish those football assumptions. AI-026
still requires both own-offense and opponent-defense chart response. The neutral
witness establishes neither full matchup capability nor historical fidelity.

Any eventual coaching policy must also satisfy the plan's human-playability
constraint: public information only, no selected-call/future-dice access,
probabilistic variety, unchanged Easy/Medium, call-mix/repetition review and both
human browser games. Positive finite-temperature support is a mathematical
property, not evidence of a practical human win rate or difficulty balance.

## Certified baseline-advantage diagnostic and stop decision

A single separately frozen rule addresses uncertain transitions in a public
proof. Let b be released normalized positive-support weights and [L,U] bounds
on each action's conversion probability followed by **released** future policy.
Unknown branches retain full mass with continuation [0,1]. Form midpoint m and
proposal t proportional to b exp((m-max m)/.45). Apply t only if
sum((t-b) * (L where t>=b else U)) >= 0; otherwise return exact b. Equal
midpoints retain b exactly; zero-prior calls stay zero. No coefficient/variant
search occurs. This ranks using Q-baseline, distinct from the earlier rule
whose ranking uses its own future mixture.

Ignored `remaining-down-certified-proof-r1.json` SHA
`38894081fa10ec6a06eef6b0f27bf835c75aef6b9643b5dc1e7e598fb956c468`
retains every independent interval endpoint for five small controls: material
accepted change, rejected optimistic gamble, equal values, complete uncertainty
and zero support. The accepted example retains 4/5 known success, 1/10 known
failure and 1/10 unknown mass, giving [4/5,9/10]. On the unchanged numeric
football witness, actual future candidate choices are recomputed independently;
series conversion is .839161932948482 versus released .7981686716503044. Root's
independent verifier reproduces all five controls, ten states and both sides.
Inherited generic scope wording is clarified immutably: a read-only formula was
demonstrated; no production formula was deployed. No proof bytes were rewritten.

The local certificate bounds expected Q-baseline advantage for all independent
interval endpoints. A whole-policy improvement argument additionally requires
valid bounds for the actual full state/history and a proper absorbing process
(or separate termination justification). Penalty replays, enforcement choices,
pending states, clock/phase changes and recovery cannot silently be treated as
acyclic. Endpoint arithmetic does not prove those football assumptions. Loose
bounds can force exact-baseline fallback, and fallback is not universal
individual-action opacity monotonicity. No real-chart material coverage is
established for this uncertainty-aware rule.

The final approved public control fixes the same own nine-call table and varies
only opponent defense: D1 modifies SHORT_PASS by -4; D2 modifies LONG_PASS by
-10; all other modifiers are zero. Each chart has identical effects across all
six formations/subrows, avoiding a hidden selected-formation input or a fitted
formation prior. All tables are frozen before execution. Ignored
`remaining-down-opponent-inputs-r1.json` SHA
`cddd22411b09f8df2e8f11dbc619bb0b2395a13825250c1fbea9c6abb43b3b4e`
and `remaining-down-opponent-proof-r1.json` SHA
`63fbf8b7f4fd031910b1380310396544f9ceb03b3fc21c6d021276361f2522d4`
bind 32,400 actual physical resolver cells on both physical sides.

| Fixed opponent chart | Released series value | Certified sampled series value | Initial SHORT_PASS probability |
| --- | ---: | ---: | ---: |
| D1 SHORT_PASS -4 | .7707350774 | .8227549206 | .1534423888 |
| D2 LONG_PASS -10 | .0411100468 | .1929260342 | .2960818469 |

The released initial SHORT_PASS probability is .2160409373 in both controls;
every reached state's released prior is independently checked against a
same-state neutral-defense clone. Only the opponent chart changes the actual
payoff distributions, Q-baseline values and certified vector. All local
certificates pass; the earlier optimistic-unknown control retains the required
rejection/fallback behavior. Full matrices, signed changes, vectors and RNG/
source identities remain available. Both sides match. These fixed favorable
controls prove a bounded matchup response, not universal optimality, historical
improvement, human balance or safe generic clock/enforcement handling.

**No-go for AI-026 release promotion.** All eight historical candidates remain
rejected; these later public proofs do not replace unchanged source/scoring/pace
gates or demonstrate real-chart operational exposure. No ninth production
implementation, historical season, held-out access, merge or push follows.
The cost/time limit ends this investigation here, without another variant or
design loop. The current released version remains v1.10.2.

If separately resumed, the smallest concrete next implementation is a pure,
test-first ordinary-state Q-baseline interval preview plus certificate helper
in an isolated checkout, using actual own/O and opponent/D physical transitions,
full state/history and explicit unknown branch bounds. It must first demonstrate
material chart exposure and correct phase/clock/procedure limits before selector
wiring. Default/special policies, Easy/Medium, charts and all historical gates
stay fixed; unresolved replay/properness cannot be papered over. This is deferred
work, not present authorization or a claim that it will qualify a release.
Probabilistic variety and public information remain necessary, with practical
human difficulty and both human browser games still unverified for any future
policy. AI-026's wider capabilities remain open.

Local evidence commands (completed, terminal exit zero; no seasons):

```bash
/tmp/paydirt-release-env/bin/python3 .ai-audits/release-readiness/v1.10.3/ai026-preparation/remaining_down_support_availability.py --run
/tmp/paydirt-release-env/bin/python3 .ai-audits/release-readiness/v1.10.3/ai026-preparation/remaining_down_certified_probe.py --run
/tmp/paydirt-release-env/bin/python3 .ai-audits/release-readiness/v1.10.3/ai026-preparation/remaining_down_opponent_probe.py --run
```

Each script's separately retained `--freeze` input predates its run. Scripts
refuse to overwrite existing proof files; these commands document the completed
executions, not an instruction to rerun them over preserved outputs.

## Final fixed feasibility result: stop without production

The user extended the original stop to one bounded attempt within ninety minutes,
ending 2026-11-08 23:18:53 UTC, with permission to finish early. The approved
feasibility check selects each of 60 attacking teams' alphabetically first
actual-calendar defender, independent of outcomes. It evaluates 720 ordinary
counterfactual roots: all three downs, distances three/ten, empty/repeated history,
own 40, Q1 ten minutes. Q-baseline intervals conservatively cover every one of
six formations at every continuation; no nominal forecast or selected-formation
peek. F/OFF/DEF/unsupported branches retain [0,1]. Known numeric geometry and
45-second-per-snap bounds close this specific field/clock scope; history ages
and 96-total-call eviction remain intact. No new yardage-factor mechanic is added.

Outward-rounded nonnegative probability operations enclose DP bounds. The final
advantage certificate uses exact rational normalization of actual returned raw
weights and bound endpoints, with no floating epsilon. Inputs and fixed
300-second/128-MiB limits precede execution. Ignored
`remaining-down-real-exposure-r1.json.gz` SHA
`5d023d2650b60b70daadb8598aa64a8b3b208673cea2f1aabdb3ba8be0253bf4`
retains every bound, raw/returned vector, certificate, TV, timing and team stratum.
Root independently verifies all 720 certificates/vectors/TV values exactly.

The frozen feasibility gate fails: **zero of 336 historical-cohort roots**
certify a nonidentity change, across all 28 teams/down/history strata. The modern
cohort has four of 384, on third down for only two of 32 teams; TV ranges
.116527–.125795 and certified local gain bounds .0000724–.0040629. There is no
material breadth in both cohorts. This is insufficient certification under broad
uncertainty/formation bounds, not proof that no football policy can improve.
No alternative prior, interval rule, coefficient or sample is selected.

The check completes in 21.31 seconds with 117,702,656-byte peak RSS. Mean cold
root time is .02455/.02144 seconds (1983/2024), warm .001043/.000996. A declared
48-candidate-season, 40,000-query/season, four-worker projection spans 8.14 minutes
if every query is warm to 3.05 hours if cold; actual cache hit/exposure/parallel
scaling is unmeasured, and engine/baseline/validation costs are additional. These
are feasibility bounds, not a promised campaign runtime.

**Final no-go; finish early.** The simulation-improvement goal is incomplete,
AI-026 stays open, all eight historical rejections remain and v1.10.3 is not
release-qualified. No ninth production implementation, RED stage, historical
campaign, held-out access, merge or push occurs. No future experiment is
authorized. The identified gap is uncertainty/formation bounds too broad for
material certified chart response; it is recorded without another design loop.
Public-information limits, stochastic variety, unchanged Easy/Medium and human
playability requirements remain. All evidence and failures are preserved, owned
proof/feasibility sessions are terminal and user game services are untouched.

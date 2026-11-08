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

No production sampling formula is selected here. In particular, replacing a
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
choice is dominated. No candidate sampling rule has been chosen or tested.

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

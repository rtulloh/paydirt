# AI-026 full-matchup policy comparison

Status: read-only recommendation after the seventh rejected experiment. No
production change, historical sweep, protocol or season campaign is authorized
by this note. The [release plan](release-1.10.3-plan.md) retains earlier rejections
and unchanged outcome gates. This is not implemented coaching or AI-026 completion.

## Stated objective before distinct-formation controls

Recommend the minimum-over-six lower-point correction as the next public
capability diagnostic:

`corrected(p) = released_score(p) + min_f L(match(p,f)) - L(neutral(p))`.

Both matchup and SAME-own-chart neutral-defense estimates use the original
offensive target, progress and risk utility, not the defensive experiment's
binary conversion utility. `L = U0 - 1.5q`, `H = U0 + 1.8q`, where `q` is
unresolved physical mass and `U0` assigns that mass zero. Known incomplete/black,
fumble risk and unmixed own OFF risk must be distinguished from unknown events.

This objective is selected for explicit pessimistic decision under formation
ignorance, before new controls or season outcomes. It requires no current
formation, probability forecast, fitted coefficient or observation transport.
Each call faces its own least favorable formation in the ranking; this is not
an equilibrium or a guarantee against an actual human opponent. The centered
score is neither a causal lower bound nor a bound on absolute play utility.
Finite-temperature sampling can lower true utility. No prior tournament is
proposed.

## Strategic mixture and material support

Preserve released same-state run/pass probability masses. Apply the released
GLOBAL competitive gap `.9`, temperature `.45` and history factors to corrected
scores, including newly admitted calls. Normalize within each positive-mass
family. An empty corrected family retains its released conditional mixture;
a zero-mass family remains zero. Exactly unchanged scores return the original
mapping. Per-family local admission without the global threshold is excluded.

The reviewed first eight public controls establish material new support: an
excluded Screen is admitted within a positive pass family, with original true
utility `.08` to `.94` and unchanged family masses. They also retain a genuine
finite-temperature loss: Screen0 plus defense3 versus Short4 changes utility
from `.14962102844442143` to `.14796465518226976`. The second 66-case batch covers
both sides, history, neutral B/QT cancellation, support expansion, empty/singleton/
zero families and opaque references. Effects were deliberately identical in all
six formations, so these controls do not select a formation objective.

Zero-family blindness and canceled own B/QT strengths remain limitations.
Preserving identical-state family mass does not preserve season run share,
clock, conversions or future states. Source-fit, scoring and pace gates remain.

## Uncertainty comparison and limits

| Adjustment | Finding |
| --- | --- |
| `U0(match)-U0(neutral)` | Reject for the next policy: known adverse mass replaced by opaque zero can favor the call. |
| `L(match)-L(neutral)` | Investigate as a declared pessimistic ranking difference with fixed-reference limits. |
| `L(match)-H(neutral)` | Uncoupled marginal lower bound on the effect; loses required neutral identity when the reference is opaque. Do not substitute silently. |
| Coupled event bound | Could tighten uncertainty, but requires a separate coupling model and proof. |

In the retained negative control, fumble-risk Screen replaced by unresolved DEF
raises neutral-point projected probability `.10395388609307123` to
`.41442932436692176`. Lower-point probability instead falls to
`.03852190406170308`; INT-to-opaque leaves that lower-point probability unchanged.
No opacity threshold or fitted blend is selected.

The proper uncoupled outer effect interval is
`[L(match)-H(neutral), H(match)-L(neutral)]`. An identical opaque neutral reference
has outer interval `[-3.3,+3.3]` while its centered point adjustment is zero.
This outer interval is not sharp: identical-event coupling could tighten it to
zero. Computational cancellation does not eliminate opaque mass or establish
a conservative defense-effect estimate. Centered ranking scores may exceed
the original utility range.

With the own offense/reference fixed, a single-call adverse-to-unknown
substitution cannot raise its lower estimate. Uniform averaging and the minimum
preserve this componentwise order. With every other call score, baseline family
mass and history fixed, lowering that call's score cannot increase its projected
probability. A lower global maximum only admits competitors; if its family
becomes empty, it previously held all admitted family mass and fallback is at
most that mass. Independent algebra and 21,384 controls cover this claim. It
does not cover simultaneous multiple-call opacity changes, changed own offense/
reference, or a guarantee that opaque formations are never selected.

## Formation assumption comparison

| Assumption | Basis and limitation |
| --- | --- |
| Uniform six | A declared nominal coaching average requiring public charts only. Equal probabilities are not an empirical forecast; revealed concentrations contradict representativeness, and averaging can hide a severe matchup. Retained alternative, not a second outcome-selected candidate. |
| Minimum six | The recommended pessimistic per-call objective, requiring public charts only. Can sacrifice likely-matchup utility; no calibrated probability, equilibrium or universal utility claim. |
| Earlier revealed-history Laplace | A distinct observable forecast option with earlier reported ordinary-third prequential skill and misleading-history losses. Broader-down skill is unverified. Requires post-resolution publication, physical-side/game isolation, save/load and web continuity; released offensive history has no formation. Not included in this bounded recommendation. |

Before production, use a few both-side real-resolver tables with DIFFERENT
formation effects to distinguish uniform averaging from the minimum. Freeze the
table inputs and show material new support, full six-by-nine payoff matrices,
scores, released/corrected support, repetition and family probabilities. Retain
contrary actual-formation utility losses rather than selecting the objective
by larger synthetic gain. Repeat fixed-reference opacity and empty/zero-family
controls. No current-call, preview, dice or RNG observation is allowed.

## Semantic and evidence boundary

The diagnostic risk fix had six expected failures/eight controls before
correction and fourteen passing controls afterward. Pending fumble recovery
retains known coaching risk `-1`; unmixed own OFF retains `-.3`. DEF, mixed/
offsetting and defense-chart penalties remain unresolved, including defensive
OFF text. Current fixture classification assumes constant defensive rows per
call/formation; it is not a generic compiler. The previous defensive compiler's
first-OFF shortcut must not be reused for arbitrary mixed-source penalties.

Ignored evidence in `.ai-audits/release-readiness/v1.10.3/ai026-preparation/`:

- `full-matchup-family-public-controls-r1.json`, SHA-256 `37823e0bbcd570e9afbb638022583c05ebc193861acfa4ea22c3103242a203fb`.
- `full-matchup-family-public-controls-r2.json`, SHA-256 `4acfbbabfa91bf2fcab0e8e7548c3cca8c601fdb57ba5ca6cc48f8446673a3ed`.
- Independent reviews `root-full-matchup-controls-r1-review.json`, `root-full-matchup-r2-independent-review.json` and `root-family-projection-fixed-input-opacity-review.json`.

These controls do not qualify a release or historical improvement. Wider
AI-026 capabilities remain open.

# AI-026 bounded full-matchup implementation proposal

Status: proposed eighth isolated experiment from released `10d7130`. Only
read-only diagnostics and test-first preparation are authorized at this stage;
production edits require review of this scope and actual-behavior RED evidence.
No historical sweep, season campaign, heldout execution or promotion is approved.
The [comparison](ai026-full-matchup-policy-comparison.md) fixes the objective
before distinct-formation evidence. All original outcome gates remain unchanged.

## Behavior and boundaries

For Hard ordinary offensive calls on downs 1–3, use:

`s(p) = released_score(p) + min_f L(full_matchup(p,f)) - L(same_own_neutral(p))`.

Use the original offensive target and numeric progress/negative-yard utility
for BOTH matchup and reference. Preserve touchdown `1.8`, INT `-1.5`, fumble
risk `-1`, unmixed own OFF risk `-.3`, temperature `.45`, global gap `.9`,
repetition age decay `.94`, repetition discount `.9` and floor `.30`.
Unknown mass uses the declared lower point `U0-1.5q`, with full physical mass
retained. Do not replace this with a difference bound, uniform mean, binary
conversion objective, clock/incompletion bonus or fitted blend.

Compute released raw weights first. Preserve their run/pass probability masses
exactly up to floating arithmetic, while allowing new calls from each positive
family through the original GLOBAL competitive threshold. Reapply released
history factors to newly admitted calls. Empty corrected family falls back to
its original conditional mixture; zero released family remains zero. Exact
neutral score identity returns the exact released mapping and call ordering.

All production sums, admission and returned populations iterate
`CHART_PLAY_TYPES` in its fixed order. Exploratory family-mass sums use sets and
can vary by floating summation order; their eligible/output population already
follows ordered raw weights. No divergent sampled sequence was demonstrated in
the diagnostic. Exact neutral identity retains original order; production must
keep corrected populations and sums deterministic too.

Wire the policy only at the existing final ordinary Hard weight-selection
branch, after victory, end-half FG, Hail Mary, fourth-down, hurry, clock killing,
goal-line and red-zone handling. Keep those branches, Easy/Medium, default own
scores/weights, conversion offense, ALL defensive selection and RNG ordering
unchanged. Use effective quarter exactly as the existing offensive caller does
for overtime. No new independent phase classifier is needed for this wiring.
All three ordinary downs are in scope; no source-fit-selected down cutoff.

The pure helper receives own O, physical opponent D, exact down/distance and
existing offensive-call history. It must not receive a selected/current defense
call, opponent AI object, forecast, dice or RNG state. No revealed-formation
counters, save schema or UI coaching calculation are added.

## Source model and audit identity

Implement a generic pure chart-distribution model rather than copying the
fixture-only risk classifier. Enumerate exact offensive and defensive physical
weights, actual priority branches, and lazily reachable B/QT secondary mass.
Parser-None secondary tokens (including opaque/blank/missing rows) use actual
uniform fallback B15..40 or QT-5..10; they are not unknown mass or parser errors.
Valid primary blank/missing-row semantics follow the core. Parser-RAISED invalid
secondary tokens such as `F INC` retain `ValueError`, lazily only when reached;
do not turn them into uniform fallback. Unreachable invalid tables are unread.

Penalty source is part of the model: own OFF plus no defensive penalty retains
the declared original coaching risk; own OFF plus ANY defensive-chart penalty
is mixed/unresolved; any defensive-chart OFF/DEF/PI is unresolved. Own DEF/PI
and unsupported reachable tokens retain unresolved category/mass. This is a
coaching risk model, not a full penalty-enforcement forecast. Pending fumble
recovery retains risk `-1`; known incomplete/black zero is conditional on actual
priority and resolver branch order. Preserve B-versus-QT secondary fumble
differences and the retained-fumble/incompletion branch.

Cache immutable physical distributions by complete relevant own/defense content,
including physical primary availability and both secondary tables. Bound target
estimates at 100 and invalidate on content mutation. New ordinary estimates of
the released own-score formula must also reflect current chart content; do not
reuse a stale own-score cache after mutation. Default/hurry methods are unchanged.
History is live per call,
never cached into chart estimates. Returned mappings cannot mutate cached data.
Use original down-dependent target utility, including target extremes and the
original rounding rule. Do not alter chart coefficients or generated charts.

Expose a shared pure ordinary-weight helper for the actual selector and
`tests/ai_audit.py`; the observer must record the actual full choice vector,
including family projection/history, without consulting selected defense. This
is necessary accounting adaptation, not a weakened audit assertion.

Unresolved primary procedures must not acquire new coaching behavior. The
released engine has no authoritative pending-primary handle: its actual pending
return precedes play-log append. If explicit pending exclusion requires engine
instrumentation, reuse the previously reviewed narrow transient identity handle
as a separately approved scope item, with test-first lifecycle checks. No fake
play-log entry or adapter-only approximation. Its existing pending-save
limitation remains; do not expand save/UI schemas for this experiment.

## Test-first evidence before production

Create a fresh isolated checkout at released `10d7130`. Initial tests observe
actual factory ordinary RNG choice vectors, not missing new APIs. Use only
synthetic/public-2026 fixtures. Record baseline assertion failures, passing
controls, full test hashes, source hashes and production-empty diff.

1. Both physical offensive sides, all three downs: exact actual-core matchup
   oracle, opponent-D reversal, material newly admitted positive-family call,
   global support/history/family mass and numeric coefficients. Include distinct
   formation effects and the min-versus-mean contrast.
2. Neutral O/D identity including B/QT, repeated own-call history with opposite
   side decoys, original support/order/RNG, empty-family fallback, zero-family
   limitation and singleton expansion. Retain finite-temperature and contrary
   actual-formation utility losses explicitly.
3. Full physical mass, known risk versus unknown, fixed-own-reference one-call
   opacity substitution, mixed-source/defensive OFF penalties, B/QT fallback,
   secondary fumble differences, reachable/unused invalid tokens and conditional
   known zero. No supported-mass renormalization or universal opacity claim.
4. Repeated previews and adversarial current-call/opponent-AI/dice traps: no
   game/history/chart mutation, no added engine/global RNG draw, stable actual
   choice vector; content mutations must update it. Freeze exact released
   selected-call/mode/RNG records for excluded phases, fourth down, conversions,
   Easy/Medium and overtime boundaries before production.
   Assert returned key order and compare complete actual selected-call/RNG
   sequences in synthetic subprocesses under two `PYTHONHASHSEED` values.
5. After production, exercise primary/defense/B/QT content changes, returned-map
   mutation and more than 100 contexts on one instance. Compare actual audit
   observer vector with captured selector vector after history; cover real
   CLI, web preview/replay/execution and auto paths without taking user ports.
   If a pending handle is approved, test real pending creation, both successful
   resolutions, no-op/exception retention and identity-safe clear.

Source/compiler/observer scope must pass independent review and clean tracked-only
focused regression before a runtime freeze. Any existing test fixture or
expectation change needs explicit rationale with assertions preserved. A later
protocol/campaign proposal must bind exact runtime/chart/source identity and all
original paired-source, scoring, pace, team, validity and cost gates. No candidate
is accepted from unit tests or conditional utility examples.

## Retained diagnostic limits

The independently reviewed 28-table distinct-formation batch is frozen at input
SHA-256 `60bc7119ecebeac260e7c1ff269396ad364969ed267608b9064c6a8edcc37318`;
output SHA-256 `b4bb7c4c7f1498428635a6954266ffa9b77710b30c2bb063cce3a79fb1ab8f2a`.
All six-by-nine actual-core distributions, scores, worst-formation identities,
history and family vectors are retained locally with source hashes.

Material new support changes original utility `.08` to `.74` in its worst
formation and `.94` elsewhere while retaining half run/half pass mass. The
contrary table retains the selected objective's cost: min-six utility
`.146008543768` in every formation versus released `.585383109509` in A–E and
`-.298724248384` in F. Uniform-six gives `1.212358838263` in A–E and
`-.933346022611` in F. These are deliberately synthetic conditional tradeoffs,
not a forecast, equilibrium, guaranteed mixture improvement or historical proof.
Centered lower subtraction is not a conservative causal effect bound; unknown
reference compensation, simultaneous multiple-call opacity, zero-family and
neutral own-secondary blind spots remain explicit. Broader AI-026 stays open.

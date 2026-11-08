# AI-026: exact continuation-analysis foundation

Developer diagnostic only. This is not a shipped coaching change, a historical
accuracy result, or evidence that v1.10.3 is ready to release.

## Scope of the resumed work

The owner resumed work on November 8 within the original 23:18:53 UTC deadline.
The preceding real-chart feasibility failure is unchanged: zero of 336 historical
roots and four of 384 modern roots certified a nonidentity change. Wiring that
rule into Hard would not solve the exposure problem. No selector is changed here.

The new `paydirt.series_analysis` module extracts a reusable, tested mathematical
foundation from the earlier ignored experiments. It evaluates a caller-supplied
baseline transition model and certifies a caller-supplied local proposal. It does
not supply a football adapter, formation forecast, new sampling rule, or empirical
chart calibration.

Compared with the ignored prototypes, it provides:

- Exact rational branch mass, baseline normalization, continuation intervals and
  certificate arithmetic, rather than floating-point enclosure helpers.
- Explicit validation of complete branch mass, matching action/formation sets,
  valid weights and unambiguous terminal/successor events. Unknown mass is never
  discarded or renormalized away.
- Opaque immutable state keys, allowing callers to preserve all relevant legal
  context instead of imposing a down/field-only cache. A caller that omits history,
  phase or pending procedures still supplies an invalid football model.
- Conservative `[0, 1]` bounds for unknown branches, cycles, expansion limits and
  depth limits, plus immutable result maps and reason counts. Counts are evaluated
  branch counts, not probability mass or historical coverage estimates.
- A separate exact local certificate that preserves baseline support and returns
  the baseline mixture if the worst interval advantage is negative.

`evaluate_series` uses the baseline mixture at every future state. Formation
minima/maxima permit arbitrary choices at each action and future state; this is
a conservative envelope, not an estimated opponent distribution. The bounds can
therefore be much wider than a plausible game's values. `certify_proposal` is a
local Q-baseline algebra check. It does not establish properness or whole-policy
improvement when repeatedly wiring proposals into an actual game.

## Fair information boundary

Public printed charts and earlier revealed plays are legitimate coaching inputs.
The opponent's current selected formation/call and future dice are not. A formation
displayed in a UI does not become legitimate information before the simultaneous
play-selection decision. Any future model adapter must enforce this boundary;
passing a generic transition callback does not enforce it automatically.

The released ordinary Hard offense in `computer_ai.py` queries
`OffensiveStrategy.weights(down, distance, offensive_call_history, is_home)`.
That query receives its own offense chart through the strategy instance and no
current defensive choice. The factory sets the AI's own team chart. This inspected
path does not establish a hidden-formation defect, nor is it a review of every
special coaching path or UI transport.

## Verification and limits

Test-first baseline: 19 new-API tests fail because `paydirt.series_analysis` does
not yet exist; one released-strategy control passes. This is a new diagnostic API
baseline, not reproduction of a released gameplay defect. No existing test
expectation changes.

The mathematical controls cover full mass, baseline rather than optimal future
policy, formation envelopes, distinct history/phase keys, cycles and resource
limits, malformed models, immutability, exact support preservation and rejection
of optimistic unknown proposals.

Six additional controls use synthetic charts on the public 2026 fixture. They
enumerate all nine calls and all six formations through actual resolver physical
dice mass, capture actual Hard factory weights, and apply known numeric outcomes
through authoritative engine clones on both physical sides. Neutral-defense
released series success is approximately .798168672; changing only the public
opponent SHORT modifier to -4 yields .770735077, and LONG modifier to -10 yields
.041110047. The improving local proposal reverses its preferred call when the
public LONG defense changes. These are synthetic diagnostic capabilities only.

The first oracle run exposed an adapter fixture error: compiling only initial
eligible calls omitted runs admitted in later long-yardage states. Compiling all
nine calls corrects the fixture without weakening any assertion. The test-only
numeric projection fixes RNG and restores it; it does not solve production clock,
penalty, recovery, replay or phase transitions. Original game state and global RNG
remain unchanged.

No historical seasons, held-out seeds, full release regression, selector changes,
merge, push or release are part of this foundation. A reviewed real full-state
adapter, material real-chart exposure, runtime cost and all unchanged historical
and human-playability gates remain necessary before any coaching rollout. This
module is not imported by gameplay, so player guidance requires no behavior update.

Final focused checks: **623 passed** across the new diagnostic, released offense
strategy/variety/AI, documentation and tracker suites; no skips or warnings. Ruff
passes for both new Python files, and `git diff --check` passes. A compact hashed
validation receipt remains in ignored audit storage. These checks do not replace
the required full pre-push/release regression.

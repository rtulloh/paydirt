# Retained fumble followed by incompletion: engine implementation

Implemented 2026-11-06. This is an implementation note for the narrow capability
approved in [the source-model review decisions](chart-source-model-review-decisions.md).
It does not approve a generated season or publish source material.

## Supported result and selection

The canonical primary offensive passing token is `F INC`. It belongs to the
existing plain-fumble priority family, but the selected terminal result is an
ordinary incomplete pass: zero net yards, no score or lost-fumble turnover,
one down, and existing five-second incompletion timing. Turnover on downs is
still applied independently by the game engine on fourth down.

`CombinedResult.retained_fumble_incompletion` and
`PlayResult.retained_fumble_incompletion` are explicit booleans, defaulting to
false. Only a selected retained composite sets them. The resolver never infers
the occurrence from descriptive text or an unselected raw chart cell. `F INC`
uses the existing fumble priority over defensive INT, QT, replacement-yard and
TD entries. Therefore substituting it for BLACK deliberately changes those
conditional terminal outcomes; preserving incomplete-cell mass alone does not
prove preservation of engine outcomes. The source/generator audit must report
signed event differences across formations and requalify whole-engine fit.

The internal fumble and recovery spots and movement are unknown. The composite
does not populate those fields, roll recovery/return dice, or manufacture a sack,
rush, completion, lost fumble, or known recovery at the line of scrimmage. Existing
zero-valued dice/spot fields remain their unset defaults. The explicit composite
flag is the occurrence evidence; generic `fumble_recovered`/`fumble_resolved`
fields are not set. The transaction contains its ordinary chart lookup and no
invented physical fumble/recovery event.

Only the five primary passing columns support this subtype. Running columns,
QB Sneak, defense, B/QT supplementary columns, and context-free result parsing
reject it explicitly. Hail Mary retains its independent table and never reads
the primary token. Two-point passing attempts follow the existing ordinary
incompletion path and fail without a turnover or score.

## Penalty lifetime and observer interface

Direct priority resolution preserves penalty precedence and suppresses the
composite flag when the penalty wins. The penalty-procedure resolver constructs
the actual selected reroll's decline candidate. When the defensive chart holds
a penalty, the candidate is evaluated against neutral defense while retaining
the original foul option and chart metadata.

Declining a foul retains the selected candidate's flag and ordinary incompletion
timing/down behavior. Accepting a foul or applying offsetting fouls clears the
flag on the final `PlayOutcome.result`. The original
`PlayOutcome.penalty_choice.play_result` still identifies the voided candidate
for an observer that separately records voided occurrences. Accepted fouls keep
the existing penalty enforcement/timing; offsetting fouls replay the down and
consume ten seconds. No lost-fumble, sack or yardage statistics survive either
nullification. Consumers must distinguish a pending candidate from a retained
final result and honor penalty decisions rather than count raw tokens.

Source/generator/observer integration is a separate owner task. Deterministic
retained composites must be excluded from ordinary F/QT allocation and stochastic
recovery denominators, while remaining one pass attempt with one retained-fumble
occurrence when the play stands.

## Test-first evidence and validation

All fixtures in `tests/test_retained_fumble_incompletion.py` are synthetic; the
only season dependency is public 2026 rules. Before production changes, the
initial suite reported **132 failures and nine passing legacy/Hail Mary
controls**. Failures demonstrated neutral/additive interpretation, defensive
INT/QT/TD replacement, incorrect ordinary-zero-yard-play timing, and absent typed
occurrence/penalty-lifetime behavior. The local log is
`.ai-audits/retained-fumble-baseline.txt` (ignored).

Later unsupported secondary-column and QB Sneak cases independently failed
before adding their guards. The final focused suite has **146 passing cases**:
both resolver routes; five pass columns; priority and penalty precedence; both
team sides; backed-up, midfield and goal-line states; first/fourth down; accepted,
declined and offsetting fouls; matching ordinary-incompletion state, clocks and
statistics; no extra dice; legacy F/QT/BLACK/numeric controls; and conversion and
Hail Mary isolation. Surrounding priority/resolver/penalty/fumble/clock/statistics
suites plus documentation checks passed **1,022 cases** after the final change
(`.ai-audits/retained-fumble-regression.txt`, ignored). Ruff passed for the three
modified production modules and the new test module. Full release regression
and generated-chart fit remain the parent/source owners' responsibility. No existing test
expectation was changed and no skip was added.

An initial new conversion test assumed the comment saying tries are untimed was
already enforced. Inspection and a BLACK control show that ordinary incomplete
two-point attempts currently charge five seconds. The composite preserves that
existing behavior. The new assertion was corrected to compare the ordinary
BLACK control, rather than expand this capability into a conversion-clock fix.
This existing clock discrepancy was reported to the parent for separate tracking.

An initial additional ordinary-resolver penalty control used `OFF 5` in the
defensive chart, whose legacy path does not classify that form as an offensive
penalty. It was replaced with supported defensive-chart DEF controls; direct
priority tests still prove that both OFF and DEF categories suppress the flag.
No legacy penalty classification was changed by this implementation.

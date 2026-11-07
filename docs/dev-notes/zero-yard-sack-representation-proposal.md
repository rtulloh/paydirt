# Proposed explicit zero-yard sack representation

Proposal only; no core implementation or acceptance claim. This supports the
[chart-confidence charter](chart-confidence-agent-charter.md). A known zero-yard
sack is distinct from an unknown gain, a numeric-zero scramble and a QB fumble.
Official targets stay fixed; no invented minus-one loss or fumble is acceptable.

## Confirmed source population

In 2024 regular-season nonconversion source rows, 103 credited sacks have
`yards_gained=0`: 87 without a fumble and 16 with a fumble. Ninety-three descriptions
explicitly state zero yards; ten fumble rows describe a negative sack loss while the structured gain is zero.
This disagreement does not establish that the structured value is net physical
movement or that the prose is the official credited loss. Initial loss, credited
loss and subsequent recovery movement require separate source reconciliation. These counts do not authorize
reading arbitrary return/recovery prose as the primary gain (DATA-025).

## Minimal vocabulary and typed semantics

Propose `SACK 0` only in the offense QB Time column. Optional `*` retains an
explicit source out-of-bounds flag. It means a nonfumble sack with zero initial
loss. Existing numeric `0` means scramble; existing `F` is a zero-initial-gain QB
fumble and retains real recovery rules. Negative QT values and positive scrambles
remain unchanged. Do not add a new rule to ordinary primary or Breakaway cells.

A QT-only parser would return `ColumnResult(yards=0, is_sack=True)`; both resolver
entry points select existing `ResultType.SACK`, preserve dice labels and OOB flags,
and describe a zero-yard loss. No new public result enum is needed. Core sack
statistics and the observer already recognize `ResultType.SACK` regardless of
loss. Verify actual clock, possession, down, field clipping and end-of-game paths
with synthetic engine controls rather than assuming those existing branches.

## Required path audit and failing controls before implementation

- Source classifier: credited sack plus a known initial zero, without a fumble,
  supplies the explicit token; unknown gain stays unsupported and visible.
  Net-zero fumble rows are not automatically declared zero initial loss.
- Offense loader and generator: accept only this narrow QT grammar, reject it in
  B/ordinary/special columns, retain the complete raw token/flag histogram.
  Empirical input validation, symbol family allocation and finite mass diagnostics
  must preserve its distinct class, not fold it into numeric-zero scrambles.
- Opponent adjustment: normalized token carries zero gain and sack class; constrain
  adjusted severity to nonpositive loss, rendering the explicit token at zero.
  Existing numeric-negative clamp policy remains unchanged. Record transitions.
- Pressure model: count this token as a sack in weighted conditional QT support.
  Both direct and penalty-procedure resolvers must return a zero-yard sack with
  no random fallback and legitimate primary/secondary dice labels.
- Exact audits: use the same QT-only parser and report `sack:0`; compare synthetic
  exact classes to actual core outcomes. Existing outcome maps erase OOB flags,
  so retain raw token/flag histograms as a separate invariant.
- Engine/observer: one sack, zero sack yards, no passing/rushing attempt, correct
  down/clock and possession, no manufactured fumble/recovery/turnover. Controls:
  numeric-zero scramble, F0 with own/lost recovery, negative sack, positive run,
  OOB flag, backed-up/midfield/goal-line and pending-penalty routes.
- API/CLI/chart preview: display engine descriptions and raw chart tokens; do not
  infer sack rules in UI. Check narrow-cell rendering and existing serialization.

Recovery ranges and their roll identities remain fixed. No special/supplemental
layout shuffling or Razzle-Dazzle behavior is proposed. This vocabulary change
requires maintained chart-format/validation documentation and fresh fingerprints,
full relevant regressions and source-candidate regeneration before calibration.

# Chart source and representation review decisions

Parent implementation decisions, 2026-11-06, following the bounded independent
review and the owner's direction to complete the chart-repair release work.
These authorize local test-first implementation and measurement. They do not
approve a release, relax the fixed statistical bounds, or certify unknown source
facts. Final acceptance still requires the charter evidence and owner review.

## Source evidence and modeled gain

Use separate provenance tiers for a reported primary-event gain, officially
verified statistical credit, and physical initial gain. None implies the others.
Automate official-gamebook extraction where deterministic event alignment and
the source establish the required fact. Record document/page and raw-event hashes,
and validate explicit extraction and rejection cases against the reviewed pilot.
A gamebook's `for N yards` does not by itself establish individual credit when a
lateral, recovery or loose-ball sequence intervenes. Box residuals do not become
verified credits merely because counts, totals and maximum gains reconcile.

A bounded, opt-in `source_reported_gain_proxy_v1` experiment is approved. It may
use an unambiguously associated reported primary-event number for a separately
named modeled gain, while unverified official credit and physical gain remain
null. Require explicit field-specific support for occurrence, originating class, actor/team,
recovery/loss and the scope of the reported number. Prefer supported physical
facts, then reviewed credit under the already approved credited proxy, then the
explicit source-reported proxy. Preserve and report disagreements; never use a
generic first-number/`for N` match, a return gain, QB position, or a residual as
the missing fact. Unknown class, ownership, recovery, numeric support or genuinely
contradictory evidence remains unsupported. Known source corrections must take
precedence over the proxy, rather than being hidden by it.

Before fitting, census the complete population by provenance and projection
basis, including every rejected event. Report exact quantized probability mass,
gain/tail effects, independent official-control coverage and aggregate source
reconciliation. Do not describe proxy-derived mass as verified physical or
individual credited yardage. This is an experiment in a reusable statistical
model, not approval to fit a silently partial population. The final review packet
must explicitly present the remaining source-evidence limitations for the
owner's release decision. The original strict policy remains available.
Field-specific support does not require a second source for every source-reported
fact. Different reported, credited and physical numbers are not automatically
contradictions; conflicting claims about the same fact are. Complete the source
census before calibration; obtain weighted mass/tail diagnostics from a diagnostic
generation before accepting any fitted candidate.

## Retained fumble followed by incompletion

Approve a narrow generic `F INC` primary passing-chart outcome. It represents one
play on which the offense fumbles, retains the ball, then throws an incomplete
pass. It carries no invented internal contact/recovery spot or movement. It is
not an extra play, completion, rush, sack, return or stochastic recovery attempt.

Use the existing fumble priority family, including its penalty precedence, and
carry an explicit typed retained-fumble/incompletion flag from the selected
result. Nonselected raw cells must not leak this flag. Resolve the final play as
an ordinary zero-yard incompletion, advance one down and apply the existing
incompletion clock. On fourth down, existing engine logic changes possession;
retained fumble must not suppress turnover on downs or manufacture a lost fumble.
No fresh recovery or return roll occurs. Preserve legacy F, QT, BLACK and numeric
behavior. Generation may emit this symbol only in supported primary passing
columns; it is not a fallback interpretation for unsupported source events.

Fumble priority is an explicit model choice: replacing BLACK with this subtype
suppresses defensive INT, QT and replacement-yard/TD outcomes that could otherwise
override BLACK. It does not preserve the old terminal distribution merely by
preserving incomplete-cell mass. Report exact signed changes across every
formation and repeat whole-engine fit; retain the same source targets and bounds.
Clear the generic fumble's provisional turnover and bypass recovery processing
before final incomplete handling. Keep turnover on downs separate.

Tests precede production edits and cover both resolver routes, both team sides,
backed-up/midfield/goal-line positions, ordinary/fourth down, selected priority,
accepted/declined/offsetting fouls, nullified statistics and timing. Include
passing controls for existing symbols. Retained/voided observer evidence must
count the explicit occurrence correctly. Exclude these deterministic retained
events from the denominator used to fit stochastic fumble-recovery ranges.
Retain them in the complete event ledger and ordinary pass-attempt population.
Also exclude them from ordinary primary-F and QT occurrence allocation. Preserve
the joint subtype through resampling and quantization; do not allocate it twice
or collapse it into BLACK. Accepted or offsetting fouls erase its retained-event
credit; a declined foul keeps only the actual selected reroll's occurrence.

## Compound fumbles and the shared return column

Approve lossless play/ordered-event ledger and complete consumer-inventory work.
One primary origin and each later conditional event remain distinct. Keep play
statistical credit separate from the fumbling/recovering player's identity;
aborted punt support already exists in the engine. Do not create a duplicate
primary rush or sack to account for a later event.

Shared-return fitting is not approved yet. Its inventory must include actual
interceptions, own/opponent recovery entries, blocked-kick entries and recursive
consumers, with explicit zero versus unknown gain and terminal eligibility after
fouls/state gates. Historical positive advances and raw dice opportunities are
not interchangeable denominators. The proposal must specify occurrence-risk,
gain/tail and loss-risk assumptions jointly: the shared peripheral recovery range
also affects return fumbles and is currently fit from offensive fumbles. Merely
pooling a new F frequency does not reconcile those losses or other consumers.

Return a concrete complete inventory, proposed denominator/missing-gain policy,
joint allocation and all-consumer residuals for parent review. Unsupported rows
remain identified until this model is implemented and qualified. No copied
reference cells, ad hoc team coefficients, changed official targets, relaxed
bounds or opened reserved/prospective families follow from these decisions.

## Conditional gain-normalization experiment

The independent review found no mathematical error in the proposed fixed-anchor
shrinkage objective. Statistical benefit remains unproven. After the corrected
source census is complete, generate and measure a fresh supported baseline
before deciding whether this extension is needed. If the fixed team yardage
bounds still fail after shared controls, local test-first implementation of the
bounded engine-baseline experiment is authorized subject to these requirements.
It is not approval to fit partial source populations or relax any acceptance
bound. If the corrected baseline passes, retain it without this extension.

- Use pooled authoritative credited numerators and eligible denominators across
  the sixteen training schedules for each baseline mean. Derive separate passing
  and rushing anchors over the complete frozen cohort, with source attempts as
  shrinkage support. All required inputs must be finite and supported; positive
  means/targets and valid source counts are prerequisites. Derive all team
  multipliers simultaneously from that one baseline, without omissions.
- Apply the derived multiplier as a deterministic cellwise transformation of
  the selected, allocated baseline, after existing B reconstruction and before
  the final layout pass. Do not feed it through the old shared scaling functions:
  they also scale F gains. Transform only ordinary numeric primary cells and
  numeric rushing B gains. Copy F, F INC, QT, other symbols, flags, defense,
  special teams, recovery ranges and dice-row weights unchanged. Keep zeroes
  and signs. Use nearest-integer rounding with ties to even, declare its numeric
  representation in the recipe, and retain existing legal limits: positive
  direct runs at most 18, other numeric gains within [-99, 99]. Reject an invalid
  baseline instead of silently repairing it. Report every rounding/cap effect.
- Preserve ordering within each transformed numeric set. Do not promise ordering
  across fixed F/QT gains. Protected probabilities mean exact weighted symbolic
  and priority-family mass; downstream first downs, touchdowns, clocks, field
  states and terminal outcomes may change and require fresh engine evidence.
- The 32-profile limit includes the initial shared profile and applies only to
  distinct shared-profile evaluations. One normalized candidate's final
  64-schedule training evaluation is outside that limit. The no-normalization
  branch also requires all 64 schedules. Distinguish repeated parameter profiles
  from different profiles that quantize to identical charts. Exhaustion, cycles
  and saturation mean procedure failure, not proof that a passing profile cannot
  exist. No manual restart or best-seed substitution follows.
- Require rename invariance with underlying inputs and seed assignments held
  fixed. The existing name-derived finite allocation is not secretly redefined
  by this test. Record full weighted before/after distributions, mean, zero/loss
  shares, quantiles, 20+/40+ gain shares, extrema and cap saturation, with pending
  branches identified. These are distribution diagnostics under the existing
  charter, not new official route targets or invented acceptance tolerances.
- Freeze the complete extraction/proxy, automatic profile search, normalization,
  seed assignments and stopping rules before transfer. Shared training streams
  and the nested 64-schedule training run are development evidence. Reserved
  held-out/reference/prospective families remain unopened until the existing
  freeze announcement and review prerequisites are satisfied.

Keep failing synthetic cases, unchanged-symbol controls, protected-mass mutants,
objective/bound controls and complete recipe receipts. Final source, mechanics,
all-team fit, benchmark, transfer and release regression still decide readiness.

## Shared-return inventory follow-up

The completed read-only inventory is retained locally in
`.ai-audits/release-readiness/return-exposure-01/`. It identifies every runtime
consumer, explicit source-zero versus unknown gains, nullified events, the
missing same-player second-fumble case and coupled recovery/loss assumptions.
Raw recovery slots cannot serve as shared-chart consultations. A preliminary
exposure bound shows substantial tension between the source INT-return and
other recovery-return fumble frequencies; this is a model limitation, not a new
exact-count acceptance threshold or permission to alter engine rules.

Local test-first implementation of the inventory's lossless ledger and a
**diagnostic joint projection** is approved. This supersedes only the earlier
hold on implementing an experiment, not the hold on final shared-return fit
acceptance. Use one originating play plus ordered conditional events; correct
the missing second identity, muff scope and blocked-return support explicitly.
Retain unresolved individual loss/physical movement as null. No numeric gain
projection may depend on an unsupported gain, and an unknown blocked-return
placeholder must never become a zero-yard observation.

For the smallest experiment, retain the current peripheral recovery ranges
(excluding deterministic F INC from their calibration denominator), and quantify
both their primary and return loss residuals. A single shared F/gain distribution
is an explicit exchangeability approximation across INT, own/opponent recovery,
blocked-kick and recursive entries. Do not claim exact reenactment or promise
simultaneous matching of each sparse source subset. Do not silently refit the
range from a new combined population or add a consumer-specific engine rule.

Estimate outcome-bearing terminal-segment exposures from the fixed candidate,
declared reference-policy training state distribution and actual ownership/range,
field, foul and recursion gates. Distinguish lookups, automatic TD overrides,
rerolls, retained segments and voided plays. Preserve unknown source eligibility
and do not replace this denominator with source INT/recovery/positive-return
counts. Allocate scoped F gains, other gains/tails and penalties jointly once;
do not allocate the INT-return F subset twice. Record all entry-specific signed
frequency/loss/gain/tail effects, range intersections, quantization and sampling
uncertainty. Show source/model eligibility conflicts independently.

Require independent deterministic or simulation controls of these calculations
and fresh whole-engine qualification under the existing bounds. Report complete
coverage, rejection and missing-support inventories before calibration. Failure
or an unresolved required gain remains explicit; it does not authorize a
favorable fallback. The parent will review the measured all-consumer residuals
before accepting a final shared model. No reserved family is opened by this
diagnostic authorization.

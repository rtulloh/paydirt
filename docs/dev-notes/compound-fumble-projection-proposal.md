# Minimal compound-fumble projection proposal

Status: diagnostic ledger/projection implemented locally under the parent
[source/model decisions](chart-source-model-review-decisions.md), 2026-11-06.
Final shared-return fit acceptance remains held. DATA-030, DATA-035 and DATA-036
remain open; the full source census now includes five compound rows. Preserve
raw inputs, targets, individual event IDs and null
physical gains. The [evidence note](compound-fumble-source-reconciliation.md)
binds the official books and distinguishes source facts from assumptions.

## Event ownership and credit

Use one source-play identity plus two ordered event identities. Each carries its
fumbling team/player, recovering team/player or terminal out-of-bounds disposition,
individual lost credit, credited statistical family, and independently nullable
credited/physical/movement fields. A reviewed correction binds the raw row hash,
book hash/page and corrected fields. Conflicting or missing required ownership,
order, recovery or credit blocks fitting. The row-level lost flag is never copied
to every event; no blank means retained possession.

| Source play | First event | Second event | Proposed chart exposure |
| --- | --- | --- | --- |
| `2024_08_NO_LAC:370` | Harris, LAC; retained by Scott; not lost; aborted punt rather than a designed rush | Scott, LAC; out of bounds in own end zone; not lost; official single zero-yard rushing credit belongs to Scott | One punt-snap mishap, followed conditionally by LAC recovery-return exposure; do not create two primary rushing F calls or credit Harris with Scott's rush |
| `2024_11_HOU_DAL:3780` | Rush, DAL; sack fumble retained by Guyton; not lost | Guyton, DAL; lost to Barnett, HOU; recovery/advance family rather than another sack | One DAL sack/QT origin and one conditional DAL recovery-return fumble; no second primary QT |
| `2024_13_PIT_CIN:1857` | Burrow, CIN; sack fumble lost to Wilson, PIT | Wilson, PIT; retained by Smith, PIT; not lost; return-family event | One CIN sack/QT origin and one conditional PIT recovery-return fumble |
| `2024_15_CIN_TEN:3191` | Pollard, TEN; rushing fumble lost to Battle, CIN | Battle, CIN; lost out of bounds in the opponent end zone; replay-confirmed touchback | One TEN rushing F origin and one conditional CIN recovery-return fumble; terminal touchback is separate from the initial rush credit |
| `2024_10_SF_TB:3527` | Mayfield, TB; own recovery after aborted-play fumble; not lost | Mayfield fumbles again after a reported one-yard recovery advance; Irving, TB, recovers; not lost | One primary origin and one ordered conditional event; blank second-fumbler fields must not erase the second occurrence |

These are official ownership/credit distinctions, not claims that every sequence
can be reproduced event-for-event by the current board. The shared recovery roll
and end-zone rules may not reproduce each historical individual lost credit at
its original spot. Keep that representational residual explicit; do not force a
recovery range, fictional movement or source-specific runtime override to match it.
Known physical gain has priority; otherwise the approved gain proxy can supply a
separate modeled gain only after the event's required credit/class is supported.
Do not subtract recovery yards from official credit to invent initial physical gain.

## Conditional shared-return exposure

The existing engine uses each recovering team's interception-return chart for
eligible own and opponent recovery advances, and may consult it recursively.
Actual interceptions use that same chart. A later fumble therefore contributes
one event to a conditional return population, never another independent primary
play. Keep the first-event origin denominator separate from later return-segment
opportunities and from original-offense pass/rush totals.

Before fitting any return-F probability, inventory **all** source-supported
eligible segments for each team: interception returns, own-fumble recovery advances
and opponent-fumble recovery returns, including eligible subsequent segments.
Record entry reason, sequence/depth, initial/terminal disposition, explicit zero
advance, null unknown advance, yards, event-F and individual lost credit. A
recovery without an advance is not silently an observed chart consultation.
The engine's dice-dependent 17–19/37–39 consultation rule is a model eligibility
mechanism; it is not a directly observed historical denominator. Report source
segment counts separately from expected engine chart consultations under fixed
primary mass/recovery ranges, and state the mapping assumption explicitly.

Proposed minimal model: pool supported return-F events and supported return
segments within each team onto this one shared column, retaining the actual
interception subset as a separately reconciled component. Quantize once through
the existing weighted allocator. Do not add a second F allocation to interception
returns that already carry F, and do not assign a fabricated denominator when the
full eligible-segment inventory is unknown. Pooling assumes exchangeable fumble
risk across entry reasons; it cannot preserve separate risks for interception,
own recovery and opponent recovery. That assumption requires parent acceptance.
If its support or residual effects are unacceptable, keep generation blocked;
a separate chart/engine design would be a consequential additional decision.

For every team, reconcile source plays, ordered fumble events, primary origins,
secondary return-F events, credited classes/losses and excluded/unsupported IDs.
Report every shared-column consumer's before/after F, lost, retained, gain and tail
probability, quantization error, and recursion/truncation exposure. Preserve known
INT counts, primary F/QT mass, official statistical targets and all acceptance
bounds. Report residual differences instead of interpreting an aggregate fit as
proof of missing physical facts or exact individual recovery fidelity.

## Acceptance boundary and next implementation

Parent review must explicitly accept or reject the conditional pooling assumption,
its denominator evidence and the aborted-punt/individual-credit residuals. This
proposal alone supplies no missing provenance or complete denominator. Obtain the
full inventory before accepting these rows, then write failing synthetic/public
regressions for all five compound plays' ownership patterns, null-versus-zero, individual lost
flags, hash-bound corrections, exactly one primary origin, conditional exposure,
shared-consumer spillover and missing/contradictory support. Implement only the
reviewed projection. Regenerate all 60 candidates and measure stable training
results only when actual source support passes. No reserved or prospective seed
family opens, and release remains held.

## Recorded diagnostic allocation recipe

2026-11-06 12:57 local. Recorded before evaluating the first joint profile.
For each team, use the supported distinct shared F IDs once and measured nonfoul,
outcome-bearing terminal segments per source season as the denominator. Desired
conditional F probability is their count divided by that exposure. Zero exposure
with positive count, probability above one, missing scoped gain or individual
loss, conflicting IDs, and missing ordinary INT gains block projection. The five
INT-F events belong to the eleven-event shared inventory and are removed from
the ordinary INT sample. Physical gains remain null.

Keep existing peripheral recovery ranges. Combine declared baseline penalty
mass/mix, conditional F probability, supported scoped F gains, and ordinary INT
gains under the explicit exchangeability approximation. Allocate once on existing
216-weight dice rows: descending requested symbolic-family probability, nearest
attainable mass against the unrounded request, then seeded weighted gain quantiles
within each family. Ordinary INT gains occupy remaining mass. There is no
additional INT-F allocation, loss-range refit or team-specific parameter search.

Report requested and quantized distributions and entry-specific signed
F/scoped-F gain/20+/40+ effects. Keep primary and conditional raw-range loss
expectations separate from sampled committed/final and official individual
losses. Expected final losses across hypothetical foul/recursion branches remain
an explicitly limited calculation. Whole conditional non-F gain and tail targets
stay null. Whole INT comparisons retain separate source eligibility, including
the known end-zone geometry conflict. These diagnostics create no official
targets or sparse-consumer acceptance thresholds.

The baseline measurement uses the preserved pre-repair candidate. A repaired
candidate requires fresh exposure measurements and parent review of complete
all-consumer residuals before final shared-model acceptance. No reserved seed
family is opened by this diagnostic implementation.

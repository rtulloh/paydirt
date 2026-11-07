---
id: DATA-030
title: Source credited fumble yardage and physical initial gain need separate definitions
status: open
priority: High
created-at: 2026-11-05
resolved-at:
closed-at:
tags:
  - investigation
  - source-coverage
links:
  - DATA-035
  - DATA-036
  - DATA-038
---

## Description

The 2024 nonconversion sack census has 117 differences between a loss stated in
the primary sack description and structured `yards_gained`. Description losses
sum to 8,623; structured losses sum to 8,640 and match normalized totals for all
32 teams. That aggregate identity is not independent confirmation if the targets
share the same source. Ten fumble rows have structured zero and a negative stated
loss; calling this known initial loss versus net-zero movement was premature.

The [NFL's 2025 statistician guide](https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf),
pages 30–31, distinguishes the contact/fumble spot, recovery location and advance,
and credited sack/fumble yardage. Recovery can reduce credited sack loss to zero;
an own passer recovery and advance beyond the line can change the credited play
category. This establishes a definition issue, not an event-by-event correction
or proof of identical 1983-era rules. The core board-game QT-fumble convention
currently uses initial gain for class/loss and records subsequent movement apart.

## Resolution / verification

Inventory source flags, retained/voided fouls, source-provided credit, primary
loss prose, recovery identities and movement in ignored evidence. Establish raw
column definitions and independent official target provenance. A strict typed
initial-gain extraction, if justified, must keep the separate credited facts and
unknowns. Do not subtract recovery yards mechanically or override structured
fields with arbitrary narrative. Do not change official targets or tune gains
around an unresolved definition mismatch.

Confirm whether the difference is a source bug, a supported engine correction,
or an inherent board-game/statistical abstraction. Test any new behavior first;
quantify remaining effects before calibration. Keep open; no accuracy claim or
public promotion follows from source-count and mechanics tests alone.

## Comments

--- 2026-11-05 21:40 ---
The current zero-yard nonfumble-sack representation is a separate capability fix.
It does not resolve physical initial gain, loose-ball movement or NFL credit on
fumble plays. Reserved seeds and prospective source data remain unopened.

--- 2026-11-05 22:16 ---
Independent 1983 evidence confirms that this distinction predates the modern
statistician guide. The [official Baltimore-at-New England September 4 gamebook](https://www.nflgsis.com/1983/Reg/01/14207/Gamebook.pdf),
page 12, credits the fourth-and-goal exchange fumble as a Grogan rush for zero
and three yards of fumble movement, with opponent possession. PFR play 159 instead
states a three-yard loss before its recovery annotation. The preceding 13-yard
quarterback draw is a separate snap; do not assign its play family to the fumble.
The book establishes credited rushing class/zero credit and separate movement,
not a universal rule for converting all fumble prose to physical initial gains.
The currently generated QT F-minus-three would produce a sack class in this
engine. No source fact or production override is applied for this definition
conflict. The ignored draft binds raw event and official PDF/page hashes and
preserves unknown physical initial gain. Parent review of the representation and
acceptance implications remains required before changing the contract or tuning.

--- 2026-11-05 22:37 ---
Four synthetic failures establish that QB position alone routed ordinary
zero/negative rushing fumbles to QT sacks. Explicit scramble/sack evidence is now
required; unknown run design is a declared primary-run heuristic. The integrated
suite catches and corrects three penalty-routing regressions without weakening
existing expectations, then passes 269 tests. All source counts still reconcile.
This corrects play classification, not the Grogan event's physical initial gain:
PFR minus-three remains distinct from official zero rushing credit and separate
fumble movement. No yardage override or acceptance revision is made.

--- 2026-11-06 03:19 ---
The [source-credit proposal](../../fumble-source-credit-proposal.md) now gives a
concrete review choice: preserve nullable physical facts and independent official
credit, with a separately labeled credited-yard proxy for modeled fumble gain.
It includes provenance, rejection conditions, class preservation, support/mass
reporting and training checks before calibration. This is unimplemented and
requires the stated parent review; no source fact, chart or acceptance criterion
has changed. The bounded gain proposal separately specifies the previously
missing automatic shared-profile selection and stopping rules. Reserved and
prospective families remain unopened.

--- 2026-11-06 06:56 ---
The parent-approved bounded proxy is implemented locally with test-first evidence;
428 focused source/CLI/bundle checks and Ruff pass. Separate nullable physical facts,
known credited class/yards/recovery, explicit modeled basis and unchanged source
hashes are retained. Source replay now binds the declared policy to the CLI flag.
See the [implementation checkpoint](../../fumble-source-credit-proposal.md#bounded-implementation--2026-11-06-0653-cst).
The unchanged 2024 source yields 514 supported single-event proxies, all physical
initial gains unknown, while four compound and thirteen continued-to-incomplete
sequences remain unsupported. No partial fit, new candidate, changed target/bound,
ordinary-gain normalization or acceptance follows. Real 1983 reviewed-credit
inventory and regenerated chart mass/tail evidence remain outstanding; keep open.

--- 2026-11-06 07:07 ---

The reviewed official exchange-fumble example is now applied to an ignored
schema-3 sidecar and full-game classification. The single rushing F retains
zero credited yards, physical initial gain null, separate loose-ball movement
minus three and opponent recovery. No QT sack or observed run design is inferred.
Raw HTML and PDF hashes are unchanged. The synthetic baseline has 17 expected
failures and 149 controls; all 393 focused source/replay checks and Ruff now pass.
Explicit unknown physical gain no longer conflicts with numeric secondary prose;
contradictory known physical values still fail. Optional separately reviewed
movement fields preserve absence, null and zero. Four other events in that game
remain unsupported under this one-event sidecar; no all-season support, fitting,
new chart, accuracy acceptance or ticket closure follows.


--- 2026-11-06 07:08 ---

Subsequent visual review covers all five offensive fumbles in that public game,
with full raw-event/PDF/page binding. The five-event sidecar classifies without
unsupported fumble projections. All physical initial gains remain unknown; four
rushing credits and one receiving credit produce five primary F outcomes.
The earlier recovery-only receiving initial gain of 17 was overstated: the book
establishes net receiving credit, not a separate physical fumble spot. The new
experimental record preserves null; the legacy recipe is unchanged and cannot
certify that value. A research-script assertion initially used the credited
class label receiving as the calibration unit; corrected to the existing passing
unit after inspecting actual adapter output, with the class/recovery checks kept.
No existing unit expectation changes or all-season acceptance follow.


--- 2026-11-06 07:12 ---

The reviewed pilot now covers six offensive fumbles across two games. The second
book's receiving credit reconciles to ten from the 106-yard player total minus
four separately reviewed receptions totaling 96. Catch/recovery positions do not
supply an inferred physical contact spot; the experimental record retains null
and separately known opponent return advance. Both full-game classifications
have no unsupported offensive-fumble projections under this six-event sidecar.
The pilot remains separate from unchanged full-season source recipes. Checking
the ten currently resolved tickets supplies no new issue-specific full-game
confirmation; none is closed from this source/adapter evidence.


--- 2026-11-06 07:16 ---

Pilot revision 02 applies nine reviewed credits across three games and retains
one unsupported exchange credit. The third game's own-recovery receiving event
reconciles to eight credited yards against the official 42-yard five-catch total.
Official recovery and next-snap locations establish zero recovery advance,
where secondary prose separately reports an additional eight-yard return.
Preserve that raw discrepancy and the independently reviewed zero; do not add
prose return yards to credit or infer contact spots. The unresolved exchange's
credited player/class and attempt allocation still need review. This confirms
why a universal prose-to-credit or physical-gain conversion would be unsound.


--- 2026-11-06 09:35 ---

The resumed core process completes with 9,615 passes, eight existing skips and
84% coverage. No warnings are reported; skips are six unavailable private-1972
data/rule cases and two existing team-chart data cases. The nine reviewed source
identities and saved partial log prefix revalidate after reconnecting. Production
hashes remain unchanged. The additional late synthetic passing control is covered
by the separate 741-check focused run; final stable full regression is outstanding.
This improves validation evidence without completing the all-season credit
inventory, resolving the pilot exchange event or authorizing accuracy acceptance.


--- 2026-11-06 09:42 ---

The pilot exchange now has a reviewed zero-yard rushing credit: the official
four-attempt/19-yard quarterback total less three narrated runs of eight, five
and six leaves one attempt for zero. Final and halftime rows and all retained
quarterback snaps were visually reviewed. The center remains the fumbler/own
recoverer; player attribution is distinct from the quarterback's statistical
credit. Physical gain and the loose-ball/recovery-advance split remain unknown;
combined one-yard fumble movement stays separate in review metadata. Revision 03
applies ten reviewed credits across three games with zero unsupported fumble
projections and zero source conflicts. No full-season inventory, new candidate,
full final regression or accuracy acceptance follows. Resolved-ticket review
provides no new issue-specific full-game confirmation; no ticket is closed.


--- 2026-11-06 10:05 ---

Pilot revision 04 now classifies twelve officially reviewed offensive fumbles
across four games with zero unsupported projections or source conflicts. The new
book establishes receiving credit fifteen and quarterback rushing credit zero;
separate minus-six combined fumble movement remains review metadata with unknown
split and unknown physical initial gain. The 224-game same-source census offers
498 potential residuals and leaves 225 unresolved; all eight computable pilot
residuals agree. Thirty-three potential residuals differ from numeric prose or
fill missing numeric prose. Matching counts and same-source arithmetic are not
independent official evidence. The first census's sack-sign error is retained and
superseded by revision 02. Owner clarification of the evidence standard remains
pending; no residual enters source facts, recipes or fitting.

Thirteen modern retained fumbles followed by incompletions expose a separate
boundary: two official books confirm the class; eleven remain source-only.
Forty-eight synthetic 2026 real-engine controls show the four ordinary mappings
cannot preserve an incomplete pass attempt together with its retained fumble.
Current passing F0 credits a completion, QT F0 a sack, BLACK no fumble, and rushing
F0 a rush. This does not prove an engine extension impossible. A continuation
representation needs separate review; protected events cannot be dropped to fit.
Two failed research checks used blanket fourth-down flag assumptions; corrected
controls independently verify engine possession and retain result-class checks.
No production code or existing unit expectation changed. The full-season recipe,
weighted chart mass and final acceptance remain incomplete. Resolved-ticket
inspection finds no new issue-specific full-game evidence; no closure follows.


--- 2026-11-06 10:13 ---

An official negative control disproves count/total residual sufficiency. The
receiver's two catches total sixteen; his first credits five, then a teammate's
lateral adds one, and his later fumble reception credits eleven. Secondary prose
describes the earlier whole play as a six-yard reception without the lateral.
Subtracting that prose from individual receiving totals yields a wrong ten-yard
credit despite matching counts. Whole-play passing gain and individual receiving
credit differ. Final/halftime rows and both snaps were visually reviewed.

Pilot revision 05 applies eighteen reviewed credits across five games with zero
source conflicts; two carries remain unsupported because their shared total
cannot allocate them and official final/halftime longest-gain fields disagree.
Among twelve computable original residuals, eleven match and this one fails.
A necessary longest-gain check flags six of 498 potentials; 404 agree and 88 sacks
have no analogous maximum. A synthetic hidden-credit error passes count, total
and maximum identities, so their agreement remains insufficient evidence.
Reports retain every original artifact and no residual enters source facts or
fitting. The evidence-standard question is still pending. Reviewed resolved
tickets have no new qualifying full-game evidence; no closure follows.


--- 2026-11-06 10:52 ---

Parent-approved reported-gain modeling now retains distinct nullable reported,
credited and physical facts. The complete 224-game census supports 475/723
events (457 explicit reported proxies, 18 reviewed credits), with all 248 rejects
preserved. No residual becomes verified credit. A parallel official-book
extractor is qualifying the missing action/alignment support against the pilot
and the lateral-credit negative control.

The modern source supports 513 ordinary credited proxies and 13 retained
incompletions through the typed F INC path, leaving exactly five compound
rejections. This corrects the older four-row screen, rather than omitting the
new same-player compound event. Source/generator and observer regressions pass
at intermediate checkpoints; broad combined validation is running. No complete
candidate or fit is claimed. Source coverage and model residuals keep this issue
open; no resolved ticket gains new qualifying full-game evidence from these
component checks.


--- 2026-11-06 11:12 ---

The 923-test F INC regression passes. The ordered modern source ledger and local
diagnostic projection additionally pass 481 focused source/documentation tests
and Ruff. All five compound plays now have hash-bound ordered identity and
individual-loss reviews; Bailey's blocked-return fumble is separately scoped.
The eleven diagnostic events divide into five primary origins and six shared
return fumbles. This is neither a fitted shared chart nor a source-complete
candidate; actual consumer exposures and residual review remain required.

The historical helper accounted for all 248 rejects but accepted no correction.
It found three scoped gain/class candidates; remaining limitations include
alignment, full-page text and book identity. First-page OCR is expanding the
strict identity catalog. Keep all rejects and the release hold; no partial fit
or resolved-ticket closure is supported by these component checks.


--- 2026-11-06 11:32 ---

The complete 224-game census now projects 490/723 events: 465 reported proxies,
24 reviewed credits and one retained incompletion. All 233 rejects remain.
Five new credits come from visually reviewed explicit gamebook annotations;
physical gain remains null. Reviewed recovery metadata clears eight previously
unsupported reported projections. The bound sack and incompletion corrections
are also included. Four unrelated field-goal description conflicts are preserved
and exactly match the previous 18-fact baseline.

The expanded exact book-identity catalog covers 98 candidate games and 102 of
the original 248 rejects. It does not accept source facts automatically. OCR's
negative reading of Krieg's one-yard rush was rejected after visual review.
Eason's later recovery advance remains unsupported as a primary credit.
Combined component regression passed 961 tests. Source completion, candidate fit
and required full-game confirmation remain outstanding; keep this issue open.


--- 2026-11-06 13:08 ---
Recovery census revision 07 contains 727 historical origins: 506 projected,
221 unsupported and zero unexplained source conflicts. Additional reviewed class
and explicit-credit facts remain distinct from nullable physical movement.
Strict actor-bound touchdown clauses now preserve their reported primary number.
A source parser ordering defect erased starter teams when the starter table
preceded the PBP headers; six capability failures and 78 controls preceded its
fix. Explicit home/visitor table identity now survives ordering, with conflicts
rejected. Two independently reviewed standalone kickoff-return rows use a
separate special-return projection rather than a primary rush or sack; six
capability failures and 84 controls preceded that extension. The combined PFR
source run now passes 355 checks. No source-population acceptance, fitted
candidate or release claim follows; complete source/model work remains open.

--- 2026-11-06 13:35 ---
Complete historical census revision 09 projects 528 of 727 originating rows, with
199 unsupported and zero classifier count conflicts. Reviewed actor/class
disagreements remain held separately. Schema 5 binds a reviewed
reported primary number when malformed secondary prose cannot associate it;
credit/physical fields remain null. Four expected capability failures and
30 controls precede implementation; three additional scope guards fail before
correction. The integrated source/documentation/tracker run passes 727 checks.
Two known-class sacks now retain independently scoped reported losses; two more
explicit run/handoff classes project under the unchanged proxy.

Visual review of a bounded 20 previously unsupported rows yields only two class
acceptances; 18 stay held. Several official pages reveal source actor/class errors
or aborted exchanges whose primary credit remains unknown, and one cached book
omits the required first-half narrative. Further OCR alone cannot turn these
into supported class/physical facts. No current-guide rule is applied
retroactively to fill 1983 credit. Ordered-occurrence gaps, four aborted-FG model
limitations and source correction work still block historical fitting. No ticket
closure or chart readiness follows from these unit/source checks.

--- 2026-11-06 21:48 ---
The current historical census is 547 projections of 727 originating records,
180 held and zero census-level conflicts; the separate Morgan conditional
occurrence remains held outside that originating-record census. A new read-only
inventory rehashes 127 raw games and checks every held event without importing
facts or generating charts. The 173 parser messages mentioning rushing are a
generic rejection bucket, not 173 independently established rushes: 153 contain
a bare actor/gain/same-fumbler clause, eight contain an incomplete-pass prefix,
ten malformed/reordered sack prefixes, one a reordered reception and one a bare
fumble prefix. Four aborted-FG model holds and three association holds complete
the 180. The syntax inventory does not establish missing class, chronological
ordering, primary credit or physical gain. Previously reviewed lateral/exchange
conflicts remain held; do not turn the incomplete-pass subgroup into F INC from
its raw wording alone. Receipt c8e28a026b53a793f78f1b5fa748ebe086354fff661b6e0bab6bc9733e376b4d
is retained in ignored release evidence. No source/fit acceptance or ticket
closure follows.

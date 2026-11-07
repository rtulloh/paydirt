# Proposed separation of source credit and modeled fumble gain

For parent review under [DATA-030](issues/DATA/DATA-030.md) and the
[chart-confidence charter](chart-confidence-agent-charter.md). **Bounded proxy
implementation is local and experimental; all-team regeneration and accuracy
acceptance remain incomplete.** This note preserves the original proposal and
records the subsequent parent decision and implementation evidence below.

## Established facts and the unresolved choice

The 2024 input has 117 sack rows where primary loss prose differs from structured
credited yardage, including ten fumble rows with zero structured credit. Their
aggregate identity with targets from the same source is not independent proof
of each event. The statistician guide distinguishes physical spots, loose-ball
movement and credited statistics. The independently reviewed 1983 official
gamebook example credits a rush for zero and separate fumble movement, while its
secondary-source prose reports a three-yard loss. The physical initial gain is
unknown. Neither that example nor a modern guide establishes a universal formula
for reconstructing contact spots from credited yards.

The proposed decision is to retain these separate facts and explicitly permit a
credited-yard proxy for *modeled* initial fumble gain when physical initial gain
is unknown. This is an approximation for a statistical board-game component.
It does not establish that contact occurred at that yard line. The alternative
is to reject generation of those supported-event populations until additional
physical evidence exists; that leaves the current all-team candidate incomplete.

## Lossless source facts

A versioned normalized fumble record carries independently nullable fields:

```json
{
  "schema_version": 1,
  "source_event_id": "synthetic-event",
  "credited_kind": "rushing",
  "credited_yards": 0,
  "physical_initial_yards": null,
  "loose_ball_yards": -3,
  "recovery_advance_yards": null,
  "lost": true,
  "gain_evidence": "official_credit_only"
}
```

This example is synthetic. Missing values remain null; zero and known retained
possession are explicit facts. Preserve the original source columns and hashes
in ignored provenance. A reviewed official-credit correction must bind the raw
event hash, official document hash/page and the exact credited fields. It may
correct credited kind/yards or movement only when supported; it cannot fill a
physical initial gain or play family that the evidence does not establish.
Contradictory reviewed facts, unknown recovery, missing required credit or
incompatible class/sign combinations fail before chart fitting. No team/year
fitting overrides or edited official targets are permitted.

## Proposed model projection

Use known physical initial yards when supported. Otherwise retain
`physical_initial_yards: null` and, only under an explicitly selected versioned
`credited_fumble_proxy_v1` policy, set a separate `modeled_initial_yards` from
known credited yards. Record `modeled_gain_basis: credited_proxy` on every such
projection. Do not overwrite the source fact or describe this as physical-gain
extraction. Unknown credited yards cannot use the policy.

Keep known credited rushing/sack class separate from QB position and inferred
route/run family. A known rushing exchange fumble remains a primary rushing
fumble even when its modeled gain is zero or negative. A known sack fumble
retains the existing QT sack convention and must have nonpositive modeled
initial gain. Unknown design stays an explicitly inferred primary-run family;
no adjacent play supplies its design. Unsupported mappings fail explicitly.

The engine continues to resolve the chart's physical movement and recovery
under its existing rules. It does not receive event-specific official-credit
overrides, and an engine play is not a reenactment of its source event. Model
credit after recovery can differ from the source proxy. Final source-supported
aggregate targets, mechanics and fixed team/league bounds remain unchanged.
A successful fit cannot verify the unknown contact spots.

## Required evidence before calibration resumes

1. Inventory every affected event and source definition; report source population,
   known/unknown physical gains, credited classes, missing recovery and correction
   provenance. Reconcile credited counts/yards with reviewed source facts, never
   with substituted prose or a changed target. State which checks share a source.
2. Write failing synthetic/public tests for unknown versus zero, preserved nulls,
   reviewed-credit hash mismatch, incorrect QB-position inference, rejected missing
   support and the two projection bases. Verify known physical facts take priority
   and renaming a team does not alter the result.
3. Regenerate all 60 candidates from public inputs. Report changed cells and exact
   weighted proxy mass by primary/QT class, physical-versus-modeled support,
   credited-target differences, gain/tail changes and all protected event counts.
   Preserve attribution and byte reproduction. Do not call proxy mass verified
   historical physical gain or use an invented sensitivity range as evidence.
4. Quantify the resulting full-engine credited totals and remaining mismatch on
   training data before the proposed ordinary-gain normalization is considered.
   The gain extension leaves primary F/QT fixed. No calibration around an
   unresolved credited-definition discrepancy, extra per-team correction, widened
   tolerance or automatic acceptance of missing physical support is authorized.
5. Parent review must decide whether the explicitly modeled physical uncertainty
   is acceptable under the charter's supported/unsupported-claim distinction.
   If physical initial-gain truth is required for these events, retain failure and
   the release hold. Neither choice opens reserved seeds or prospective 2023.

The proposed implementation is limited to source facts, provenance, an explicit
projection policy and coverage diagnostics. The parent must review this choice
before production changes. It does not resolve every source event merely by
introducing fields, and it does not claim a passing empirical candidate.

## Additional source ownership findings (2026-11-06)

Read-only 2024 review identifies five interception-return fumbles incorrectly
attributed to original-offense passing calibration. DATA-035's narrow ownership
correction excludes those entries without changing their INT/return chart
representations. Separately, four non-interception rows contain multiple fumbles:
two have two original-offense fumblers and two include a later return-team fumble.
A global lost flag and one initial play class do not provide separate credited
classes/recoveries for every event. DATA-036 now rejects that unsupported
projection before fitting. Its four source events remain unresolved.

Approval of the proposed gain proxy alone would not certify those compound rows
or permit duplicating primary F mass. The required event inventory and provenance
must preserve every fumble separately and identify any unsupported credit or
sequence projection before calibration. The current 2024 preparation therefore
fails on four explicit source-support gaps; the earlier all-team consistency
passes do not supersede this new evidence. No aggregate target is changed.

The [compound-event evidence note](compound-fumble-source-reconciliation.md)
records the four official ownership sequences and the separate model requirements.
It confirms that the global lost flag can disagree with the first fumbler's
individual credit. Neither that evidence nor approval of the credited-yard proxy
provides the missing compound projection. Official books are primary records,
not proof of independent upstream data origins.

## Parent decision — 2026-11-06 06:13 CST

The parent approved a bounded, test-first `credited_fumble_proxy_v1` experiment.
Known credited gain/class and recovery remain required; unknown physical initial
gain stays null, with a separate modeled gain and basis. Known physical evidence
wins. Raw source hashes, official targets and fixed bounds remain unchanged.
Record affected probability mass and gain/tail effects. This is a statistical
board-game approximation, not established physical truth, final accuracy acceptance
or a waiver for unsupported source events. No production proxy implementation
has been made at this checkpoint. Ordinary-gain normalization and the automatic
training recipe remain unapproved; any later gain adjustment must preserve primary
F/QT mass. The four compound rows need their own reviewed projection; see the
[minimal compound projection proposal](compound-fumble-projection-proposal.md).

## Bounded implementation — 2026-11-06 06:53 CST

The common fact/projection types retain nullable physical/loose-ball/advance
fields, raw-event identity/hash, explicit credited class/yards and recovery.
The adapters and both generator CLIs implement opt-in policies. Known physical
gain wins; the proxy leaves unknown physical gain null. A known rushing fumble
uses a primary rushing family even with zero/negative gain or QB metadata; a sack
retains one primary QT and one supplemental F. Unsupported class, credit,
recovery, ownership and compound sequences stop fitting. No engine rule, source
aggregate target, fixed bound, candidate CSV or calibration profile changes.

PFR schema 3 adds reviewed credited class/yards to the existing event sidecar;
its official document/page and raw-play hashes remain required. The initial
checkpoint had no real schema-3 sidecar; the subsequent single-event application
below preserves that earlier limitation and records the new evidence. Structured
nflverse records bind all parsed original fields with a canonical hash; this is
not independent official confirmation or a raw CSV-byte hash. The full source-file
hash is bound separately. Both manifests retain the selected policy, and
source-bundle replay requires the matching flag before it invokes a generator.

Test-first evidence in ignored `.ai-audits/chart-confidence/`:
initial projection baseline 50 expected failures and two controls; 255 existing
source controls passed separately. Six follow-up failures catch recovery/identity,
class/unit and missing-recovery census errors. Four CLI failures establish actual
policy wiring and pre-fitting rejection. The bundle baseline has six expected
policy/replay failures and 108 controls. After correction, 428 focused tests pass
(`fumble-proxy-after-05.log`); no existing expectation is weakened or skipped.
These are component checks, not the final regression or a public-snapshot result.

The ignored `fumble-proxy-source-01/report.json` inventories the unchanged 2024
source: 47,274 rows, 272 regular-season games and 514 unique supported single
fumble projections. All 514 use credited proxies and retain physical gain null:
155 sacks (mean -7.716, range -22 to 0), 238 rushes (mean 2.345, range -10 to 50),
and 121 receptions (mean 8.868, range -10 to 48). Three rushing and sixteen
receiving proxies are at least 20 yards. These are observed source-event counts
and tails, **not quantized chart dice masses or whole-engine credited yields**.

Seventeen source rows remain unsupported: the four compound sequences and thirteen
retained fumbles followed by incomplete passes. The latter have no supported
credited sack/rushing/receiving class; a zero net pass gain does not establish
an initial F gain or permit replacing the eventual incompletion. Their raw prose
and flags are retained locally for review. No partial-population fit is attempted.
The real 1983 event-credit inventory, full-source projection support, regenerated
60-team weighted mass/tail comparison, byte reproduction and subsequent training
checks remain outstanding. Ordinary-gain normalization and compound projection
remain unapproved; reserved seeds and prospective 2023 are unopened.

Both actual generator commands were then exercised from the unchanged bound public
source bundles with the explicit proxy flag. Both exit one before fitting and emit
no generation manifest (`fumble-proxy-source-01/generator-guards.json`). The 1983
224-game classification has one supported reviewed sack projection, 721 missing
credited-class projections and one final unknown recovery; the existing schema-2
sidecar is not an all-event official-credit inventory. The 2024 command retains
exactly the seventeen unsupported rows described above and its partial projection
ledger. Source-bundle bytes remain unchanged. Broader source/ownership/gate checks
pass 592 (`fumble-proxy-after-06.log`); documentation/tracker/component checks pass
529 (`fumble-proxy-docs-01.log`), with Ruff passing. Full final regression and a
fresh clean public snapshot remain outstanding.

The local component binding is `fumble-proxy-component-01.json`; the parent's
combined milestone receipt is `parent-handoff-2026-11-06-proxy-risk-01.json`.
The subsequent all-60 [formation diagnostic](formation-risk-census.md) has its own
scope and does not resolve these source gaps. Developer generation documentation
is updated; player/offline guide navigation is unaffected because gameplay and
player controls do not change.


## Reviewed first-game application — 2026-11-06 07:08 CST

The first actual schema-3 sidecar applies the independently reviewed exchange
fumble without changing its raw source or official PDF. A synthetic regression
exposes an incorrect loader rejection: explicitly reviewed unknown physical gain
was treated as a conflicting numeric claim when secondary prose included yards.
The correction permits unknown, while keeping rejection of contradictory known
physical values. Schema 3 also retains optional separately reviewed
`loose_ball_yards` and `recovery_advance_yards`; absence, null and zero remain
distinct in the sidecar. Movement is signed in the original offense's direction,
so an opponent return has negative advance. Movement never changes the modeled
initial gain.

The unchanged implementation baseline has 17 expected failures and 149 passing
controls (`fumble-proxy-movement-before-01.log`). After correction all 393 focused
projection, source, CLI and portable-bundle checks pass, along with Ruff. No
existing test expectation changes. The one-event report retains a rushing F
with credited zero, physical initial null and separate loose-ball minus three;
the other four offensive fumbles remain unsupported under that one-event input.

Visual review of the same official book's pages 8, 9, 12 and 13 then establishes
all five offensive-fumble credits: four rushing events and one reception.
The ignored `gsis-1983-reconciliation/reviewed-week01-14207-v3.json` and
`reviewed-week01-14207-applied-01.json` bind those rows and document the applied
full-game classification. The separate kickoff-return fumble stays outside the
offensive-fumble projection. All five use explicitly labeled credited proxies
with physical initial gain unknown; known recovery advances and loose-ball
movement remain separate facts.

This review corrects an earlier evidentiary overstatement: the recovery-only
draft/sidecar's receiving initial gain of 17 treated net receiving credit as a
physical spot. The gamebook establishes receiving credit and an out-of-bounds
fumble, but does not independently establish the physical initial gain. The new
experimental sidecar preserves null. Existing legacy source recipes and prior
reports remain unchanged and cannot certify that physical value.

These are five reviewed events in one game, not an all-season inventory,
regenerated weighted chart mass, full final regression or accuracy acceptance.
No fitting, new candidate, target/bound change or release follows. The current
all-season generator guard results above remain the last complete source census.


The subsequent two-game pilot applies six reviewed offensive fumbles with no
unsupported fumble projections in either game's classification
(`gsis-1983-reconciliation/reviewed-credit-pilot-applied-01.json`). The second
book's receiving credit is derived from its official 106-yard player total less
four separately reviewed nonfumble receptions totaling 96; this confirms ten
credited yards without claiming a physical contact spot or inferring loose-ball
movement from catch/recovery locations. Known opponent return advance remains
separate. Offsetting postplay unnecessary roughness retains the turnover in the
official narrative. Two special-teams return fumbles remain outside this
offensive projection. This pilot does not replace the full-season source recipe.


Pilot revision 02 extends the applied ledger to nine reviewed offensive credits
across three games, retaining one unsupported exchange event in the third game
(`reviewed-credit-pilot-applied-02.json`). Its own-recovery reception reconciles
to eight credited yards against all five official catches totaling 42. The
official recovery and next snap are at the reception endpoint, establishing zero
recovery advance; secondary prose's additional eight-yard return is retained raw
and is not added to the modeled gain. The exchange's credited player/class and
attempt allocation remain unreviewed, so no projection is invented. No full-season
source census or generator recipe is replaced by these pilot classifications.


Pilot revision 03 resolves that exchange after visual review of the final and
halftime rushing rows and every retained quarterback run. Four official rushing
attempts total 19 yards; the three narrated runs total 19, leaving one zero-yard
rushing credit. The credited quarterback and fumbling/recovering center are
distinct source attributions. Physical initial gain remains null. The official
separate one-yard fumble movement is retained in review metadata, with its
loose-ball/recovery-advance split unknown. All ten reviewed events across three
games now classify without unsupported fumble projections or source conflicts
(`reviewed-credit-pilot-applied-03.json`). This is a bounded pilot, not a new
full-season recipe, weighted chart-mass measurement or accuracy acceptance.


## 2026-11-06 reviewed-source and continuation checkpoint

Pilot revision 04 applies twelve reviewed offensive fumbles across four games,
with zero unsupported fumble projections and zero source conflicts
(`gsis-1983-reconciliation/reviewed-credit-pilot-applied-04.json`). The fourth
official book supports a fifteen-yard receiving credit from three receptions
totaling 46, less the two other reviewed gains of 25 and six. A separate
quarterback fumble has one official rushing attempt for zero yards and separately
recorded minus-six fumble movement. That movement does not establish its split
between loose-ball movement and recovery advance. Both components and physical
initial gain remain null. Raw secondary prose remains unchanged.

A same-source feasibility census covers 224 games and 723 classified fumble
ledger entries. It finds 498 potential unique per-player box residuals (281
rushing, 129 receiving, 88 sacks), leaving 225 unresolved: 152 multiple-event
allocations, 52 attempt-count mismatches, nine missing player boxes and twelve
unclear origins. Thirty-three potential residuals differ from numeric prose or
fill missing numeric prose. All eight computable residuals among the twelve
officially reviewed pilot events agree; the other four remain unresolved by this
method. This is a feasibility result, not independent verification or approved
source-derived credit. Ordinary nonfumble gains still come from the same source;
matching counts cannot exclude offsetting errors. The first research census
incorrectly signed ordinary sack losses and is explicitly superseded by revision
02. No sidecar, full-season recipe or chart fit uses these residuals. The source
evidence standard remains pending owner clarification.

A separate 2024 census identifies thirteen retained fumbles followed by incomplete
passes: ten self-recoveries and three recoveries by another offensive player.
All thirteen structured source rows record one pass attempt, one incompletion,
no completion/sack/rush, zero final yards and one nonlost fumble. Two official
gamebooks independently confirm this continued-play class; eleven remain
source-only. The reviewed books include both self-recovery and a center's fumble
recovered by the quarterback. Keep player attribution separate. A raw-versus-book
snap-position difference in one reviewed sequence is retained as a conflict;
neither narrative's initial number is promoted to physical gain.

Forty-eight synthetic 2026 controls exercise four current representations through
the real engine, both team sides, own two/own forty/opponent five and first/fourth
down (`retained-fumble-continuation-01/engine-controls-03.json`):

| Representation | Engine statistical class | Fumble retained |
| --- | --- | --- |
| Ordinary passing F0 | One pass attempt and completion | Yes |
| QT F0 | One sack | Yes |
| BLACK | One pass attempt and incompletion | No |
| Rushing F0 | One rushing attempt | Yes |

None of these four mappings preserves the source combination of one incomplete
pass attempt and a retained fumble. This establishes a bounded representation
gap, not impossibility of extending the engine. Any proposed continuation model
must preserve the single play/down and protected event without inventing a sack,
rush or completion, or discarding the fumble. It requires separate review before
implementation or fitting. The approved credited-gain proxy remains unchanged.

The first two research control versions made incorrect blanket assumptions about
fourth-down turnover flags. Their failed logs are retained. Revision 03 verifies
engine-owned possession separately and asserts each path's current flag while
retaining all result-class checks. No production behavior or existing unit-test
expectation changed. These controls do not replace full games, weighted event
mass, rare-event exposure, all-season reconciliation or final regression.


## 2026-11-06 10:13 CST — residual counterexample and expanded pilot

The next official book provides a counterexample to the count/total residual
method. Its receiver has two receptions for sixteen yards. The earlier play
credits him five, then a lateral credits a teammate one; the later fumble
reception credits eleven. Secondary prose collapses the earlier play into a
six-yard reception, omitting the lateral attribution. Subtracting six from the
individual box produces a false ten-yard fumble credit despite exact attempt
counts. Six remains the whole passing play's gain; it is not the first receiver's
individual credit. The final and halftime rows plus both snaps were visually
reviewed. Raw prose and all official targets remain unchanged.

Revision 05 applies six additional reviewed credits, bringing the pilot to
eighteen across five games. Two carries in the fifth game remain unsupported:
their shared total cannot allocate both credits, and the official final and
halftime longest-gain fields disagree. Do not resolve that discrepancy by choosing
the convenient row. The six new projections retain physical gain and movement
components null; a separate minus-one snap-fumble movement is review metadata.
The fifth game's retained incomplete source support prevents fitting.

The original residual census now has twelve computable official pilot controls:
eleven agree and the lateral counterexample fails. The earlier eight-of-eight
result remains a historical bounded checkpoint, not evidence that all 498
potential residuals are correct. A supplemental necessary longest-gain identity
rejects six of those 498, including the confirmed counterexample; 404 agree with
that identity, and 88 sacks have no analogous individual maximum. Agreement does
not independently establish event credit. A synthetic control deliberately
changes a smaller ordinary credit and the residual while preserving attempt
count, total and longest gain; it still passes all three identities.

Ignored evidence is `reviewed-credit-pilot-applied-05.json` and
`box-credit-maxima-01.json` in `gsis-1983-reconciliation/`. These are research
controls, not an approved source derivation rule. No residual is promoted and no
production behavior, existing unit expectation, full-season recipe or candidate
changes. The outstanding evidence-standard question remains unanswered; this
counterexample must inform any subsequent decision.

## 2026-11-06 10:41 CST — typed reported-gain implementation

The parent [source/model decision](chart-source-model-review-decisions.md)
authorizes the explicit `source_reported_gain_proxy_v1` experiment. New optional
reported class, number, actor, team and scope fields remain distinct from nullable
credited and physical facts. Supported physical facts win, then reviewed credit,
then an actor-bound reported primary-clause gain. Existing strict policies remain
available. Disagreement is retained; no box residual becomes an event credit.

The PFR grammar requires the complete named run/direction, reception or sack
clause and the same originating fumbler. It rejects bare exchanges, reordered
recovery prose, lateral/compound sequences, return-only numbers and missing
recovery support. An existing unique team-loss constraint may support recovery,
with its receipt retained; it supplies no class or gain. The unchanged baseline
has 36 expected missing-policy/field failures and 84 controls. The implementation
passes all 120 focused cases plus Ruff. No existing assertion changes.

The complete 224-game census has 723 ledger events: 457 reported proxies and
18 reviewed-credit proxies, with all 248 rejects retained. Of those rejects,
222 lack a complete explicit run/action clause; remaining failures concern actor,
number or recovery support. Some legacy descriptions reorder recovery information
inside the sack clause. These are not a partial training population. The ignored
`gsis-1983-reconciliation/reported-gain-census-01.json` binds all inputs and
implementation hashes. No candidate is generated or fit.

Next source work uses cached official books and a deterministic extractor:
bind book/game/date first, segment each retained fumble with its quarter/down/
distance/line/actor, require a unique PFR-event alignment, and parse explicit
primary action/gain separately from recovery/return/lateral movement. A primary
book's reported number remains reported evidence unless it explicitly establishes
individual credit. OCR and ambiguous alignment fail closed. Synthetic cases and
the reviewed pilot qualify each supported grammar before batch application.
No hundreds-row manual sidecar or residual fallback is planned.

---
id: DATA-036
title: Multiple fumbles on one source play collapse into one calibration event
status: open
priority: Medium
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - source-coverage
links:
  - DATA-030
  - DATA-035
  - DATA-038
---

## Current audit — 2026-11-08

Lowered High to Medium. This remains a real compound-event projection limitation: the corrected modern screen has five compound plays, not the original four, and a historical omitted secondary occurrence is documented. Ordered event ledgers preserve ownership; unsupported generation paths are guarded instead of silently duplicating a primary event. Complete shared-return exposure/residual qualification and production projection remain unfinished. The bounded known source cases warrant follow-up, but do not establish a broad current gameplay failure; small counts do not prove zero outcome impact. No existing generation guard or acceptance criterion is waived.

The original investigation and checkpoints below are retained as history.

## Description

Four non-interception 2024 scrimmage rows explicitly contain two fumbles. The
adapter records one offensive event using the row's global lost flag, without
representing separate ownership, recovery and credited play classes. Two rows
have two original-offense fumblers; two have an offensive fumble followed by a
return-team fumble. A one-row count is not an event-level reconciliation. Merely
adding two copies of the original passing/rushing event would invent the second
fumble's credited class and can misassign its recovery.

## Resolution / verification

Preserve the raw public facts and reject unsupported compound calibration before
fitting. Separately reconcile event-level ownership, credit, recovery and source
provenance under DATA-030; define the source-to-board-game projection explicitly.
Do not duplicate primary F mass or change official targets to hide multiplicity.
Regenerate and measure affected candidates only after that support is implemented.
Keep the issue open while generation correctly refuses these unresolved rows.

## Comments

--- 2026-11-06 03:46 ---
The synthetic baseline has ten expected failures and seventeen passing controls,
including all fourteen corrected DATA-035 cases. It covers completion, sack and
rush rows; repeated-team/opposite-team second fumblers; a known second player with
unknown team; and the actual generator's pre-fitting guard. The old generator
reaches the deliberately instrumented fitting boundary instead of rejecting the
unsupported input. Production now reports compound ownership as unsupported and
omits a misleading partial offensive-fumble ledger entry. The existing generator
rejection path is reused. This guard does not resolve the four raw compound events
or authorize a credit model; source acceptance remains unmet pending that work.

--- 2026-11-06 03:48 ---
All 275 combined ownership, generator, source and source-bundle checks pass.
The actual maintained 2024 preparation now exits one and retains exactly four
`fumble_ownership` failures before fitting; no fresh generated manifest is emitted.
The analogous 1983 preparation succeeds with all 84 CSVs reproduced. This is the
required unsupported-source failure, not a skip, waiver or four resolved events.
A single Ruff warning requests combining the new CLI test's nested contexts;
that style-only cleanup preserves every assertion and its thirteen checks pass.
The first full-core refresh is explicitly interrupted for that cleanup; a new
stable run is required, and no success is claimed for the interrupted command.

--- 2026-11-06 03:55 ---
Four pinned official gamebooks confirm distinct ownership sequences, including
Rush retaining his fumble before Guyton loses the second, and two later returner
fumbles. The [reconciliation note](../../compound-fumble-source-reconciliation.md)
records page identities and unresolved projection requirements. The corrected
ignored evidence revision 02 discovers actual statistics pages; draft 01 retains
a superseded notice for its incorrect universal page-2 assumption. All four
source rows remain unsupported. The accepted 527-event ledger is explicitly
partial; no event is silently waived, duplicated or assigned the global lost
flag. Primary official records do not establish independent upstream origins.

--- 2026-11-06 03:57 ---
Stable full core regression passes 8,904 tests, eight existing skips, 83% coverage;
Ruff and 275 focused checks pass. The public 2024 preparation still fails on all
four unresolved rows. Their official ownership evidence is a source fact review,
not implemented event projection or an acceptance waiver. Keep open. The new
public-only isolated checkout is testing the same adapter with no private season
inputs; its result is pending.

--- 2026-11-06 04:02 ---
A follow-up synthetic audit finds a remaining compound marker: a second player's
name can be explicit even if its team and ID are missing. Four new name-only
cases fail on the unchanged implementation, with 39 controls passing; three
incorrectly enter the single-event ledger, and the INT case lacks the compound
diagnostic. Twelve new blank/None/NA/nan controls remain supported. The guard now
considers the name as evidence of a second event without inventing its ownership.
No prior expectation changes. The four actual public compound failures and all
unknown physical gains remain unresolved; fresh stable validation is required.

--- 2026-11-06 04:08 ---
The first name-marker fix misclassifies NA sentinels; three new passing controls
catch that regression, with 288 other checks passing. A narrow sentinel correction
preserves every assertion. All 291 source checks now pass and Ruff passes; all
43 ownership cases also pass in a fresh public-only copy. Fresh maintained 2024
preparation still rejects the same four compound rows. Prior full isolated suites
are retained at their earlier runtime; new full core validation is pending.

--- 2026-11-06 04:12 ---
Complete stable core suite passes 8,920 tests with eight existing skips and 83%
coverage; focused source suite passes 291, isolated ownership suite passes 43,
and Ruff passes. The actual 2024 producer still rejects exactly four compound
rows before fitting, while 1983 reproduces all 84 CSVs. The stable component gate
rejects both cohorts: 2024 source preparation fails, and prior one-schedule engine
evidence remains stale and below required final exposure. Unit and source guard
success does not close the unresolved event projection. Keep open.

--- 2026-11-06 06:56 ---
The explicit credited-fumble proxy experiment preserves all four compound-source
rejections. Its public 2024 census separately rejects thirteen single retained
fumbles followed by incomplete passes because no supported credited class is
established. It projects 514 supported single events, without duplicating primary
mass or using the global lost flag for compound ownership. These are observed
source counts, not regenerated weighted chart mass. Compound projection remains
unapproved and no accuracy acceptance or closure is justified.


--- 2026-11-06 10:05 ---

The thirteen separately blocked single-fumble/incomplete-pass sequences now have
a complete source inventory: ten self-recoveries and three other-player offensive
recoveries. Two official books independently confirm this continued-play class;
eleven rows remain source-only. Forty-eight synthetic 2026 real-engine controls
across both sides, three field positions and first/fourth down show ordinary
passing F0 produces a completion, QT F0 a sack, BLACK an incompletion without F,
and rushing F0 a rush. None preserves the required incomplete pass plus retained
fumble. This is a bounded representation gap, not proof an engine extension is
impossible. It does not resolve the four compound rows or approve their ownership
and return-pool model. Failed research fourth-down flag assumptions are retained;
corrected controls assert engine-owned possession separately and retain class
checks. No production or existing unit expectation changes. No full-game or
weighted-mass acceptance evidence is added; keep open.

### 2026-11-06 10:47 CST — continued-pass primary review complete

All thirteen retained-fumble/incomplete sequences now have visually reviewed
official PBP, following snap and final individual-statistics pages. The ignored
`retained-fumble-continuation-01/primary-review-02.json` binds all thirteen PDFs,
page numbers and raw source identities (SHA-256
`4af0447fdbc32037f3ff53f9ad42f0b973e93ef2627d8195f2b192bc465ac810`).
Ten self recoveries and three teammate recoveries retain one incomplete attempt
without an extra rush or sack. One intermediate narrative enters the offense's
own end zone before the eventual incomplete pass; the next snap retains the
original line and no safety is awarded. Unknown internal physical/movement facts
remain null. The parent approved narrow `F INC`; engine work is separate and
source/generator/observer integration is in progress. This does not close the
issue or qualify rare-event probabilities.

The return inventory additionally identifies a fifth modern compound source row
whose second fumbler fields are blank despite two final-narrative fumbles and
two recovery records. The prior four-row inventory is incomplete; it remains a
historical checkpoint. Replay replacement and no-play controls are required
before strengthening the guard. The LAC aborted-punt sequence had been incorrectly
described as NO's offense in the proposal; LAC owns both fumbles. Preserve that
correction in subsequent ledgers and projection review.


--- 2026-11-06 10:52 ---

Typed F INC now passes through both source adapters, empirical input, opponent
adjustment, generation, recovery calibration and retained/voided observers.
The complete modern census projects all 13 reviewed continuations with physical
gain null; ordinary F/QT allocation and recovery denominators exclude them.
All 526 supported single events reconcile, while exactly five compound plays
remain unsupported. Exact all-formation diagnostics disclose the priority change
versus BLACK; full-engine fit and source-complete compound projection remain
required. This component milestone does not close the issue or release hold.


--- 2026-11-06 11:12 ---

Ordered source evidence and a diagnostic projection now pass 481 focused tests.
Official review confirms the fifth compound play's two retained Mayfield fumbles
and Bailey's blocked-punt recovery advance of two before a lost fumble. Together
with the four earlier books, eleven events reconcile as five primary origins
and six shared-return fumbles, preserving individual losses, scoped advances,
play credit actors and null physical gains. The local packet binds raw records
and official book pages; it does not authorize chart fitting.

All 42 blocked-kick source rows are captured, with unknown advance placeholders
kept null. Muff-only provider flags remain unsupported occurrence evidence.
Existing five-compound generation guards, peripheral ranges and release bounds
remain unchanged. Measured shared-consumer exposures and independent residual
review are still outstanding, so this issue stays open.


--- 2026-11-06 13:08 ---
The preserved diagnostic exposure baseline resolves all 409 terminal shared
segments and 450 lookups. The first single-allocation profile independently
checks all 32 teams and 256 consumer rows without changing charts or running
new games. Quantized aggregate expected F is 10.887774 versus eleven source
events, but INT expected F is 9.118141 versus five and conditional expected F
is 1.769633 versus six. Scoped F gain is 233.567870 versus 241 reported/model
yards; expected 20+/40+ counts are 4.034916/1.960098 versus four/two. All physical
gains remain null. Raw-range loss expectation is 4.934064 versus four official
individual losses; hypothetical final-loss expectation and incompatible whole
conditional non-F targets remain null. Current peripheral ranges and all 32
penalty masses are unchanged. This diagnostic neither accepts exchangeability
fit nor closes the issue. Corrected candidate exposures, supported typed adapter
ingestion and fresh complete qualification are still required. Ignored immutable
receipts are under release-readiness/return-exposure-03/.

--- 2026-11-06 18:47 ---
The historical source review found another multiplicity case in the November 20, 1983 Cleveland–New England official book, page 8. After Collins's primary carry/fumble, Morgan recovers, returns, then explicitly fumbles and recovers himself. The raw PFR play text reports Collins's fumble and Morgan's recovery/return but omits Morgan's second occurrence. Root independently viewed the bound scan. The primary rushing-class finding can be retained separately; it does not reconcile the conditional event or establish its physical gain, individual credit or shared-chart projection. Keep the omitted occurrence explicit in the held source inventory. The 727-record historical classifier census is not proof of a complete individual-fumble ledger. No duplicate primary F mass or zero-gain substitution is authorized. Evidence remains ignored under `gsis-1983-reconciliation/recovery-source-07/`; no production code or chart changed for this finding.

--- 2026-11-08 17:08 ---
Lowered High to Medium. This remains a real compound-event projection limitation: the corrected modern screen has five compound plays, not the original four, and a historical omitted secondary occurrence is documented. Ordered event ledgers preserve ownership; unsupported generation paths are guarded instead of silently duplicating a primary event. Complete shared-return exposure/residual qualification and production projection remain unfinished. The bounded known source cases warrant follow-up, but do not establish a broad current gameplay failure; small counts do not prove zero outcome impact. No existing generation guard or acceptance criterion is waived.

Reviewed current committed implementation and existing issue evidence. Fresh
focused validation: 239 gameplay/ownership/source/runner/standings checks and
417 parser/reconciliation/generation/source-bundle checks pass, without skips
or warnings. These focused checks are not full regression or new season runs.
See [high-priority audit](../../high-priority-issue-audit-2026-11-08.md).

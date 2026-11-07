# Primary-source PFR event reconciliation proposal

Development design under the [chart-confidence charter](chart-confidence-agent-charter.md).
Implemented locally after the baseline below; release remains held. The independently
verified [Denver gamebook](chart-source-denver-1983-coverage.md) motivates this
capability, not a team-specific exception or change to official targets.

## Separate facts and physical assumptions

A supplemental record may establish a credited sack and its credited loss without
establishing the initial loose-ball location or recovery movement. Preserve the
raw PFR play, including its conflicting prose, and represent those facts as
separate typed fields. An unknown physical initial gain must supply no numeric
QT/fumble sample. Count the independently supported sack and retain the fumble
occurrence/recovery family; report the missing conditional severity explicitly.
Do not turn a credited loss into an observed physical F cell.

The first bounded capability supports credited sacks and their known/unknown
initial severity. It does not introduce generic outcome replacements, route-depth
facts, target-count overrides or arbitrary chart tokens. Existing route allocation
remains a declared heuristic. Unknown recovery ownership still blocks generation.

## Provenance and validation

Use an optional JSON event-fact input to the existing PFR root command. Each record
identifies a game and play, the raw HTML SHA-256 and a canonical hash of every
parsed play field. Bind independent evidence to a local file's actual SHA-256,
a public HTTPS source URL and positive reviewed page numbers. Keep the evidence
files and sidecar in ignored storage. This proves input identity/consistency, not
that software can independently read a historical scan or certify a human fact
review. Retain that limitation in the report.

Reject duplicate or unused event keys, absent plays/games, changed raw bytes or
play context, changed evidence bytes, malformed types, invalid page references,
unknown fields and facts attached to nullified/offsetting plays. Preserve source
conflicts rather than rewriting narratives. Record applied facts and evidence in
the source ledger and hash every extra input in the generation manifest, so the
existing raw-input/reproduction checks cover the correction.

## Test-first acceptance

Synthetic regressions must first fail for counted-but-unknown physical sacks,
known zero versus unknown initial severity, real fumble recovery ownership and
unchanged controls. Negative controls must reject all provenance/type/inventory
mutants above. Root-command tests must show ledger/manifest propagation and
refusal of unresolved required recovery fields. No historical data belongs in
unit collection; the actual source event is a separate ignored integration check.
A correction may reconcile credited occurrence counts without satisfying physical
initial-gain or full chart acceptance. Keep those verdicts separate.

## Baseline checkpoint

The initial synthetic fixture accidentally included the substring `pass` in its
quarterback's name, triggering the pre-existing text classifier. That control
was corrected to a neutral name before any production change; this is not an
existing expectation change. The resulting baseline has 33 failures and 50
passing PFR controls: 31 absent typed-API/provenance cases, the absent CLI option,
and a separate concrete loss of fumble occurrence when an explicit sack has
unknown severity. The latter fails on the existing classifier's returned values,
not setup. The new loader/API is intentionally absent at baseline; no new source
or runtime dependency is required.

## Local implementation checkpoint

The optional CLI input, typed loader and source/event checks are implemented.
Unknown initial severity now retains known fumble occurrence even for an existing
explicit sack. Whole source facts, evidence inputs and all fumble events propagate
to ledgers/manifests; two additional root-ledger cases fail first when that fumble
inventory is absent. The first integrated run passes 256 tests; the extended
ledger run is recorded after completion. Two newly added assertions are corrected
to the existing canonical `F - 2` spelling and the existing capitalized error
message; no pre-existing test expectation or behavior is weakened.

A root regression completed before this feature: 7,262 passes, eight existing
missing-data skips and 81% coverage in 359.89 seconds. Its checkpoint includes
parser name/location and display-state corrections, not this later feature.
Fresh whole-candidate regression remains required. The actual ignored 224-game
source check now reconciles the three official occurrence totals, without a
physical initial gain for the newly supported event or a candidate acceptance.

## Reviewed fumble facts and split rows: next bounded extension

Implemented locally after the baseline below: schema 2 retains schema-1 sack records and adds
explicit `fumble` and `prepass_fumble` record types. A fumble record supplies
reviewed recovery ownership and an out-of-bounds fact; an optional initial-gain
field distinguishes an absent correction from an explicitly unknown gain.
Require an existing retained offensive fumble, reject ownership/gain conflicts
with already known parsed facts, and reject lost-plus-out-of-bounds assertions.
These are observed source facts, never arbitrary chart tokens or fitting knobs.
The existing engine's generic F recovery model does not exactly reproduce an
observed out-of-bounds recovery; retain that limitation rather than invent F*.

A prepass record binds both a standalone source fumble row and its immediately
following incomplete-pass row by complete hashes. Require the same actor,
quarter, down, distance and location. The independently reviewed gamebook must
establish one snap: fumble, own recovery, then incomplete pass. Retain one passing
fumble occurrence, one incomplete-pass outcome and both raw row identities;
create no extra rush, sack, physical gain or terminal F outcome. Explicitly count
this unmodeled conditional fumble rather than claiming the BLACK cell reproduces
it. Reject missing, changed, nonadjacent or incompatible continuation rows and
overlapping reconciliation records. Raw prose remains unchanged.

The source review finds seven events explicitly marked out of bounds in their
play narratives; two additional player-level tables uniquely identify the
remaining unannotated out-of-bounds fumbles. The Green Bay table confirms three
Huckleby fumbles, including one out of bounds; the following Dickey fumble is
separate. Do not erase the Huckleby event from an incomplete play annotation.
The Raiders' interrupted completion description has an independently verified
initial loss of five. The Seattle split row is one incomplete pass with an
earlier own-recovered fumble. All actual-event records stay in ignored local
source inputs; synthetic regressions must fail before extending production.

The first schema-2 baseline has ten expected missing-capability failures and 138
passing controls. Three later adversarial failures expose accepted fouls with
unapplied F facts, a numeric run disguised as a bare prepass fumble and an unknown
actor name. After correction, 340 integrated source/generator tests and lint pass.
The root test runs both input schemas and verifies the manifest's actual version.
The schema-2 extension above is now implemented locally, without changing any
pre-existing expectation. A fresh root regression is running.

The actual 224-game ledger reproduces byte for byte. All 28 teams still reconcile
1,215 sacks, 620 interceptions and 771 field-goal attempts. Twelve reviewed records
remove all nine remaining unknown recoveries and both required-gain gaps: ten F
facts, one split prepass event and the existing sack fact. The offensive subset
remains 713 fumbles/417 losses; thirty other recoveries still use the unique
team-box constraint. Twenty-five sacks have unknown physical severity. Nine
reviewed out-of-bounds recoveries and one prepass fumble expose conditional model
limitations, not an accuracy pass.

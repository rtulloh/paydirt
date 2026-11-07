# Compound-fumble source reconciliation

Status: investigation checkpoint, 2026-11-06. Event ownership has supporting
primary-source evidence; compound-event chart projection and physical initial
gains remain unresolved. DATA-030, DATA-035 and DATA-036 remain open. This note
does not authorize a source-credit model, calibration or release.

## Current source boundary

The unchanged public 2024 input contains five interception-return fumbles that
were falsely recorded as original-offense passing fumbles. The narrow ownership
fix removes those five offensive entries and preserves their INT/return results.
Four other rows explicitly contain two fumbles. Current generation rejects all
four before fitting rather than treating a partial ledger as complete truth.

The current adapter records 527 accepted offensive-fumble entries, five excluded
interception-return cases and four unsupported compound rows. The 527 is a
partial count, not a complete offensive-fumble target or a new acceptance total.
The maintained 2024 preparation fails; 1983 reproduces all 84 candidate CSVs.
Neither result supplies missing physical gain or a reviewed compound-event model.

## Primary evidence

The official gamebooks support these distinct ownership sequences. Page numbers
refer to the pinned PDF bytes in ignored local evidence; hosted versions can
have different pagination. Lost below describes each individual fumble.

| Source event | Official event sequence | Primary book pages |
| --- | --- | --- |
| `2024_08_NO_LAC`, play 370 | Aborted punt: Harris fumbles, Scott recovers and later fumbles out of the end zone. Both fumbles are recorded as not lost. Scott receives one zero-yard rush; separate fumble movement is recorded. | [Saints–Chargers](https://static.clubs.nfl.com/image/upload/saints/z5bb8asupbqw21gac6gz.pdf), individual statistics 2, play 8 |
| `2024_11_HOU_DAL`, play 3780 | Rush's sack fumble is recovered by Guyton. Guyton then loses his own fumble to Barnett. The row's lost flag cannot be assigned to both Dallas fumblers. | [Texans–Cowboys](https://static.www.nfl.com/image/upload/v1732015858/gamecenter/ae9d82c3-1312-11ef-afd1-646009f18b2e.pdf), individual statistics 2, play 14 |
| `2024_13_PIT_CIN`, play 1857 | Burrow loses a sack fumble to Wilson. Wilson fumbles during the return; Smith recovers for Pittsburgh. The second fumble belongs to the return team. | [Steelers–Bengals](https://static.www.nfl.com/image/upload/v1733139292/gamecenter/45c0f754-1313-11ef-afd1-646009f18b2e.pdf), individual statistics 3, play 11 |
| `2024_15_CIN_TEN`, play 3191 | Pollard loses a rushing fumble to Battle. Battle later fumbles out of the end zone. Replay replaces the initial touchdown with a touchback; each player is credited with a lost fumble. | [Bengals–Titans](https://static.www.nfl.com/image/upload/v1734350422/gamecenter/45c18ce8-1313-11ef-afd1-646009f18b2e.pdf), individual statistics 3–4, play 14 |

The [nflfastR field definitions](https://github.com/nflverse/nflfastR/blob/master/data-raw/variable_list.txt)
distinguish first and second fumblers. Recovery columns identify a recovering
player and credited movement; their descriptions do not promise that array
positions form a complete chronological recovery chain. The documented
`yards_gained` definition excludes recovery/lateral gains. It does not establish
a physical contact/fumble spot or eliminate official credit adjustments.

The books are separately retrieved primary evidence, not proof of statistically
independent data origins: nflverse may derive from the same NFL records. Table
and play-by-play identities must be retained separately from modeled projections.

## Retained evidence and limits

Ignored `compound-fumble-source-evidence-02/report.json` binds the raw input hash,
event-row hashes, selected structured facts, exact PDF bytes, PDF page images,
locally extracted page text, and the pinned nflfastR
field-definition revision. Individual tables were visually inspected. Version
01 is retained with a superseded notice because its draft incorrectly assumed
all individual-statistics tables were on page 2. Version 02 discovers the actual
individual-statistics pages and retains the continuation page where applicable.

Every event's physical initial gain remains null in this receipt. The prose can
report locations and movement without proving that a single signed number is
the correct engine input or the official statistical credit. No recovery-yard
subtraction, duplicate primary F mass, narrative override, global-lost assignment,
source omission or target change is introduced.

The existing engine can resolve chained fumbles in `_resolve_return_chain`.
Some own/opponent recoveries continue on the recovering team's interception-return
chart, which is also used by actual interceptions. This establishes a capability,
not a reviewed source projection: fitting the later fumble population on that
shared chart can also change interception and other recovery behavior. Separate
event inventory, conditional mass and all affected distributions must reconcile.
The four current source failures do not establish an irreducible engine limit.

Before generation can accept these rows, the reviewed model must specify:

- Separate fumbling and recovering teams, player identities, terminal recovery
  or out-of-bounds disposition, and event-level lost credit.
- The original play's credited family and the later fumble's distinct event
  family, including the aborted-punt case and return fumbles.
- Which facts are source-provided, officially confirmed, unknown or modeled;
  how missing recovery order and conflicting fields fail before fitting.
- The explicit projection into available board-game charts, with diagnostics
  for events the charts cannot separately represent and exact mass accounting.

The existing gain-proxy proposal alone does not supply that compound projection.
The four support failures remain failures until the additional model and its
acceptance implications are reviewed, implemented test-first, and validated.
Reserved seed families and prospective data remain unopened.


## Follow-up — 2026-11-06 11:19 CST

The preceding four-row census is a historical checkpoint. The corrected complete
modern screen includes a fifth compound play, `2024_10_SF_TB:3527`: Mayfield
fumbles, recovers, advances one reported yard, then fumbles again to Irving.
Official gamebook pages three and thirteen confirm both fumbles were retained.
A separate blocked-punt sequence, `2024_05_MIA_NE:1249`, reports Bailey's own
recovery and two-yard advance before his lost fumble; official pages two and ten
confirm that scope. Provider return zero is not the two-yard advance.

The ignored `compound-fumble-source-evidence-03/reviewed-ledger-projection-03.json`
packet binds all five compound plays plus the blocked-return event to raw play
hashes, individual loss reviews and official book hashes/pages. It preserves
eleven ordered events, five primary origins and six shared-return fumbles, with
unknown physical gains null. Scott's aborted-punt statistical rushing credit
remains separate from Harris's first fumble. The source adapters expose this
lossless ledger; the diagnostic projection does not feed chart generation.

Focused source/regression and Ruff checks pass. Generation still rejects the five
compound rows pending complete source support, actual shared-consumer exposure
measurements and independent residual review under the existing model decision.
This is no final shared-model acceptance, candidate qualification or release.

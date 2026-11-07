# Generated defense pattern census

Read-only investigation, November 6, 2026. Requested after the owner found a
repeated interception row in Bowl Bound. No Paydirt chart, source fact,
generator, tolerance, coaching policy or release was changed by this audit.

The concern does occur in Paydirt. Repeated defensive cells come from a shared
tactical template and ordered interception allocation. They deserve explicit
model review; visual repetition alone does not establish an incorrect frequency.
The dedicated follow-up is [DATA-040](issues/DATA/DATA-040.md).

## Coverage and verification

Every defense has 270 cells: nine calls, six formations, five subrows. The census
checks all 60 maintained generated teams, the separate newer 28-team historical
and 32-team modern candidates, the approved older layout snapshot, and public
2026 fictional fixtures. It also covers every public-provenance generation
manifest found under `seasons/` and ignored `.ai-audits/`: 206 manifested cohorts.
The total including the public fixtures and two layout cohorts is **209 cohorts,
6,210 team instances and 1,676,700 cells**. These contain **319 distinct defensive
contents**; copied snapshots and experiments are not independent observations.
Each cohort remains separately identified in the report.

The independent raw-CSV checker reconciles all cells, core-loader values,
category counts, physical masses, coordinate inventories, all-formation stripes
and uniqueness counts. All **6,416 chart/manifest hashes** and five runtime source
hashes match. Synthetic checks detect an injected all-formation `INT 17` row,
distinguish parenthesized replacements, reject unknown tokens, and show that
different printed counts can have equal physical mass: row 1 equals rows 2+5.

Ignored evidence is in
`.ai-audits/release-readiness/defense-pattern-census-01/`:

- `report.json`: complete coordinate, pattern, pairwise and resolver census;
  SHA-256 `359c35b3635fbf95e1ac254108906428e159e1f6999e1b62b8d788246e99d53b`.
- `independent-verification-and-geometry-01.json`: independent CSV/hash checks,
  exact-token/category/mechanism runs, adjacency, 2-by-2 blocks, numeric bands
  and replacement flags.
- `generator-cause-reproduction-01.json`: bounded synthetic reproduction using
  the current generator's interception allocator.
- `unbound-path-inventory-01.json`: path-only inventory outside accepted roots.
  Imported private charts are excluded. Unmanifested older experiments and
  copied sample fixtures do not become accepted cohorts by their folder names;
  their contents were not read for this additional inventory.

## Repeated interception rows

An all-formation stripe means the same call and subrow has the same token in
**all six** Paydirt formations, rather than all nine calls in a printed row.

| Separate chart set | All-formation Short Pass row 5 `INT 5` | All-formation Screen row 5 `INT 5` |
| --- | ---: | ---: |
| Maintained older 1983, also served in the approved layout snapshot | 23/28 teams | 4/28 teams |
| Maintained older 2024, also in that snapshot | 2/32 teams | 0/32 teams |
| Newer 1983 shared-calibration candidate 03 | 0/28 teams | 4/28 teams |
| Newer 2024 corrected-joint diagnostic 02 | 0/32 teams | 0/32 teams |
| Public fictional 2026 fixture | 0/2 teams | 0/2 teams |

The four newer historical Screen cases are Cardinals, Chiefs, Redskins and
Steelers. Seven newer historical teams also have interceptions across all five
passing calls in formation D's fifth row, with depths `5, 5, 12, 18, 8`.
Neither pattern should be described as eliminated by the existing correction.

Across all 319 distinct contents, 75 have at least one all-formation interception
stripe and 27 have a passing-row interception stripe. No defense has one exact
token filling a whole nine-call row or all five subrows of a formation/call.
None has all five passing calls intercepted on row 5 in every formation.
These absences apply to the inspected generated population, not imported charts.

## Weight and engine meaning

The core defensive dice give rows 1–5 weights **12, 11, 9, 3, 1 out of 36**.
Six repeated row-five cells do not mean six chances on one selected play. The
selected formation/call encounters that cell with probability **1/36**.
Aggregate mass across uniformly counted contexts is labeled descriptive; it is
not a claim about actual coaching usage.

The real resolver confirms that the newer Cardinals Screen stripe contributes
an interception at depth 5 with probability 1/36 in each formation against the
synthetic ordinary-10 offense. All six full outcome distributions still differ:
coverage, gains and touchdown risk also matter. This is a real shared event
component, despite those broader tactical differences. Protected offensive
overrides, fumbles, penalties and other priority branches can change exposure;
1/36 is not an unconditional historical interception rate.

The census evaluates all 319 distinct defenses through the real priority and
B/QT resolver against that declared synthetic offense. All 2,871 defense/call
comparisons retain five or six distinct full formation distributions. Thus no
complete collapse of tactical outcomes is found in this control. This does not
certify all offenses, positions, penalty choices, recoveries or terminal returns.
Pending outcomes are retained rather than assigned invented net yards.

## Other repeatable structure

The mechanism comparison merges ordinary positive, zero and negative numeric
adjustments, while preserving parenthesized replacements, BLACK, QT, TD and INT.
The more detailed core categories and numeric bands are also reported separately.

| Separate set | Positions with one mechanism across all teams | Closest team pair: exact cell agreement |
| --- | ---: | ---: |
| Older 1983 | 252/270 | Bengals/Raiders, 96.67% |
| Older 2024 | 254/270 | 49ers/Titans, 99.26% |
| Newer 1983 candidate 03 | 252/270 | Bears/Dolphins, 92.22% |
| Newer 2024 diagnostic 02 | 261/270 | Dolphins/Titans, 99.26% |

Every individual cohort has distinct complete team defenses. Near duplicates
and high mechanism agreement remain model limitations, despite uniqueness.
Every historical/modern team in these four sets has negative-yard bands with
vertical runs of five and horizontal runs of at least three. Parenthesized
replacement bands also reach five subrows. The newer historical candidate has
horizontal QT runs of three in all 28 teams. The appendix measures these
patterns without imposing invented universal run caps.

All interception tokens observed across the manifested corpus use just four
numbers: `INT 5`, `INT 12`, `INT 18`, `INT 8`. The core uses this number as
interception depth, separately from its return roll. These fixed depths are
shared model support, not recovered team-specific catch locations.

## Cause and corrective boundary

`_generate_defense()` starts from a common tactical template, optionally with
the source-constrained neutral pressure map. Efficiency changes affect numeric
values; `_allocate_defense_interceptions()` clears old INT positions and assigns
strength through a fixed ordered list of fifth-row cells. A declared synthetic
rate of .06 fills all six Screen row-five cells with `INT 5`; neutral .025 does
not. This reproduces the mechanism without inferring a historical formation
rate or changing any chart.

The newer candidates keep every defensive INT on the 1/36 subrow, removing the
older high-mass interception floor tracked in [DATA-022](issues/DATA/DATA-022.md).
That correction can still create row-five stripes and retains fixed depth
support. Existing formation contrast does not establish that these placements
or depths are historically accurate.

Defense cannot inherit the primary offense's free equal-weight cell dispersion.
Its five subrows have different weights, and exchanging cells across formations
changes their conditional tactics even if an aggregate histogram stays fixed.
Any proposed change needs a declared purpose, preserved weighted conditional
outcomes or an explicit supported model change, and renewed source/engine/AI
qualification. This census makes no cosmetic permutation or new source claim.

No game or browser campaign ran for this audit. Existing resolved issues were
reviewed; these stationary diagnostics supply no new issue-specific play-test
closure evidence. DATA-022 and [DATA-039](issues/DATA/DATA-039.md) remain open.

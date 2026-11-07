# Defensive allocation correction

November 6, 2026. Bounded DATA-040 change implemented after parent model review.
This is development evidence, not source certification or release qualification.

The previous strong-defense queue eventually replaced every Screen fifth-row
result with `INT 5`, including the parenthesized counterplay in B, C and F. The
source stats supply a team interception rate, not formation/call interception
rates. That queue had an unsupported tactical side effect.

The correction replaces three queue entries at the same tiers: B/Screen becomes
B/Short Pass, C/Screen becomes C/Short Pass, and F/Screen becomes F/Medium Pass.
Each destination is already BLACK after interception normalization. The neutral
D/Short and E/Long allocations, first nine additions, rate scale, 1/36 subrow and
maximum seventeen units remain. Every formation retains its total interception
units at every strength tier. At saturation the five passing calls have 3, 4, 5,
3 and 2 cells respectively; none occupies all six formations.

This is a model change: six formation/call conditional distributions can change,
so it is not equal-weight layout. In B/C/F Screen the parenthesized counterplay
returns; the corresponding coverage calls exchange a 1/36 BLACK incompletion for
an interception. F's moved tier uses the existing Medium Pass depth twelve instead
of Screen depth five; the available depth support itself is unchanged. Under the
declared normal reference weights, maximum defensive
interception exposure rises by 520/201600 (about .002579 per selected primary
passing call). That quantity is not an official credited-attempt rate. Actual
primary overrides, pending fouls, QT, field position, returns and coaching change
exposure. Whole-candidate source fit must be renewed.

The pressure allocator already reserves the interception queue. Its three new
destinations therefore cannot receive relocated QT. A synthetic .035 source sack
rate previously moved QT into F/row-five/Medium; the corrected allocation finds
another attainable pressure layout. High interception strength preserves that
layout's QT and B/C/F Screen replacements through generation and CSV loading.

## Retained pattern classifications

| Pattern | Purpose and boundary | Verification |
| --- | --- | --- |
| Numeric bands and repeated small adjustments | The common tactical template expresses formation strengths/costs. Source rushing/passing efficiency shifts its numeric values through exact defensive weights. Similar inputs can remain similar; no historical formation-specific yardage is inferred. | Existing close-efficiency, strength and tactical contracts; new controls preserve every run cell and rows one through four while interception strength changes. |
| Parenthesized numeric and touchdown bands | These are replacement outcomes, not ordinary additive numbers. They preserve counterplay even against protected/secondary primary outcomes. Interception strength must not consume these costs. | Complete weighted B/C/F Screen inventories remain; real resolver controls cover ordinary/protected/B/QT/INT/fumble/penalty inputs. |
| BLACK coverage | This supplies incompletions and coverage tradeoffs. Extra interception strength can consume specified rare BLACK slots; identical BLACK components alone do not imply identical formations. | Existing tactical contracts plus the declared per-call allocation change. Shared coverage and formation D's possible five-call row-five INT band remain modeled structure, not source-recovered placement. |
| QT runs | Pressure is separate from interception strength. The shared pressure model uses source sack ceilings and declared normal reference weights, while preserving designated strength controls. | Existing cohort-pressure regressions and new .035/.04 source sack controls; every QT cell survives high interception strength. |
| Four fixed interception depths | The generator uses depth 5/12/18/8 by call; the resolver treats depth separately from return gain. The available team totals do not identify conditional catch depths. | Existing support is preserved. Depth accuracy and downstream field-position/return fit remain open qualification limits. |

These classifications do not make repeated templates historically accurate.
There is no universal run cap or name-seeded depth/layout decoration. The change
preserves known tactical costs and isolates the consequential allocation change.

## Test-first evidence and remaining qualification

The nineteen synthetic-only allocation cases first produced five intended
failures and fourteen passing controls. Two additional pressure-integration cases
then failed on a QT collision and lost Screen counterplay before production edits.
The implemented change passes all twenty-one cases. No existing expectation or
skip changed. The earlier in-process trial also passed existing tactical contracts
at 101 synthetic rates from zero through .10.

The combined generator, pressure, tactical and source-bundle suites recorded 286
passes and one unrelated offense-layout failure. That same failure reproduces
with the previous interception queue; it belongs to the separate DATA-039 lane.
The source CLI/PFR suites pass 78 cases, generated-source audits pass 56, and owned
Ruff checks pass. Receipts remain ignored under
`.ai-audits/release-readiness/data040-defense-fix-01/`.

The bounded local paired diagnostic covers sixty teams and 16,200 defensive cells
per side using hash-bound normalized stats and retained neutral maps. It finds
no all-six interception stripe after the change; tactical contracts and five or
six ordinary-10 formation distributions remain. Fourteen historical projections
change, with fifty-four changed cells; modern projections do not reach the moved
tiers. This is not a final-candidate census: normalized stats precede the source
pipeline's opponent-adjusted defense calibration, and the old-map projections do
not reproduce old candidate CSVs. The report explicitly retains those differences
and does not overwrite earlier receipts.

Fresh source/pressure generation, frozen all-sixty candidate census, exact chart/API
identity, source fit, stateful return/recovery effects, AI and required full
regression remain parent qualification work. DATA-040 stays open until the normal
committed-fix/play-test workflow is complete.

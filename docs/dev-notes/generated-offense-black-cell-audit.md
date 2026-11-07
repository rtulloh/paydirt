# Generated offense black-cell investigation

Read-only investigation, 2026-11-05, prompted by the owner's side-by-side
Dolphins chart review. **The generated chart is not established as more faithful
than the supplied developer chart.** No generator, chart CSV, gameplay rule or
display behavior changed during this investigation. The existing release hold
remains in effect.

## Reproduction and physical probability

Reclassified all 224 regular-season source games, repeated opponent adjustment,
applied the promoted profile, and regenerated the public Dolphins offense in a
temporary directory. The resulting `offense.csv` is byte-identical to
`seasons/1983-generated/Dolphins/offense.csv`. The browser is rendering the
loaded results; the black cells are not missing data or a rendering failure.

There are 30 visible rows, but their physical dice weights sum to 216 and range
from 1 to 18. Visible cell counts cannot substitute for probability:

| Generated Dolphins column | Black cells / 30 | Black physical mass / 216 | Black probability |
| --- | ---: | ---: | ---: |
| Screen | 13 | 62 | 28.70% |
| Short | 14 | 70 | 32.41% |
| Medium | 16 | 94 | 43.52% |
| Long | 20 | 130 | 60.19% |
| T/E S/L | 14 | 81 | 37.50% |

These are primary offense-chart incompletion probabilities. Defense priority,
QT, penalties, and retained/nullified plays affect final engine statistics;
these percentages are not final completion-rate complements.

## Why the black cells form blocks

`_empirical_column()` allocates the most common symbolic family first.
`_nearest_roll_mass()` retains the first subset reaching a physical mass. The
candidate order comes from the available integer-row set and is not randomized
by the supplied column seed. Large BLACK families consequently occupy many
early, low-mass rows. The seed changes family variants and numeric assignments
but not that BLACK selection in the five tested Dolphins columns: seeds
3, 19, 41 and 8306 produce identical black-row masks for fixed inputs.

This is an observed layout limitation, not proof of a probability defect. Any
future visual redistribution must preserve the physical outcome distribution;
an unrestricted shuffle among unequal-weight rows would change play behavior.
The separate confirmed sparse-mass rounding bug remains
[DATA-016](issues/DATA/DATA-016.md).

## Why the rates and remaining gains need scrutiny

The promoted profile uses a completion adjustment of -0.06 and a passing-yard
multiplier of 1.55. The empirical pass-event step replaces source event rates
with aggregate-model rates and applies that profile; it does not simply replay
the source's observed completion/incompletion ratio. Rates are further rounded
to empirical sample counts, then quantized onto physical dice mass.

| Column | Classified source incomplete share | Aggregate baseline incomplete share | Profile-adjusted empirical incomplete share | Published incomplete share |
| --- | ---: | ---: | ---: | ---: |
| Screen | 27.27% | 22.22% | 28.57% | 28.70% |
| Short | 36.31% | 26.39% | 32.40% | 32.41% |
| Medium | 31.09% | 37.50% | 43.52% | 43.52% |
| Long | 48.57% | 54.63% | 60.00% | 60.19% |
| T/E S/L | No separate source sample | 31.48% | 37.56% | 37.50% |

Shares in this table use all entries in their respective primary column,
including pressure, interception and penalty entries. Those other shares also
change. A higher incomplete share alone therefore does not prove a lower
completion rate conditional on a counted pass attempt. T/E S/L uses the combined
adjusted Short/Medium/Long samples rather than a separately identified route.

For Long, the classified raw numeric gains average 44.63 yards, the
opponent-adjusted numeric sample averages 44.69, the profile-adjusted resampled
numeric sample averages 67.43, and the final physical conditional numeric mean
is 66.13. Two generated cells contain 99 or 99*; another contains 95. These
conditional means exclude other result families and precede engine field
clipping, priority and recovery rules. They are not whole-play passing YPA.

The PFR adapter infers missing pass families partly from observed total gain
and down/distance. It assigns most gains of at least 30 yards to Long. Total
gain does not independently establish intended route depth or air yards.
Consequently, neither these family samples nor a visually similar chart can
certify historical play-family accuracy. The manifest already discloses
16,141 heuristic pass-depth assignments across the season.

## Current engine evidence and next work

The final corrected-observer study already ran 1,024 Dolphins team-games and
31,315 pass attempts. Its completion rate is 53.58%, against the normalized
aggregate source target of 254/442 = 57.47%; passing YPA is 7.78 against
3235/442 = 7.32. This is evidence under the declared measurement policy, not an
independent historical coaching replay. It reinforces the open
[DATA-018](issues/DATA/DATA-018.md) calibration finding. It does not identify one
parameter as the sole cause, prove the supplied developer chart accurate, or
justify tuning around the unresolved source and priority defects.

Resolve the recorded source/engine/allocation blockers first. Subsequent
calibration should inspect team and play-family completion/turnover/yield
tradeoffs, sample support and independent validation seeds, with explicit
limitations for inferred route families. Preserve the full outcome distribution
when considering layout improvements. The comprehensive gate and its limits
remain documented in [the combined audit](generated-chart-release-audit.md).

The reproducible diagnostic script and public aggregate report remain in
ignored `.ai-audits/chart-release-audit/diagnose_black_cells.py` and
`black-cell-diagnostic.json`. No private developer chart cells, historical
source narratives or workbook data were exported into this note.

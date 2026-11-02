# Generated Chart Completeness Audit

Developer investigation, November 2, 2026. This records implemented corrections and remaining
model limitations; it does not certify that generated charts reproduce developer charts or actual
NFL results. Tickets: [DATA-014](issues/DATA/DATA-014.md),
[DATA-013](issues/DATA/DATA-013.md), and [DATA-006](issues/DATA/DATA-006.md).
Current calibration evidence belongs to [DATA-011](issues/DATA/DATA-011.md); DATA-006 records
the earlier completed input and engine-measurement work.

## Coverage

The local comparison covers all 28 teams in the developer and generated 1983 sets: eleven offense
columns, six special-teams columns, extra-point misses, fumble recovery ranges, metadata, and all
six defensive formations. All 54 primary play/formation combinations are combined through the
engine's priority chart with physical dice weights. Blank legacy cells are measured as the engine's
zero defaults rather than omitted from probability denominators. Complete generated rows remain a
strict requirement. Full-game replay measures secondary B/QT resolution, coaching, field position,
clock, and scoring separately.

Private charts and detailed comparison reports remain in ignored local storage. The maintained
audit implementation and regressions contain no historical chart fixtures.

## Confirmed defects corrected

| Area | Correction |
|---|---|
| Numeric distribution | Sort empirical quantiles numerically, including negative and marked gains. |
| Season sampling | Resample across the full sequence instead of taking only early-season outcomes. |
| Penalty variants | Retain observed foul types while calibrating total penalty exposure. |
| Long runs | Preserve B out-of-bounds markers; leave fumbles on the originating run family. |
| Physical limits | Bound scaled gains at 99 yards; retain the 18-yard direct-run limit. |
| Field goals | Encode supplied block counts and avoid counting their accuracy loss twice. |
| Kickoff fouls | Assign OFF/DEF relative to the chart actually receiving the foul. |
| Kickoff boundaries | Distinguish the kick going out from a return ending out of bounds. |
| Modern return samples | Exclude zero placeholders on fair catches, touchbacks, downed kicks, and blocked punts. |
| Penalty enforcement | Preserve nominal foul yards and recognized automatic-first-down symbols. |
| Source omissions | Record observed coverage and explicitly modeled features in each generation manifest. |
| Generation gate | Both source commands automatically write `chart-audit.json` and fail on structural errors. |
| Recovery coverage | Reject overlapping, uncovered, reversed, or out-of-range fumble recovery intervals. |

Changed previous expectations: a fumble on a long run remains on that run column and is excluded
from the shared Breakaway distribution; observed penalty symbols may extend beyond the generic
baseline's variants. The preceding special-teams change also corrected kick-mean tests to condition
on numeric cells because the engine rerolls penalty results.

## Explicit modeling defaults

The saved 1983 descriptions contain no explicit offensive clock-stop or fair catch annotations.
They do record illegal kickoffs using the penalty abbreviation `Kickoff OOB`; the adapter now
recognizes that as an actual OB result rather than a generic foul. They
also contain no recorded field-goal blocks or special snap/interception-return fumbles. Missing
season-wide annotations now trigger conservative modeling defaults rather than disabling those
mechanisms. These are estimates; a zero observed count does not prove that the event never occurred.

| Missing annotation | Initial modeling target |
|---|---:|
| Line Plunge clock stop | 1% |
| Off Tackle clock stop | 2% |
| End Run clock stop | 15% |
| Draw clock stop | 2% |
| Screen clock stop | 10% |
| Short Pass clock stop | 2% |
| Medium Pass clock stop | 5% |
| Long Pass clock stop | 6% |
| T/E S/L clock stop | 12% |
| QT numeric clock stop | 2.5% |
| Breakaway clock stop | 2% |
| Punt fair catch | 25% of chart mass |
| Kickoff out of bounds | 1% of chart mass |
| Field-goal block | 2% of chart mass |
| Field-goal snap fumble | 0.5% of chart mass |
| Punt snap fumble | 0.5% of chart mass |
| Interception-return fumble | 1% of chart mass |

Physical chart rows quantize these targets. Rare modeled mechanisms retain at least one eligible
row. Existing source observations take precedence; the fallback is selected from season-wide
coverage rather than a single team's small sample. Both the selected feature names and the default
rates appear in `generation-manifest.json`. Actual 2024 annotations preserve its observed clock
stops, fair catches, illegal kickoffs, interception-return fumbles, and supplied field-goal blocks.
Its missing special snap-fumble annotations use the corresponding defaults.

These defaults require further source validation and sensitivity assessment. They restore playable
mechanisms without pretending to recover historical events. Special-team foul exposure also has
separate fallback profiles, described in the generator guide.

## Differences that are not missing engine features

- Literal run touchdowns are forbidden. Numeric gains and B results score through field position.
- Numeric kickoff and punt returns can score; their charts do not need literal TD cells.
- Interception returns can score numerically, although sparse literal pick-six TD cells occur in
  the developer set. A source touchdown flag is not enough to justify an unconditional TD cell.
- The calibrated offense can have no direct INT cells while defense supplies interceptions.
  The combined play/formation matrix and full-game turnover rates assess the actual risk.
- The defensive tactical template has a different pattern of numeric overrides, incompletions,
  QT, and TD holes. The audit reports those differences; copying private reference cells would not
  establish the right source-derived team strength.
- A field-goal numeric threshold below the attempted distance supplies an ordinary miss, so a
  separate NG cell is not required.

## Matched engine assessment

The final matched assessment uses the actual 224-game 1983 regular-season schedule, eight seeds per
chart set and policy. Hard-vs-Hard and legacy balanced decisions are evaluated separately. The
generated side was rerun after the final corrections/profile, with the same seeds as the developer
side. The comparison covers 7,168 full games, all completed. The balanced policy here is the existing
situation-aware auto AI; it is not the removed no-coaching difficulty. No standings were saved.

| Per-team metric | Developer Hard | Generated Hard | Developer balanced | Generated balanced |
|---|---:|---:|---:|---:|
| Completion rate | 62.41% | 61.30% | 66.74% | 58.29% |
| Passing yards / attempt | 5.96 | 7.38 | 5.96 | 7.08 |
| Rushing yards / attempt | 4.11 | 3.94 | 4.21 | 3.97 |
| Sacks / team-game | 1.14 | 1.59 | 1.37 | 2.07 |
| Turnovers / team-game | 1.98 | 1.45 | 1.73 | 1.91 |
| Plays / team-game | 58.49 | 60.81 | 56.04 | 58.58 |
| Yards / team-game | 288.91 | 350.72 | 266.66 | 295.30 |
| Points / team-game | 19.32 | 24.32 | 17.13 | 20.63 |

A preliminary pilot identified completion and rushing-efficiency drift, so the 1983 profile changed from
-0.05 to -0.06 completion adjustment and from 1.00 to 1.025 rushing-yard multiplier. Interception
and pressure adjustments remain -0.07, and the passing-yard multiplier remains 1.55. The 2024
profile remains +0.02/-0.06/-0.02/1.30/1.00 for completion/interception/pressure/pass/run.

Fresh 64-season training runs on the final charts replayed the actual schedules. Every 1983 team
supplied 1,024 games and every 2024 team supplied 1,088. All five configured training tolerances
passed in both seasons; no tolerance was widened. Percentages below are resolved engine rates.

| Metric | 1983 actual | 1983 training | 2024 actual | 2024 training | Tolerance |
|---|---:|---:|---:|---:|---:|
| Completion | 56.90% | 58.31% | 65.29% | 65.81% | 1.5 percentage points |
| Interceptions / attempt | 4.41% | 3.92% | 2.17% | 2.79% | 1.0 percentage point |
| Sacks / dropback | 7.96% | 7.14% | 6.87% | 6.73% | 1.0 percentage point |
| Passing yards / attempt | 7.18 | 7.07 | 7.13 | 7.10 | 0.25 yards |
| Rushing yards / attempt | 4.09 | 3.96 | 4.44 | 4.30 | 0.15 yards |

The training policy is the generic situation-aware auto AI, without Hard chart-strength selection.
Its scoring and volume remain diagnostics: 1983 produced 20.64 points and 58.52 plays per team-game;
2024 produced 19.47 points and 57.60 plays. Passing five efficiency tolerances does not establish
historical scoring, pace, standings, or strategy-independent accuracy. Existing fourth-down/field-
goal coaching limitations remain tracked in [AI-024](issues/AI/AI-024.md).

The supplementary generated-schedule AI audit completed 448/448 games, reconciling 61,834 calls
across both policies. It covered 113 scoring-penalty choices, ten QB-scramble touchdown accounting
checks, 10,611 incompletions, and 491 fumbles at the spot. Its one advisory was legacy balanced
Screen on third-and-11+: 19/35 calls, three distinct calls, longest comparable streak three. Screen
was behind Medium and Long in conditional chart yardage, so this remains a coaching observation
under [AI-003](issues/AI/AI-003.md), not a reason to cap frequencies or alter charts. No Hard group
triggered the concentration advisory.

The same audit recorded 258 finalized punt penalty calls and 23 finalized field-goal penalty calls.
These are observed engine events, not merely proof that penalty text exists in a CSV. The call audit
does not enumerate automatic kickoff/return decisions, so these counts are not the full special-
teams penalty total.

The final 256-season held-out 1983 Hard run completed all 57,344 actual-schedule regular-season
games, supplying 4,096 team-games per team. It produced 61.22% completions, 7.39 passing yards per
attempt, 3.97 rushing yards per attempt, 1.95% interceptions, 4.09% sacks per dropback, 24.50 points,
351.51 yards, 60.80 plays, and 1.42 turnovers per team-game. These Hard rates differ materially
from the chart-focused targets; completion, sacks, and interceptions do not pass the training
tolerances under this policy. This is a disclosed calibration limitation, not a second successful
statistical fit. Historical 1983 scoring was 21.83 points and turnover volume was 2.49 per team-game.

The renewed 2024 held-out Hard assessment also completed all 256 seasons: 69,632 regular-season
games and 4,352 games per team. It produced 65.07% completions, 7.81 passing yards per attempt,
4.20 rushing yards per attempt, 1.13% interceptions, 4.93% sacks per dropback, 24.30 points,
371.29 yards, 60.95 plays, and 0.87 turnovers per team-game. Actual 2024 scoring, yardage, and
turnovers were 22.91, 337.42, and 1.15 respectively. The five training tolerances also do not all
hold under Hard for this season; both policies and the discrepancies must remain visible.

The focused historical-schedule Hard sanity runs completed 224 regular-season plus nine postseason
games for 1983 and 272 plus thirteen for 2024, with no tied playoff finals. The verified final files
are promoted to `seasons/1983-generated` and `seasons/2024`. Regeneration from the saved profiles
reproduces all 180 chart CSV files byte for byte. The complete core suite passes 6,394 tests with
eight existing skips for unavailable local test data; focused generator/audit, documentation,
tracker, Ruff, and whitespace checks pass. This is generator validation, not a new claim that the
entire push/release regression checklist has run.

## Remaining measured differences

No additional missing engine mechanism was found in the final feature review. The generated and
developer sets are nevertheless different models, and several differences remain material:

- Run B probability is lower in the generated set, while ordinary numeric run gains can extend
  farther within the 18-yard limit. For example, league End Run B mass is 2.35% versus 10.12% in
  the developer set. Their combined resolved rushing efficiency is measured above.
- Generated Long Pass has 56.30% primary incomplete mass versus 41.40% in the developer set, but
  its offense has no direct INT/TD cells and defense supplies different overrides. Isolated BLACK
  rates therefore do not measure combined completion probability.
- Primary Long Pass foul mass is 5.59% versus 12.62% in the reference; Punt foul mass is 5.29%
  versus 10.65%. Presence is fixed, but equal historical penalty frequency is not established.
- Conditional QT fumble exposure is 13.94% versus 7.57%; overall turnover volume remains below
  actual under Hard. Changing that one secondary column to match the reference would not by
  itself establish the correct whole-game turnover rate.
- Historical source pass-depth allocation is heuristic and missing-annotation defaults are
  estimates. More simulations cannot recover source details that were never recorded.

These differences are retained in the audit and DATA-011 calibration evidence. They should not be
silently converted into copied reference cells or hidden by claims of chart equivalence.

## Repeatable operator check

Both PBP generators run the structural gate automatically. To compare a candidate to a locally
installed reference set, write the detailed report into ignored storage:

```sh
python3 -m paydirt.chart_audit \
  --season-dir /path/to/generated-season \
  --reference /path/to/local-reference-season \
  --output .ai-audits/chart-generation/comparison.json
```

Inspect errors, coverage advisories, missing reference feature families, and combined primary rates.
A missing reference family is evidence to review rather than a command to duplicate that symbol.
Then run the historical-schedule engine pilot, inspect finalized penalties and turnovers, and use
the [generation workflow](../chart-generation-workflow.md) for numerical calibration.

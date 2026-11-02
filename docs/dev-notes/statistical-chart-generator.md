# Statistical Paydirt Chart Generator

**Status:** Implemented experimental development tool, November 1, 2026.

This note records the investigation, design, validation, and remaining limits of the
statistical chart generator. The maintained command reference is
[Chart generation and Excel import](../chart-generator.md). This development note does
not define a stable public data model.

## Objective

The generator explores whether offense, defense, and special-teams charts can be
reconstructed from a team's full-season statistics. Its practical goals are:

1. Produce CSV files accepted by the existing Paydirt chart loader.
2. Preserve the real probability represented by chart rolls 10 through 39.
3. Generate a useful estimate from ordinary season totals.
4. Accept classified play outcomes when full play-by-play analysis is available.
5. Support repeatable original-versus-generated chart comparisons.

The implementation is in [`paydirt/chart_generator.py`](../../paydirt/chart_generator.py),
with the command entry point at [`generate_charts.py`](../../generate_charts.py).

## Investigation Result

The historical workbook templates examined during development contain formulas that
summarize or audit chart entries after they have been entered. They do not contain a
formula that converts team season totals into complete charts.

Aggregate season totals are insufficient for exact reconstruction. Passing attempts,
completions, yards, touchdowns, interceptions, and sacks do not reveal how the chart
maker divided plays among Screen, Short, Medium, Long, and Tight End columns. The same
loss occurs for run direction, designed draws, breakaways, field-goal distance, defense
formation effects, and several symbolic outcomes.

This means two separate generation modes are useful:

- **Aggregate estimation:** construct a calibrated chart from season totals.
- **Empirical reconstruction:** quantize already classified play outcomes onto chart rows.

An exact historical reconstruction requires the second mode plus consistent judgment for
plays whose source descriptions do not identify depth, route, design, or coverage.

## Reference Approach: Data-Driven Football

The archived [Data-Driven Football design process](https://web.archive.org/web/20250524072210/http://www.datadrivenfootball.com/designprocess.html)
is a useful reference for the level of source data and validation used by a commercial
chart maker. Its published process described four stages:

1. Parse every official regular-season play-by-play gamebook into a database, review every
   database record, and watch video of every play to verify the gamebook and record details
   such as defensive alignment.
2. Analyze the confirmed season data with database and statistical software, then reconcile
   the computed values back to the gamebooks.
3. Map outcomes and probabilities to team charts with a combination of software and manual
   judgment.
4. Simulate at least 100 seasons and supplement those results with head-to-head play testing.

That process guides the direction of this tool. The empirical input path supports already
classified play outcomes, the generator maps requested rates with actual chart-roll
probabilities, and the replay workflow compares many identical seeds rather than one game.
The current aggregate mode remains a smaller experiment: it starts from season totals, does
not review every source play or video, does not infer defensive alignments, and has not yet
completed a 100-season validation set. The reference therefore defines a useful target for
future empirical reconstruction and quality assurance rather than evidence that aggregate
statistics can reproduce the original charts exactly.

## Probability Model

The offense and special-teams charts use rows 10 through 39. These rows represent all 216
ordered outcomes of three six-sided dice, grouped by the first two dice as a two-digit row
number. Rows therefore have unequal weights.

The generator obtains those weights from `chart_roll_weights()` and uses them for:

- symbolic result rates;
- weighted numeric means;
- empirical outcome quantization;
- extra-point misses; and
- validation helpers.

A requested event rate is approximated with whole chart rows. The result is the closest
reachable dice mass, rather than treating each of the 30 visible rows as equally likely.

## Input Model

`TeamSeasonStats` contains:

- season and team metadata;
- offense rushing and passing totals;
- defense rushing and passing totals; and
- kickoff, return, punt, field-goal, and extra-point totals;
- optional field-goal attempts and makes by statistical kick distance; and
- offensive fumbles lost for weighted recovery calibration.

The command reads this structure from JSON:

```sh
python generate_charts.py team-stats.json \
  --output seasons/1983-gen/Eagles \
  --seed 8306
```

The seed controls where equivalent outcomes are placed. Each team and column receives a
SHA-256-derived child seed, so adding or changing one column does not reshuffle unrelated
columns.

## Offense Generation

Rushing columns start with a normal-like yardage distribution based on team rushing
average. Style offsets and spreads distinguish Line Plunge, Off Tackle, End Run, and Draw.
The generator then allocates fumbles, breakaways, and penalty results by weighted rate and
readjusts the remaining numeric cells toward the target mean.

Passing columns derive a yards-per-completion baseline and apply separate completion and
yardage profiles for Screen, Short, Medium, Long, and Tight End passes. Incompletions,
interceptions, touchdowns, quarterback pressure, and penalties receive disjoint weighted rows.
A subset-sum allocator chooses the closest achievable dice mass for each requested rate. This
prevents later pressure or penalty placement from overwriting earlier outcome classes.

Breakaway and quarterback-time columns use rushing efficiency and sack-loss information.
These columns remain estimates unless classified outcomes are supplied.

## Defense Generation

Defense generation starts from a complete six-formation tactical template. Allowed rushing
and passing efficiency produce continuous target shifts. Whole-number shifts apply to every
numeric modifier, and fractional shifts are distributed across eligible sub-rows using the
actual red/green defensive dice weights. Interception and sack rates adjust a small number of
disruption outcomes.

This weighted calibration preserves close efficiency differences that the original integer
rounding discarded. It also keeps the formation and sub-row structure intact. It is not an
exact reconstruction of a historical defense chart because aggregate defense totals do not
identify which formation or offensive-play intersection produced each result.

## Special-Teams Generation

Punt, kickoff, and return columns use the corresponding season averages and deterministic
spreads. Blocked-punt and extra-point miss rates are converted to weighted chart rows.
Field-goal totals without attempts by distance produce a generic fallback column. When exact
attempts and makes by statistical kick distance are supplied, the generator pools noisy buckets
into a nonincreasing success curve and maps it to maximum-distance chart results. Offensive
fumbles lost similarly select the closest reachable weighted recovery interval instead of using
a fixed range for every team.

Special teams were the strongest aggregate reconstruction in the 1983 comparison. Across
all 28 teams, generated punt averages had a 0.19-yard mean absolute error and 0.99
correlation with the original chart averages. Kickoff-return and punt-return correlations
were 0.79 and 0.88 respectively.

## Classified Play Outcomes

`EmpiricalChartData` accepts a source-neutral CSV:

```csv
unit,chart,result
offense,line_plunge,3
offense,line_plunge,F
offense,screen,BLACK
offense,screen,12
special_teams,punt,42
```

Each supplied column replaces its aggregate estimate. Inputs are rejected when their result
symbols are outside the supported offense or special-teams grammar. Marked numeric outcomes such
as `4*` retain their out-of-bounds semantics and observed frequency; unmarked numeric outcomes
are assigned as weighted quantiles. Columns absent from the empirical input continue to use
aggregate generation.

Source-specific parsing deliberately occurs before this boundary. A gamebook, statistical
site export, or film-review process must decide the Paydirt category and normalized result.

## Generated 1983 Comparison Set

A local comparison set was generated under `seasons/1983-gen/` with seed `8306`. It
contains all 28 team directories, copied roster metadata, `1983.yaml`, and a generation
manifest. The directory is ignored by Git and must remain local because historical chart
sets and derived audit artifacts are not distributed with the project.

Season-rule loading accepts a suffixed directory such as `1983-gen` and reads the base-year
file `1983.yaml`. Auto-game path resolution also accepts absolute or repository-relative
team directories. This permits commands such as:

```sh
python -m paydirt --auto \
  seasons/1983/Eagles \
  seasons/1983-gen/Cowboys
```

The normal team picker continues to list numeric season directories only.

## Initial Play-Test Evidence

A first paired audit ran the standard 14 matchups once with the same seed for each original
and generated pair. Per-team cohort results were:

| Metric | Original charts | Generated charts |
|---|---:|---:|
| Points | 16.89 | 16.29 |
| Total yards | 268.64 | 256.71 |
| Turnovers | 1.89 | 1.75 |

Only 5 of 14 winner orientations matched. A single paired seed is not a useful expectation
of identical outcomes: the first changed result alters field position, clock, AI choices,
and subsequent random-number consumption. Confidence should come from distributions across
many seeds.

## DATA-004 2024 Calibration Experiment

The initial aggregate 2024 generation produced only 13 distinct `defense.csv` files for 32
teams. Replacing integer efficiency rounding with weighted fractional sub-row shifts produced
32 distinct defense charts. A synthetic regression confirms that nearby allowed-yardage rates
now produce ordered, distinct chart strength. A separate scaling test confirms that 16-game and
17-game counting totals produce identical charts when their rates are unchanged.

The first same-seed replay became slightly worse after the defense-only change. That result led
to a second audit, which found that aggregate offense generation allowed each symbolic outcome
pass to overwrite rows assigned by earlier passes. Touchdowns and quarterback pressure could
disappear entirely, and a greedy row selector often missed a closer dice-mass combination. The
final fix reserves only remaining numeric rows for each outcome class and finds the nearest
achievable probability with a bounded subset-sum search.

Five paired Hard-vs-Hard seasons used identical schedules and base seeds for the original and
fixed generators. Each side of the comparison covered 1,360 regular-season games plus its
postseasons. The averages were:

| Metric | Original aggregate generator | DATA-004 fixes |
|---|---:|---:|
| Distinct defense charts | 13 / 32 | 32 / 32 |
| Mean absolute error in wins | 3.71 | 2.39 |
| RMSE in wins | 4.57 | 3.01 |
| Win correlation | 0.03 | 0.62 |
| Actual playoff-team overlap | 6.0 / 14 | 9.4 / 14 |
| Points-for correlation | -0.03 | 0.93 |
| Points-against correlation | 0.50 | 0.68 |
| Point-differential correlation | 0.30 | 0.90 |
| Kansas City average wins | 5.6 | 9.2 |

The fixed generator is substantially better at preserving team scoring and season strength,
although Kansas City still falls well short of its actual 15 wins. Philadelphia won the
2024 season championship; Kansas City was the runner-up. Aggregate charts remain estimates. Classified play-by-play
distributions and broader validation are still needed for closer team-specific reconstruction.

The same five schedules and seeds were replayed at each coaching difficulty. A temporary
`none` experiment also used a fixed play population and uniform defensive formations to test
whether removing coaching improved chart evaluation. It did not improve record fit and was
removed from the code after the comparison. Its saved figures below remain historical evidence,
not a supported difficulty mode.

| Metric | Hard-vs-Hard | Medium-vs-Medium | Easy-vs-Easy | None-vs-None |
|---|---:|---:|---:|---:|
| Mean absolute error in wins | 2.39 | 2.38 | 2.39 | 2.61 |
| RMSE in wins | 3.01 | 2.93 | 3.03 | 3.22 |
| Mean per-season win correlation | 0.62 | 0.63 | 0.59 | 0.54 |
| Actual playoff-team overlap | 9.4 / 14 | 10.0 / 14 | 9.6 / 14 | 8.4 / 14 |
| Correlation of five-seed team mean points for | 0.93 | 0.89 | 0.88 | 0.86 |
| Correlation of five-seed team mean points against | 0.68 | 0.75 | 0.62 | 0.60 |
| Correlation of five-seed team mean point differential | 0.90 | 0.88 | 0.85 | 0.83 |
| Kansas City average wins | 9.2 | 9.8 | 8.8 | 7.8 |
| Philadelphia average wins | 11.0 | 12.8 | 11.0 | 11.0 |

Easy uses generic situational play calling and conservative aggression, without Hard chart
analysis or Medium's team-strength run/pass bias. The removed neutral experiment completed all
five seasons and retained meaningful team signal, but it was less accurate than all three
coached modes on wins, playoff membership, and scoring relationships. The result supports using
existing coaching modes plus direct engine observations for calibration rather than maintaining
a separate no-coaching difficulty.

## November 1 Review: Historical Fit and Remaining Defects

This historical review reconciled the saved five-seed results for Hard, Medium, Easy, and the removed neutral experiment with
the local actual regular-season schedule. Each report contains 272 regular-season games,
32 teams with 17 games apiece, matching league points-for/points-against totals, and 13
postseason games. This checks the saved summaries; it does not rerun the 20 seasons or
establish play-level statistical correctness. The local replay script uses the actual
regular-season matchups and simplified playoff tiebreakers (winning percentage, point
differential, points scored, team abbreviation), not the complete NFL tiebreaking procedure.

### Ranking accuracy is not scoring calibration

The scoring correlations above correlate each team's **average over five simulations** with
its historical total. The win correlations instead average five separate correlations.
For Hard, the mean individual-season points-for correlation is 0.844, versus 0.933 after
averaging team totals; the corresponding points-against values are 0.544 and 0.681.
Both summaries are useful, but averaging reduces simulation noise and the two definitions
must not be presented as the same statistic.

| Absolute scoring measure | Historical | Hard | Medium | Easy | None |
|---|---:|---:|---:|---:|---:|
| Points per team-game | 22.91 | 19.98 | 20.21 | 19.83 | 21.00 |
| MAE of five-seed team mean season points for | — | 50.1 | 47.2 | 53.8 | 40.0 |
| MAE of five-seed team mean season points against | — | 51.4 | 49.0 | 55.6 | 41.1 |

Hard preserves scoring order well while underproducing approximately 2.94 points per
team-game. The removed neutral experiment has weaker ranking and record accuracy but smaller
absolute scoring errors on these measures. Therefore the evidence supports a narrower claim that coached modes
improve record fit in this sample; it does not establish that they are uniformly better
calibrated. Five seeds also do not establish a meaningful Hard-versus-Medium advantage.

### Why Kansas City and playoff champions differ

Kansas City's historical regular-season totals were 385 points for and 326 against
(+59), with 15 wins. The five Hard replays average 316.8 for and 307.2 against (+9.6),
with 9.2 wins. There is a real scoring-model gap as well as a record gap.

The actual schedule also yields 11 wins and zero losses by eight points or fewer for
Kansas City, consistent with the [NFL's Week 16 account](https://fantasy-www.nfl.com/news/neil-reynolds-week-16-wrap-2024).
An aggregate chart retains neither the timing of those decisive plays nor a separately
estimated close-game skill. Regression away from that observed record is consequently
plausible; attributing all of it to luck, or all of it to a chart defect, is unsupported.
Static season rates also pool different opponents, game situations, and personnel usage.
They are not opponent-adjusted or week-specific estimates.

The championship for the 2024 season was Philadelphia's 40–22 win on February 9, 2025
([official gamebook](https://static.www.nfl.com/gamecenter/882c1e9c-dc59-11ef-8d24-59614ea9df0f.pdf)).
A playoff bracket compounds uncertainty: qualification, seeding, and several single-game
results all vary. For illustration, even a team with a 65% chance in each of three games
wins all three only 27.5% of the time. Five champions provide weak evidence for estimating
title probabilities. Evaluate playoff qualification and advancement distributions, and
report where the observed season falls within simulated ranges.

## November 1 Follow-up: Preserved Inputs and Engine Calibration

The temporary no-coaching difficulty was removed before this follow-up. The generator now:

- validates normalized empirical result symbols and preserves numeric `*`/`†` markers;
- accepts field-goal attempts and makes by statistical kick distance, applying a weighted
  monotonic success curve;
- uses supplied offensive fumbles lost to choose the weighted recovery range; and
- provides `EngineCalibrationObserver`, which pairs normal auto-game decisions and finalized
  engine results, then reports completions, passing attempts and yards, sacks, interceptions,
  fumbles lost, turnovers, play volume, scoring, and field-goal accuracy.

The same five Hard and Medium schedules and seeds were rerun after regeneration:

| Metric | Hard before | Hard after | Medium before | Medium after |
|---|---:|---:|---:|---:|
| Mean absolute error in wins | 2.39 | 2.36 | 2.38 | 2.34 |
| RMSE in wins | 3.01 | 2.91 | 2.93 | 2.89 |
| Mean per-season win correlation | 0.62 | 0.65 | 0.63 | 0.64 |
| Actual playoff-team overlap | 9.4 / 14 | 9.4 / 14 | 10.0 / 14 | 10.0 / 14 |
| Five-seed mean point-differential correlation | 0.90 | 0.92 | 0.88 | 0.91 |

The resolved engine report prevents those ranking improvements from being mistaken for complete
calibration. Across the five new Hard runs, field-goal accuracy averaged 83.03% versus 84.04%
historically, but completion rate was 59.13% versus 65.29%, passing yards per attempt were 5.07
versus 7.13, sacks were 0.95 versus 2.42 per team-game, and scoring was 20.49 versus 22.91 points
per team-game. Medium produced 84.73% field goals, 56.96% completions, 5.44 passing yards per
attempt, 1.57 sacks, and 20.91 points per team-game. The new inputs improve records modestly and
fix the identified information losses, while the offense-plus-defense passing model remains
underpowered and is still tracked by DATA-006.

### Concrete code findings

- **Empirical clock semantics were lost.** DATA-005 now preserves marked numeric outcomes and
  rejects unknown normalized symbols before generation. Written and loaded charts retain the
  marker that the engine parses as out of bounds.
- **Important supplied totals previously did not affect generation.** Field-goal distance
  results and fumble-loss rates now change the generated kick and recovery distributions. The
  aggregate longest-kick fallback remains available when distance buckets are unavailable.
- **Cell means are not resolved play means.** Numeric audits omit symbols and defense
  interactions. Passing generation separately allocates incompletions, interceptions,
  touchdowns, pressure, and penalties using different source denominators; actual completion,
  sack, turnover, and scoring rates require engine-level validation. A classified final gain
  also cannot simply be treated as an offense-only contribution without considering the
  defense adjustment that the engine will apply. The empirical boundary needs an explicit
  normalization contract. These calibration investigations are tracked in
  [DATA-006](issues/DATA/DATA-006.md).

The fixed defense template still encodes only a few efficiency/disruption dimensions.
Thirty-two unique files establish differentiation, not thirty-two accurate defenses.
Likewise, fixed offensive style profiles omit situational success, route/run mix, and
red-zone distributions. The removed neutral experiment also contained arbitrary play mix,
formation, and fourth-down choices, which is why direct engine metrics now serve as the
calibration control.

The archived DDF process was checked against the source and is accurately summarized above.
Its detailed play classification, film review, and repeated validation offer a stronger
methodological target. Simply running more seeds with unchanged biased charts reduces
Monte Carlo uncertainty; it does not recover missing inputs or correct the mapping.

### Review verification and follow-up

The focused generator/AI/audit/path/rules/documentation run passed 220 tests with three
existing missing-1972-rule skips in `test_season_rules.py`; these remain covered by open
[VAL-010](issues/VAL/VAL-010.md). Ruff passed. The tracker suite initially had one failure
because its summary counts had not been regenerated after DATA-004 closed. The review
regenerated that index while recording these findings. No production behavior or existing
test expectations were changed, and no full push regression was claimed.

DATA-004 remains closed for its demonstrated defense-compression and symbolic-allocation
fixes. DATA-005 is resolved in focused synthetic generation/loading coverage and awaits a
broader empirical play-test before closure. DATA-006 remains open because the new engine
report confirms that passing efficiency, sack frequency, fumble losses, play volume, and
scoring are still not jointly calibrated.

A second engine-calibration pass corrected the denominator error instead of adding a blind
completion boost: interceptions, pressure, and penalties are reserved first, then completions and
incompletions are allocated over the remaining pass-attempt mass. QB-time fumbles are calibrated
through the probability of reaching the secondary QB-time chart, and rushing fumbles use the full
supplied occurrence rate. Engine observations then set bounded offsets for the fixed defense
template's interception contribution, completed-pass yardage reductions, and the fraction of
QB-time results that become sacks. Aggregate inputs may also supply run/pass `out_of_bounds`
counts; those mark weighted numeric outcomes and preserve clock semantics without inventing a
rate when the source omits it.

The initial five-seed check was expanded to 256 Hard-vs-Hard seasons. Seeds begin at 202422,
advance by 10,000 to avoid overlapping game seeds, and cover 69,632 regular-season plus 3,328
postseason games:

| Engine metric | 2024 actual | Before engine calibration (5 seasons) | Calibrated charts (256 seasons) |
|---|---:|---:|---:|
| Completion rate | 65.29% | 59.13% | 65.28% |
| Passing yards / attempt | 7.13 | 5.07 | 6.53 |
| Sacks / team-game | 2.42 | 0.95 | 2.35 |
| Interception rate | 2.17% | 2.76% | 2.25% |
| Fumble losses / play | 0.70% | 0.25% | 0.66% |
| Turnovers / team-game | 1.15 | 1.01 | 1.11 |
| Plays / team-game | 62.15 | 59.97 | 59.02 |
| Points / team-game | 22.91 | 20.49 | 23.13 |
| Field-goal rate | 84.04% | 83.03% | 85.20% |
| Yards / team-game | 337.42 | 286.50 | 314.72 |

Across the 256 seasons, mean per-season win MAE was 2.37, mean win correlation was 0.62,
and mean playoff overlap was 9.25 of 14 teams. Correlating each team's 256-season mean with
actual 2024 results produced 0.76 for wins, 0.92 for points scored, and 0.66 for points allowed.
Kansas City averaged 8.80 wins and reached the playoffs in 41.0% of seasons; Philadelphia
averaged 12.09 wins and reached the playoffs in 93.8%.

The postseason produced 58 distinct AFC/NFC Super Bowl pairs and 20 champions. The leading
pairs were Baltimore–Detroit 39 times, Baltimore–Philadelphia 30, and Baltimore–Green Bay 27.
The actual Kansas City–Philadelphia pair did not occur: Kansas City won the AFC five times and
Philadelphia won the NFC 50 times, but never in the same season. Pair discovery was still rising
at the checkpoints—12, 22, 29, 42, and 58 distinct pairs after 16, 32, 64, 128, and 256
seasons—so 58 is the observed count rather than an estimate of every reachable pair.

This is useful negative evidence: matching engine event rates and scoring does not recover
team-specific situational distributions from aggregate totals. DATA-006 remains open for low
yardage and play volume, overstrong Baltimore outcomes, understrength Kansas City and Minnesota
outcomes, field-goal overperformance, and held-out validation.

Before tuning win totals, compare source and simulated play volume, possession count,
completion rate, yards per attempt, sacks, interceptions, fumbles lost, third-down and
red-zone success, and field-goal success by distance. Retain game summaries and per-call
evidence in ignored reports. Use stable independent per-team play-selection streams and
separate engine seeds; the local replay currently uses lazy AI stream initialization,
unlike the public audit harness. Then expand the seed count with uncertainty intervals
and evaluate held-out teams/seasons. Vary chart-generation seeds separately to measure
quantization sensitivity rather than confusing it with gameplay randomness.

## 1983 Full Play-by-Play Reconstruction Experiment

The complete 1983 regular season was parsed from locally saved Pro Football Reference boxscore
HTML and generated as a third local comparison set, `seasons/1983-pbp/`. The source adapter is
implemented in [`paydirt/pfr_play_by_play.py`](../../paydirt/pfr_play_by_play.py), with the batch
entry point at [`generate_pfr_charts.py`](../../generate_pfr_charts.py). The archived
[Data-Driven Football design process](https://web.archive.org/web/20250524072210/http://www.datadrivenfootball.com/designprocess.html)
remains the methodological reference: full play-by-play supplies the empirical database, while
film review and manual judgment would be needed to recover omitted alignment and play-design data.

The local generation processed 224 games and 39,354 source rows. It produced 41,070 normalized
chart outcomes, retained 775 non-nullified field-goal attempts and 692 fumbles, and used aggregate
fallbacks for 28 sparse columns across the 28 teams. A source audit found 13 accepted-penalty field
goals explicitly marked `no play`; a failing regression was added before excluding those kicks.
The manifest also records 16,141 pass-family heuristic decisions because historical PFR text
usually gives the final gain but not route depth.

### Direct comparison with the developer charts

The empirical path did not reproduce the developer charts cell for cell. Its offense exact-cell
rate was 4.98%, compared with 6.66% for the initial aggregate generator, while special teams rose
to 3.31% from 2.50%. Defense remained identical to current aggregate generation because PFR text
does not identify the defensive formations required by the chart.

| Developer-chart column | Initial aggregate MAE | Play-by-play MAE | Initial correlation | Play-by-play correlation |
|---|---:|---:|---:|---:|
| Line plunge | 0.356 | 0.484 | 0.651 | 0.546 |
| Off tackle | 0.370 | 0.456 | 0.449 | 0.319 |
| End run | 0.603 | 1.355 | 0.306 | 0.129 |
| Screen | 1.305 | 1.482 | 0.283 | 0.073 |
| Short pass | 1.284 | 1.249 | -0.259 | -0.009 |
| Medium pass | 1.409 | 1.316 | 0.158 | 0.228 |
| Long pass | 4.956 | 5.681 | 0.066 | -0.032 |
| QB time | 2.113 | 1.239 | 0.571 | 0.875 |

Play by play materially improved QB-time reconstruction and slightly improved short- and
medium-pass mean error. It worsened the run columns and did not create strong team-by-team pass
correlations. Observed final gain is insufficient to determine pass depth, and a historical chart
can encode play selection and defensive interaction differently from a raw final-outcome sample.

### Matched 100-season engine comparison

Four chart sets replayed the actual 224-game 1983 schedule 100 times with Hard versus Hard and the
same 100 base seeds. This covered 89,600 regular-season games. The playoff-overlap measure applies
the project's deterministic division-winner and wildcard ranking to the simulated standings; it
does not reproduce every historical NFL tiebreaker.

| Chart set | Win MAE / season | Win correlation / season | Historical playoff overlap / 10 | Team-mean win correlation | Team-mean point-differential correlation |
|---|---:|---:|---:|---:|---:|
| Developer charts | 1.907 | 0.691 | 6.19 | 0.820 | 0.831 |
| Initial aggregate | 3.583 | -0.004 | 3.72 | -0.004 | 0.036 |
| Current aggregate | 2.101 | 0.516 | 5.44 | 0.768 | 0.792 |
| Play by play | 2.152 | 0.514 | 5.11 | 0.724 | 0.782 |

| League metric | Actual 1983 | Developer | Current aggregate | Play by play |
|---|---:|---:|---:|---:|
| Completion rate | 56.90% | 62.46% | 59.75% | 62.95% |
| Passing yards / attempt | 7.18 | 5.98 | 6.63 | 6.80 |
| Sack rate | 7.96% | 3.38% | 7.73% | 6.06% |
| Interception rate | 4.41% | 3.33% | 3.91% | 2.18% |
| Plays / team-game | 65.79 | 58.44 | 59.18 | 59.77 |
| Yards / team-game | 334.36 | 289.11 | 289.07 | 341.23 |
| Points / team-game | 21.83 | 19.33 | 19.51 | 25.47 |
| Turnovers / team-game | 2.49 | 2.00 | 1.22 | 1.31 |
| Field-goal rate | 71.47% | 54.18% | 59.30% | 62.54% |

The experiment supports adding play-by-play analysis, but the first implementation is not a
replacement for the developer charts and does not yet beat the calibrated aggregate generator
on standings. It recovers total yardage and passing gain more closely, then overproduces
completions and scoring while underproducing interceptions and turnovers. Final observed offense
outcomes already contain the effect of the historical opponent; applying a separately generated
defense in the engine can apply that interaction a second time. The next empirical design should
separate offense and defense contributions, use reviewed pass depth and alignment where available,
and calibrate the combined engine result rather than quantizing raw final outcomes directly.

DATA-005 is closed because marked numeric outcomes now survive a full empirical generation and
100-season engine play test. DATA-006 remains open: play by play changes which calibration errors
appear, but does not resolve volume, turnovers, scoring, or team-strength fidelity.

## Opponent-Adjusted Play-by-Play Follow-up

Raw play outcomes cannot identify offense and defense independently because every snap contains
both. The implemented follow-up fits a regularized league-wide additive model for each empirical
chart and resolved metric:

```text
observed outcome = league baseline + offense effect + defense effect
```

Offense and defense effects are centered on zero, so an offense-only prediction describes that
team against a league-average defense. Ridge pseudo-counts partially pool small samples toward
the league mean. The source adapter now retains the opponent on every offensive outcome, adjusts
resolved offense samples to average defense, and converts fitted defense residuals into the
rushing yards per attempt, passing yards per attempt, completion, interception, and sack rates
accepted by the existing defense generator. This is an identifiable convention for relative
effects; it does not claim that either side was observed in isolation.

Two engine-boundary corrections were also required. Pass incompletions, interceptions, pressure,
and penalties retain the aggregate generator's engine-calibrated baseline while empirical data
supplies resolved gains, touchdowns, fumbles, and out-of-bounds markers. Empirical quantization
now allocates combined probability to result families before choosing variants. Previously, rare
variants such as `F + 3`, `F + 4`, and different interception depths were each rounded separately;
a synthetic 9.09% fumble family collapsed to 0.46%. The family-level implementation preserves
the combined rate. Optional command-line offsets support later engine calibration without baking
the 1983 pilot into defaults.

### Matched 100-season result

The accepted neutral set, `seasons/1983-pbp-joint-final/`, replayed the same 100 Hard-versus-Hard
seeds as the earlier comparison.

| Chart set | Win MAE / season | Win correlation / season | Playoff overlap / 10 | Team-mean win correlation | Team-mean point-differential correlation |
|---|---:|---:|---:|---:|---:|
| Developer charts | 1.907 | 0.691 | 6.19 | 0.820 | 0.831 |
| Current aggregate | 2.101 | 0.516 | 5.44 | 0.768 | 0.792 |
| Raw play by play | 2.152 | 0.514 | 5.11 | 0.724 | 0.782 |
| Opponent-adjusted play by play | 2.070 | 0.513 | 6.08 | 0.767 | 0.866 |

| League metric | Actual 1983 | Raw play by play | Opponent-adjusted |
|---|---:|---:|---:|
| Completion rate | 56.90% | 62.95% | 59.59% |
| Passing yards / attempt | 7.18 | 6.80 | 5.91 |
| Sack rate | 7.96% | 6.06% | 8.72% |
| Interception rate | 4.41% | 2.18% | 3.83% |
| Plays / team-game | 65.79 | 59.77 | 59.06 |
| Yards / team-game | 334.36 | 341.23 | 301.28 |
| Points / team-game | 21.83 | 25.47 | 22.69 |
| Turnovers / team-game | 2.49 | 1.31 | 2.03 |
| Field-goal rate | 71.47% | 62.54% | 60.93% |

The joint model materially improved relative team strength, playoff selection, scoring, and
turnovers. It also exposed a tradeoff: using the engine-calibrated pass-event baseline reduced
passing gain and total yardage too far. A 16-season pilot with fitted completion, interception,
pressure, and yardage offsets increased passing gain but raised scoring to 24.15 and reduced
team-mean win correlation to .655, so those season-specific offsets were rejected.

A separate 32-season run included all 7,168 regular-season games and 288 postseason games. It
produced 20 distinct Super Bowl pairs and 11 champions. Raiders–Redskins, the historical matchup,
was the most common pair at 7/32; it appeared 4/32 with the raw empirical charts. Washington won
eight championships and the Raiders won three. All playoff games completed without a tied final.

This is the accepted stopping point for the current extractor work. DATA-006 remains open for low
play volume and yardage, field-goal underperformance, residual completion and turnover error, and
held-out validation. Further numerical tuning should use another season or held-out teams rather
than optimizing the complete 1983 sample.

## Recommended Validation

For every selected matchup, run both chart sets across the same seed list and compare:

- mean and median score;
- score and yardage distributions;
- rushing and passing yardage;
- turnovers and sacks;
- win, loss, and tie rates;
- play-selection distributions;
- team rankings over a generated schedule; and
- sensitivity to home/away reversal.

Use enough seeds to report confidence intervals. Investigate systematic differences by chart
column before adjusting formulas. Matching one historical score or one seeded simulation is
not evidence of calibration.

## Known Limits

- Aggregate passing totals cannot recover team-specific play-category shapes.
- Run direction and designed-play labels are often absent from historical descriptions.
- The defense template is calibrated by unit efficiency, not reconstructed by formation.
- Field-goal generation needs attempt distance for an exact survival curve.
- Penalty and fumble conventions may differ from the original chart designer's rules.
- A stable generator seed makes output reproducible but does not make generated and original
  games consume random values identically.

## Next Work

1. Add a reusable multi-seed chart-set comparison runner.
2. Produce per-team distribution and ranking reports.
3. Normalize a complete season of play-by-play into empirical chart categories.
4. Compare empirical reconstruction with both aggregate generation and original charts.
5. Tune formulas only from training teams, then evaluate held-out teams to avoid fitting the
   complete historical set directly.

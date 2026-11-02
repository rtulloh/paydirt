# Chart Generation and Excel Import

[Documentation index](README.md) · [Seasons and file formats](seasons.md)

Paydirt has two separate chart tools:

- [`generate_charts.py`](../generate_charts.py) creates a new statistical estimate from
  normalized season totals and optional classified play outcomes.
- [`extract_charts.py`](../extract_charts.py) converts an existing formatted Excel chart.

Both write the same game CSV format. Generate into a staging directory because existing
files are overwritten.

## Generate a Statistical Chart

The statistical generator uses the real chart dice distribution: rows 10 through 39
represent 216 equally likely three-die combinations with unequal row weights. Season rates
set symbolic outcome frequency and numeric strength. Symbolic outcome classes reserve distinct
rows, and a subset-sum allocator chooses the closest available dice probability without allowing
later classes to overwrite earlier ones. A stable seed changes where equivalent results appear
without changing the inputs.

Aggregate totals provide a fallback estimate when complete play-by-play is unavailable. They
do not uniquely determine an original chart. For example, one passing total does not reveal
which attempts were screens, short passes, medium passes, long passes, or tight-end passes.
When a complete, suitable play-by-play source is available, use classified full-season outcomes
as the primary input and retain aggregate totals for calibration and sparse-column fallback.

Create a JSON file such as `team-stats.json`:

```json
{
  "season": 2026,
  "team_name": "Example Foxes",
  "short_name": "FOX '26",
  "offense": {
    "rushing": {
      "attempts": 480, "yards": 2160, "touchdowns": 18,
      "fumbles": 12, "fumbles_lost": 6, "out_of_bounds": 38
    },
    "passing": {
      "attempts": 520, "completions": 338, "yards": 4056,
      "touchdowns": 30, "interceptions": 12, "sacks": 32, "sack_yards": 220,
      "fumbles": 4, "fumbles_lost": 2, "out_of_bounds": 66
    }
  },
  "defense": {
    "rushing": {"attempts": 440, "yards": 1760, "touchdowns": 12},
    "passing": {
      "attempts": 560, "completions": 336, "yards": 3920,
      "touchdowns": 24, "interceptions": 16, "sacks": 40, "sack_yards": 280
    }
  },
  "special_teams": {
    "kickoff_return": {"attempts": 54, "yards": 1188},
    "punt": {"attempts": 72, "yards": 3024, "blocked": 1},
    "punt_return": {"attempts": 38, "yards": 380},
    "interception_return": {"attempts": 16, "yards": 192},
    "field_goal": {"attempts": 32, "made": 25, "long": 52},
    "field_goal_by_distance": [
      {"distance": 30, "attempts": 10, "made": 9},
      {"distance": 45, "attempts": 12, "made": 9},
      {"distance": 55, "attempts": 10, "made": 7}
    ],
    "extra_point": {"attempts": 30, "made": 29}
  }
}
```

Run the generator from the repository root:

```sh
python generate_charts.py team-stats.json --output /path/to/staging/2026/Foxes
```

To keep a generated historical comparison set beside its source charts, use a suffixed season
directory such as `seasons/1983-gen/`, copy the base `1983.yaml` rules file into it, and invoke
auto games with the complete team paths. See [Seasons and team data](seasons.md#adding-a-season).

### Classified Full-Season Outcomes

For closer team-specific results, normalize play-by-play or reviewed film into a CSV with
`unit`, `chart`, and `result` columns:

```csv
unit,chart,result
offense,line_plunge,3
offense,line_plunge,F
offense,screen,BLACK
offense,screen,12
special_teams,punt,42
special_teams,punt,BK -10
```

Valid offense chart names are `line_plunge`, `off_tackle`, `end_run`, `draw`, `screen`,
`short_pass`, `medium_pass`, `long_pass`, `te_short_long`, `breakaway`, and `qb_time`.
Valid special-teams names are `kickoff`, `kickoff_return`, `punt`, `punt_return`,
`interception_return`, and `field_goal`.

Each supplied column replaces its aggregate estimate. Unspecified columns still use season
totals. When classified short, medium, or long passes are available without a separately
classified `te_short_long` sample, the generator builds that route column from the combined
observed pass outcomes. The generator validates every normalized result before generation,
preserves numeric out-of-bounds markers such as `4*`, approximates symbolic frequencies with
whole chart-row weights, and fills unmarked numeric rows from the observed yardage distribution.
Primary rushing columns cap direct numeric gains at 18 yards. For empirical columns, gains of
19 yards or more determine the rare `B` trigger frequency, while the separate Breakaway column
is learned from the full distribution of observed gains of 10 yards or more. Aggregate fallback
columns apply the same direct-gain cap to their modeled distribution. This keeps ordinary long
gains field-position aware and uses the two-stage chart mechanism for exceptional runs.

```sh
python generate_charts.py team-stats.json \
  --plays classified-plays.csv \
  --output /path/to/staging/2026/Foxes \
  --seed 8306
```

The input boundary is source neutral. A Pro-Football-Reference, Stathead, nflverse, official
gamebook, or film workflow must first decide which Paydirt play column and result each play
represents. Keep licensed or private source data outside the repository.

### Play-by-Play Source Policy

Use complete regular-season play-by-play whenever a suitable source is available. The source
adapter must retain opponent identity, accepted penalties, field-goal distance and result,
fumble-loss events, empirical out-of-bounds markers, and observed yardage, including the yardage
of scoring plays. For kickoff, kickoff-return, punt, punt-return, interception-return, and
field-goal charts, retain both accepted and declined non-offsetting fouls: a chart penalty cell
represents a called foul, and the engine decides whether the resulting penalty is accepted. Assign
the result relative to the chart owner (`OFF` for that team and `DEF` for its opponent). The
baseline generator does not translate a source touchdown flag directly into
a guaranteed chart `TD`. High numeric gains remain field-position aware and can score normally.
Aggregate-only generation is an explicit fallback for a season without complete play-by-play or
for empirical columns below the minimum sample threshold.

Chart creation uses two tools. The source generator produces a deterministic baseline from the
source evidence. [`tune_charts.py`](../tune_charts.py) measures candidates through multi-seed engine replays and
writes a calibration profile that the source generator applies on the next run. Use 64 complete
regular seasons for tuning, which produces 1,024 team-games in a 16-game season or 1,088 in a
17-game season. Validate the selected profile with 256 additional seasons and unused seeds. Match
completion, yardage, sacks, turnovers, play volume, and scoring together; matching isolated chart
averages is insufficient. Sparse literal `TD` cells, when required after numeric gains are
calibrated, belong to this second stage. Record the effective profile in
`generation-manifest.json`. See the [two-phase operator workflow](chart-generation-workflow.md) and the
[chart generator tuning tool](dev-notes/chart-generator-tuning-tool.md).

### Generate from Pro Football Reference Play by Play

[`generate_pfr_charts.py`](../generate_pfr_charts.py) provides a source adapter for saved
Pro Football Reference boxscore HTML. It parses the full play-by-play table, classifies each
regular-season result, enriches field-goal and fumble inputs, and then uses the same aggregate
and empirical generator described above.

```sh
python generate_pfr_charts.py \
  --html-dir /path/to/pfr-boxscores \
  --stats-dir /path/to/team-stat-json \
  --template-season /path/to/template-season \
  --team-map /path/to/pfr-team-map.json \
  --output /path/to/staging/1983-pbp \
  --audit-dir /path/to/local-audit \
  --through-date 19831219 \
  --calibration-profile /path/to/profile.json \
  --seed 8306
```

The team map is a JSON object from PFR abbreviations to template directory names. The command
writes a `generation-manifest.json` with source-row counts, classification diagnostics, per-team
field-goal and fumble counts, empirical outcomes used, and columns that fell back to aggregate
generation. The audit directory contains source rows for local review. Keep downloaded HTML,
audit rows, historical templates, and intermediate generated seasons local and ignored. A reviewed
final chart set may be published without those source materials under the publication policy below.

The adapter fits a league-wide additive model that separates relative offense and defense effects
under an explicit average-defense-zero constraint. Every offensive audit row therefore includes
its opponent. Offense outcomes are translated to a league-average defense, while fitted defense
residuals replace schedule-biased allowed rates before the defense template is generated. A ridge
pseudo-count, configurable with `--opponent-shrinkage`, partially pools small samples.

Pass event families use the aggregate generator's engine-calibrated baseline by default, while
empirical play by play supplies resolved yard distributions, scoring-play yardage, fumbles, and
clock-stop markers. Quantization preserves the combined mass of fumble, interception, penalty, and marked
numeric families before selecting individual variants. Optional replay-derived adjustments are
available as `--run-yard-multiplier`, `--pass-completion-adjustment`,
`--pass-interception-adjustment`, `--pass-pressure-adjustment`, and
`--pass-yard-multiplier`. Leave them neutral unless a matched multi-season engine replay justifies
a change, and record non-neutral values in the manifest.

Historical PFR descriptions usually identify run direction, sacks, turnovers, penalties, kicks,
and observed yardage, but usually omit pass depth and defensive alignment. The adapter therefore
uses a deterministic pass-family heuristic and estimates relative defense effects from matched
league-wide residuals rather than attempting to reconstruct unobserved formations.

### Generate from nflverse Play by Play

[`generate_nflverse_charts.py`](../generate_nflverse_charts.py) reads a regular-season nflverse
CSV or gzip-compressed CSV and feeds the same opponent-adjusted empirical pipeline. nflverse air
yards distinguish screens, short, medium, and long passes more directly than historical narrative
heuristics. Run gaps and locations select run columns; sacks also populate quarterback-time;
interceptions produce both pass results and return outcomes.

```sh
python generate_nflverse_charts.py \
  --pbp /path/to/play_by_play_2024.csv.gz \
  --stats-dir /path/to/2024-team-stat-json \
  --template-season /path/to/2024-template \
  --team-map /path/to/nflverse-team-map.json \
  --output /path/to/staging/2024 \
  --audit-dir /path/to/local-audit \
  --seed 8306
```

The command accepts the same opponent and pass calibration controls as the PFR adapter plus
`--run-yard-multiplier`. Leave all multipliers at `1.0` and rate adjustments at `0.0` until a
matched engine replay demonstrates a systematic boundary error. The manifest records source
coverage, diagnostics, fallback columns, and all calibration values.
A minimum sample threshold prevents a penalty-only or otherwise sparse empirical column from
replacing its aggregate fallback. Every special-teams family also has a deterministic fallback
penalty profile, so a resolved empirical sample cannot erase foul risk merely because no foul was
observed in that small sample. Observed special-teams penalties replace that fallback distribution
when present. Field-goal accuracy is calibrated only across numeric cells because the engine
rerolls penalty cells; accepted field goals marked `no play` are excluded from kick calibration.
Review the manifest, including `special_teams_penalties`, before using the charts.

The source approach is informed by the archived
[Data-Driven Football design process](https://web.archive.org/web/20250524072210/http://www.datadrivenfootball.com/designprocess.html),
which describes parsing every regular-season gamebook, reviewing every record, adding information
from video, and validating with at least 100 simulated seasons. PFR-only classification implements
the database portion of that approach; it does not supply the film review or manual chart-design
judgment described there.

### Publication Policy

Publish only reviewed chart files generated by this repository. Include the concise notice in
[CHART_ATTRIBUTION.md](../CHART_ATTRIBUTION.md), and keep raw play-by-play, downloaded pages,
aggregate source tables, audit rows, templates, original developer charts, and replay reports out
of the release. The accepted 1983 generator output is stored as `seasons/1983-generated` so it can
coexist with ignored private comparison charts; release packaging maps it to `seasons/1983`. The
2024 and fictional 2026 sets already use their final numeric directory names.

### What Can Be Recovered

- Punt and return columns track their corresponding season distributions closely.
- Rushing and passing totals produce cohort-calibrated column strengths.
- Defensive rushing and passing efficiency shift a complete tactical formation template.
  Fractional shifts are distributed across defense sub-rows according to the actual red/green
  dice probabilities. Defensive interception strength is allocated across sub-row-five cells,
  limiting any one play-and-formation adjustment to 1/36 while preserving team differences; sack
  rates alter separate rare pressure outcomes.
- Classified plays preserve team-specific distributions that aggregate totals discard.

Exact reproduction still needs charting judgment. Historical descriptions often identify run
direction and receiver but omit pass depth, route, coverage, or designed play. When
`field_goal_by_distance` is supplied, each distance is interpreted as the statistical kick
distance and the generator builds a nonincreasing success curve; aggregate field-goal totals
remain a fallback. Supplied offensive fumbles and fumbles lost determine the chart's weighted
recovery interval. Penalty, breakaway, and formation conventions can still differ between chart
designers.

Aggregate passing symbols are allocated against the same denominators used by the engine:
completion and interception rates apply to resolved pass attempts, while quarterback-time and
penalty rows sit outside that attempt denominator. Passing yardage, pressure, and the template's defensive interception contribution use
engine-observed calibration factors rather than matching offense-column averages in isolation.
The defensive contribution is expressed through multiple low-mass cells instead of changing one
high-mass sub-row at a source-rate threshold. Supplied `out_of_bounds` counts mark weighted
numeric run and pass outcomes with `*`; omitted counts preserve the previous unmarked fallback.

The 2026-11-01 two-phase reference run used 64 chart-focused training seasons and 256 held-out
Hard-vs-Hard validation seasons for both 1983 and 2024. The selected 1983 profile applies
completion, interception, pressure, and passing-yard adjustments of `-0.05`, `-0.07`, `-0.07`,
and `1.55`; its rushing multiplier remains `1.0`. The selected 2024 values are `0.02`, `-0.06`,
`-0.02`, `1.30`, and `1.0` respectively. Every training and validation game completed.

Under the team-independent situation-aware training policy, all five configured chart-boundary
metrics met tolerance for both seasons. Hard play selection produced a separate distribution:
1983 completion rose to 60.86% versus 56.90% actual while interceptions and sacks fell to 1.25%
and 4.31% versus 4.41% and 7.96%; 2024 completion was 64.86% versus 65.29%, passing yardage was
7.81 versus 7.13 yards per attempt, and sacks were 4.96% versus 6.87%. The 2024 Hard run still
finished near actual scoring and volume at 22.16 versus 22.91 points and 61.16 versus 62.15 plays
per team-game. These policy differences are reported diagnostics. Chart tuning must not force one
profile to cancel the strategic choices made by every AI policy.

A 2026-11-02 DATA-012 rerun replaced the old binary defensive-interception threshold with the
low-mass allocation described above. The existing profiles still met all five 64-season training
tolerances. The 1983 Hard interception rate increased from 1.25% to 1.96%; 2024 moved from 1.30%
to 1.11%, while its chart-focused rate improved from 3.12% to 2.79% against a 2.17% source rate.
The specific Dallas D/Short matchup found in manual testing fell from 38.89% to 11.11%. For the
47-pass call mix in that game, expected defensive interceptions fell from 2.50 to 1.58 and the
probability of at least five fell from 6.84% to 1.87%.

The original historical workbooks examined during development contain chart-entry formatting
and quantitative audit formulas. They do not contain a hidden season-statistics-to-chart formula.

## Import an Existing Excel Chart

### What the Importer Does

[`extract_charts.py`](../extract_charts.py) generates game CSV charts from existing Excel workbooks.
It is a **converter**, not a tool that derives new team ratings from football statistics.
Run it from a source checkout; it is not a browser menu feature or separately packaged executable.

| Output | Contents |
|--------|----------|
| `offense.csv` | Offensive dice rows 10–39, nine play columns, breakaway, QB-time, and fumble entries |
| `defense.csv` | Formations A–F, sub-rows 1–5, and play columns 1–9 |
| `special.csv` | Kickoffs, returns, punts, field goals, and extra points |

It reads BLACK cell backgrounds, RED extra-point backgrounds (written as `NG`),
parentheses-style defense number formats, and fumble recovered/lost ranges from offense column Q.
Numeric extra-point cells are written blank for a good kick; RED cells mark misses.

### Requirements and Input Layout

Install the importer's optional dependency in your active Python environment:

```sh
python -m pip install xlrd==1.2.0
python extract_charts.py --help
```

`xlrd` is needed for importing, not ordinary gameplay. Use **Excel 97–2003 `.xls`** files,
one workbook per team, with sheets named exactly **OFFENSE** and **DEFENSE**.
The importer expects the original chart layout, not arbitrary spreadsheets:

- Offense dice values in B; nine offensive play columns in C–K.
- Offense special columns N–P: breakaway, QB-time, and fumble; fumble-range text in Q.
- Defense formation/sub-row labels on the left and numbered play columns in the chart header.
- Special teams on the DEFENSE sheet in N–T; T supplies dice rows and extra-point color.

Preserve colors and number formats. Converting to CSV first loses that information.
Renaming an `.xlsx` file to `.xls` does not convert it.

### Convert Workbooks

From the repository root, always supply **both** paths:

```sh
# All .xls workbooks in a directory
python extract_charts.py -i /path/to/workbooks -o /path/to/staging/2026

# One workbook, filename relative to the input directory
python extract_charts.py -i /path/to/workbooks -o /path/to/staging/2026 -t DemoTeam.xls
```

| Option | Meaning |
|--------|---------|
| `-i`, `--input` | Workbook directory |
| `-o`, `--output` | Destination season directory |
| `-t`, `--team` | One workbook filename |

Default paths are developer-specific historical download locations; do not rely on them.
Batch discovery selects lowercase `.xls` filenames. Team folder names come from workbook filenames,
with legacy 1972/1983 prefixes removed and a few legacy mappings applied.
For other years, use `DemoTeam.xls` rather than assuming a year prefix is stripped.

**Generate into staging first.** Existing CSVs are overwritten without confirmation,
and errors can leave partial output. Per-team errors are caught and processing continues:
**zero exit status does not prove every import succeeded**. Check `ERROR processing` messages and row counts.

### Synthetic Workbook Example

This optional example uses constant-value synthetic data, not private charts or a realistic team.
Install `xlwt` only to create this example:

```sh
python -m pip install xlwt==1.3.0
```

Save the following as `make_demo_workbook.py` in a scratch directory outside the repository and run it there:

```python
from pathlib import Path
import xlwt

Path("workbooks").mkdir(exist_ok=True)
book = xlwt.Workbook()
offense = book.add_sheet("OFFENSE")
defense = book.add_sheet("DEFENSE")
for play in range(1, 10):
    offense.write(1, play + 1, play)
    defense.write(1, play + 2, play)
for index, roll in enumerate(range(10, 40)):
    row = index + 2
    offense.write(row, 1, roll)
    for column in range(2, 11):
        offense.write(row, column, 3)
    for column in (13, 14):
        offense.write(row, column, 0)
    offense.write(row, 15, "R")
    defense.write(row, 0, "ABCDEF"[index // 5])
    defense.write(row, 1, index % 5 + 1)
    for column in range(3, 12):
        defense.write(row, column, 0)
    for column, value in enumerate((60, 20, 40, 5, 0, "1-40", roll), start=13):
        defense.write(row, column, value)
offense.write(0, 16, "Fumble Recovered 10-29; Lost Ball 30-39")
book.save("workbooks/DemoTeam.xls")
```

Return to the repository root and import using those scratch paths:

```sh
python extract_charts.py -i /path/to/scratch/workbooks -o /path/to/scratch/2026 -t DemoTeam.xls
```

Expect 30 offense, 30 defense, and 30 special-teams rows in `2026/DemoTeam/`.
Row counts are useful controls, not complete semantic validation.

## Validate and Install

1. Check all three CSVs, their headers, and row counts.
2. Compare representative entries to the workbook: gains/losses, BLACK, parentheses, fumbles,
   special-teams ranges, missed extra points, and empty cells.
3. Load the staged chart from the source checkout:

   ```sh
   python -c "from paydirt.chart_loader import load_team_chart; load_team_chart('/path/to/scratch/2026/DemoTeam'); print('Chart files loaded')"
   ```

4. Add `2026.yaml` beside the team directories. For this demo, copy the public
   `seasons/2026/2026.yaml`. Chart loading alone does not validate season rules.
5. Optionally add fictional `team.yaml` and `roster.json` files using [these formats](seasons.md).
6. Back up existing data, then copy the reviewed season to the [appropriate location](seasons.md#season-data-locations).
7. Select the team and inspect its charts and a practice game. In a source checkout with the demo installed:

   ```sh
   python -m paydirt --play --compact --home 2026/DemoTeam --away 2026/Ironclads
   ```

Do not overwrite the distributed Thunderhawks or Ironclads when experimenting.

## Troubleshooting and Limitations

- **Unknown empirical chart:** use the normalized names listed above; source play labels are
  not interpreted automatically.
- **Aggregate chart differs from a historical chart:** add classified plays for the affected
  columns. Season totals cannot recover information that was aggregated away.
- **Field-goal column looks generic:** provide normalized empirical field-goal results derived
  from attempts by distance. Made/attempted and longest-made totals are insufficient.

- **Missing xlrd:** install 1.2.0 with the interpreter used for the script.
- **Missing sheet / index errors:** verify exact sheet names, columns, header placement, and original layout.
- **No teams found:** check `-i` and lowercase `.xls` extensions.
- **Empty formula cells:** `xlrd` does not evaluate formulas. Recalculate/save usable cached results in a spreadsheet application,
  or replace formulas with verified literal values in a copy preserving formatting. Inspect the CSV afterward.
- **Wrong BLACK/extra-point entries:** verify solid BLACK/RED fills survived editing.
- **Stray characters in result cells:** a source cell holding only a backtick or quote mark is a
  blank (zero-yard) result. The generator drops such characters when writing `special.csv`, and the
  game loader does the same with a warning naming the column and dice roll, so existing CSVs do not
  need to be regenerated to play correctly.
- **Partial output:** repair only the affected staged team, rerun, and review every message.
- **Team missing in the app:** check rules YAML and source-versus-bundled data locations.

The workbook extractor has no general chart-validity report, dry-run, overwrite protection, or
metadata generator. Loading successfully is not an accuracy guarantee. Import only authorized workbooks;
keep private sources, extracted charts, intermediate generations, and replay artifacts local.
Only reviewed generator outputs intended for a release belong in the public season directories,
and historical release charts remain outside unit fixtures.

### Automatic completeness audit

Both PBP generation commands write `chart-audit.json` and reject invalid or incomplete generated
charts. The audit checks all primary and secondary columns, result symbols, physical yardage limits,
fumble recovery coverage, and scoring conventions; it also measures the combined primary offense/defense result probabilities
for all 54 play/formation combinations. `generation-manifest.json` records source annotation counts
and explicitly modeled fallback features and rates. A missing season-wide annotation is not
interpreted as evidence that its probability was zero.

Saved historical sources can omit clock stops, fair catches, illegal kickoffs, blocked field goals,
and special snap fumbles. Documented modeling defaults preserve those engine mechanisms when the
whole season contains no corresponding observations. These estimates are distinct from source
evidence and still need sensitivity and historical validation. The full findings and repeatable
comparison command are in the [completeness audit](dev-notes/generated-chart-completeness-audit.md).

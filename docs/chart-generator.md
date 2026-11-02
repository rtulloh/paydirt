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
totals. The generator validates every normalized result before generation, preserves numeric
out-of-bounds markers such as `4*`, approximates symbolic frequencies with whole chart-row
weights, and fills unmarked numeric rows from the observed yardage distribution.

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
fumble-loss events, and empirical out-of-bounds markers, then pass normalized outcomes through
the opponent-adjusted generator. Aggregate-only generation is an explicit fallback for a season
without complete play-by-play or for empirical columns below the minimum sample threshold.

Calibrate source adapters through multi-seed engine replays. Match completion, yardage, sacks,
turnovers, play volume, and scoring together; matching isolated chart averages is insufficient.
Record every non-neutral run or pass calibration value in `generation-manifest.json`.

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
  --seed 8306
```

The team map is a JSON object from PFR abbreviations to template directory names. The command
writes a `generation-manifest.json` with source-row counts, classification diagnostics, per-team
field-goal and fumble counts, empirical outcomes used, and columns that fell back to aggregate
generation. The audit directory contains provenance rows for local review. Keep downloaded HTML,
audit rows, historical templates, and generated historical seasons local and ignored.

The adapter fits a league-wide additive model that separates relative offense and defense effects
under an explicit average-defense-zero constraint. Every offensive audit row therefore includes
its opponent. Offense outcomes are translated to a league-average defense, while fitted defense
residuals replace schedule-biased allowed rates before the defense template is generated. A ridge
pseudo-count, configurable with `--opponent-shrinkage`, partially pools small samples.

Pass event families use the aggregate generator's engine-calibrated baseline by default, while
empirical play by play supplies resolved yard distributions, touchdowns, fumbles, and clock-stop
markers. Quantization preserves the combined mass of fumble, interception, penalty, and marked
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
replacing its aggregate fallback. Accepted field goals marked `no play` are excluded from kick
calibration. Review the manifest before using the charts.

The source approach is informed by the archived
[Data-Driven Football design process](https://web.archive.org/web/20250524072210/http://www.datadrivenfootball.com/designprocess.html),
which describes parsing every regular-season gamebook, reviewing every record, adding information
from video, and validating with at least 100 simulated seasons. PFR-only classification implements
the database portion of that approach; it does not supply the film review or manual chart-design
judgment described there.

### What Can Be Recovered

- Punt and return columns track their corresponding season distributions closely.
- Rushing and passing totals produce cohort-calibrated column strengths.
- Defensive rushing and passing efficiency shift a complete tactical formation template.
  Fractional shifts are distributed across defense sub-rows according to the actual red/green
  dice probabilities, while interception and sack rates alter rare defensive outcomes.
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
penalty rows sit outside that attempt denominator. Passing yardage, pressure, and the template's
baseline defensive interception contribution use engine-observed calibration factors rather than
matching offense-column averages in isolation. Supplied `out_of_bounds` counts mark weighted
numeric run and pass outcomes with `*`; omitted counts preserve the previous unmarked fallback.

A 256-season 2024 Hard-vs-Hard calibration run measured the generated charts through 72,960
completed engine games. Completion rate was 65.28% versus 65.29% actual, sacks were 2.35 versus
2.42 per team-game, turnovers were 1.11 versus 1.15, scoring was 23.13 versus 22.91 points per
team-game, and field goals were 85.20% versus 84.04%. Passing yards remained low at 6.53 versus
7.13 yards per attempt, total yardage at 314.72 versus 337.42 yards per team-game, and play
volume at 59.02 versus 62.15 plays per team-game. These are calibration measurements, not
guarantees for a team or a single simulated season.

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

There is no general chart-validity report, dry-run, overwrite protection, or metadata generator.
Loading successfully is not an accuracy guarantee. Import only authorized workbooks;
keep private sources and generated historical charts local, out of commits and unit fixtures.

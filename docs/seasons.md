# Seasons and Team Data

[Documentation index](README.md) · [Chart generator / Excel import](chart-generator.md)

## Available Seasons

Version 1.10.4 includes **1977**, **1983**, and **2024** chart sets generated from season statistics and
play-by-play, plus the fictional **2026** Thunderhawks and Ironclads sample. The generated
historical charts are independent reconstructions; source and license details are in the
[chart attribution](../CHART_ATTRIBUTION.md). The supplied rule model is not a claim that every
professional-league rule for those seasons is implemented.

### Included Chart Attribution

The 1977 and 1983 charts are independent statistical reconstructions generated from historical
play-by-play and aggregate season data, including archived Pro Football Reference records.
The 2024 charts are independent reconstructions generated from nflverse play-by-play and
aggregate season data; nflverse play-by-play is provided under CC BY 4.0. The generated chart
files are distributed under Paydirt's MIT License. No raw source data or original Paydirt team
charts are included. These unofficial charts are not endorsed by Sports Reference, nflverse,
the NFL, Avalon Hill, or the original game designers.

The 1977 set contains all 28 teams and uses a modeled historical source scope.
It ships with explicitly disclosed accuracy limitations, rather than a claim
that every statistical tolerance passed. Consult the bundled season
`NOTES.md` for source gaps, final measurements and known interception/scoring
biases. Historical winners and playoff qualifiers are never forced.

## Season Data Locations

For a source checkout, put data under the repository's `seasons/` directory. Release builds
contain numeric `seasons/1977`, `seasons/1983`, `seasons/2024`, and `seasons/2026` directories. The tracked
1983 charts use `seasons/1983` in both the source tree and packaged application.
Private comparison charts belong outside `seasons/`, in ignored local audit storage. The separate
user-data directory is used by bundled applications, not ordinary source runs.

| Bundled platform | Custom seasons directory |
|------------------|--------------------------|
| macOS | `~/Library/Application Support/Paydirt/seasons/` |
| Windows | `%LOCALAPPDATA%\Paydirt\seasons\` |
| Linux | `~/.local/share/Paydirt/seasons/` |

On Linux, `XDG_DATA_HOME` overrides `~/.local/share`. Create the seasons directory if needed.
User-installed seasons are searched before bundled seasons; avoid incomplete duplicate season directories.
Restart the application after installing data if it is not shown.

## Adding a Season

Create a year directory containing a matching `YYYY.yaml` rules file and a directory for every team:

```text
seasons/
└── 2026/
    ├── 2026.yaml
    └── DemoTeam/
        ├── offense.csv
        ├── defense.csv
        ├── special.csv
        ├── team.yaml
        └── roster.json
```

The three CSVs and season rules are required. Team metadata and commentary rosters are optional.
The [chart generator](chart-generator.md) creates the CSVs from compatible Excel workbooks;
it does not create the rules, metadata, or roster.

For local chart-set comparisons, a directory may add a suffix to the base year, such as
`seasons/1983-gen/`. Keep the rules file named for the base year (`1983.yaml`) and declare
`season: 1983` inside it. Suffixed variants are loaded when their team paths are supplied
directly, for example:

```sh
python -m paydirt --auto seasons/1983-gen/Eagles seasons/1983-gen/Cowboys
```

The normal team picker lists numeric season directories only, so comparison variants do not
appear alongside installed seasons.

## Chart File Formats

Use the small public sample files under `seasons/2026/` as concrete format references. The
generated historical sets use the same file format but are not unit-test fixtures.

| File | Structure |
|------|-----------|
| `offense.csv` | Dice rows 10–39; columns `#,Line Plunge,Off Tackle,End Run,Draw,Screen,Short,Med,Long,T/E S/L,B,QT,Fumble` |
| `defense.csv` | Formation/sub-row entries; columns `#,Formation,Sub,1,2,3,4,5,6,7,8,9` |
| `special.csv` | Dice rows 10–39; columns `#,Kickoff,Kickoff Return,Punt,Punt Return,Int. Return,Field Goal,Extra Point` |

Keep symbolic entries and number formatting intact. Empty cells are not interchangeable with numeric zero.
A successful file load is not proof that imported values match the source workbook; inspect the charts.

In the QT column, `SACK 0` explicitly represents a sack with zero yards lost;
`SACK 0*` also carries the out-of-bounds marker. Plain numeric `0` is a scramble,
and `F 0` is a real fumble at the line with its recovery procedure. These entries
are distinct. The explicit zero-yard sack syntax is supported only in QT, not
the primary play, B or special-team columns.

## Team Metadata and Rosters

Example `team.yaml`, using fictional data:

```yaml
team_name: Example City Demo Team
short_name: DEM
team_color: "#0066CC"
team_mascot: Comet
city: Example City
state: IL
founded: 2026
history: "A fictional team for local chart experiments."
```

Example `roster.json` (position lists supply commentary names):

```json
{
  "qb": ["Alex Example"],
  "rb": ["Casey Example"],
  "wr": ["Jordan Example"],
  "k": ["Morgan Example"]
}
```

## Season Rules

The **home team's season rules** apply, including cross-season games.
Missing rules YAML is an error. The file controls conversion availability and overtime rather than the UI guessing from a year.

The season year also determines possession after an unblocked, unreturned
missed field goal. Before 1974 the opponent starts at its 20; from 1974 through
1993 it takes the better of its 20 and the line of scrimmage; from 1994 onward
it takes the better of its 20 and the kick spot. The same rule applies when a
foul is declined and the missed kick stands. Blocked kicks and fumbled snaps
use their recovery procedures. See the Hall of Fame's
[1974 rule history](https://www.profootballhof.com/football-history/general-history-chronology-1960-to-1979)
and [1994 change](https://www.profootballhof.com/news/nfl-kickers-up-up-and-away).

```yaml
season: 2026
two_point_conversion: true
overtime:
  enabled: true
  format: modified_sudden_death
  period_length_minutes: 10
  max_periods_regular: 1
  max_periods_playoff: 0
  can_end_in_tie_regular: true
  can_end_in_tie_playoff: false
  coin_toss_winner_receives: true
```

Formats supported here are `sudden_death` and `modified_sudden_death`. A maximum of zero periods means unlimited.
Use CLI `--playoff-game` to select playoff rather than regular-season overtime limits.

### Scaffolding Rules

From a source checkout:

```sh
python -m paydirt --scaffold-season 2027
```

This creates a starter file under the checkout's built-in `seasons/` path, **not** the bundled user-seasons path.
For a bundled installation, prepare the YAML in a source checkout and copy it with the team directories into the user season folder.
The command refuses to overwrite existing rules unless `--force` is supplied. Back up intentional customizations first.

The scaffold's era defaults are: no two-point conversions before 1994; sudden death before 2010;
modified sudden death from 2010; 15-minute overtime before 2017 and ten minutes from 2017.
These are defaults provided by the tool, not an exhaustive history of NFL rules. Review the generated YAML.

## Data Publication and Privacy

The project publishes only chart files generated by this repository. Original developer charts,
source workbooks, raw play-by-play, intermediate experiments, and game logs remain private and
ignored. Generated releases carry the concise notice in
[CHART_ATTRIBUTION.md](../CHART_ATTRIBUTION.md). Use only synthetic fixtures or public 2026
sample teams in unit tests; the larger historical sets are release data, not test fixtures.
Standalone local integration runners have separate private-data requirements documented in
[AGENTS.md](../AGENTS.md).

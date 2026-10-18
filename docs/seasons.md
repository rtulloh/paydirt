# Seasons and Team Data

[Documentation index](README.md) · [Chart generator / Excel import](chart-generator.md)

## Available Seasons

The public sample is **2026**, with fictional Thunderhawks and Ironclads, two-point conversions,
and configured modified-sudden-death overtime. Other seasons require user-supplied data.
The supplied rule model is not a claim that every current professional-league rule is implemented.

## Season Data Locations

For a source checkout, put data under the repository's `seasons/` directory.
The separate user-data directory is used by bundled applications, not ordinary source runs.

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

## Chart File Formats

Use the public sample files under `seasons/2026/` as concrete format references.

| File | Structure |
|------|-----------|
| `offense.csv` | Dice rows 10–39; columns `#,Line Plunge,Off Tackle,End Run,Draw,Screen,Short,Med,Long,T/E S/L,B,QT,Fumble` |
| `defense.csv` | Formation/sub-row entries; columns `#,Formation,Sub,1,2,3,4,5,6,7,8,9` |
| `special.csv` | Dice rows 10–39; columns `#,Kickoff,Kickoff Return,Punt,Punt Return,Int. Return,Field Goal,Extra Point` |

Keep symbolic entries and number formatting intact. Empty cells are not interchangeable with numeric zero.
A successful file load is not proof that imported values match the source workbook; inspect the charts.

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

## Data Privacy

Do not commit or redistribute private/historical workbooks, charts, or game logs.
Use only synthetic fixtures or public 2026 sample teams in unit tests, even when historical charts exist locally.
Standalone local integration runners have separate private-data requirements documented in [AGENTS.md](../AGENTS.md).

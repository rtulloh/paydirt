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

## Web Season Campaigns

Choose **Seasons** from the web main menu to create or reopen a campaign. A campaign is your
saved competition, separate from a chart year. You can keep several independent replays of the
same historical year, or build a custom league from team editions across installed years.
In exhibition team selection, **Search by name within year** filters only the active chart year.
Changing the year or selection side clears the search and keeps the other selected edition.

Use **New season** to choose an installed historical calendar or a custom league. Historical
1983 and 2024 templates appear only when the full team/rule/calendar inputs are available;
they begin with empty results. Actual historical scores do not determine your outcomes.
A custom league lets you select year/team editions, divisions and conferences, and one shared
rules year. Choose a single or home-and-away round robin, or enter individual fixtures.
The same franchise from different years is allowed; duplicate exact team editions are rejected.
Odd-sized round robins include byes. Team membership/rules become fixed once play begins.
After creation, review the **Schedule** and use **Edit schedule** before starting a game.
Editing a historical calendar turns that competition into a custom season. **Duplicate season**
creates a fresh competition with the regular calendar and team editions, without results,
active games or playoff progress. Choose a followed team to focus the overview and schedule;
this preference stays with that campaign and can change after play starts.

Use the campaign selector to switch competitions. **Schedule** shows each fixture and its state.
Choose **Play** on an unstarted fixture to open **Game setup**. Select the home or away team
to coach and **Easy**, **Medium** (the default), or **Hard** CPU difficulty, then choose
**Start game** to continue to the coin toss. **Cancel** leaves the fixture unstarted. The side
and difficulty stay with the saved game when resumed. Reopen an in-progress fixture from
**Saved games**. A legal final is recorded once; reloads do not add a second win or statistics.
**Simulate unplayed games** runs real engine games and saves each completed result. Stop takes
effect between games. Played or in-progress fixtures are never overwritten by simulation.

**Overview** combines division standings and recent results. Standings show every division grouped by conference. NFC appears before
AFC, side by side on wider screens and stacked on smaller screens. Custom conferences are also
shown. Use **Standings scope** to narrow the view to a conference or division. Following a team
does not hide the other divisions. Tables show W/L/T and points for/against.
Click a column header to sort; click again to reverse direction. Number columns start highest
first and names start alphabetically. Sorting a division keeps its teams within that division.
The arrow and header announce the current direction; keyboard users can press Enter or Space.
Missing values always stay last. Statistics sort by the full recorded value, before rounding.

**Team statistics** has separate **Offense**, **Defense** and **Kicking** categories. Offense and
defense offer totals or per-game counts. Each counter shows its recorded-game count against
completed regular-season games. **Not recorded** means none of those games contains that
counter; **Partial** means only some games contain it. Neither label means a recorded zero.
**Leaders** ranks teams in supported categories, with game counts. Individual player statistics
are not tracked. Missing older statistics are unknown, not zero; per-game denominators include
only games with that statistic recorded. Regular-season totals exclude playoff games. Ranking
uses winning fraction, point differential, points scored and team name; it does **not** implement
every official NFL tiebreak.

**Offense** includes team points, net total offense, gross and net passing yards, passing and
rushing attempts, touchdowns, long gains and fumbles. Receiving shows receptions, yards,
yards per reception, touchdowns, longest reception and receiving fumbles from completed-pass
production. **Downs** separates rushing, passing and penalty first downs, then third- and
fourth-down conversions, attempts and percentages. The directory keeps passing, rushing,
receiving and downs in focused tables. Compact headings have full accessible names and hover
labels; gross and net passing yards remain explicitly distinguished.

Completion percentage, yards per attempt/reception and **Team passer rating** use combined
recorded counters, including when the table shows per-game counts. Passing averages exclude
sacks. Team passer rating uses the [NFL passer-rating formula](https://www.profootballhof.com/news/nfl-s-passer-rating),
including its component limits, with the team’s combined attempts, completions, gross yards,
passing touchdowns and interceptions. Each rate uses only games with all its required counters
recorded; zero attempts produce no rate. Rates are not averages of game ratings or percentages.
Longest gains and kicks remain season maximums in either view. Points include all team scoring
and remain available from final scores even when an older game has no detailed box score.

**Defense** shows the corresponding opponent production, including scoring, passing, rushing,
receiving and down conversions allowed. Interceptions, fumble recoveries, takeaways and sacks
come from the opposing offense’s recorded interceptions thrown, fumbles lost, total giveaways
and sacks taken. The **Turnovers** table shows season totals. Its giveaways, takeaways and
differential use the same games with both teams’ turnover totals recorded; differential is
takeaways minus giveaways. That paired coverage can differ from the individual interception
and fumble-recovery coverage. With no paired games, the turnover balance remains unknown. These are team statistics; individual players are not tracked.

**Kicking** shows field-goal and extra-point makes, attempts and percentages, the longest made
field goal, and field-goal makes and attempts in 0–19, 20–29, 30–39, 40–49 and 50+ yard bands.
Distances include the snap and hold. **Punting** shows attempts, yards, gross and net averages,
longest punt, blocks, inside-20 punts, touchbacks, fair catches, returned punts and return yards
allowed, plus the opponents’ average yards per recorded return. Team gross punt average is punt yards divided by all recorded punts, including blocked
team kicks. Net average subtracts punt-return yards and 20 yards per touchback before dividing
by that same count. A blocked team punt contributes no punt yards or punt-return statistics,
following the [NFL GSIS statistical definitions](https://www.nflgsis.com/gsis/Documentation/Partners/StatIDs_files/sheet001.html). These team measures are provided by the engine statistics, not calculated
by the UI. **Returning** separates kickoff and punt returns into counts, yards, averages, long
returns and touchdowns, with punt fair catches shown separately. Special teams tables show
season totals and authoritative combined rates, rather than per-game counts. No attempts or
unavailable required counters show — for an average or percentage.

Blocked kicks count as attempts; fumbled snaps and kicks erased by accepted penalties do not.
A declined penalty counts the retained kick once. Older saves keep unknown detailed coverage
even when resumed; new recorded zero-attempt games remain distinct from those older records.
The overview retains five cards, each showing the top five teams for total offense, passing,
rushing, scoring and total defense.

Once the regular schedule is complete, seed the playoffs. Historical campaigns use their supported
8/10/14-team formats; custom campaigns use the selected power-of-two field. Advance each completed
round from campaign results; original historical entrants/winners are not forced. Tied playoff
finals cannot advance. This is a game competition, not official historical qualification certification.

Browser/hosted campaigns and checkpoints are stored in this browser profile. The installed
application uses its durable local user-data library instead. **Export season** keeps a portable
backup; imports create a separate
campaign rather than replacing an existing one. Keep all required chart editions installed;
exports contain saved play state, not chart files. Clearing site data or changing browser origin/profile
can remove access to browser-owned saves. Export before changing devices or resetting the machine.
See [saved games](saved-games-and-standings.md) for recovery and compatibility boundaries.

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

Historical display abbreviations must describe the franchise in the selected season.
Run `python3 scripts/audit_team_names.py` from the repository root to check all 90
bundled metadata files, including era-specific franchise locations and nicknames.
The core chart loader and backend read `short_name` from `team.yaml`.

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

Exhibitions use the **home team's season rules**, including cross-season games.
A web custom campaign instead uses its explicitly selected fixed rules year for every fixture;
historical campaigns use their calendar year.
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

### CPU Behavior

An optional `ai_behavior.yaml` in the season directory tunes CPU pace and
strategic choices for that era. If it is absent, era defaults are used; partial
files are merged with the defaults. The fields are:

```yaml
two_minute_drill:
  q2_hurry_when_trailing_by: 7
  q4_any_deficit_minutes: 2.0
  q4_deficit_9_minutes: 3.0
  q4_deficit_4_minutes: 2.0
  q4_always_minutes: 2.0
  skip_when_leading_by: 14

hurry_up:
  q4_deficit_9_minutes: 3.0
  q4_deficit_4_minutes: 2.0
  q4_any_minutes: 2.0

clock_killing:
  q4_any_lead_minutes: 3.0
  q4_big_lead_minutes: 2.0
  clock_run_on_any_lead: false

strategic:
  spike_ball_chance: 0.10
  oob_designation_aggression: 0.2
  fourth_down_aggression: 0.5
```

`fourth_down_aggression` is the era baseline for ordinary fourth-down
conservatism. The selected difficulty shifts it by −0.2 (Easy), 0 (Medium) or
+0.2 (Hard), clamped to `[0, 1]`. Field-goal attempts additionally use the
kicking team's chart make probability; see [AI difficulty](ai-difficulty.md).

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

### Team-statistics categories

The Team statistics tab includes an Offense, Defense and Special teams directory.
Choose a category, such as Passing or Receiving, to open a focused sortable table.
The Offense, Defense and Kicking overview buttons restore the full tables.
Totals and Per game remain available for offensive and defensive counters;
percentages and efficiency ratings retain their combined-total definitions.
Receiving uses the recorded completed-pass production counters.
Returning separates kickoff and punt returns; Punting includes team gross and net averages.
Existing saves and completed results retain their recorded coverage, so newly supported
counters remain unknown for older games that did not record them.

The main statistics view shows five leader cards (total offense, passing, rushing,
scoring and total defense), each listing up to five teams using recorded per-game
rankings. Detailed tables use abbreviated headers such as GP, CMP, ATT, CMP%,
YDS and AVG. Hover or focus a column button for its full name; screen readers
retain the full names. Passing and rushing prefixes distinguish shared labels
in the combined overview.

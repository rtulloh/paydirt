# ESPN team-statistics reference review

Research and proposed design, reviewed November 19, 2026. This is an inventory of the rendered ESPN team-statistics pages, not a claim that every field is implemented in Paydirt.

The normal Chromium browser successfully rendered the directory and all thirteen category destinations. The text-only web reader was blocked; the inventory below comes from rendered table headers and their explanatory title attributes. Local browser receipts are in ignored `.ai-audits/season-ui/espn-review/`. No player tables were included.

## Verified category inventory

Every table includes Team and Games Played. Repeated labels such as YDS and AVG belong to the grouped sections shown below.

### Offense: Total Yards

[ESPN source](https://www.espn.com/nfl/stats/team)

Rendered header groups and columns:

```text
TEAM
TOTAL	PASSING	RUSHING	POINTS
GP	YDS	YDS/G	YDS	YDS/G	YDS	YDS/G	PTS	PTS/G
```

Header explanations: GP: Games Played; YDS: Net Total Yards; YDS/G: Net Yards Per Game; YDS: Net Passing Yards; YDS/G: Net Passing Yards Per Game; YDS: Rushing Yards; YDS/G: Rushing Yards Per Game; PTS: Total Points; PTS/G: Total Points Per Game.

### Offense: Passing

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/offense/stat/passing/table/passing/sort/netPassingYardsPerGame/dir/desc)

Rendered header groups and columns:

```text
TEAM
GP	CMP	ATT	CMP%	YDS	AVG	YDS/G	LNG	TD	INT	SACK	SYL	RTG
```

Header explanations: GP: Games Played; CMP: Completions; ATT: Passing Attempts; CMP%: Completion Percentage; YDS: Net Passing Yards; AVG: Yards Per Pass Attempt; YDS/G: Net Passing Yards Per Game; LNG: Longest Pass; TD: Passing Touchdowns; INT: Interceptions; SACK: Total Sacks; SYL: Sack Yards Lost; RTG: Passer Rating.

### Offense: Rushing

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/offense/stat/rushing/table/rushing/sort/rushingYardsPerGame/dir/desc)

Rendered header groups and columns:

```text
TEAM
GP	ATT	YDS	AVG	YDS/G	LNG	TD	FUM	LST
```

Header explanations: GP: Games Played; ATT: Rushing Attempts; YDS: Rushing Yards; AVG: Yards Per Rush Attempt; YDS/G: Rushing Yards Per Game; LNG: Long Rushing; TD: Rushing Touchdowns; FUM: Rushing Fumbles; LST: Rushing Fumbles Lost.

### Offense: Receiving

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/offense/stat/receiving/table/receiving/sort/receivingYardsPerGame/dir/desc)

Rendered header groups and columns:

```text
TEAM
GP	REC	YDS	AVG	YDS/G	LNG	TD	FUM	LST
```

Header explanations: GP: Games Played; REC: Receptions; YDS: Receiving Yards; AVG: Yards Per Reception; YDS/G: Receiving Yards Per Game; LNG: Long Reception; TD: Receiving Touchdowns; FUM: Receiving Fumbles; LST: Receiving Fumbles Lost.

### Offense: Downs

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/offense/stat/downs/table/miscellaneous/sort/firstDowns/dir/desc)

Rendered header groups and columns:

```text
TEAM
FIRST DOWNS	THIRD DOWNS	FOURTH DOWNS	PENALTIES
GP	TOTAL	RUSH	PASS	PEN	MADE	ATT	PCT	MADE	ATT	PCT	TOTAL	YDS
```

Header explanations: GP: Games Played; TOTAL: Total 1st downs; RUSH: Rushing 1st downs; PASS: Passing 1st downs; PEN: 1st downs by penalty; MADE: Third Down Conversions; ATT: Third Down Attempts; PCT: 3rd down %; MADE: Fourth Down Conversions; ATT: First Downs Attempts; PCT: 4th down %; TOTAL: Total Penalties; YDS: Total Penalty Yards.

### Defense: Yards Allowed

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/defense/table/passing/sort/netTotalYards/dir/desc)

Rendered header groups and columns:

```text
TEAM
TOTAL	PASSING	RUSHING	POINTS
GP	YDS	YDS/G	YDS	YDS/G	YDS	YDS/G	PTS	PTS/G
```

Header explanations: GP: Games Played; YDS: Net Total Yards; YDS/G: Net Yards Per Game; YDS: Net Passing Yards; YDS/G: Net Passing Yards Per Game; YDS: Rushing Yards; YDS/G: Rushing Yards Per Game; PTS: Total Points; PTS/G: Total Points Per Game.

### Defense: Turnovers

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/turnovers)

Rendered header groups and columns:

```text
TEAM
TAKEAWAYS	GIVEAWAYS
GP	DIFF	INT	FUM	TOTAL	INT	FUM	TOTAL
```

Header explanations: GP: Games Played; DIFF: Turnover Ratio; INT: Take Away Interceptions; FUM: Fumbles Recovered; TOTAL: Total Takeaways; INT: Give Away Interceptions; FUM: Fumbles Lost; TOTAL: Total Giveaways.

### Defense: Passing

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/defense/stat/passing/table/passing/sort/netPassingYardsPerGame/dir/desc)

Rendered header groups and columns:

```text
TEAM
GP	CMP	ATT	CMP%	YDS	AVG	YDS/G	LNG	TD	INT	SACK	SYL	RTG
```

Header explanations: GP: Games Played; CMP: Completions; ATT: Passing Attempts; CMP%: Completion Percentage; YDS: Net Passing Yards; AVG: Yards Per Pass Attempt; YDS/G: Net Passing Yards Per Game; LNG: Longest Pass; TD: Passing Touchdowns; INT: Interceptions; SACK: Total Sacks; SYL: Sack Yards Lost; RTG: Passer Rating.

### Defense: Receiving

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/defense/stat/receiving/table/receiving/sort/receivingYardsPerGame/dir/desc)

Rendered header groups and columns:

```text
TEAM
GP	REC	YDS	AVG	YDS/G	LNG	TD	FUM	LST
```

Header explanations: GP: Games Played; REC: Receptions; YDS: Receiving Yards; AVG: Yards Per Reception; YDS/G: Receiving Yards Per Game; LNG: Long Reception; TD: Receiving Touchdowns; FUM: Receiving Fumbles; LST: Receiving Fumbles Lost.

### Defense: Downs

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/defense/stat/downs/table/miscellaneous/sort/firstDowns/dir/desc)

Rendered header groups and columns:

```text
TEAM
FIRST DOWNS	THIRD DOWNS	FOURTH DOWNS	PENALTIES
GP	TOTAL	RUSH	PASS	PEN	MADE	ATT	PCT	MADE	ATT	PCT	TOTAL	YDS
```

Header explanations: GP: Games Played; TOTAL: Total 1st downs; RUSH: Rushing 1st downs; PASS: Passing 1st downs; PEN: 1st downs by penalty; MADE: Third Down Conversions; ATT: Third Down Attempts; PCT: 3rd down %; MADE: Fourth Down Conversions; ATT: First Downs Attempts; PCT: 4th down %; TOTAL: Total Penalties; YDS: Total Penalty Yards.

### Special teams: Returning

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/special/stat/returning/table/returning/sort/yardsPerKickReturn/dir/desc)

Rendered header groups and columns:

```text
TEAM
KICKOFFS	PUNTS
GP	ATT	YDS	AVG	LNG	TD	ATT	YDS	AVG	LNG	TD	FC
```

Header explanations: GP: Games Played; ATT: Kick Returns; YDS: Kick Return Yards; AVG: Yards Per Kick Return; LNG: Long Kick Return; TD: Kick Return Touchdowns; ATT: Punt Returns; YDS: Punt Return Yards; AVG: Yards Per Punt Return; LNG: Long Punt Return; TD: Punt Return Touchdowns; FC: Punt Return Fair Catches.

### Special teams: Kicking

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/special/stat/kicking/table/kicking/sort/fieldGoalPct/dir/desc)

Rendered header groups and columns:

```text
TEAM
FIELD GOALS	EXTRA POINTS
GP	FGM	FGA	FG%	LNG	1-19	20-29	30-39	40-49	50+	XPM	XPA	XP%
```

Header explanations: GP: Games Played; FGM: Field Goal Made; FGA: Field Goal Attempts; FG%: Field Goal Percentage; LNG: Long Field Goal Made; 1-19: 1-19 yard field goals; 20-29: 20-29 yard field goals; 30-39: 30-39 yard field goals; 40-49: 40-49 yard field goals; 50+: 50+ yard field goals; XPM: Extra Points Made; XPA: Extra Point Attempts; XP%: Extra Point Percentage.

### Special teams: Punting

[ESPN source](https://www.espn.com/nfl/stats/team/_/view/special/stat/punting/table/punting/sort/grossAvgPuntYards/dir/desc)

Rendered header groups and columns:

```text
TEAM
GP	PUNTS	YDS	LNG	AVG	NET	BP	IN20	TB	FC	RET	RETY	AVG
```

Header explanations: GP: Games Played; PUNTS: Punts; YDS: Punt Yards; LNG: Long Punt; AVG: Gross Average Punt Yards; NET: Net Average Punt Yards; BP: Punts Blocked; IN20: Punts Inside 20; TB: Touchbacks; FC: Fair Catches; RET: Punt Returns; RETY: Punt Return Yards; AVG: Average Punt Return Yards.

## Proposed Paydirt organization

Use the three-column Offense / Defense / Special teams directory, with the thirteen categories above leading to focused sortable team tables. Retain team receiving and receiving defense. Add rushing defense access within defense even though the reviewed directory does not have a separate rushing link. Use grouped headers for totals, downs, turnovers, returns, and kicking. Explain abbreviations with accessible labels/tooltips and retain raw numeric sorting.

## Capture and semantics work

Existing persisted counters cover pass attempts/completions/touchdowns, gross and net passing yards, sacks and sack yards, interceptions, rush attempts/yards, first downs, penalties, giveaways, and field-goal attempts/makes by distance. Opponent production supplies many defensive counterparts. Scores supply points for/against. Receiving receptions, gross yards and yards/reception can be derived from the corresponding offensive passing counters, with explicit definition tests.

Additional complete persisted counters are required before presenting longest plays; rushing touchdowns and rushing/receiving fumble splits; first downs by source and third/fourth-down attempts/conversions; extra-point attempts/makes and longest made field goal; and the return/punting breakdowns in the inventory. Existing logs or scoring events may contain some inputs, but their completeness and save/load behavior must be audited rather than assumed.

ESPN labels team passing YDS as net passing yards while receiving YDS is receiving yardage. Keep those definitions distinct. NFL passer rating uses gross passing yards and excludes sacks from attempts; it is not ESPN Total QBR. Confirm each efficiency denominator independently rather than infer it from an abbreviated label. The receiving touchdown/fumble treatment also needs explicit tests for recovery touchdowns and retained/nullified penalties.

## NFL passer-rating definition

For nonzero attempts, calculate `(COMP/ATT - .3)*5`, `(YDS/ATT - 3)*.25`, `(TD/ATT)*20`, and `2.375 - (INT/ATT)*25`; clamp each to [0, 2.375], sum, divide by six, and multiply by 100. Use gross passing yards. Aggregate inputs before calculating season rating. With zero attempts display unavailable. The exact maximum is 158.333..., conventionally displayed as 158.3. [Pro Football Hall of Fame reference](https://www.profootballhof.com/news/nfl-s-passer-rating).

## Delivery safeguards

Start with regression tests for new counters and their penalty/turnover edge cases, then persist through native and browser checkpoints, final results, campaign aggregation, and export/import. Add the category navigation and focused tables against that contract. Legacy missing data remains unknown unless a separately verified recovery is possible. This review changes no game state or production behavior.

## Preview implementation, November 19

Added all thirteen category destinations to the team-statistics directory, with focused sortable tables for existing counters. The full overview tables remain accessible. Punting and Returning explicitly report that capture is pending. Category notes identify missing detailed counters rather than imply full ESPN statistical parity. No engine counters or save formats changed in this preview step.

Test-first baseline: the new directory/navigation regression failed on the absent navigation landmark; all 28 existing component controls passed. After implementation all 29 focused component tests passed, with no existing expectation changes.

Preview validation: all 575 frontend tests passed across 71 files. SeasonDesk coverage measured 90.31% lines and 87.72% branches; remaining gaps are existing management/modal/error paths. The production build, documentation test and whitespace check passed. Chromium verified the live preview category tables, receiving-column numeric sorting, pending-capture messages and 390px phone page containment. Browser screenshots remain in ignored review evidence. No push or full-regression qualification is claimed. Build output retains existing Browserslist-age and mixed static/dynamic import warnings.

Final browser validation: all five season acceptance tests passed, including the new persisted public-sample campaign navigation/sorting/responsive-layout check. Screenshot review caught a general navigation CSS rule overriding the directory grid; an explicit failing browser geometry assertion preceded the specificity fix. The phone stacking assertion likewise exposed a media-rule specificity conflict, corrected without weakening the assertion. The new sorting fixture was amended to simulate real games before asserting a numeric default direction: its initial all-unknown counters provided no numeric type evidence. An initial E2E launch used system Python 3.9 and failed importing pairwise; the final successful run explicitly used the repository Python 3.12 environment. Existing test assertions were unchanged.

## Compact headers and leader overview, November 19

Implemented GP, CMP, ATT, CMP%, YDS, AVG and other abbreviated team-statistic headers. Full meanings remain in accessible header/button labels and button titles; overview passing/rushing prefixes disambiguate shared labels. Reduced cell padding and coverage font size. The main offensive overview now includes five category cards (total offense, passing, rushing, scoring and total defense), each with up to five backend-ranked teams and per-game values; ties retain backend ranks, and missing categories show an empty-state message. No new engine calculation or persistence format is introduced.

Test-first baseline: new regression failed because Pass attempts had not become ATT, with 29 existing tests passing. All 576 frontend tests now pass; SeasonDesk line coverage is 90.81%, branch coverage 88.62%, with remaining gaps in existing management/modal/error paths. Five real-engine season browser checks, production build, documentation test and whitespace check pass. Existing test selectors now read full accessible header labels rather than visible full-name text, because visible labels are deliberately abbreviated; all numeric, coverage and ordering assertions are retained. Browser checks also verify GP/CMP and the five leader lists. At a 1440px viewport, live Passing, Rushing and Receiving tables each fit their 1126px container without horizontal overflow; phone page containment also passed. Evidence/screenshots are in ignored ESPN review storage. Existing build/tooling warnings remain unchanged.

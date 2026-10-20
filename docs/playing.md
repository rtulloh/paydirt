# Playing in the Terminal

[Documentation index](README.md) · [Browser controls](web-interface.md) · [Clock management](clock-management.md)

## How to Play

From the repository root with [dependencies installed](installation.md):

```sh
python -m paydirt --play --compact
```

Choose your team, opponent, and home/away side, then follow the opening prompts.
Or choose teams explicitly (the example controls the home Thunderhawks):

```sh
python -m paydirt --play --compact -d easy --home 2026/Thunderhawks --away 2026/Ironclads
```

### Command Line Options

| Option | Purpose |
|--------|---------|
| `-p`, `--play` | Start interactive CLI play |
| `-d LEVEL` | CPU difficulty: easy, medium (default), or hard |
| `-c`, `--compact` | Abbreviated display |
| `--home YEAR/Team`, `--away YEAR/Team` | Select teams |
| `--playoff-game` | Use the selected season's playoff overtime rules |
| `--week N` | Week number when recording standings |
| `--load [file]` | Resume a CLI save; put this command first |
| `-a AWAY HOME`, `--auto AWAY HOME` | CPU-vs-CPU game, away team first |
| `--teams` | List locally available teams |
| `--simulate` | Run season simulation |
| `--scaffold-season YEAR` | Create starter season rules |
| `--help` | Show the CLI's command reference |

Automatic games use balanced AI; passing `-d hard` to `--auto` does not enable interactive Hard analysis.
For a public-team CPU game:

```sh
python -m paydirt --auto 2026/Ironclads 2026/Thunderhawks
```

### Reading the Display

Each play reports quarter/time, score, possession, field position, down/distance, and timeouts.
Compact traces show chart/dice details alongside the engine's result description.
Read the outcome, not just the offensive chart entry: defense, priority rules, penalties, and secondary rolls can change it.
Use `/` to view current statistics.

### Calling Plays on Offense

| Key | Play | General purpose |
|-----|------|-----------------|
| `1` | Line Plunge | Inside run |
| `2` | Off Tackle | Run outside the guard |
| `3` | End Run | Outside run |
| `4` | Draw | Delayed run |
| `5` | Screen | Short pass behind the line |
| `6` | Short Pass | Short route |
| `7` | Medium Pass | Intermediate route |
| `8` | Long Pass | Deep route |
| `9` | T/E S/L | Tight-end short/long route |
| `Q` | QB Sneak | Short-yardage attempt |
| `H` | Hail Mary | Desperation pass, subject to engine restrictions |
| `S` | Spike Ball | Standalone clock-stopping play; consumes a down |
| `K` | QB Kneel | Run clock while conceding yardage |
| `P` | Punt | Kick away possession |
| `F` | Field Goal | Attempt a kick |

Play names describe calls, not guaranteed yardage. Team charts determine their results.

| Control | Action |
|---------|--------|
| Enter | Accept the displayed default |
| `?` | Show the full menu in compact mode |
| `N` | Toggle no-huddle |
| `/` | View statistics |
| `W` | Save the CLI game |
| `Z` | Toggle the Easy-mode coaching helper |
| `+`, `-`, `T`, `S` suffix | Request a [clock modifier](clock-management.md), for example `7T` |

### Calling Plays on Defense

| Key | Formation | General purpose |
|-----|-----------|-----------------|
| `A` | Standard | Balanced |
| `B` | Short Yardage | Defend short runs |
| `C` | Spread | Spread coverage |
| `D` | Short Pass | Defend quick passes |
| `E` | Long Pass | Defend deep routes |
| `F` | Blitz | Pressure with coverage risk |

Add `T` to request a defensive timeout after the play, for example `AT`.
`/`, `W`, and the Easy helper toggle are also available at defensive play selection.

### Fourth Down and Special Teams

On fourth down, punt, attempt a field goal, or call an offensive play to go for the first down.
Where a separate fourth-down menu offers `G`, select it to proceed to play selection;
in compact play selection, enter the desired play directly.
Early-down punts and field goals are also offered.

After a touchdown, kick for one point or try for two if the season rules permit it.
Availability is controlled by [season YAML](seasons.md#season-rules), not just the year in the team name.
Conversion points belong to the touchdown's quarter, even if the live clock has
already advanced. The CPU keeps its own touchdown and accepts an eligible replay
penalty that erases an opponent's touchdown when that score is known at decision time.
On kickoff selection, `K` is the normal kick and `O` requests an onside kick. The kicking team
rolls for the kick distance and the receiving team then rolls its own dice for the return; the
compact trace shows both (`KO:` and `RT:`, or `RT:none` when the kick is not returned). Follow the current prompt;
an onside attempt does not guarantee recovery.

Return charts (kickoff, punt, interception, and fumble/blocked-kick returns) follow one
procedure. `OFF` is a foul by the returning team and `DEF` a foul by the other team: the
return is rerolled for its result and the penalty is then assessed automatically against the
end of the return — backward for `OFF` (a return touchdown is wiped out and the ball placed
that many yards short of the goal line), forward for `DEF` (never a penalty touchdown) —
with half the distance applied near either goal line. Possession is never changed by a return
penalty, and there is nothing to accept or decline. Two fouls by the same team keep the larger
one; fouls by both teams nullify the whole play: a kick is re-kicked and a turnover or blocked
kick is replayed from the previous spot, with ten seconds run off. A fumble cell on a return is
resolved with the returning team's recovery roll; 17–19 (kept) or 37–39 (lost) give the
recovering team a fumble return on its interception-return chart, which can chain further.
The one decision on a return: when the reroll after a returning-team foul is a fumble that the
other team recovers, that team keeps the recovery or takes the penalty (which gives the ball
back to the returning team, backed up). Kickoffs prompt for it; the CPU keeps the recovery.

### Quick Play with Defaults

Press Enter to accept the choice shown in each prompt, including plays and formations.
Defaults vary with down, distance, and context; they are conveniences, not a promise of optimal strategy.

## Play Resolution

1. The offense calls a play and the defense selects a formation.
2. Offensive and defensive dice select chart entries.
3. The [priority chart](priority-chart.md) combines those entries.
4. Secondary rolls, penalties, and special-play procedures apply as required.
5. The engine updates field position, possession, statistics, scoring, and time.

Common results include gains/losses, incompletions, interceptions, fumbles, breakaways, and penalties.
A BLACK offensive entry is not necessarily the final result; the defensive entry and priority chart still matter.
Asterisks and daggers mark sideline results; actual clock treatment depends on the situation.
See the [player priority reference and worked examples](priority-chart.md) for the combination table.

For an offensive fumble recovery with an advance, the action line separates yards before
the fumble, the recovery location, and yards advanced afterward. Recovery rolls 17–19
(offense) and 37–39 (defense) use the interception-return chart; a 39 is a chart return
like any other, and 19/39 are automatic touchdowns only on blocked kicks. The chart value
is not necessarily the actual advance, which stops at the goal line. Compact transaction
traces label the recovery roll (`R:`), advance roll and actual yards (`Ret:`), rerolls
(`Ret reroll:`), fumble returns (`FR:`), and raw chart result separately.
The defensive call is confirmed once as `Defense: Long Pass (E)`, for example; the
following `Offense runs:` line identifies the opponent's actual call.

An ordinary offensive recovery at the fumble spot has no extra advance; its action
line labels the yards before the fumble and the net result. QB-time scrambles are
rushing actions even when the original call was a pass. Incomplete passes are
labeled separately from completed passes or runs for no gain, including penalty
choices. Non-scoring breakaways do not guarantee a touchdown.

CLI result output announces each touchdown, safety, made field goal, and first down
once, while keeping chart evidence in the technical details. An intentional QB kneel
uses the engine's kneel description rather than ordinary tackled-loss commentary. Goal-to-go
status shows one location, for example `1st & Goal @ AWAY 6`.

Turnover-on-downs results and pass-interference first downs are announced once
in the final play output; penalty-choice previews and scoring summaries remain separate.

Colorful narration uses a separate random stream: displaying or reformatting a play
does not advance the game's dice/coaching RNG. Seeded interactive games from older
versions can consequently follow different sequences; rendering no longer affects
future game outcomes.

## Game Rules

- Four 15-minute regulation quarters; overtime follows the home team's season rules.
- Four downs to gain ten yards, or reach the goal line in goal-to-go situations.
- Failing on fourth down turns over possession. Offsetting penalties replay the same down without
  changing possession; a replayed fourth down is not a turnover on downs.
- Touchback placement depends on the event and applicable engine rules; do not assume every touchback is at the 20.
- Time depends on the play result and applicable modifiers; see [Time Management](clock-management.md).
- A touchdown on the last play of a half or of regulation still gets its try; the scoring team does not
  kick off afterwards, and a half-ending safety has no free kick. The second-half kickoff follows at halftime.

| Score | Points |
|-------|--------|
| Touchdown | 6 |
| Extra-point kick | 1 |
| Two-point conversion, when enabled | 2 |
| Field goal | 3 |
| Safety | 2 |

## Strategy Tips

Mix runs and passes, then use your team's actual chart strengths rather than relying on play names alone.
Short-yardage runs and sneaks can be useful near the line to gain. Long yardage may favor passing,
but screens and draws can also exploit defensive expectations.

Standard is a balanced defensive starting point. Consider Short Yardage against short runs,
Short Pass against quick routes, or Long Pass against deep threats. Blitzes trade coverage for pressure.
No formation is universally best.

When trailing late, preserve time with no-huddle, sideline calls, and timeouts.
When leading late, protect possession and consider runs, kneels, and in-bounds calls.
See [clock management](clock-management.md) before combining modifiers.

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
On kickoff selection, `K` is the normal kick and `O` requests an onside kick. Follow the current prompt;
an onside attempt does not guarantee recovery.

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

## Game Rules

- Four 15-minute regulation quarters; overtime follows the home team's season rules.
- Four downs to gain ten yards, or reach the goal line in goal-to-go situations.
- Failing on fourth down turns over possession.
- Touchback placement depends on the event and applicable engine rules; do not assume every touchback is at the 20.
- Time depends on the play result and applicable modifiers; see [Time Management](clock-management.md).

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

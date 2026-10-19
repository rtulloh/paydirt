# AI Difficulty and Coaching

[Documentation index](README.md) · [CLI controls](playing.md) · [Clock management](clock-management.md)

Choose difficulty in the browser setup or use `-d easy`, `-d medium`, or `-d hard` with CLI `--play`.
Medium is the default. Difficulty changes decisions and coaching, **not dice odds**.

## Difficulty Levels

| Mode | Aggression | Main distinction |
|------|------------|------------------|
| Easy | 0.3 | Conservative CPU and CLI player coaching |
| Medium | 0.5 | Balanced CPU with a coarse early-down run/pass strength adjustment |
| Hard | 0.7 | Aggressive CPU, weighted individual-play chart analysis, recent-call variety, and opponent-tendency tracking |

Aggression influences decisions such as going for it on fourth down and attempting longer field goals.
Special situations still have their own policy. Hard is not an always-optimal opponent and does not
always choose the highest chart average.

## Easy Player Coaching

The CLI helper is available in **Easy mode**, enabled by default. Use `Z` at play selection to toggle it.
It is not currently available in Medium/Hard CLI games. These keyboard controls do not imply a browser helper panel.
Use `?` for the full compact-mode menu and `/` for statistics.

The offensive helper ranks up to three callable plays using a down-and-distance target:

| Down | Target yardage |
|------|----------------|
| First | Half the distance to gain |
| Second | 70% of the distance to gain |
| Third/fourth | The full distance to gain |

Targets are rounded up and never lower than one yard. The display reports target-reaching percentage,
positive-gain percentage, average yards, and evaluated chart coverage, plus separate situation/clock tips.
For example, second-and-seven has a five-yard target; third-and-seven has a seven-yard target.

### Reading the Estimates

These are dice-weighted estimates from **plain numeric offensive chart cells only**.
Missing rows, penalties, turnovers, breakaways, BLACK, and other symbolic results are excluded.
They do not resolve a particular defense, the priority chart, or secondary procedures.

- Target rate and average yardage are conditional on the evaluated numeric cells.
- Coverage describes how much chart probability was evaluated, not a confidence interval.
- Coverage below 50% is marked limited and ranks behind better-supported estimates.
- A perfect rate over sparse coverage is not evidence of guaranteed success.

These are **not full-engine conversion odds**. Defensive helper suggestions are situational advice;
do not treat them as an adaptive model learning the CPU's calls during CLI play.

## Medium Team Strengths

On ordinary first and second downs, Medium can shift its existing run/pass probability by **ten percentage points**
toward the stronger category. It retains variety among plays within the category.

The summary averages each callable play's dice-weighted known positive-gain mass equally within run/pass categories.
Both categories must have at least 50% numeric coverage, and their difference must exceed five percentage points.
Without enough evidence, Medium retains its existing mix.

Ordinary third/fourth-down, red-zone, goal-line, clock-killing, and timeout policies
are not changed by this adjustment. Hurry-up uses a small supported run-strength
bias on early downs, then applies the shared urgency preference below.
Medium does not use Hard's opponent model.

## Hard Chart Analysis

On ordinary first, second, and third downs, Hard samples a weighted mixture of competitive
offensive plays rather than repeatedly overriding its call with one chart winner. All nine
primary offensive plays use the same policy; B and QT are secondary tables, never standalone calls.
Goal-line, red-zone, fourth-down, and clock-killing policies still take precedence
outside hurry-up; hurry-up reuses the chart/history mixture with urgency weighting.

The chart score favors reaching half the distance on first down, 70% on second down,
and the full distance on third down (rounded up, at least one yard). It also considers
bounded numeric progress/losses and known interception, fumble, and offensive-penalty risk.
Dice-weighted outcomes retain their full probability mass: failures and risks are not
removed to inflate the apparent chance of a gain. Missing or unresolved results, including
breakaways, QB-time, variable yardage, and defensive penalty effects, receive neutral
coaching value rather than invented yardage or extra random rolls. These scores are
conservative heuristics, **not full-engine conversion probabilities or expected points**;
they do not simulate the current defense or complete secondary procedures.

Recent executed calls in similar down/distance situations modestly reduce a play's weight.
The adjustment fades as the team makes other calls and never bans a play or forces a
predictable rotation. A clearly superior call can still dominate when alternatives are poor.
There are no historical usage quotas and no penalties to the actual result of a repeated play.
Selection does not inspect the human's unrevealed defense. Hard also tracks opponent
run/pass tendencies to inform its own defensive choices. Recognized primary calls,
QB sneaks, and Hail Mary attempts count as run/pass choices. Punts, field goals,
kickoffs, kneels, spikes, unknown names, and secondary tables do not change those
totals or streaks—even if a caller labels them "not a pass." Previously saved
aggregate learning cannot be retroactively corrected without the original calls.

Call history is game-local and shared by the CLI and browser engine. Recommendations
and previews do not add calls; penalty rerolls belong to one executed call. CLI saves
preserve recent call history; older saves without it start with empty history. This is
separate from cross-game opponent learning and does not promise identical random
selections after save/resume. Easy and Medium do not use Hard's recent-call policy.

Analysis does not change gameplay dice odds or base timing, and a sensible call can still fail.
For experiment history, see the [AI play-testing notes](dev-notes/ai-playtesting.md).

## Shared Clock Policy

All three modes use the same offensive and defensive timeout thresholds and accounting.
Neither aggression nor Hard analysis changes those thresholds. See [clock management](clock-management.md)
for timeout ownership, stopped-clock safeguards, and modifier interactions.

### Hurry-Up Play Choice

No-huddle pace does not mean pass-only play calling. A two-score fourth-quarter
comeback can retain credible runs while time remains. Passing preference increases
with the number of scores needed (respecting the season's two-point-conversion
availability) and dwindling time, but no clock threshold bans
runs. Hard retains chart strengths, down/distance targets, and recent-call variety;
Easy/Medium use a situational mixture. Goal-line/red-zone hurry-up excludes long
routes. Victory formation, last-chance Hail Mary, fourth-down decisions, and timely
field goals keep their existing priority. The weights are coaching heuristics, not
historical usage targets or new timing rules.

Normal `--auto` CPU-vs-CPU games use balanced AI and do not exercise interactive Hard chart analysis,
even if `-d hard` is also supplied.

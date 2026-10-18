# AI Difficulty and Coaching

[Documentation index](README.md) · [CLI controls](playing.md) · [Clock management](clock-management.md)

Choose difficulty in the browser setup or use `-d easy`, `-d medium`, or `-d hard` with CLI `--play`.
Medium is the default. Difficulty changes decisions and coaching, **not dice odds**.

## Difficulty Levels

| Mode | Aggression | Main distinction |
|------|------------|------------------|
| Easy | 0.3 | Conservative CPU and CLI player coaching |
| Medium | 0.5 | Balanced CPU with a coarse early-down run/pass strength adjustment |
| Hard | 0.7 | Aggressive CPU, individual-play chart suggestions, and opponent-tendency tracking |

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

Third/fourth-down decisions, red-zone and goal-line choices, hurry-up, clock-killing, and timeout policies
are not changed by this adjustment. Medium does not use Hard's opponent model.

## Hard Chart Analysis

Hard mixes chart-based individual-play suggestions into ordinary offensive selection on 40% of selections,
alongside situational playcalling. It tracks opponent run/pass tendencies by situation to inform defensive choices.
Hard's existing chart metrics differ from the Easy numeric-only estimates: for example, BLACK is counted as a
zero-yard failure in the existing conditional Hard metrics.

Chart analysis is not a complete simulation of conversion probability, turnover risk, or expected points.
It does not change dice rolls, and a sensible call can still fail.
For an experiment evaluating this behavior, see the [AI play-testing notes](dev-notes/ai-playtesting.md).

## Shared Clock Policy

All three modes use the same offensive and defensive timeout thresholds and accounting.
Neither aggression nor Hard analysis changes those thresholds. See [clock management](clock-management.md)
for timeout ownership, stopped-clock safeguards, and modifier interactions.

Normal `--auto` CPU-vs-CPU games use balanced AI and do not exercise interactive Hard chart analysis,
even if `-d hard` is also supplied.

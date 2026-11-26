# AI Difficulty and Coaching

[Documentation index](README.md) · [CLI controls](playing.md) · [Clock management](clock-management.md)

Choose difficulty in the browser setup or use `-d easy`, `-d medium`, or `-d hard` with CLI `--play`.
Medium is the default. Difficulty changes decisions and coaching, **not dice odds**.

## Difficulty Levels

| Mode | Aggression | Precision | Main distinction |
|------|------------|-----------|------------------|
| Easy | 0.3 | Bounded, fallible | Conservative CPU and CLI player coaching |
| Medium | 0.5 | Slightly fallible | Balanced CPU with a coarse early-down run/pass strength adjustment |
| Hard | 0.6 | Bounded, near-exact | Aggressive CPU, weighted individual-play chart analysis, recent-call variety, and recency-weighted opponent-tendency tracking |

Aggression influences decisions such as going for it on fourth down and attempting longer field goals.
Special situations still have their own policy. Hard is not an always-optimal opponent and does not
always choose the highest chart average.

## Fourth-Down Field Goals

The CPU no longer uses fixed 1983 distance tiers for every season. It asks the
core engine for the possession team's dice-weighted chance to convert the kick
from the current line of scrimmage to the goal line. That probability comes from
the kicking team's own Field Goal column: rows are weighted by the chart dice,
penalty rows are rerolled and renormalized away, and blocked kicks, fumbled
snaps, no-good cells and empty cells count as misses. The decision therefore
differs between a weak historical chart and a stronger modern chart in the same
down, distance, score and clock situation.

Coaching bands turn that make probability into an ordinary fourth-down choice:

| Make probability | Coaching band | Ordinary choice |
|------------------|---------------|-----------------|
| 0.70 or higher | Routine | Kick, except a fourth-and-inches exception deep in the red zone at extreme aggression |
| 0.35 up to 0.70 | Worth taking | Kick unless a short conversion is attractive |
| 0.15 up to 0.35 | Long but plausible | Short yardage and aggressive coaches may try it; otherwise punt |
| Below 0.15 | Outside plausible range | Punt or go for it according to field position and distance |

The season's `ai_behavior.strategic.fourth_down_aggression` sets the era
baseline. Difficulty shifts that value by −0.2 for Easy, 0 for Medium and +0.1
for Hard, clamped to `[0, 1]`. Late-game rules still override the bands: a kick
that can tie or win in the final seconds, an end-of-half kick with little time
left, a multi-score urgency decision, victory formation and last-chance Hail
Mary retain their own policies.

Charts without resolvable Field Goal rows (mock or partial charts in tests and
legacy callers) use a documented distance-based fallback curve. Normal charted
games do not take that path. The estimate never rolls gameplay dice. It models
the non-penalty continuation: if the kick draws a foul, the engine still offers
the offended team its normal choice among the kick result and the penalty, and
that later choice is not folded back into the pre-kick probability.

## Last-Possession Fourth Downs

When the CPU trails in the fourth quarter with at most two minutes left, an
ordinary fourth-down decision that cannot take a tying or winning field goal is
reviewed again against the clock. Inside 30 seconds, the shared policy selects a
clock-stopping conversion plan rather than the ordinary short-yardage mixture.
That window is the engine's longest no-huddle snap (25 seconds) plus a quick
next snap (5 seconds), not a claim that every 31-second situation is safe.

The plan still begins only after victory formation, end-of-half field goals,
Hail Mary attempts, and makeable tie/win kicks have had priority. It uses the
remaining score deficit, season two-point rules, field position, and distance to
convert:

- Outside the goal line, short and medium distances favor Short Pass, Screen,
  T/E Short/Long and Medium Pass. Long yardage favors Medium Pass, Long Pass
  and T/E Short/Long, because a short completion plus the sideline cost is
  unlikely to convert.
- Near the goal line, a short run remains available only when a touchdown ties
  or wins. If another score is still required, the plan prefers a pass that can
  stop the clock.
- No-huddle is always requested in this branch, and every pass receives the
  sideline designation. The plan does not assume a following offensive timeout:
  the auto-game caller does not request one, so the designation's five-yard cost
  is the clock safeguard that all callers actually honor. A caller that also
  requests a timeout (the web backend) still pays the five yards, while the
  engine correctly skips the now-redundant timeout. A designation cannot save a
  sack or a fumble; those results can still end the period.

This is a bounded coaching rule, not a win-probability model. It does not
change dice odds, resolve a hypothetical defense, or guarantee a successful
conversion. The audit mode is `Last-Possession 4th Down`, distinct from an
ordinary `4th Down` call.

## Decision Precision

Difficulty is not only aggression. Every mode may misjudge a marginal
fourth-down kick in two bounded ways:

- **Optimism:** Easy adds 0.05, Medium adds 0.02 and Hard adds 0.0075 to the
  chart probability, modelling a coach who slightly overrates a marginal kicker.
- **Band confusion:** when the adjusted probability is within 0.06 of a decision
  threshold, Easy has a 30% chance, Medium a 12% chance and Hard a 4% chance to
  misread it by up to 0.06.

The adjustment applies only to the ordinary field-goal bands below. It does not
touch last-second tie/win kicks, end-of-half kicks, urgent multi-score drives,
victory formation, Hail Mary attempts, play legality, scores or an endgame rule.
It can move a borderline call at most one band, so an obvious kick or punt stays
obvious. The noise uses its own decision stream: it does not consume or change
the gameplay dice, and a balanced auto game (the legacy `ComputerAI` baseline)
has no precision profile.

The values are coaching heuristics, not calibrated estimates of human error.
They are deterministic under a controlled decision-stream seed and are intended
to make Easy and Medium less precise than Hard on marginal calls without
changing dice odds or the core engine's resolution.

Hard's profile is deliberately tiny: it can move only a borderline ordinary
call, while last-second and endgame rules remain exact. The aggregate error
still orders Easy above Medium above Hard.

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
For fourth down the decision itself takes precedence, and a conversion attempt then
uses that same hurry-up mixture rather than a separate go-for-it table.

The chart score favors reaching half the distance on first down, 70% on second down,
and the full distance on third down (rounded up, at least one yard). It also considers
bounded numeric progress/losses and known interception, fumble, and offensive-penalty risk.
Dice-weighted outcomes retain their full probability mass: failures and risks are not
removed to inflate the apparent chance of a gain. Missing or unresolved results, including
breakaways, QB-time, variable yardage, and defensive penalty effects, receive neutral
coaching value rather than invented yardage or extra random rolls. These scores are
conservative heuristics, **not full-engine conversion probabilities or expected points**;
they do not simulate the current defense or complete secondary procedures.

When the CPU intercepts in its own end zone, it applies one shared depth/score/clock
policy instead of a pre-game preference. Shallow catches return unless a late multi-score
lead argues for avoiding return risk; catches five or more yards deep take the touchback.
The policy cannot see return dice, and the same function serves CLI, web and engine `auto`
mode. A human can still choose after seeing the engine-reported catch depth, score and clock.

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

### Hard Defense

Hard's defensive call keeps situational coaching authoritative. Goal-line, red-zone,
prevent and two-minute situations are evaluated before the opponent model, so a
formation such as Short Yardage remains available inside the five even when the
model expects a pass. On third down, and on fourth down with four or more yards to
go, the coach blends the model with the situational call: roughly 70% model and 30%
situational coaching. The blend still respects the season's formation legality and
never reveals the human's unrevealed offense.

Fourth-and-short (one to three yards) is a **base-rate call** instead of a blend.
A punt or field goal ignores the defensive formation, so the old
"likely to kick, play Standard" rule protected nothing; a genuine fourth-and-short
attempt is a run situation even when the opponent has shown no tendency yet.
Hard therefore uses a fixed run-leaning base rate — roughly 72% Short Yardage,
18% Blitz, 7% Standard and 3% Short Pass — and only mixes in the opponent model
once at least three calls exist in that exact bucket. Sparse evidence is ignored
rather than blended, because the neutral prior's Standard answer is not a tendency
read. The rule is symmetric for both teams and changes no dice odds.

The opponent model uses a recency window of the last 20 calls in the same
down/distance situation, exponential decay of 0.88 per call, and a neutral prior
of four weighted run and pass observations. Sparse evidence therefore stays close
to balanced rather than pretending to be a strong tendency. On obvious passing
downs (third or fourth and seven or more), the model keeps a bounded minority
share for Long Pass and Blitz instead of collapsing every call onto one pass
defense. A 9% second-choice mechanism occasionally selects the next-best
formation, so Hard is less predictable without becoming random. These are coaching
heuristics, not new dice probabilities or defensive-formation quotas.

Call history is game-local and shared by the CLI and browser engine. Recommendations
and previews do not add calls; penalty rerolls belong to one executed call. CLI saves
preserve recent call history; older saves without it start with empty history. This is
separate from cross-game opponent learning and does not promise identical random
selections after save/resume. Easy and Medium do not use Hard's recent-call policy.

Analysis does not change gameplay dice odds or base timing, and a sensible call can still fail.
For experiment history, see the [AI play-testing notes](dev-notes/ai-playtesting.md).

## Penalty Choices

When an ordinary scrimmage gain already earns a first down, CPU coaching
compares it with the engine-projected first-down penalty options. It keeps
the most advanced resulting spot, retaining the play on a tie. An automatic
first-down flag does not outweigh a longer gain that also earns first down.
Comparisons use actual enforcement, including half-distance and pass
interference spots, without applying state or consuming dice.

This comparison does not override the existing end-of-half policy within
the last 45 seconds of the second, fourth, or overtime periods: a retained gain may
expire the period while a defensive penalty can preserve time or an untimed
down.

When the defense is offended by an offensive foul, CPU coaching compares the
retained play with each engine-projected enforcement rather than testing only
whether the play gained yardage. It ranks the resulting situations by yards the
offense still must cover to reach the defense's goal, then by the down, then by
the distance to convert, so an incomplete first-down pass becomes first-and-25
instead of second-and-10 at the same spot, and a half-distance foul that moves
the ball only a short way is priced at its real spot. The play is kept unless
enforcement is strictly better; a retained loss that exceeds the foul, a
retained score or safety, a fourth-down stop, a turnover, a fumble, or a
requested spike keeps its existing policy. This is a coaching ordering, not an
expected-points estimate, and it does not redesign kick/return penalty
choices, general clock management, or play-plus-spike decisions.

On a field-goal attempt the same principle applies to the score itself. A made
kick with an offensive foul no longer stands automatically: the offended defense
enforces the longest available foul and forces a longer re-kick instead of
conceding three points. A missed kick still keeps its existing policy, and the
kicking team keeps a made kick when it is the offended side.

A terminal made kick is not worth trading for a live down, so one engine-checked
guard stands ready to override enforcement. The engine projects both choices on
a throwaway copy, including the resulting score, clock, period, game-over and
untimed-down state, without touching live state, statistics, the play log or
dice. If keeping the kick ends the game with the defense ahead and enforcing the
foul leaves the game unfinished, the defense keeps the kick. RULE-005 removed
the phantom extension that made this guard necessary: an accepted offensive kick
foul no longer adds an untimed down, so enforcement itself expires the clock and
the guard no longer fires on the reported scenarios. It stays as a safety check
for any future rule that leaves enforcement live.

When the live game state is available, a trailing defense in the fourth quarter
adds one late-game check before enforcing an offensive foul. The engine projects
both resolutions, including the spot, down, distance, resulting clock, period,
game-over and untimed-down state, without applying statistics, the play log or
dice. Deferred timeout or spike requests are evaluated under the same
clock-stopped rule; a resolved flagged foul cannot use them to save more time.
If enforcement would leave the leading offense on first through third down
with enough clock to kneel out the game, while declining would preserve the
down and prevent that kneel-out, the defense keeps the play.
The check evaluates the engine's own `can_kneel_out_game` rule
on those post-decision projections; it does not model later play calls,
two-minute strategy or score attempts. A defense that already leads, overtime and
earlier periods keep the position/down ordering unchanged. CLI auto games, the
web backend and live-engine callers pass the game context; callers without it
retain the AI-002 heuristic.

## Two-Point Tries

CLI two-point play selection uses a separate, untimed conversion situation from
the engine: first-and-two at the opponent's two-yard line, worth two points.
The previous touchdown's field position, down, and clock cannot trigger a kneel,
spike, punt, or field-goal call. Easy samples the nine primary chart plays;
Medium and Hard weight competitive plays by bounded try-specific chart utility.
Reaching the goal is what matters: extra yards beyond it add no coaching value.
Missing/unresolved results keep their full dice mass with neutral value; known
turnover and fumble risks reduce the score. These remain coaching heuristics,
not defense-adjusted conversion odds. No hypothetical gameplay dice are rolled.

When the human goes for two in the CLI, the CPU chooses a goal-line formation
with a short-yardage preference, rather than always using Standard. When the
CPU goes for two, the human chooses A–F for the try. Ordinary clock-management
selection is not used by either conversion selector. A regulation touchdown
with a try still owed at 0:00 can prompt a two-point attempt when the season
rules allow it; a game-ending overtime touchdown cannot. The API PAT-choice
query also distinguishes an owed try from an already finished game.

## Season-Aware Late-Game Pace

In regulation Q4, a trailing CPU offense enters hurry-up below the configured multi-score threshold when the active season rules say the deficit requires at least two scoring possessions. The default threshold is 3:00, so exactly 3:00 remains ordinary. The score count uses eight points per possession when two-point conversions are available and seven when they are not. Thus, down eight at 2:59 is urgent in a no-conversion season but remains a one-possession situation in a conversion season.

This additional gate does not apply while tied or leading, in earlier quarters, or in overtime. When it applies, ordinary, analyzed, red-zone, goal-line, and fourth-down calls request no-huddle consistently; eligible passing calls retain the configured chance to use the sideline designation.

### Fourth-Down Pace

The fourth-down *decision* is evaluated before the two-minute drill, so a punt or field goal keeps its own priority. Once that decision selects a conversion attempt, the attempt uses the same pace and play mixture as first through third down:

- Either pace predicate enables no-huddle. The two-minute drill also covers the end of the second quarter and a Q4 deficit of at least 14 inside the configured `q4_always_minutes` window, so a fourth-down conversion in those states is not left on ordinary pace. A larger Q4 deficit during the rest of the quarter uses the same clock-based hurry-up gates as every other call.
- Hard's conversion attempt samples the hurry-up chart/history mixture instead of the separate go-for-it table, so the call still respects down, distance, chart strength and recent calls.
- The sideline designation is drawn from the coaching stream, never the gameplay dice.
- A punt or field goal keeps its pre-existing pace flagging; reaching the two-minute drill never turns a kick into a conversion.

`AI-037` tracks this. `AI-038` closes the former Q4 `-14` catch-all with the same clock bound described above.

## Shared Clock Policy

All three modes use the same offensive and defensive timeout thresholds and accounting.
Neither aggression nor Hard analysis changes those thresholds. See [clock management](clock-management.md)
for timeout ownership, stopped-clock safeguards, and modifier interactions.

A trailing defense keeps its one- and two-score timeout windows unchanged: four
minutes at an eight-point deficit and five minutes at fourteen. A
three-or-more-score deficit must also fit the remaining clock before a timeout
is spent. The estimate allows a bounded scoring drive for every needed score and
for the opponent's next score; it is coaching arithmetic, not a win estimate.
The 32-point fourth-quarter blowout from the 2026-11-25 play-test therefore keeps
its timeouts, while a one-score state still calls one. `AI-039` tracks this.

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


### Late multi-score fourth downs

With two to five minutes left in the final period, the shared fourth-down policy
estimates the time for the required scoring possessions plus a defensive stop.
Remaining offensive timeouts shorten that stop estimate, and current field
position affects the drive budget. When multiple scores are needed and punting
would consume that budget, fourth-and-ten or shorter can be attempted in the
team's own territory. Earlier games, one-score deficits and long-distance
controls retain the conservative policy. A makeable field goal remains useful
when its three points remove one required scoring possession. These are bounded
coaching estimates, not full-engine win probabilities; season two-point rules
determine whether a scoring possession can supply seven or eight points.

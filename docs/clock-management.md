# Clock Management

[Documentation index](README.md) · [CLI controls](playing.md) · [Browser controls](web-interface.md)

## Time Management

The engine applies play timing, warnings, timeouts, and period boundaries. Clock controls request particular
procedures; they do not guarantee another snap if time has expired. Base timing is not changed by difficulty.
The examples below use CLI input; the browser exposes corresponding play controls.

## Saving Time

| Control | CLI example | Effect and tradeoff |
|---------|-------------|---------------------|
| No-huddle | `N`, then a play | Eligible 40-second sequences become 20 seconds; may trigger the no-huddle penalty procedure |
| Out-of-bounds designation | `7+` | Eligible final-minutes play uses ten seconds, with the applicable five-yard offensive cost |
| Timeout after a play | `7T` on offense; `AT` on defense | Eligible preceding play is reduced to ten seconds and the requesting team is charged a timeout |
| Standalone spike | `S` | A separate short clock-stopping play that consumes a down |
| Play-plus-spike modifier | `7S` | Requests a spike after an eligible play; total play-plus-spike time is capped at 20 seconds |

No-huddle is not a universal halving of every play's duration. Likewise, a designation does not remove
turnovers, penalties, or scoring: the actual result determines which timing procedures apply.
The five-yard designation adjustment can turn a small gain into a loss.

## Keeping the Clock Running

| Control | CLI example | Tradeoff |
|---------|-------------|----------|
| In-bounds designation | `3-` | Keeps an eligible result in bounds, at the applicable five-yard cost |
| QB kneel | `K` | Concedes yardage to use time |
| Run | `1`–`4` | Usually keeps time moving, but the actual outcome still governs |

Do not combine `+` and `-` on one call. A play can still end a period or the game before another snap.

## Timeouts

Each team starts regulation halves with three timeouts; the budget resets at halftime.
Offense and defense can request them. Use a play/formation suffix (`7T` or `AT`);
entering `T` alone asks you to choose a play and is not a completed timeout call.

A timeout is charged only when the core engine applies it. Requests with no timeouts remaining must not
shorten a play for free. Incomplete passes, existing clock stops, possession changes, penalties,
and completed spike procedures can make a requested timeout unnecessary or inapplicable.
The same elapsed time must not be reduced twice by overlapping adjustments.

The CPU uses shared clock-preservation thresholds across difficulty levels. Easy does not deliberately
waste its timeout budget, and Hard does not receive a different timeout allowance.
Two-minute warnings in the second and fourth quarters are handled automatically.

## Spike Modifier and Combinations

`7S` means Medium Pass followed by the spike modifier. Unlike standalone `S`, the modifier does not
advance the down a second time. If applicable, the engine caps the first play at 17 seconds and
adds three seconds for the spike, for at most 20 seconds total.
It is skipped when the outcome already stops the clock or makes it inapplicable, such as an incompletion,
out-of-bounds result, or turnover.

Modifiers can be combined, for example `7+S` or `7ST`. A requested timeout takes precedence over
the spike modifier when applicable. Already-stopped outcomes do not justify an additional timeout charge.
Always read the resulting engine description and updated clock.

## Final Seconds Strategy

Before calling a play, check time, downs, field position, score, and remaining timeouts.

- Need to preserve time with a timeout available: consider `7T`.
- No timeout: consider no-huddle or `+`, accepting their tradeoffs; a standalone spike also spends a down.
- Need a field-goal attempt after a gain: `7S` can help only if enough time remains after the combined sequence.
- Need a touchdown on the last snap: consider a legal desperation pass, not a field goal that cannot overcome the deficit.

For example, with 30 seconds remaining, an eligible `7T` may leave about 20 seconds.
The next call must be chosen from the actual outcome and time remaining—not a scripted assumption that
there will be two more snaps. A 20-second play-plus-spike starting with exactly 20 seconds can leave **zero**.

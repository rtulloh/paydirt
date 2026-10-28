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

`7S` means **Medium Pass followed by a spike**, not a free clock stop.
The spike must carry a down cost. For a `7S` call made on **first down**, the agreed rule is:
when the completion and spike both apply, the next play is **third down**, **even if the pass earns a first down**.
An **incompletion needs no spike**; it leaves second down without an extra spike cost.
Penalties must be resolved before deciding the spike's effect on down and clock.

The engine charges the extra down only when the spike actually applies. It
skips the modifier after an incompletion, out-of-bounds play, score, or loss of
possession (including a failed fourth down). A third-down play that falls short
can leave fourth down, then the spike itself turns the ball over on downs. No
additional chart roll or invented yardage is added. The engine reports the
final down, possession and field position for both CLI and browser displays.

A pending foul preserves the S request without applying its down/clock effect
early. If the play is retained, eligibility is checked against that finalized
play; if the penalty is enforced or fouls offset, there is no subsequent spike.

**Remaining implementation mismatch:** offensive spike versus defensive timeout
priority is still tracked separately (SPIKE-002). The agreed timeout-priority
procedure below is not a claim that this remaining fix has shipped.

For an applied spike modifier, the existing timing procedure caps the first play at 17 seconds and
adds three seconds for the spike, for at most 20 seconds total. This timing cap does not make the spike free.
Standalone `S` is a separate spike play and also consumes a down. If the modifier
consumes the final seconds after a completion, normal period-end handling still
applies, including game completion, overtime eligibility, or a pending untimed down.

### Spike and Defensive Timeout Priority

The agreed resolution order is **penalty decision, applicable timeout, then the planned spike**.
An applicable defensive `AT` stops the clock before the spike: charge the defense's timeout and
cancel the spike, without charging a spike-related down. A request with no timeout available cannot cancel it.
On an incompletion, neither a spike nor a clock-saving timeout is needed.
The game log should identify the winning procedure, for example: **Defensive timeout; planned spike canceled.**

The current engine already gives an offensive timeout request precedence over a spike when both are requested
on the offensive call, such as `7ST`. Extending that priority to defensive requests is a pending fix;
do not infer that `7S` against `AT` is currently resolved correctly.

### Worked Spike Examples

All examples start on **first down**, with possession retained, no score ending the sequence,
and enough time for the stated actions. Rows without penalties assume none occurs.
Downs in this table describe the **agreed behavior**, subject to the implementation mismatch above.

| Calls and outcome | Spike / timeout treatment | Next play |
|-------------------|---------------------------|-----------|
| `7S`: complete for 4 yards on first-and-ten | Apply spike; if the completion is capped at 17 seconds plus a three-second spike, the total is 20 seconds | Third-and-six |
| `7S`: complete for 12 yards on first-and-ten | The first-down gain does **not** waive the agreed spike down cost | Third-and-ten at the new spot |
| `7S`: incomplete | No spike needed; no extra three seconds or spike down | Second-and-ten |
| `7S` against `AT`: complete for 4 yards; defense has an applicable timeout | Charge defense; use timeout timing instead of the spike sequence | Second-and-six; no spike-related down |
| `7S` against `AT`: complete for 4 yards; defense has no timeout left | Reject the unavailable timeout; apply the spike normally | Third-and-six |
| `7S` against `AT`: incomplete | No spike and no timeout charged | Second-and-ten |
| `7S` with a penalty flag | Resolve acceptance/declination and enforcement first | Follow the enforced down/distance and applicable spike procedure; do not blindly force third down |

For the first row, starting at 0:30 and using the full 20-second sequence leaves 0:10.
Starting with exactly 0:20 can leave **zero**, so a field-goal attempt is not guaranteed.
An out-of-bounds designation is not, by itself, the agreed reason to waive a called spike's down cost;
incompletions and penalty resolution must be distinguished from a completed pass. The defensive-timeout
cancellation above is the separately agreed exception.

## Final Seconds Strategy

Before calling a play, check time, downs, field position, score, and remaining timeouts.

- Need to preserve time with a timeout available: consider `7T`.
- No timeout: consider no-huddle or `+`, accepting their tradeoffs; a standalone spike also spends a down.
- Need a field-goal attempt after a gain: `7S` can help only if enough time remains after the combined sequence.
- Need a touchdown on the last snap: consider a legal desperation pass, not a field goal that cannot overcome the deficit.

For example, with 30 seconds remaining, an eligible `7T` may leave about 20 seconds.
The next call must be chosen from the actual outcome and time remaining—not a scripted assumption that
there will be two more snaps. A 20-second play-plus-spike starting with exactly 20 seconds can leave **zero**.

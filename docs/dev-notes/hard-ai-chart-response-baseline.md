# Hard AI chart-response baseline

Investigation checkpoint, 2026-11-06 06:40 CST. This records current behavior
and an unimplemented correction direction. It does not certify chart fit,
coaching strength or season qualification. See [AI-026](issues/AI/AI-026.md)
and [VAL-019](issues/VAL/VAL-019.md). Release remains held.

## Verified data flow

`create_computer_ai("hard", game, cpu_is_home)` stores the selected side's
complete chart in `TeamAnalyzer`, including its `DefenseAnalyzer`, and builds
`OffensiveStrategy` from that side's offense. The controlled baseline asserts
these identities for both home and away. Having a defensive analyzer does not
make the selection method consult it.

Ordinary `ComputerAI.select_defense` reads public down/distance, field position,
clock and score, then calls `OpponentModel.predict_defense` before the
non-analysis situational branches. The model stores observed run/pass categories
and game-state flags. Its ordinary recommendation comes from those categories;
it stores no chart or chart-derived prior. The late pressure override reads
state/rules and uses a separate RNG. Neither path reads the stored defense
analyzer or opposing offense chart. This confirms more than a missing argument.

Ordinary Hard offense asks `OffensiveStrategy.weights` for utilities based on
its own offense chart plus comparable call history. That strategy stores only
the offense chart; its scoring/cache has no opponent defense or defensive
formation mixture. The ordinary caller also supplies no such information.
Two-point and special/clock situations are separate paths and are not claimed
fully covered by this baseline.

The production auto loop creates both home/away AIs through its supplied
factory; the historical Hard factory delegates to `create_computer_ai`. It
chooses the defender from current possession and calls that configured instance.
Interactive new/resumed games and web new/replay games use the same factory.
Their selection adapters delegate to the configured object. Loaded CLI opponent
models restore tendencies/state, not chart knowledge. Existing public wiring
checks pass for both team sides and new/resumed/replayed configurations.
AI-025's observed-call recording fix remains distinct.

## Controlled requirement tests

Ignored local evidence:
`.ai-audits/chart-confidence/hard-chart-response-01/`. The explicit prototype
pytest file is outside default collection and uses only synthetic cells on public
2026 teams. No production AI or existing test assertion changes in this slice.

All snapshots hold third-and-15, own40, Q1/10:00, tied score, empty history and
identical tendency inputs. The factory binds the intended side. A fresh
namespaced AI RNG is fixed to development master 20261108; selection cannot
access patched-to-fail engine dice. No current offensive call is provided.

The existing real-resolver distribution helper independently enumerates exact
216-by-36 physical mass and core priority semantics. All cells here are complete
numeric controls, so no unknown/penalty/fumble branch gets an invented value.
A uniform nine-call mixture is an explicitly declared diagnostic prior, not a
historical call-frequency target or knowledge of the pending call.

| Controlled change | Exact resolver control | Current Hard response |
| --- | --- | --- |
| Own defense: uniquely strong formation A becomes F | Favored formation allows zero conversions; all others allow every call to convert | C in both configurations, on both team sides |
| Opponent offense: run strength becomes pass strength, own defense fixed | A then F uniquely minimizes conversion probability to zero; C permits 4/9 then 5/9 under the declared mixture | C in both configurations, on both sides |
| Opponent defense: run weakness becomes pass weakness, own offense fixed | Every formation gives favored calls 18 yards and other calls 2 yards | Same 1/9 weight for all nine calls in both configurations, on both sides |

Six intended chart-response requirements fail for these behaviors, with six
passing controls: own-offense changes alter supported call weights; twelve
observed runs versus passes change defense B versus D; selection preserves
engine state/global RNG and never calls engine dice. There are no setup errors,
skips, missing data or historical unit dependencies. An additional 144 existing
AI/CLI controls and 32 backend AI controls pass.

These are stationary decision probes, not full games, repeated-season estimates,
proof of an optimal mixed strategy or an issue-closure play-test. They establish
the requested ordinary chart responses are absent in current paths.

## Correction direction for review

A future test-first correction should combine public chart information with
observed tendencies and situational priorities, retaining coaching variation.
Use the authoritative core priority semantics and physical weights for supported
outcomes. Preserve unresolved mass and disclose bounded utility assumptions;
do not turn partial known-yard estimates into full-engine success probabilities.
Cache by all chart/context inputs used. Selection must never inspect the other
side's pending call, future dice or unrevealed outcomes, nor advance the engine
RNG or mutate game state during a preview.

Before implementation, review the opponent-call prior, defense-mixture prior,
utility for supported/unsupported outcomes, situational ordering and cache cost.
Do not introduce new frequency caps, alter chart outcomes/targets, import BB
RZDZ behavior or fold AI-019's situational-ordering scope into an accidental fix.
Renew exploit/repetition and complete policy/season evidence after the policy
changes; existing campaigns remain versioned development observations.

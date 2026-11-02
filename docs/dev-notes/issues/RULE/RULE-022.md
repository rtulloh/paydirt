---
id: RULE-022
title: Declined late-game penalty loses clock-stoppage context and charges ordinary scrimmage time
status: closed
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - reproduced
---

## Description

A late-game play-test observation prompted a synthetic/public-sample reproduction:
Q4 1:25, third-and-four at own 35, nine-yard completed pass with a defensive
five-yard foul declined. With the timing draw fixed at 44 seconds, the engine
leaves Q4 0:41, first-and-ten at own 44. The pending choice leaves the clock
at 1:25, and resolution makes exactly one timing draw. This is ordinary
scrimmage timing, not a duplicate clock charge or time spent choosing.

`apply_penalty_decision(accept_play=True)` passes the retained result to
`_apply_play_result` without preserving the fact that a foul stopped the clock.
An ordinary in-bounds completion consequently draws 25–45 seconds, just like
a clean completion. Accepted penalties also retain their separate ordinary
25–45-second timing branch; include that branch in the investigation.

Published rule evidence supports a stoppage rather than ordinary dead time:

- Avalon Hill's [All-Star Replay, volume 3, number 1](https://www.vftt.co.uk/files/AH%20All-Star%20Replay/All-Star%20Replay%20Vol%203%20No%201.pdf),
  alternate timing article, classifies Paydirt plays involving penalties as
  referee-timeout plays with zero dead time. Its completed-pass action-time
  formula would charge five seconds for nine yards. This optional system has
  **not** been adopted in full by this implementation.
- The [2023 NFL rulebook, Rule 4-3-2(e)](https://operations.nfl.com/media/tvglh0mx/2023-rulebook_final.pdf)
  explicitly starts the clock on the snap following enforcement or declination
  of a foul inside the last five minutes of the second half. This corroborates
  the modern NFL behavior; it does not independently establish 1983 rules or
  the standard Paydirt Timing Chart's exact charge.

## Resolution / verification

The engine preserves foul clock-stop context through accepted and declined
scrimmage decisions. Flagged plays use the supplied 2008 rulebook's Alternate
Timing Method action/actual-return time with zero dead time (printed pages
22–23), extending the existing selected incompletion rule without enabling
that entire optional timing system. The nine-yard completion uses five
seconds. Standalone fouls without a live result use five base seconds;
Hail Mary interference uses its action-time formula. Offset and special-kick
policies remain separate. No spike or timeout is charged after this stop.

Public test-first cases cover both teams, regulation/overtime, accepted and
declined choices, clean controls, incompletions, enforcement versus live
movement, losses, retained returns, warning/expiry boundaries and untimed
downs. The final focused set passes 465 tests. A 64-game public-chart audit
confirms 767 finalized foul clock stops without a duplicate spike/timeout.
See the maintained clock guide and release-readiness note for every changed
prior test expectation and the explicitly selected timing policy.

## Comments

--- 2026-11-02 10:08 ---
Read-only engine reproduction used public 2026 sample teams and a synthetic
nine-yard pass result. Both the clean completion and declined defensive foul
make one `(25, 45)` timing draw and leave 41 seconds when that draw is 44.
Only the flagged case pauses for a decision, still at 85 seconds. The original
local game log is unchanged and is not included in this ticket. No claim is
made that existing passing penalty-clock tests prove conformity with the
missing standard Timing Chart.

--- 2026-11-02 10:15 ---
The completed game retains the reported 44-second declined-foul runoff. All 31 other finalized incompletions use exactly five seconds, and timeout adjustments/two-minute warnings reconcile. RULE-023 separately records a reproduced natural out-of-bounds marker suppression; do not conflate either issue with duplicate penalty-choice charging. No timing behavior changed during this audit. See ../../game-audit-2026-11-02.md.

--- 2026-11-02 10:50 ---
Included in the pending local fix commit. Issue-specific full-game evidence
is recorded above; private charts and narrative logs remain ignored.

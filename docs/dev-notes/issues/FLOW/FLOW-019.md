---
id: FLOW-019
title: Offsetting kickoff fouls end the period before the required re-kick
status: open
priority: High
created-at: 2026-11-07
resolved-at:
closed-at:
tags:
  - reproduced
  - monitoring
---

## Description

The repeated-season campaign found offsetting kickoff-return fouls charging ten
seconds, ending regulation, then recursively attempting a kickoff after game end.
The same ordering affects opposite-team fouls across the kick and return charts,
and can advance other periods before resolving the required replay.

## Resolution / verification

The pending core fix uses the clock's existing defensive/offsetting-foul period
extension for both ten-second charges. It holds the original period at zero until
the re-kick resolves, without leaving an untimed scrimmage-down flag. Await commit
and repeated-season confirmation before resolving or closing this ticket.

## Comments

--- 2026-11-07 00:00 ---
Synthetic/public-2026 test-first matrix: twenty expected failures across quarters
1–5, both kicking sides and both foul paths; four ordinary-clock controls passed.
After the two-line fix, all 122 focused kickoff/untimed-down/clock-trace tests
passed. The expiry tests verify original-period replay, one retained play,
nullified penalty statistics, period/game completion and no dangling untimed down.
No existing expectations were changed. The campaign agent is rerunning its frozen
512-seed schedule; unit tests alone do not close this issue. Private reproduction
evidence remains in ignored local audit storage.

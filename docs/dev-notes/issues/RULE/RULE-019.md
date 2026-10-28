---
id: RULE-019
title: Punt returns bypass the unified return resolver: penalty touchdowns, discarded TD/F rerolls, no recovery roll
status: resolved
priority: High
created-at: 2026-10-27
resolved-at: 2026-10-28
closed-at:
tags:
  - reproduced
links:
  - RULE-014
  - TRACE-004
commits:
---

## Description

`docs/playing.md:114-127` and commit `9be5487` describe one return procedure for every return chart, but punt returns still use the legacy `_handle_return_penalty` (`paydirt/game_engine.py:365-431`, called at `:3915`) and inline enforcement (`:4231-4271`). Reproduced with a punt landing at the receiver's 35 versus a kickoff landing at the same spot, identical rolls:
- **Penalty touchdown.** Return cells `DEF 10` then `60`: the punt is scored as a return touchdown (`:4266-4271`); the kickoff correctly stops at the 3 by half the distance with no touchdown (`:775-780`). The punt KEEP option similarly awards a touchdown (`:4046-4049`, `:4453-4455`).
- **Discarded cells.** Cells `DEF 10`, `TD`, `F + 5`, `7`: the punt consumed five dice and reported "reroll 13 → 7 yards", silently skipping the TD and fumble cells (`:415-421` catches `ValueError` and keeps rolling); the kickoff scored the touchdown on the first reroll.
- **No recovery roll.** Cell `F + 5` with a recovery roll available: the punt awards the ball to the kicking team without consuming the roll (`:3931-3934`, `:4368`, `:4382-4387`); the kickoff rolls recovery and the returner keeps the ball on 15.
- An offensive foul on a punt-return touchdown is enforced from the catch point (`:4234-4240`) rather than from the end of the return as for other returns (`:771-774`).

## Resolution / verification

- Failing regressions mirroring the kickoff cases for punts: no penalty touchdown, TD/F reroll cells honored, recovery roll consumed and traced, enforcement spot consistent.
- Route punt returns through `_resolve_return_chain` and delete the legacy path; update `docs/playing.md` only if any documented behavior intentionally differs.

## Comments

--- 2026-10-27 18:00 ---
Found during the Bowl Bound 2026-10-27 full review cross-check; reproduced in Paydirt with public 2026 sample fixtures and synthetic chart cells only. No private charts or logs were used.

--- 2026-10-28 07:10 ---
Implemented locally, pending final validation/commit. Initial test-first matrix:
23 expected failures and one passing plain-punt control. Punt returns now use
`_resolve_return_chain`, including TD/F penalty rerolls, actual recovery/optional
fumble-return rolls, end-zone outcomes, live return fouls, nested recoveries,
and ten-second offset/re-kick flow. Kick-chart replay/KEEP/decline decisions
store the resolved chain without applying statistics/scores early or rerolling
it later. KEEP enforcement cannot manufacture a touchdown. Removed the legacy
return-penalty/fumble helpers and inline return enforcement.

All 31 new punt cases pass. The short-drop raw-cell/trace test first failed
because an intermediate implementation replaced negative chart cells with 0;
keep the chart cell intact and apply short-drop movement through an end rule.
Existing expectation changes: fumble fixtures explicitly supply the missing
recovery roll (dice-count assertion 2→3); KEEP preview on a 50-yard return now
stops at the opponent 4 instead of scoring via a foul, retaining a 60-yard
genuine-TD control; returner OFF on a TD is enforced from the goal line (own
85), not the catch point, while a DEF foul cannot wipe a genuine TD or invent
a future kickoff carryover. The trace-helper test now targets the shared roller
instead of the deleted helper. No skips added or unrelated assertions weakened.

The runner retains all twelve historical games and adds a thirteenth after
correct recovery-roll consumption shifts one mandatory event seed; see
[seed-drift investigation](../../historical-seed-drift.md). Test-first runner
baseline: eight expected failures/47 controls. Both mandatory untimed events
remain required. Real runner: 13/13 historical, 224/224 generated regular games
(10 OT, three allowed ties), 9/9 playoffs (no ties), exit zero. Standings remain
unpersisted. Player guidance already describes this shared procedure; no new
player rule, control, or API is introduced by the migration. Nothing pushed.

--- 2026-10-28 07:13 ---
Core 5,847 passed / eight existing skips / 76% coverage; backend 218 passed
(existing Pydantic warnings); frontend 255 passed / one existing skip; Ruff,
production build, both complete Hard browser games and offline guide passed
(existing stale Browserslist warning). Both AI audits passed and were reviewed
in AI-009. A second instrumented real full-game runner verified 951 applied
punt chains, 36 fumble chains with recovery traces and reconciled lost-fumble
stats, 77 return-foul chains with reconciled penalty stats, seven penalty-to-
fumble rerolls, and one end-zone fumble chain with matching final possession
and scoring flags. No new skip or weakened gameplay assertion. Mark resolved
with the scoped local commit, not closed: rare TD-wipe/penalty-near-goal cases
remain synthetic-regression evidence rather than observed play-test cases.

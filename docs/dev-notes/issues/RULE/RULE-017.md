---
id: RULE-017
title: Own-recovery fumble advance resets the down to second regardless of the down before
status: closed
priority: High
created-at: 2026-10-27
resolved-at: 2026-10-27
closed-at: 2026-11-06
tags:
  - reproduced
links:
commits:
---

## Description

When the fumbling team recovers with a 17–19 roll and advances short of the line to gain, `_handle_fumble` (`paydirt/game_engine.py:1596`) calls `_apply_return_chain`, which sets `down = 1` as a new-series placeholder (`:942`), and then `self.state.next_down()` (`:1657`) increments that placeholder. Synthetic reproduction: HOME 3rd-and-8 at its 42, play cell `F + 2`, recovery roll 17, return cell `2` → engine reports **2nd-and-4** at the 46; the expected result is 4th-and-4. From 2nd-and-8 the same inputs also give 2nd-and-4 (expected 3rd-and-4). Control with recovery roll 20 (no advance) correctly gives 4th-and-6. Regression introduced by `9be5487`; `tests/test_offensive_fumble_advance.py:84` parametrizes only downs 1 and 4, so it cannot catch it.

## Resolution / verification

- Failing regression first: 2nd- and 3rd-down own-recovery advances short of the sticks produce 3rd and 4th down respectively; an advance past the line to gain gives 1st-and-10; roll 20 unchanged.
- Preserve the pre-fumble down through the advance path instead of relying on the return-chain placeholder.
- Extend the parametrization in `tests/test_offensive_fumble_advance.py` to all four downs.

## Comments

--- 2026-10-27 18:00 ---
Found during the Bowl Bound 2026-10-27 full review cross-check; reproduced in Paydirt with public 2026 sample fixtures and synthetic chart cells only. No private charts or logs were used.

--- 2026-10-27 22:14 ---
Implemented locally, not committed or pushed. The test-first expanded matrix
plus a focused 3rd-and-8 reproduction produced 76 expected failures and 282
passing controls against the unchanged engine (3rd-and-8 incorrectly became
2nd-and-4). Preserve down_before before next_down after an own recovery short
of the sticks. Expanded existing first/fourth-down coverage to all four downs;
changed its hardcoded expected second down to starting-down + 1, preserving
the original first-down case rather than weakening it. Added roll-20 no-advance
controls and both entry points. All 358 fumble-advance cases pass; 390 pass
with return-chain and display regressions. Core 5,663/8 existing skips, backend
218, frontend 255/1 existing skip, build/browser, Ruff, historical 12/12,
generated 224/224 plus 9/9 playoffs, and both full AI audits passed.
Player guidance now explicitly describes the preserved series/down. Keep open
until the tested fix is committed, then mark resolved pending an issue-specific
full-game play-test; unrelated game completion alone is not grounds for closure.

--- 2026-10-27 22:15 ---
Included in the current local fix commit with its tests and player guidance.
Marked resolved; issue-specific full-game confirmation is still required for
closure. No push authorized or performed.

--- 2026-10-28 12:40 ---
Supplied-game own-recovery fumble correctly gains a first down at the
recovery spot, but this is a first-down call with no recovery advance
(local lines 1269-1277). It is only a passing control. The reported
second/third-down advance short of the sticks is not exercised, so keep
resolved pending that specific full-game evidence. No closure inferred.

--- 2026-11-06 02:17 ---
Issue-specific confirmation now comes from complete public-generated training
games at runtime `871af55a…`, not unit tests alone. A read-only replay captures
all 37 own-recovery advances across 496 legally completed games. Every one of
the eight qualifying second/third-down recoveries short of the sticks preserves
the original down progression and remaining distance, with no first down or
turnover incorrectly reported.

Two examples include actual positive recovery advances: Saints at Packers,
development seed 20502259, third-and-five at the 20, six-yard recovery advance
after the initial loss, finishes fourth-and-five at the 20; Jaguars at Colts,
seed 20524457, second-and-four at the 83, a three-yard advance, finishes
third-and-one at the 86. These are generated 2024 games, not historical results.
The retained local evidence binds runtime, chart fingerprints, every game seed
and all qualifying cases. The seeds derive from development master 20261108;
no reserved family was opened. Close RULE-017 on this specific play-test
confirmation. DATA-033's separate accepted-penalty rights and RULE-027's
cross-chart foul/timing work do not change these unpenalized passing cases.

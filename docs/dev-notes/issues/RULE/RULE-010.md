---
id: RULE-010
title: Kickoffs resolved the kick distance and the return from **one** dice roll
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at:
links:
  - AUD-021
  - FLOW-005
tags:
  - was: implemented, uncommitted
---

## Description

Kickoffs resolved the kick distance and the return from **one** dice roll: `kickoff()` read `special_teams.kickoff[dice_roll]` and `special_teams.kickoff_return[dice_roll]` with the same roll (traces showed `KO:n … RT:n` on every kick). The rules (Kickoff / Kickoff Return) require the kicking team to roll for the kick and the receiving team to roll its own offensive dice for the return. Punts already rolled the return separately.

## Resolution / verification

Test-first: 12 failing engine cases (separate return roll home/away, no return roll for touchbacks/end-line/out-of-bounds kicks, end-zone depth with the chart value shown, kick-chart penalty with decline using the flagged kick's return and accept re-kicking with fresh rolls, return-chart penalty rerolls from the separate roll, safety free kick) and one passing onside control. The return is now rolled once, only when the kick is returnable; `PlayResult.kickoff_return_dice`/`kickoff_return_result` carry it; the trace shows `KO:` and `RT:` (plus return rerolls) or `RT:none`; the web `dice_details.defense` reports the real return roll. Changed prior expectations (all encoded the single roll): 11 cases in `tests/test_kickoff_return.py`, 3 in `tests/test_kickoff_return_td_flow.py`, and 2 in `tests/test_auto_game_flow.py` now supply the receiving team's roll in their dice sequences with unchanged spot/score assertions; `backend/tests/test_api.py::test_kickoff_returns_dice_details` no longer asserts the return dice equal the kickoff dice. Seeded trajectories change (one extra roll per returned kickoff); see validation below for the historical reproductions.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Implemented, uncommitted).

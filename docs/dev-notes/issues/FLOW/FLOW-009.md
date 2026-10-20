---
id: FLOW-009
title: On interception, fumble-advance and blocked-kick returns the "other team recovers the reroll fumble while a…
status: open
priority: Medium
created-at: 2026-10-20
resolved-at: 
closed-at:
links:
  - RULE-014
tags:
  - documented limitation
---

## Description

On interception, fumble-advance and blocked-kick returns the "other team recovers the reroll fumble while a returner's foul is live" decision is applied automatically as the recovering team's natural choice (keep the ball, penalty declined) instead of being offered to a human; kickoffs do prompt. Adding a pending decision inside `run_play`/`_handle_fumble` means deferring possession/scoring until the decision, a larger refactor. Vanishingly rare (penalty × reroll fumble × lost × opponent human).

## Resolution / verification

Resolve the chain without applying it (already the case), return a pending outcome from `run_play` with `kick_phase="return_fumble"`, and apply through `apply_penalty_decision`. Design note from the 2026-10-20 review: a live/dead-ball distinction (stacking 15-yard dead-ball fouls) is not representable with the chart data and is not planned.

## Comments

--- 2026-10-20 00:00 ---
Migrated from the single-file tracker (status at migration: Open (documented limitation)).

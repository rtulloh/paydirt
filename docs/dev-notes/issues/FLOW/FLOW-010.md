---
id: FLOW-010
title: Random-opponent API assigns the opponent as the player in away games
status: resolved
priority: High
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at:
tags:
  - reproduced
---

## Description

In `paydirt-web/backend/routes.py:new_game`, the no-opponent branch swaps
`player_team_id` and `cpu_team_id` when `play_as_home` is false, then derives
home and away from those swapped IDs. A public 2026 request for Ironclads as
away with no `opponent_team` returns Ironclads as home/CPU and Thunderhawks as
away/human. The home random-opponent control returns the requested human team.
The current team-selection UI always supplies an opponent, so this affects API
clients using the supported random-opponent path.

## Resolution / verification

Keep the requested team assigned to the player and place it on the requested
side. Added a public-2026 API regression covering home and away games with both
explicit and random opponents; it checks returned home/away identity, player
and CPU IDs, human side, and possession-derived player offense. Against the
unchanged route, the random-opponent away case failed because Ironclads was
returned as the home team. The regression passes after the fix, as do the
explicit-opponent home and away API tests.

## Comments

--- 2026-10-30 15:09 ---
Reproduced with FastAPI TestClient against the two public 2026 teams.

--- 2026-10-30 17:23 ---
Fixed the random-opponent away assignment and verified the regression against
public sample teams.

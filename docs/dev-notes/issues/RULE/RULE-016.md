---
id: RULE-016
title: Penalty cells on the Int. Return chart were read as yardage
status: resolved
priority: High
created-at: 2026-10-20
resolved-at: 2026-10-20
closed-at:
commits:
  - 9be5487
---

## Description

Penalty cells on the Int. Return chart were read as yardage: `_parse_return_yards("OFF 10")` extracted "10" as a 10-yard advance (interceptions, fumble advances both sides, blocked punt/FG and fumbled-snap returns), fumble cells were yardage too, and a stray cell parsed as 0 silently. The private 1983 charts carry 68 OFF, 18 DEF, 17 TD and 12 fumble cells in that column; the public charts carry none, which is why nothing caught it.

## Resolution / verification

All consumers go through `_resolve_return_chain` (rule-book example: intercepted at own 13, OFF 10 then 52 → own 55). Offsetting fouls set `PlayResult.replay_down`: possession/spot/down restored, ten seconds, turnover not recorded. `_parse_return_yards` removed. `int_return_yards` keeps reporting the chart value for a plain return and the net advance when a penalty or fumble altered it. Tests: `tests/test_return_chart_rules.py` (INT: OFF/DEF/TD/half-distance/offsetting/same-type/fumble both ways/fumble after a foul/unreadable cell; fumble advances 17 and 37 with fouls; blocked FG return foul, 39 auto-TD control, offsetting replay for fumble advance and blocked FG). Changed prior expectation: `tests/test_kickoff_after_score.py` used `find_team_charts("seasons")` (arbitrary, possibly private charts with unpatched dice — against AGENTS.md) and now uses the public sample game. Validation (2026-10-20): core 5,228 passed/8 existing skips (76%); backend 218; frontend 254/1 existing skip; build; both browser games; Ruff; docs; 14-game runner; 10/10 historical reproductions; 224/224 generated games (14 OT, 1 regular-season tie; previously 16 and 6 — trajectories move with every corrected return) and 9/9 playoffs; public 32/32 (3,856 calls) and local 448/448 (52,695 calls) audits reconciled with normalized probability vectors; tracked-source snapshot 5,211 core/25 existing skips and 218 backend. Advisories: Oilers and Rams carried over; Colts and Vikings balanced 3rd-and-11+ at exactly the 50% threshold with three alternatives (36 calls each, longest comparable streak four) — legacy balanced policy, observational.

## Comments

--- 2026-10-20 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved (`9be5487`)).

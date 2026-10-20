---
id: RULE-003
title: Originally reported as: when the defense chart shows DEF n and the offense rolled B, QT, BLACK, TD, F, or I n, the…
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - re-scoped
links:
  - AUD-014
  - FLOW-003
---

## Description

Originally reported as: when the defense chart shows `DEF n` and the offense rolled `B`, `QT`, `BLACK`, `TD`, `F`, or `I n`, the priority step returns bare yards and accept-play applies `offense_yards` (0 for symbolic cells), so a breakaway becomes no gain and `I 15` becomes a 15-yard offensive gain. **Re-scoped 2026-10-19:** defense charts never contain penalties. All 30 local `defense.csv` files (28 × 1983, 2 × 2026) have zero `OFF`/`DEF`/`PI` cells; penalties exist only on offense charts and special-teams columns (Punt, Field Goal, Int./Punt/Kickoff Return, Kickoff), and the priority reference lists `DEF/OFF/PI` only as an offensive row. The reproduction and the earlier semantic tests used an impossible chart (`defense.modifiers = {..: "DEF 5"}`). The offense-chart path (`DEF 5` cell → reroll `TD`) already resolves correctly (FLOW-003 CPU-offense test).

## Resolution / verification

Work plan when picked up, test-first: (1) Re-verify on the real resolver that an offense-chart `DEF n`/`OFF n` reroll into `B`, `QT`, `INT`, `F`, `BLACK`, or `TD` keeps the real result type and secondary rolls for accept-play, the CPU valuation, the CLI/web previews, and `projected_touchdown`; if any consumer still reads `offense_yards`/`play_result.yards` for those cases, that is the remaining defect. (2) Delete the dead `def_cat == PENALTY` branch in `apply_priority_chart` and the `defense_modifier.startswith("DEF")` projection branch in `run_play_with_penalty_procedure` (both committed-era code paths for charts that cannot exist), or convert them to an explicit error. (3) Add a chart-loader validation (and `extract_charts.py` check) that rejects penalty cells on defense charts so synthetic tests cannot depend on them. (4) Rewrite `paydirt-web/backend/tests/test_pending_penalty_scoring.py::test_human_offense_goal_crossing_gain_with_defensive_flag` and any `tests/test_audit_*` cases that build defensive-chart penalties to use an offense-chart `DEF 5` → numeric/symbolic reroll instead; keep home/away coverage. (5) Close AUD-014 with the same change or re-scope it to the offense-chart preview. Not reachable in 1983 or 2026 play; no longer a play-test blocker.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (re-scoped)).

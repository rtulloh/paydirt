---
id: FLOW-001
title: After a half-ending TD the CLI passed the current quarter to can_kickoff_after_play, so the scoring team kicked…
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at:
links:
  - RULE-002
commits:
  - 2e37986
---

## Description

After a half-ending TD the CLI passed the current quarter to `can_kickoff_after_play`, so the scoring team kicked off and the loop then ran the second-half kickoff too.

## Resolution / verification

Engine now records the start period of every scoring-capable action (`run_play`, penalty procedure, kickoff/onside, safety free kick; tries preserve it) and `can_kickoff_after_play()` / `should_kickoff_after_score()` default to it; explicit arguments still work. `_complete_touchdown_sequence` uses the engine default. Full-loop CLI regressions (new/resumed × home/away) require exactly one kick after a Q2-expiring TD — the scheduled second-half kickoff by the opening receiver — with Q1/Q3-expiry and time-remaining controls; engine tests cover each entry point including half-expiring kick-return scores. Committed in `2e37986`; no release contains this fix yet.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

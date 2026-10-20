---
id: RULE-012
title: The final-try rule is era-dependent and the engine currently applies the pre-2018 rule to every season
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - decided: season configuration
links:
  - RULE-002
---

## Description

The final-try rule is era-dependent and the engine currently applies the pre-2018 rule to every season. Through 2017 a Try follows every regulation touchdown, even at 0:00 (what RULE-002 implemented). From 2018 the Try is attempted only if it can affect the outcome: scoring team tied, down one or two, or ahead by one or two (a defensive two-point return can still swing it); it is skipped when the scorer is still trailing or ahead by more than two. Overtime walk-offs never get a Try in either era (already handled). The public 2026 season therefore currently offers unnecessary tries.

## Resolution / verification

Add a required season-YAML field (e.g. `final_try: always | only_if_outcome_affected`) with scaffold defaults by year (≥ 2018 → `only_if_outcome_affected`); set 1983 = `always`, 2026 = `only_if_outcome_affected`; load it in `SeasonRules` and expose it in `get_season_rules()`. `can_attempt_conversion_after_touchdown()` consults it for an expired fourth quarter; CLI, web, and `auto_game` already route through that query. Tests first: engine matrix for both rule values × post-TD margins −3…+3 at 0:00 and with time remaining, loader rejection of a missing field, CLI/web controls that a skipped Try ends the game with no PAT prompt and no kickoff. Expectation change to disclose: `test_regulation_try_is_allowed_while_leading_at_expiry` asserts a PAT when ahead by 7 at 0:00 on the public fixture (correct for 1983 rules only); parametrize by rule.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (decided: season configuration)).

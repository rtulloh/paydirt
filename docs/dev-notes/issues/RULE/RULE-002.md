---
id: RULE-002
title: A TD at 0:00 of regulation that left the scores unequal set game_over before the try
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at:
links:
  - FLOW-001
  - RULE-001
  - FLOW-005
  - RULE-012
commits:
  - 2e37986
---

## Description

A TD at 0:00 of regulation that left the scores unequal set `game_over` before the try; CLI (`while outcome.touchdown and not game_over`) and web (`is_pending_pat`) skipped the PAT/2PT, and `attempt_two_point` raised "Game is over". Only `auto_game` consulted `can_attempt_conversion_after_touchdown`.

## Resolution / verification

Test-first with FLOW-001/002 (37 failing, 17 passing controls across the full-loop CLI and engine files; 4 failing backend API cases). CLI and web now gate the try on the engine query; `attempt_two_point` runs under a conversion-in-progress flag and both try methods share `_recompute_game_over_after_try`. Covered: trailing by 7 → PAT → tie → OT or miss → final; leading → PAT still kicked; 1983 rules offer PAT only; OT-winning TD has no try; web `pending_pat` at 0:00 with the PAT endpoint completing the game. One assertion deliberately narrowed: the two-point-at-expiry test checks availability and the recomputed game-over flag only, because the point total is RULE-001's defect (the try still scores 8 until that fix). Committed in `2e37986`; no release contains this fix yet.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

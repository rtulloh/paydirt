---
id: FLOW-034
title: Final scoring action can report kickoff pending after game over
status: open
priority: Low
target-release:
created-at: 2026-11-17
resolved-at:
closed-at:
tags:
  - observed-api
links:
  - FLOW-033
commits:
---

## Description

A terminal-field-goal diagnostic against the actual browser Python runtime found
that the execute response reports `game_state.is_kickoff: true` while a fresh
canonical game-state read and replay export both correctly report `false`.
The action response overrides the stored flag from the scoring result even when
the engine has ended the game. Full canonical state and export remain identical.
No player-facing failure was established; the final-score screen takes priority.

## Resolution / verification

- Add a synthetic/public-sample regression before changing the final-scoring API response.
- Keep the engine authoritative for whether any kickoff remains owed.
- Verify field-goal and other terminal-scoring responses agree with canonical state and export, with live nonterminal scoring controls.

## Comments

--- 2026-11-17 20:29 ---
Found while investigating an unseeded Node audit export-parity failure. The
original failure did not retain a field diff; a separate terminal-field-goal
diagnostic proves this exact single-field discrepancy. The audit now compares
export with a fresh canonical state read, retaining complete equality and the
terminal action snapshot as separate evidence. No production fix or closure is
claimed for this low-priority response metadata finding.

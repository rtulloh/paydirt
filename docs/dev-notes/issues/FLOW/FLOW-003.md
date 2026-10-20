---
id: FLOW-003
title: Web execute_play called setup_for_pat() and set pending_pat from result.touchdown without checking…
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at:
links:
  - RULE-003
commits:
  - 072875a
---

## Description

Web `execute_play` called `setup_for_pat()` and set `pending_pat` from `result.touchdown` without checking `pending_penalty_decision`; the provisional touchdown flag widened this to goal-crossing yardage with a flag. Ball moved to the 98 before the choice: penalty enforced from the 98, accepted play credited as a 2-yard TD. The penalty endpoint also overrode `touchdown`/ball position after decisions.

## Resolution / verification

Test-first: 12 failing backend API cases (human offense/defense deciding, CPU deciding, home/away) plus 20 failing core cases; two API controls passed. Pending outcomes now keep `touchdown=False` and expose `PlayOutcome.projected_touchdown` for CPU/oracle use; one backend helper arms PAT/kickoff state only for finalized outcomes in `execute_play` (both paths) and the penalty endpoint; the spot-based touchdown override is removed. Changed prior expectation: `test_cpu_scoring_choice_has_real_engine_consequences` asserted the pending `touchdown` flag that encoded the defect; it now asserts `touchdown is False` and `projected_touchdown`. A CPU-offense defensive-chart `TD` scenario exposed RULE-003 instead and is deferred to it. Validation recorded in the commit. Committed in `072875a`; no release contains this fix yet.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

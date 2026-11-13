---
id: FLOW-006
title: Resume_game scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick)
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

`resume_game` scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick). The engine scores at play time, so a save with the ball at the goal line already includes the points; the path would double-count. Currently latent in the CLI.

## Resolution / verification

Replace with an engine-owned completion method or remove; align with the web `load_replay` behavior.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

--- 2026-11-11 12:00 ---
1.10.6 scope review: resume_game still directly adds six touchdown points or two safety points and appends generic ScoringPlay entries. Existing tests/test_resume_pending_score.py mirrors manual score additions and checks kickoff ownership; those tests do not demonstrate score-idempotent handling of an already-scored real save. Retain as open/code-read pending a real-engine save/resume regression; do not describe double scoring as newly reproduced in this review. No production change.

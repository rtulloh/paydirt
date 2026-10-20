---
id: RULE-007
title: Uncommitted _log_score try attribution relies on scoring_plays[-1] being the TD
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
links:
  - RULE-001
---

## Description

Uncommitted `_log_score` try attribution relies on `scoring_plays[-1]` being the TD; with RULE-001 unfixed a 2PT attaches to the spurious TD, and the try keeps the live clock time.

## Resolution / verification

Fix with RULE-001; pass the TD scoring entry/quarter explicitly from the try methods.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

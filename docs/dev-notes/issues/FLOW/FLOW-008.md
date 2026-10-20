---
id: FLOW-008
title: Web load_replay reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

Web `load_replay` reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession; a TD is inferred from `ball_position >= 100`.

## Resolution / verification

Persist authoritative flags with the replay; stop parsing text.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

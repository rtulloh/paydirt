---
id: DATA-001
title: Seasons/1983/Cardinals/special.csv Int
status: resolved
priority: Medium
created-at: 2026-10-20
resolved-at: 2026-10-20
closed-at:
---

## Description

`seasons/1983/Cardinals/special.csv` Int. Return roll 30 is a stray backtick; the engine read it as a 0-yard return without saying so. Root cause 2026-10-20: the character is in the original XLS workbook, so the extractor must make the best guess rather than copy it.

## Resolution / verification

`chart_loader.normalize_special_cell` drops characters no result can contain (backticks, quote marks) and treats an emptied cell as a blank, zero-yard result; `extract_charts.py` applies it when writing `special.csv`, and `parse_special_csv` applies it on load with a warning naming the column and roll (a cell that is still unreadable after cleanup also warns). Tests: `tests/test_chart_loader.py` (normalizer matrix, stray cell read as blank, valid cells silent). A scan of all local charts reports exactly the Cardinals cell.

## Comments

--- 2026-10-20 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved (extractor and loader)).

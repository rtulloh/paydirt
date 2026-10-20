---
id: TRACE-002
title: Fumble traces show unknown defensive rows and placeholder-looking zero return rolls
status: open
priority: Low
created-at: 2026-10-18
resolved-at: 
closed-at:
links:
  - TRACE-007
---

## Description

Fumble traces show unknown defensive rows and placeholder-looking zero return rolls.

## Resolution / verification

Preserve actual defensive-row metadata; distinguish no return roll from an actual zero-yard return. Do not fabricate a `Ret:0` die roll. Reconfirmed in the latest audit.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

--- 2026-10-20 18:00 ---
Reproduced from `/tmp/game.log` using the current engine and the 1983 Cardinals/Redskins charts. The Q4 punt trace reported `P:19→"31" | R:11→""`, followed by a punt-return fumble and Cardinals recovery at ARI 46. The raw chart data confirms that the Redskins Punt Return row 11 is `F`, so the fumble and possession change are correct; the trace is wrong/incomplete because it suppresses the raw `F` cell and the recovery roll. The exact reproduction with rolls `19` and `11` produced the same result, including Redskins turnovers +1. This confirms TRACE-002 rather than a new gameplay ticket.

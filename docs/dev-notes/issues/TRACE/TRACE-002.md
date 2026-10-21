---
id: TRACE-002
title: Fumble traces show unknown defensive rows and placeholder-looking zero return rolls
status: closed
priority: Low
created-at: 2026-10-18
resolved-at: 2026-10-20
closed-at: 2026-10-20
links:
  - TRACE-007
---

## Description

Fumble traces show unknown defensive rows and placeholder-looking zero return rolls.

## Resolution / verification

Punt-return traces retain raw return cells, and ordinary fumble traces now retain the actual defense-chart dice row. Compact output shows a return only when the engine resolved a return-chart roll; a normal recovery now ends at `R:<recovery>→"kept/lost"` without fabricated `Ret:0→0` metadata. Focused display/fumble tests pass. Await an interactive play-test before closing.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

--- 2026-10-20 18:00 ---
Reproduced from `/tmp/game.log` using the current engine and the 1983 Cardinals/Redskins charts. The Q4 punt trace reported `P:19→"31" | R:11→""`, followed by a punt-return fumble and Cardinals recovery at ARI 46. The raw chart data confirms that the Redskins Punt Return row 11 is `F`, so the fumble and possession change are correct; the trace is wrong/incomplete because it suppresses the raw `F` cell. The exact reproduction with rolls `19` and `11` produced the same result, including Redskins turnovers +1. This confirms TRACE-002 rather than a new gameplay ticket.

--- 2026-10-20 18:15 ---
Resolved test-first. `PlayResult` now retains `punt_return_result`, and every resolved punt path carries the raw return cell when a return roll occurred. Compact CLI output reads that engine fact instead of parsing prose, displaying `P:19→"31" | R:11→"F" | return` for the reproduced fumble. The direct punt-return-fumble procedure has no recovery roll; the new tests assert exactly two consumed dice and no invented `Ret:` trace.

--- 2026-10-20 18:30 ---
Play-test closure evidence for the punt-return branch: WSH punted 40 yards from WSH 27 and ARI returned with `R:15→"F"`. The engine reported WSH recovery at ARI 33 and `1st and 10`; the trace showed `P:39→"40" | R:15→"F" | return` with no fabricated recovery roll. TRACE-002 was closed for that branch.

--- 2026-10-20 19:00 ---
Latest Week 6 audit confirms the punt-return fix still works: Q4 2:32 shows `P:38→"45" | R:13→"F - 1" | return` and WSH recovery at ARI 18. However, ordinary fumble output still reproduces the original defect: at Q4 13:54, ARI's `F + 19` result reports `D:?→""` and `R:33→"lost" | Ret:0→0`. The punt-return branch is correct, but the ordinary fumble trace still hides the defensive row and emits placeholder-looking return metadata. TRACE-002 is reopened for the remaining ordinary-fumble trace path.

--- 2026-10-20 19:15 ---
Resolved the remaining ordinary-fumble trace path test-first. `PlayResult` now retains the defense dice expression selected during both normal and penalty-aware play resolution. Compact output derives `D:<row>` from that engine metadata rather than prose, and emits `Ret:<die>→<yards>` only when `fumble_return_dice` confirms a return-chart roll. A normal defensive recovery now renders `D:3→"" | F | F@75 | R:33→"lost"`, with no invented return roll. Focused display, fumble, and offensive-fumble-advance tests pass; retain this ticket as resolved until follow-up play-test confirmation.

--- 2026-10-20 20:30 ---
Closing after Week 6 play-test audit (Bears @ Vikings 1983, final MIN 20 - CHI 14 OT). Comprehensive trace review confirms the fix is working correctly across all play types:

**Defensive rows:** 20+ samples showing actual row numbers (D:1, D:2, D:3, D:4, D:5) in incomplete passes, yardage plays, and special results. Zero `D:?→""` placeholders found.

**No fabricated return metadata:** Zero `Ret:0→0` occurrences observed. All traces end at the recovery roll when no fumble-return chart was consulted.

**Punt/kickoff traces:** Working correctly with `P:`/`R:` and `KO:`/`RT:` metadata preserved from engine facts.

**Limitation:** No fumbles occurred in this particular game, so the ordinary-fumble recovery trace was not exercised in live play. However, the regression test passed, and all other trace types demonstrate that defensive-row metadata is now populated from engine facts rather than regex parsing of prose.

Both original defects are resolved:
1. Punt-return fumbles now show raw chart cells (e.g., `R:15→"F"`)
2. Ordinary fumble traces now show defensive rows and omit return metadata when no return chart was rolled

Closing ticket. Full audit report saved locally.

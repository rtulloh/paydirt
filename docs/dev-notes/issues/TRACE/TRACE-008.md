---
id: TRACE-008
title: End-line fumble depth roll is dropped from the description when the defense recovers
status: open
priority: Low
created-at: 2026-10-27
resolved-at:
closed-at:
tags:
  - reproduced
links:
commits:
---

## Description

A fumble carried beyond the opponent's end line rolls white dice for depth and records "Fumble into end zone (W3+W4=N yards deep)" at `paydirt/game_engine.py:1509`, but `:1520` overwrites the description on a defensive recovery with "Fumble recovered by defense in end zone - TOUCHBACK" and `rule_explanation` is None, so the physical roll that occurred is absent from the trace and the beyond-end-line and in-end-zone defensive paths are textually indistinguishable. Reproduced with HOME at the 98, cell `F + 15`, white dice 7: offensive recovery keeps the depth text; defensive recovery loses it.

## Resolution / verification

- Keep the depth roll in the trace for both recovering sides; regression asserting the white roll text survives a defensive recovery.

## Comments

--- 2026-10-27 18:00 ---
Found during the Bowl Bound 2026-10-27 full review cross-check; reproduced in Paydirt with public 2026 sample fixtures and synthetic chart cells only. No private charts or logs were used.

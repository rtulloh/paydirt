---
id: RULE-015
title: Recovery roll 39 on an ordinary fumble was an automatic defensive touchdown (R:39→"lost" | Ret:35→97 in the…
status: resolved
priority: High
created-at: 2026-10-20
resolved-at: 2026-10-20
closed-at:
commits:
  - 9be5487
---

## Description

Recovery roll 39 on an ordinary fumble was an automatic defensive touchdown (`R:39→"lost" | Ret:35→97` in the 2026-10-20 Jets–Browns log, where the return roll was taken and ignored); the repository's own rule note and the offense side (19) already said automatic touchdowns apply only to blocked kicks.

## Resolution / verification

37/38/39 all use the interception-return chart in `_handle_fumble`; 19/39 stay automatic only in the blocked-punt/FG paths. Changed prior expectations: `tests/test_fumble.py::test_defense_auto_td_on_roll_39` became two cases (chart return, TD only from a TD cell); `tests/test_end_zone_fumble_commentary.py` and `tests/test_presentation_audit_fumbles.py` "return-touchdown" scenarios now set a `TD` cell instead of relying on the automatic score; `tests/test_box_score_accounting.py::test_fumble_return_touchdown_first_down_attribution` gives the defense's chart a `TD` cell.

## Comments

--- 2026-10-20 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved (`9be5487`)).

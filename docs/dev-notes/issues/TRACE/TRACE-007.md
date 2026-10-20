---
id: TRACE-007
title: The PlayTransaction/PlayEvent model (paydirt/play_events.py) does not deliver its stated purpose and is now a…
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - investigating
links:
  - AUD-018
  - TRACE-001
  - TRACE-002
  - TRACE-005
---

## Description

The `PlayTransaction`/`PlayEvent` model (`paydirt/play_events.py`) does not deliver its stated purpose and is now a third, less complete copy of play state. Populated only by `_apply_play_result`; `run_play`, punts, kickoffs, field goals, tries, and offsetting/accepted penalties leave it `None`. Only 7 of 26 event types are ever emitted; `PendingDecision`/conditional events, `create_penalty_event`, `create_safety_event`, and `paydirt/transaction_display.py` have no production callers. The resolver's transaction, the only one holding the real dice breakdown and defensive row, is discarded and rebuilt with `"Roll N"`/`D:?` (the source of TRACE-002). Consumed only by the CLI compact branch; absent from the web API, frontend, saves, and audit JSON. The compact branch still builds its dice line from regexes and a priority-chart recomputation, and it has display defects the legacy branch lacks: end-zone interceptions render without a turnover marker (touchback) or as an offensive score (pick-six); fabricated `Ret:0→0` rolls; uncapped fumble spot `F@104` versus `99`; `FUMBLE_RETURN` events never carry `is_touchdown`. Thirteen tests force `transaction=None` to keep both display paths first-class.

## Resolution / verification

Read-only review 2026-10-19 with synthetic reproductions. Decision needed between two options, both test-first: (A) complete it — carry one transaction per play from resolver through application, add interception-before-early-return, scoring, penalty-reroll, QT/breakaway, kick, and clock events, serialize it in the API/audit output, then remove the CLI/backend regexes (medium-large; prerequisite for TRACE-005); or (B) retire it — promote the few fields only it carries onto `PlayResult`/`PlayOutcome` (offense/defense dice descriptions and row, return-roll descriptions, `int_touchback`, public FG distance), point compact output at those fields, delete `play_events.py`, `transaction_display.py`, `PenaltyChoice.transaction`, and `PlayOutcome.transaction`, and fold the seven engine-produced-transaction assertions into field assertions (small-medium, low risk; the legacy branch already renders the failing cases correctly). Recommendation: B unless TRACE-005 replay is scheduled. Fixes AUD-018, TRACE-001, and TRACE-002 should follow the chosen direction rather than patching both paths.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Investigating).

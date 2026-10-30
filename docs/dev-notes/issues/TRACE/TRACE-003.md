---
id: TRACE-003
title: Compact traces do not explicitly identify called modifiers and the winning clock procedure
status: open
priority: Medium
created-at: 2026-10-18
resolved-at: 
closed-at:
---

## Description

Compact traces do not explicitly identify called modifiers and the winning clock procedure.

## Resolution / verification

Record calls such as spike, timeout, sideline designation, and no-huddle separately from resolved effects. Explain skipped/canceled modifiers. A five-yard reduction cannot be independently attributed to a designation when the call is absent from the trace.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

--- 2026-10-28 12:40 ---
Supplied-game audit confirms that called offensive modifiers remain absent
from compact call/trace lines. Timeout-used/skipped output is visible, but
the echoed call names alone cannot distinguish an unmodified call from
T, S, +, - or their combinations. In particular, skipped-timeout messages
after incomplete/penalty outcomes do not prove which full modifier call
the user entered or whether another modifier was also planned. Retain
request-versus-effect observability as open; do not infer missing input
from elapsed time. No raw private log exported.

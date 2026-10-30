---
id: STAT-002
title: Successful PAT is allocated to the live next quarter instead of the touchdown quarter
status: closed
priority: Medium
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at: 2026-10-28
commits:
  - eb37c60
---

## Description

Successful PAT is allocated to the live next quarter instead of the touchdown quarter.

## Resolution / verification

Try logging reuses the preceding TD period without rewinding live clock/quarter or changing save schema. Boundaries, failed tries, untimed downs, OT/no-try, and public save/resume controls; two-point logging is covered separately from full conversion mechanics. Committed in `eb37c60`; no release contains this fix yet.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved).

--- 2026-10-28 12:40 ---
Supplied full-game confirmation includes a touchdown called with 18
seconds left in Q1, followed by a successful PAT across the live period
boundary. Both halftime/final period totals and the scoring summary assign
all seven points to Q1; totals reconcile. The next scrimmage status is Q2
after the ensuing kickoff. Close STAT-002 for successful PAT attribution.
No two-point, overtime or final-regulation-try defect is claimed confirmed
from this occurrence. Original private narrative/charts remain local.

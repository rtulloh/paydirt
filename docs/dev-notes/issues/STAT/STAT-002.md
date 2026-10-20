---
id: STAT-002
title: Successful PAT is allocated to the live next quarter instead of the touchdown quarter
status: resolved
priority: Medium
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at:
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

---
id: DATA-002
title: Local 1983 Chiefs commentary roster includes Joe Delaney despite his death before the season
status: open
priority: Low
created-at: 2026-10-28
resolved-at:
closed-at:
tags:
  - reproduced
---

## Description

The supplied game names Joe Delaney as an active 1983 Chiefs ball carrier
and receiver (local log lines 335, 342, 572 and 728). He died on June 29,
1983, before that regular season. The Chiefs' own remembrance identifies
June 29, 2023 as the fortieth anniversary of his death:
[official historical source](https://www.chiefs.com/video/chiefs-kingdom-joe-delaney-17299618).

Read-only inspection confirms the name is present in the installed local
`seasons/1983/Chiefs/roster.json` running-back list. That file is not tracked.
`get_roster`/`load_roster_from_file` load the team-local JSON for commentary;
no hardcoded production-source occurrence was found. This establishes a
local historical roster-data mismatch, not a demonstrated chart-resolution
or scoring defect. No private roster list, chart cells or narrative
excerpt is copied into this ticket.

## Resolution / verification

Verify the intended regular-season roster against authoritative sources
and correct the local data only with authorization. Check the provenance
of the roster-generation/import process for similar season mismatches;
do not assume a single incorrect entry proves every roster is wrong.
Do not commit/export historical team data or add historical-dependent unit
tests. Any loader/validation change must use synthetic/public fixtures and
keep historical verification in local-only tooling. See the
[sanitized audit](../../game-audit-2026-10-28.md). No fix authorized.

## Comments

--- 2026-10-28 12:47 ---
Opened separately at the user's request. Public historical fact and local
loader provenance verified; the installed private file has not been
edited, staged or exported. This is commentary-data accuracy work.

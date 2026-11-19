---
id: FLOW-035
title: Add roster-backed player narration to ordinary web plays
status: open
priority: Low
target-release:
created-at: 2026-11-17
resolved-at:
closed-at:
tags:
  - deferred
  - observed-ui
links:
  - FLOW-033
commits:
---

## Description

The owner observed generic ordinary-play descriptions during a TB '83 versus
CIN '83 game: the supplied log shows chart arithmetic such as `Add: 12+-3=9`
without player names. The owner confirmed the same behavior in the native web
application at `127.0.0.1:8000`, so this is shared web presentation behavior,
not evidence that the browser bundle lacks rosters. All 90 bundled public team
rosters were verified as loaded in the actual Pyodide runtime.

Read-only inspection of immutable v1.10.6 confirms that its backend never wired
`Commentary` or `ResultFormatter` into ordinary execute responses. The optional
`commentary` response field exists but is not populated; the frontend banner
supports that field, while ordinary play-log entries store only the raw
`description`. Existing engine-generated scoring and complex-result narratives
remain separate and may already contain names. This is an unscheduled, unassigned
follow-up to FLOW-033, not additional v1.11.0 release scope.

## Resolution / verification

- Write failing synthetic/public-2026 regressions before changing behavior. Cover
  ordinary runs, passes, incompletions and sacks with distinct offensive/defensive
  player names, both possession orientations, and missing-roster fallback.
- Reuse the existing core `Commentary` and roster loaders with the pre-play
  offense/defense chart identities. Return supplemental narration separately from
  the authoritative raw description; display it in the banner and persistent
  play log. Avoid activating unrelated unused formatter behavior.
- Preserve raw chart arithmetic, captured dice and rule explanations verbatim.
  Keep canonical engine narration authoritative for scores, penalties, turnovers,
  pending choices, special teams and other complex results; supplemental prose
  must never invent or contradict a resolved outcome.
- Prove narration changes neither engine state nor the global gameplay/AI random
  stream. Verify matching response behavior through HTTP and worker transports.
- Verify rendered narration and retained raw chart evidence in frontend tests,
  then play-test ordinary named actions in native and static browser builds.
  Keep historical/public-season checks in standalone integration qualification;
  unit fixtures remain synthetic or public 2026 only.

## Comments

--- 2026-11-17 21:52 ---
Owner requested this follow-up after comparing the TB '83/CIN '83 log with the
native application. Generic web narration predates the browser port in v1.10.6;
roster inclusion alone does not connect it to ordinary play presentation. No
production change, release assignment or completed fix is claimed.

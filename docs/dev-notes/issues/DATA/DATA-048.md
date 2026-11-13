---
id: DATA-048
title: Move fictional teams into sample and exclude them from season play
status: open
priority: Medium
target-release: v1.10.6
created-at: 2026-11-11
resolved-at:
closed-at:
tags:
  - release-planning
links:
commits:
---

## Description

The fictional Thunderhawks and Ironclads currently live in seasons/2026 and appear as a real season choice. Move the existing sample set to seasons/sample so 2026 is reserved for the actual NFL season. Samples remain available explicitly for demonstrations and automated tests but must not be offered as a season for season play. This is part of the v1.10.6 release scope discussion.

## Resolution / verification

- Add failing synthetic/sample regressions before production changes: numeric seasons remain discoverable, sample is absent from season-play choices, and explicitly loading sample teams still works.
- Move the fictional charts and their rules into seasons/sample with no changes to chart values. Define a valid non-calendar sample identity without pretending the sample set is a complete NFL season.
- Update core/CLI/web discovery, packaging manifests, browser fixtures, audit commands and documentation. Preserve sample/demo access separately from real-season selection and regular-season schedules.
- Update the repository development guide and synthetic/sample fixture paths so unit tests remain independent of historical or real current-season data. A real seasons/2026 directory must never become an accidental test fixture.
- Define saved-game compatibility for existing fictional 2026 team references using unambiguous team identity; do not remap real 2026 teams into samples or break historical saves.
- Update native install-verification profiles for the next release while retaining immutable 1.10.5 expectations. Run clean tracked-only tests, full regression, applicable reviewed chart/runtime evidence, and downloaded-package verification before declaring the migration released.

## Comments

--- 2026-11-11 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

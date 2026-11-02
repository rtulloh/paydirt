---
id: DATA-008
title: Generated season charts are excluded from published game builds
status: closed
priority: High
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: 2026-11-01
tags:
  - reproduced
links:
  - DATA-007
---

## Description

Release packaging includes only the fictional 2026 sample season. The independently
generated 1983 and 2024 chart sets are complete enough to publish, but current ignore
rules and PyInstaller specifications exclude them. The game also lacks a concise,
distributed notice that attributes the statistical sources and distinguishes generated
charts from original developer charts and raw source data.

## Resolution / verification

Publish only chart sets produced by this repository's generator. Keep original developer
charts, intermediate experiments, raw play-by-play, and replay artifacts ignored. Bundle
the accepted 1983 reconstruction as the normal `1983` season in release builds, bundle the
2024 reconstruction directly, and distribute a concise attribution and license notice on
all platforms. Verify the release specifications and documentation without loading
historical charts from unit tests.

## Comments

--- 2026-11-01 21:25 ---
Published the reviewed 1983 and 2024 generator outputs while retaining original and
intermediate chart directories in ignore rules. All four PyInstaller specifications map
`seasons/1983-generated` to the numeric release destination `seasons/1983` and bundle
2024 and 2026 under their numeric names. Platform packages and the offline season guide
carry the concise attribution. No raw play-by-play, downloaded pages, aggregate source
tables, actual-results CSVs, or original developer charts are included.

Loaded all 28 generated 1983 teams, 32 generated 2024 teams, and two 2026 sample teams
through the chart loader and verified a staged release exposes only `1983`, `2024`, and
`2026`. Core tests passed 6,327 with eight existing local-data skips; backend tests passed
279 with 20 existing Pydantic deprecation warnings; Ruff and documentation/issue checks
passed. Packaging itself was verified by specification and staged-tree checks because
PyInstaller is not installed in the current development environment.

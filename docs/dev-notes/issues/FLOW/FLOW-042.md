---
id: FLOW-042
title: Require every desktop package before publishing a release
status: open
priority: High
target-release: v1.12.2
created-at: 2026-11-19
resolved-at:
closed-at:
tags:
  - packaging
links:
commits:
---

## Description

The v1.12.1 Windows build encountered a Chocolatey HTTP 503 while installing NSIS. Both NSIS installation and installer compilation allowed failure, and uploading the portable executable satisfied a combined artifact upload despite the missing installer. The release published four assets; downloaded-native installer verification correctly failed because PaydirtSetup.exe did not exist. The other four actual packages passed functional verification. Retain the incomplete release and tag; correct under the next unused version.

## Resolution / verification

- Make installer acquisition and compilation fail closed; require both Windows files and the exact five-package inventory before publication; reject unmatched release uploads; demonstrate missing-file and acquisition-failure regressions before fixing the workflow; run full qualification and verify all five actual downloads on native platforms before closing. Browser play remains the preferred distribution.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 21:16 ---
The new regressions failed in twelve expected cases with twenty-two passing
controls before the workflow repair. NSIS acquisition and compilation now stop
the build on failure. Before publication, an executed guard requires every exact
nonempty package, rejects symlinks and extra stale DMGs, and the upload rejects
unmatched required files. The generated release text now leads with browser play.
The focused workflow/packaging suite passes 42 tests. Across the executed positive
and negative inventory cases, the inline guard covers all eleven statements and
eight branches; the per-fixture aggregate is reported separately rather than
mistaken for combined path coverage. This does not qualify native packages:
full regression, exact-commit CI and all-five downloaded verification remain
required. No retries or weaker gates hide an external installer-tool failure.

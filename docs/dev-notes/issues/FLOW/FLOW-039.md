---
id: FLOW-039
title: Align division standings across conference columns
status: closed
priority: Low
target-release: v1.12.0
created-at: 2026-11-19
resolved-at: 2026-11-19
closed-at: 2026-11-19
tags:
  - ui
links:
commits:
---

## Description

The overview places NFC and AFC side by side, but independently stacked conference tables make East and West division headings stair-step when corresponding divisions have different team counts. The owner requested aligned division starts for clearer comparison.

## Resolution / verification

- Add a browser geometry regression with unequal division sizes, demonstrate the initial heading offsets, and align corresponding desktop division rows using their natural heights. Preserve mobile NFC-above-AFC ordering, conference/division scope controls, accessible standings groups and arbitrary custom conferences. Run relevant frontend and browser checks.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 16:32 ---
Verified expected baseline misalignment of 50.25 pixels before the fix, then a passing real Chromium geometry test with all corresponding division headings within one pixel. The same test preserves conference filtering, a custom third conference and mobile NFC-before-AFC ordering. Forty-two existing SeasonDesk cases pass; changed-module coverage is 91.28% lines/89.14% branches, with every changed line covered. Remaining gaps are existing download/dialog/admin controls outside this focused suite. Full release regression and exact-commit CI remain publication gates.

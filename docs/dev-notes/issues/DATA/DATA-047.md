---
id: DATA-047
title: 1983 Chargers are presented as Los Angeles instead of correct San Diego naming
status: open
priority: Low
created-at: 2026-11-09
resolved-at:
closed-at:
tags:
  - reproduced
links:
commits:
---

## Description

The 1983 Chargers were the San Diego Chargers; the franchise did not move to Los Angeles until 2017. But the 1983 season metadata identifies the team with Los Angeles naming: seasons/1983/Chargers/team.yaml sets short_name "LAC '83", which is the modern Los Angeles Chargers abbreviation, and the player reported the team list showing 'Los Angeles Chargers' where 'San Diego Chargers' is expected. The 1983 roster (Dan Fouts, Kellen Winslow, Charlie Joiner) confirms it is the same San Diego-era franchise. The defect is in the team metadata/labels rather than gameplay charts.

## Resolution / verification

- Correct the 1983 Chargers metadata to era-accurate San Diego Chargers naming (team name, short_name/abbreviation) everywhere it is consumed: team lists, matchup banners, and any derived display labels.
- Audit the other bundled-season team.yaml metadata for similar era-mismatched city names or abbreviations before the fix.
- Add a synthetic/public-2026 regression that fails on era-mismatched team metadata before changing production data, and pass tests/test_issue_tracker.py after regenerating the index.

## Comments

--- 2026-11-09 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

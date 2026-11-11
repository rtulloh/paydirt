---
id: DATA-047
title: 1983 Chargers are presented as Los Angeles instead of correct San Diego naming
status: resolved
priority: Low
target-release: v1.10.5
created-at: 2026-11-09
resolved-at: 2026-11-10
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

--- 2026-11-10 00:00 ---
Corrected Chargers to SD '83. The bundled 90-team audit also identified and
corrected Cardinals ARI → STL and Raiders OAK → LA in 1983; all other
metadata associations passed. The standalone audit failed on exactly these
three labels before the edits and passes afterward. Synthetic/public-2026
loader controls pass; 459 focused tests pass with Python 3.11.
See [audit evidence](../../data-047-team-name-audit.md).
Browser play-test confirmation remains pending, so this issue is not closed.
The immutable released-chart gate fails on these three metadata files;
no policy exclusions were added and no push/release was performed.

--- 2026-11-10 00:01 ---
Owner approved the exact three-label gate allowance. The updated 1983 and 2024
released-chart gates pass; the 1983 receipt lists the accepted DATA-047 corrections
and their original/corrected hashes. Automatic post-publication native checks now
require the corrected labels for v1.10.5. Full pre-push regression and actual
downloaded-app/browser confirmation remain separate requirements.

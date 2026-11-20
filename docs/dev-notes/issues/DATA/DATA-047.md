---
id: DATA-047
title: 1983 Chargers are presented as Los Angeles instead of correct San Diego naming
status: closed
priority: Low
target-release: v1.10.5
created-at: 2026-11-09
resolved-at: 2026-11-10
closed-at: 2026-11-19
tags:
  - reproduced
links:
commits:
  - d893c42
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

--- 2026-11-10 21:31 ---
Fix committed as d893c42 for v1.10.5. Final regression passes: 11,195 core tests
with 86% branch-inclusive coverage, clean tracked-only tests, 450 backend tests,
362 frontend tests, build/lint, all historical games and reviewed public/private
AI audits. The owner's 18-case browser run passes. The fresh 1977 receipt accepts
only the approved exact version-string equivalence and retains its four disclosed
statistical misses. Both released-chart gates and the 90-team identity audit pass.
The browser run uses public 2026 teams; correction-specific downloaded-native
label checks remain required before closing this issue.

--- 2026-11-19 11:46 ---
Fresh local packaged-candidate acceptance independently confirms the corrected 1983 API labels Chargers SD, Cardinals STL and Raiders LA on both initial launch and app restart. The candidate also exposes all 28 unique 1983 team identifiers. This is a locally built macOS arm64 candidate, not a downloaded published artifact; correction-specific downloaded-release acceptance remains outstanding. Keep resolved, not closed. Evidence: ignored release-1.12.0/native-final-smoke/receipt.json, both launch API receipts.

--- 2026-11-19 12:25 ---
The final rebuilt c0b4292 native candidate independently reconfirms corrected SD/STL/LA 1983 API labels on both launches. Keep resolved: this is a locally built package, not the downloaded published-native acceptance required by this ticket.

--- 2026-11-19 22:49 ---
All five actual v1.12.2 downloaded-native profiles confirm the exact approved
1983 short names SD '83, STL '83 and LA '83, plus the complete unique team inventory.
The actual published Apple Silicon package now also passes correction-specific
rendered selection, scoreboard, chart and play checks in an isolated non-checkout
launch: Chargers/Cardinals and Raiders/Chargers each advance through coin toss,
actual kickoff and one scrimmage play; both teams' three chart sections contain
all 30 rows. All 28 rendered 1983 selection entries are present and the three
corrected labels remain visible during play. No JavaScript or request errors occur.

The test binds the published ARM DMG SHA-256
`72ea95514afe0a7ce1e842f7a3e40da6a591ab1c5e301ee43702d7f3d699e9a4`
and v1.12.2 commit `2618016116f4bf4489924aa63e6ca528d3332cce`.
The ignored targeted receipt is
`.ai-audits/release-1.12.2/data047-published-browser-ready-controls/receipt.json`;
the [published-native workflow](https://github.com/rtulloh/paydirt/actions/runs/44674721368)
records all five profiles. An initial QA helper raced the role controls; waiting
for their ready state fixes the helper without a product change. Closed from
actual corrected-label play and downloaded-native acceptance. This is not a full
game or fresh-quarantine first-launch proof; the Mac security limitation remains
explicit in the [readiness note](../../release-1.12.2-readiness.md).

---
id: DATA-044
title: 1983 Buccaneers commentary roster incorrectly includes Doug Williams
status: open
priority: Low
created-at: 2026-11-08
resolved-at:
closed-at:
tags:
  - reproduced
---

## Description

The local Week 6 player-game audit confirmed that Tampa Bay commentary names a
quarterback who had departed before the 1983 season. Both the original and
generated 1983 Buccaneers roster metadata include Doug Williams. The
[official Buccaneers season history](https://www.buccaneers.com/team/history/1983)
identifies his departure to the USFL and Jack Thompson as the new starter.
Private play logs remain local and ignored.

## Resolution / verification

Correct the season-specific roster provenance and audit the other listed players.
Add synthetic roster-selection regressions before changing behavior, and confirm
correct names in a subsequent play test. This finding concerns commentary names;
the audit did not establish an effect on chart resolution or the recorded score.

## Comments

--- 2026-11-08 18:00 ---
Recorded from a completed player-game audit. No gameplay changes made.

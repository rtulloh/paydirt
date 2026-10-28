---
id: RULE-001
title: Two-point tries run through run_play
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
links:
  - RULE-002
  - RULE-007
  - STAT-003
  - AI-022
tags:
  - reproduced
---

## Description

Two-point tries run through `run_play`: a successful try scores a TD (+6) and +2, logs two TDs, consumes 25–45 s (a Q2 try rolled into Q3 15:00), credits rushing yards/first down/play log/call history; a pick-six on the try awards the defense 6 and credits the Def 2PT to the wrong team; a plain interception leaves possession flipped, so the web kickoff picks the wrong kicker.

## Resolution / verification

Every existing two-point test mocks `run_play`. Add unmocked regressions first: +2 only, one scoring entry, clock/stats/history untouched, possession restored, correct Def 2PT team. Resolve the try in a conversion mode without scoring/clock/stat side effects.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (reproduced)).

--- 2026-10-20 17:30 ---
Priority changed from High to Medium: two-point conversion support is not a current product priority. The defect remains reproduced and must be addressed before prioritizing 2026 two-point-conversion play-testing.

--- 2026-10-28 14:00 ---
TRACE-009 investigation reconfirmed the known clock side effect using only
public 2026 fixtures: an actual medium-pass try from Q2 0:30 with a
synthetic two-yard gain and controlled 35-second duration advances to
Q3 15:00. The try still uses ordinary run_play. No change to conversion
mechanics is included in TRACE-009, and its zero-charge evidence is limited
to PAT kicks. This issue remains open; do not label two-point tries as
observed zero-time events until the conversion sandbox is implemented.

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
  - FLOW-018
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

--- 2026-11-06 10:34 ---
Synthetic/public retained-fumble/incompletion controls reconfirm ordinary BLACK
incomplete two-point attempts charge five seconds despite the untimed comment.
The new F INC subtype matches that existing path; its passing conversion checks
are compatibility evidence, not verification of zero-time conversion mechanics.
See `docs/dev-notes/retained-fumble-incompletion-engine.md`. Keep this ticket
open; no conversion sandbox or play-test closure is included in the chart fix.

--- 2026-11-06 14:20 ---
Uncommitted test-first repair and validation are in progress. See
[conversion completion evidence](../../two-point-conversion-completion.md) for
expected RED controls, implementation boundaries, and the disclosed retained-
fumble test expectation change. Keep open until the scoped fix is committed;
closure additionally needs actual engine/API/browser play-test evidence.

--- 2026-11-06 14:35 ---
Actual chart, API and browser checks now confirm exact two-point scoring,
defensive-return ownership, zero ordinary accounting/time/history changes and
restoration after early and late resolution exceptions. Both full real-engine
browser games and eight compiled conversion/0:00 final cases pass. The clean
public snapshot passes 10,166 core tests. The mandatory chart source gates fail
their missing source-preparation prerequisite; no full-regression or release
qualification is claimed. Keep open because the scoped repair is uncommitted.
See the linked completion evidence for receipts and remaining validation.

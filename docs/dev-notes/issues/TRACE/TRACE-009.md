---
id: TRACE-009
title: Half-ending touchdown and kickoff lack elapsed-time evidence to verify whether another snap was owed
status: closed
priority: Medium
created-at: 2026-10-28
resolved-at: 2026-10-28
closed-at: 2026-10-28
tags:
  - play-test-confirmed
links:
  - AI-007
---

## Description

The supplied local game has a touchdown call from Q2 0:45, a successful
try, and a kickoff-return fumble recovered by the kicking team, immediately
followed by halftime. No intermediate clock or per-event elapsed-time
breakdown establishes whether a scrimmage snap remained after the recovery
(local log lines 584-603). The missing evidence is confirmed; an improperly
removed snap is a possibility to investigate, not an established rules bug.

Current source uses a normal 25-45-second scrimmage duration and a separate
5-15-second kickoff duration; the PAT does not add a clock charge in this
sequence. Those ranges can exhaust 45 seconds, or leave time. For example,
35 + 10 seconds exhausts the half, while 25 + 5 leaves 15 seconds. These are
illustrations, not reconstructed random draws from the supplied game.
Neither the exact live draws nor the producing build are present in the log.

## Resolution / verification

Implemented immutable engine-owned ClockTrace records for ordinary direct/
penalty-procedure touchdown outcomes, QB sneaks, Hail Mary outcomes and
standard kickoff/return resolution. Each holds clock before/after, requested
seconds, actual charged seconds, and clock expiry/period transition.
An expiry cap is measured before the next period resets, not by subtracting
Q3 15:00 from Q2 time. Records are attached to their outcome, so later PAT/
kickoff actions cannot overwrite touchdown evidence. PAT kick descriptions
explicitly show zero charged time. Two-point conversion side effects remain
the separate known RULE-001 defect; no zero-time evidence is invented for them.

New and resumed CLI touchdown sequences display engine-generated clock
records without parsing dice or calculating time in the UI. No timing
rules, random draws, possession decisions or halftime flow changed.
AI-007 is already fixed separately. The original game cannot be exactly
reconstructed from its missing draws/build; this fix prevents the same
evidence gap in future ordinary touchdown/standard-kickoff sequences.
It does not establish that the original game lost a snap.

The sanitized investigation remains in docs/dev-notes/game-audit-2026-10-28.md;
the private original log/charts remain local and unchanged.

## Comments

--- 2026-10-28 12:47 ---
Opened separately at the user's request for the possible halftime clock
issue. Source inspection explains why halftime is possible under current
code but does not prove that the particular game charged the correct
elapsed time. Original log/charts remain local and untouched.

--- 2026-10-28 14:00 ---
User authorized the TRACE-009 fix. Test-first baseline: 18 expected
missing-evidence failures, 19 passing existing halftime controls after
repairing new CLI fixture setup. Dedicated coverage now also checks warning/
OOB/expiry caps, successful/failed PATs and period holds for pending fouls
or untimed downs. Two new period-hold cases caught and corrected an early
trace-labeling error (expiry is not period end while an extension is held).
No existing test expectation was changed. New floating-point clock checks
use pytest.approx because minute arithmetic produces normal tiny residuals.

Four complete public CLI games (Ironclads at Thunderhawks; seeds 19830601,
19830914, 8306, 8307) confirmed 492 per-outcome clock records, including 16
touchdowns, 13 expiry records, and 15 PAT kicks with zero charged time.
All games finished; period/final scores reconciled and no untimed downs
remained. Standings persistence was disabled. Natural evidence complements
the deterministic Q2 0:45 recovery cases, which explicitly verify the
next scrimmage prompt or halftime in both new and resumed CLI games.
The original private game still cannot be reconstructed from missing
draws: no claim is made that it incorrectly removed a snap.

--- 2026-10-28 14:01 ---
Final dedicated suite: 25 passing TRACE-009 cases. Clock/halftime/guide/
tracker focused checks: 253 passed. A clean staged-only snapshot (no
ignored season data) passed 6,198 core tests with 25 existing private-data
skips, 219 backend tests with 40 existing Pydantic deprecation warnings,
and Ruff. Earlier working-tree core/coverage run passed 6,239 with eight
existing skips at 77% coverage before the final seven trace controls were
added; all final controls passed in the clean snapshot. Browser regression
passed both complete Hard games plus offline guide navigation (two tests);
the existing stale Browserslist warning remains. No skips were introduced.

The local commit contains the fix, player-guide explanation, this ticket,
AI-007 reciprocal backlink, RULE-001 reconfirmation comment, and an index
generated from staged tickets only. Unrelated audit/ticket/permission work,
private charts, narrative logs, and standings are preserved. No push, tag
or release is authorized. This is not the full required pre-push regression;
private-season integration runners and both AI audits must run before any
future authorized push.

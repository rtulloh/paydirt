---
id: FLOW-018
title: Browser omits the season-enabled two-point conversion choice after a touchdown
status: closed
priority: Medium
created-at: 2026-11-06
resolved-at: 2026-11-07
closed-at: 2026-11-08
links:
  - RULE-001
  - STAT-003
tags:
  - reproduced
  - play-test-reproduced
---

## Description

The owner cannot choose a two-point conversion while playing 2024 teams in
the web review UI. The backend exposes season-owned `can_go_for_two` eligibility
for a pending try, but the original frontend store does not retain that value
when updating, starting or loading a game. The choice consequently remains
hidden. This is distinct from the engine's conversion scoring/timing defect
in RULE-001 and accounting side effects in STAT-003.

## Resolution / verification

The uncommitted frontend fix copies backend eligibility through update, start,
and load paths. The compiled review service on port 8157 includes this fix and
the conversion engine repair; it offers the season-enabled choice. Actual-engine
API and browser evidence is recorded below and in the linked completion note.

Before enabling the option in the review/release build, resolve RULE-001 and
its linked STAT-003 accounting assertions with unmocked public/synthetic engine
tests. Then verify the API and compiled UI together: an eligible pending try
offers both KICK XP and GO FOR 2, either human side can complete the try,
ineligible seasons hide it, true-to-false transitions clear stale eligibility,
and save/resume preserves the supported pending phase. Successful and failed
tries must leave correct scores, clock, statistics, possession and kickoff
flow. Require issue-specific real-engine browser confirmation before closure.

## Comments

--- 2026-11-06 14:07 ---
Opened a separate UI ticket after the owner again reported the missing 2024
choice and asked whether it was tracked. RULE-001 and STAT-003 already track
the engine blockers; AI-022 addresses conversion-specific CPU selection and
does not close this UI integration issue. No production code or review-build
eligibility changed while creating this ticket.

--- 2026-11-06 14:20 ---
Uncommitted test-first repair and validation are in progress. See
[conversion completion evidence](../../two-point-conversion-completion.md) for
expected RED controls, implementation boundaries, and the disclosed retained-
fumble test expectation change. Keep open until the scoped fix is committed;
closure additionally needs actual engine/API/browser play-test evidence.

--- 2026-11-06 14:35 ---
The new isolated compiled review at `http://127.0.0.1:8157` includes the root
store's three existing eligibility assignments and both timeout counts. Actual
engine/browser cases pass home/away successful and failed tries, correct next
kickoff receiver, prohibited-season stale-choice clearing, saved pending tries
and Q4 0:00 final screens without a kickoff. The required eighteen-case browser
suite also completes both real games. Original owner services/storage remain
preserved. Keep open until committed; the source-gate failures prevent a full
regression qualification claim. See the completion evidence linked above.

--- 2026-11-06 14:45 ---
Completion audit added actual API cases for successful/failed/defensively
returned halftime tries, the second-half kicker and receiver, and defensive
returns before ordinary kickoffs and Q4 0:00 finals, from either human side.
Ten expected failures plus a passing season control on the saved old engine
become ten passes on the repair; the expanded full backend passes 411 tests in
both shared and clean public checkouts. Production identity is unchanged.
The completion note also discloses the unrelated random modifier-test fixture
failure and its stronger deterministic repair. Status remains open/uncommitted.

--- 2026-11-06 16:18 ---
Timestamp is CST (22:18 UTC).
After the isolated 8157 service was restored, the owner confirms: "2pt choice
now shows in the UI." This supplies direct owner play-test evidence for choice
visibility. The owner has not yet reported a try outcome; scoring, clock and
accounting evidence remains the existing automated checks. Four fresh live API
success/failure cases from both human sides preserve time/statistics/history and
route the next kickoff correctly. Eight live chart books match their preserved
snapshot CSVs. The attempted fresh browser recheck was blocked before page
interaction by macOS Chromium launch permission; earlier successful browser
receipts remain unchanged. Keep open while the fix is uncommitted. Recovery
receipts remain local in ignored release-readiness/resume-2026-11-06-01/.

--- 2026-11-08 16:36 ---
Completed-work reconciliation: Pending-try eligibility propagation shipped in 8c0bb8b. November 6 real-engine browser success/failure checks cover both human sides, prohibited seasons and final/halftime flow; the owner confirmed the choice was visible. The v1.10.2 hosted two-point browser cases pass, and current conversion API tests pass.

The earlier keep-open/uncommitted wording records its original checkpoint;
it is superseded by this closure. See the [full review](../../open-issue-reconciliation-2026-11-08.md)
and [published verification](../../release-1.10.2-scope.md#published-release-verification).
Closure uses the recorded issue-specific gameplay/integration evidence plus
committed-source review, not unit tests alone. No new full regression was run.

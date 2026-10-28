---
id: SPIKE-001
title: The S modifier adjusts time without charging the agreed additional down
status: closed
priority: High
created-at: 2026-10-18
resolved-at: 2026-10-28
closed-at: 2026-10-28
links:
  - SPIKE-003
---

## Description

The `S` modifier adjusts time without charging the agreed additional down.

## Resolution / verification

For `7S` called on first down, an applied completion-plus-spike must leave third down, including when the pass earns a first down. An incompletion needs no spike and leaves second down. Resolve penalties before determining the spike effect. Add explicit tests for the agreed first-down-gain exception; do not substitute conventional football assumptions.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

--- 2026-10-28 08:58 ---
Fixed in the core engine, with 46 new synthetic/public regressions. Before
production changes, the focused baseline had 28 expected failures and 108
passing controls (18 new controls plus the existing spike/clock suites).
No existing test expectation was changed, weakened or skipped.

An applied S modifier charges a down and updates the engine outcome and
transaction final down/spot/possession. The explicitly agreed exception is
preserved: a first-down call plus spike leaves third even after earning a
first down. Yardage, first-down statistics and call history remain those of
the actual play; no fictional chart roll or extra yardage is introduced.
A third-down play falling short can leave fourth, then the spike exhausts
that down and changes possession through GameState.next_down. Incomplete,
OOB, scoring, turnover and failed-fourth-down outcomes do not charge a spike.
Existing requested-offensive-timeout precedence and base clock cap are unchanged.

S-only context survives a pending scrimmage foul without early state changes.
Retaining the play applies an eligible spike afterward; accepting a penalty
or offsetting fouls does not spike. Consuming the context avoids carrying an
old request into another decision. RULE-006 remains open for T/T+S snapshots;
SPIKE-002 remains open for defensive-timeout priority. Neither is claimed fixed.

Player clock guidance and the stale AGENTS down-cost statement are updated.
No API schema, frontend rule logic, guide navigation or packaging change is
needed: displays receive the corrected core state. Full core: 5,964 passed,
eight existing skips, 77% coverage; backend 219 passed with existing Pydantic
warnings; frontend 255 passed/one existing skip, Ruff, production build, both
complete Hard browser games and offline guide checks pass. Existing stale
Browserslist warning remains. Clean staged-only check is still pending.

Standalone games, 13/13 historical games, 224/224 generated regular-season
games and 9/9 playoffs passed (ten regular-season OT games, three valid ties,
no playoff ties; no standings saved). Both full AI audits passed and were
reviewed: public/local 32/32 and 448/448 games, 3,938/52,962 calls, 200/3,068
groups; no Hard warning. Same one balanced advisory remains (see AI-009).

--- 2026-10-28 08:59 ---
Case-specific full-game confirmation, not just unit tests: an instrumented
replay of all 13 historical + 224 generated + nine playoff games observed
17 S requests, eight applied spikes, nine ineligible requests, and one actual
first-down-gain exception leaving third down. Four S requests crossed penalty
decisions: two enforced penalties correctly did not spike; two plays were
retained, of which one was eligible and spiked afterward. Checked final down,
field position, possession/turnover-on-downs agreement and unchanged call
count on every applied spike. All games completed. This directly confirms
the reported missing-down and first-down-gain cases plus delayed-foul handling,
so close SPIKE-001 with this local fix. No spike-at-period-expiration event
occurred in this observation; SPIKE-003 is not newly closed from it. Private
charts/narratives stay local, no standings were saved, nothing pushed.

--- 2026-10-28 09:02 ---
Clean staged-only checkout passed 5,933 core tests with 25 existing ignored-
data skips, 219 backend tests with existing Pydantic warnings, and project
Ruff. Corrected a timestamp-only tracker comment-format error before this
successful full staged-only run. All pre-existing gameplay expectations are
unchanged. The scoped local commit includes only this fix, tests, guidance
and tracker/audit evidence; unrelated permission and ticket work stays unstaged.
Full regression and issue-specific play-test confirmation are complete.
No push, tag or release performed.

--- 2026-10-28 11:48 ---
SPIKE-002 full-game revalidation observed 18 S requests: seven applied,
nine ineligible, and two correctly cancelled by useful defensive timeouts
before charging a down. Both cancelled cases preserved the post-play down.
The existing additional-down regressions still pass. SPIKE-002 is now
confirmed separately; this does not claim new SPIKE-003 expiration evidence.

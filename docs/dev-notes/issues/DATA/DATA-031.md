---
id: DATA-031
title: Fumble return replay still credits nullified yardage and sacks
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
  - chart-audit
links:
  - DATA-020
  - VAL-018
---

## Description

The new repeated-call campaign fails strict play denominators for public 2024
Giants at Seahawks (seed 20336783, repeat-screen and repeat-short-pass) and Bills
at Rams (seed 20466944, repeat-medium-pass). A fumble return encounters offsetting
fouls, setting result.replay_down and restoring the preplay state. The observer
correctly excludes that no-play, but the engine's shared scrimmage-credit helper
still records the primary fumble's yards and, for a nonpositive QT fumble, a sack.
Voided ordinary rushing/completion fumbles also leak yardage without necessarily
breaking the play-count identity. DATA-020's earlier observer correction is
retained; this is a separate authoritative box-score defect.

## Resolution / verification

Twelve public-2026 regressions first fail on leaked rushing/passing/sack totals;
twelve retained-play controls pass. They cross direct and penalty-procedure
routes, offensive and defensive recovery returns, and rushing/completion/QT-sack
fumbles. The shared core credit helper now refuses replay_down results. All 131
focused fumble, return and observer tests pass; no existing assertion changes or
skips. Fresh complete repeated-call campaigns and root regression are running.
The old failed campaign is retained, and old runtime receipts cannot certify the
changed engine. Full charter validation and independent review remain required.

## Comments

--- 2026-11-05 23:04 ---
Opened from complete-schedule repeated-call stress, not merely unit tests.
Baseline 12 expected failures/12 passing controls, followed by 131 passing focused
tests. Reports and reproduction remain local in ignored chart-confidence storage.
Release remains held.

--- 2026-11-05 23:13 ---
Fresh complete repeated-call campaigns pass all eighteen families: 2,016 1983
and 2,448 2024 games, including the three previously failing passing campaigns.
Every game's box/play identities reconcile. Core checkpoint passes 7,472 tests,
eight existing skips, 82% coverage; later auto-learning work has a distinct
runtime and is not covered by this checkpoint. The core replay-credit fix is
play-tested locally but remains open pending the full charter validation/review.
Resolved issue inventory was reviewed; these receipts do not independently
confirm unrelated narrative, interactive-control or rare-return closure criteria.

--- 2026-11-06 00:18 ---
Fresh full-exposure public training completes 31,744 games and reconciles every
game/team box total, offensive-play identity and 4,590,012 ordered calls.
The retained decision records include 2,116/1,551 nullified selected fumbles
(1983/2024). This supplies additional natural play confirmation beyond the
original eighteen repeated-call campaigns and unit regressions. The current
source-tool addition changes the conservative package fingerprint to
c31059f80baf5ec0930f703fcf7fa2f81a4d365a53c8f064fc9400edbf691c85;
both training reports identify that runtime. Charter fit/review remain separate
and incomplete; retain the issue's pending final-review status.

--- 2026-11-06 00:49 ---
Current policy/family/repeated-call campaigns finish 13,392 games with every
box/play/scoring identity and 1,947,385 calls reconciled. The receipts contain
1,585 nullified selected fumbles, adding natural-play confirmation for the replay
credit correction. The real isolated public unit checkpoint also passes 7,761
core tests with 25 preexisting private-data skips. Full charter acceptance and
independent review remain separate and incomplete; retain pending final review.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Replay-down credit guard is committed with natural nullified-fumble campaign evidence; final independent confirmation remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

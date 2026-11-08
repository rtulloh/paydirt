---
id: DATA-023
title: Primary pressure allocation ignores conditional QB Time sacks and defensive overlap
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
---

## Description

The shared 1.7 multiplier treats each team's sack rate as the same primary QT
requirement. QT actually contains team-specific sacks and scrambles, and neutral
defense already contributes pressure. Under a synthetic .08 sack target, the
old model produces .0368/.1072/.1394 as conditional sack shares change. Its
denominator is counted attempts plus sacks; positive and numeric-zero scrambles
are excluded. QT F0 is a sack before recovery movement.

## Resolution / verification

Four new controls fail before the local correction. Primary QT allocation now
uses weighted conditional outcomes and core priority survival/overlap under the
declared normal policy. Primary fumbles protect against defensive QT, penalties
remain pending, and attempt-conditional incompletions/interceptions rescale when
QT changes. Targets without sack support or outside attainable pressure fail
explicitly. The tactical defense template and official target facts are unchanged.
This allocation is a reference-policy model, not historical pass-family truth.

The second 2024 training trial reduces maximum team sack error from .04685 to
.01688 across 1,088 legal games, still short of acceptance sample size and with
one team sack miss. Final all-team, held-out and policy evidence remains required.
Keep open pending the full charter and parent review. See
[implementation evidence](../../chart-confidence-implementation.md).

## Comments

--- 2026-11-05 20:30 ---
Test-first local implementation only. No public chart promotion, commit or release.
Held-out family remains unopened. General variant allocation changes and all
existing expectation revisions are disclosed in the implementation evidence.

--- 2026-11-05 22:26 ---
Fresh fully reconciled 1983 input exposes a genuine lower-bound feasibility
failure for San Diego (28 source sacks/635 pass attempts). Under a declared
neutral profile, all five pass families require joint QT mass .042728 but their
neutral-defense floors range .046217–.047766. A separate all-28-team inventory
confirms no other team has this continuous-pressure failure. Generation stops
without a complete manifest; no clamp, target change or favorable fallback is
introduced. This needs a general pressure-allocation correction and new synthetic
regressions before another candidate, not relaxation of the fixed fit contract.

--- 2026-11-05 22:37 ---
The subsequent test-first QB-family correction changes the conditional QT
population. It supersedes the sole-San-Diego inventory above: both San Diego
(required joint QT .041931) and Los Angeles (.046095) fail all five pass families,
whose floors are .046217–.047766 and .047110–.047766 respectively. All source sack
counts still reconcile. No source correction is reverted to conceal this model
floor; shared source-constrained allocation is being designed before production
changes. Fixed targets and acceptance bounds remain unchanged.

--- 2026-11-05 22:45 ---
The shared source-constrained neutral-pressure procedure is implemented test-first
with no team/year fitting table. Eight capability failures/49 controls and two
root propagation failures precede correction; a later F+2 spelling mutant exposes
and removes duplicated sack classification. 284 integrated and 95 runtime/tactics
tests pass with lint. Both source commands now prepare the whole cohort and use
one resolved template for offensive overlap and defense. Fresh all-28-team 1983
output completes under a neutral profile with one common relocation; all 84 CSVs
reproduce and the source component passes. 2024 requires zero relocations and all
96 CSVs reproduce/source-pass. Fixed targets/bounds stay unchanged. Four-repetition
training diagnostics are pending; this is feasibility, not final fit or closure.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Conditional sack/defensive-overlap allocation and shared neutral-pressure preparation are committed; final all-team/held-out/policy validation remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

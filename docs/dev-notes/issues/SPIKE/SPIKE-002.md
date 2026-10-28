---
id: SPIKE-002
title: Offense 7S is processed before a defensive AT, so execution order blocks the agreed defensive-timeout priority
status: closed
priority: Medium
created-at: 2026-10-18
resolved-at: 2026-10-28
closed-at: 2026-10-28
links:
  - AI-005
  - RULE-006
---

## Description

Offense `7S` is processed before a defensive `AT`, so execution order blocks the agreed defensive-timeout priority.

## Resolution / verification

Resolve penalty decisions, then an applicable defensive timeout, then any remaining spike request. Charge a useful available defensive timeout, cancel the planned spike, and charge no spike-related down. An unavailable timeout cannot cancel the spike; incompletions charge neither. Log the winning procedure.

## Comments

--- 2026-10-18 00:00 ---
Migrated from the single-file tracker (status at migration: Open).

--- 2026-10-28 11:48 ---
Fixed in the core: penalty decision, useful defensive timeout, then remaining
spike request. Pre-snap defensive ownership/timeouts survive a scrimmage
foul; retained eligible plays arbitrate afterward, enforced/offsetting fouls
charge neither procedure. A defensive win marks the outcome, logs the
winning procedure and cancels S before it can consume a down. Unavailable
timeouts preserve eligible spikes, and incompletions/OOB need neither.
New/resumed CLI games pass both human AT and CPU requests into the engine;
the resumed loop no longer discards S. No frontend rule logic was added.

Test-first baseline: 16 expected failures and 107 passing controls across
the new priority tests and existing defensive-timeout/spike-down suites.
After the fix and boundary regressions, all 320 focused clock/spike/AI
penalty checks pass, including 76 new synthetic/public cases. Additional
boundary tests exposed the first-half reset/old-budget fallback and newly
reached two-minute-warning cases before their corrections. No existing
test expectation or skip was changed. Incomplete-pass base timing is
intentionally unchanged. A clock-saving procedure restoring first-half
time also restores first-half budgets; fresh second-half timeouts cannot
fund a first-half request. A spike cannot be charged after an already
ended period when even its 20-second cap cannot preserve time.

Issue-specific play-test confirmation: instrumented replay of all 13
historical reproductions, 224 generated games and nine playoffs observed
326 defensive requests, 165 useful timeouts, and four competing S/AT
requests. Two useful timeouts cancelled S with unchanged post-play down;
two competing requests correctly did not apply a timeout. Across 18 S
requests: seven applied, nine ineligible, two defensive cancellations.
All games completed, no playoff ties, and no standings were saved. This
confirms the actual reported ordering defect, not merely unit-test coverage,
so close SPIKE-002. No new natural period-expiration case confirms
SPIKE-003. RULE-006 offensive T/T+S snapshots and FLOW-007 remaining loop
divergences remain separate. Private reports/charts/narratives stay local.

--- 2026-10-28 11:49 ---
Full regression passed: 6,117 core tests, eight existing private-data skips,
77% coverage; 219 backend tests (39 existing Pydantic deprecation warnings);
255 frontend tests (one existing skip); Ruff; production build; both
complete real-engine Hard browser games and offline User Guide. Existing
stale Browserslist warning remains; no dependencies changed or vulnerabilities
remediated in this scope. Standalone games, 13/13 historical reproductions,
224/224 generated games and 9/9 playoffs passed, with 13 regular-season
overtime games, three valid ties and no playoff ties. Public/local AI
audits passed 32/32 and 448/448, with 3,909/52,903 calls reconciled across
200/3,090 groups; existing balanced advisory is recorded in AI-003.
Clock-management guidance and AGENTS integration guidance updated; no guide
navigation, packaging or API schema change needed. Clean staged-only
validation follows before the local commit. Nothing pushed, tagged or released.

--- 2026-10-28 11:53 ---
Clean staged-only checkout passed 6,079 core tests with 25 existing
ignored-data skips and 219 backend tests (37 existing Pydantic warnings).
Initial Ruff invocation in the metadata-free checkout linted an unchanged
integration runner normally excluded by repository ignore rules; initializing
Git metadata in that temporary checkout restored identical ignore handling,
and the same Ruff command passed. No source, test expectations or lint
configuration was changed to mask that tooling-context failure. The working
checkout had already passed Ruff. Scoped tracker/docs/focused checks passed
521 in the working checkout and 513 in the staged-only checkout. Unrelated
permissions/tickets and ignored local data are
not part of the commit. No push, tag or release authorized or performed.

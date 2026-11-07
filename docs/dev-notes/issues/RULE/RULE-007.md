---
id: RULE-007
title: Uncommitted _log_score try attribution relies on scoring_plays[-1] being the TD
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
links:
  - RULE-001
---

## Description

Uncommitted `_log_score` try attribution relies on `scoring_plays[-1]` being the TD; with RULE-001 unfixed a 2PT attaches to the spurious TD, and the try keeps the live clock time.

## Resolution / verification

Fix with RULE-001; pass the TD scoring entry/quarter explicitly from the try methods.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

--- 2026-11-06 14:20 ---
Uncommitted test-first repair and validation are in progress. See
[conversion completion evidence](../../two-point-conversion-completion.md) for
expected RED controls, implementation boundaries, and the disclosed retained-
fumble test expectation change. Keep open until the scoped fix is committed;
closure additionally needs actual engine/API/browser play-test evidence.

--- 2026-11-06 14:35 ---
Both try methods now pass the captured preceding touchdown entry explicitly to
the score logger. Actual chart controls retain that touchdown's period/time,
including a second-quarter touchdown with live state already in the third
quarter, without creating an ordinary touchdown entry. Keep open pending the
scoped commit; see the linked completion evidence and source-gate limitations.

--- 2026-11-06 14:45 ---
Actual API completion controls now verify a second-quarter touchdown followed
by a successful or defensive-return try while live state is Q3 15:00: only the
proper try entry is added, with the captured touchdown's period/time. The failed
try adds no score entry. Both human sides and the following second-half kickoff
pass. These add play-flow evidence without changing the production repair.

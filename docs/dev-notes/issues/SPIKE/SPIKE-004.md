---
id: SPIKE-004
title: Standalone spike passes a minute value to the seconds-based clock
status: closed
priority: Medium
created-at: 2026-11-06
resolved-at: 2026-11-07
closed-at: 2026-11-08
links:
---

## Description

The current-candidate HTTP smoke found a standalone `S` at Q2 1:30 leaving 1:29 rather than 1:27. The core passed `0.05` to `_use_time`, which accepts seconds; `0.05` was the intended three seconds expressed in minutes. This also allowed an extra play with two seconds left in a half. The separate play-plus-spike modifier uses minute-valued state adjustments and is a different path.

## Resolution / verification

Use three seconds for the standalone clock call. New public-sample regressions cover both engine entry points in all four quarters, half/game expiration with two seconds left, fourth-down possession changes, and no chart dice. All fourteen new cases failed against the unchanged implementation for the expected timing mismatch; ten existing standalone controls passed. The focused post-fix run passes all twenty-four cases. No existing test expectation was changed or skipped. The clock-management guide now states the three-second standalone duration.

Keep this ticket open pending a committed tested fix and the project's remaining qualification. Fresh current-service HTTP confirmation is recorded below; this component fix does not establish full release qualification.

## Comments

--- 2026-11-06 20:24 ---

Found while staging the corrected sixty-team visual-review candidate. The frozen port8158 snapshot retains the failing behavior and its HTTP probe for provenance; stage a separate updated snapshot after the root's focused verification. Evidence remains in ignored `.ai-audits/release-readiness/current-ui-review-01/` and `resume-2026-11-06-01/standalone-spike-*.log`.


--- 2026-11-06 20:24 ---

The separate port8159 snapshot now includes the fix. Four actual HTTP season/role cases preserve the unchanged 90→87 seconds and down-two assertions; twelve additional HTTP cases confirm Q2/Q4 expiration and fourth-down turnovers. The parent independently verified the runtime identity and served asset bytes, and rehashed all nineteen bound service artifacts and 434 snapshot files. Related core clock/spike/timeout regression passes 302 cases; the backend suite passes 421 cases with eighteen existing Pydantic `dict` deprecation warnings. Documentation/tracker checks pass. Service receipt: ignored `current-ui-review-02/service-readiness-01.json`, SHA-256 `a92566a66ad3d9c9232a51310b3b29ed0eb884a3513e73b8d48dc834e788ab2a`. Browser launch remains blocked by the host permission error; no full E2E pass or release qualification is claimed. No issue status or existing expectation changed.

--- 2026-11-08 16:36 ---
Completed-work reconciliation: The standalone three-second clock call shipped in 8c0bb8b. November 6 served HTTP checks verify 90 to 87 seconds, half/game expiration and fourth-down possession changes across 16 cases. Current standalone-spike regressions pass, and later v1.10.2 hosted core/browser qualification is recorded. This does not close unrelated spike/modifier issues.

The earlier keep-open/uncommitted wording records its original checkpoint;
it is superseded by this closure. See the [full review](../../open-issue-reconciliation-2026-11-08.md)
and [published verification](../../release-1.10.2-scope.md#published-release-verification).
Closure uses the recorded issue-specific gameplay/integration evidence plus
committed-source review, not unit tests alone. No new full regression was run.

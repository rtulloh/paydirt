---
id: FLOW-011
title: Web conversion endpoints execute without a pending touchdown try
status: resolved
priority: High
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at:
tags:
  - reproduced
---

## Description

`attempt_extra_point` and `attempt_two_point` in `paydirt-web/backend/routes.py`
do not require a pending PAT before invoking the engine or arming a kickoff.
With a fresh public 2026 game, a direct extra-point request returned 200,
added a point and entered kickoff state before any touchdown. A two-point
request also returned 200 and changed the score and kickoff state. The +8
result observed on a successful try is separately tracked in RULE-001; the
missing phase guard affects both conversion endpoints independently.

## Resolution / verification

Both API endpoints now require the backend's pending-try flag before changing
engine or kickoff state. The two-point endpoint also rejects seasons that do
not allow two-point conversions. API regressions cover fresh and game-over
requests without a pending try, duplicate requests after a valid attempt,
valid pending tries including a final regulation try, the season eligibility
control, and extra-point availability when two-point conversions are disabled.
The new regressions produced eight expected failures against the old routes.
The existing request-shape test now marks a try pending: the old fresh-game
expectation was wrong because no touchdown had made a PAT owed. No engine-level
test was needed because pending-try phase state is maintained by the web route;
the engine conversion methods still handle the actual try once the API accepts
it. Backend tests pass (279 passed); Ruff passes for the backend.

## Comments

--- 2026-10-30 15:09 ---
Reproduced both endpoints with isolated FastAPI TestClient games and public
sample teams; no external service or persisted game was used.

--- 2026-10-30 17:24 ---
Added phase and season guards without blocking a valid untimed try after a
game-ending regulation touchdown. Duplicate and invalid calls leave the game
unchanged.

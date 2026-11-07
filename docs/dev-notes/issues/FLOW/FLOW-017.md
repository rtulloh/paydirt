---
id: FLOW-017
title: Scoreboard omits the opponent timeout budget and leaves the displayed count ambiguous
status: open
priority: Low
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - play-test-reproduced
---

## Description

The scoreboard shows only the human team's timeout budget under a generic
TIMEOUTS heading. In the completed owner game, the human had three while the
CPU had used all three; the owner could not see the opponent budget and thought
the CPU had not called timeouts. The problem occurs whether the human is home
or away. Counts are already supplied by the backend; no new game logic is needed.

## Resolution / verification

Local frontend change displays `TO: n` beneath each team's score, including
zero, with team-specific accessible labels. The timeout action remains tied
to the human team and reads Call timeout. The scoreboard wraps on narrow
screens so both budgets remain visible. No engine behavior changes.

Test-first baseline: six new display regressions fail because team-labeled
budgets are absent; five new timeout-action controls and 24 existing scoreboard
tests pass. Added coverage includes human home/away, either possession, zero,
independent budget updates and unavailable timeout actions. Existing test
expectations are unchanged. Browser checks cover both counts inside a phone
viewport using synthetic saved positions and public-2026 teams. Keep open
while the local change remains uncommitted and publication checks are pending.

## Comments

--- 2026-11-06 14:00 ---
Owner identified the ambiguous single-team scoreboard count after reviewing
the completed game's timeout usage. The canonical browser guide now explains
both team counts and the human timeout action. Test receipts stay under ignored
`.ai-audits/timeout-display-review-01/`; no private chart data is needed.

--- 2026-11-06 14:01 ---
Verification: all 343 frontend tests pass, including 35 scoreboard cases.
Scoreboard coverage is 100% statements/lines/functions and 89.47% branches.
Both focused Chromium checks pass against the compiled review service on 8156;
team-labeled counts fit inside the 390px viewport on offense and defense.
The production and held-eligibility review builds both pass, with the existing
stale Browserslist warning. Documentation/tracker checks: 363 passed.
An initial browser harness hit an occupied port; its alternate development
origin then encountered the backend's existing CORS restriction. The passing
run uses the compiled service's normal same-origin API routing. Cleanup now
uses the actual load-response origin so it deletes the created game from the
correct service. No existing test expectations changed. No complete pre-push
regression or release qualification is claimed by these focused checks.

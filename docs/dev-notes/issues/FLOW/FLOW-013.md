---
id: FLOW-013
title: Web modifier panel hides defensive timeout requests and does not forward them to the engine
status: open
priority: High
created-at: 2026-11-02
resolved-at:
closed-at:
tags:
  - reproduced
---

## Description

The human defender cannot select the next-play timeout modifier: both the
playing screen and PlayModifiers hide the panel on defense. The execute
endpoint also omits the existing engine's `call_defensive_timeout` argument.
Simply exposing the panel would submit invalid formation `AT` instead of `A`.
The separate scoreboard TO button does not provide this next-play request.

## Resolution / verification

Show None and Timeout on both sides of the ball, with the human's home/away
budget. Keep no-huddle, OOB and spike on offense. Disable controls and
shortcuts during execution and required decisions, and prevent the keyboard
from selecting exhausted timeouts. Forward an explicit defensive-timeout
flag through the API to the existing engine procedure; reject offensive
callers attempting to request the opposing team's timeout. Expose the engine's
applied flag in execute and penalty-decision responses.

Clear the browser selection after a successful submission even if a foul
requires a choice; the engine retains the request until that choice is final.
Both accepted and declined fouls already stop the clock, so no timeout is
spent. No core rules are changed.

## Comments

--- 2026-11-02 13:51 ---
Before production changes, backend regressions produced eight expected
failures and eight passing controls; mounted frontend regressions produced
nine expected failures and eight passing controls (including the five existing
modifier tests). Fixed a missing penalty_index in the new test fixture, and
corrected its proposed declined-foul expectation to the existing clock rule
before recording this baseline. No existing expectation or skip was changed.
Tests use public 2026 teams and synthetic results only. Browser confirmation
and verification are pending; the fix is uncommitted.

--- 2026-11-02 13:56 ---
Both real-engine browser games complete (35–42 human home, 23–24 human away),
each confirming six defensive timeouts through the modifier panel, exactly
one halftime and clean NEW GAME state. The offline guide passes too.
Review then exposed keyboard cancellation ignored while a radio has focus:
an additional regression fails as expected with six passing controls. Keep
text entry unaffected, permit shortcuts on radios, and require the browser
suite to exercise cancellation and reselection before repeating both games.

--- 2026-11-02 13:59 ---
Final browser verification passes both complete games again, with the same
35–42 / 23–24 finals, 145/157 executed plays, 13/11 kickoffs, exactly one
halftime each and six human defensive timeouts each. Both games verify
keyboard cancellation/reselection with a focused radio, correct human timeout
ownership, exhausted controls, cleared selections and clean NEW GAME state.
The offline guide passes. No API/browser errors occur. Reviewed the resolved
issue inventory; these games provide no issue-specific evidence for closing
other tickets.

Backend suite: 296 passed with 18 existing Pydantic deprecation warnings.
Frontend suite: 280 passed, one existing skipped kickoff-component test.
Core timeout/priority and documentation checks: 77 passed. Ruff, diff checks
and the production build pass; existing stale Browserslist and browser
NO_COLOR warnings remain. The earlier coverage run measured 92% statement
coverage for PlayModifiers; whole-screen/API coverage remains lower because
those modules include unrelated flows. No existing test expectation or skip
was changed.

Rebuilt the local served UI and restarted the normal service on port 8000.
Health, API schema and served-JavaScript checksum confirm the new UI/API are
active. Raw reports remain ignored in `.ai-audits/flow-013/`. Implementation
and browser verification are complete locally; this ticket remains open
until the uncommitted fix is committed. No push or release was performed.

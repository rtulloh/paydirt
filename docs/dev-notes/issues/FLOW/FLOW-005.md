---
id: FLOW-005
title: Second-half kicker was guessed from current possession in resume_game ("Approximate") and in the web kickoff…
status: closed
priority: Medium
created-at: 2026-10-19
resolved-at: 2026-10-19
closed-at: 2026-10-20
tags:
  - was: implemented, uncommitted
links:
  - RULE-002
  - RULE-010
---

## Description

Second-half kicker was guessed from current possession in `resume_game` ("Approximate") and in the web kickoff endpoint; the engine never recorded the opening kicker. The web also showed halftime only from the `/execute` response and returned early for a pending PAT before that check, so a touchdown that ended the second quarter skipped halftime and the scoring team kicked off; the kickoff and penalty-decision endpoints hard-coded `half_changed=False`.

## Resolution / verification

Exposed by the RULE-010 trajectory change in the required browser suite. Test-first: 19 engine cases (opening kicker recorded once by kickoff/onside, `halftime_pending()` after Q2-ending TD/PAT, safety, penalty decision, kick return and ordinary plays, not for other transitions, cleared by the second-half kickoff, `prepare_second_half_kickoff()`, save/resume of the opening kicker), 3 API cases (Q2-ending TD → PAT → halftime pending with the opening receiver kicking; Q2-ending penalty decision reports halftime), 2 Vitest cases (halftime shown once from the engine flag, after an outstanding try). Engine owns `opening_kicking_home`, `halftime_pending()`, `second_half_kicking_home()`, `prepare_second_half_kickoff()`; saves persist the opening kicker with a legacy fallback; the web state carries `halftime_pending`, all kick setup goes through one backend helper, and the frontend drives the halftime screen from the engine flag. `resume_game` uses the engine query. A game-ending final try no longer arms a kickoff (found by the browser suite after RULE-002).

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Implemented, uncommitted).

--- 2026-10-20 17:00 ---
Play-test confirmation: NYG '83 kicked off to PHI '83 to begin Q3 after the 2nd-quarter scoring sequence. PHI received at PHI 25 and continued at 1st & 10. Halftime occurred once; second-half ownership matched the engine's opening-kicker rule. FLOW-005 is closed.

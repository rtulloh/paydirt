---
id: FLOW-023
title: Choose end-zone interception returns during play
status: open
priority: Medium
target-release: v1.10.6
created-at: 2026-11-11
resolved-at:
closed-at:
tags:
links:
commits:
---

## Description

The pre-game end-zone interception preference is too coarse for situational coaching. A human should decide after the engine establishes the interception catch location, with score and time visible, but before any return dice are rolled or return outcome is revealed. A catch at the goal line or one yard deep while trailing may warrant a different choice from a deep catch while protecting a lead. Implement the same core-engine pending decision in CLI and web; the CPU should decide using catch depth and game situation.

## Resolution / verification

- Write failing synthetic/public-2026 regressions before production changes, including goal-line, one-yard-deep and deep catches, leading/trailing situations, and unaffected field-interception controls.
- Default human behavior is Ask each time. Present Touchback and Attempt return after catch location is known and before return dice; show engine-provided catch depth, score and clock.
- Keep all rules and pending-decision state in the core engine. CLI and web display and submit the same decision; resolving it once cannot duplicate rolls, turnovers, clock changes or statistics.
- CPU decisions use catch depth and game situation without advance knowledge of return dice; add meaningful tests for the policy.
- Saving and loading preserves an unresolved interception decision and its random state. Define backward-compatible handling of existing saved preferences; retain Always take touchbacks as an optional convenience.
- Preserve existing board-game touchback/depth mechanics and legal return eligibility. Update CLI/web player guides, API documentation and affected browser tests; complete required full regression and actual play-test confirmation.

## Comments

--- 2026-11-11 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-13 00:00 ---
Implemented the in-play choice in the core engine, CLI and web, with tests first.
Core: policies are ask/auto/return/touchback per team; an ask interception in the
intercepting team's own end zone returns a pending outcome with engine-provided
catch depth, catch field position, score/clock text and return team. No return
dice, possession, clock or statistics change until
`apply_end_zone_interception_return_decision(outcome, attempt_return)` resolves it
once. Requested spikes and defensive timeouts are retained across the pause.
`auto` uses the shared depth/score/clock policy in `paydirt/interception_policy.py`;
old boolean preferences and saves still map to return/touchback. Pending saves
serialize the deferred play and the captured dice RNG state.
CLI: new games ask the human in play; the CPU uses auto. Both game loops and
post-penalty resolution prompt with the engine situation.
Web: `/api/game/new` accepts policy fields (legacy booleans retained) for
compatibility, but the browser game always sends ask for the human and auto for
the CPU. `/api/game/execute` and `/api/game/penalty-decision` expose the pending
fields; `/api/game/end-zone-interception-decision` resolves once (repeat
submission is 400). The in-game panel shows catch depth, score and clock. There
is no pre-game return menu.
No stored return outcome is revealed before the choice.

Failing-first baselines: the new core test module failed to import until the
policy module existed; the pending/decision tests then failed before the engine
API, save/RNG round trip and policy existed. Verification run so far:
`tests/test_end_zone_interception_decision.py` 29 passed (repeated for flake
control), `test_end_zone_interception_returns.py` plus related interception/
save/penalty/game suites passed, backend `test_end_zone_interception_policy.py`
passed, frontend panel/team-select tests passed, production build passed and
ruff passed. `npm test -- --run` still shows pre-existing Node localStorage
failures in PlayingPhaseSave/PlayingPhaseTwoPoint in this environment.

Remaining before closure: repository full regression (including the 1983/2024
chart audits, season runners, AI audits and real-engine browser E2E) and
issue-specific human/CPU play-test confirmation. This comment does not claim
those gates or relabel prior receipts.

--- 2026-11-13 18:30 ---
Regression results for the implemented candidate:
- Core unit suite with coverage: 11269 passed, 86% total (17:42).
- Web backend: 450 passed. The one remaining failure is the pre-existing
  Pydantic-v1 runtime check in `test_frozen_launcher.py`
  (`__pydantic_complete__`); `requirements.txt` pins Pydantic 2.5.0.
- Frontend unit suite: 366 passed with
  `NODE_OPTIONS=--no-experimental-webstorage`. Node 25's built-in localStorage
  otherwise shadows jsdom and breaks 12 storage-setup tests; this is an
  environment issue, not a product regression.
- Browser E2E: 18 passed, including both full real-engine games.
- `tests/run_all_games.py` passed; 1983 full season passed
  (224 regular + 9 postseason); public 2026 and 1983 AI audits passed.
- Released-chart regression for 1983 and 2024 returned the expected FAIL:
  "Gameplay implementation inventory changed; paired trusted-baseline
  qualification required", with trusted-content mismatches in
  `routes.py`, `computer_ai.py`, `game_engine.py`, `game_state.py`,
  `interactive_game.py`, `play_resolver.py` and `save_game.py`. This is the
  documented consequence of an intentional gameplay change, not a relabeled
  pass or a tolerance change. Owner-reviewed paired evidence against the
  immutable baseline is still required before release.

Supporting fixes made while running the required checks: the web chart endpoint
and E2E try fixture now use `dict()` when `model_dump()` is unavailable
(Pydantic-v1 local runtime only); the seeded CLI clock harness answers `T` at
the new end-zone prompt to preserve its previous automatic-touchback outcomes;
and the generated issue index was regenerated after correcting the DATA-049
front-matter status/closed-at inconsistency.

Still outstanding: clean tracked-files-only unit run, the separate 1977 release
policy gate, downloaded native-install verification, and issue-specific
play-test confirmation. No push or release claim is made here.

--- 2026-11-13 18:45 ---
Owner direction: whether to return is a game-time play decision only. The
pre-game end-zone return menu was removed from team selection, including the
previous "Always take touchback"/"Always attempt return" convenience options.
Every new browser game sends human `ask` and CPU `auto`. When the human team
intercepts in its own end zone, the in-game panel offers TAKE TOUCHBACK or
ATTEMPT RETURN after the engine reports catch depth, score and clock, before any
return dice. Engine/audit callers may still declare explicit policies for
controlled runs and legacy compatibility; those settings are not exposed in the
game UI.

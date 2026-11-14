---
id: FLOW-029
title: Browser regression assumes a defensive timeout is used by the request that asked for it
status: closed
priority: High
target-release: v1.10.6
created-at: 2026-11-14
resolved-at: 2026-11-14
closed-at: 2026-11-14
tags:
links:
  - AI-002
commits:
---

## Description

The required browser regression failed reproducibly on 2026-11-13 and 2026-11-14
with the same seed pair (20261026/20261027) at
`paydirt-web/frontend/e2e/full-games.spec.js:209`:
`expect(sent.call_defensive_timeout).toBe(true)`.

The real cause is not a penalty-retained timeout. The route forwards the CPU
defence's own timeout decision (`cpu_defensive_timeout or
request.call_defensive_timeout` in `paydirt-web/backend/routes.py`), so an
ordinary human offensive call can return `defensive_timeout_used: true` with no
`call_defensive_timeout` field in the request body. Instrumented run evidence
from the failing browser game:

```
/api/game/execute  {"player_play":"1","call_defensive_timeout":false,"cpu_play":"A",...}
  -> "Add: 1 + -1 = 0 ... | Defensive timeout: clock stopped."
```

The test assumed the flag reports every engine-confirmed timeout and that the
human budget always decreased by one. Both assumptions are wrong for a CPU
timeout. The assertion predates FLOW-023 (8c0bb8b, 2026-11-07); later engine and
dice-flow changes made this seeded game reach a CPU defensive timeout.

## Resolution / verification

- Add a failing-first control that exercises a retained defensive timeout resolved by the penalty-decision endpoint.
- Scope the request-body assertions to the execute endpoint (or assert the retained-timeout contract) so the real-engine browser regression passes both complete games without weakening its timeout evidence.
- Re-run the browser step and record the pass before the next push.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-14 15:40 ---
Corrected the original hypothesis and fixed the regression check. The first
report guessed a retained defensive timeout resolved by the penalty-decision
request; a backend probe disproved that path (`_should_apply_timeout_after_play`
refuses when `clock_stopped_for_penalty` or the outcome is a turnover), and an
instrumented browser run showed the actual case: a human offensive call whose
response reported the CPU defence's own timeout.

Fix is test-side, because the product behaviour is correct and already
documented in `docs/clock-management.md`: the browser loop now splits
`defensiveTimeouts` from `humanDefensiveTimeouts`. A request that carries the
flag must be a human defence control with the human budget down by one and the
selected defense call; an unrequested timeout must be a CPU decision during a
human offensive call, with the human budget unchanged. Both complete games
still require at least one human-requested timeout, the keyboard timeout
exercise, the description text and the exhausted-control checks.

Added the contract the loop depends on:
`paydirt-web/backend/tests/test_defensive_timeout_api.py::test_cpu_defense_timeout_is_reported_without_a_human_request`
asserts an unflagged execute reports the CPU timeout and leaves the human budget
untouched. `paydirt-web/frontend/e2e/README.md` records the rule.

Play-test confirmation: `full-games.spec.js` passed (4.3m), then the complete
browser suite passed 18/18 (6.1m) on isolated ports 18012/15185. No production
code, expectation about gameplay, or other check was weakened.

---
id: FLOW-029
title: Browser regression assumes a defensive timeout is used by the request that asked for it
status: open
priority: High
target-release: v1.10.6
created-at: 2026-11-14
resolved-at:
closed-at:
tags:
links:
  - AI-002
commits:
---

## Description

The required browser regression fails reproducibly on 2026-11-13 and 2026-11-14 with the same seed pair (20261026/20261027) at paydirt-web/frontend/e2e/full-games.spec.js:209: expect(sent.call_defensive_timeout).toBe(true). The response reported defensive_timeout_used while the captured request body had no call_defensive_timeout field. The assertion is only valid for the execute endpoint: a human defensive timeout requested with the T modifier is retained by the engine across a pending penalty choice, and the /api/game/penalty-decision request that resolves the retained play reports defensive_timeout_used=true with a penalty-decision body. The assertion predates FLOW-023 (8c0bb8b, 2026-11-07), so later engine or dice-flow changes made the penalty-plus-timeout combination occur in this seeded game. 17 other browser checks pass; both full games are otherwise unaffected. Local receipt: .ai-audits/full-regression/20261114T130120Z/browser.log (ignored).

## Resolution / verification

- Add a failing-first control that exercises a retained defensive timeout resolved by the penalty-decision endpoint.
- Scope the request-body assertions to the execute endpoint (or assert the retained-timeout contract) so the real-engine browser regression passes both complete games without weakening its timeout evidence.
- Re-run the browser step and record the pass before the next push.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

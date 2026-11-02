---
id: FLOW-012
title: Competing CPU fourth-down requests can restore a stale kick panel after possession changes
status: closed
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - reproduced
links:
  - VAL-015
---

## Description

The playing screen requests the CPU's fourth-down decision from an effect and
again on an early defense click. A late first response can restore the kick
panel after the second decision has executed and possession has changed.
Confirming that stale panel submits defensive formation A as an offensive
play and the real engine rejects it with HTTP 400.

This was reproduced while fixing the browser driver failure in
[run 41499019565](https://github.com/rtulloh/paydirt/actions/runs/41499019565).
A timing-only hold of the first genuine CPU response exposed the competing
requests; no engine response content or game state was replaced.

## Resolution / verification

One effect owns the outstanding request. Early defense clicks wait for it;
failed requests can be retried, and a completed go-for-it decision is reused.
Effect cleanup discards replies after navigation, unmounting or a changed
engine situation. Starting execution clears the cached go-for-it decision.
All coaching choices still come from the engine.

Twelve mounted component regressions cover duplicate requests, stale replies,
new-game ownership, go-for-it reuse, retry and ordinary punt controls. Against
unchanged production code they produced ten expected failures and two passing
controls. All twelve pass after the fix, alongside four existing component
tests. No existing expectation or skip was changed. Full browser confirmation
and the complete pre-push regression are required before closing.

## Comments

--- 2026-11-02 12:37 ---
The strengthened real-engine browser regression first exposed HTTP 400 for
offensive play A. Added and ran the mounted regressions before production
changes; the failures show competing requests and stale global decision state.
Raw traces and logs remain in ignored local audit storage.

--- 2026-11-02 12:39 ---
Closed after the real-engine browser play test completes both full games
(35–13 home/receiving, 24–17 away/kicking), with 156/149 execution calls,
eight/nine kickoffs, exactly one halftime each and clean NEW GAME state.
The first game must and does follow the delayed CPU confirmation after an
early defense click. No stale panel, HTTP error, browser error or duplicate
execution occurs. The offline guide also passes. Reviewed the resolved-ticket
inventory; these games add no specific new evidence to close unrelated issues.

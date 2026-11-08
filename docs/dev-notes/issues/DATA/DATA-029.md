---
id: DATA-029
title: Zero-yard nonfumble sacks are represented as QT scrambles
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
---

## Description

Known zero-yard sacks cannot be expressed by legacy numeric QT cells: zero means
scramble, while F0 adds a real fumble. The 2024 source has 87 nonfumble sack rows
with known zero structured gain. Replacing them with minus one would fabricate
loss. Negative/zero initial fumbles and net recovery movement are separate facts.

## Resolution / verification

The reviewed proposal adds narrow QT-only `SACK 0[*]` with a typed flag and the
existing SACK result enum. Both resolver routes, engine statistics/clock, observer,
source classifier, opponent adjustment, generator, loading, pressure model and
exact audits require synthetic regression controls before production. Numeric-zero
scrambles and real F0 fumbles retain their behavior. No UI game logic is added.

The new representation allows an adjusted negative sack to reach zero severity
while retaining sack class. This supersedes DATA-027's temporary minus-one floor;
new failing controls and explicit expectation-change disclosure are required.
See [representation proposal](../../zero-yard-sack-representation-proposal.md).
Keep open pending full source regeneration and charter validation.

## Comments

--- 2026-11-05 21:12 ---
Seventeen expected baseline failures and sixteen passing controls preceded the
QT-only representation. The integrated source/generator/resolver/audit suite
passes 361 tests. Two chart-viewer display cases failed first, then all 26 viewer
tests pass; the viewer displays the typed token and adds no game decision.
Numeric-zero, F0 and negative/positive controls retain their distinct behavior.
The runtime observer inventory separately exercises a real zero-yard sack.
No full source regeneration or final chart campaign has yet certified this fix.

--- 2026-11-05 21:30 ---
Parent approved the narrow test-first design. Official targets and bounds stay
fixed; no source class, fumble or yard loss is invented. Recovery roll identities
and ranges remain unchanged. This does not resolve initial-versus-net F gains.

--- 2026-11-06 00:05 ---
The maintained public-source archive/staging/preparation chain reproduces both
full cohorts (84/96 CSVs), complete generation manifests and chart fingerprints
from relocated actual inputs. This supplies fresh source reproducibility,
not final source-fit/held-out or complete play-test acceptance. Representation
and source-model distinctions remain explicit; retain open pending the remaining
charter validation. No private reference inputs are opened or exported.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: QT-only SACK 0 is committed across source, resolver, engine, observer, generator and audit paths; final source/charter validation remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

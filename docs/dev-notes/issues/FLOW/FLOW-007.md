---
id: FLOW-007
title: Resumed CLI omits spike and skipped-modifier messages; duplicated game loops still diverge
status: open
priority: Medium
target-release: v1.10.7
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
links:
  - FLOW-027
---

## Description

`resume_game` never passes the human/CPU spike modifier and prints no skipped-modifier messages; other divergences from the new-game loop: OT banner, safety punt option, CPU offensive-timeout helper, hard-coded quarter advance with `time_remaining = 15.0`.

## Resolution / verification

Extract one shared per-down routine used by both loops; regression matrix across new/resumed.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

--- 2026-10-28 11:45 ---
SPIKE-002 wires both human/CPU S and defensive AT requests through the core
for new and resumed CLI games. The resumed loop no longer discards the S
flag; real-engine synthetic/public regressions cover both control sides.
Keep FLOW-007 open for skipped-modifier messages and the remaining loop
divergences/shared-per-down refactor; this does not claim they are fixed.

--- 2026-11-11 12:00 ---
1.10.6 scope review corrects the obsolete title: both loops pass call_spike, call_timeout and defensive timeout requests to the engine. SPIKE-002 already fixed the lost-spike request. The resumed loop still prints only timeout-used output after display_play_result; the new-game loop separately prints spike-used and skipped timeout/spike messages. The duplicated loops remain and hard-coded quarter clock assignments are still present. Narrow remaining work to presentation/parity and justified shared-loop cleanup, not reimplementing spike execution. Combined focused penalty/spike suites: 188 passed; no new full CLI presentation play-test or production change.

--- 2026-11-13 22:40 ---
The 2026-11-13 review of `cedf6117..HEAD` found one more new/resumed divergence
in the same family: a restored pending end-zone interception is printed but its
outcome is never processed, so a return touchdown or safety skips the try and
kickoff or the safety free kick. Tracked as [FLOW-027](../FLOW/FLOW-027.md) so
that defect can be verified on its own; the shared-loop and presentation items
above remain open here.

--- 2026-11-17 18:15 ---
Deferred to v1.10.7 during the v1.10.6 release review. The remaining work is a
broader CLI parity and shared-loop cleanup with no evidence of blocking the
completed v1.10.6 gameplay fixes or the Week 7 play-test. Keeping it out of the
release avoids expanding scope after regression and play-test qualification.

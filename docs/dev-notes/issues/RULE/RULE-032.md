---
id: RULE-032
title: Late timeout overwrites the next period clock
status: resolved
priority: High
target-release: v1.11.0
created-at: 2026-11-17
resolved-at: 2026-11-17
closed-at:
tags:
  - browser-spike
links:
  - FLOW-033
commits:
---

## Description

The all-season browser regression returned a genuine engine state with Q3, zero seconds, halftime pending and timeout budgets 3/2 after a Q2 screen pass with an out-of-bounds designation. A deterministic public-2026 reproduction shows that a timeout admitted with about 10.5 seconds left restores old-half budgets and then clamps its adjusted clock to zero over the newly initialized Q3 clock. The next kickoff can advance straight to Q4. Chart files are unaffected.

## Resolution / verification

- Use public 2026 or synthetic fixtures to reproduce before fixing; preserve a fresh next-period clock and halftime timeout budgets when a requested timeout cannot retain playable old-period time; retain useful offensive and defensive timeout controls across Q1-Q4; keep the browser halftime 900-second assertion and complete both full games in every public season.

## Comments

--- 2026-11-17 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-17 20:22 ---
The test-first baseline produced 44 failures and 37 passing controls. The narrow
fix rejects timeout requests that cannot preserve playable old-period time before
restoring or charging timeout budgets; the low-level adjustment also preserves an
already advanced period clock. All 242 focused timeout regressions pass, including
the real screen-pass/out-of-bounds pipeline with both timeout owners. An independent
review and 362 broader clock tests pass. No existing expectation was weakened.
Full regression and eight browser games are being repeated. Keep resolved pending
issue-specific play-test confirmation; unit tests alone do not close this ticket.

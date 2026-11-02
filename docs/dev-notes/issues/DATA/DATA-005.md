---
id: DATA-005
title: Empirical chart generation discards numeric out-of-bounds markers
status: closed
priority: Medium
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: 2026-11-01
tags:
  - reproduced
  - play-tested
---

## Description

`paydirt.chart_generator._empirical_column` accepts numeric outcomes with a trailing
asterisk, but stores only the integer and emits an unmarked value. A synthetic input
of one hundred `4*` outcomes produces thirty `4` cells. The engine parses `4*` as
out of bounds and `4` as in bounds, so empirical reconstruction changes clock
semantics and consequently game volume and late-game behavior.

This does not explain the aggregate-only 2024 replay results. It affects the
empirical path proposed to improve reconstruction accuracy. See the
[generator review](../../statistical-chart-generator.md#concrete-code-findings).

## Resolution / verification

Add failing synthetic regressions before production changes for all-marked and
mixed marked/unmarked numeric samples, with plain numeric and symbolic controls.
Preserve yardage and clock semantics jointly when quantizing outcomes. Verify
the written/loaded chart and actual engine clock behavior, not just strings or
conditional numeric averages. Record any changed expectations and confirm the
fix through an appropriate public/synthetic play test before closing.

## Comments

--- 2026-11-01 15:04 ---
Reproduced during pending-change review using synthetic data only. No production
fix or test expectation change was made. Existing focused tests pass but do not
cover preservation of the numeric asterisk.

--- 2026-11-01 17:40 ---
Fixed test-first. Empirical validation now rejects unsupported offense and special-teams
result symbols with the source row number. Numeric outcomes carrying `*` or `†` are
quantized as marked outcomes instead of being converted to bare integers. Synthetic
coverage verifies mixed `4`/`4*` frequencies, written/loaded chart values, and the
engine parser's out-of-bounds interpretation. The focused generator suite passes.
The issue remains resolved pending broader empirical season play-test confirmation.

--- 2026-11-01 23:20 ---
Generated all 28 1983 teams from 224 regular-season PFR play-by-play games and
ran 100 Hard-vs-Hard replays of the actual schedule. The empirical path retained
marked numeric results through CSV generation and engine loading. During source
reconciliation, 13 accepted-penalty field goals marked `no play` were found to be
entering kick calibration; a failing regression was added before excluding them.

All 22,400 affected replay games completed after regeneration. The broader test
shows remaining calibration errors, but the DATA-005 information-loss defect no
longer occurs in the empirical pipeline. Close the ticket; the combined offense
and defense calibration work remains tracked by DATA-006.

---
id: STAT-007
title: Distinguish offense yardage columns in compact season statistics
status: open
priority: Low
target-release:
created-at: 2026-11-19
resolved-at:
closed-at:
tags:
  - ui
  - statistics
links:
commits:
---

## Description

The owner reports that repeated YDS headings in the season offense statistics make total, passing and rushing yardage difficult to distinguish. Their ESPN example groups abbreviated columns under Total, Passing, Rushing and Points. The current table should preserve its compact presentation while making each yardage category clear without requiring users to infer it from column order.

Consider distinct visible abbreviations such as TYDS/PYDS/RYDS, or accessible grouped headings that make the total/passing/rushing relationship explicit. Passing columns must also distinguish gross passing yards from net passing yards where both appear. Select the final design during implementation rather than treating the example as a mandated copy of ESPN.

This is a release follow-up for team statistics, not a release-blocking defect. No UI implementation change is requested in this ticket-creation task. The existing cumulative team-statistics feature remains documented by STAT-006.

## Resolution / verification

- Make total, passing and rushing yardage visually distinguishable in offense tables; distinguish gross and net passing yardage where both appear. Use reviewed compact labels or coherent grouped headings without relying on color or column position alone.
- Preserve accessible full metric names, table header associations, keyboard-operable sorting and accurate sort indicators. If grouped headings are chosen, associate them with the individual columns for assistive technologies.
- Preserve totals versus per-game semantics, units, rate/percentage formatting and known-versus-unknown statistic coverage. Labels must describe the engine-provided team values rather than recalculating them.
- Keep tables legible and unambiguous on desktop and narrow screens, including horizontal scrolling. Keep the feature team-only; do not imply individual player statistics.
- Before a UI change, add a meaningful failing regression for the selected behavior with synthetic/public-2026 fixtures, then review rendered desktop/mobile headings, sorting and accessibility. Run applicable frontend and real-engine browser checks and update affected player guidance.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 21:12 ---
Created at the owner's explicit request as a nonblocking follow-up. This records the ambiguity and design constraints only; no UI, statistics, release qualification or prior ticket status changed.

---
id: LINT-001
title: Ruff gate fails on 756 default-rule violations across 29 files
status: open
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at:
closed-at:
tags:
links:
commits:
---

## Description

The required pre-push gate 'ruff check paydirt/ tests/ paydirt-web/backend/' fails with 756 violations: 602 E701 (multiple statements after a colon), 149 E702 (semicolon-joined statements) and 5 E731 (lambda assignment). 755 violations are in 29 test modules added with the 1977/chart-validation work; exactly one is production code, the end_rule lambda assignment in paydirt/game_engine.py. Verified with both ruff 0.15.2 and a pinned ruff 0.9.10, so this is a real backlog rather than tool-version drift: a7c70cb (2026-10-26, after the lint-backlog cleanup) is clean, v1.10.3 has 696, v1.10.4 has 747, and v1.10.5/HEAD has 756. The CI lint job runs the same command with an unpinned 'pip install ruff', so the gate has been failing across those releases. The project config selects ruff defaults and only ignores E402/F401; E701/E702/E731 have no autofixes. Chosen remedy: reformat the affected modules with 'ruff format', replace each lambda assignment with an equivalent def, and keep the rule set unfiltered.

## Resolution / verification

- 'ruff check paydirt/ tests/ paydirt-web/backend/' exits 0 with no per-file ignores added for these rules.
- All 29 reformatted test modules pass, and the full core pytest suite remains green.
- paydirt/game_engine.py end_rule no longer assigns a lambda and its return-chain tests still pass.
- No gameplay, chart, or frontend behavior changes are introduced; the diff is formatting plus the engine lambda rewrite.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

---
id: LINT-001
title: Ruff gate fails on 756 default-rule violations across 29 files
status: resolved
priority: High
target-release: v1.10.6
created-at: 2026-11-13
resolved-at: 2026-11-13
closed-at:
tags:
links:
commits:
  - 2e43766
---

## Description

The required pre-push gate `ruff check paydirt/ tests/ paydirt-web/backend/` failed with 756 violations: 602 E701 (multiple statements after a colon), 149 E702 (semicolon-joined statements) and 5 E731 (lambda assignment). 755 violations were in 29 test modules added with the 1977/chart-validation work; one was production code, the `end_rule` lambda assignment in `paydirt/game_engine.py`.

Verified with both ruff 0.15.2 and a pinned ruff 0.9.10, so this was a real backlog rather than tool-version drift: `a7c70cb` (2026-10-26, after the lint-backlog cleanup) is clean, v1.10.3 has 696, v1.10.4 has 747, and v1.10.5/HEAD has 756. The CI lint job runs the same command with an unpinned `pip install ruff`, so the gate was failing across those releases. The project config selects ruff defaults and only ignores E402/F401; E701/E702/E731 have no autofixes.

## Resolution / verification

- 28 affected test modules were reformatted with `ruff format`, clearing all 755 E701/E702 violations. The four test-file lambda assignments were rewritten as equivalent `def` statements.
- The single production E731 in `paydirt/game_engine.py` was **not** rewritten. `paydirt.released_chart_regression_audit` byte-compares every runtime module under `paydirt/` and `paydirt-web/backend/` against the immutable v1.10.3 baseline, and the 1977 gate fingerprints the same runtime sources; any byte change there fails `gameplay_implementation_unchanged`. The gate was confirmed PASS with the file restored, so the fix stays out of scope until a separately reviewed gameplay change. A scoped `per-file-ignores` entry for that one file and rule records the reason in `pyproject.toml`.
- `ruff check paydirt/ tests/ paydirt-web/backend/` now exits 0 with no other per-file ignores.
- Full core suite at the time of the reformat: 11219 passed, with the only 2 failures caused by this ticket's own malformed front matter (see below). The affected modules and the issue-tracker, documentation and permission regressions pass afterwards.
- A defect found while creating this ticket was fixed in the same commit: `scripts/create_issue.py` emitted `tags: !!seq ''` on this PyYAML version, which the line-based tracker parser read as a one-character link. Empty lists now serialize as bare `key:` lines, with a regression test in `tests/test_create_issue.py`.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-13 07:20 ---
Fix committed as 2e43766 (v1.10.6): 28 test modules reformatted, four test lambdas rewritten, scoped engine exception documented, `create_issue.py` empty-list serialization repaired. `ruff check paydirt/ tests/ paydirt-web/backend/` exits 0; no gameplay, chart or frontend behavior changed. Engine byte identity was re-verified with `paydirt.released_chart_regression_audit --season 1983` (PASS) before and after reverting the formatter's rewrite of `paydirt/game_engine.py`.
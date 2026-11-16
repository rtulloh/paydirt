---
id: FLOW-006
title: Resume_game scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick)
status: resolved
priority: Medium
created-at: 2026-10-19
resolved-at: 2026-11-15
closed-at:
tags:
  - code-read
  - tested
---

## Description

`resume_game` scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick). The engine scores at play time, so a save with the ball at the goal line already includes the points; the path would double-count. Currently latent in the CLI.

## Resolution / verification

Replace with an engine-owned completion method or remove; align with the web `load_replay` behavior.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

--- 2026-11-11 12:00 ---
1.10.6 scope review: resume_game still directly adds six touchdown points or two safety points and appends generic ScoringPlay entries. Existing tests/test_resume_pending_score.py mirrors manual score additions and checks kickoff ownership; those tests do not demonstrate score-idempotent handling of an already-scored real save. Retain as open/code-read pending a real-engine save/resume regression; do not describe double scoring as newly reproduced in this review. No production change.

--- 2026-11-15 00:00 ---
Fixed the save/resume contract. The engine now records `pending_post_score_action` (`try`, `kickoff`, or `safety_free_kick`) and persists it with `last_play_start_quarter`. `load_game` returns that engine-owned follow-up and no longer infers an unscored touchdown or safety from `ball_position`. `resume_game` runs only the try/free kick/kickoff a previous play left due; it never adds points or writes a synthetic ScoringPlay. A malformed end-zone save without a matching scoring record is rejected.

Test-first evidence: `tests/test_resume_score_state.py` forces real engine touchdowns and a real safety, saves them, reloads, and asserts unchanged score and scoring log plus exactly one follow-up action. It also covers a missed try, an owed field-goal kickoff, and malformed end-zone saves. A resumed kickoff returned for a touchdown was found to skip its try during review; that regression now fails first and passes with the resumed kick routed through the shared touchdown sequence. The obsolete ball-position tests in `tests/test_resume_pending_score.py` were removed because they asserted the incorrect contract; no remaining assertion was relaxed. Review-adjacent evidence: 429 save/scoring/kickoff/CLI tests and the full unit suite (11514 passed) are green; Ruff passed. Full regression still required before commit.

--- 2026-11-15 18:30 ---
Post-review hardening (codex findings P1/P2). P1: the legacy end-zone fallback also ran for modern saves that explicitly recorded no owed action, so a completed overtime touchdown invented a try. Migration is now limited to saves whose marker key is absent, and it honors `can_attempt_conversion_after_touchdown`; `resume_game` likewise refuses an ineligible try marker. P2: `setup_for_kickoff()` cleared the owed kickoff/free-kick marker before the kick ran, so a save between setup and execution lost the kick. Setup now preserves the marker and only the executed kick consumes it. Tests added: completed-OT-TD reload owes no try, stale try marker on a finished game runs no conversion, kickoff setup keeps the marker, and the kick consumes it. Updated the two malformed-save tests to delete the marker (true legacy shape) and `test_audit_scoring_semantics` to require an actual kick before the marker clears, with half/period-ending tries correctly owing none. Focused suites: 148 and then 444 passed; Ruff passed.

Final local evidence for this change set: full unit suite 11519 passed (18:35), focused save/resume/scoring/kickoff/CLI suites 444 passed, documentation/tracker 461 passed, Ruff clean. Backend suite 462 passed with one unrelated pre-existing failure (`test_frozen_launcher`, Pydantic/Python 3.15 `ChartBookResponse.__pydantic_complete__`). Full regression remains the owner's gate before commit. Ticket stays resolved pending a real CLI save/reload play-test.

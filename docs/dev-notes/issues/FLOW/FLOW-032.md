---
id: FLOW-032
title: Hail Mary end-zone interception deferral uses ordinary scrimmage timing
status: resolved
priority: Medium
target-release: v1.10.6
created-at: 2026-11-14
resolved-at: 2026-11-14
closed-at:
tags:
  - code-review
links:
commits:
---

## Description

Found in the 2026-11-14 review of the FLOW-028 Hail Mary deferral fix. A Hail Mary own-end-zone interception that is deferred for the ask choice finalizes through _apply_play_result, which uses ordinary scrimmage timing of 25-45 seconds. Immediate Hail Mary resolution uses 5-15 seconds in _handle_hail_mary. Merely changing the policy from touchback to ask, then choosing touchback, can therefore consume extra time and incorrectly end a half or game. Verified with identical synthetic interceptions: the deferred path requests random.uniform(5,15) versus random.uniform(25,45).

## Resolution / verification

- Add failing-first public/synthetic regressions comparing immediate and deferred Hail Mary interception timing under identical synthetic dice. Preserve the originating play's timing semantics across deferral, including touchback and return resolution, while retaining one-time clock, possession, scoring and statistic application. Run focused Hail Mary/interception/clock suites and update this ticket with evidence.

## Comments

--- 2026-11-14 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-14 18:20 ---
Fixed. The pending own-end-zone interception state now carries the originating
play's clock range (`play_seconds_range`), and
`apply_end_zone_interception_return_decision` passes it to `_apply_play_result`
instead of always using the ordinary 25-45 second scrimmage roll. The Hail Mary
deferral records `HAIL_MARY_PLAY_SECONDS` (5-15), matching immediate Hail Mary
timing; ordinary scrimmage deferrals keep `ORDINARY_PLAY_SECONDS` (25-45). The
range is serialized with the pending choice; legacy saves without the key
restore `None` and keep scrimmage timing. Malformed saved ranges raise
`ValueError`.

Tests first: six new cases failed against the unchanged engine with the
deferred path requesting `(25, 45)` instead of `(5.0, 15.0)`; the direct
scrimmage control passed. New tests compare immediate touchback vs ask-then-
touchback and immediate return vs ask-then-return under identical synthetic
dice, assert both final state tuples match, cover save/load round trip,
malformed saved ranges, and single application of clock, possession, score and
statistics. Focused interception/timeout/resume/Hail Mary suites: 244 passed;
`test_save_game.py` + `test_game.py`: 31 passed; Ruff passed; the new
`game_engine.py` lines report covered except unrelated pre-existing branches.
Full regression and browser E2E were not run for this ticket; the pre-commit
full-regression receipt for this branch remains pending.

--- 2026-11-14 21:05 ---
Follow-up from the read-only review of the FLOW-032 fix. Three items addressed.

Non-finite saved ranges (P2): `_restored_play_seconds_range` now converts each
bound to float, rejects any `OverflowError`/`ValueError` as `ValueError`, and
requires both bounds finite, non-negative, at most `MAX_PLAY_SECONDS` (900), and
ordered. Previously `[1e309, 1e309]` was accepted and left `time_remaining` as
NaN after resolution. New parametrized cases cover `[1e309, 1e309]`,
`[5, 1e309]`, `[-1e309, 15]`, `[NaN, 15]`, an unconvertible oversized float and
an oversized JSON integer; each asserts the message names the finite/range
requirement.

Wrong-side statistics in the parity tests (P3): `_applied_state` now reads both
teams' statistics explicitly instead of `state.offense_stats`, which belongs to
the receiving team after a turnover. A mutation check confirms the old helper
reported parity while the throwing team's interception/turnover counts differed;
the new helper catches it.

Legacy timing (architectural): the per-play ranges now live in
`PLAY_SECONDS_BY_TYPE`, immediate Hail Mary timing and the deferred Hail Mary
both read it, and a restored save without `play_seconds_range` derives its
default from the saved `play_type` via `_default_play_seconds_range`. A legacy
Hail Mary save therefore resolves with Hail Mary timing rather than retaining
the old 25-45 second defect; a legacy direct-play save still uses 25-45.

Tests written first: the six new save-timing/validation cases failed against
the prior implementation (`None`/scrimmage timing and accepted infinity) before
the production change. Focused suites (`test_end_zone_interception_decision.py`,
`test_end_zone_interception_returns.py`, `test_defensive_timeout_flow.py`,
`test_resume_pending_end_zone_flow.py`, `test_hail_mary.py`, `test_save_game.py`,
`test_game.py`): 287 passed; tracker/documentation: 455 passed; Ruff passed. The
new helper and derivation lines report full coverage. Full regression and browser
E2E were not run for this follow-up.

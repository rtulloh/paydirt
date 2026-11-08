---
id: STAT-004
title: Standings game numbers target the wrong record after out-of-order weeks
status: closed
priority: High
created-at: 2026-10-30
resolved-at: 2026-11-08
closed-at: 2026-11-08
tags:
  - reproduced
---

## Current audit — 2026-11-08

Retain High. Fresh synthetic in-memory review reproduces the mismatch: display_games sorts week 1 ahead of an earlier-inserted week 2 record, while edit/delete still index season.games in insertion order. This can change or delete the wrong saved result. Existing standings tests passing does not cover or resolve this defect. No user standings were read or changed.

The original investigation and checkpoints below are retained as history.

## Description

`paydirt/standings.py:display_games` groups and sorts by week, then assigns
sequential display numbers. `main` edits or deletes `season.games[number - 1]`
in insertion order. In a temporary synthetic season, add Bills-Jets in week 2
followed by Bears-Lions in week 1. `games` displays Bears-Lions as game 1;
`edit 2026 1 --home-score 31` instead changes the Bills-Jets score. `delete`
has the same index mismatch (its confirmation does show the different game).
Editing a week can also reorder the display. The player guide tells users to
use the numbers from `games` for these commands.

## Resolution / verification

Use a consistent record identifier or mapping for display, edit and delete.
Add temporary-directory CLI regressions for out-of-order and equal-week games,
week edits, deletion confirmation, and an already ordered control. Verify that
the selected record alone changes and no existing standings are used.

## Comments

--- 2026-10-30 15:09 ---
Reproduced the incorrect edit against a temporary standings directory; no user
standings were read or modified.

--- 2026-11-08 17:08 ---
Retain High. Fresh synthetic in-memory review reproduces the mismatch: display_games sorts week 1 ahead of an earlier-inserted week 2 record, while edit/delete still index season.games in insertion order. This can change or delete the wrong saved result. Existing standings tests passing does not cover or resolve this defect. No user standings were read or changed.

Reviewed current committed implementation and existing issue evidence. Fresh
focused validation: 239 gameplay/ownership/source/runner/standings checks and
417 parser/reconciliation/generation/source-bundle checks pass, without skips
or warnings. These focused checks are not full regression or new season runs.
See [high-priority audit](../../high-priority-issue-audit-2026-11-08.md).


--- 2026-11-08 17:18 ---
Test-first fix maps the displayed stable week order back to the persisted record index for both edit and delete. Two wrong-record regressions failed before the fix while two ordered controls passed. Eight synthetic temporary-directory CLI regressions now pass, including week reordering, equal weeks, cancelled deletion and invalid numbers; all 37 standings checks pass. No existing expectation changed or user standings touched. Actual `codex review` found no actionable bug in the fix. Resolved pending independent command-level acceptance and integrated release validation; closure is not claimed from unit tests alone.


--- 2026-11-08 17:21 ---
Independent temporary-directory command acceptance listed out-of-order weeks, edited displayed game 1, listed again, deleted displayed game 1 and verified the untouched Bills result remained. Eight selection regressions and 37 total standings tests pass. Actual Codex review found no actionable defect. Closed from issue-specific command/API acceptance in addition to test-first regressions; this does not assert full release qualification. No user saved data was changed.

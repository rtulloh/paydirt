# Issue Files

**Developer-only working record, not a player guide or a release promise.**

One file per issue: `<PREFIX>/<ID>.md`, for example [`RULE/RULE-013.md`](RULE/RULE-013.md).
The status view lives in the generated [issue index](../issue-tracker.md). See the
[developer-note disclaimer](../README.md).

## File format

```markdown
---
id: RULE-013                 # must equal the file name
title: One line, <= 120 characters
status: open                 # open | resolved | closed
priority: High               # High | Medium | Low
created-at: 2026-10-19       # the day the issue was first recorded
resolved-at:                 # the day a tested fix was committed
closed-at:                   # the day a play-test audit confirmed it
tags:                        # optional: deferred, investigating, monitoring, re-scoped, …
  - investigating
links:                       # optional: other issue IDs (links must be mutual)
  - RULE-014
commits:                     # optional: short hashes carrying the fix
  - 9be5487
---

## Description

What is wrong, with the evidence that established it.

## Resolution / verification

The plan while open; the fix, tests, and every changed prior expectation once resolved.

## Comments

--- 2026-10-20 12:00 ---
Newest material goes at the end under a timestamped separator.
```

`tests/test_issue_tracker.py` enforces the format, the date rules, mutual links, and that
the committed index matches the files. Regenerate the index after any change:

```bash
python3 scripts/build_issue_index.py
```

## Status model

- **open** — confirmed work remains, or an observation whose cause is not yet established
  (use the `investigating`, `deferred` or `monitoring` tag for those nuances).
- **resolved** — a fix is committed with tests and the verification is recorded. Set
  `resolved-at`. Resolved is **not** the end state: the fix is still awaiting play-test
  confirmation.
- **closed** — a play-test audit confirmed the issue no longer occurs. Set `closed-at`.
  An issue closed without a fix (re-scoped, duplicate, won't fix) records why in its
  Resolution section and carries the matching tag.

## Priorities

- **High:** incorrect gameplay or an announcement falsely claiming a possession change.
- **Medium:** materially poor coaching decisions, missing audit evidence, or regression-validation blockers.
- **Low:** wording, formatting, or exploratory work without a demonstrated gameplay defect.

## Working rules

- Add failing synthetic/public-2026 regressions before behavior changes. Never weaken tests
  or infer missing dice.
- Keep resolved and closed issues. Add a comment when work ships or an issue reopens
  (reopening clears `resolved-at`/`closed-at` and records why).
- Private logs and historical charts stay local and ignored. Do not attach or reproduce them here.
- Keep detailed designs in their linked notes rather than maintaining duplicate specifications.

## Current work order (High items first)

1. [FLOW-004](FLOW/FLOW-004.md) — frontend pending-PAT fallback crash; include a Vitest case
   that a pending-penalty response for a goal-line play routes to the penalty UI.
2. [VAL-002](VAL/VAL-002.md) and [VAL-003](VAL/VAL-003.md) — CI enforcement and the untracked
   private standings file.
3. [AI-015](AI/AI-015.md) — CPU must take the better KEEP option on a kicking-team punt foul;
   confirmed by the 2026-10-20 NYJ/CLE play test.
4. [AUD-020](AUD/AUD-020.md) — punt-penalty menu play-result preview is misleading; same play test.
5. [TRACE-004](TRACE/TRACE-004.md) — completed punt-penalty trace drops the return roll; same play test.
6. [RULE-011](RULE/RULE-011.md) and [RULE-012](RULE/RULE-012.md) — era kickoff spot and the
   era-dependent final-try rule, both as season configuration.
7. [RULE-003](RULE/RULE-003.md) (re-scoped Medium); then remaining Medium items by area, including
   [RULE-001](RULE/RULE-001.md) and [STAT-003](STAT/STAT-003.md) when two-point conversion support
   becomes a priority, and [FLOW-009](FLOW/FLOW-009.md) if a human ever needs the non-kickoff return-fumble prompt.

Play-testing closes issues: see [AI play-testing](../ai-playtesting.md) and the
[validation record](../game-audit-validation.md). Everything in the **resolved** section of
the index is a candidate for the next play-test audit.

## Context for the older findings

- The 2026-10-19 full code review covered every production change since `f7bab92` plus the
  worktree. **Reproduced** meant a real-engine or API reproduction was executed; **code-read**
  meant established by reading code only and still requiring a failing regression first; those
  distinctions are now tags. Recurring causes it identified: the conversion path reuses the
  live-play engine; parallel implementations drift (`run_play`/`_apply_play_result`,
  `run_interactive_game`/`resume_game`, CLI versus web flow); and tests mock the exact
  boundary where the defect lives. `auto_game` already had the correct half-ending and
  final-try behavior, so season/audit runs could not catch the CLI/web variants.
- An earlier local full-game audit reconciled score, quarter totals, first downs, scrimmage
  yardage, turnovers, sacks, and penalty totals; its apparent penalty discrepancy was explained
  by a recorded punt-return foul. A later audit found a **different**, confirmed punt
  double-foul accounting defect ([STAT-001](STAT/STAT-001.md)); do not conflate them.
- Die-roll and replay work: [replayable game logs](../replayable-game-logs.md). Actual captured
  rolls are authoritative; never reconstruct a missing roll from its result.

---
id: RULE-013
title: A penalty on the kickoff-return chart was enforced automatically with no reroll trace and no fumble handling…
status: closed
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-20
closed-at: 2026-10-20
links:
  - AI-016
commits:
  - d1a9cd6
  - 9be5487
---

## Description

A penalty on the kickoff-return chart was enforced automatically with no reroll trace and no fumble handling (`RT:23→"OFF 15" … → NYJ 8` in the 2026-10-19 Jets–Browns log); the web never surfaced kickoff penalty decisions at all. **Rule clarification 2026-10-20:** return penalties are *assessed automatically* against the end of the return — there is no accept/decline — so the choice mechanism added in `d1a9cd6` was wrong and has been removed.

## Resolution / verification

The corrected model (one resolver for every return chart) is in `_resolve_return_chain` / `_apply_return_chain`: OFF = returning team's foul, walked back from the end of the return (a return TD is wiped out and the ball placed that many yards short of the goal line); DEF = other team's foul, added forward (half the distance to the goal, never a penalty touchdown, never takes a TD away); same-type rerolls keep the larger foul; offsetting fouls nullify the play (kick re-kicked, otherwise the down is replayed from the previous spot, ten seconds). Kept from `d1a9cd6`: end-zone return fouls counted, no penalty "touchdown", stats to the fouling team, kick/return trace, the web kickoff endpoint surfaces pending decisions and saves the outcome, the panel uses engine previews. Changed prior expectations: the 24 engine/CLI, 5 API and 2 Vitest "choice" cases from `d1a9cd6` were rewritten as automatic-assessment cases (`tests/test_kickoff_return_penalties.py`, `tests/test_kickoff_return_penalty_cli.py`, `backend/tests/test_kickoff_penalty_api.py`); the four `tests/test_kickoff_return.py` cases and one `tests/test_kickoff_return_roll.py` case that had been changed to assert the pending choice now assert the automatic spot (their original values). The kick-chart choice (a genuine re-kick decision) is unchanged and keeps its inverted `offended_team` convention (AI-016).

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved (`d1a9cd6`, corrected in `9be5487`)).

--- 2026-10-20 14:00 ---
Play-test confirmation: opening CLE '83 kickoff to NYJ '83 returned `OFF 15` on `RT:23`, rerolled to `RT reroll:16→"46"`, and automatically assessed it. The trace showed both kickoff and return rolls; NYJ retained possession at NYJ 32 with no accept/decline prompt. RULE-013 is closed.

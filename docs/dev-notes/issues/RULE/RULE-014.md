---
id: RULE-014
title: A fumble cell on the kickoff return was never resolved
status: resolved
priority: High
created-at: 2026-10-19
resolved-at: 2026-10-20
closed-at:
links:
  - FLOW-009
  - RULE-010
  - RULE-018
commits:
  - 9be5487
---

## Description

A fumble cell on the kickoff return was never resolved: the penalty reroll loop skipped non-numeric cells (`RT reroll:13→"F + 17"` discarded in the 2026-10-19 log) and an ordinary return treated a fumble cell as plain yardage, so kickoff returns could never be fumbled away.

## Resolution / verification

Return fumbles are resolved with the returning team's recovery roll (its `fumble_recovered_range`); 17–19 (kept) and 37–39 (lost) give the recovering team a fumble return on its interception-return chart, recursively (depth-limited), so KR→FR→FR chains resolve. A penalty whose segment ended in a lost fumble stays live: assessed from the end of the play when the fouling team ends with the ball; after a returner's OFF foul the recovering team chooses (kickoffs prompt, phase `return_fumble`; the CPU keeps the recovery; interception/fumble/blocked-kick returns apply the recovering team's natural choice automatically — see FLOW-009); after the other team's DEF foul the offended returner always takes the penalty and keeps the ball ("clean hands": earlier changes of possession are never reopened). Stats: fumbles_lost/turnovers per lost fumble, penalties to the fouling team. Trace: `R:n→"recovered|lost"`, `FR:n→"cell"`. Tests: `tests/test_kickoff_return_penalties.py` (TestReturnFumbles), `tests/test_return_chains.py` (the full permutation matrix incl. DEF-then-fumble both ways, FR with OFF/DEF/TD/offsetting, KR,FR,FR back to the returner), CLI and API cases for the kicking team's choice.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Resolved (`9be5487`)).

--- 2026-10-20 16:00 ---
Play-test confirmation — ordinary recovered kickoff-return fumble: CLE '83 kicked 57 yards; NYJ '83 returned with `RT:14→"F + 26"`; recovery roll `R:15→"recovered"`. NYJ retained possession at NYJ 34 and continued at 1st & 10, with no turnover or incorrect touchdown. This confirms the initial KR → fumble → returning-team recovery path. RULE-014 remains resolved/awaiting closure pending a play-test of a lost return fumble or a fumble reached through a penalty reroll.

--- 2026-10-20 17:00 ---
Latest Week 6 audit adds a penalty-reroll fumble: the NYG '83/PHI '83 game reached `OFF 10` on a penalty reroll, then `F + 8`, followed by `R:35→"lost"`. NYG recovered the ball at NYG 49 and continued at 1st & 10. This confirms the penalty-reroll fumble path. RULE-014 remains resolved/awaiting closure because no chained fumble return (recovery roll 37–39) or explicit kicking-team recovery choice occurred.

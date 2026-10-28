# Developer Issue Tracker

**Developer-only working record, not a player guide or a release promise.**

*Generated from [`issues/`](issues/README.md) by `python3 scripts/build_issue_index.py`; do not edit by hand.*
Open an issue's own file for its description, verification and comments.
See the [conventions and work order](issues/README.md) and the
[developer-note disclaimer](README.md).

94 issues: 48 open, 37 resolved, 9 closed.

## Open (48)

Confirmed work remains, or an observation whose cause is not yet established.

| ID | Priority | Title | Dates | Links |
|----|----------|-------|-------|-------|
| [AI-002](issues/AI/AI-002.md) | Medium | On an incomplete first-down pass, CPU declines a 15-yard offensive penalty | created 2026-10-18 | AI-003, AI-018 |
| [AI-003](issues/AI/AI-003.md) | Medium | Evaluate whether Hard uses weaker-team strengths, varies calls, and makes sensible situation-dependent choices | created 2026-10-18 | AI-001, AI-002, AI-006 |
| [AI-012](issues/AI/AI-012.md) | Medium | Third-and-long competitive window may admit a weakly scored run despite much stronger alternatives | created 2026-10-18 | AI-010 |
| [AI-013](issues/AI/AI-013.md) | Medium | Fourth-and-one midfield choice ignores a large late lead | created 2026-10-19 | — |
| [AI-015](issues/AI/AI-015.md) | Medium | CPU receiving team never takes "keep return + yards" on a kicking-team punt foul (always index 0 = decline) | created 2026-10-19 | AUD-020, TRACE-004 |
| [AI-016](issues/AI/AI-016.md) | Medium | CPU never acts on kickoff-chart penalties | created 2026-10-19 | AUD-020, RULE-013 |
| [AI-017](issues/AI/AI-017.md) | Medium | Defense accepts a made field goal instead of the offensive foul that would force a longer re-kick | created 2026-10-19 | — |
| [AI-018](issues/AI/AI-018.md) | Medium | Penalty valuation compares nominal yards and ignores half-the-distance and first-down equivalence (AI-001 family) | created 2026-10-19 | AI-001, AI-002 |
| [AI-019](issues/AI/AI-019.md) | Medium | Hard defense bypasses goal-line, red-zone, prevent, two-minute, and fourth-down policies and returns Standard… | created 2026-10-19 | — |
| [AI-020](issues/AI/AI-020.md) | Medium | Ordinary-down selection never sets no-huddle even when _needs_hurry_up is true (the special-situation branches do) | created 2026-10-19 | — |
| [AUD-014](issues/AUD/AUD-014.md) | Medium | Penalty-choice preview was reported to show penalty yardage instead of the retained play when the defense chart… | created 2026-10-19 | RULE-003 |
| [AUD-015](issues/AUD/AUD-015.md) | Medium | Web double FIRST DOWN (result_formatter still passes is_first_down while the frontend renders its own banner) | created 2026-10-19 | — |
| [AUD-016](issues/AUD/AUD-016.md) | Medium | Web play-log team labels and colouring assume the human is home (PlayingPhase.jsx offense/defense naming) | created 2026-10-19 | — |
| [AUD-017](issues/AUD/AUD-017.md) | Medium | Duplicate FIRST DOWN on offensive fumble recoveries | created 2026-10-19 | — |
| [AUD-018](issues/AUD/AUD-018.md) | Medium | CLI display parses description strings to decide output (first-down marker check, reroll-dice and touchback… | created 2026-10-19 | TRACE-007 |
| [AUD-020](issues/AUD/AUD-020.md) | Medium | Punt-penalty choice menu for the kicking team lists two decline options | created 2026-10-19 | AI-015, AI-016, TRACE-004 |
| [FLOW-006](issues/FLOW/FLOW-006.md) | Medium | Resume_game scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick) | created 2026-10-19 | — |
| [FLOW-007](issues/FLOW/FLOW-007.md) | Medium | Resume_game never passes the human/CPU spike modifier and prints no skipped-modifier messages | created 2026-10-19 | — |
| [FLOW-008](issues/FLOW/FLOW-008.md) | Medium | Web load_replay reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession | created 2026-10-19 | — |
| [FLOW-009](issues/FLOW/FLOW-009.md) | Medium | On interception, fumble-advance and blocked-kick returns the "other team recovers the reroll fumble while a… | created 2026-10-20 | RULE-014 |
| [RULE-001](issues/RULE/RULE-001.md) | Medium | Two-point tries run through run_play | created 2026-10-19 | RULE-002, RULE-007, STAT-003, AI-022 |
| [RULE-003](issues/RULE/RULE-003.md) | Medium | Originally reported as: when the defense chart shows DEF n and the offense rolled B, QT, BLACK, TD, F, or I n, the… | created 2026-10-19 | AUD-014, FLOW-003 |
| [RULE-004](issues/RULE/RULE-004.md) | Medium | Run_play and _apply_play_result disagree on the −5 designation (floor at 0 vs negative), sack distance… | created 2026-10-19 | — |
| [RULE-005](issues/RULE/RULE-005.md) | Medium | Apply_fg_penalty_decision extends the half for an accepted offensive foul (time_remaining <= 0.5 heuristic) but… | created 2026-10-19 | — |
| [RULE-006](issues/RULE/RULE-006.md) | Medium | Offensive T/S modifiers are dropped whenever a penalty decision intervenes | created 2026-10-19 | SPIKE-002 |
| [RULE-007](issues/RULE/RULE-007.md) | Medium | Uncommitted _log_score try attribution relies on scoring_plays[-1] being the TD | created 2026-10-19 | RULE-001 |
| [RULE-011](issues/RULE/RULE-011.md) | Medium | Kickoff spot is a constant 35 (kickoff(kickoff_spot=35), web KickoffRequest.kickoff_spot=35) and the touchback… | created 2026-10-19 | — |
| [RULE-012](issues/RULE/RULE-012.md) | Medium | The final-try rule is era-dependent and the engine currently applies the pre-2018 rule to every season | created 2026-10-19 | RULE-002 |
| [SPIKE-002](issues/SPIKE/SPIKE-002.md) | Medium | Offense 7S is processed before a defensive AT, so execution order blocks the agreed defensive-timeout priority | created 2026-10-18 | AI-005, RULE-006 |
| [STAT-001](issues/STAT/STAT-001.md) | Medium | Enforced 15-yard punt double-foul penalty moves the ball but is absent from penalty count/yardage stats | created 2026-10-19 | STAT-003 |
| [STAT-003](issues/STAT/STAT-003.md) | Medium | Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception… | created 2026-10-19 | RULE-001, STAT-001 |
| [TRACE-001](issues/TRACE/TRACE-001.md) | Medium | Secondary QB-time rolls/results are not visible consistently, especially QB-time fumbles and transaction-based… | created 2026-10-18 | TRACE-007 |
| [TRACE-003](issues/TRACE/TRACE-003.md) | Medium | Compact traces do not explicitly identify called modifiers and the winning clock procedure | created 2026-10-18 | — |
| [TRACE-004](issues/TRACE/TRACE-004.md) | Medium | Offsetting/double-foul procedures can omit initial rolls and rerolls, including previously observed empty… | created 2026-10-18 | TRACE-006, AI-015, AUD-020, RULE-019, RULE-020 |
| [TRACE-005](issues/TRACE/TRACE-005.md) | Medium | Full deterministic engine replay from logs is not implemented | created 2026-10-18 | TRACE-007 |
| [TRACE-007](issues/TRACE/TRACE-007.md) | Medium | The PlayTransaction/PlayEvent model (paydirt/play_events.py) does not deliver its stated purpose and is now a… | created 2026-10-19 | AUD-018, TRACE-001, TRACE-002, TRACE-005 |
| [VAL-001](issues/VAL/VAL-001.md) | Medium | Full-game browser regression lost its execution context during navigation | created 2026-10-18 | AUD-001 |
| [VAL-004](issues/VAL/VAL-004.md) | Medium | Local tag v1.9.0 points behind the pushed v1.8.1; git push --tags would build a stale 1.9.0 | created 2026-10-19 | — |
| [VAL-005](issues/VAL/VAL-005.md) | Medium | Corrupt offensive_call_history in a save aborts --load with a traceback instead of the "Failed to load" message | created 2026-10-19 | — |
| [VAL-006](issues/VAL/VAL-006.md) | Medium | CI matrix includes Python 3.9 while requires-python >= 3.10 and the audit harness uses 3.10 syntax | created 2026-10-19 | — |
| [VAL-007](issues/VAL/VAL-007.md) | Medium | Corrected offensive dice invalidated two seeded untimed-down reproduction requirements | created 2026-10-26 | — |
| [AI-007](issues/AI/AI-007.md) | Low | Base incomplete-pass durations appear long in some logs | created 2026-10-18 | — |
| [AI-021](issues/AI/AI-021.md) | Low | Mixed RNG sources (Medium early-down tilt, fourth-down OOB, coffin corner use global dice RNG) | created 2026-10-19 | AUD-021 |
| [AUD-019](issues/AUD/AUD-019.md) | Low | Defense-recovery fumble text prints raw internal positions | created 2026-10-19 | — |
| [AUD-021](issues/AUD/AUD-021.md) | Low | Kick/return presentation from the play-test log | created 2026-10-19 | AI-021, RULE-010 |
| [DOC-001](issues/DOC/DOC-001.md) | Low | Run_full_season.py comment attributes the changed historical seeds to narration RNG only (the CPU penalty change… | created 2026-10-19 | — |
| [RULE-008](issues/RULE/RULE-008.md) | Low | Spikes, kneels, and fourth-down offensive fumble recoveries that exhaust downs set turnover=True as well as… | created 2026-10-19 | — |
| [RULE-009](issues/RULE/RULE-009.md) | Low | In run_play, a +3 QB scramble with a −5 designation becomes −2 and is classified as a sack | created 2026-10-19 | — |


## Resolved (awaiting play-test confirmation) (37)

A fix is committed with tests. A play-test audit must confirm it before the issue is closed.

| ID | Priority | Title | Dates | Links |
|----|----------|-------|-------|-------|
| [AUD-001](issues/AUD/AUD-001.md) | High | Fourth-down offsetting penalties incorrectly announce turnover on downs despite replaying the down and retaining… | created 2026-10-18, resolved 2026-10-18 | VAL-001, AUD-011 |
| [FLOW-001](issues/FLOW/FLOW-001.md) | High | After a half-ending TD the CLI passed the current quarter to can_kickoff_after_play, so the scoring team kicked… | created 2026-10-19, resolved 2026-10-19 | RULE-002 |
| [FLOW-002](issues/FLOW/FLOW-002.md) | High | Both CLI loops free-kicked after a half-ending safety (burning Q3 clock and flipping possession), then kicked off… | created 2026-10-19, resolved 2026-10-19 | — |
| [FLOW-003](issues/FLOW/FLOW-003.md) | High | Web execute_play called setup_for_pat() and set pending_pat from result.touchdown without checking… | created 2026-10-19, resolved 2026-10-19 | RULE-003 |
| [FLOW-004](issues/FLOW/FLOW-004.md) | High | CheckPendingPat fallback references the deleted isHomeScoring | created 2026-10-19, resolved 2026-10-20 | — |
| [RULE-002](issues/RULE/RULE-002.md) | High | A TD at 0:00 of regulation that left the scores unequal set game_over before the try | created 2026-10-19, resolved 2026-10-19 | FLOW-001, RULE-001, FLOW-005, RULE-012 |
| [RULE-014](issues/RULE/RULE-014.md) | High | A fumble cell on the kickoff return was never resolved | created 2026-10-19, resolved 2026-10-20 | FLOW-009, RULE-010, RULE-018, RULE-019 |
| [RULE-015](issues/RULE/RULE-015.md) | High | Recovery roll 39 on an ordinary fumble was an automatic defensive touchdown (R:39→"lost" | Ret:35→97 in the… | created 2026-10-20, resolved 2026-10-20 | — |
| [RULE-016](issues/RULE/RULE-016.md) | High | Penalty cells on the Int. Return chart were read as yardage | created 2026-10-20, resolved 2026-10-20 | — |
| [RULE-017](issues/RULE/RULE-017.md) | High | Own-recovery fumble advance resets the down to second regardless of the down before | created 2026-10-27, resolved 2026-10-27 | — |
| [RULE-018](issues/RULE/RULE-018.md) | High | Return-chain fumbles in or beyond an end zone are clamped to the 1 with no touchdown, touchback or safety | created 2026-10-27, resolved 2026-10-28 | RULE-014 |
| [RULE-019](issues/RULE/RULE-019.md) | High | Punt returns bypass the unified return resolver: penalty touchdowns, discarded TD/F rerolls, no recovery roll | created 2026-10-27, resolved 2026-10-28 | RULE-014, TRACE-004 |
| [RULE-020](issues/RULE/RULE-020.md) | High | Kickoff with kick-chart and return-chart fouls by the same team is treated as offsetting with no re-kick | created 2026-10-27, resolved 2026-10-28 | TRACE-004 |
| [SPIKE-003](issues/SPIKE/SPIKE-003.md) | High | A completion could leave time, then its spike reduce the clock to zero without processing period/game expiration | created 2026-10-18, resolved 2026-10-18 | SPIKE-001 |
| [VAL-002](issues/VAL/VAL-002.md) | High | CI never runs the backend pytest suite, Ruff is continue-on-error and omits the backend path, and the public AI… | created 2026-10-19, resolved 2026-10-27 | — |
| [AI-004](issues/AI/AI-004.md) | Medium | Chart analysis treated rows as equally likely | created 2026-10-17, resolved 2026-10-17 | — |
| [AI-005](issues/AI/AI-005.md) | Medium | Difficulty/coaching differentiation and timeout budget handling needed improvement | created 2026-10-17, resolved 2026-10-17 | SPIKE-002 |
| [AI-006](issues/AI/AI-006.md) | Medium | Late-game offense/defense and season-aware conversions needed better decisions | created 2026-10-17, resolved 2026-10-17 | AI-003 |
| [AI-008](issues/AI/AI-008.md) | Medium | Hard can become predictable by overconcentrating on any top chart recommendation | created 2026-10-18, resolved 2026-10-18 | — |
| [AI-010](issues/AI/AI-010.md) | Medium | Opponent learning treated punts/field goals as runs because a false pass flag overrode action classification | created 2026-10-18, resolved 2026-10-18 | AI-012 |
| [AI-011](issues/AI/AI-011.md) | Medium | A two-score Q4 deficit triggered a whole-quarter deep-pass-only hurry-up branch, bypassing down/distance and… | created 2026-10-18, resolved 2026-10-18 | — |
| [AI-022](issues/AI/AI-022.md) | Medium | CPU two-point try play is chosen by the ordinary policy on the stale post-touchdown state | created 2026-10-27, resolved 2026-10-28 | RULE-001 |
| [AUD-007](issues/AUD/AUD-007.md) | Medium | Rendering colorful commentary advances the same global random stream as dice/coaching | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-008](issues/AUD/AUD-008.md) | Medium | Full interception-TD output can name the original offense as scorer because the engine omits result scoring-team… | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-009](issues/AUD/AUD-009.md) | Medium | QB-time rushing touchdown is described as a completed pass to a receiver | created 2026-10-19, resolved 2026-10-19 | — |
| [DATA-001](issues/DATA/DATA-001.md) | Medium | Seasons/1983/Cardinals/special.csv Int | created 2026-10-20, resolved 2026-10-20 | — |
| [STAT-002](issues/STAT/STAT-002.md) | Medium | Successful PAT is allocated to the live next quarter instead of the touchdown quarter | created 2026-10-19, resolved 2026-10-19 | — |
| [TRACE-006](issues/TRACE/TRACE-006.md) | Medium | Compact punt-return penalty output lacked its reroll and enforcement details | created 2026-10-17, resolved 2026-10-17 | TRACE-004 |
| [AUD-002](issues/AUD/AUD-002.md) | Low | Non-touchdown breakaway commentary claims nobody will catch the runner | created 2026-10-18, resolved 2026-10-19 | — |
| [AUD-003](issues/AUD/AUD-003.md) | Low | QB-kneel commentary credits a running back and describes an ordinary tackled loss | created 2026-10-18, resolved 2026-10-19 | — |
| [AUD-004](issues/AUD/AUD-004.md) | Low | Goal-to-go headers repeat the position separator, such as a goal-distance marker followed by a second @ | created 2026-10-18, resolved 2026-10-19 | — |
| [AUD-005](issues/AUD/AUD-005.md) | Low | Offensive fumble-advance commentary exposes internal positions, conflates recovery/advance rolls and chart/actual… | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-006](issues/AUD/AUD-006.md) | Low | CLI repeats touchdowns/first downs, made field goals, defensive fumble scores, safeties, and fourth-down kneel… | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-010](issues/AUD/AUD-010.md) | Low | Ordinary offensive fumble recovery describes pre-fumble gain as an extra post-recovery advance | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-011](issues/AUD/AUD-011.md) | Low | Complete new/resumed CLI loops repeat the actual turnover-on-downs announcement | created 2026-10-19, resolved 2026-10-19 | AUD-001 |
| [AUD-012](issues/AUD/AUD-012.md) | Low | Pass interference repeats the achieved first-down wording | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-013](issues/AUD/AUD-013.md) | Low | Incomplete result/menu labels say No gain, obscuring the actual pass result | created 2026-10-19, resolved 2026-10-19 | — |


## Closed (9)

A play-test audit confirmed the issue no longer occurs.

| ID | Priority | Title | Dates | Links |
|----|----------|-------|-------|-------|
| [AI-014](issues/AI/AI-014.md) | High | CPU preserves an opponent touchdown instead of accepting an eligible offensive foul that erases it | created 2026-10-19, resolved 2026-10-19, closed 2026-10-20 | — |
| [RULE-010](issues/RULE/RULE-010.md) | High | Kickoffs resolved the kick distance and the return from **one** dice roll | created 2026-10-19, resolved 2026-10-19, closed 2026-10-20 | AUD-021, FLOW-005, RULE-014 |
| [RULE-013](issues/RULE/RULE-013.md) | High | A penalty on the kickoff-return chart was enforced automatically with no reroll trace and no fumble handling… | created 2026-10-19, resolved 2026-10-20, closed 2026-10-20 | AI-016 |
| [SPIKE-001](issues/SPIKE/SPIKE-001.md) | High | The S modifier adjusts time without charging the agreed additional down | created 2026-10-18, resolved 2026-10-28, closed 2026-10-28 | SPIKE-003 |
| [VAL-003](issues/VAL/VAL-003.md) | High | Standings_data.save/season_1983.json is untracked and not ignored and contains private-season results | created 2026-10-19, resolved 2026-10-27, closed 2026-10-27 | — |
| [AI-001](issues/AI/AI-001.md) | Medium | CPU accepts a five-yard automatic-first-down penalty instead of an eleven-yard gain that also earns a first down | created 2026-10-18, resolved 2026-10-28, closed 2026-10-28 | AI-003, AI-018 |
| [AI-009](issues/AI/AI-009.md) | Medium | Existing balanced auto/season checks do not exercise Hard-vs-Hard or expose structured play-balance evidence | created 2026-10-18, resolved 2026-10-18, closed 2026-10-26 | — |
| [FLOW-005](issues/FLOW/FLOW-005.md) | Medium | Second-half kicker was guessed from current possession in resume_game ("Approximate") and in the web kickoff… | created 2026-10-19, resolved 2026-10-19, closed 2026-10-20 | RULE-002, RULE-010 |
| [TRACE-002](issues/TRACE/TRACE-002.md) | Low | Fumble traces show unknown defensive rows and placeholder-looking zero return rolls | created 2026-10-18, resolved 2026-10-20, closed 2026-10-20 | TRACE-007 |

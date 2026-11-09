# Developer Issue Tracker

**Developer-only working record, not a player guide or a release promise.**

*Generated from [`issues/`](issues/README.md) by `python3 scripts/build_issue_index.py`; do not edit by hand.*
Open an issue's own file for its description, verification and comments.
See the [conventions and work order](issues/README.md) and the
[developer-note disclaimer](README.md).

203 issues: 73 open, 57 resolved, 73 closed.

## Open (73)

Confirmed work remains, or an observation whose cause is not yet established.

| ID | Priority | Title | Dates | Links |
|----|----------|-------|-------|-------|
| [AI-002](issues/AI/AI-002.md) | Medium | On an incomplete first-down pass, CPU declines a 15-yard offensive penalty | created 2026-10-18 | AI-003, AI-018 |
| [AI-003](issues/AI/AI-003.md) | Medium | Evaluate whether Hard uses weaker-team strengths, varies calls, and makes sensible situation-dependent choices | created 2026-10-18 | AI-001, AI-002, AI-006, AI-028, AI-029 |
| [AI-012](issues/AI/AI-012.md) | Medium | Third-and-long competitive window may admit a weakly scored run despite much stronger alternatives | created 2026-10-18 | AI-010 |
| [AI-013](issues/AI/AI-013.md) | Medium | Fourth-and-one midfield choice ignores a large late lead | created 2026-10-19 | — |
| [AI-016](issues/AI/AI-016.md) | Medium | CPU never acts on kickoff-chart penalties | created 2026-10-19 | AUD-020, RULE-013 |
| [AI-017](issues/AI/AI-017.md) | Medium | Defense accepts a made field goal instead of the offensive foul that would force a longer re-kick | created 2026-10-19 | — |
| [AI-018](issues/AI/AI-018.md) | Medium | Penalty valuation compares nominal yards and ignores half-the-distance and first-down equivalence (AI-001 family) | created 2026-10-19 | AI-001, AI-002 |
| [AI-019](issues/AI/AI-019.md) | Medium | Hard defense bypasses situational policies and can repeat one model formation on every late down | created 2026-10-19 | AI-025, AI-026, AI-023, DATA-012 |
| [AI-020](issues/AI/AI-020.md) | Medium | Ordinary-down selection never sets no-huddle even when _needs_hurry_up is true (the special-situation branches do) | created 2026-10-19 | — |
| [AI-023](issues/AI/AI-023.md) | Medium | select_defense uses the raw quarter so overtime never triggers prevent or two-minute defense | created 2026-10-27 | AI-019 |
| [AI-024](issues/AI/AI-024.md) | Medium | Fourth-down AI uses fixed 1983 field-goal ranges for every season | created 2026-11-01 | DATA-011 |
| [AI-029](issues/AI/AI-029.md) | Medium | Last-possession fourth-down call prioritizes conversion over remaining scoring distance and time | created 2026-11-06 | AI-003, AI-006 |
| [AI-030](issues/AI/AI-030.md) | Medium | Isolate chart calibration policy effects from Hard season outcomes | created 2026-11-07 | DATA-018, DATA-042 |
| [AUD-014](issues/AUD/AUD-014.md) | Medium | Penalty-choice preview was reported to show penalty yardage instead of the retained play when the defense chart… | created 2026-10-19 | RULE-003 |
| [AUD-015](issues/AUD/AUD-015.md) | Medium | Web double FIRST DOWN (result_formatter still passes is_first_down while the frontend renders its own banner) | created 2026-10-19 | — |
| [AUD-016](issues/AUD/AUD-016.md) | Medium | Web play-log team labels and colouring assume the human is home (PlayingPhase.jsx offense/defense naming) | created 2026-10-19 | — |
| [AUD-017](issues/AUD/AUD-017.md) | Medium | Duplicate FIRST DOWN on offensive fumble recoveries | created 2026-10-19 | — |
| [AUD-018](issues/AUD/AUD-018.md) | Medium | CLI display parses description strings to decide output (first-down marker check, reroll-dice and touchback… | created 2026-10-19 | TRACE-007 |
| [AUD-020](issues/AUD/AUD-020.md) | Medium | Punt-penalty choice menu for the kicking team lists two decline options | created 2026-10-19 | AI-015, AI-016, TRACE-004 |
| [AUD-022](issues/AUD/AUD-022.md) | Medium | Fourth-down own-recovery turnover on downs prints contradictory recovery labels and a fabricated lost roll | created 2026-10-27 | RULE-008 |
| [DATA-018](issues/DATA/DATA-018.md) | Medium | Promoted generated cohorts fail fresh current-engine accuracy gate | created 2026-11-05 | DATA-019, VAL-019, DATA-042, AI-030 |
| [DATA-030](issues/DATA/DATA-030.md) | Medium | Source credited fumble yardage and physical initial gain need separate definitions | created 2026-11-05 | DATA-035, DATA-036, DATA-038 |
| [DATA-036](issues/DATA/DATA-036.md) | Medium | Multiple fumbles on one source play collapse into one calibration event | created 2026-11-06 | DATA-030, DATA-035, DATA-038 |
| [DATA-040](issues/DATA/DATA-040.md) | Medium | Generated defenses repeat interception stripes and fixed depth patterns across formations and teams | created 2026-11-06 | DATA-022, DATA-039 |
| [DATA-041](issues/DATA/DATA-041.md) | Medium | Empirical variant allocation locks primary QT into low-weight rows that layout cannot disperse | created 2026-11-06 | DATA-039 |
| [DATA-042](issues/DATA/DATA-042.md) | Medium | Updated season simulations still inflate scoring and offensive play counts | created 2026-11-07 | DATA-018, AI-030 |
| [DATA-046](issues/DATA/DATA-046.md) | Medium | 1977 candidate misses Washington interception fit and overstates scoring | created 2026-11-08 | — |
| [FLOW-006](issues/FLOW/FLOW-006.md) | Medium | Resume_game scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick) | created 2026-10-19 | — |
| [FLOW-007](issues/FLOW/FLOW-007.md) | Medium | Resume_game never passes the human/CPU spike modifier and prints no skipped-modifier messages | created 2026-10-19 | — |
| [FLOW-008](issues/FLOW/FLOW-008.md) | Medium | Web load_replay reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession | created 2026-10-19 | — |
| [FLOW-009](issues/FLOW/FLOW-009.md) | Medium | On interception, fumble-advance and blocked-kick returns the "other team recovers the reroll fumble while a… | created 2026-10-20 | RULE-014 |
| [FLOW-021](issues/FLOW/FLOW-021.md) | Medium | Web UI cannot record completed games to season standings or show season progress | created 2026-11-08 | FLOW-022 |
| [RULE-003](issues/RULE/RULE-003.md) | Medium | Originally reported as: when the defense chart shows DEF n and the offense rolled B, QT, BLACK, TD, F, or I n, the… | created 2026-10-19 | AUD-014, FLOW-003 |
| [RULE-004](issues/RULE/RULE-004.md) | Medium | Run_play and _apply_play_result disagree on the −5 designation (floor at 0 vs negative), sack distance… | created 2026-10-19 | — |
| [RULE-005](issues/RULE/RULE-005.md) | Medium | Apply_fg_penalty_decision extends the half for an accepted offensive foul (time_remaining <= 0.5 heuristic) but… | created 2026-10-19 | — |
| [RULE-006](issues/RULE/RULE-006.md) | Medium | Offensive T/S modifiers are dropped whenever a penalty decision intervenes | created 2026-10-19 | SPIKE-002 |
| [RULE-011](issues/RULE/RULE-011.md) | Medium | Kickoff spot is a constant 35 (kickoff(kickoff_spot=35), web KickoffRequest.kickoff_spot=35) and the touchback… | created 2026-10-19 | — |
| [RULE-012](issues/RULE/RULE-012.md) | Medium | The final-try rule is era-dependent and the engine currently applies the pre-2018 rule to every season | created 2026-10-19 | RULE-002 |
| [RULE-027](issues/RULE/RULE-027.md) | Medium | Review legacy punt double-foul enforcement and ambiguous penalty classification | created 2026-11-06 | DATA-033, DATA-034, RULE-028 |
| [STAT-001](issues/STAT/STAT-001.md) | Medium | Enforced 15-yard punt double-foul penalty moves the ball but is absent from penalty count/yardage stats | created 2026-10-19 | STAT-003 |
| [TRACE-001](issues/TRACE/TRACE-001.md) | Medium | Secondary QB-time rolls/results are not visible consistently, especially QB-time fumbles and transaction-based… | created 2026-10-18 | TRACE-007 |
| [TRACE-003](issues/TRACE/TRACE-003.md) | Medium | Compact traces do not explicitly identify called modifiers and the winning clock procedure | created 2026-10-18 | — |
| [TRACE-004](issues/TRACE/TRACE-004.md) | Medium | Offsetting/double-foul procedures can omit initial rolls and rerolls, including previously observed empty… | created 2026-10-18 | TRACE-006, AI-015, AUD-020, RULE-019, RULE-020 |
| [TRACE-005](issues/TRACE/TRACE-005.md) | Medium | Full deterministic engine replay from logs is not implemented | created 2026-10-18 | TRACE-007 |
| [TRACE-007](issues/TRACE/TRACE-007.md) | Medium | The PlayTransaction/PlayEvent model (paydirt/play_events.py) does not deliver its stated purpose and is now a… | created 2026-10-19 | AUD-018, TRACE-001, TRACE-002, TRACE-005 |
| [VAL-001](issues/VAL/VAL-001.md) | Medium | Full-game browser regression lost its execution context during navigation | created 2026-10-18 | AUD-001 |
| [VAL-004](issues/VAL/VAL-004.md) | Medium | Local tag v1.9.0 points behind the pushed v1.8.1; git push --tags would build a stale 1.9.0 | created 2026-10-19 | — |
| [VAL-005](issues/VAL/VAL-005.md) | Medium | Corrupt offensive_call_history in a save aborts --load with a traceback instead of the "Failed to load" message | created 2026-10-19 | VAL-008 |
| [VAL-013](issues/VAL/VAL-013.md) | Medium | Web tests exercise duplicate or unmounted paths instead of live behavior | created 2026-10-30 | — |
| [VAL-019](issues/VAL/VAL-019.md) | Medium | Historical season runner implemented; official qualification verification remains | created 2026-11-06 | DATA-018, AI-025, AI-026 |
| [VAL-020](issues/VAL/VAL-020.md) | Medium | Core coverage suite takes nearly an hour after chart regression expansion | created 2026-11-07 | — |
| [AI-021](issues/AI/AI-021.md) | Low | Mixed RNG sources (Medium early-down tilt, fourth-down OOB, coffin corner use global dice RNG) | created 2026-10-19 | AUD-021 |
| [AI-026](issues/AI/AI-026.md) | Low | Hard ordinary selection ignores own defensive and opponent chart strengths | created 2026-11-06 | AI-019, AI-025, VAL-019 |
| [AUD-019](issues/AUD/AUD-019.md) | Low | Defense-recovery fumble text prints raw internal positions | created 2026-10-19 | — |
| [AUD-021](issues/AUD/AUD-021.md) | Low | Kick/return presentation from the play-test log | created 2026-10-19 | AI-021, RULE-010 |
| [AUD-023](issues/AUD/AUD-023.md) | Low | CSV fallback team metadata repeats the nickname in the matchup banner | created 2026-10-28 | — |
| [AUD-024](issues/AUD/AUD-024.md) | Low | Postgame tendency summary labels distance bands as exact down-and-distance situations | created 2026-10-28 | — |
| [DATA-002](issues/DATA/DATA-002.md) | Low | Local 1983 Chiefs commentary roster includes Joe Delaney despite his death before the season | created 2026-10-28 | — |
| [DATA-003](issues/DATA/DATA-003.md) | Low | Add a PDF import backend for Paydirt charts | created 2026-10-30 | — |
| [DATA-015](issues/DATA/DATA-015.md) | Low | Assess whether sparse symbolic passing touchdowns improve calibrated generated charts | created 2026-11-02 | DATA-011 |
| [DATA-038](issues/DATA/DATA-038.md) | Low | Aborted field-goal labels omit snap fumbles and distinct statistical actors | created 2026-11-06 | DATA-030, DATA-036 |
| [DATA-039](issues/DATA/DATA-039.md) | Low | Primary chart dispersion scores BLACK only and leaves other reducible result clusters | created 2026-11-06 | DATA-040, DATA-041 |
| [DATA-044](issues/DATA/DATA-044.md) | Low | 1983 Buccaneers commentary roster incorrectly includes Doug Williams | created 2026-11-08 | — |
| [DATA-045](issues/DATA/DATA-045.md) | Low | Evaluate pre-1977 historical seasons with incomplete play-by-play, starting with 1972 | created 2026-11-08 | — |
| [DOC-001](issues/DOC/DOC-001.md) | Low | Run_full_season.py comment attributes the changed historical seeds to narration RNG only (the CPU penalty change… | created 2026-10-19 | — |
| [FLOW-020](issues/FLOW/FLOW-020.md) | Low | Allow web players to select opposing teams from different seasons | created 2026-11-07 | — |
| [FLOW-022](issues/FLOW/FLOW-022.md) | Low | Web UI cannot start and watch an AI-versus-AI game | created 2026-11-08 | FLOW-021 |
| [RULE-008](issues/RULE/RULE-008.md) | Low | Spikes, kneels, and fourth-down offensive fumble recoveries that exhaust downs set turnover=True as well as… | created 2026-10-19 | AUD-022 |
| [RULE-009](issues/RULE/RULE-009.md) | Low | In run_play, a +3 QB scramble with a −5 designation becomes −2 and is classified as a sack | created 2026-10-19 | — |
| [STAT-006](issues/STAT/STAT-006.md) | Low | Track cumulative team statistics and performance throughout a season | created 2026-11-07 | — |
| [TRACE-008](issues/TRACE/TRACE-008.md) | Low | End-line fumble depth roll is dropped from the description when the defense recovers | created 2026-10-27 | — |
| [VAL-008](issues/VAL/VAL-008.md) | Low | CLI argv dispatch rejects the advertised -l flag, ignores -A/-H ordering and skips validation on --load | created 2026-10-27 | VAL-005 |
| [VAL-011](issues/VAL/VAL-011.md) | Low | Documented frontend lint command has no npm script | created 2026-10-30 | — |


## Resolved (awaiting play-test confirmation) (57)

A fix is committed with tests. A play-test audit must confirm it before the issue is closed.

| ID | Priority | Title | Dates | Links |
|----|----------|-------|-------|-------|
| [AUD-001](issues/AUD/AUD-001.md) | High | Fourth-down offsetting penalties incorrectly announce turnover on downs despite replaying the down and retaining… | created 2026-10-18, resolved 2026-10-18 | VAL-001, AUD-011 |
| [AUD-025](issues/AUD/AUD-025.md) | High | Punt fumble commentary mixes initial return yards with the final chain spot and guesses who recovered | created 2026-11-02, resolved 2026-11-02 | RULE-019, AUD-006 |
| [AUD-030](issues/AUD/AUD-030.md) | High | Engine report validator trusts unverified derived score pace and special rates | created 2026-11-06, resolved 2026-11-07 | — |
| [DATA-011](issues/DATA/DATA-011.md) | High | Chart generation needs a reproducible engine tuning tool | created 2026-11-01, resolved 2026-11-02 | DATA-015, DATA-009, DATA-010, AI-024, DATA-012, DATA-014 |
| [DATA-016](issues/DATA/DATA-016.md) | High | Sparse empirical event allocation can choose a worse physical probability | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-017](issues/DATA/DATA-017.md) | High | Source event-count corrections implemented; final qualification pending | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-022](issues/DATA/DATA-022.md) | High | Generated defense interception floor overwhelms low-risk quarterback inputs | created 2026-11-05, resolved 2026-11-07 | DATA-040 |
| [DATA-023](issues/DATA/DATA-023.md) | High | Primary pressure allocation ignores conditional QB Time sacks and defensive overlap | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-024](issues/DATA/DATA-024.md) | High | Two-point rushing attempts contaminate regular nflverse chart inputs | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-025](issues/DATA/DATA-025.md) | High | Opponent adjustment treats return and sack prose as primary passing gains | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-026](issues/DATA/DATA-026.md) | High | Opponent adjustment reduces outcome categories with chronological prefixes | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-027](issues/DATA/DATA-027.md) | High | Opponent yard adjustment changes QB Time sack and scramble classes | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-028](issues/DATA/DATA-028.md) | High | Unknown required source facts remain explicit; qualification pending | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-029](issues/DATA/DATA-029.md) | High | Zero-yard nonfumble sacks are represented as QT scrambles | created 2026-11-05, resolved 2026-11-07 | — |
| [DATA-031](issues/DATA/DATA-031.md) | High | Fumble return replay still credits nullified yardage and sacks | created 2026-11-05, resolved 2026-11-07 | DATA-020, VAL-018 |
| [DATA-032](issues/DATA/DATA-032.md) | High | Punt snap-fumble routing fixed; final closing review pending | created 2026-11-06, resolved 2026-11-07 | DATA-034 |
| [DATA-035](issues/DATA/DATA-035.md) | High | Interception-return ownership correction implemented; regeneration review pending | created 2026-11-06, resolved 2026-11-07 | DATA-030, DATA-036 |
| [FLOW-001](issues/FLOW/FLOW-001.md) | High | After a half-ending TD the CLI passed the current quarter to can_kickoff_after_play, so the scoring team kicked… | created 2026-10-19, resolved 2026-10-19 | RULE-002 |
| [FLOW-002](issues/FLOW/FLOW-002.md) | High | Both CLI loops free-kicked after a half-ending safety (burning Q3 clock and flipping possession), then kicked off… | created 2026-10-19, resolved 2026-10-19 | — |
| [FLOW-003](issues/FLOW/FLOW-003.md) | High | Web execute_play called setup_for_pat() and set pending_pat from result.touchdown without checking… | created 2026-10-19, resolved 2026-10-19 | RULE-003 |
| [FLOW-004](issues/FLOW/FLOW-004.md) | High | CheckPendingPat fallback references the deleted isHomeScoring | created 2026-10-19, resolved 2026-10-20 | — |
| [FLOW-010](issues/FLOW/FLOW-010.md) | High | Random-opponent API assigns the opponent as the player in away games | created 2026-10-30, resolved 2026-10-30 | — |
| [FLOW-011](issues/FLOW/FLOW-011.md) | High | Web conversion endpoints execute without a pending touchdown try | created 2026-10-30, resolved 2026-10-30 | — |
| [FLOW-016](issues/FLOW/FLOW-016.md) | High | Penalty dialog invents midfield and incorrect enforcement previews | created 2026-11-06, resolved 2026-11-07 | — |
| [RULE-002](issues/RULE/RULE-002.md) | High | A TD at 0:00 of regulation that left the scores unequal set game_over before the try | created 2026-10-19, resolved 2026-10-19 | FLOW-001, RULE-001, FLOW-005, RULE-012 |
| [RULE-014](issues/RULE/RULE-014.md) | High | A fumble cell on the kickoff return was never resolved | created 2026-10-19, resolved 2026-10-20 | FLOW-009, RULE-010, RULE-018, RULE-019 |
| [RULE-015](issues/RULE/RULE-015.md) | High | Recovery roll 39 on an ordinary fumble was an automatic defensive touchdown (R:39→"lost" | Ret:35→97 in the… | created 2026-10-20, resolved 2026-10-20 | — |
| [RULE-016](issues/RULE/RULE-016.md) | High | Penalty cells on the Int. Return chart were read as yardage | created 2026-10-20, resolved 2026-10-20 | — |
| [RULE-018](issues/RULE/RULE-018.md) | High | Return-chain fumbles in or beyond an end zone are clamped to the 1 with no touchdown, touchback or safety | created 2026-10-27, resolved 2026-10-28 | RULE-014 |
| [RULE-019](issues/RULE/RULE-019.md) | High | Punt returns bypass the unified return resolver: penalty touchdowns, discarded TD/F rerolls, no recovery roll | created 2026-10-27, resolved 2026-10-28 | RULE-014, TRACE-004, AUD-025 |
| [RULE-020](issues/RULE/RULE-020.md) | High | Kickoff with kick-chart and return-chart fouls by the same team is treated as offsetting with no re-kick | created 2026-10-27, resolved 2026-10-28 | TRACE-004 |
| [RULE-025](issues/RULE/RULE-025.md) | High | CLI discards a playable final second and prints FINAL before the engine ends the game | created 2026-11-02, resolved 2026-11-02 | — |
| [RULE-026](issues/RULE/RULE-026.md) | High | Selected offensive fumble priority is misclassified as defensive interception | created 2026-11-05, resolved 2026-11-07 | — |
| [RULE-029](issues/RULE/RULE-029.md) | High | Interception chart spots on or beyond the offense end line score touchdowns instead of safeties | created 2026-11-06, resolved 2026-11-07 | — |
| [RULE-030](issues/RULE/RULE-030.md) | High | Own-end-zone interceptions lack the permitted coaching return choice | created 2026-11-06, resolved 2026-11-07 | — |
| [SPIKE-003](issues/SPIKE/SPIKE-003.md) | High | A completion could leave time, then its spike reduce the clock to zero without processing period/game expiration | created 2026-10-18, resolved 2026-10-18 | SPIKE-001 |
| [VAL-002](issues/VAL/VAL-002.md) | High | CI never runs the backend pytest suite, Ruff is continue-on-error and omits the backend path, and the public AI… | created 2026-10-19, resolved 2026-10-27 | — |
| [VAL-017](issues/VAL/VAL-017.md) | High | Engine audit disk fingerprints do not identify replaced loaded observers | created 2026-11-05, resolved 2026-11-07 | — |
| [VAL-018](issues/VAL/VAL-018.md) | High | Engine report validation ignores policy and selected-call evidence | created 2026-11-05, resolved 2026-11-07 | DATA-031 |
| [AI-004](issues/AI/AI-004.md) | Medium | Chart analysis treated rows as equally likely | created 2026-10-17, resolved 2026-10-17 | — |
| [AI-005](issues/AI/AI-005.md) | Medium | Difficulty/coaching differentiation and timeout budget handling needed improvement | created 2026-10-17, resolved 2026-10-17 | SPIKE-002 |
| [AI-006](issues/AI/AI-006.md) | Medium | Late-game offense/defense and season-aware conversions needed better decisions | created 2026-10-17, resolved 2026-10-17 | AI-003, AI-028, AI-029 |
| [AI-008](issues/AI/AI-008.md) | Medium | Hard can become predictable by overconcentrating on any top chart recommendation | created 2026-10-18, resolved 2026-10-18 | — |
| [AI-015](issues/AI/AI-015.md) | Medium | CPU receiving team never takes "keep return + yards" on a kicking-team punt foul (always index 0 = decline) | created 2026-10-19, resolved 2026-11-07 | AUD-020, TRACE-004 |
| [AI-022](issues/AI/AI-022.md) | Medium | CPU two-point try play is chosen by the ordinary policy on the stale post-touchdown state | created 2026-10-27, resolved 2026-10-28 | RULE-001 |
| [AUD-007](issues/AUD/AUD-007.md) | Medium | Rendering colorful commentary advances the same global random stream as dice/coaching | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-008](issues/AUD/AUD-008.md) | Medium | Full interception-TD output can name the original offense as scorer because the engine omits result scoring-team… | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-028](issues/AUD/AUD-028.md) | Medium | Generated primary BLACK cells form unnecessary contiguous runs and blocks | created 2026-11-05, resolved 2026-11-07 | — |
| [AUD-029](issues/AUD/AUD-029.md) | Medium | Exact mechanics treats missing supplemental rows as zero instead of core fallback | created 2026-11-06, resolved 2026-11-07 | — |
| [DATA-001](issues/DATA/DATA-001.md) | Medium | Seasons/1983/Cardinals/special.csv Int | created 2026-10-20, resolved 2026-10-20 | — |
| [DATA-037](issues/DATA/DATA-037.md) | Medium | Reference decoder accepts signed defensive fumbles absent from priority table | created 2026-11-06, resolved 2026-11-07 | — |
| [FLOW-015](issues/FLOW/FLOW-015.md) | Medium | Browser play log shows raw seconds and attributes half-ending plays to the next period | created 2026-11-06, resolved 2026-11-07 | — |
| [TRACE-006](issues/TRACE/TRACE-006.md) | Medium | Compact punt-return penalty output lacked its reroll and enforcement details | created 2026-10-17, resolved 2026-10-17 | TRACE-004 |
| [VAL-012](issues/VAL/VAL-012.md) | Medium | Invalid API play calls silently execute a different play | created 2026-10-30, resolved 2026-10-30 | — |
| [AUD-005](issues/AUD/AUD-005.md) | Low | Offensive fumble-advance commentary exposes internal positions, conflates recovery/advance rolls and chart/actual… | created 2026-10-19, resolved 2026-10-19 | — |
| [AUD-006](issues/AUD/AUD-006.md) | Low | CLI repeats touchdowns/first downs, made field goals, defensive fumble scores, safeties, and fourth-down kneel… | created 2026-10-19, resolved 2026-11-07 | AUD-025 |
| [AUD-011](issues/AUD/AUD-011.md) | Low | Complete new/resumed CLI loops repeat the actual turnover-on-downs announcement | created 2026-10-19, resolved 2026-10-19 | AUD-001 |


## Closed (73)

A play-test audit confirmed the issue no longer occurs.

| ID | Priority | Title | Dates | Links |
|----|----------|-------|-------|-------|
| [AI-014](issues/AI/AI-014.md) | High | CPU preserves an opponent touchdown instead of accepting an eligible offensive foul that erases it | created 2026-10-19, resolved 2026-10-19, closed 2026-10-20 | — |
| [AI-025](issues/AI/AI-025.md) | High | Auto-game Hard never records observed opponent calls | created 2026-11-05, resolved 2026-11-07, closed 2026-11-08 | AI-009, AI-019, VAL-019, AI-026 |
| [AI-027](issues/AI/AI-027.md) | High | Web CPU drops selected clock-management options and never requests strategic timeouts | created 2026-11-06, resolved 2026-11-07, closed 2026-11-08 | — |
| [AUD-031](issues/AUD/AUD-031.md) | High | Local return-exposure observer reuses stale object identity keys across plays and games | created 2026-11-06, resolved 2026-11-06, closed 2026-11-06 | — |
| [DATA-007](issues/DATA/DATA-007.md) | High | Modern season chart generation bypasses available play-by-play data | created 2026-11-01, resolved 2026-11-01, closed 2026-11-01 | DATA-006, DATA-008, DATA-009 |
| [DATA-008](issues/DATA/DATA-008.md) | High | Generated season charts are excluded from published game builds | created 2026-11-01, resolved 2026-11-01, closed 2026-11-01 | DATA-007 |
| [DATA-009](issues/DATA/DATA-009.md) | High | Play-by-play rushing scores become field-independent touchdown chart results | created 2026-11-01, resolved 2026-11-02, closed 2026-11-02 | DATA-007, DATA-010, DATA-011 |
| [DATA-012](issues/DATA/DATA-012.md) | High | Defensive interception calibration concentrates risk in a high-mass Short Pass row | created 2026-11-01, resolved 2026-11-02, closed 2026-11-02 | DATA-011, AI-019 |
| [DATA-013](issues/DATA/DATA-013.md) | High | Generated charts omit special-teams penalty results | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | DATA-014 |
| [DATA-014](issues/DATA/DATA-014.md) | High | Comprehensive chart audit exposes lost source features and biased empirical quantization | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | DATA-006, DATA-011, DATA-013 |
| [DATA-019](issues/DATA/DATA-019.md) | High | Calibration observer counts QT fumbles as completed passes instead of sacks or rushing | created 2026-11-05, resolved 2026-11-07, closed 2026-11-08 | DATA-018 |
| [DATA-020](issues/DATA/DATA-020.md) | High | Calibration observer credits nullified offsetting-penalty plays | created 2026-11-05, resolved 2026-11-07, closed 2026-11-08 | DATA-031 |
| [DATA-021](issues/DATA/DATA-021.md) | High | Generated supplemental columns contain symbols that invoke unintended engine fallback | created 2026-11-05, resolved 2026-11-07, closed 2026-11-08 | — |
| [DATA-034](issues/DATA/DATA-034.md) | High | Punt-foul rerolls discard retained kick classes and markers | created 2026-11-06, resolved 2026-11-06, closed 2026-11-06 | DATA-032, RULE-027 |
| [FLOW-012](issues/FLOW/FLOW-012.md) | High | Competing CPU fourth-down requests can restore a stale kick panel after possession changes | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | VAL-015 |
| [FLOW-013](issues/FLOW/FLOW-013.md) | High | Web modifier panel hides defensive timeout requests and does not forward them to the engine | created 2026-11-02, resolved 2026-11-07, closed 2026-11-08 | — |
| [FLOW-019](issues/FLOW/FLOW-019.md) | High | Offsetting kickoff fouls end the period before the required re-kick | created 2026-11-07, resolved 2026-11-07, closed 2026-11-07 | — |
| [RULE-010](issues/RULE/RULE-010.md) | High | Kickoffs resolved the kick distance and the return from **one** dice roll | created 2026-10-19, resolved 2026-10-19, closed 2026-10-20 | AUD-021, FLOW-005, RULE-014 |
| [RULE-013](issues/RULE/RULE-013.md) | High | A penalty on the kickoff-return chart was enforced automatically with no reroll trace and no fumble handling… | created 2026-10-19, resolved 2026-10-20, closed 2026-10-20 | AI-016 |
| [RULE-017](issues/RULE/RULE-017.md) | High | Own-recovery fumble advance resets the down to second regardless of the down before | created 2026-10-27, resolved 2026-10-27, closed 2026-11-06 | — |
| [RULE-021](issues/RULE/RULE-021.md) | High | Matching second-possession field goal incorrectly ends modified sudden-death overtime tied | created 2026-11-01, resolved 2026-11-01, closed 2026-11-01 | DATA-006 |
| [RULE-022](issues/RULE/RULE-022.md) | High | Declined late-game penalty loses clock-stoppage context and charges ordinary scrimmage time | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | — |
| [RULE-023](issues/RULE/RULE-023.md) | High | Numeric defensive adjustments suppress natural out-of-bounds clock stops | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | — |
| [RULE-024](issues/RULE/RULE-024.md) | High | Missed field goals always transfer at the kick spot instead of using season-specific rules | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | — |
| [RULE-028](issues/RULE/RULE-028.md) | High | Returner fouls can exceed half the distance and overstate assessed yardage | created 2026-11-06, resolved 2026-11-06, closed 2026-11-06 | RULE-027 |
| [SPIKE-001](issues/SPIKE/SPIKE-001.md) | High | The S modifier adjusts time without charging the agreed additional down | created 2026-10-18, resolved 2026-10-28, closed 2026-10-28 | SPIKE-003 |
| [STAT-004](issues/STAT/STAT-004.md) | High | Standings game numbers target the wrong record after out-of-order weeks | created 2026-10-30, resolved 2026-11-08, closed 2026-11-08 | — |
| [VAL-003](issues/VAL/VAL-003.md) | High | Standings_data.save/season_1983.json is untracked and not ignored and contains private-season results | created 2026-10-19, resolved 2026-10-27, closed 2026-10-27 | — |
| [VAL-009](issues/VAL/VAL-009.md) | High | Review season lookup path confinement at API boundaries | created 2026-10-30, resolved 2026-11-08, closed 2026-11-08 | — |
| [VAL-014](issues/VAL/VAL-014.md) | High | Two complete browser games share a single three-minute test budget in hosted CI | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | — |
| [VAL-022](issues/VAL/VAL-022.md) | High | Frozen web launcher leaves API model annotations unresolved | created 2026-11-08, resolved 2026-11-08, closed 2026-11-08 | VAL-023 |
| [AI-001](issues/AI/AI-001.md) | Medium | CPU accepts a five-yard automatic-first-down penalty instead of an eleven-yard gain that also earns a first down | created 2026-10-18, resolved 2026-10-28, closed 2026-10-28 | AI-003, AI-018 |
| [AI-009](issues/AI/AI-009.md) | Medium | Existing balanced auto/season checks do not exercise Hard-vs-Hard or expose structured play-balance evidence | created 2026-10-18, resolved 2026-10-18, closed 2026-10-26 | AI-025 |
| [AI-010](issues/AI/AI-010.md) | Medium | Opponent learning treated punts/field goals as runs because a false pass flag overrode action classification | created 2026-10-18, resolved 2026-10-18, closed 2026-10-28 | AI-012 |
| [AI-011](issues/AI/AI-011.md) | Medium | A two-score Q4 deficit triggered a whole-quarter deep-pass-only hurry-up branch, bypassing down/distance and… | created 2026-10-18, resolved 2026-10-18, closed 2026-11-02 | — |
| [AI-028](issues/AI/AI-028.md) | Medium | Fourth-down urgency falls through to conservative punting in own territory when multiple scores are needed | created 2026-11-06, resolved 2026-11-07, closed 2026-11-07 | AI-003, AI-006 |
| [AUD-009](issues/AUD/AUD-009.md) | Medium | QB-time rushing touchdown is described as a completed pass to a receiver | created 2026-10-19, resolved 2026-10-19, closed 2026-11-02 | — |
| [AUD-026](issues/AUD/AUD-026.md) | Medium | Kickoff penalty preview invents a touchdown by applying kick-penalty yards to the prior scoring spot | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | — |
| [DATA-004](issues/DATA/DATA-004.md) | Medium | Aggregate chart generation compresses distinct teams into coarse defensive templates | created 2026-11-01, resolved 2026-11-01, closed 2026-11-01 | — |
| [DATA-005](issues/DATA/DATA-005.md) | Medium | Empirical chart generation discards numeric out-of-bounds markers | created 2026-11-01, resolved 2026-11-01, closed 2026-11-01 | — |
| [DATA-006](issues/DATA/DATA-006.md) | Medium | Aggregate chart calibration omits supplied rates and lacks resolved-outcome validation | created 2026-11-01, resolved 2026-11-01, closed 2026-11-01 | RULE-021, DATA-007, DATA-010, DATA-014 |
| [DATA-010](issues/DATA/DATA-010.md) | Medium | Generated breakaway triggers and B yardage are not reconstructed from play by play | created 2026-11-01, resolved 2026-11-02, closed 2026-11-02 | DATA-006, DATA-009, DATA-011 |
| [DATA-033](issues/DATA/DATA-033.md) | Medium | Return-penalty modifiers lack an explicit consumer interpretation | created 2026-11-06, resolved 2026-11-06, closed 2026-11-06 | RULE-027 |
| [DATA-043](issues/DATA/DATA-043.md) | Medium | Prevent cross-play interception spot allocation in generated passing charts | created 2026-11-07, resolved 2026-11-07, closed 2026-11-07 | — |
| [FLOW-005](issues/FLOW/FLOW-005.md) | Medium | Second-half kicker was guessed from current possession in resume_game ("Approximate") and in the web kickoff… | created 2026-10-19, resolved 2026-10-19, closed 2026-10-20 | RULE-002, RULE-010 |
| [FLOW-014](issues/FLOW/FLOW-014.md) | Medium | Save game gives no visible success or failure feedback | created 2026-11-06, resolved 2026-11-06, closed 2026-11-06 | — |
| [FLOW-018](issues/FLOW/FLOW-018.md) | Medium | Browser omits the season-enabled two-point conversion choice after a touchdown | created 2026-11-06, resolved 2026-11-07, closed 2026-11-08 | RULE-001, STAT-003 |
| [RULE-001](issues/RULE/RULE-001.md) | Medium | Two-point tries run through run_play | created 2026-10-19, resolved 2026-11-07, closed 2026-11-08 | RULE-002, RULE-007, STAT-003, AI-022, FLOW-018 |
| [RULE-007](issues/RULE/RULE-007.md) | Medium | Uncommitted _log_score try attribution relies on scoring_plays[-1] being the TD | created 2026-10-19, resolved 2026-11-07, closed 2026-11-08 | RULE-001 |
| [SPIKE-002](issues/SPIKE/SPIKE-002.md) | Medium | Offense 7S is processed before a defensive AT, so execution order blocks the agreed defensive-timeout priority | created 2026-10-18, resolved 2026-10-28, closed 2026-10-28 | AI-005, RULE-006 |
| [SPIKE-004](issues/SPIKE/SPIKE-004.md) | Medium | Standalone spike passes a minute value to the seconds-based clock | created 2026-11-06, resolved 2026-11-07, closed 2026-11-08 | — |
| [STAT-002](issues/STAT/STAT-002.md) | Medium | Successful PAT is allocated to the live next quarter instead of the touchdown quarter | created 2026-10-19, resolved 2026-10-19, closed 2026-10-28 | — |
| [STAT-003](issues/STAT/STAT-003.md) | Medium | Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception… | created 2026-10-19, resolved 2026-11-07, closed 2026-11-08 | RULE-001, STAT-001, FLOW-018 |
| [STAT-005](issues/STAT/STAT-005.md) | Medium | Scrimmage return narration omits assessed penalties and hides their rerolls | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | — |
| [TRACE-009](issues/TRACE/TRACE-009.md) | Medium | Half-ending touchdown and kickoff lack elapsed-time evidence to verify whether another snap was owed | created 2026-10-28, resolved 2026-10-28, closed 2026-10-28 | AI-007 |
| [VAL-006](issues/VAL/VAL-006.md) | Medium | CI matrix includes Python 3.9 while requires-python >= 3.10 and the audit harness uses 3.10 syntax | created 2026-10-19, resolved 2026-11-07, closed 2026-11-08 | — |
| [VAL-007](issues/VAL/VAL-007.md) | Medium | Corrected offensive dice invalidated two seeded untimed-down reproduction requirements | created 2026-10-26, resolved 2026-10-30, closed 2026-10-30 | — |
| [VAL-010](issues/VAL/VAL-010.md) | Medium | Unit regressions still depend on private historical seasons and silently skip | created 2026-10-30, resolved 2026-11-07, closed 2026-11-08 | — |
| [VAL-015](issues/VAL/VAL-015.md) | Medium | Browser driver waits for execution when an early defense click needs a later CPU confirmation | created 2026-11-02, resolved 2026-11-02, closed 2026-11-02 | FLOW-012 |
| [VAL-016](issues/VAL/VAL-016.md) | Medium | Development API proxy cannot reach an IPv4-only backend when localhost resolves to IPv6 | created 2026-11-05, resolved 2026-11-07, closed 2026-11-08 | — |
| [VAL-021](issues/VAL/VAL-021.md) | Medium | Release workflow token cannot publish despite successful platform builds | created 2026-11-07, resolved 2026-11-07, closed 2026-11-07 | — |
| [VAL-023](issues/VAL/VAL-023.md) | Medium | Windows published-asset smoke cannot confirm normal console shutdown | created 2026-11-08, resolved 2026-11-09, closed 2026-11-09 | VAL-022 |
| [VAL-024](issues/VAL/VAL-024.md) | Medium | Required local source chart gates reject current public release manifests | created 2026-11-08, resolved 2026-11-09, closed 2026-11-09 | — |
| [AI-007](issues/AI/AI-007.md) | Low | Base incomplete-pass durations appear long in some logs | created 2026-10-18, resolved 2026-10-28, closed 2026-10-28 | TRACE-009 |
| [AUD-002](issues/AUD/AUD-002.md) | Low | Non-touchdown breakaway commentary claims nobody will catch the runner | created 2026-10-18, resolved 2026-10-19, closed 2026-11-02 | — |
| [AUD-003](issues/AUD/AUD-003.md) | Low | QB-kneel commentary credits a running back and describes an ordinary tackled loss | created 2026-10-18, resolved 2026-10-19, closed 2026-11-02 | — |
| [AUD-004](issues/AUD/AUD-004.md) | Low | Goal-to-go headers repeat the position separator, such as a goal-distance marker followed by a second @ | created 2026-10-18, resolved 2026-10-19, closed 2026-10-28 | — |
| [AUD-010](issues/AUD/AUD-010.md) | Low | Ordinary offensive fumble recovery describes pre-fumble gain as an extra post-recovery advance | created 2026-10-19, resolved 2026-10-19, closed 2026-10-28 | — |
| [AUD-012](issues/AUD/AUD-012.md) | Low | Pass interference repeats the achieved first-down wording | created 2026-10-19, resolved 2026-10-19, closed 2026-10-28 | — |
| [AUD-013](issues/AUD/AUD-013.md) | Low | Incomplete result/menu labels say No gain, obscuring the actual pass result | created 2026-10-19, resolved 2026-10-19, closed 2026-10-28 | — |
| [AUD-027](issues/AUD/AUD-027.md) | Low | Chart viewer loses keyboard focus when its native modal closes | created 2026-11-05, resolved 2026-11-07, closed 2026-11-08 | — |
| [FLOW-017](issues/FLOW/FLOW-017.md) | Low | Scoreboard omits the opponent timeout budget and leaves the displayed count ambiguous | created 2026-11-06, resolved 2026-11-07, closed 2026-11-08 | — |
| [TRACE-002](issues/TRACE/TRACE-002.md) | Low | Fumble traces show unknown defensive rows and placeholder-looking zero return rolls | created 2026-10-18, resolved 2026-10-20, closed 2026-10-20 | TRACE-007 |

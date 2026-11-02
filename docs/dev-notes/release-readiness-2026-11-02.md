# Release readiness investigation — 2026-11-02

This is a work log and review record, not a claim of historical statistical fit.
Scope: RULE-022, RULE-023, RULE-024, AUD-026, STAT-005, followed by the full
AGENTS.md regression checklist and a reviewable local result. Push requires
the user's final approval. RULE-025 was added when the required regression
exposed the separate CLI clock-boundary defect.

### Grilling Notes

**Assumptions verified:** 5/6. Numeric defensive adjustments retain the offensive
result; actual overruling results replace it (`priority_chart.py`). Kickoff
penalty choices occur before the old scrimmage spot is replaced
(`game_engine.py:kickoff`). The missed-kick spot changed in 1994 ([Hall of Fame](https://www.profootballhof.com/news/nfl-kickers-up-up-and-away)).
The extra fifteen penalty yards are not reproduced by either visible kickoff
foul in isolation. Follow-up identifies omitted scrimmage-fumble-return
enforcement in the compact narration (STAT-005).

**Open Questions:** 6 -> 0 (removed 6, added 0).
The user directed use of the supplied rulebook rather than a search for the
separate standard board chart. RULE-022 adopts its action/return time with
zero dead time for flagged scrimmage plays, consistently with the existing
selected incompletion rule. The full alternate system is not enabled.
STAT-005 has a causal public/synthetic reproduction and complete-game
confirmation. No full RNG capture exists for the manual game; the original
missing numeric reroll is not reconstructed.

**Status changed:** QUESTIONS_PENDING -> READY_FOR_REVIEW_WITH_LIMITS.
All five initial findings now have issue-specific confirmation. Statistical
calibration still predates the clock fixes and is not re-certified by these
completion/presentation audits.

**Key revision:** Resolve sideline provenance in the priority resolver, use
season rules for missed kicks, and generate kickoff previews in the engine.
Do not infer an accounting fix from a mismatched final total or invent the
missing Timing Chart. Preserve existing secondary B/QT rolls and avoid
preview-only dice consumption or statistics mutations. Changes can be reverted
by their eventual scoped commits; no chart regeneration is required for these
engine fixes.

## Test-first evidence

- RULE-023: initial valid baseline 28 failing / 28 passing; added priority
  provenance cases yielded 34 failing / 31 passing. After the fix, 392 focused
  tests passed, including priority, resolver, spike and incomplete timing.
- RULE-024: 20 failing / 16 passing before the fix across both teams, direct
  misses, declined fouls, 1973/1974 and 1993/1994 boundaries, and twenty-yard
  minimums. Then 124 focused tests passed, with three existing local-data
  skips. Existing generic FG fixtures now use public-era 2026 rather than
  1983: their unchanged modern kick-spot assertions were invalid for 1983.
- AUD-026: ten expected failing kickoff previews and three existing passing
  CLI controls; engine previews preserve dice and statistics.
- RULE-022: the initial clock-stop baseline had 42 expected failures and
  twenty clean controls, followed by six direct-foul cases and one Hail Mary
  case. A provisional twenty-second RedZone policy was removed after the
  user's rulebook clarification. Rulebook action-time cases then showed
  thirteen duration failures and one passing incompletion control, plus two
  new return-time cases. The final 465 focused clock/CLI/untimed tests pass.
- RULE-025: full regression exposed a playable 1.0016277568-second remainder
  that the CLI discarded. Four public new/resume cases failed while two
  zero-clock controls passed. All six now pass using an engine-owned expiry
  query. Neither CLI writes the clock to end the game.
- STAT-005: initial halftime/return/re-kick controls passed but did not exercise
  the scrimmage-fumble return. Follow-up produced 72 valid missing-explanation
  failures and 36 clean controls, then 208 focused passes. New synthetic cases
  cover both sides, direct/procedure/declined paths, both CLI layouts,
  interceptions, retained/lost fumble returns and both foul attributions. The
  fixture's opposing-team near-goal expectation was corrected to half-distance,
  then the baseline rerun on the unchanged engine. No existing assertion or
  accounting mutation changed.

## Timing policy and changed expectations

The supplied *Paydirt Rules 2008*, printed pages 22–23, specifies action plus
return plus dead time; any play involving a foul has zero dead time. Runs and
completions take five seconds plus the tens digit of distance covered. A
nine-yard flagged completion therefore leaves 1:20 from 1:25. The engine uses
this selected rule for flagged scrimmage plays, not the entire alternate
method. Standalone foul cells have no observed live-play movement and use
base action time; enforcement yards do not represent yards covered. Kicks
and offsetting fouls retain their existing separate policies.

Every existing-test adjustment has a specific reason:

- `test_oob_priority_chart` and `test_out_of_bounds`: a genuine defensive
  overrule cannot retain the superseded offensive sideline marker. Their
  raw offensive marker remains present, but the resolved marker is false.
- `test_field_goal`: the fixture now uses public-era 2026 because its
  unchanged assertions describe modern kick-spot placement, not 1983.
- `test_penalty_clock_context`: flagged results use action time rather than
  an ordinary huddle. Period-boundary inputs now bracket actual action-time
  expiry, preserving all untimed-down assertions and passing controls.
- `test_spike_down_cost` and `test_spike_timeout_priority`: a foul already
  stops the clock; declining it needs neither an additional spike down nor
  an extra timeout. Down, field position and timeout-budget assertions remain.
- `test_timeout_quarter_change`: mocked outcomes explicitly set the new
  boolean to false; an unconfigured MagicMock attribute is truthy.
- `test_kickoff_after_score`: its fixture now pins ordinary kick/return cells
  rather than randomly encountering the newly generated foul/fumble cells.
  Possession and scoring assertions are unchanged. A later full-suite run
  exposed the same assumption in `test_resume_pending_score`: seed 325
  reproduces a pending kickoff foul before a receiving possession exists.
  Its load fixture now supplies ordinary kicks/returns, preserving every
  ownership assertion. The unused historical-data skip marker was removed;
  no test was skipped or assertion relaxed. The uncaptured full-suite event
  itself is not claimed to be an exact seed-325 replay.
- `test_halftime_ownership`, `test_period_scoring_queries` and backend
  `test_halftime_api`: flagged half/quarter-ending fixtures use five seconds
  instead of twenty. The API also checks a twenty-second control correctly
  retaining fifteen seconds. No halftime or kickoff assertion was relaxed.
- `test_full_season_runner`: all thirteen old complete games remain. Two
  verified current-timing supplements are added, with mandatory extension
  checks transferred to them. Fifteen attempts, both events, and injected
  failure accounting are required. See the seed-drift note. This does not
  change dice or live AI to manufacture a result.
- Frontend `user-guide.spec.js`: expected heading/link/anchor now match the
  earlier documented title, “Chart Generation and Excel Import.” Offline
  navigation assertions remain mandatory.
- The earlier `test_display_play_result` adjustment removes dependence on a
  fabricated recovery announcement and checks the authoritative engine text;
  AUD-025 records its separate test-first evidence.

## Current validation

All required AGENTS.md commands passed. Logs and raw reports remain ignored
under `.ai-audits/release-readiness/` and `.ai-audits/`.

| Check | Result |
|---|---|
| Core pytest with coverage | 6,770 passed, eight existing data-dependent skips; 79% total coverage |
| Clean staged-files snapshot, no ignored/private charts | 6,753 passed, 25 existing data-dependent skips |
| Backend pytest | 280 passed, twenty existing Pydantic deprecation warnings |
| Frontend unit tests | 255 passed, one existing skipped test, 27 files passed |
| Frontend build | Passed |
| Real browser games and offline guide | Two tests passed; both home/receiving and away/kicking games completed |
| Ruff | Passed |
| Final documentation/tracker checks | 269 passed |
| Standalone games | 14/14 passed |
| Historical CLI reproductions | 15/15 passed; both required untimed downs exercised |
| Generated 1983 regular season | 224/224 passed; twelve OT games, one valid tie |
| Generated postseason | 9/9 passed; one OT game, no ties |
| Required public AI audit | 32/32 passed; 4,807 calls, no concentration warnings |
| Required local AI audit | 448/448 passed; 65,224 calls, one advisory warning |

The clean snapshot exposes seventeen additional pre-existing private-data
skips rather than hiding them with local charts; no skip was added in this
change. The current clean run includes the save/resume fixtures and all new
return-narration cases. Browser tooling reports existing stale Browserslist data and
NO_COLOR/FORCE_COLOR warnings. These are disclosed, not suppressed.

A separate 64-game audit uses public sample teams with synthetic End Run
sideline markers, one kickoff foul cell, and 1983/2026 era overrides. It
confirmed 767 foul clock stops, 68 late-window sideline stops, nineteen
kickoff previews, and 34/39 era-specific missed-kick spots, without failures.
Its 576 narrated scrimmage-penalty increments are not a complete special-teams
accounting oracle or an exact replay of the uncaptured manual game.

A separate 64-game public/synthetic return audit confirms the STAT-005 fix:
84 interception-return fouls, four lost-fumble-return fouls and three retained
fumble-advance fouls display their enforcement/reroll evidence in both CLI
layouts. Formatting leaves penalty totals and gameplay RNG unchanged. This
explicitly covers the return path omitted by the earlier lifecycle controls;
the original game's printed six-yard return is net of the hidden fifteen-yard
foul. Its four-for-45 total now reconciles without changing accounting.

Per-team/down/distance/mode call shares, distinct alternatives and repetition
streaks were reviewed in both required AI reports. The sole warning is legacy
balanced Broncos third-and-11-plus: 48 calls, 50% Screen, three alternatives,
streak three. Hard's largest supported ordinary concentration is 47.9% with
seven alternatives, streak three, n=48. The warned balanced policy selects uniformly from its three very-long-yardage
pass options, independent of chart strength (16 Medium, eight Long, 24 Screen).
These advisory findings are recorded on AI-008 without imposing a universal usage cap or weakening checks.

## Ticket and release limits

RULE-022/023/024 and AUD-026 have issue-specific full-game evidence. AUD-025
and RULE-025 retain resolved status pending their particular post-fix
full-game presentation/final-second observation. STAT-005 closes after the
causal narration reproduction and dedicated complete-game confirmation.
The 32 remaining resolved tickets were reviewed again after the return audit;
no unrelated issue is closed without its own event evidence. AUD-009 closes after its
dedicated full-game semantic oracle verifies twelve scramble-TD narratives
and their rushing/scoring attribution. Unobserved browser, conversion,
recovery or coaching cases are not closed from ordinary completion alone.

DATA-009/010/012/013/014 have generated-chart manual confirmation. DATA-011's
tool is implemented; sparse passing-TD experiments are separately deferred in
DATA-015. Earlier 64-season training and 256-season held-out results describe
the earlier engine. The clock fixes change pace and seeded trajectories, so
today's completion/selection audits are not a renewed statistical fit claim.
Generated source CSVs are unchanged by these clock fixes.

The reviewable local commit includes only tracked/public generated data and
reviewed source/docs/tests; ignored developer charts, downloaded rules,
source caches, calibration reports and narrative logs are excluded. Push
still requires the user's explicit final approval for this goal.

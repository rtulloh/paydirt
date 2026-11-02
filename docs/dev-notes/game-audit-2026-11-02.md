# Completed manual game audit — November 2, 2026

Developer investigation, not a release promise or a chart-quality certification.
The original narrative, local charts, and detailed line references remain local.
Aggregate diagnostics are ignored under `.ai-audits/manual-2026-11-02/`.

## Reconciled game results

Human Dallas beat Hard Philadelphia 37–17 using the generated 1983 teams.
The 147 pre-play headers contain 128 statistical scrimmage plays, ten punts,
five field-goal attempts, and four accepted/nullified scrimmage plays. Kickoffs
and tries occur between headers and are not included in that count.

| Metric | Philadelphia | Dallas |
|---|---:|---:|
| Quarter points | 0 / 0 / 10 / 7 | 3 / 17 / 3 / 14 |
| Total yards | 241 | 411 |
| Rushes / yards | 14 / 47 | 47 / 158 |
| Completions / attempts | 14 / 32 (43.8%) | 18 / 31 (58.1%) |
| Gross / net passing yards | 231 / 194 | 253 / 253 |
| Sacks allowed / yards lost | 4 / 37 | 0 / 0 |
| First downs | 12 | 25 |
| Interceptions / lost fumbles | 0 / 3 | 0 / 1 |
| Field goals | 1 / 1 | 3 / 4 |
| Printed penalties / yards | 3 / 22 | 4 / 45 |
| Visible accepted penalties / yards | 3 / 22 | 3 / 30 |

All 31 incompletions use five seconds, including hurry-up and skipped-timeout
cases. Both two-minute warnings and halftime timeout resets occur. All 117
ordinary nonturnover/non-scoring same-period field-position transitions checked
against the next header reconcile. First downs include touchdown first downs
and one accepted automatic-first-down foul; the box-score totals reconcile.
The learning summary's 79 eligible human calls splits into 47 runs and 32
passes, excluding three punts, four field goals, and the final kneel, while
retaining the two penalty-triggering primary calls.

Both special-teams touchdowns are valid recovery advances. Each team scores
once after recovering the opponent's return fumble and rolling enough actual
return yardage to reach the goal. The third Philadelphia lost fumble is a
goal-line run recovered by Dallas in its end zone for a touchback; the other
is a nine-yard QT sack/fumble followed by a six-yard defensive advance. A
one-yard QT fumble retained by Philadelphia is not a giveaway. Dallas scores
17 points on possessions immediately following Philadelphia's three giveaways;
Philadelphia scores seven immediately on Dallas's kickoff-return giveaway.

## Findings and limitations

- [RULE-022](issues/RULE/RULE-022.md): the declined late-game foul uses the
  ordinary 44-second completion charge. The precise replacement duration
  still requires standard Timing Chart verification.
- [RULE-023](issues/RULE/RULE-023.md): two naturally marked out-of-bounds runs
  inside Q4's last five minutes consume 29 and 35 seconds. A full-resolver
  public/synthetic reproduction confirms numeric defense adjustments suppress
  the ten-second timing benefit. Blank and actual-overrule controls distinguish
  the defect from valid ordinary timing.
- [RULE-024](issues/RULE/RULE-024.md): an untouched missed field goal gives
  Philadelphia its 42 instead of its 35 under 1983 rules. Public reproduction
  confirms the unconditional holder-spot policy; primary rule-history sources
  document the 1994 change.
- [AUD-026](issues/AUD/AUD-026.md): the kickoff penalty menu falsely predicts
  another touchdown from a stored scoring spot. The CPU accepts the re-kick
  and the actual score remains correct. Reproduced with public sample teams.
- [STAT-005](issues/STAT/STAT-005.md): Dallas's extra reported fifteen-yard
  foul is unexplained. Visible accepted penalties total three for 30, not
  four for 45. Isolated return-foul and re-kick replays do not reproduce it.
- [AUD-025](issues/AUD/AUD-025.md): this already-running process still shows
  the old punt narrative and duplicate touchdown wording. The underlying score
  is valid; this game cannot verify the later presentation patch.
- [TRACE-001](issues/TRACE/TRACE-001.md) and
  [TRACE-003](issues/TRACE/TRACE-003.md): secondary QT rolls and complete called
  modifiers remain absent, preventing an exact full-game replay. Clock traces
  round display seconds while headers truncate them, explaining one-second
  apparent disagreements without establishing a second clock charge. The
  timeout-skip message also calls downed punts out of bounds and says the
  clock is already at ten seconds even where the headers show seven or eleven;
  the automatic possession-change stop is valid, but that explanation is inaccurate.

Seven explicit penalty menus plus the automatic second-half kickoff-return
foul demonstrate special-teams penalty coverage; two scrimmage fouls are
declined. This game therefore does not reproduce the earlier complete absence
of generated special-teams fouls. Zero interceptions also avoids the earlier
interception burst, but one game cannot certify the chart distribution.

## Coaching and ticket review

Philadelphia's 52 primary scrimmage choices use eight play types. Screen and
TE Short/Long tie for the largest share at 11/52 (21.2%). Its fifteen Q4 calls
span six choices, including Draw, with no deep-pass-only hurry-up lock. Every
observed Philadelphia down/distance group has a longest comparable repetition
streak of two; the largest group has twenty calls and eight choices. Counts
are below the season audit's supported-group advisory threshold. No fixed
frequency cap or probabilistic policy certification is inferred.

Punting on fourth-and-20 at own 43 with 3:25 left while down twenty is a
questionable recovery strategy. A synthetic public-team AI probe reproduces
the punt: the 2–5-minute desperation branch falls through for long yardage
in own territory. Record under AI-003/AI-006; no outcome-based conversion-odds
claim or new coaching policy is made.

Issue-specific observed non-scoring breakaway wording, final QB-kneel wording,
and varied hurry-up choices close AUD-002, AUD-003, and AI-011. RULE-014 now
also has a captured lost kickoff-return fumble with a recovery advance, but
its explicit live-foul recovery choice remains unobserved; keep resolved.
RULE-019's rare penalty/TD variants remain unobserved. No generic game-completion
claim closes those tickets. Current uncommitted generator/punt work remains open.

No gameplay, generator, chart data, standings, or original log changed. No
commit, push, full-season rerun, or full pre-push regression is part of this
read-only audit. Public synthetic probes support the diagnoses, not proposed fixes.

Validation: 405 existing documentation/tracker, punt-commentary, and incomplete-pass
timing tests pass; whitespace checks pass. These passing suites do not cover the
newly diagnosed behaviors and are not proof those issues are fixed. The original
log's SHA-256 is unchanged, and the aggregate report is confirmed ignored.

# Developer Issue Tracker

**Developer-only working record, not a player guide or a release promise.**

Last reviewed: 2026-10-18. See the [developer-note disclaimer](README.md).
This is the status index for audit findings, die-roll/replay work, and AI follow-ups.
Keep the detailed designs in their linked notes rather than maintaining duplicate specifications.

## Tracking Conventions

- **High:** incorrect gameplay or an announcement falsely claiming a possession change.
- **Medium:** materially poor coaching decisions, missing audit evidence, or regression-validation blockers.
- **Low:** wording, formatting, or exploratory work without a demonstrated gameplay defect.
- **Open:** confirmed work remains. **Investigating:** observation exists but cause is not established.
  **Deferred:** deliberately not scheduled. **Implemented, uncommitted:** working-tree fix, not released.
  **Monitoring:** validation now passes, but the original cause remains unconfirmed.
  **Resolved:** committed fix with verification recorded; add the commit and release when known.
- Keep resolved rows. Update their resolution/verification notes when work ships or an issue reopens.
- Add failing synthetic/public-2026 regressions before behavior changes. Never weaken tests or infer missing dice.
- Private logs and historical charts stay local and ignored. Do not attach or reproduce them here.

## Gameplay and CLI Audit Findings

The latest local full-game audit reconciled score, quarter totals, first downs, scrimmage yardage,
turnovers, sacks, and penalty totals. An initial apparent penalty discrepancy was explained by an
enforced punt-return foul; it is **not** an outstanding accounting defect.

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| AUD-001 | High | Fourth-down offsetting penalties incorrectly announce turnover on downs despite replaying the down and retaining possession. Accepted replay-down penalties can produce the same false banner. | Resolved | Fix committed together with this tracker entry; see this file's Git history for the commit. Added engine-owned `PlayOutcome.turnover_on_downs`; actual-result displays and both CLI loops now consume it. Added 76 synthetic/public-fixture cases, including genuine failures, conversions, fumbles, special plays, and new/resumed games. Initial baseline: 29 expected failures, 33 passing controls. Current core: 4,381 passed, 8 existing skips; clean snapshot: 4,364 passed, 25 existing private-data skips. Full browser validation passed on an isolated rerun, including both full games and offline help; initial failure remains disclosed under VAL-001. No release contains this fix yet. |
| AI-001 | Medium | CPU accepts a five-yard automatic-first-down penalty instead of an eleven-yard gain that also earns a first down. | Open | Compare resulting field position and down/distance, rather than automatically preferring an automatic-first-down flag. The latest local audit reconfirmed this choice; use synthetic fixtures for the regression. |
| AI-002 | Medium | On an incomplete first-down pass, CPU declines a 15-yard offensive penalty: second-and-ten instead of first-and-25. | Open | Current defensive choice uses positive play yardage as its acceptance test. Evaluate the resulting situations and relevant clock context; do not declare every declined penalty illegal or require automatic acceptance in every situation. |
| AUD-002 | Low | Non-touchdown breakaway commentary claims nobody will catch the runner. | Open | Gate touchdown-specific commentary on the final engine outcome; retain ordinary breakaway excitement for gains that end short of the goal line. |
| AUD-003 | Low | QB-kneel commentary credits a running back and describes an ordinary tackled loss. | Open | Display the engine kneel action and appropriate QB attribution without fabricating a rushing attempt by a running back. |
| AUD-004 | Low | Goal-to-go headers repeat the position separator, such as a goal-distance marker followed by a second `@`. | Open | Render one clear engine-provided down/distance and field-position description; cover compact goal-to-go headers. |

## Die-Roll Tracking and Replay

Detailed requirements: [Replayable game logs](replayable-game-logs.md).
Actual captured rolls are authoritative; never reconstruct a missing roll from its result.

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| TRACE-001 | Medium | Secondary QB-time rolls/results are not visible consistently, especially QB-time fumbles and transaction-based compact output. | Open | Existing resolvers already retain `qb_scramble_dice` and yardage. Audit all render paths and expose the captured secondary result in compact and normal output without rerolling, parsing commentary, changing RNG consumption, or altering gameplay. Cover sacks/safeties, scrambles, fumbles, and non-QT controls. This is the narrow next-round item in the replay note. |
| TRACE-002 | Low | Fumble traces show unknown defensive rows and placeholder-looking zero return rolls. | Open | Preserve actual defensive-row metadata; distinguish no return roll from an actual zero-yard return. Do not fabricate a `Ret:0` die roll. Reconfirmed in the latest audit. |
| TRACE-003 | Medium | Compact traces do not explicitly identify called modifiers and the winning clock procedure. | Open | Record calls such as spike, timeout, sideline designation, and no-huddle separately from resolved effects. Explain skipped/canceled modifiers. A five-yard reduction cannot be independently attributed to a designation when the call is absent from the trace. |
| TRACE-004 | Medium | Offsetting/double-foul procedures can omit initial rolls and rerolls, including previously observed empty punt-return details. | Open | Retain the actual event sequence even when the down is replayed. Prior finding; not independently reproduced for punt returns in the latest game. |
| TRACE-005 | Medium | Full deterministic engine replay from logs is not implemented. | Deferred | Follow the versioned input/event stream, clock samples, decisions, chart/rule identifiers, and checkpoint requirements in the replay note. A partial legacy-log reconstruction or saved display history is not a verified full replay. |
| TRACE-006 | Medium | Compact punt-return penalty output lacked its reroll and enforcement details. | Resolved | `c155864` preserves and displays return reroll/enforcement information with focused tests. The latest audit contains the expected return-penalty details. Broader double-foul trace coverage remains TRACE-004. |

## Agreed Spike Follow-ups

Player-facing explanation and pending-implementation warning: [Clock management](../clock-management.md#spike-modifier-and-combinations).
These rules are agreed project behavior, not a claim that the engine changes have shipped.

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| SPIKE-001 | High | The `S` modifier adjusts time without charging the agreed additional down. | Open | For `7S` called on first down, an applied completion-plus-spike must leave third down, including when the pass earns a first down. An incompletion needs no spike and leaves second down. Resolve penalties before determining the spike effect. Add explicit tests for the agreed first-down-gain exception; do not substitute conventional football assumptions. |
| SPIKE-002 | Medium | Offense `7S` is processed before a defensive `AT`, so execution order blocks the agreed defensive-timeout priority. | Open | Resolve penalty decisions, then an applicable defensive timeout, then any remaining spike request. Charge a useful available defensive timeout, cancel the planned spike, and charge no spike-related down. An unavailable timeout cannot cancel the spike; incompletions charge neither. Log the winning procedure. |
| SPIKE-003 | High | A completion could leave time, then its spike reduce the clock to zero without processing period/game expiration. | Resolved | v1.9.0: exposed by generated-season validation, then fixed with eight failing synthetic home/away direct/integrated regressions plus clock-preserved, tied-game, and untimed-down controls. Newly expired spike clocks delegate to existing `_use_time(0)` period/OT handling. No base timing, spike down charging, or defensive-timeout arbitration changes; SPIKE-001/002 remain open. Final 224-game season and nine playoffs passed. |

## AI Work and Evaluation

Detailed experiment and metric limitations: [AI play-testing](ai-playtesting.md).
Current supported behavior: [AI difficulty guide](../ai-difficulty.md).
Keep decision quality separate from unlucky dice and personnel differences; do not alter dice odds to distinguish difficulty.

| ID | Priority | Issue / work item | Status | Resolution / verification |
|----|----------|-------------------|--------|---------------------------|
| AI-003 | Medium | Evaluate whether Hard uses weaker-team strengths, varies calls, and makes sensible situation-dependent choices. | Open | Continue the existing play-testing experiment. Record decisions judged questionable before the outcome, not just final scores. Conditional chart averages exclude important outcomes and are not full defense-specific expected value or human win-rate estimates. Track penalty-choice defects separately as AI-001 and AI-002. |
| AI-004 | Medium | Chart analysis treated rows as equally likely. | Resolved | `34479d0` weights analysis using actual chart-dice probabilities. Actual dice odds are unchanged; this does not make Hard an always-optimizing opponent. |
| AI-005 | Medium | Difficulty/coaching differentiation and timeout budget handling needed improvement. | Resolved | `a1526f4` adds bounded team-strength-aware early-down choices for Medium, clearer distance-aware Easy coaching, and timeout-accounting/CLI defensive-timeout improvements. Hard retains individual-play analysis; timeout thresholds are shared across difficulties. Spike-versus-timeout arbitration remains SPIKE-002. |
| AI-006 | Medium | Late-game offense/defense and season-aware conversions needed better decisions. | Resolved | `cd6dc17` and `45ceed8` improve endgame choices and trailing defense. Continue evaluating through AI-003; these changes do not imply all coaching decisions are optimal. |
| AI-007 | Low | Base incomplete-pass durations appear long in some logs. | Deferred | No authoritative standard Timing Chart evidence establishes a defect. Preserve base timing until supported by evidence; difficulty should change decisions/coaching, not timing or dice odds. |
| AI-008 | Medium | Hard can become predictable by overconcentrating on any top chart recommendation. Pre–Week 6 priority. | Resolved | v1.9.0: weighted competitive calls across all nine primary plays replace the 40% winner override on ordinary downs, with down/distance targets, known-risk/full-dice-mass scoring, and bounded decaying repetition adjustments. Engine-owned call history excludes previews, counts rerolls once, and survives CLI save/resume. B/QT cannot be primary recommendations. Added 129 core and two backend regressions; expanded pre-fix baseline was 101 expected failures and eight passing controls. Eight existing dice-weighting parameter cases assert weighted preference rather than the obsolete forced winner; dice/ranking assertions remain. Full validation and broader outcome-modeling limitations are recorded below. |
| AI-009 | Medium | Existing balanced auto/season checks do not exercise Hard-vs-Hard or expose structured play-balance evidence. | Resolved | v1.9.0: testing-only `tests/run_ai_audit.py` reuses the complete production auto-game loop with optional configuration/observation hooks. Supports single/repeated/generated-season modes, asymmetric difficulty, reproducible streams, balanced comparisons, finalized outcomes, JSON/CSV, concentration and comparable-situation streak evidence. Normal auto defaults unchanged; no standings or cross-game learning persistence. Mandatory regression includes public/local audits and evidence review. Final 32 public and 448 local games complete with reconciled totals; no Hard ordinary-group warning and one balanced very-long-third-down advisory warning. Reports remain local/ignored, never private chart/log exports. Validation below. |
| AI-010 | Medium | Opponent learning treated punts/field goals as runs because a false pass flag overrode action classification. | Resolved | v1.9.0: exact canonical/display/legacy run/pass classification precedes overrides. Kicks, kneels, spikes, unknown calls, and secondary columns leave totals/streaks untouched; sneaks and Hail Mary count as actual choices. Covers new/resumed CLI and browser centrally. Existing aggregate learning cannot be reconstructed retroactively. Synthetic 32 runs + 26 passes + two punts + FG correctly reports 58, not 61. |
| AI-011 | Medium | A two-score Q4 deficit triggered a whole-quarter deep-pass-only hurry-up branch, bypassing down/distance and recent-call safeguards. | Resolved | v1.9.0: no-huddle pace is separate from gradual clock/deficit passing preference. Hard shares chart/history eligibility and weights; Easy/Medium use situational weights. Credible runs retain positive weight even late, with no pass quota. Endgame/fourth-down priorities and compact-field route restrictions remain. Urgency respects season two-point-conversion availability; audits include hurry-up probabilities. No engine rules, dice odds, or base timing changes. Validation below. |
| AI-012 | Medium | Third-and-long competitive window may admit a weakly scored run despite much stronger alternatives. | Open | Confirmed during local Week 6 decision review. The current .9 utility gap is a coaching heuristic, not a conversion-probability bound. Review candidate quality with target-sensitive synthetic tests and team chart context; do not ban runs categorically or narrow the window merely to satisfy concentration warnings. Kept separate from AI-010/011. |

### AI-008: Implementation Scope and Acceptance Criteria

The bounded pre–Week 6 fix implements play-independent variety, chart targets and
known risks, and game-local history. **Broader outcome modeling remains open:**
breakaway/QB-time/variable-yardage outcomes, complete penalty-choice valuation,
and defense-adjusted conversion probabilities are not simulated. Their unresolved
probability mass receives neutral coaching value instead of fabricated outcomes
or conditioning it away. The criteria below retain that longer-term goal; this
is not a claim that full-engine outcome analysis has been delivered.

Recent-call state is preserved in CLI game saves, not in cross-game opponent
learning files. Existing browser saved display/replay history is not a promise
of deterministic coaching or restored recent-call state.

Ordinary Hard selection uses a separate namespaced random stream without advancing
gameplay dice. AI-011 extends that isolation to hurry-up selection and its modifier
choices at every difficulty; other special-situation policies retain existing
randomness and precedence. Tests use fixed streams and synthetic/public charts;
no private chart content or historical log is added to the repository.

Original audit evidence: 20 screens among 52 announced AI calls (38.5%), including
12 of 21 first-and-ten calls (57.1%); these include penalty/replayed-down calls.
A post-fix local fixed-stream policy probe interleaved first-and-ten, second-and-eight
and third-and-eight for three different teams, 400 calls per context/team. Largest
individual-play shares ranged from 15.8% to 24.7%; the reported team's first-and-ten
screen share was 13.5%, with its largest first-down play share 19.5%. These are
sampled coaching decisions, not complete games, quality guarantees, or enforced
usage caps. Full-game coverage separately passed in both Hard-mode browser games.

**Goal:** make the AI difficult to predict without erasing team strengths or choosing
poor plays merely for variety. The reported pattern—expecting Screen on first down
and subsequent downs with more than five yards to gain—is a specific regression target,
not a claim that every such call is wrong.

- **Use the full outcome distribution.** Evaluate gains and losses, incompletions,
  interceptions, fumbles, breakaways, QB-time outcomes, and penalty effects rather
  than ranking only ordinary positive-yardage results. Offensive-chart summaries
  precede defensive combination and secondary resolution; they are not final
  conversion probabilities. Derive analysis from supported engine/chart semantics,
  not a second implementation of gameplay rules.
- **Score the situation.** Consider down/distance, field position, score, and time.
  Distinguish useful early-down progress from third-/fourth-down conversion needs
  and late-game scoring/clock objectives. A high probability of gaining something
  does not necessarily make a play suitable for the yards needed.
- **Select weighted alternatives.** Replace repeated winner-only overrides with a
  weighted mix of competitive, situation-appropriate plays. Preserve meaningful
  team preferences; do not require uniform play frequencies or force dominated
  alternatives when only one call is credible.
- **Account for similar situations.** Consider recent calls in comparable
  down/distance contexts, not just consecutive repetitions. Apply a bounded,
  decaying repetition adjustment so alternating between situations cannot conceal
  an otherwise predictable first-down or longer-yardage pattern. Occasional
  consecutive screens remain valid; avoid deterministic rotation or a new
  predictable cooldown. History should belong to the relevant team/game and have
  defined new-game and save/resume handling.
- **Respect the evidence.** The reviewed Quantitative Analysis describes outcome
  probabilities, not historical play-frequency counts, sample sizes, or usage
  quotas. Do not infer seasonal caps or declining chart odds from repeated calls.
  Explicit usage restrictions would require separate authoritative evidence.
  Use each team's own charts; do not generalize the Bills' preferences to the Jets.
- **Keep the opponent honest.** Any defensive-tendency adjustment must use only
  previously observable information, never the human's unrevealed current call.
  Preserve dice odds, base timing, and authoritative play resolution.
- **Test first.** Add failing synthetic/public-2026 regressions before production
  changes. Include a persistent top Screen recommendation, first-down and
  greater-than-five-yard situations interleaved with other contexts, and controls
  where a strong team preference or a uniquely suitable call should remain.
  Evaluate conditional call distributions and repetition across many fixed seeds,
  not one game or an assertion that screens can never repeat. Define justified
  diversity bounds during implementation; use deterministic, non-flaky checks
  that preserve team strengths and situational quality. Verify no cross-game
  history leakage, hidden-defense access, or analysis-time consumption of engine
  gameplay randomness.

### AI-009: Validation

- Added 30 public/synthetic audit regressions. Initial baseline: 14 expected missing-hook/harness failures; 59 existing auto-flow controls passed. Added CLI/report validation before its implementation; no existing test expectations changed for this harness.
- Final core: 4,540 passed, eight existing private-data skips, 74% aggregate coverage. Backend: 185 passed with existing Pydantic deprecation warnings. Frontend: 250 passed, one existing skip. Ruff/build passed with existing configuration/Browserslist warnings.
- Browser: both full Hard-mode games (home/receiving, away/kicking), clean new-game state, and offline guide passed. No retry or assertion changes needed.
- Existing integration: 14-game runner, seven historical reproductions, 224 regular games and all nine playoffs passed; zero playoff ties.
- Clean tracked-files-plus-proposed-additions snapshot: core 4,523 passed/25 existing private-data skips, backend 185 passed, and public audit 32/32 passed. Ignored local charts/reports were not copied.
- Full audit: 32/32 public and 448/448 local games passed, including balanced comparisons; every selected call reconciles with the situation aggregates. A further 20-game public Hard-vs-Medium batch passed. Reports stay ignored under `.ai-audits/`; no standings persisted. The one balanced-policy warning remains observational, not a new correctness blocker or proof of Hard decision quality.
- Documentation: canonical developer audit guide and index updated. This is a developer-only topic, so player/offline-guide navigation and packaging do not need additions.

### AI-010 / AI-011: Validation and Limitations

- Test-first baseline: 57 intended accounting/hurry-up failures and 19 passing controls after fixing the new terminal-priority control to patch the not-yet-existing preview method. Fixtures use only synthetic/public teams. Four further audit regressions first failed because hurry-up probabilities were absent.
- Focused core integration: 403 passed, two existing skips. Browser API: six new home/away punt/FG/spike controls passed through the shared tracker.
- Changed prior expectations explicitly: hurry-up no longer bypasses Hard chart/history selection; the ordinary-only audit-weight assertion now applies only to ordinary calls because hurry-up weights are also reported. The existing under-one-minute run-share check keeps its <25% bound but now uses a fixed 2,000-call stream rather than 20 unseeded samples, and requires some runs. No dice/ranking assertions or skips were weakened.
- Full regression caught a genuine baseline mismatch after moving hurry-up RNG off gameplay dice: the audit forced a different balanced stream than plain auto. Kept the existing seeded-equivalence assertion and fixed the testing harness to retain production lazy stream initialization for balanced comparisons. Configured difficulty runs still use independent team streams.
- An additional failing synthetic regression verifies that an eight-point deficit needs greater urgency when season rules disable two-point conversions. Urgency reads that authoritative configuration rather than assuming every era permits eight-point scores.
- Same-chart synthetic first-and-ten, down 14: passing selection weight rises from 63.9% at 15 minutes to 78.7% at four minutes and 98.7% at 30 seconds; all nine calls remain credible. These are a controlled policy probe, not historical usage quotas or outcome probabilities.
- Full generated-season validation exposed SPIKE-003, a distinct period-finalization defect when the spike—not the completion—uses the last seconds. The initial run stopped at 223/224 and correctly did not run playoffs. Eight synthetic cases failed before the narrow engine fix; 282 focused AI/audit/spike tests then passed. Final rerun: all 224 regular games and nine playoffs passed (zero playoff ties), along with the 14-game runner and seven historical reproductions.
- Final core: 4,638 passed/eight existing private-data skips, 74% coverage. Backend: 191 passed. Frontend: 250 passed/one existing skip; build, Ruff, documentation tests, and guide/API checks passed. Existing Pydantic deprecation, Ruff configuration, and outdated Browserslist warnings remain.
- Clean tracked-files-plus-proposed-additions snapshot: core 4,621 passed/25 existing private-data skips, backend 191 passed, public audit 32/32 passed. No ignored private charts, local reports, or standings copied.
- Final audit: public 32/32 and local 448/448 passed, including balanced comparisons; every call/probability/situation total reconciled. No Hard ordinary-group warning. One balanced very-long-third-down group met the advisory threshold; it samples only three alternatives, so retain this as monitoring rather than a universal frequency cap. Reports remain ignored/local.
- A browser rerun reproduced the already tracked VAL-001 navigation/context failure; offline help passed. A subsequent isolated full suite passed both complete real-engine games and offline help (2 tests, 57.6 seconds), with no retry configuration, assertions, or skips changed. This is not a claimed root-cause fix.
- Updated canonical AI/audit/clock guides and this tracker. Existing offline-guide pages/navigation and packaging lists remain unchanged; the offline browser guide check passed.
- Broader outcome modeling, third-and-long eligibility (AI-012), incomplete trace metadata, and agreed spike/down/defensive-timeout fixes remain separate open work. No private charts or narrative logs are committed.

## Validation Blockers

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| VAL-001 | Medium | Full-game browser regression lost its execution context during navigation. | Monitoring | First run during AUD-001 validation: full-game test failed, offline-guide test passed. Trace showed Vite losing its server connection and reconnecting immediately before a page reload; the cause of that disconnect is not established. An isolated full-suite rerun passed both complete real-engine games and offline help (2 tests, 58.7 seconds), with no assertion changes or skips added. The validation blocker is cleared, but this is not a claimed root-cause fix. Core/backend/frontend unit suites, build, lint, clean-snapshot tests, 14-game runner, 224-game season, nine playoff games, and seven historical reproductions also passed. |

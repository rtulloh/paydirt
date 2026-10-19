# Developer Issue Tracker

**Developer-only working record, not a player guide or a release promise.**

Last reviewed: 2026-10-19. See the [developer-note disclaimer](README.md).
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

An earlier local full-game audit reconciled score, quarter totals, first downs, scrimmage
yardage, turnovers, sacks, and penalty totals; its apparent penalty discrepancy was
explained by a recorded punt-return foul. A subsequent audit found a **different**,
confirmed punt double-foul accounting defect (STAT-001 below); do not conflate them.

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| AUD-001 | High | Fourth-down offsetting penalties incorrectly announce turnover on downs despite replaying the down and retaining possession. Accepted replay-down penalties can produce the same false banner. | Resolved | Fix committed together with this tracker entry; see this file's Git history for the commit. Added engine-owned `PlayOutcome.turnover_on_downs`; actual-result displays and both CLI loops now consume it. Added 76 synthetic/public-fixture cases, including genuine failures, conversions, fumbles, special plays, and new/resumed games. Initial baseline: 29 expected failures, 33 passing controls. Current core: 4,381 passed, 8 existing skips; clean snapshot: 4,364 passed, 25 existing private-data skips. Full browser validation passed on an isolated rerun, including both full games and offline help; initial failure remains disclosed under VAL-001. No release contains this fix yet. |
| AI-001 | Medium | CPU accepts a five-yard automatic-first-down penalty instead of an eleven-yard gain that also earns a first down. | Open | Compare resulting field position and down/distance, rather than automatically preferring an automatic-first-down flag. The latest local audit reconfirmed this choice; use synthetic fixtures for the regression. |
| AI-002 | Medium | On an incomplete first-down pass, CPU declines a 15-yard offensive penalty: second-and-ten instead of first-and-25. | Open | Current defensive choice uses positive play yardage as its acceptance test. Evaluate the resulting situations and relevant clock context; do not declare every declined penalty illegal or require automatic acceptance in every situation. |
| AUD-002 | Low | Non-touchdown breakaway commentary claims nobody will catch the runner. | Implemented, uncommitted | Non-scoring breakaways use yardage-aware big-run templates; scoring breakaways retain scoring commentary. Every applicable template has deterministic controls. |
| AUD-003 | Low | QB-kneel commentary credits a running back and describes an ordinary tackled loss. | Implemented, uncommitted | CLI and shared web formatter use the engine kneel description. Synthetic/public tests cover normal kneels, safety and fourth-down controls, yardage, time, down, and no dice rolls. |
| AUD-004 | Low | Goal-to-go headers repeat the position separator, such as a goal-distance marker followed by a second `@`. | Implemented, uncommitted | CLI consumes core `get_status()` down/position descriptions in compact/full views, including goal-to-go beyond ten yards and non-goal controls. |
| AUD-005 | Low | Offensive fumble-advance commentary exposes internal positions, conflates recovery/advance rolls and chart/actual yards, repeats touchdown announcements, and duplicates the defensive-call confirmation. | Implemented, uncommitted | Engine descriptions use team-relative recovery spots and explicitly distinguish recovery roll, advance roll, chart result, and actual advance. CLI displays the engine action explanation without repeating its scoring narrative; transaction traces preserve the raw advance chart cell. New/resumed games confirm the named defense once. Synthetic/public-only baseline: 52 expected wording/display failures and six passing gameplay controls, plus two failing raw-trace cases before that addition. No scoring, dice, timing, possession, AI, or defensive-row-capture changes. Validation recorded below. |
| AUD-006 | Low | CLI repeats touchdowns/first downs, made field goals, defensive fumble scores, safeties, and fourth-down kneel announcements. | Implemented, uncommitted | Keep one canonical scoring narrative or one result marker/banner, not both; preserve technical chart evidence. Synthetic tests cover compact/legacy/full paths, both possession directions, penalty first downs, defensive returns, and offensive fumble-advance safeties. |
| AUD-007 | Medium | Rendering colorful commentary advances the same global random stream as dice/coaching; display frequency can change later outcomes. | Implemented, uncommitted | Colorful commentary and its roster selections use a dedicated narration RNG. Default core roster methods retain global seeded behavior. CLI and shared web formatter rendering are covered by noninterference regressions. Old display-dependent interactive seeded trajectories intentionally change. |
| AUD-008 | Medium | Full interception-TD output can name the original offense as scorer because the engine omits result scoring-team metadata. | Implemented, uncommitted | Both interception touchdown branches now provide authoritative scoring-team metadata. Full output uses that team in its single pick-six announcement; scoreboard/possession rules unchanged. |
| STAT-001 | Medium | Enforced 15-yard punt double-foul penalty moves the ball but is absent from penalty count/yardage stats. | Open | Confirmed with synthetic public charts: the early-return path changes possession/spot without recording the enforced penalty. Fix with test-first accounting regressions separately; enforcement-rule interpretation is not validated by this finding. |
| AI-013 | Medium | Fourth-and-one midfield choice ignores a large late lead. | Open | Short-yardage branch automatically goes for it; evaluate lead/clock/risk separately from this presentation repair. Conversion success is not validation of the decision process. |
| AI-014 | High | CPU preserves an opponent touchdown instead of accepting an eligible offensive foul that erases it. | Implemented, uncommitted | Scorer-aware choices precede generic turnover/special-teams handling. Core pending outcomes identify ordinary/QT/breakaway gains crossing the goal line. Inverse offensive/defensive-score controls and real enforcement verify score, down/distance, penalty accounting and no reroll. |
| STAT-002 | Medium | Successful PAT is allocated to the live next quarter instead of the touchdown quarter. | Implemented, uncommitted | Try logging reuses the preceding TD period without rewinding live clock/quarter or changing save schema. Boundaries, failed tries, untimed downs, OT/no-try, and public save/resume controls; two-point logging is covered separately from full conversion mechanics. |
| AUD-009 | Medium | QB-time rushing touchdown is described as a completed pass to a receiver. | Implemented, uncommitted | Canonical scoring narrative follows the resolved QB scramble. Rushing classification stays unchanged; the prior core receiver-selection RNG draw is preserved deliberately for seeded compatibility. CLI and shared web formatter consume the corrected description. |
| AUD-010 | Low | Ordinary offensive fumble recovery describes pre-fumble gain as an extra post-recovery advance. | Implemented, uncommitted | Core action explanation separates pre-fumble yards, recovery at spot, and net result; real advance-roll controls remain unchanged. |
| AUD-011 | Low | Complete new/resumed CLI loops repeat the actual turnover-on-downs announcement. | Implemented, uncommitted | Final display owns the announcement; strengthened existing full-loop tests require exactly one, with accepted/offsetting/declined penalty controls. Distinct from AUD-001 false announcements. |
| AUD-012 | Low | Pass interference repeats the achieved first-down wording. | Implemented, uncommitted | Display recognizes the engine explanation already contains first-down wording; state flags and automatic-first-down semantics remain intact. |
| AUD-013 | Low | Incomplete result/menu labels say No gain, obscuring the actual pass result. | Implemented, uncommitted | Compact/full/menu output labels incompletions explicitly; genuine zero-yard plays remain No gain. A synthetic offense 9 plus defense BLACK resolves incomplete through real priority/penalty rules; charts are unchanged. |

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
| TRACE-007 | Medium | The `PlayTransaction`/`PlayEvent` model (`paydirt/play_events.py`) does not deliver its stated purpose and is now a third, less complete copy of play state. Populated only by `_apply_play_result`; `run_play`, punts, kickoffs, field goals, tries, and offsetting/accepted penalties leave it `None`. Only 7 of 26 event types are ever emitted; `PendingDecision`/conditional events, `create_penalty_event`, `create_safety_event`, and `paydirt/transaction_display.py` have no production callers. The resolver's transaction, the only one holding the real dice breakdown and defensive row, is discarded and rebuilt with `"Roll N"`/`D:?` (the source of TRACE-002). Consumed only by the CLI compact branch; absent from the web API, frontend, saves, and audit JSON. The compact branch still builds its dice line from regexes and a priority-chart recomputation, and it has display defects the legacy branch lacks: end-zone interceptions render without a turnover marker (touchback) or as an offensive score (pick-six); fabricated `Ret:0→0` rolls; uncapped fumble spot `F@104` versus `99`; `FUMBLE_RETURN` events never carry `is_touchdown`. Thirteen tests force `transaction=None` to keep both display paths first-class. | Investigating | Read-only review 2026-10-19 with synthetic reproductions. Decision needed between two options, both test-first: (A) complete it — carry one transaction per play from resolver through application, add interception-before-early-return, scoring, penalty-reroll, QT/breakaway, kick, and clock events, serialize it in the API/audit output, then remove the CLI/backend regexes (medium-large; prerequisite for TRACE-005); or (B) retire it — promote the few fields only it carries onto `PlayResult`/`PlayOutcome` (offense/defense dice descriptions and row, return-roll descriptions, `int_touchback`, public FG distance), point compact output at those fields, delete `play_events.py`, `transaction_display.py`, `PenaltyChoice.transaction`, and `PlayOutcome.transaction`, and fold the seven engine-produced-transaction assertions into field assertions (small-medium, low risk; the legacy branch already renders the failing cases correctly). Recommendation: B unless TRACE-005 replay is scheduled. Fixes AUD-018, TRACE-001, and TRACE-002 should follow the chosen direction rather than patching both paths. |

## Agreed Spike Follow-ups

Player-facing explanation and pending-implementation warning: [Clock management](../clock-management.md#spike-modifier-and-combinations).
These rules are agreed project behavior, not a claim that the engine changes have shipped.

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| SPIKE-001 | High | The `S` modifier adjusts time without charging the agreed additional down. | Open | For `7S` called on first down, an applied completion-plus-spike must leave third down, including when the pass earns a first down. An incompletion needs no spike and leaves second down. Resolve penalties before determining the spike effect. Add explicit tests for the agreed first-down-gain exception; do not substitute conventional football assumptions. |
| SPIKE-002 | Medium | Offense `7S` is processed before a defensive `AT`, so execution order blocks the agreed defensive-timeout priority. | Open | Resolve penalty decisions, then an applicable defensive timeout, then any remaining spike request. Charge a useful available defensive timeout, cancel the planned spike, and charge no spike-related down. An unavailable timeout cannot cancel the spike; incompletions charge neither. Log the winning procedure. |
| SPIKE-003 | High | A completion could leave time, then its spike reduce the clock to zero without processing period/game expiration. | Resolved | v1.8.1: exposed by generated-season validation, then fixed with eight failing synthetic home/away direct/integrated regressions plus clock-preserved, tied-game, and untimed-down controls. Newly expired spike clocks delegate to existing `_use_time(0)` period/OT handling. No base timing, spike down charging, or defensive-timeout arbitration changes; SPIKE-001/002 remain open. Final 224-game season and nine playoffs passed. |

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
| AI-008 | Medium | Hard can become predictable by overconcentrating on any top chart recommendation. Pre–Week 6 priority. | Resolved | v1.8.1: weighted competitive calls across all nine primary plays replace the 40% winner override on ordinary downs, with down/distance targets, known-risk/full-dice-mass scoring, and bounded decaying repetition adjustments. Engine-owned call history excludes previews, counts rerolls once, and survives CLI save/resume. B/QT cannot be primary recommendations. Added 129 core and two backend regressions; expanded pre-fix baseline was 101 expected failures and eight passing controls. Eight existing dice-weighting parameter cases assert weighted preference rather than the obsolete forced winner; dice/ranking assertions remain. Full validation and broader outcome-modeling limitations are recorded below. |
| AI-009 | Medium | Existing balanced auto/season checks do not exercise Hard-vs-Hard or expose structured play-balance evidence. | Resolved | v1.8.1: testing-only `tests/run_ai_audit.py` reuses the complete production auto-game loop with optional configuration/observation hooks. Supports single/repeated/generated-season modes, asymmetric difficulty, reproducible streams, balanced comparisons, finalized outcomes, JSON/CSV, concentration and comparable-situation streak evidence. Normal auto defaults unchanged; no standings or cross-game learning persistence. Mandatory regression includes public/local audits and evidence review. Final 32 public and 448 local games complete with reconciled totals; no Hard ordinary-group warning and one balanced very-long-third-down advisory warning. Reports remain local/ignored, never private chart/log exports. Validation below. |
| AI-010 | Medium | Opponent learning treated punts/field goals as runs because a false pass flag overrode action classification. | Resolved | v1.8.1: exact canonical/display/legacy run/pass classification precedes overrides. Kicks, kneels, spikes, unknown calls, and secondary columns leave totals/streaks untouched; sneaks and Hail Mary count as actual choices. Covers new/resumed CLI and browser centrally. Existing aggregate learning cannot be reconstructed retroactively. Synthetic 32 runs + 26 passes + two punts + FG correctly reports 58, not 61. |
| AI-011 | Medium | A two-score Q4 deficit triggered a whole-quarter deep-pass-only hurry-up branch, bypassing down/distance and recent-call safeguards. | Resolved | v1.8.1: no-huddle pace is separate from gradual clock/deficit passing preference. Hard shares chart/history eligibility and weights; Easy/Medium use situational weights. Credible runs retain positive weight even late, with no pass quota. Endgame/fourth-down priorities and compact-field route restrictions remain. Urgency respects season two-point-conversion availability; audits include hurry-up probabilities. No engine rules, dice odds, or base timing changes. Validation below. |
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


### AUD-005: Commentary Repair Validation

- Added 60 self-contained cases using only public 2026 charts and synthetic cells.
  The original 58-case baseline had 52 intended failures and six passing controls;
  two additional raw-trace cases failed before their presentation fix.
- Covered home/away offense, recovery rolls 17–19, direct/procedure/declined-penalty
  resolution, transaction/legacy compact and full displays, non-scoring and
  defensive recoveries, and new/resumed defensive prompts on third/fourth down.
- Core suite: **4,698 passed, eight existing private-data skips**, 74% coverage.
  Backend: **191 passed** (41 existing Pydantic deprecation warnings). Frontend:
  **250 passed, one existing skip**. Ruff, production frontend build, documentation
  check, and both browser checks passed, including two complete real-engine games
  and the offline guide (59.8 seconds). Existing Ruff configuration/Browserslist
  warnings remain. No existing test expectations were changed.
- Player guidance updated in `docs/playing.md`; no guide page/navigation or packaging
  list changes were required. No gameplay rules, scores, yardage, RNG consumption,
  timing, or possession changes. Raw chart cells remain distinct from goal-line-
  capped actual advances; unknown defensive-row capture remains TRACE-002.
- This repair is **uncommitted and not included in v1.8.1**. No push was requested;
  rerun the mandatory complete pre-push checklist before publishing it.


### AUD-003 / AUD-004 / AUD-006–008: Presentation Audit

- New public/synthetic presentation matrix covers both possession directions; direct
  and penalty-procedure resolution; compact transaction, legacy compact, full CLI,
  and shared web formatting where applicable. Checks include authoritative scorers,
  goal-line-capped yards, state/outcome immutability, normal/goal status, kneels,
  penalty first downs, safeties, interceptions, defensive fumbles, and field goals.
- Initial baseline: 76 new expected failures with all 60 prior fumble-clarity cases
  passing. Sixteen additional RNG noninterference cases failed before isolation.
  Extended edge/fumble cases reproduced further duplicates and absent interception
  scoring-team metadata before their fixes. Made-FG baseline: two full-mode failures
  and two compact passing controls. Fixture mistakes were corrected before treating
  a failure as evidence (the FG resolver owns its roll, not the engine wrapper).
- Added seeded real-drive comparisons: one/two renderings per play in each display
  mode and the shared formatter must match a non-rendered drive, including final
  gameplay RNG state. A separate regression preserves default core roster selection
  and RNG consumption. Narration templates use a separate stream, not global-state
  swapping; no clock, scoring, possession, probabilities, or AI-policy changes.
- An initial over-broad RNG isolation also affected core scoring-name selection;
  regression found it and the implementation was narrowed to UI narration only.
  Old display-dependent interactive trajectories intentionally still change. The
  first browser run lacked its required human penalty-decision event; the full
  rerun passed after core roster RNG compatibility was restored. No browser assertion
  was removed or relaxed, and this was not classified as the VAL-001 navigation flake.
- **Existing presentation expectation changes (three tests):** compact defensive
  returns now require the existing `SCOOP AND SCORE` announcement instead of also
  demanding `RETURNED FOR TD`; full defensive returns credit the same defense in
  their single fumble-return announcement instead of a second generic TD banner;
  full end-zone recoveries require the same authoritative engine sentence as compact
  output, plus exactly one TD, instead of requiring a redundant generic TD banner.
  Scorer, no-fake-return, real dice, and scoreboard assertions remain.
- **Seeded integration expectation changes:** retain all seven prior complete games.
  Seeds 19831104/19831623 no longer require the untimed event that their old shared
  display-RNG trajectories produced. Mandatory same-matchup supplements 19831107
  and 19831624 exercise real untimed downs with unchanged dice/rules. There are now
  nine reproductions and still two required extension cases. Synthetic runner tests
  update 7-game counts/failure totals to 9 and independently require each new event;
  no private data is loaded by those unit tests. Full 224-game season and nine-game
  playoff validation passed, including all nine reproductions.
- Audit follow-ups remain explicit: STAT-001 penalty accounting, AI-013 large-lead
  fourth-down coaching, existing AI-002 penalty choices, AUD-002 non-scoring
  breakaway wording, and missing TRACE fields. These were not silently folded into
  this presentation repair. Private charts/logs/audit reports remain ignored.
- Documentation updated in `docs/playing.md`; the additive core status field is
  `down_description`. Guide page/navigation/packaging lists are unchanged.
- Repair remains uncommitted and is not part of the published v1.8.1 release.

#### Final Validation Evidence

- Core: **4,867 passed, eight existing skips; 75% coverage**. Backend: **191 passed**.
  Frontend: **250 passed, one existing skip**; production build passed. Both browser
  checks passed, including home/receiving and away/kicking full games and offline help.
  Ruff, documentation tests and whitespace checks passed.
- No-private-data tracked-source snapshot plus the three new regression files:
  **4,850 passed, 25 pre-existing data-dependent skips**; backend **191 passed**.
  The extra 17 skips expose existing historical-fixture test debt, not added skip
  guards or missing new fixtures. New regressions use only synthetic/public teams.
- Integration: all 14 standalone games, nine historical reproductions, 224 generated
  regular games, and nine playoff games passed; no tied playoff final.
- AI audit: public **32/32 games, 3,812 calls** and local **448/448 games, 52,665 calls**.
  Call records reconcile with audit totals. Reviewed team/down/distance/mode groups,
  distinct calls and comparable streaks; checked 22,772 recorded probability vectors
  for finite normalized values. No Hard concentration warnings. Among non-small
  ordinary groups, largest Hard call share was 28.9% public / 46.9% local; longest
  comparable streak was three / five. These are observations, not policy caps.
- One local legacy-balanced advisory remains on third-and-11+ (32 calls); it is a
  chart-strength/alternative-review follow-up, not a reason to weaken assertions or
  change policy in this repair. No private team charts or narrative logs exported.
- Final fumble-safety cross-check added six expected baseline failures: offensive
  recovery advances into their own end zone repeated SAFETY in all three CLI views.
  The authoritative action explanation now owns that announcement; the full text,
  two real resolution rolls and defensive two-point scoreboard remain asserted.
- Existing warnings remain: Pydantic `.dict()` deprecation, Ruff configuration
  deprecation, stale Browserslist data. No commits, pushes, tags or releases made.

## Latest Eight-Finding Audit Repair

AI-014, STAT-002, AUD-002, and AUD-009–013 are implemented locally, not released.
See the [validation record](game-audit-validation.md) for failing baselines, every
changed prior expectation, full regression results, checker false alarms, explicit
event coverage, three concentration advisories, and limitations. Earlier validation
sections remain historical evidence and are not the latest worktree totals.


## Full Code Review 2026-10-19 (f7bab92 through the current worktree)

Independent read-only review of every production change since `f7bab92` plus the
uncommitted worktree, covering gameplay rules, statistics, messages, flow, AI,
persistence, CI, and documentation. **Reproduced** means a real-engine or API
reproduction was executed; **code-read** means established by reading code only
and still requires a failing regression before any fix. Work the High items first,
in the listed order, following the AGENTS.md test-first workflow; none of these
findings is fixed yet. Recurring causes: the conversion path reuses the live-play
engine; parallel implementations drift (`run_play`/`_apply_play_result`,
`run_interactive_game`/`resume_game`, CLI versus web flow); and tests mock the
exact boundary where the defect lives. `auto_game` already has the correct
half-ending and final-try behavior, so season/audit runs cannot catch the CLI/web
variants.

### Priority order for High items

1. FLOW-003 (web pending-penalty touchdown setup) — implemented 2026-10-19 (`072875a`).
2. FLOW-001, RULE-002, FLOW-002 (end-of-period TD/safety flow) — implemented 2026-10-19 in one change set; see rows. Validation: core 5,137 passed/8 existing skips (75%); backend 209; frontend 250/1 existing skip; build; both browser games; Ruff; docs; 14-game runner; nine historical reproductions; 224/224 generated games and 9/9 playoffs (no tied final); public 32/32 and local 448/448 audits reconciled (three existing advisories); tracked-source snapshot 5,120 core/25 existing skips and 209 backend. Expected trajectory change: the generated CLI season now reports 19 OT games and 2 regular-season ties (previously 16 and 0) because half-ending scores no longer double-kick and final tries are played; regular-season ties are valid under 1983 rules.
3. RULE-001 (two-point tries resolved as live plays) — unreachable under 1983 rules; required before any 2026 play-test.
4. FLOW-004 (frontend pending-PAT fallback crash) — include a Vitest case that a pending-penalty response for a goal-line play routes to the penalty UI, not the PAT choice.
5. VAL-002 and VAL-003 (CI enforcement; untracked private standings file).
6. RULE-003 — re-scoped to Medium (defense charts never carry penalties); see its row for the work plan.

### Rules and scoring engine

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| RULE-001 | High | Two-point tries run through `run_play`: a successful try scores a TD (+6) and +2, logs two TDs, consumes 25–45 s (a Q2 try rolled into Q3 15:00), credits rushing yards/first down/play log/call history; a pick-six on the try awards the defense 6 and credits the Def 2PT to the wrong team; a plain interception leaves possession flipped, so the web kickoff picks the wrong kicker. | Open (reproduced) | Every existing two-point test mocks `run_play`. Add unmocked regressions first: +2 only, one scoring entry, clock/stats/history untouched, possession restored, correct Def 2PT team. Resolve the try in a conversion mode without scoring/clock/stat side effects. |
| RULE-002 | High | A TD at 0:00 of regulation that left the scores unequal set `game_over` before the try; CLI (`while outcome.touchdown and not game_over`) and web (`is_pending_pat`) skipped the PAT/2PT, and `attempt_two_point` raised "Game is over". Only `auto_game` consulted `can_attempt_conversion_after_touchdown`. | Implemented, uncommitted | Test-first with FLOW-001/002 (37 failing, 17 passing controls across the full-loop CLI and engine files; 4 failing backend API cases). CLI and web now gate the try on the engine query; `attempt_two_point` runs under a conversion-in-progress flag and both try methods share `_recompute_game_over_after_try`. Covered: trailing by 7 → PAT → tie → OT or miss → final; leading → PAT still kicked; 1983 rules offer PAT only; OT-winning TD has no try; web `pending_pat` at 0:00 with the PAT endpoint completing the game. One assertion deliberately narrowed: the two-point-at-expiry test checks availability and the recomputed game-over flag only, because the point total is RULE-001's defect (the try still scores 8 until that fix). |
| RULE-003 | Medium | Originally reported as: when the defense chart shows `DEF n` and the offense rolled `B`, `QT`, `BLACK`, `TD`, `F`, or `I n`, the priority step returns bare yards and accept-play applies `offense_yards` (0 for symbolic cells), so a breakaway becomes no gain and `I 15` becomes a 15-yard offensive gain. **Re-scoped 2026-10-19:** defense charts never contain penalties. All 30 local `defense.csv` files (28 × 1983, 2 × 2026) have zero `OFF`/`DEF`/`PI` cells; penalties exist only on offense charts and special-teams columns (Punt, Field Goal, Int./Punt/Kickoff Return, Kickoff), and the priority reference lists `DEF/OFF/PI` only as an offensive row. The reproduction and the earlier semantic tests used an impossible chart (`defense.modifiers = {..: "DEF 5"}`). The offense-chart path (`DEF 5` cell → reroll `TD`) already resolves correctly (FLOW-003 CPU-offense test). | Open (re-scoped) | Work plan when picked up, test-first: (1) Re-verify on the real resolver that an offense-chart `DEF n`/`OFF n` reroll into `B`, `QT`, `INT`, `F`, `BLACK`, or `TD` keeps the real result type and secondary rolls for accept-play, the CPU valuation, the CLI/web previews, and `projected_touchdown`; if any consumer still reads `offense_yards`/`play_result.yards` for those cases, that is the remaining defect. (2) Delete the dead `def_cat == PENALTY` branch in `apply_priority_chart` and the `defense_modifier.startswith("DEF")` projection branch in `run_play_with_penalty_procedure` (both committed-era code paths for charts that cannot exist), or convert them to an explicit error. (3) Add a chart-loader validation (and `extract_charts.py` check) that rejects penalty cells on defense charts so synthetic tests cannot depend on them. (4) Rewrite `paydirt-web/backend/tests/test_pending_penalty_scoring.py::test_human_offense_goal_crossing_gain_with_defensive_flag` and any `tests/test_audit_*` cases that build defensive-chart penalties to use an offense-chart `DEF 5` → numeric/symbolic reroll instead; keep home/away coverage. (5) Close AUD-014 with the same change or re-scope it to the offense-chart preview. Not reachable in 1983 or 2026 play; no longer a play-test blocker. |
| RULE-004 | Medium | `run_play` and `_apply_play_result` disagree on the −5 designation (floor at 0 vs negative), sack distance (`yards_to_go` not updated), and interception `yards_gained`. `run_play` still serves tries, `simulate_week`, `game.py`, and `cli_charts`. | Open (code-read) | Delegate the scrimmage branch of `run_play` to `_apply_play_result` or align the three rules with tests on identical inputs. |
| RULE-005 | Medium | `apply_fg_penalty_decision` extends the half for an accepted offensive foul (`time_remaining <= 0.5` heuristic) but not for a defensive one, and FG offsetting omits `defensive_penalty=True`; inverse of the untimed-down rule used elsewhere. | Open (code-read) | Drop the OFF extension, pass `defensive_penalty` to `_use_time`, then `check_untimed_down_for_defensive_penalty`. |
| RULE-006 | Medium | Offensive `T`/`S` modifiers are dropped whenever a penalty decision intervenes; `apply_penalty_decision` cannot re-apply them, contrary to the documented order (decision, timeout, spike). | Open (reproduced) | `7T` with a flag and accepted play: no timeout, full play time charged. Persist the requests and pre-snap clock/timeout snapshot on the pending outcome and apply them after an accepted play. Related to SPIKE-002. |
| RULE-007 | Medium | Uncommitted `_log_score` try attribution relies on `scoring_plays[-1]` being the TD; with RULE-001 unfixed a 2PT attaches to the spurious TD, and the try keeps the live clock time. | Open (code-read) | Fix with RULE-001; pass the TD scoring entry/quarter explicitly from the try methods. |
| RULE-008 | Low | Spikes, kneels, and fourth-down offensive fumble recoveries that exhaust downs set `turnover=True` as well as `turnover_on_downs`, contrary to the documented separation; UI shows a turnover marker. | Open (code-read) | Set `turnover=False, turnover_on_downs=True` on all downs-exhausted paths; keep statistical turnovers unchanged. |
| RULE-009 | Low | In `run_play`, a +3 QB scramble with a −5 designation becomes −2 and is classified as a sack. | Open (code-read) | Classify sacks from the chart result, not designation-adjusted yards. |

### Game flow (CLI and web)

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| FLOW-001 | High | After a half-ending TD the CLI passed the current quarter to `can_kickoff_after_play`, so the scoring team kicked off and the loop then ran the second-half kickoff too. | Implemented, uncommitted | Engine now records the start period of every scoring-capable action (`run_play`, penalty procedure, kickoff/onside, safety free kick; tries preserve it) and `can_kickoff_after_play()` / `should_kickoff_after_score()` default to it; explicit arguments still work. `_complete_touchdown_sequence` uses the engine default. Full-loop CLI regressions (new/resumed × home/away) require exactly one kick after a Q2-expiring TD — the scheduled second-half kickoff by the opening receiver — with Q1/Q3-expiry and time-remaining controls; engine tests cover each entry point including half-expiring kick-return scores. |
| FLOW-002 | High | Both CLI loops free-kicked after a half-ending safety (burning Q3 clock and flipping possession), then kicked off again at halftime; `auto_game` already checked `should_kickoff_after_score`. | Implemented, uncommitted | Both loops now ask `should_kickoff_after_score()` before the free kick. Full-loop regressions: Q2-expiring safety → no free kick, halftime kickoff only, clock/possession intact; Q1-expiry and time-remaining controls still free-kick from the 20. |
| FLOW-003 | High | Web `execute_play` called `setup_for_pat()` and set `pending_pat` from `result.touchdown` without checking `pending_penalty_decision`; the provisional touchdown flag widened this to goal-crossing yardage with a flag. Ball moved to the 98 before the choice: penalty enforced from the 98, accepted play credited as a 2-yard TD. The penalty endpoint also overrode `touchdown`/ball position after decisions. | Implemented, uncommitted | Test-first: 12 failing backend API cases (human offense/defense deciding, CPU deciding, home/away) plus 20 failing core cases; two API controls passed. Pending outcomes now keep `touchdown=False` and expose `PlayOutcome.projected_touchdown` for CPU/oracle use; one backend helper arms PAT/kickoff state only for finalized outcomes in `execute_play` (both paths) and the penalty endpoint; the spot-based touchdown override is removed. Changed prior expectation: `test_cpu_scoring_choice_has_real_engine_consequences` asserted the pending `touchdown` flag that encoded the defect; it now asserts `touchdown is False` and `projected_touchdown`. A CPU-offense defensive-chart `TD` scenario exposed RULE-003 instead and is deferred to it. Validation recorded in the commit. |
| FLOW-004 | High | `checkPendingPat` fallback references the deleted `isHomeScoring`; a missing/null `player_offense` throws `ReferenceError` in the TD flow. | Open (reproduced) | Remove the fallback (engine flag is authoritative) and add a unit test. |
| FLOW-005 | Medium | Second-half kicker is guessed from current possession in `resume_game` ("Approximate") and in the web kickoff endpoint; the engine never records the opening kicker. | Open (code-read) | Track the opening kicker in `GameState`/saves and expose an engine query; all UIs consume it. |
| FLOW-006 | Medium | `resume_game` scores a "pending" TD/safety from the UI (+6/+2, generic "Touchdown" entry, CPU auto-kick). The engine scores at play time, so a save with the ball at the goal line already includes the points; the path would double-count. Currently latent in the CLI. | Open (code-read) | Replace with an engine-owned completion method or remove; align with the web `load_replay` behavior. |
| FLOW-007 | Medium | `resume_game` never passes the human/CPU spike modifier and prints no skipped-modifier messages; other divergences from the new-game loop: OT banner, safety punt option, CPU offensive-timeout helper, hard-coded quarter advance with `time_remaining = 15.0`. | Open (code-read) | Extract one shared per-down routine used by both loops; regression matrix across new/resumed. |
| FLOW-008 | Medium | Web `load_replay` reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession; a TD is inferred from `ball_position >= 100`. | Open (code-read) | Persist authoritative flags with the replay; stop parsing text. |

### Penalty and coaching decisions

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| AI-015 | Medium | CPU receiving team never takes "keep return + yards" on a kicking-team punt foul (always index 0 = decline); the web CPU punt path also drops `penalty_index`. | Open (reproduced) | Select the KEEP option when available; pass the index through the backend. |
| AI-016 | Medium | CPU never acts on kickoff-chart penalties: option labels use the opposite OFF/DEF convention, so the eligibility filter is always empty. | Open (reproduced) | Evaluate the accept/decline pair directly for kickoffs. |
| AI-017 | Medium | Defense accepts a made field goal instead of the offensive foul that would force a longer re-kick. | Open (reproduced) | `accept_play = offended_is_offense` when the kick is good; test both sides. |
| AI-018 | Medium | Penalty valuation compares nominal yards and ignores half-the-distance and first-down equivalence (AI-001 family); AI-002 unchanged. | Open (reproduced) | Compute post-enforcement spot/down/distance per option with `resolve_penalty` and compare to the play's result. |
| AI-019 | Medium | Hard defense bypasses goal-line, red-zone, prevent, two-minute, and fourth-down policies and returns Standard deterministically when protecting a lead late; the new `_late_trailing_defense` docstring claims those behaviors are preserved. | Open (code-read) | Route Hard through situational checks first; use the model only in the standard branch; correct the docstring. |
| AI-020 | Medium | Ordinary-down selection never sets no-huddle even when `_needs_hurry_up` is true (the special-situation branches do). | Open (code-read) | Apply the shared hurry-up check before standard returns. |
| AI-021 | Low | Mixed RNG sources (Medium early-down tilt, fourth-down OOB, coffin corner use global dice RNG); onside/late-defense checks not OT-aware; 9 s vs 10 s Hail-Mary/FG thresholds; `-d Easy` disables the helper (case-sensitive); Q2 ≤1:00 CPU timeout while leading; `TD` rows counted as 100 yards in `avg_yards`; three cell parsers disagree on `12*`. | Open (code-read) | Address individually with synthetic tests; none changes dice odds. |

### Statistics

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| STAT-003 | High | Two-point tries pollute team statistics, play log, and call history (yardage, first downs, turnovers, interception counts). | Open (reproduced) | Fixed by RULE-001; add accounting assertions to its regressions. STAT-001 remains separately open. |

### Messages and presentation

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| AUD-014 | Medium | Penalty-choice preview was reported to show penalty yardage instead of the retained play when the defense chart produced the foul. Defense charts never contain penalties (see RULE-003 re-scope), so the reported trigger cannot occur. | Open (re-scoped) | When RULE-003 is picked up, verify the CLI preview (`handle_penalty_decision`) and the backend `_calculate_post_play_state` for the offense-chart reroll case: the accept-play preview must describe the rerolled result (numeric yards, breakaway/QT secondary roll, interception, incomplete, touchdown), not `play_result.yards`. Replace the UI-side `_calculate_post_play_state` recomputation with an engine-owned retained-play preview if any discrepancy is found. |
| AUD-015 | Medium | Web double FIRST DOWN (`result_formatter` still passes `is_first_down` while the frontend renders its own banner); web TD commentary returns the raw description including the ` \| ` technical trace; headline and description both announce TOUCHDOWN. | Open (code-read) | Pass `is_first_down=False`; use the engine narrative helper in the shared formatter. |
| AUD-016 | Medium | Web play-log team labels and colouring assume the human is home (`PlayingPhase.jsx` offense/defense naming). | Open (code-read) | Derive from `game_state.possession`. |
| AUD-017 | Medium | Duplicate FIRST DOWN on offensive fumble recoveries: engine explanation ends with it and the CLI adds its marker/banner. | Open (code-read) | Suppress the CLI marker when the explanation already announces it; prefer an engine flag over text checks. |
| AUD-018 | Medium | CLI display parses description strings to decide output (first-down marker check, reroll-dice and touchback regexes, punt/FG branches); AGENTS.md anti-pattern. | Open (code-read) | Expose engine flags (`int_touchback`, return reroll metadata, FG distance) and remove the regexes; the `_fg_*` private attributes read by the UI should become public outcome fields. |
| AUD-019 | Low | Defense-recovery fumble text prints raw internal positions; `auto_game` pre-announces spikes, prints "END OF QUARTER 5" on OT1→OT2, and never attempts two; `Defense shows: A` raw letter in resumed CPU prompts; "Incomplete" vs "Incomplete pass"; dead TD commentary templates; "Stuffed at the line" for zero-yard completions; `[DEBUG]` prints on every save; `get_status` re-implements goal-to-go; dice info printed for kicks with different field meanings. | Open (code-read) | Individually small; keep wording changes test-first. |

### Persistence, CI, hygiene, documentation

| ID | Priority | Issue | Status | Resolution / verification |
|----|----------|-------|--------|---------------------------|
| VAL-002 | High | CI never runs the backend pytest suite, Ruff is `continue-on-error` and omits the backend path, and the public AI audit is not in CI; AGENTS.md lists all as required. | Open (reproduced) | Add backend tests, make lint fail the build with the backend path, add the public 2026 audit step. |
| VAL-003 | High | `standings_data.save/season_1983.json` is untracked and not ignored and contains private-season results; `.gitignore` covers only `standings_data/`. | Open (reproduced) | Ignore `standings_data*/` or remove the directory; never commit it. |
| VAL-004 | Medium | Local tag `v1.9.0` points behind the pushed `v1.8.1`; `git push --tags` would build a stale 1.9.0. The uncommitted behavior changes have no version bump or release notes. | Open (reproduced) | Never push the stale tag; next release uses a higher number with notes covering the worktree changes. |
| VAL-005 | Medium | Corrupt `offensive_call_history` in a save aborts `--load` with a traceback instead of the "Failed to load" message. | Open (code-read) | Catch `ValueError` in the CLI loader and print the reason. |
| VAL-006 | Medium | CI matrix includes Python 3.9 while `requires-python >= 3.10` and the audit harness uses 3.10 syntax. | Open (code-read) | Drop 3.9 from the matrix. |
| DOC-001 | Low | `run_full_season.py` comment attributes the changed historical seeds to narration RNG only (the CPU penalty change also alters trajectories); AGENTS.md spike table describes current behavior while `clock-management.md` documents the agreed unimplemented rule; stale "Unreleased" spike section at the bottom of `RELEASE_NOTES.md`; `semantic_audit` oracles are coupled to engine wording and the AI's own eligibility rules; dev-notes README lost a blank line before "Adding Notes". | Open (reproduced) | Documentation-only corrections; run the documentation tests. |

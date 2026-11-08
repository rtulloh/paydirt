# Open-issue reconciliation — November 8, 2026

Follow-up: the [High-priority audit](high-priority-issue-audit-2026-11-08.md)
supersedes the remaining High-ticket dispositions and counts in this earlier
checkpoint. Four more tickets are resolved and four move to Medium; the live
issue index is authoritative.

Developer working record; no gameplay change or release qualification.

Reviewed all 116 initially open records against completed tickets, their recorded
issue-specific evidence, committed source through v1.10.2, and current main.
Sixteen stale open records are closed as already completed; 22 additional
committed fixes are resolved pending confirmation, leaving 78 open.
These are primarily shipped fixes with stale status, not newly discovered fixes.

## Closure evidence

The published verification in [v1.10.2 scope](release-1.10.2-scope.md#published-release-verification)
records correctness CI and publication. Individual tickets retain their earlier
test-first and actual browser/game/campaign evidence; closure comments identify
the narrow completed behavior. A general green workflow does not waive their
unrelated source-fit, policy or historical-model requirements.

Fresh bounded rechecks: 334 core tests, 33 observer cases (2 unrelated cases
deselected), 74 backend tests, and 72 frontend component tests pass. Backend
emits three existing httpx/Pydantic deprecation warnings; frontend emits the
existing stale Browserslist warning. No browser service or full regression was
started for this documentation reconciliation. Final documentation/tracker
validation passes 403 checks; git diff --check also passes.

## Every initially open ticket

| Ticket | Recorded priority | Decision | Reason |
|---|---|---|---|
| [AI-025](issues/AI/AI-025.md) | High | Close: completed | Auto-game observation recording is committed in 8c0bb8b. The November 5 renewed Hard/balanced campaigns completed 7,936 games and reconciled 1,179,571 selected calls after the fix. Current auto-game regressions pass. This closes observation routing, not AI-019 response quality or AI-026 chart awareness. |
| [AI-026](issues/AI/AI-026.md) | High | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-027](issues/AI/AI-027.md) | High | Close: completed | The server-owned CPU plan, clock-option routing, timeout integration and call mappings shipped in 8c0bb8b and remain in v1.10.2. November 6 built-service Chromium and the completed owner game confirm CPU timeout use. Current CPU-clock API regressions pass. Strategic policy quality remains separately open. |
| [AUD-030](issues/AUD/AUD-030.md) | High | Resolve: confirmation pending | Committed report validation reconstructs derived rates; independent fresh campaign/report validation remains pending. |
| [DATA-016](issues/DATA/DATA-016.md) | High | Resolve: confirmation pending | Unrounded-target finite-mass selection and QT/QT* allocation controls are committed; final regenerated play/audit confirmation remains pending. |
| [DATA-017](issues/DATA/DATA-017.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-018](issues/DATA/DATA-018.md) | High | Keep open | The shipped cohorts retain explicitly accepted fit exceptions; publication is not proof these accuracy misses are fixed. DATA-042 and AI-030 separately own pace/scoring and policy-transfer diagnostics. |
| [DATA-019](issues/DATA/DATA-019.md) | High | Close: completed | The corrected QT-fumble observer shipped in 8c0bb8b. The November 5 renewed 31,744-game campaign reconciled every team/league play identity with the corrected counters. Current observer tests pass. This closes the measurement classification defect, not historical chart-fit or source-model acceptance. |
| [DATA-020](issues/DATA/DATA-020.md) | High | Close: completed | The offsetting-penalty observer exclusion shipped in 8c0bb8b. November 5 exact previously failing game replays and the renewed 31,744-game campaign confirm reconciled accounting. Current real-engine/observer regressions pass. Broader nullified fumble-return handling remains under DATA-031. |
| [DATA-021](issues/DATA/DATA-021.md) | High | Close: completed | Follow-up confirms column guards and both adapters are repaired; zero OFF/DEF B/QT cells across all 60 shipped teams, both complete public compatibility audits pass, 15 focused regressions pass. Prior reproduced cohorts and all-team real-engine release evidence cover the repaired artifacts. Broader source-fit requirements remain separate. |
| [DATA-022](issues/DATA/DATA-022.md) | High | Resolve: confirmation pending | Neutral interception-floor correction and low-mass strength ordering are committed; final fit/stress confirmation remains pending, with depth/stripe model limits retained. |
| [DATA-023](issues/DATA/DATA-023.md) | High | Resolve: confirmation pending | Conditional sack/defensive-overlap allocation and shared neutral-pressure preparation are committed; final all-team/held-out/policy validation remains pending. |
| [DATA-024](issues/DATA/DATA-024.md) | High | Resolve: confirmation pending | Conversion exclusion, provenance and coverage guards are committed; final regenerated and independent qualification remain pending. |
| [DATA-025](issues/DATA/DATA-025.md) | High | Resolve: confirmation pending | Initial-gain fitting/parsing guards are committed and unknown required gains fail explicitly; complete source/integrated confirmation remains pending. |
| [DATA-026](issues/DATA/DATA-026.md) | High | Resolve: confirmation pending | Representative midpoint-quantile selection is committed in empirical_adjustment.py; regenerated source/population and independent validation remain pending. |
| [DATA-027](issues/DATA/DATA-027.md) | High | Resolve: confirmation pending | QB-time class preservation is committed and SACK 0 supersedes the temporary minus-one floor; final source/campaign confirmation remains pending. |
| [DATA-028](issues/DATA/DATA-028.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-029](issues/DATA/DATA-029.md) | High | Resolve: confirmation pending | QT-only SACK 0 is committed across source, resolver, engine, observer, generator and audit paths; final source/charter validation remains pending. |
| [DATA-030](issues/DATA/DATA-030.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-031](issues/DATA/DATA-031.md) | High | Resolve: confirmation pending | Replay-down credit guard is committed with natural nullified-fumble campaign evidence; final independent confirmation remains pending. |
| [DATA-032](issues/DATA/DATA-032.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-035](issues/DATA/DATA-035.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-036](issues/DATA/DATA-036.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-038](issues/DATA/DATA-038.md) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [FLOW-013](issues/FLOW/FLOW-013.md) | High | Close: completed | Human defensive timeout controls and engine routing shipped in 8c0bb8b. The recorded November 2 full browser games verify six human defensive timeouts per game, correct home/away ownership, exhausted budgets and keyboard cancellation/reselection. The v1.10.2 hosted 18-browser-check pass includes both real-engine games; current API and component regressions pass. |
| [FLOW-016](issues/FLOW/FLOW-016.md) | High | Resolve: confirmation pending | Engine-owned preview fix exists, but the recorded pending updated-service play-test confirmation has not been located. Mark resolved pending confirmation; do not reimplement the already-shipped projection. |
| [RULE-026](issues/RULE/RULE-026.md) | High | Resolve: confirmation pending | Selected-priority fumble classification is corrected in committed code; required regenerated/full-game/audit confirmation remains pending. |
| [RULE-027](issues/RULE/RULE-027.md) | High | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-029](issues/RULE/RULE-029.md) | High | Resolve: confirmation pending | End-line interception safety and retained-play geometry corrections are committed; issue-specific gameplay confirmation remains pending. |
| [RULE-030](issues/RULE/RULE-030.md) | High | Resolve: confirmation pending | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [STAT-004](issues/STAT/STAT-004.md) | High | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [VAL-009](issues/VAL/VAL-009.md) | High | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-017](issues/VAL/VAL-017.md) | High | Resolve: confirmation pending | Loaded runtime/observer identity checks and display-preference correction are committed; final frozen-candidate integration review remains pending. |
| [VAL-018](issues/VAL/VAL-018.md) | High | Resolve: confirmation pending | Ordered-call, policy/distribution and repetition validation are committed; final complete collection and independent review remain pending. |
| [VAL-019](issues/VAL/VAL-019.md) | High | Keep open | Historical calendars/postseasons are implemented and exercised, but the ticket explicitly retains official tiebreak/neutral-site/full-transition verification. AI-026 separately owns chart-response work. Keep open for that narrower remaining verification; do not implement the calendar runner again. |
| [AI-002](issues/AI/AI-002.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-003](issues/AI/AI-003.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-012](issues/AI/AI-012.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-013](issues/AI/AI-013.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-015](issues/AI/AI-015.md) | Medium | Resolve: confirmation pending | KEEP-option selection and API index routing are committed; independent updated-service play testing remains pending. |
| [AI-016](issues/AI/AI-016.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-017](issues/AI/AI-017.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-018](issues/AI/AI-018.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-019](issues/AI/AI-019.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-020](issues/AI/AI-020.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-023](issues/AI/AI-023.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-024](issues/AI/AI-024.md) | Medium | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [AI-029](issues/AI/AI-029.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-030](issues/AI/AI-030.md) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AUD-014](issues/AUD/AUD-014.md) | Medium | Keep open | Overlaps FLOW-016 previews and RULE-003, but its retained symbolic penalty-reroll/secondary-result checks and dead projection paths are broader than the confirmed numeric/incomplete preview repair. |
| [AUD-015](issues/AUD/AUD-015.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-016](issues/AUD/AUD-016.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-017](issues/AUD/AUD-017.md) | Medium | Keep open | Overlaps the broad AUD-006 display work, but the available general first-down/punt evidence is not a new explicit offensive-fumble first-down play-test confirmation. Retain pending a targeted check. |
| [AUD-018](issues/AUD/AUD-018.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-020](issues/AUD/AUD-020.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-022](issues/AUD/AUD-022.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-028](issues/AUD/AUD-028.md) | Medium | Resolve: confirmation pending | Deterministic equal-weight placement and invariant/review tooling are committed; frozen all-team campaigns and owner review remain pending. |
| [AUD-029](issues/AUD/AUD-029.md) | Medium | Resolve: confirmation pending | Missing-secondary-row audit defaults now preserve the core fallback distribution; actual stable-corpus integration remains pending. |
| [DATA-037](issues/DATA/DATA-037.md) | Medium | Resolve: confirmation pending | Signed defensive F rejection is committed in reference-decoder preflight; complete actual-corpus integration remains pending. |
| [DATA-040](issues/DATA/DATA-040.md) | Medium | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-041](issues/DATA/DATA-041.md) | Medium | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-042](issues/DATA/DATA-042.md) | Medium | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [FLOW-006](issues/FLOW/FLOW-006.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-007](issues/FLOW/FLOW-007.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-008](issues/FLOW/FLOW-008.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-009](issues/FLOW/FLOW-009.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-015](issues/FLOW/FLOW-015.md) | Medium | Resolve: confirmation pending | Clock formatting and preplay-clock attribution are committed; issue-specific half-ending log browser confirmation remains pending. |
| [FLOW-018](issues/FLOW/FLOW-018.md) | Medium | Close: completed | Pending-try eligibility propagation shipped in 8c0bb8b. November 6 real-engine browser success/failure checks cover both human sides, prohibited seasons and final/halftime flow; the owner confirmed the choice was visible. The v1.10.2 hosted two-point browser cases pass, and current conversion API tests pass. |
| [FLOW-021](issues/FLOW/FLOW-021.md) | Medium | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [FLOW-022](issues/FLOW/FLOW-022.md) | Medium | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [RULE-001](issues/RULE/RULE-001.md) | Medium | Close: completed | The isolated untimed conversion implementation shipped in 8c0bb8b. November 6 actual chart/API/browser checks verify +2-only scoring, defensive ownership, no ordinary time/statistics/history changes and restoration on exceptions. v1.10.2 hosted two-point browser checks and current unmocked conversion tests pass. |
| [RULE-003](issues/RULE/RULE-003.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-004](issues/RULE/RULE-004.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-005](issues/RULE/RULE-005.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-006](issues/RULE/RULE-006.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-007](issues/RULE/RULE-007.md) | Medium | Close: completed | Explicit touchdown-entry attribution in both try methods shipped with the conversion repair in 8c0bb8b. November 6 actual API halftime cases verify touchdown period/time attribution for successful, failed and defensive-return tries on both sides. Current conversion regressions pass; this is completed shared work with RULE-001, not another implementation task. |
| [RULE-011](issues/RULE/RULE-011.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-012](issues/RULE/RULE-012.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [SPIKE-004](issues/SPIKE/SPIKE-004.md) | Medium | Close: completed | The standalone three-second clock call shipped in 8c0bb8b. November 6 served HTTP checks verify 90 to 87 seconds, half/game expiration and fourth-down possession changes across 16 cases. Current standalone-spike regressions pass, and later v1.10.2 hosted core/browser qualification is recorded. This does not close unrelated spike/modifier issues. |
| [STAT-001](issues/STAT/STAT-001.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [STAT-003](issues/STAT/STAT-003.md) | Medium | Close: completed | Ordinary-statistics isolation shipped with RULE-001 in 8c0bb8b. November 6 real chart/API/compiled-browser cases confirm no ordinary statistics, play-log or call-history credit for successful, failed, intercepted and fumbled tries. Current unmocked isolation/API tests pass. STAT-001 punt accounting is separate. |
| [TRACE-001](issues/TRACE/TRACE-001.md) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-003](issues/TRACE/TRACE-003.md) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-004](issues/TRACE/TRACE-004.md) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-005](issues/TRACE/TRACE-005.md) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-007](issues/TRACE/TRACE-007.md) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [VAL-001](issues/VAL/VAL-001.md) | Medium | Keep open | A monitoring record, not a demonstrated duplicate root-cause fix: repeated browser passes clear the blocker but do not establish what caused the original reload. Retain monitoring without treating it as a reproduced release failure. |
| [VAL-004](issues/VAL/VAL-004.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-005](issues/VAL/VAL-005.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-006](issues/VAL/VAL-006.md) | Medium | Close: completed | The supported CI matrix is now Python 3.10/3.11/3.12, with the full core run only on 3.10 and compatibility checks on the others; the workflow configuration shipped by d321242. The v1.10.2 exact-source hosted workflow passed all nine jobs. Current workflow regressions pass. No Python 3.9 job remains. |
| [VAL-010](issues/VAL/VAL-010.md) | Medium | Close: completed | The historical-dependent unit cases were replaced with synthetic/public fixtures in the shipped 8c0bb8b integration. Reviewed the originally named commentary, interactive, season-rule and chart test files; historical-looking labels are synthetic metadata, not private file loads. v1.10.2 clean hosted core completed 10,893 tests with no skips. Current targeted core checks pass without skips. Do not confuse intentionally local historical integration runners with unit fixtures. |
| [VAL-013](issues/VAL/VAL-013.md) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-016](issues/VAL/VAL-016.md) | Medium | Close: completed | The API proxy now explicitly targets 127.0.0.1:8000; this shipped in 8c0bb8b. The existing November 5 unchanged browser guide test passed after the correction, including all seven images and HTTP 200 through Vite; later v1.10.2 hosted offline-guide checks pass. This closure is limited to the /api IPv4 proxy defect, not the separate WebSocket target. |
| [VAL-020](issues/VAL/VAL-020.md) | Medium | Keep open | Owner explicitly requested this remain open. Focused performance improvements shipped, but the recorded hosted total runtime did not improve. |
| [AI-021](issues/AI/AI-021.md) | Low | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AUD-006](issues/AUD/AUD-006.md) | Low | Resolve: confirmation pending | Display repair and punt-renderer follow-up are committed; complete issue-specific display confirmation remains pending. |
| [AUD-019](issues/AUD/AUD-019.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-021](issues/AUD/AUD-021.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-023](issues/AUD/AUD-023.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-024](issues/AUD/AUD-024.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-027](issues/AUD/AUD-027.md) | Low | Close: completed | The native chart dialog closes before restoring focus; this shipped in 8c0bb8b. November 5 user and agent browser runs explicitly verify both Escape and Close focus restoration. Those assertions remain in the hosted-passing v1.10.2 chart browser test; current chart component regressions pass. |
| [DATA-002](issues/DATA/DATA-002.md) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DATA-003](issues/DATA/DATA-003.md) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DATA-015](issues/DATA/DATA-015.md) | Low | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-039](issues/DATA/DATA-039.md) | Low | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-044](issues/DATA/DATA-044.md) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DATA-045](issues/DATA/DATA-045.md) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DOC-001](issues/DOC/DOC-001.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-017](issues/FLOW/FLOW-017.md) | Low | Close: completed | Both team timeout counts shipped in 8c0bb8b. November 6 focused Chromium checks verify both counts within a 390px viewport; v1.10.2 hosted player-help checks retain team-labeled counts. Current scoreboard tests pass. The old uncommitted-fix condition is satisfied; this is not new 1.10.3 work. |
| [FLOW-020](issues/FLOW/FLOW-020.md) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [RULE-008](issues/RULE/RULE-008.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-009](issues/RULE/RULE-009.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [STAT-006](issues/STAT/STAT-006.md) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [TRACE-008](issues/TRACE/TRACE-008.md) | Low | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [VAL-008](issues/VAL/VAL-008.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-011](issues/VAL/VAL-011.md) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |

## Limits

No source data, historical charts, scoring bounds, AI selectors or saved standings
were changed. Existing ticket history is preserved. Open records containing
implemented components should be checked before coding; open does not imply
the entire original description still reproduces. No private evidence is exported.

Follow-up: DATA-021 was initially retained too broadly. Direct producer/adapter and
all-60-team artifact review establishes the specific generated-symbol defect is
fixed. Both public audits pass without certifying historical accuracy; fifteen
focused checks pass (189 unrelated cases deselected). No source/model bounds changed.

Status follow-up: RULE-030 and FLOW-016 are resolved because their fixes are
committed; their outstanding issue-specific play-test confirmation prevents
closure, not resolution. No gameplay changes or new play-test claims.

Implementation-status follow-up: twenty more committed repairs are marked
resolved pending confirmation. Open is reserved for remaining implementation,
modeling decisions or unresolved investigations. Together with RULE-030/FLOW-016,
22 initially open tickets are now resolved; 16 are closed and 78 remain open.
No outstanding campaign, corpus, browser or independent-review pass is implied.

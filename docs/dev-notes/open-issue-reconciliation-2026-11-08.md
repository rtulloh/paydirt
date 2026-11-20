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
| [AI-025](https://github.com/rtulloh/paydirt/issues/27) | High | Close: completed | Auto-game observation recording is committed in 8c0bb8b. The November 5 renewed Hard/balanced campaigns completed 7,936 games and reconciled 1,179,571 selected calls after the fix. Current auto-game regressions pass. This closes observation routing, not AI-019 response quality or AI-026 chart awareness. |
| [AI-026](https://github.com/rtulloh/paydirt/issues/28) | High | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-027](https://github.com/rtulloh/paydirt/issues/29) | High | Close: completed | The server-owned CPU plan, clock-option routing, timeout integration and call mappings shipped in 8c0bb8b and remain in v1.10.2. November 6 built-service Chromium and the completed owner game confirm CPU timeout use. Current CPU-clock API regressions pass. Strategic policy quality remains separately open. |
| [AUD-030](https://github.com/rtulloh/paydirt/issues/67) | High | Resolve: confirmation pending | Committed report validation reconstructs derived rates; independent fresh campaign/report validation remains pending. |
| [DATA-016](https://github.com/rtulloh/paydirt/issues/84) | High | Resolve: confirmation pending | Unrounded-target finite-mass selection and QT/QT* allocation controls are committed; final regenerated play/audit confirmation remains pending. |
| [DATA-017](https://github.com/rtulloh/paydirt/issues/85) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-018](https://github.com/rtulloh/paydirt/issues/86) | High | Keep open | The shipped cohorts retain explicitly accepted fit exceptions; publication is not proof these accuracy misses are fixed. DATA-042 and AI-030 separately own pace/scoring and policy-transfer diagnostics. |
| [DATA-019](https://github.com/rtulloh/paydirt/issues/87) | High | Close: completed | The corrected QT-fumble observer shipped in 8c0bb8b. The November 5 renewed 31,744-game campaign reconciled every team/league play identity with the corrected counters. Current observer tests pass. This closes the measurement classification defect, not historical chart-fit or source-model acceptance. |
| [DATA-020](https://github.com/rtulloh/paydirt/issues/88) | High | Close: completed | The offsetting-penalty observer exclusion shipped in 8c0bb8b. November 5 exact previously failing game replays and the renewed 31,744-game campaign confirm reconciled accounting. Current real-engine/observer regressions pass. Broader nullified fumble-return handling remains under DATA-031. |
| [DATA-021](https://github.com/rtulloh/paydirt/issues/89) | High | Close: completed | Follow-up confirms column guards and both adapters are repaired; zero OFF/DEF B/QT cells across all 60 shipped teams, both complete public compatibility audits pass, 15 focused regressions pass. Prior reproduced cohorts and all-team real-engine release evidence cover the repaired artifacts. Broader source-fit requirements remain separate. |
| [DATA-022](https://github.com/rtulloh/paydirt/issues/90) | High | Resolve: confirmation pending | Neutral interception-floor correction and low-mass strength ordering are committed; final fit/stress confirmation remains pending, with depth/stripe model limits retained. |
| [DATA-023](https://github.com/rtulloh/paydirt/issues/91) | High | Resolve: confirmation pending | Conditional sack/defensive-overlap allocation and shared neutral-pressure preparation are committed; final all-team/held-out/policy validation remains pending. |
| [DATA-024](https://github.com/rtulloh/paydirt/issues/92) | High | Resolve: confirmation pending | Conversion exclusion, provenance and coverage guards are committed; final regenerated and independent qualification remain pending. |
| [DATA-025](https://github.com/rtulloh/paydirt/issues/93) | High | Resolve: confirmation pending | Initial-gain fitting/parsing guards are committed and unknown required gains fail explicitly; complete source/integrated confirmation remains pending. |
| [DATA-026](https://github.com/rtulloh/paydirt/issues/94) | High | Resolve: confirmation pending | Representative midpoint-quantile selection is committed in empirical_adjustment.py; regenerated source/population and independent validation remain pending. |
| [DATA-027](https://github.com/rtulloh/paydirt/issues/95) | High | Resolve: confirmation pending | QB-time class preservation is committed and SACK 0 supersedes the temporary minus-one floor; final source/campaign confirmation remains pending. |
| [DATA-028](https://github.com/rtulloh/paydirt/issues/96) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-029](https://github.com/rtulloh/paydirt/issues/97) | High | Resolve: confirmation pending | QT-only SACK 0 is committed across source, resolver, engine, observer, generator and audit paths; final source/charter validation remains pending. |
| [DATA-030](https://github.com/rtulloh/paydirt/issues/98) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-031](https://github.com/rtulloh/paydirt/issues/99) | High | Resolve: confirmation pending | Replay-down credit guard is committed with natural nullified-fumble campaign evidence; final independent confirmation remains pending. |
| [DATA-032](https://github.com/rtulloh/paydirt/issues/100) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-035](https://github.com/rtulloh/paydirt/issues/103) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-036](https://github.com/rtulloh/paydirt/issues/104) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-038](https://github.com/rtulloh/paydirt/issues/106) | High | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [FLOW-013](https://github.com/rtulloh/paydirt/issues/133) | High | Close: completed | Human defensive timeout controls and engine routing shipped in 8c0bb8b. The recorded November 2 full browser games verify six human defensive timeouts per game, correct home/away ownership, exhausted budgets and keyboard cancellation/reselection. The v1.10.2 hosted 18-browser-check pass includes both real-engine games; current API and component regressions pass. |
| [FLOW-016](https://github.com/rtulloh/paydirt/issues/136) | High | Resolve: confirmation pending | Engine-owned preview fix exists, but the recorded pending updated-service play-test confirmation has not been located. Mark resolved pending confirmation; do not reimplement the already-shipped projection. |
| [RULE-026](https://github.com/rtulloh/paydirt/issues/189) | High | Resolve: confirmation pending | Selected-priority fumble classification is corrected in committed code; required regenerated/full-game/audit confirmation remains pending. |
| [RULE-027](https://github.com/rtulloh/paydirt/issues/190) | High | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-029](https://github.com/rtulloh/paydirt/issues/192) | High | Resolve: confirmation pending | End-line interception safety and retained-play geometry corrections are committed; issue-specific gameplay confirmation remains pending. |
| [RULE-030](https://github.com/rtulloh/paydirt/issues/193) | High | Resolve: confirmation pending | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [STAT-004](https://github.com/rtulloh/paydirt/issues/203) | High | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [VAL-009](https://github.com/rtulloh/paydirt/issues/224) | High | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-017](https://github.com/rtulloh/paydirt/issues/232) | High | Resolve: confirmation pending | Loaded runtime/observer identity checks and display-preference correction are committed; final frozen-candidate integration review remains pending. |
| [VAL-018](https://github.com/rtulloh/paydirt/issues/233) | High | Resolve: confirmation pending | Ordered-call, policy/distribution and repetition validation are committed; final complete collection and independent review remain pending. |
| [VAL-019](https://github.com/rtulloh/paydirt/issues/234) | High | Keep open | Historical calendars/postseasons are implemented and exercised, but the ticket explicitly retains official tiebreak/neutral-site/full-transition verification. AI-026 separately owns chart-response work. Keep open for that narrower remaining verification; do not implement the calendar runner again. |
| [AI-002](https://github.com/rtulloh/paydirt/issues/4) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-003](https://github.com/rtulloh/paydirt/issues/5) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-012](https://github.com/rtulloh/paydirt/issues/14) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-013](https://github.com/rtulloh/paydirt/issues/15) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-015](https://github.com/rtulloh/paydirt/issues/17) | Medium | Resolve: confirmation pending | KEEP-option selection and API index routing are committed; independent updated-service play testing remains pending. |
| [AI-016](https://github.com/rtulloh/paydirt/issues/18) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-017](https://github.com/rtulloh/paydirt/issues/19) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-018](https://github.com/rtulloh/paydirt/issues/20) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-019](https://github.com/rtulloh/paydirt/issues/21) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-020](https://github.com/rtulloh/paydirt/issues/22) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-023](https://github.com/rtulloh/paydirt/issues/25) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-024](https://github.com/rtulloh/paydirt/issues/26) | Medium | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [AI-029](https://github.com/rtulloh/paydirt/issues/31) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AI-030](https://github.com/rtulloh/paydirt/issues/32) | Medium | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AUD-014](https://github.com/rtulloh/paydirt/issues/51) | Medium | Keep open | Overlaps FLOW-016 previews and RULE-003, but its retained symbolic penalty-reroll/secondary-result checks and dead projection paths are broader than the confirmed numeric/incomplete preview repair. |
| [AUD-015](https://github.com/rtulloh/paydirt/issues/52) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-016](https://github.com/rtulloh/paydirt/issues/53) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-017](https://github.com/rtulloh/paydirt/issues/54) | Medium | Keep open | Overlaps the broad AUD-006 display work, but the available general first-down/punt evidence is not a new explicit offensive-fumble first-down play-test confirmation. Retain pending a targeted check. |
| [AUD-018](https://github.com/rtulloh/paydirt/issues/55) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-020](https://github.com/rtulloh/paydirt/issues/57) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-022](https://github.com/rtulloh/paydirt/issues/59) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-028](https://github.com/rtulloh/paydirt/issues/65) | Medium | Resolve: confirmation pending | Deterministic equal-weight placement and invariant/review tooling are committed; frozen all-team campaigns and owner review remain pending. |
| [AUD-029](https://github.com/rtulloh/paydirt/issues/66) | Medium | Resolve: confirmation pending | Missing-secondary-row audit defaults now preserve the core fallback distribution; actual stable-corpus integration remains pending. |
| [DATA-037](https://github.com/rtulloh/paydirt/issues/105) | Medium | Resolve: confirmation pending | Signed defensive F rejection is committed in reference-decoder preflight; complete actual-corpus integration remains pending. |
| [DATA-040](https://github.com/rtulloh/paydirt/issues/108) | Medium | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-041](https://github.com/rtulloh/paydirt/issues/109) | Medium | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-042](https://github.com/rtulloh/paydirt/issues/110) | Medium | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [FLOW-006](https://github.com/rtulloh/paydirt/issues/126) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-007](https://github.com/rtulloh/paydirt/issues/127) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-008](https://github.com/rtulloh/paydirt/issues/128) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-009](https://github.com/rtulloh/paydirt/issues/129) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-015](https://github.com/rtulloh/paydirt/issues/135) | Medium | Resolve: confirmation pending | Clock formatting and preplay-clock attribution are committed; issue-specific half-ending log browser confirmation remains pending. |
| [FLOW-018](https://github.com/rtulloh/paydirt/issues/138) | Medium | Close: completed | Pending-try eligibility propagation shipped in 8c0bb8b. November 6 real-engine browser success/failure checks cover both human sides, prohibited seasons and final/halftime flow; the owner confirmed the choice was visible. The v1.10.2 hosted two-point browser cases pass, and current conversion API tests pass. |
| [FLOW-021](https://github.com/rtulloh/paydirt/issues/141) | Medium | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [FLOW-022](https://github.com/rtulloh/paydirt/issues/142) | Medium | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [RULE-001](https://github.com/rtulloh/paydirt/issues/164) | Medium | Close: completed | The isolated untimed conversion implementation shipped in 8c0bb8b. November 6 actual chart/API/browser checks verify +2-only scoring, defensive ownership, no ordinary time/statistics/history changes and restoration on exceptions. v1.10.2 hosted two-point browser checks and current unmocked conversion tests pass. |
| [RULE-003](https://github.com/rtulloh/paydirt/issues/166) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-004](https://github.com/rtulloh/paydirt/issues/167) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-005](https://github.com/rtulloh/paydirt/issues/168) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-006](https://github.com/rtulloh/paydirt/issues/169) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-007](https://github.com/rtulloh/paydirt/issues/170) | Medium | Close: completed | Explicit touchdown-entry attribution in both try methods shipped with the conversion repair in 8c0bb8b. November 6 actual API halftime cases verify touchdown period/time attribution for successful, failed and defensive-return tries on both sides. Current conversion regressions pass; this is completed shared work with RULE-001, not another implementation task. |
| [RULE-011](https://github.com/rtulloh/paydirt/issues/174) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-012](https://github.com/rtulloh/paydirt/issues/175) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [SPIKE-004](https://github.com/rtulloh/paydirt/issues/199) | Medium | Close: completed | The standalone three-second clock call shipped in 8c0bb8b. November 6 served HTTP checks verify 90 to 87 seconds, half/game expiration and fourth-down possession changes across 16 cases. Current standalone-spike regressions pass, and later v1.10.2 hosted core/browser qualification is recorded. This does not close unrelated spike/modifier issues. |
| [STAT-001](https://github.com/rtulloh/paydirt/issues/200) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [STAT-003](https://github.com/rtulloh/paydirt/issues/202) | Medium | Close: completed | Ordinary-statistics isolation shipped with RULE-001 in 8c0bb8b. November 6 real chart/API/compiled-browser cases confirm no ordinary statistics, play-log or call-history credit for successful, failed, intercepted and fumbled tries. Current unmocked isolation/API tests pass. STAT-001 punt accounting is separate. |
| [TRACE-001](https://github.com/rtulloh/paydirt/issues/207) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-003](https://github.com/rtulloh/paydirt/issues/209) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-004](https://github.com/rtulloh/paydirt/issues/210) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-005](https://github.com/rtulloh/paydirt/issues/211) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [TRACE-007](https://github.com/rtulloh/paydirt/issues/213) | Medium | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [VAL-001](https://github.com/rtulloh/paydirt/issues/216) | Medium | Keep open | A monitoring record, not a demonstrated duplicate root-cause fix: repeated browser passes clear the blocker but do not establish what caused the original reload. Retain monitoring without treating it as a reproduced release failure. |
| [VAL-004](https://github.com/rtulloh/paydirt/issues/219) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-005](https://github.com/rtulloh/paydirt/issues/220) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-006](https://github.com/rtulloh/paydirt/issues/221) | Medium | Close: completed | The supported CI matrix is now Python 3.10/3.11/3.12, with the full core run only on 3.10 and compatibility checks on the others; the workflow configuration shipped by d321242. The v1.10.2 exact-source hosted workflow passed all nine jobs. Current workflow regressions pass. No Python 3.9 job remains. |
| [VAL-010](https://github.com/rtulloh/paydirt/issues/225) | Medium | Close: completed | The historical-dependent unit cases were replaced with synthetic/public fixtures in the shipped 8c0bb8b integration. Reviewed the originally named commentary, interactive, season-rule and chart test files; historical-looking labels are synthetic metadata, not private file loads. v1.10.2 clean hosted core completed 10,893 tests with no skips. Current targeted core checks pass without skips. Do not confuse intentionally local historical integration runners with unit fixtures. |
| [VAL-013](https://github.com/rtulloh/paydirt/issues/228) | Medium | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-016](https://github.com/rtulloh/paydirt/issues/231) | Medium | Close: completed | The API proxy now explicitly targets 127.0.0.1:8000; this shipped in 8c0bb8b. The existing November 5 unchanged browser guide test passed after the correction, including all seven images and HTTP 200 through Vite; later v1.10.2 hosted offline-guide checks pass. This closure is limited to the /api IPv4 proxy defect, not the separate WebSocket target. |
| [VAL-020](https://github.com/rtulloh/paydirt/issues/235) | Medium | Keep open | Owner explicitly requested this remain open. Focused performance improvements shipped, but the recorded hosted total runtime did not improve. |
| [AI-021](https://github.com/rtulloh/paydirt/issues/23) | Low | Keep open | Distinct remaining policy/evaluation scope; existing coaching fixes do not establish this ticket's full completion. |
| [AUD-006](https://github.com/rtulloh/paydirt/issues/43) | Low | Resolve: confirmation pending | Display repair and punt-renderer follow-up are committed; complete issue-specific display confirmation remains pending. |
| [AUD-019](https://github.com/rtulloh/paydirt/issues/56) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-021](https://github.com/rtulloh/paydirt/issues/58) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-023](https://github.com/rtulloh/paydirt/issues/60) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-024](https://github.com/rtulloh/paydirt/issues/61) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [AUD-027](https://github.com/rtulloh/paydirt/issues/64) | Low | Close: completed | The native chart dialog closes before restoring focus; this shipped in 8c0bb8b. November 5 user and agent browser runs explicitly verify both Escape and Close focus restoration. Those assertions remain in the hosted-passing v1.10.2 chart browser test; current chart component regressions pass. |
| [DATA-002](https://github.com/rtulloh/paydirt/issues/70) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DATA-003](https://github.com/rtulloh/paydirt/issues/71) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DATA-015](https://github.com/rtulloh/paydirt/issues/83) | Low | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-039](https://github.com/rtulloh/paydirt/issues/107) | Low | Keep open | Partial tooling/source fixes do not satisfy the recorded remaining model, stable-corpus, regenerated-fit or independent integration acceptance; no fully completed equivalent established. |
| [DATA-044](https://github.com/rtulloh/paydirt/issues/112) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DATA-045](https://github.com/rtulloh/paydirt/issues/113) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [DOC-001](https://github.com/rtulloh/paydirt/issues/120) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [FLOW-017](https://github.com/rtulloh/paydirt/issues/137) | Low | Close: completed | Both team timeout counts shipped in 8c0bb8b. November 6 focused Chromium checks verify both counts within a 390px viewport; v1.10.2 hosted player-help checks retain team-labeled counts. Current scoreboard tests pass. The old uncommitted-fix condition is satisfied; this is not new 1.10.3 work. |
| [FLOW-020](https://github.com/rtulloh/paydirt/issues/140) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [RULE-008](https://github.com/rtulloh/paydirt/issues/171) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [RULE-009](https://github.com/rtulloh/paydirt/issues/172) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [STAT-006](https://github.com/rtulloh/paydirt/issues/205) | Low | Keep open | Distinct remaining correction or requested feature; no completed equivalent established. |
| [TRACE-008](https://github.com/rtulloh/paydirt/issues/214) | Low | Keep open | Distinct trace/replay requirement; no completed equivalent with issue-specific evidence established. |
| [VAL-008](https://github.com/rtulloh/paydirt/issues/223) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |
| [VAL-011](https://github.com/rtulloh/paydirt/issues/226) | Low | Keep open | No fully completed equivalent with evidence covering the entire recorded scope established; retain existing acceptance requirements. |

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

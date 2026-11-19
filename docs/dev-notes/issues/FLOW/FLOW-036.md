---
id: FLOW-036
title: Add persistent web seasons, custom mixed-era leagues, and browser save/load
status: open
priority: Medium
target-release: v1.12.0
created-at: 2026-11-18
resolved-at:
closed-at:
tags:
  - feature-request
  - umbrella
links:
  - FLOW-020
  - FLOW-021
  - STAT-006
  - FLOW-008
  - FLOW-033
commits:
  - d059990035d5d8f235936696b8e1a24b968bc169
  - ced3856
---

## Description

The owner approved the [season UI preview](../../season-ui-preview.html) and the six-slice delivery approach on 2026-11-18. This umbrella issue records the agreed direction: a dedicated Seasons page, multiple independent campaigns, historical calendars beginning with 1983, custom and mixed-era leagues, recorded final results, standings, team statistics/leader categories, and durable game/season save and restore.

The canonical specification, inspected source evidence, product choices, validation matrix, and preview limitations are in the [design and delivery plan](../../season-ui-design.md). Keep detailed decisions there rather than duplicating a second specification here. The preview uses illustrative data and is not an implemented feature.

Existing FLOW-020 covers cross-year exhibition setup, FLOW-021 covers web result recording and standings, and STAT-006 covers cumulative team statistics. Retain and coordinate those issues rather than opening duplicate work. FLOW-008 is related legacy replay reconstruction debt. Browser persistence extends the temporary-session distribution investigated in FLOW-033; it is not a claim that the current spike already supports durable saves.

The owner also requested subagent assistance and goal-based execution. The linked plan records bounded ownership, dependencies, evidence-based completion, and integration responsibilities. This issue documents work; approval of the preview and slices does not approve unresolved product policies, a particular release date, publishing, or changes to the permission profile.

## Resolution / verification

- Slice 1 — Canonical checkpoints and browser save/load: round-trip engine, AI, both team editions, governing rules, phase/pending decisions, stats, history, and campaign linkage through shared HTTP/worker operations. Provide named saves, autosave and portable import/export. Verify real restart recovery and write/import/migration failure safety; UI-only snapshots are insufficient.
- Slice 2 — Cross-year exhibitions (FLOW-020): independent year/team selectors, complete selection swap, clear governing rules, both human roles, same-franchise/different-year identities, confined catalog lookup, and save round trips. Preserve same-year compatibility.
- Slice 3 — Persistent season domain: separate campaign/participant/fixture identities, historical-template validation, a canonical result ledger, idempotent finalization, result revisions/recomputation, and transactional persistence. Reopening or retrying a final must not count it twice.
- Slice 4 — Historical Seasons page (FLOW-021 / STAT-006): campaign selection, dashboard, actual 1983 calendar/divisions, fixture play/resume, standings, supported team statistics and team leader categories. Completed-game totals reconcile; missing statistics remain unknown. Separate campaigns from the same chart year stay isolated across restart.
- Slice 5 — Custom and mixed-era seasons: reusable team-edition selection, reviewed division/schedule setup, byes, validated fixtures, active-definition locking, explicit campaign rules policy, and portable export/import. Confirm the rule policy before implementing its core seam.
- Slice 6 — Remaining-game simulation and postseason: explicit cancellable engine-driven simulation, resumable committed progress, no overwriting played/in-progress fixtures, legal finals, and documented ranking/qualification. Postseason entrants derive from campaign results, never forced historical winners. Confirm first-release scope and ranking policy.
- Execute the dependency and agent/goal workflow in the canonical plan. Each behavior change begins with a meaningful failing synthetic/public-2026 regression and passing controls; measure changed-module coverage. Goal completion requires actual acceptance evidence, not code presence or an agent success message.
- Before push, satisfy every root AGENTS.md full regression and clean-checkout gate; retain private evidence locally and preserve important work remotely through an authorized route. Update affected player/offline guides. Native release health requires downloaded-artifact verification. Keep open until implementation and required play-test confirmation are complete.

## Comments

--- 2026-11-18 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-18 11:17 ---
Owner approved the preview and six-slice approach and explicitly excluded individual
player statistics. Team statistics/leader categories are in scope. An independent
subagent reviewed task ownership, dependencies, and goal completion evidence; the
canonical plan now records that workflow. Rule policy, first-release scope and
manual score entry remain decisions before their dependent implementation.
This issue remains open and unscheduled; no implementation was performed.

--- 2026-11-18 11:40 ---
Owner subsequently instructed “proceed”; all six slices are now being implemented locally
with the recommended defaults recorded in the canonical plan. Team statistics only; no
individual player statistics. Subagents own bounded checkpoint/runtime, campaign/domain,
and UI/recovery tasks, with integration and independent review at the parent goal.
Initial integrated frontend suite: 479 passed; backend: 522 passed (existing deprecations).
Full regression and actual Wasm engine checks are running. Recovery review findings are
being fixed test-first. Browser launch remains unavailable due to macOS registration errors;
no release qualification, commit, push or remote preservation is claimed. Issue stays open.

--- 2026-11-18 11:47 ---
Final integrated frontend: 494 passed; backend: 529 passed (371 existing deprecation
warnings); production and browser builds pass. Final Wasm campaign audit passes 17
checks; the design note records hashes, coverage, test-first failures, recovery fixes
and evidence paths. The new actual-browser restart test fails before assertions because
macOS denies Chromium process registration. Full regression is still running.
Reviewed the resolved-ticket index after the Wasm play/audit checks: their evidence does
not establish the specific outstanding browser/CLI/chart qualification required to close
those tickets, so none is closed from these general runtime passes. FLOW-036 also stays
open: implementation is uncommitted and actual browser recovery remains unqualified.

--- 2026-11-18 12:01 ---
All six slices are implemented locally, including the final regulation-TD/owed-PAT
checkpoint/finalization fix. Final suites: core 11,740 passed in the working tree and
again in the clean candidate export; backend 530; frontend 499. Both builds, lint,
fourteen-game regression, all 224 regular/nine playoff games, both AI audits and
released 1983/2024 chart checks pass. Full runner summary: 12 pass/one browser failure,
zero skipped. Its port-conflict failure was followed by fresh-port full and targeted
retries; Chromium still fails before assertions with macOS MachPort permission denied.
Actual restart/visual/native qualification remains incomplete. AI review is recorded in
AI-008; no unsupported ticket closures. Canonical design note records receipts, hashes,
coverage and a live isolated preview at http://127.0.0.1:18466/ while running.
Keep open and the umbrella goal unachieved. No commit, push or verified remote backup.

--- 2026-11-18 12:10 ---
Requirement-by-requirement continuation audit corrects the earlier overly broad “all
six slices implemented” statement. Native user-data persistence and pre-action writer
ownership were missing, as were duplicate season, generated-schedule editing and a
public authoritative correction command. These are being implemented, not deferred by
redefining scope. Native SQLite + frontend adapter now pass separate-process restart
on a different origin; process ownership/canonical origin guards are in progress.
Browser Web Locks/preflight checks pass focused tests. Domain duplicate/edit/correction
commands and followed-team identity remapping pass test-first regressions; related UI
and final integration review are underway. Explicit browser-storage protection is now
offered on demand. Prior regression receipts remain evidence for their exact candidates;
they do not qualify these subsequent changes. Issue and goal remain open/unachieved.

--- 2026-11-18 12:26 ---
Continuation acceptance audit and fixes are recorded in
[the acceptance matrix](../../season-ui-acceptance.md). Native SQLite ownership,
loopback/origin guards, frontend storage routing, pre-action game/campaign writer
leases, duplicate/edit schedule, followed-team views and authoritative result review
now have focused regressions. Latest frontend suite: 538 passed; production build
passes (existing Browserslist and mixed-import warnings). Native HTTP and injected-lock
cross-module restart receipts are runtime evidence, not actual browser qualification.
A fresh full regression including clean candidate export is running. Native normal
launcher verification and final browser bundle audit are in progress. Issue remains
open; no push, release or verified remote preservation is claimed.

--- 2026-11-18 12:40 ---
Fresh full runner `.ai-audits/full-regression/20261118T181701Z/summary.json`:
12 passed, one failed, zero skipped. Core and tracked-only candidate export each
pass 11,745 tests; frontend 538, backend 568 at its run point; builds, lint,
14-game runner, all 224 regular/nine playoff games, both AI audits and released
1983/2024 chart audits pass. A later narrow --web/-w dispatch fix passes the full
backend suite (574), focused launcher regressions and actual normal-entrypoint
restart/ownership audit (ten checks). Final guide-bound Wasm audit passes 18 checks;
see canonical design/acceptance matrix for exact hash and coverage limitations.
The runner browser step hit an occupied localhost port; a separate final retry
checked free IPv4/IPv6 ports and started both services, then Chromium failed
before assertions with MachPort permission denied 1100/SIGTRAP. Actual browser
storage, game/recovery, focus/mobile/visual acceptance remains unverified. Do not
push or resolve this umbrella from the other passing evidence. No commit, push,
release, downloaded-artifact qualification or verified remote backup is claimed.

--- 2026-11-18 13:56 ---
Local six-slice implementation and actual browser acceptance are complete;
[final evidence](../../season-ui-acceptance.md) records exact provenance and limitations.
Dedicated historical/custom mixed-era seasons, team-only statistics/leaders, durable
browser/native checkpoints, cross-year exhibitions, result revisions, simulation and
postseason are implemented. Final HTTP28 and built-Wasm5 pass; the latter completes
eight real games across all four public years without HTTP API calls. Native/browser
restart and writer-lock checks pass. Core11,765 passes in working tree and clean export;
backend610/frontend558 and all generated-season/AI/chart/lint/build commands have
passing evidence. Original combined-run browser failure remains recorded separately
from final passing follow-ups; no single green combined summary is claimed.

Live current preview: http://127.0.0.1:18785/ (isolated local native library).
One earlier safely rejected unfinished simulation did not reproduce in 2,000 seeded
public-sample controls; test-only diagnostics capture future recurrences. No guard
was weakened or failed result committed. Issue remains open for review/integration;
no commit, push, release or verified remote preservation.


### 2026-11-18 — Season fixture pregame setup

Owner testing found that Schedule → Play immediately launched Medium difficulty.
Play now opens a focused Game setup dialog with the team editions, home/away coach
choice, and Easy/Medium/Hard difficulty (Medium by default). Start game creates the
checkpoint and proceeds to coin toss; Cancel/Escape leaves the fixture unstarted.
Saving disables controls; failures stay in the dialog for retry. The confirmed
choice is passed to UI restoration when the campaign launch response omits its
top-level difficulty; actual engine difficulty remains set by the start command.
Resuming retains the saved choice.

Test-first evidence: six expected setup failures with 15 passing controls before
production edits; an additional difficulty propagation regression failed with
21 passing controls before its fix. The previous immediate-launch expectation
was changed to require explicit Start game because creation must wait for setup.
Final focused tests: 22 passing; SeasonDesk.jsx coverage 88.38% lines / 84.42%
branches. Remaining module gaps include existing season-management error/actions
and defensive focus branches; no skips or exclusions were added. Full frontend:
564 passing in 71 files. Actual Chromium: all four season desk/recovery tests pass,
including rendered Away/Hard setup, canonical checkpoint session verification,
coin toss, reload/resume, cancellation, and mobile width. Documentation test passes.
Normal and browser builds pass with existing Browserslist/mixed-import warnings.
Evidence and reviewed mobile screenshot: `.ai-audits/season-ui/pregame/`.
Preview http://127.0.0.1:18785/ serves the updated build; refresh the tab without
clearing site data. No backend restart or user library mutation was needed.
This focused frontend follow-up is local and uncommitted; it does not claim a new
full regression, release qualification, push, or verified remote backup.


### 2026-11-18 — Punt checkpoint rejection and invisible blocked play

Owner play-test: STL punted from its 11; NO received at STL 47. The engine had
correct possession, first-and-10, Q1 13:48, but native autosave returned 422.
Offline inspection of the captured checkpoint reproduced the exact cause:
`PlayOutcome.field_position_before` was the integer 11 in punt history, while
its source annotation is `str`. Existing special-team paths retain this numeric
coordinate; restore now explicitly accepts only integer coordinates 0–100 for
this exact record field. Other fields keep strict annotation validation, and
booleans, fractional/out-of-range/null/object values remain rejected. No engine
outcomes, field position, possession, or game rules changed; existing checkpoint
bytes remain intact. No version/schema migration is needed.

The persistence coordinator correctly stopped subsequent mutations after the
failed save, but normal play request exceptions were console-only. PlayingPhase
now displays those errors in its existing alert, clears the rolling state, and
clears the prior action error on retry.

Test-first: the real public-2026 CPU punt and valid legacy numeric-position cases
failed restore (4 expected failures, 29 passing controls); the UI blocked-play
regression also failed before the fix. Added native SQLite put/reopen/restore
coverage and a rendered post-punt recovery/next-offensive-play/save browser test.
Backend suite: 621 passing, 443 existing deprecation warnings. Frontend suite:
565 passing. Focused checkpoint suites: 73 passing, checkpoints.py 91% line
coverage; remaining gaps are defensive malformed-save/unsupported-shape branches
and optional type alternatives, not the newly accepted numeric field path.
PlayingPhase.jsx coverage: 82.87% lines / 83.12% branches; existing specialty
presentation/control paths remain outside this unit run, with real-engine browser
checks supplemental. Ruff and documentation check pass. No skips/exclusions or
existing expectation changes were introduced for this fix.

Recovery: captured both live saves, verified an SQLite backup against every row
and integrity_check, and independently restored the exact failing checkpoint.
Restarted only our identified port-18785 preview process to load the fix. Through
the normal native library command API, atomically saved the owner's exact captured
post-punt checkpoint alongside its unchanged campaign: game revision 9→10,
campaign revision 12→13. API reread verified exact checkpoint bytes. Owner can
refresh → Saved games → resume STL/NO at Q1 13:48, first-and-10 at STL 47.
Private local evidence/backup: `.ai-audits/season-ui/punt-save/`; recovery receipt
records exact IDs/revisions. Backup is local only; no remote preservation claimed.
Issue remains open for review/integration; no commit/push/release claimed.


Follow-up from the same owner session: exiting and choosing main-menu LOAD GAME
opened the legacy local-storage loader, restoring older display data through its
separate API path. LOAD GAME now opens the same durable Saved games library as
SAVED GAMES. Old local-storage data is retained, not deleted or silently migrated.
A new menu regression failed before the change, then passed; an actual native
Chromium test seeds stale legacy data, enters through LOAD GAME, resumes the real
post-punt checkpoint, executes the next offensive play and saves successfully,
without any load-replay request. Final frontend suite: 566 passing; MenuPhase.jsx
70.17% lines / 72.22% branches, with remaining gaps chiefly legacy replay controls,
loading/error branches, and the optional no-handler fallback (App supplies the
handler). PlayingPhase coverage remains 82.87% lines / 83.12% branches.

The surrounding browser recovery suite and both complete real-engine games pass
(6 tests, 2.8 minutes): home/receiving 38–24 with 171 executes and 12 kickoffs;
away/kicking 41–34 with 150 executes and 14 kickoffs; one halftime each. This run
preceded only the narrow menu alias fix, which has its separate final native
browser proof above. The rebuilt actual Node/Pyodide engine also passes a public
2026 real punt → checkpoint → restore → next offensive play audit. Normal/browser
builds pass, retaining existing Browserslist/mixed-import warnings. Evidence is
in `.ai-audits/season-ui/punt-save/`. No full core/season/AI/released-chart rerun
is claimed for these narrow checkpoint/UI changes; all mandatory gates still
apply before any push. Work remains local/uncommitted.


### 2026-11-18 — Pending field-goal penalty checkpoint and blocked decision

Owner reached Q2 0:09, second-and-10 at NO 17, with STL's missed 34-yard FG
owing the human an OFF 5 accept/decline choice. The engine exported the pending
state, but native validation rejected the checkpoint as Unknown record fields.
The engine legitimately attaches five integer FG context attributes to PlayOutcome:
`_fg_distance_to_goal`, `_fg_statistical_distance`, `_fg_spot_of_hold`,
`_fg_ball_pos_before`, `_fg_ytg_before`. A closed per-record extra-field type map
now preserves precisely these values, alongside the existing TeamStats boolean
completeness marker. Unknown fields still fail; all five fields reject boolean,
fractional, string, null and object values. An AST review of private outcome-field
assignments in game_engine.py found these five attached fields; no catch-all
attribute acceptance was introduced. No engine rules/outcomes changed.

The failed save correctly blocked further mutations; penalty-request exceptions
and non-OK HTTP responses previously only logged to console. They now use the
existing visible action error, retain the pending choice, and clear the error on
a successful retry. Test-first baseline: 4 expected FG checkpoint failures with
33 passing controls; both transport and HTTP penalty error tests failed before
UI changes (6 passing controls). New synthetic/public-2026 tests cover made/missed
FG × accept/decline after restore, matching live-engine outcomes, and 25 wrong-type
cases. No tests weakened, skipped or excluded. Focused checkpoint suites: 102 pass,
checkpoints.py 91% lines (remaining gaps defensive malformed-save/optional-shape
branches). Full backend: 650 pass, 478 dependency deprecation warnings; frontend:
568 pass, PlayingPhase.jsx 83.1% lines / 83.12% branches (remaining specialty UI
paths supplemented by actual browser checks). Ruff and documentation check pass.

Actual native Chromium recovery suite: all 6 pass, including pending FG restore,
rendered acceptance and manual save, plus ordinary penalty, interception, halftime,
expired touchdown try and post-punt play/save. Actual rebuilt Pyodide: all four
made/missed × accept/decline checkpoint round trips pass; receipt binds archive
hash. Normal/browser builds pass with existing Browserslist/mixed-import warnings.
No claim of another full core/season/AI/released-chart audit or two full games for
this narrow follow-up; previous evidence remains separately dated. Full required
gates still apply before pushing.

Recovery retained the owner's exact undecided checkpoint. Verified an SQLite
backup row-for-row and integrity_check, independently restored the captured state,
restarted only our identified preview process, then used the native transaction
API to save the exact checkpoint: saved-game revision 172→173, campaign revision
175→176. API reread verifies exact bytes; penalty was NOT chosen during recovery.
Refresh → Load Game → resume STL/NO returns Q2 0:09, second-and-10 at NO 17 with
the choice still open. Private evidence/backup:
`.ai-audits/season-ui/penalty-stall/`. Local only, no remote backup/commit/push or
release claimed. FLOW-036 remains open for review/integration.


### 2026-11-18 — Phantom resolved penalty blocked a real season final

Owner completed Saints 21–Cardinals 20, Q4 0:00. Engine flags confirmed no try,
untimed down, end-zone return or other outstanding action. Its latest play-log
entry and canonical web history both recorded the final clock-ending kneel.
However, the web backend's `_last_play_outcome` pointer still referenced an earlier
pending sack/penalty, although the corresponding resolved sack and later plays
were already in the engine log. Thus the strict campaign final guard correctly
rejected that inconsistent recovery pointer; the UI had already shown Game Over.

Fixed the bookkeeping lifecycle in `_arm_follow_up_state`: each published engine
outcome, including a resolved penalty replacement, becomes the recovery pointer.
This covers both automatically resolved CPU decisions and human decisions. No
legal-final guard was removed or weakened; real outstanding choices/tries/untimed
downs still block final acceptance. No gameplay rules/outcomes changed.

Test-first: four real public-2026 regular-play cases (human/CPU × accept/decline)
failed on the stale pending flag with 35 controls passing. Regressions also check
that duplicate penalty decisions are rejected, checkpoint restore does not
resurrect the choice, a subsequent real kneel ends the game, and campaign final
acceptance is idempotent. Full backend: 654 pass, 478 dependency deprecation
warnings. Canonical routes.py coverage 92%; campaign_operations.py 88%. The full
report also includes three isolated frozen-launcher fixture copies of routes at
33% each, making its aggregate 50%; those copies exercise import/launcher paths,
not the live endpoint suite. Remaining canonical gaps are import/fallback and
error/legacy/optional specialty paths; no skips or exclusions were introduced.
Changed pointer line and both human/CPU resolved-choice paths are exercised.

Actual native Chromium: all seven recovery cases pass, including a new rendered
campaign final after resolving a real engine penalty, native checkpoint/result
commit, one game per standings row, and completed fixture after page reload.
The fixture exposes the engine's real pending response rather than inventing UI
choice state. Actual rebuilt Pyodide runs all four regular-penalty choices through
checkpoint restore and idempotent season final acceptance. Receipt binds archive.
Ruff/documentation checks pass. Frontend production code is unchanged from the
previous 568-test passing suite; no new frontend unit count is claimed. Browser
build passes with existing mixed-import/Browserslist warnings. Existing player
save/final guidance still describes the intended behavior, so no additional
player-guide change is needed for this bookkeeping correction.

Recovery: verified a row-for-row SQLite backup and integrity_check; independently
restored the exact final checkpoint. Verified the newest core log entry matches
the canonical final kneel and has no pending choice. Applied the same bookkeeping
helper to that authoritative final outcome. Verified that ONLY the checkpoint's
`engine._last_play_outcome` changed: engine state, scores, statistics, every history
entry, AI state, rules, charts and session metadata bytes compare equal. Passed
that repaired state through the normal legal-final and idempotency validators.
Restarted only our identified preview process; committed final checkpoint and
completed campaign atomically through the native library API. Reread verifies
result revision 1, fixture completed, Saints 1–0/Cardinals 0–1, and the retained
final checkpoint. Saved-game revision 308→309; campaign revision 311→312.
Private evidence: `.ai-audits/season-ui/final-stall/`. Backups remain local only;
no remote preservation, commit, push or release claimed. Full push gates remain
mandatory; this follow-up does not claim new core/season/AI/chart audits.

2026-11-18: Final follow-up validation completed: both complete real-engine Chromium games passed (38–24 and 41–34), including halftime, final screens and clean new-game state. Evidence: `.ai-audits/season-ui/final-stall/full-games.log`. This supplements focused final-save recovery checks; it is not a new complete pre-push regression.

--- 2026-11-18 16:30 ---
Owner-requested season refinements are implemented locally: default conference/division standings (NFC before AFC; responsive columns), distinct Offense/Defense/Kicking categories, defensive interceptions/fumble recoveries/sacks, FG distance bands, passing/rushing attempts and weighted team efficiency including NFL passer rating. The final stable-source actual Chromium run passed all 12 selected checks: both complete games (38–24, 41–34), real-engine season simulations and team-stat reconciliation, pending-decision recovery, single final recording, persistent browser restart and desktop/phone layouts. Reviewed this issue against that play-test evidence; retain open for review/integration, with no published fix/commit claimed. Coverage and original interrupted/failed receipts remain in [acceptance notes](../../season-ui-acceptance.md) and ignored `.ai-audits/season-ui/standings-kicking/`. Broad final core test run remains in progress; no complete pre-push qualification claimed.

2026-11-18 final validation: complete stable-source core suite 11,839 passed; backend 657 passed (480 existing deprecation warnings), frontend 572 passed, all 12 selected real Chromium checks passed, including complete games and requested team-stat displays. Ruff/docs pass. Detailed coverage and original interrupted evidence retained in acceptance notes. Current requested refinements are complete locally; status remains open for review/integration, with required pre-push gates still applicable.

--- 2026-11-18 21:40 ---
Implemented sortable season-table headers, keyboard/direction announcements, raw numeric sorting and unknown-last behavior. Zero coverage now reads Not recorded rather than Partial. All 574 frontend tests/four rendered season checks pass; focused SeasonDesk coverage 89.72% lines/87.13% branches. Also recovered missing kicking/offensive attempt counters for the owner’s specific completed legacy game from fully aligned structured history, with all existing yardage/sack/INT counters reconciling, normal result correction/history retention and atomic CAS. Actual UI verifies both teams’ offense/defense/kicking fields populated. Private receipts remain ignored; score 21–20 and single result preserved. See acceptance notes for tests/baselines and repair boundaries. Issue remains open for integration; no push/release claimed.

--- 2026-11-19 11:36 ---
Integrated work is committed locally for v1.12.0: persistent browser/native seasons,
canonical checkpoints, mixed-era setup, team statistics and the owner-requested
Overview/Standings consolidation. Browser-only acceptance completed all 90 team/chart
initializations and eight full games (both roles across all four public years).
A locally built Mac candidate completed both an initial campaign run and a fresh-browser
reopen after application restart: identical exports and full counter coverage across
all thirteen categories. This is not downloaded published-artifact acceptance.
The first broad core run found 39 failures and 149 setup errors, all from runtime
identity rejecting the new retained-play decorators. Strict source-bound wrapper,
original/helper globals and policy-constant verification was added test-first;
180 audit-policy and 97 reference-pair tests pass, coverage 92%, with independent
tamper and hash-seed review. No pinned chart policy was weakened.
A fresh fail-fast full regression and clean export are running. Keep this issue open
until the complete gates and per-issue play-test review finish; no push/tag is claimed.
Private data and Git history have locally verified archives for the owner to upload;
remote private preservation is still unverified.

--- 2026-11-19 12:25 ---
Final product source c0b4292 passes 11,952 core tests, 667 backend tests, 588 frontend tests/build, all 90 Wasm inventory/eight full games, both native standard/mixed restart suites, fourteen-game regression, all 224 regular/nine playoff games, both AI audits and released 1983/2024 chart gates. Actual per-issue review closes FLOW-020/FLOW-021/STAT-006; FLOW-021 explicitly records the approved fixture-before-play workflow. DATA-047/RULE-032 retain their narrower unresolved evidence requirements; AI-008 remains resolved. The all-step browser run exposed obsolete localStorage fixture setup, corrected in test-only 49afba9 with all nine focused cases passing; complete 34 browser and clean-export core remain running. Keep umbrella open pending final gates and qualified public-source preservation. Private archive is locally verified for owner upload; remote private verification and published-download acceptance are not claimed. Overview alone now contains standings/recent results. Owner preview on port 18785 was restarted with a consistent SQLite backup and exactly unchanged library rows.

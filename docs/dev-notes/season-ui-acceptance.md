# FLOW-036 acceptance evidence

Local feature acceptance completed on 2026-11-18. Subsequent verified v1.12.2
publication and actual downloaded-native qualification are recorded in the
[current readiness note](release-1.12.2-readiness.md). Historical candidate evidence
and its limitations below remain intact.
The [design](season-ui-design.md) retains the approved scope and dated investigation history.
The [umbrella issue](issues/FLOW/FLOW-036.md) is closed from actual acceptance.

| Requirement | Implementation and current evidence | Acceptance status |
| --- | --- | --- |
| Dedicated Seasons page; independent campaigns | SeasonDesk, campaign UUIDs and repositories; same-year isolation and selector regressions | Rendered custom/historical desk and restart checks pass |
| Historical calendars and divisions | Catalog-bound 1983/2024 templates; actual calendars, no historical results; standalone Wasm checks 224 fixtures | Actual built Wasm Chromium: 1983, 224 fixtures, 28 participants |
| Custom and mixed-era seasons | Independent edition pickers, round robin/byes/manual fixtures, definition locks; synthetic domain tests | Rendered custom/mixed-edition creation and schedule editing pass |
| Review/edit generated schedules and duplicate fresh seasons | edit_schedule/duplicate_campaign and public operations; Schedule editor and fresh-selection UI tests | Rendered custom/mixed-edition creation and schedule editing pass |
| Follow a team, division/conference/league standings | Persistent followed_participant_id with import/duplicate remapping; overview/filter/standings tests | Rendered custom/mixed-edition creation and schedule editing pass |
| Team statistics and leader categories | Canonical result ledger, all thirteen supported team-statistic categories and authoritative counters, totals/rates/coverage denominators, tied ranks; no individual player statistics | Rendered statistics/rates/leaders and mobile review pass |
| Exactly-once finals and explicit corrections | Engine-bound legal final, revisions/history/recompute, frozen feeding results; Saved games review/confirmation with leased revision checks | Rendered cancel/idempotent confirm/correction revision, stats recompute and engine cleanup pass |
| Cross-year exhibitions | Complete edition identity/swap/role/rules banner, confined catalog lookup, checkpoint roundtrip | Actual built Wasm mixed-era exhibition/save/reload passes |
| Canonical checkpoint recovery | Closed typed JSON codec, trusted chart/rule bindings, engine/AI/history/pending choices/phase/linkage | Backend continuation tests and Wasm verified |
| Pending procedures | Penalty/end-zone restore hydration, halftime once, expired TD owed PAT continuation and finalization guard | Four actual Chromium recovery cases pass after original engine deletion |
| Browser durability | IndexedDB atomic writes, CAS, visible save failure and retry, exports/imports; explicit persistence request | Actual IndexedDB campaign survives closing/reopening persistent Chromium profile |
| Pre-action writer ownership | Web Locks over game/campaign plus persisted revision checks, unsupported contexts fail closed | Actual Chromium second-tab Web Lock denies mutation visibly before engine POST |
| Native durability | SQLite user-data library, atomic linked writes/imports, CAS, enabled only for local application mode | Actual HTTP/frontend transport and process restart verified |
| Native ownership and origin | Process-lifetime SQLite ownership, crash release, canonical frontend origin, loopback-peer guard | Separate-process ownership/crash/restart and ASGI peer tests pass |
| Normal native launcher | Source/frozen explicit --web dispatch; explicit directory, environment and frozen-default precedence; launcher guards installed whenever enabled | Launcher regressions and actual source command restart audit pass |
| Native served-origin API address | Default same-origin config; explicit Vite override preserved | Config regressions and changed-port actual transport audit pass |
| Simulate remaining fixtures and playoffs | Core engine, one committed final per game, cancel between games, legal final checks, derived seeding/advancement | Rendered simulation, postseason advancement and champion checks pass |
| Portable backups and compatibility safety | Opaque checkpoints; new imported identities; atomic active bundles; no chart content; reject unknown schemas/changed bindings | Unit, native HTTP and Wasm verified |
| Accessible dialogs, mobile tables and visuals | Labeled row editors, keyboard/Escape/focus controls, overflow containers | Actual keyboard/Escape/focus, 390px tables and independent screenshot review pass |
| Packaging and guides | Explicit browser registry allowlist; native SQLite modules/spec; maintained season/save/web guides | Packaging tests pass; final bundle checks recorded below |
| Full regression | All thirteen gates on `2618016`, including core and clean export (12,029 each), backend 682, frontend 593 and 39 browser cases | Pass; exact receipts and CI in [current readiness](release-1.12.2-readiness.md) |
| Native release artifacts | All five actual v1.12.2 downloads pass native inventory, UI/game/chart, log and shutdown verification | Functional qualification passes; Mac first-launch security limitation remains explicit |

## Runtime receipts

Ignored, local receipts under `.ai-audits/season-ui/`:

- `campaign-node-wasm.json`: actual Pyodide campaign, checkpoint, fixed-rule, import/relink,
  simulation and native-registry-without-SQLite checks. The final receipt hash must match
  the guide-bound `python.zip`; rebuilding guides changes that hash.
- `native-http.json`: actual frontend native-library transport, SQLite atomicity/CAS,
  concurrent backend rejection, canonical-origin rejection and crash/restart recovery.
- `native-crossmodule.json`: actual frontend gameFetch/sessionPersistence/repositories,
  no IndexedDB, injected lock manager, real HTTP/SQLite action/autosave/restore/relink;
  concurrent/stale writers rejected before raw engine POSTs. This does not certify browser
  Web Locks or IndexedDB.
- The normal-launcher audit also runs `python -m paydirt --web --port … --no-browser`.
  Its ten-check receipt is `native-launcher.json`.
  A rejected rival exposes no API, but its main loop can remain alive after its server
  thread fails; clean startup-failure exit is not claimed.
- `full-access-recovery-browser.log` and `final-browser.log`: Chromium fails before assertions
  with MachPortRendezvous bootstrap_check_in permission denied (1100), SIGTRAP.
- `final-candidate-browser.log`: the same launch failure on the final candidate, after
  verifying isolated ports on both IPv4 and IPv6. No assertions ran.

Final guide-bound browser archive SHA-256:
`3bef4a363b7cef660ec58c1028391a5d223b7e2473aad2bd1a87e93bc0498117`.
The final 18-check Node/Pyodide and eight-check actual browser receipts match this archive. Node runtime evidence does not
qualify actual browser storage, controls or visuals.

The current verified preview at <http://127.0.0.1:18785/> uses isolated native data under
`.ai-audits/season-ui/final-preview-native/` while its process runs. Its developer launcher
serves the current compiled frontend. Earlier libraries, including `preview-native/`, remain
separate. This data is local-only and ignored; no remote backup is verified. Export important
preview campaigns before stopping/resetting the machine.

## Completion rule

Do not mark the goal achieved or the umbrella resolved from code presence, unit tests, or
Node runtime receipts. Actual game/recovery/focus/mobile evidence is complete locally. Original combined-run
failures and their passing follow-ups remain explicit below.
No commit, push, release, downloaded-artifact health claim or remote preservation is included.

## Browser validation resumed after configuration restart

Chromium launches in the refreshed root session with Full Access. Existing agents
retained their earlier sandbox, so actual browser commands run in the root session.
The first real HTTP browser suite passed 14 of 21 tests; its failures exposed
checkpoint timing assumptions, obsolete save-status assertions, and a missing
visible kickoff/try conflict error. The latter is fixed test-first, including a
retry for a rejected automatic try; focused/full frontend regressions pass.

`native-browser.json` verifies real UI saving, Chromium Web Locks denial before
engine POST, reload/resume, and closing Chromium/backend followed by restart on
changed origins. Screenshot review found that this state-only receipt missed a
lost kickoff history row. History recovery therefore remains incomplete until
fixed and rerun with exact log assertions. The earlier MachPort blocker is no
longer a blocker for the refreshed root process. Browser-only full games and the
rendered season/mobile/restart checks still require a stable final-candidate run.

## Refreshed final-candidate evidence (19:18 UTC)

`native-browser.json` now passes eight actual Chromium checks, including a second-tab
Web Lock rejection before mutation, exact canonical play-log recovery on reload, and
closing Chromium/backend then resuming from SQLite on changed origins.
`wasm-browser-recovery.json` passes eight checks on the archive above: served-byte
hash verification, historical calendar, custom mixed-era season, independent exhibition,
real kickoff/save, fresh-worker recovery with exact history, and zero HTTP API calls.
`campaign-node-wasm.json` passes 18 checks on the same hash. Independent visual review
of all eight refreshed screenshots found no new blocking visual defect.

The rendered season desk and pending-procedure suites previously passed six tests:
custom scheduling/followed-team views, all supported team statistics and leaders, real
simulation/postseason, persistent-profile restart, dialog keyboard/focus, 390px layout,
penalty/end-zone decisions, halftime and an expired touchdown still owing its PAT.
Full final regression and complete browser games remain in progress.

Real full-game validation exposed lazy CPU `random.Random` fields omitted from the
checkpoint codec. The closed explicit codec now preserves all three independent CPU
streams; 31 focused regressions pass with 91% checkpoint coverage. History parity fixes
retain canonical timestamps, turnover/big-play/score markers and engine-owned kickoff
origin. Five kickoff-origin baseline failures became passing regressions; 44 focused
history/checkpoint tests pass. The sole core change adds an engine-owned display receipt,
without changing kickoff calculations or random calls.

The stalled 19:03 full runner was terminated after diagnosis: existing CLI `-p -w 10`
was mistaken for the Web launcher. Four bounded source/frozen regressions demonstrated
the failure; 37 CLI and 12 launcher tests now pass. Standalone `-w` still selects Web.
A fresh unbuffered full runner with clean export is running on the fixed source.

`result-review-final-browser-results` passes the actual rendered result-review flow:
cancel leaves the ledger unchanged, unchanged confirmation is idempotent, a changed
trusted engine final produces revision two with prior history retained and recomputes
team totals, and all four temporary preview engine sessions are deleted. Correction
requests contain identities/revisions rather than client-authored score/stat totals.
The initial test setup bypassed the runtime response cache; supplying its authoritative
test-fixture response fixed setup without changing production behavior.

The first final-archive complete-game run was superseded before completion because its
test observer repeatedly serialized complete histories/checkpoint exports, creating a
multi-gigabyte diagnostic trace. The bounded observer retains latest state/catalog/ID,
scalar progress, 40 recent diagnostic messages and all errors. Two standalone controls
confirm genuine application responses remain unchanged (100% helper lines, 84% branches).
All gameplay, quarter, halftime, final-score, fresh-game and zero-HTTP assertions remain.
Replacement evidence is under `bounded-final-wasm-browser-results`; archive unchanged.

## Full-game findings after the 19:18 candidate

The bounded observer allowed full-game validation to reach halftime. A real fast-click
race executed an additional play after an engine response reported Q3/15:00 with
`halftime_pending`, before the overlay settled; Q3/14:55 under the halftime overlay is
failed acceptance. The 15:00 assertion is retained. Test-first halftime guards now
block normal snaps, CPU execution, punts and timeouts until acknowledgment and the
actual kickoff; owed PAT remains available. Baseline three failures/two controls,
plus a separately failing stale-callback case, now pass. All 13 PlayingPhase suites
pass 101 tests; module coverage is 82.73% lines and 82.64% branches.

Separate 1977/1983 failures were stale test-driver action selection: penalty decisions
were enabled while defense controls correctly disabled. The driver now reacquires
a newly rendered decision without changing action budgets, assertions or production.
A scope audit identified missing year-local exhibition name search and per-counter
coverage labels for partially populated imported boxes. Both are being completed;
domain totals/rate denominators already use known-game coverage. The final frontend
bundle and browser receipts require rebuilding after these UI changes.

## Frozen UI candidate (19:28 UTC)

Year-local name search and explicit per-counter known-game coverage/Partial labels are
implemented. Baseline two expected failures with 17 controls; five focused suites now
pass 34 tests. TeamSelect coverage: 98.69% lines/89.23% branches; SeasonDesk: 87.38%
lines/83.27% branches. Remaining branches are existing create/edit/sim/export/display
paths outside those focused tests. The season guide documents the behavior.

The rebuilt Python archive hash above supersedes f318… because the bundled guide
changed. Its actual Node/Pyodide audit passes 18 checks and actual built Chromium
recovery audit passes eight (including served-byte hash and zero HTTP API requests).
Native Chromium restart/lock/exact-history audit passes eight checks again on the
frozen source. Complete browser games run under `qualified-wasm-browser-results`.
No commit, push, release or verified remote preservation has occurred.

## Kickoff guard and final verification pass

The 28-test HTTP browser suite passed in full at
`.ai-audits/full-regression/20261118T193712Z/summary.json`, including two complete
home/away games, halftime/finals, all recovery procedures, correction revisions,
custom season statistics/postseason and persistent-profile restart. Updated screenshot
review found no blocking desktop/390px layout problem; search/Partial states were
not pictured and retain focused component evidence. Backend now passes 610 tests
(including seven test-only diagnostic controls), with 430 existing deprecations.

All eight built-Wasm full games completed, but the 1983 test correctly failed its
zero-error assertion: a normal snap was requested while a kickoff was owed, and the
engine rejected it with HTTP-equivalent 400. The UI now blocks normal controls and
stale callbacks immediately on authoritative kickoff state. Three regression failures
became passing controls; 104 PlayingPhase tests pass (82.77% lines/82.73% branches).
An existing end-zone test had manufactured its choice via an illegal normal snap
during kickoff; it now restores the authoritative pending result directly, preserving
all precedence/save/timeout checks and asserting zero engine calls. Its old execute-one
expectation was invalid. No engine/Python changes or error filtering were introduced.

The atomic test-helper change required updating its synthetic DOM stub: four setup
TypeErrors became six passing controls, retaining preferred/alternative/unavailable
assertions and adding disappearance/CSS visibility. Full frontend passes 558 tests.
Both builds pass with existing Browserslist/mixed-import warnings. Python archive
remains the hash above; browser JS is now `index-Dte-4LAD.js`. Complete final-source
browser evidence is being collected under `kickoff-guard-final-wasm-results`.

One earlier season simulation was safely rejected with zero committed results.
A 2,000-seed public-2026 real-engine sweep could not reproduce it; no engine fix,
automatic retry or weakened final guard is claimed. The isolated E2E server now
captures RNG state and terminal flags on recurrence, without production changes or
chart narrative. Subsequent rendered simulation and postseason checks passed.

The verified current preview is <http://127.0.0.1:18785/>. Its ignored developer
launcher `.ai-audits/season-ui/serve-final-preview.py` points only that process at
`frontend/dist`, because the normal source launcher otherwise reads the older
`backend/web_static` build. Shared static assets and earlier preview sessions were
left untouched. It uses isolated SQLite data in `final-preview-native/`; rendered
Seasons and native capability were checked. Preview data/evidence is local-only.

## Final command provenance

The original combined runner at `20261118T191821Z` completed: core 11,765,
clean-export core 11,765, generated 14-game runner, actual 224-game calendar plus
nine playoff games, both AI audits, both released-chart gates and lint all pass.
Its browser step failed four now-investigated cases; the original summary remains
12 pass/one failure/zero skipped and must not be relabeled green.

The complete HTTP browser command was rerun through the same runner after fixes.
`20261118T194658Z/summary.json` passes all 28 tests on the final kickoff-guard UI,
including both full games (171 and 150 normal executions; one halftime each),
all pending procedures, correction, statistics/postseason and persistent restart.
Backend full suite now passes 610 tests with 430 existing deprecations; final frontend
passes 558 tests across 71 files. Both final builds, documentation regression and
diff whitespace checks pass. These follow-up receipts supersede only the relevant
older candidate checks; no single all-green combined summary is claimed.

Native and built-Wasm browser recovery receipts were refreshed at 19:46 UTC and
each pass eight checks. The final native preview also verifies trimmed, case-insensitive
year-local search and clearing the query after changing year, with a screenshot.
Its isolated asset override avoids replacing shared older native static assets;
release CI separately copies the new frontend into the native bundle before packaging.
No downloaded-artifact/native release qualification or remote preservation is claimed.

## Local acceptance complete

The final `kickoff-guard-final-wasm-results/.last-run.json` reports passed. All five
actual built-browser tests pass (8.3 minutes): complete public inventory/chart loading
and eight complete games, home and away for 1977/1983/2024/2026. Every year retains
all-quarter/halftime/final/fresh-game checks, zero worker errors and zero HTTP API
requests. The 1983 kickoff-position error no longer occurs. Native/Wasm recovery,
HTTP28, frontend558, backend610, core11,765 in both working tree/clean export,
generated season/AI/chart/lint/build checks provide the scoped evidence above.

This completes local implementation acceptance for all six slices. FLOW-036 remains
open for owner review/integration; no commit, push, release or verified remote copy
was made. The original combined runner remains 12 pass/one failure and is retained
verbatim; passing final-source follow-ups are separate receipts. Before publication,
follow the applicable push/release gates rather than treating this as artifact health.


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

## 2026-11-18 — Division landing view and team kicking

Owner requested division standings on the first season screen, NFC before AFC, and team field-goal statistics by distance. Overview now places standings before recent results; conference columns stack below 1050px. All divisions are visible by default even when following a team; custom conference/division membership remains authoritative. A previous followed-team unit/browser expectation changed intentionally because it hid the other division races. Conference filters retain division grouping.

Test-first evidence: initial grouping regression failed on the previous followed-division default with 22 controls passing; kicking regression failed on missing FG headers with 23 controls passing; priority regression failed because recent results preceded standings with 23 controls passing. All 570 frontend tests now pass. SeasonDesk focused coverage measured 88.88% lines /85.75% branches before the final ordering change; remaining existing gaps include management actions/error paths. Real Chromium confirmed NFC left of AFC on desktop and above AFC on a 390px phone without page overflow. Evidence remains ignored under `.ai-audits/season-ui/standings-kicking/`. Backend kicking validation is still in progress; this is not a publication receipt.

### Additional team statistics requested during validation

Owner additionally requested distinct Offense/Defense/Kicking categories, defensive interceptions/fumble recoveries/sacks, offensive attempts/completions/interceptions/rush attempts, completion percentage, team passer rating and yards per passing/rushing attempt. The UI now exposes three category buttons, a category heading, offensive passing/rushing column groups by ordering, and explicit defensive labels. Defensive takeaways/sacks use opponents’ authoritative offensive counters, with a synthetic domain control verifying both sides. NFL team-stat pages informed the column organization; the Hall of Fame’s NFL formula is the documented passer-rating reference.

Test-first UI baseline: category/defensive-label regression failed on the missing category group (24 controls passed); offensive volume/efficiency regression failed on missing pass-attempt headers (25 controls passed). Existing assertions changed from 14 to 22 columns because eight requested volume/rate fields were added; coverage assertions now find columns by their labels so column organization can improve without weakening numerical/coverage checks. No existing numerical expectations were relaxed. Backend attempt/rate tracking is still undergoing focused validation.

The first integrated kicking browser run passed 11 checks, including season simulation, kicking totals and checkpoint recovery. Its complete-game check failed when the page execution context disappeared, with the browser back on the main menu; builds were running concurrently. Preserve that failure under `.ai-audits/season-ui/standings-kicking/browser-first/`; rerun with source/build work frozen before claiming complete-game acceptance.

### Final team-statistics source and focused evidence

Final review caught offensive receiver-fumble recovery TD attribution. The new regression failed first (one failure, 31 controls); retaining the completed pass now counts an attempt/completion without inventing a passing TD from the recovery touchdown. Ordinary pass TD controls remain passing. Final focused combined suites: 195 passed, with offense_stats and kicking_stats at 100% lines/branches, campaigns 94%, save_game 72%, game_state 81%, and game_engine 27% in the deliberately narrow FG/attempt suites. The existing engine’s unrelated gameplay branches are outside that coverage selection; new classification/attempt/penalty/recovery paths are covered. Browser archive builder coverage is 100%. Checkpoints and campaign_operations each measured 88% with 104 focused backend tests passing; remaining gaps are existing malformed-state, optional transport and error paths, exercised in part by broader backend/native integration. SeasonDesk measured 89.34% lines/86.37% branches with all 26 focused tests passing; remaining gaps are existing management/error actions and modal branches, not exclusions. All 572 frontend tests pass. Full backend: 657 passed with 480 existing Pydantic deprecation warnings.

Both frontend builds passed. Actual built Pyodide runtime passed ten distance-band kick/checkpoint roundtrips plus passing/rushing counter checkpoint roundtrip; archive hash is in the ignored wasm receipt. The initial offense Wasm probe used the penalty resolver mock with the ordinary run_play API and therefore failed its counter assertion; correcting that probe to mock run_play’s actual resolve_play seam passed without a production change. Preview at port18785 was rebuilt/restarted using the existing native library after verifying a row-identical SQLite backup locally. Live rendered preview confirms all divisions and category controls; no user result edits occurred for this enhancement.

The obsolete broad core run was interrupted after 2979 passes/73 errors because new owner requests changed engine source after import; each error explicitly reported loaded-runtime/source mismatch. A fresh-process paired audit control passed. A second run was intentionally interrupted after 2474 passes for the fumble-TD review fix before qualification. Neither interrupted run counts as full regression. Final stable-source core and complete-game browser validation remain in progress. No commit/push/release or remote backup is claimed.

Final stable-source rendered browser validation: all 12 selected checks passed in 3.0 minutes, including both full games (38–24 and 41–34), real campaign simulations reconciled against engine-derived offense/defense/kicking counters and efficiency, save/restore decisions, season finals, persistent browser restart, and NFC/AFC desktop/phone geometry. Source/builds remained frozen during this run. Original invalid/interrupted attempts remain disclosed above. Final broad core run still in progress; issue tracker review left FLOW-036/STAT-006 open for integration.

Validation boundary detail: optional attempt metadata validates allowed keys, integer bounds, completions/TDs versus attempts and TDs versus completions. Campaign result/import validation also rejects completions plus interceptions exceeding attempts. The checkpoint codec preserves its existing separately serialized interception-counter compatibility (including synthetic legacy/manual counter edits) instead of adding a new cross-record rejection there. Existing save/load assertions were retained; no skips or coverage exclusions were added.

### Final acceptance complete (2026-11-18)

Stable-source complete core suite: **11,839 passed in 643.33s**, with no skips or warnings reported. Full backend: **657 passed**, with 480 existing Pydantic deprecation warnings; full frontend: **572 passed**. All **12 selected actual Chromium checks** passed, including both complete games and real season-stat reconciliation. Focused coverage suites: 195 core/package cases, 104 backend cases, 26 SeasonDesk cases. Ruff and documentation checks pass. Browser/native frontend builds pass; the final browser archive (including updated guide formatting) passed ten kick checkpoint roundtrips and an offensive counter checkpoint roundtrip in actual Pyodide; see `wasm-receipt.json` for the final hash. Live native preview was verified at port 18785. The original recovered 21–20 result remains revision 1 and saved checkpoint revision 309; no user results were altered by the statistics enhancement.

All current requested refinements are implemented locally. This is not a new complete pre-push regression: clean-checkout, season/AI/chart gates and the remainder of the full browser suite must still run before any push. No commit, push, release or verified remote preservation is claimed.

## 2026-11-18 21:40 — Column sorting, coverage labels and recovered legacy statistics

Season table headers now sort numeric values highest-first and names alphabetically; repeated activation reverses direction. Raw backend numbers supply statistic/leader keys, keeping full precision and excluding formatted percentage/coverage text. Missing values remain last in either direction; ties preserve original order. Division sorting keeps conference/division membership intact. Direction is visible and exposed through aria-sort; native buttons support Enter/Space. Schedule action cells remain controls. Default unsorted ranking is retained until a header is selected.

Zero-coverage completed counters now say **Not recorded**; **Partial** is reserved for nonzero incomplete coverage. Existing zero-coverage expectation deliberately changed from `0/3 games · Partial` to `0/3 games · Not recorded`; missing numeric values remain dashes. Test-first baseline: two sorting regressions failed on missing header buttons with 26 controls passing; adding the coverage-label expectation yielded three expected failures/25 controls. Final 28 focused cases pass, covering numeric direction, 100 versus 9, negatives, zero versus unknown, raw precision, coverage staying with the team, per-game reordering, alphabetical ordering and division boundaries. SeasonDesk coverage 89.72% lines/87.13% branches; remaining gaps are existing management/modal/error paths. All 574 frontend tests and four real Chromium season checks pass; keyboard/browser sorting is included. Both frontend builds and documentation checks pass. No gameplay/backend source changed in this follow-up.

The owner’s old 1983 final predates kicking/attempt counters. A private, document-specific offline repair aligned all 157 canonical play outcomes with preplay saved history after excluding five extra-point records. Typed possession/LOS plus all five typed FG outcomes recover NO 0/2 (41-,48-yard misses) and STL 2/3 (51-,44-yard makes,34-yard retained-foul miss). Five accepted scrimmage penalties are excluded; no combined spikes or ambiguous scramble/fumble TD attribution exists in this document. Reconstructed attempts/completions/passTD/rush attempts are NO 23/13/1/38 and STL 38/21/0/22; all twelve independent existing yardage/sack/INT comparisons reconcile exactly.

Normal checkpoint roundtrip was byte-structurally identical before enrichment. Only four optional statistics dictionaries changed in the saved engine; all scores, history, session fields, RNG and prior counters remain identical. Normal correct_campaign/legal-final/team/rules validation revised result 1→2 while retaining the exact old result in history; repeated completion is idempotent. Root reviewed the proposal, verified a row-identical/integrity-checked local SQLite backup and every source row hash, then applied the normal native library atomic CAS command: game 309→310 and campaign 312→313. Rereads and actual rendered preview verify every offense/defense/kicking cell for Saints/Cardinals now has recorded coverage, FG totals match, and NO 21–STL 20 remains one completed game. This is a narrowly verified repair, not unrestricted automatic reconstruction for other legacy saves. Private source/history/proposal/backup/receipts remain ignored under `.ai-audits/season-ui/standings-kicking/legacy-recovery/`; no remote backup claimed.

Evidence for sorting is in ignored `.ai-audits/season-ui/season-table-sorting/`. Existing core/backend/full-game receipts above remain separate; no new pre-push qualification, commit, push or release is claimed.

## 2026-11-19 — v1.12.0 final local candidate qualification

The final production source is `c0b4292`; test-only `49afba9` updates obsolete display-save E2E setup without changing packaged inputs or weakening game assertions. All thirteen root regression gates pass, including 11,952 core tests again in a tracked-files-only export, 667 backend tests, 588 frontend tests, the build, all 34 real-engine browser cases, every required schedule/AI/chart gate and lint. No gate is skipped. Earlier failed/interrupted invocations remain separately recorded.

Fresh Wasm acceptance passes all 90 teams and eight complete games across the four bundled years. The rebuilt Mac candidate passes ordinary and mixed-edition campaign create/restart/reopen checks, with all thirteen team-stat categories and identical exports. Individual player statistics remain excluded. Overview contains division standings and recent results; the duplicate Standings tab is removed. Actual mixed 1983/2024 same-franchise play preserves identities, both roles, charts, rules and canonical saves.

See [release readiness](release-1.12.0-readiness.md) for exact receipts, artifact hashes, test-first failures, coverage gaps, E2E setup changes, warning review and tracker decisions. FLOW-020, FLOW-021 and STAT-006 are closed from actual acceptance; FLOW-036 remains open for release/preservation follow-through. Upstream exact-commit CI, remote preservation and downloaded published-package health are distinct gates; none is inferred from this local acceptance. The private archive is locally readback-verified for the owner to upload, with final evidence supplementation and remote verification status recorded separately.

The first qualified push exposed two existing test reliability defects in upstream CI: random-sampling extra-point odds and chart observation starting before setup acknowledgement. Test-only `1fbf09c`/`b457594` make these checks deterministic without changing production or weakening assertions. The full thirteen-gate qualification was repeated: core/clean core 11,952 each, backend 667, frontend 588/build, full 34-case browser regression, every required gameplay/AI/chart gate and lint all pass. Full evidence and the retained intermediate failures are in the release readiness note. Exact follow-up CI remains pending until its push; local package acceptance applies to unchanged product bytes.

## Verified v1.12.2 publication — 2026-11-19

The six-slice umbrella is closed. The [current release readiness](release-1.12.2-readiness.md)
binds all thirteen pre-tag gates, exact-commit upstream CI, actual five-platform-package
functional receipts and asset hashes to `2618016116f4bf4489924aa63e6ca528d3332cce`.
Earlier local/Wasm/native feature and restart receipts remain their own evidence;
packaged smoke checks are new-game checks, not a claim of complete native games.
Both downloaded Mac bundle resource seals pass. Fresh quarantined Apple Silicon
launch is rejected by Gatekeeper without an override; ad-hoc signing is not
Developer ID signing/notarization. Browser play remains primary.

Local private base/delta archives are readback verified; the owner reports private
upload complete. Independent remote readback remains unavailable. DATA-047 is closed after actual
downloaded ARM corrected-label selection/chart/kickoff/scrimmage checks plus all
five native API profiles; STAT-007 and DATA-051 remain open follow-ups. No individual player statistics are introduced.

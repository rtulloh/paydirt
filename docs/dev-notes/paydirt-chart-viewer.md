# Paydirt chart viewer implementation and validation

Developer record, 2026-11-05. Implemented locally; not committed or released.

Current browser validation: after restarting Codex, the agent-run full
`npm run test:e2e` suite passes all three specifications. See the restart
confirmation below; earlier permission failures describe the initial attempts.

The Bowl Bound chart-viewer worktree supplied the interaction reference: a lazy
Charts control, native dialog, team selection, independent chart sections, error
recovery, and server-supplied labels/colors. Paydirt's sheets instead follow its
original white backgrounds, bold black grids, numbered rushing/passing columns,
and grouped A–F defenses. Special Plays shows auxiliary B/QT/fumble columns;
Special Teams shows kicks, returns, field goals, and extra points.

The read-only API serializes the current engine-loaded chart objects. It neither
loads caller-selected paths nor changes the engine. CSV retains result tokens
but not original workbook fills, so colors are reconstructed from those tokens.
No private chart data, workbook images, or historical logs were copied.

Test-first baseline: backend had 23 expected failures for the absent chart API
with one passing game-state control; frontend had six expected failures for the
absent Charts control with one passing normal-play control. Existing test
expectations and skips were unchanged.

Validation: 24 chart API tests pass; the full backend suite has 320 passes.
The frontend has 287 passes and one existing skipped kickoff test. Build, lint,
chart-loader/documentation checks, and offline-guide API checks pass. Chart
serializer statement coverage is 99%; viewer statement coverage is 100% and
branch coverage is 89.47%. Existing Pydantic and Browserslist warnings remain.

Browser verification is pending: both normal and escalated Playwright attempts
failed before tests because this environment denies binding the isolated server
to port 8000. A separate Chromium launch also failed with a macOS Mach-port
permission error, including an escalated attempt. The new real-engine chart
browser test remains enabled; these failures are not skips or passing checks.
No push or full-season/AI audit was performed.

The separate tracker-format check found a pre-existing failure in the uncommitted
FLOW-013 ticket: required empty `resolved-at`/`closed-at` fields are missing.
Those empty fields were subsequently added; its status and existing evidence were
preserved. The tracker-format checks now pass. The browser suite collects
all three specifications successfully, including the new chart test.

Reviewed the per-issue tracker, including resolved browser/display issues.
There is no new completed browser play-test evidence to close any ticket.

## User-run browser results and focus correction

The user's normal terminal runs Chromium successfully. Both full games pass
(35–42 and 23–24), as does the offline guide. The chart test confirms rendering,
team switching, all four sections, mobile scrolling, modal focus containment,
and unchanged game state before failing the final Escape focus-restoration
assertion. This is an application lifecycle bug, tracked in
[AUD-027](issues/AUD/AUD-027.md), rather than a browser-installation problem.

The fix closes the native modal before focusing the CHARTS button, releasing
the game's native inertness. New tests model that missing browser behavior:
two expected baseline failures, seven passing controls, then nine passing
chart cases after the fix. The browser test retains its Escape assertion and
also checks closing through the button. Frontend validation now reports 289
passes and one existing skip; the build passes. Statement coverage remains
100%, with 89.61% branch coverage. Agent-run browser verification remains
blocked by the port-binding permission error; the corrected focus behavior
still needs real-browser confirmation. No existing test expectation changed.

The subsequent user-run focused chart browser test passes: 5.6 seconds for the
test, 10.1 seconds overall. Both Escape and Close restore focus. Combined with
the preceding complete-game and offline-guide results, every browser
specification has now passed against the applicable changes. The focus fix
changed only the viewer close procedure; the full suite has not yet been rerun
as one invocation after that fix.

The user then enabled Full access so future browser runs can be agent-owned.
Retries during the same running turn still report the `opencode-import`
permission profile, macOS Seatbelt sandboxing, an active command network proxy,
and local binding disabled. The runner rejects access to `127.0.0.1` even with
an escalation request. No persistent permission configuration was changed.

### Full-access retry and proxy configuration

After the permission refresh, the runner reports `:danger-full-access`, but
macOS still reports sandboxed execution. The command network proxy stays active
with its local/private-network guard enabled. Browser-suite attempts fail before
tests with an explicit block on `127.0.0.1`. A standalone Chromium launch also
still fails at `MachPortRendezvousServer` registration with permission denied.

Updated the user's Codex `[features]` proxy toggle to the supported table form:
the proxy remains enabled and explicitly allows only `localhost`, `127.0.0.1`,
and `::1` at the feature level. The previous exceptions lived only under the
custom `opencode-import` profile, which Full access no longer selects. Existing
permission profiles and the default profile selection were preserved. CLI
configuration parsing accepts the table form. The running proxy has not applied
the new exceptions; a Codex restart is the next diagnostic. This change has not
yet been demonstrated to resolve Chromium's independent IPC denial. No browser
result from these agent attempts is claimed as a pass.

### Restart confirmation

After the user restarted Codex, the agent launched `npm run test:e2e` directly.
Chromium and both isolated services started successfully. All three browser
specifications passed: original-style charts (including both focus-restoration
paths), two complete real-engine games in one session, and the offline guide.
Playwright's last-run result records `status: passed` with no failed tests.
The generated public-team offense and defense screenshots were inspected; they
show the intended white sheets, bold black grids, numbered play columns and
original chart colors. No test or runner configuration was weakened.

Full access, the explicit feature-level loopback proxy exceptions, and a fresh
Codex process together allow agent-owned browser testing in this environment.
The earlier local-network and Chromium IPC failures no longer block this run.
Reviewed the resolved issue inventory after the browser play-test; these
specifications supply no new issue-specific evidence for additional closures.
AUD-027 remains open because its verified fix is still uncommitted. No push or
full-season/AI audit was performed.

## Separate tabs/windows and complete desktop sheets

Implemented locally on 2026-11-05, following the Bowl Bound priority-viewer
worktree's separate-chart interaction. Both launch controls preserve the
selected team and sheet in a standalone URL. The parent modal releases focus
and inertness before returning to play. The shared chart panel renders all four
sections in either shell; the standalone route mounts no gameplay controls or
game-store hooks. Window launch failures leave the modal and new-tab fallback
available. Invalid links do not fetch; expired games show a retry.

Desktop row height and header spacing respond to viewport height, retaining
text at least 12px in the tested sizes. The legend starts collapsed. All four
sheets fit without grid or dialog scrolling at 1366×768, 1280×900, 1440×1100
and 1920×1080. Phone layouts retain readable scrolling. Public-team offense
and defense screenshots were inspected, including the short laptop viewport.

Test-first evidence: 13 new launch/standalone tests failed for the missing
controls and route while nine existing controls passed. A separate collapsed
legend regression failed before the layout change. The first browser geometry
baseline placed the last row at 1470px in a 900px viewport; the new assertions
also caught residual dialog overflow on the shorter laptop screen before the
final spacing correction.

One existing chart test now expands the legend before asserting its contents
are visible. The previous assumption that help starts open conflicts with the
requested complete-sheet layout; the visibility assertion remains intact. A
new browser test initially assumed that reopening charts during the receiving
team's kickoff should default to Offense. Corrected that new expectation to
the existing defensive role; no production gameplay/default-role behavior was
changed and no assertion was removed.

Validation: all 23 chart component tests pass; full frontend validation has
303 passes and one existing skipped kickoff test. Chart viewer statement/line
coverage is 99.14%, branch coverage 93.26%, and function coverage 100%. The
production build passes with the existing Browserslist warning. Eight chart
browser cases pass, including independent tab/window navigation and reload,
both parent kickoffs, expired links, phone scrolling, unchanged game state
while browsing, and all desktop geometry checks. These focused checks used a
temporary runner configuration against the already running development
services and explicitly selected public 2026 teams, preserving the backend
and existing games. The committed isolated-server Playwright configuration
was not relaxed. The two complete-game browser scenarios were not rerun after
this UI extension; their earlier full-suite result remains recorded above.

The accompanying offline guide browser check exposed an IPv6/IPv4 mismatch
in Vite's development API proxy. Its unchanged image assertions failed, while
all eight chart checks passed. Targeting IPv4 loopback fixes the connection;
the guide browser test then passes and a proxied image returns HTTP 200. See
[VAL-016](issues/VAL/VAL-016.md) for the baseline and verification. Reviewed the
resolved issue inventory after the focused play checks; no additional ticket
has scenario-specific confirmation for closure. No push or season/AI audit was
performed.

## Compact Special Plays beside Offense

Implemented locally on 2026-11-05. Offense now places the same engine-supplied
Special Plays table alongside its main sheet at viewport widths of at least
1200px. The two tables align their caption, heading block and 30 roll rows.
Narrower screens stack the strip below Offense. B, QT and fumble recovery cells
are preserved; the roll-number column moves to the right, with a fixed 32px
width inside a 272px strip. The dedicated Special Plays section uses a smaller
900px viewer shell and centers the compact strip. Modal and detached views
share this rendering without additional chart requests or engine changes.

Test-first baseline: three added regressions failed for the absent combined
view and trailing roll column while all 23 existing chart tests passed. The
real-browser 1280×900 case then failed because Offense had no auxiliary table.
After implementation all 26 component cases pass. Eight existing waiting
queries now identify the Offense table explicitly because the view intentionally
contains two tables. No assertion was removed or weakened; the synthetic
auxiliary fixture now exercises B, QT and fumble cells instead of B alone.

Validation: 306 frontend tests pass with the same one existing kickoff skip;
viewer coverage is 99.18% statements/lines, 94.35% branches and 100% functions.
All eight focused chart browser cases pass (43.4 seconds), retaining the
existing focus, state-preservation, tab/window, reload and parent-kickoff checks.
Additional assertions verify adjacency, aligned rows, a strip at most 300px
wide, a roll column at most 36px wide on the right, every loaded auxiliary label,
the smaller standalone section, and phone stacking without horizontal overflow.
Offense and Special Plays screenshots were inspected at 1366×768. The same
temporary configuration uses the running development services and public 2026
teams; the committed isolated-server configuration remains unchanged.

Reviewed the resolved issue inventory after the play checks. These display and
kickoff checks add no scenario-specific evidence for unrelated issue closures.
AUD-027 remains open because its verified focus fix is still uncommitted. No
push, full-season runner or AI audit was performed for this display change.

## Special Plays navigation consolidated into Offense

Implemented locally on 2026-11-05 at the user's request. Chart navigation now
offers Offense, Defense and Special Teams. The independent Special Plays
screen and its smaller-shell styling were removed; the compact table remains
part of Offense in modal, detached and phone layouts. Existing
`view=special_plays` URLs use the normal unsupported-view fallback to Offense,
retain the requested team, and produce new links with `view=offense`.

Test-first baseline: four failures for the still-visible control and old
standalone screen, with 21 passing chart controls. Tests now expect three
navigation options, verify auxiliary cells in Offense before switching sections,
and replace the obsolete single-table screen expectation with both combined
tables on an older link. The independent Special Plays URL parameter case was
removed from the generic standalone-section matrix because that screen no
longer exists; its compatibility behavior has explicit component and browser
coverage instead. No auxiliary-value, geometry, focus or game-state assertion
was weakened.

Validation: 25 chart component cases pass; the full frontend has 305 passes
and the existing one kickoff skip. Viewer coverage is 99.18% statements/lines,
94.26% branches and 100% functions. Build passes with the existing Browserslist
warning. The focused chart and offline-guide browser invocation passes all
10 cases in 47.0 seconds, including the added older-link case and both parent
kickoffs. Reviewed the resolved tracker inventory after play checks; no
unrelated ticket has new scenario-specific closure evidence. AUD-027 remains
open while uncommitted. No push or full-season/AI play audit was performed.

# Corrective chart release preparation, November 6

Development checkpoints only. Source reconciliation, corrected all-team chart
qualification, and complete regression against a frozen final candidate remain
separate requirements. These component results do not approve a release.

## Interface and backend checks

At the 10:34 CST checkpoint, the frontend suite passes **306 tests with no
skips** across 31 files. The production build passes, with the existing warning
that Browserslist's `caniuse-lite` database is eight months old. Local frontend
logs are under ignored `.ai-audits/release-readiness/`.

The formerly skipped kickoff-touchdown test was first enabled without any other
change; it failed because it never clicked KICKOFF and therefore never left the
choice screen. The corrected test performs that user action, asserts the exact
visible touchdown label, then verifies that CONTINUE calls the completion
callback once with the authoritative API state. The old substring assertion
also matched the narrative; the exact label assertion now checks the displayed
result. No production component changed. An intermediate verification used a
matcher unavailable in this Vitest version; replacing it with separate count
and argument assertions preserves the intended check. Final log:
`frontend-unit-03.log` (306 passed, zero skipped).

The backend checkpoint passes **322 tests**, with **21 existing Pydantic v2
deprecation warnings** for `.dict()` calls. This run precedes final source/model
freeze and is not the required final-candidate regression.

The isolated browser checkpoint passes **all 11 tests**, including nine chart
checks, both full real-engine games in one session, and the offline guide.
Chart checks cover four desktop viewport sizes, detached tabs/windows, expired
links and the old Special Plays link. Both games reached halftime and final
screens and exercised defensive timeouts; the first finished 31–24 after 145
plays and the second 41–7 after 150. Log: `browser-02.log` under the same ignored
directory. The initial attempt (`browser-01.log`) could not start because the
selected Python lacked uvicorn; rerunning with the existing backend virtual
environment fixed the environment failure. Existing Browserslist and Node
color-environment warnings remain disclosed. Development services were restored
after the isolated run; port 8152's owner review was never interrupted.

No player-guide change is needed for this test-only restoration. The engine's
new chart token has its own implementation note and requires a player-facing
chart key when the generator integration is complete.

## Clean public core checkpoint

The immutable 959-file development snapshot collected 9,803 tests and finished
with **9,633 passed, 170 failed, zero skips**. It captured the new source and
retained-incompletion tests before their implementations converged. All failures
are confined to those two new modules (36 reported-gain, 134 retained-incompletion);
there are no historical-data missing-file failures. Snapshot hashes stayed
unchanged. This is a failed development checkpoint, not a final regression pass.
The source test author must distinguish fixture/setup failures from meaningful
behavioral baseline failures; the full snapshot's failures alone are not a
test-first claim.

After the live implementations converged, an independent focused run of those
two modules passes **183 cases** (146 retained-incompletion, 37 reported-gain).
Log: `source-engine-convergence-01.log`. The final frozen candidate still needs
the entire clean public suite and required full regression, including coverage
and all standalone audits. VAL-010 remains open pending that complete result.

## Other findings

The retained-fumble/incompletion implementation reproduced the already tracked
two-point conversion clock side effect (RULE-001). Its passing control confirms
the new subtype preserves ordinary incompletion behavior; it does not repair or
certify untimed conversion mechanics.

## Owner play-test follow-up: Blitz and save feedback

The owner's November 6 review exposed a missing F-to-Blitz API mapping and
SAVE GAME's absent confirmation. Ten new Blitz regressions failed with fourteen
passing controls before the mapping fix. Two save-feedback regressions failed
on absent messages after confirming real browser storage success/failure. All
new cases pass after implementation. No existing unit assertion or skip changed.

The full backend now passes 350 tests with 20 existing Pydantic warnings; the
frontend passes 308 tests, zero skips. Build, documentation and edited Python
Ruff checks pass, with the existing stale Browserslist warning. Independent
Chromium verification against the updated isolated review service on 8154
executes F through the actual button and real engine (HTTP 200, response F),
saves the resulting position/history and observes the success message with
zero page errors. The owner's existing game and saved browser history on 8152
remain intact; no backend restart or field-position correction was performed.

The full-game browser policy now rotates all six defenses, requiring each
to execute in both games, and checks save confirmation. The old literal-A
timeout assertion now checks the exact selected defense on scrimmage plays
and the existing A placeholder on CPU kick confirmations. Its first expanded
run passed all ten other browser cases but failed on that kick-placeholder
assumption; the corrected full-game rerun is separate evidence. These checks
remain development checkpoints, not final source/model-qualified release approval.

The corrected full-game rerun passes both real-engine games: 17–27 after 158
execution calls and 38–37 after 151. Each exercises all A–F formations, browser
save confirmation, exactly one halftime and six human defensive timeouts, then
reaches final scores and clean NEW GAME state. No API/browser error occurs.
The ten other browser checks passed in the preceding full-suite attempt;
the driver-only correction was verified with the targeted full-game rerun.
Logs are `browser-blitz-save-01.log` and `browser-blitz-save-full-02.log`.
Normal development services on 8000/5173 were restored afterward. Existing
Browserslist and Node color-environment warnings remain. The resolved-ticket
review added specific valid-Blitz evidence to VAL-012, without claiming that
these games establish unrelated issue-specific coverage or release readiness.


## Upstream release execution: supported Python matrix

The package now declares Python 3.10+ and classifiers for 3.10, 3.11 and 3.12,
but the hosted test matrix still included 3.9. New source adapters use standard
library APIs introduced in 3.10. A new regression compares the workflow matrix
with the package's independent supported-version metadata: it first fails on
the extra 3.9 entry, while twelve existing workflow controls pass. The workflow
now tests the three declared supported minors and keeps independent matrix
failures enabled. All thirteen workflow checks pass afterward.

One existing expectation changes from four minor versions to the three declared
supported versions; the former 3.9 expectation no longer matched the package
contract. No runtime assertion, chart gate or supported-version test was skipped.
The developer guide is updated in the same change. Evidence remains ignored under
`.ai-audits/release-readiness/upstream-release-01/`. This narrow CI correction
establishes neither corrected-chart source fit nor release readiness.


## Upstream release execution: dynamic backend helper

Release packaging omitted `chart_viewer.py`, which the dynamically loaded
`routes.py` imports at runtime. PyInstaller cannot infer that dependency through
the file-based route loader. A standard-library regression stages the actual
spec's backend data and resolves the routes' local imports without any backend
dependency or historical chart data. Before the fix it fails specifically on
missing `chart_viewer`, with the four existing packaging controls passing.

The active `paydirt.spec` now places that helper directly under the bundled
backend import directory. This preserves its runtime import path; the helper
must not be placed in an extra `chart_viewer.py/` directory. No game or viewer
behavior and no existing test expectation changed. Full release-executable and
artifact checks remain separate from this dependency-inclusion regression.

The helper review also found its `paydirt.chart_layout` dependency outside the
static import graph from `paydirt_runner.py`. A separate regression walks the
entry-point graph and checks the dynamically loaded backend's actual core imports;
it failed only for `paydirt.chart_layout`, with five passing packaging controls.
The active spec now declares that hidden import. This check does not execute
PyInstaller or replace a built-executable API check. No runtime source changed.


## Upstream release execution: isolated public checks and AI audit

A fresh intended-public snapshot copies all 1,026 tracked or intended new
nonignored files byte for byte, without ignored sources or private seasons.
All 10,564 core and 423 backend tests collect there. Focused source staging,
preparation, typed bindings, CI, packaging and documentation checks pass 205/205.
The complete isolated backend passes 423 tests with 19 existing Pydantic `.dict()`
deprecation warnings; frontend installation succeeds, all 350 frontend tests pass
with no skips, and the production build passes. Its Browserslist warning remains.
Installation reports existing inflight/glob deprecations and 17 npm audit
advisories; no dependency version or lockfile changed. No source file changes
during these checks. This is not the final full clean-core regression or a
source-qualified chart freeze.

The exact public 2026 16-week seed-8306 paired AI command passes all 32 games,
with 4,878 calls and all 217 situation groups independently reconciled and
reviewed. No ordinary concentration warning occurs. Engine/runtime, harness
and public chart bytes remain unchanged before/after the run. The report SHA is
`1323eb567f3ffb61a2737bbb0c82d6b3948d8718ad8a867554987a5d96a1455a`.
AI-008 and AI-009 record the bounded call-share evidence and resolved-ticket
review; unrelated issues are not closed from game completion alone. Private
cohort checks, source/fit acceptance and browser E2E remain separate requirements.


The exact required local1983 paired audit also completes all 448 games with
65,212 calls and 3,181 situation groups independently reconciled, including
exact CSV/JSON agreement and unchanged runtime/harness/input bytes. Three
legacy-balanced ordinary advisories are retained and reviewed in AI-008/AI-009;
there is no Hard ordinary concentration warning. Private reports and input
identities remain ignored/local. This current-runtime completion does not
promote corrected generated charts or waive source/fit and browser gates.


Fresh standalone current-runtime validation passes the 14-game runner and the
actual 1983 calendar: 224 regular games, nine simulated playoff games with no
ties, and all 16 private historical reproductions including both mandatory
untimed-down events. Independent receipt review confirms exact regular fixtures,
16 games per team, legal final states and every box/period/scoring identity.
Runtime, schedule and chart bytes stay unchanged. This validates the current
canonical inputs; corrected-chart source/fit acceptance remains separate.


The original full core run completes with 10,551 passes, five failures and five
setup errors at 85% coverage. Four failures use pre-collected mocked audit reports
without the required explicit interception-return policy; one uses the old Python
matrix expectation. Their corrections were already focused-verified. All five
setup errors share a public synthetic punt fixture calling the internal audit task
with four fields after its contract added a required fifth policy boolean. The
focused unchanged fixture reproduces five setup errors with five passing controls.
It now explicitly declares the existing default `False`; no assertion, production
code, runtime policy or skip changes. Final fresh full-core verification is required.

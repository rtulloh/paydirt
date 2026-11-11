# DATA-047 bundled team-name audit

Development verification, November 10, 2026. This is a metadata correction,
not a new chart generation or historical-fit qualification.

Reviewed all 90 tracked bundled team.yaml files: 28 in 1977, 28 in 1983,
32 in 2024 and the two fictional 2026 sample teams. Found three wrong
geographic associations, all in 1983:

| Team | Before | Corrected association and label |
| --- | --- | --- |
| Chargers | LAC '83 | San Diego, SD '83 |
| Cardinals | ARI '83 | St. Louis, STL '83 |
| Raiders | OAK '83 | Los Angeles, LA '83 |

Other metadata nicknames and abbreviations were consistent with their seasons.
Baltimore Colts in 1977/1983, Oakland Raiders in 1977, Houston Oilers and
Washington Redskins in 1977/1983, and the modern 2024 identities remain correct.
Established abbreviation variants (for example SFO/SF and SDG/SD) are accepted.
Directory IDs and nickname-only team names remain stable.

Before editing release metadata, the standalone regression
`python3 scripts/audit_team_names.py` failed on exactly these three labels;
the remaining 87 were passing controls. After editing, all 90 pass.
Four additional synthetic/public-2026 tests verify that metadata short names
reach the loaded chart; these controls also passed before the edits.
No production Python or frontend code, gameplay charts, test expectations,
fit tolerances or release policies changed.

The Python 3.9 default interpreter caused 19 fixture setup errors in the wider
focused suite; it is below the supported minimum. With Python 3.11, all 459
focused chart, identity, documentation and tracker tests passed.

The original immutable 1983 audit failed on the three changed team.yaml files;
its receipt remains in `.ai-audits/data-047-released-chart.json`. On November 10,
2026, the owner explicitly approved a narrow allowance for these exact corrections.
The gate now binds complete original/corrected bytes to the immutable baseline,
retains every other check and records both hashes for each accepted correction.

Test-first evidence: the new synthetic acceptance regression failed on exactly
these three files before the gate change; all 35 existing/rejection controls passed.
No existing test expectation was changed. The synthetic fixture copies only public
2026 chart bytes and constructs its own labels and Git baseline.
A fresh real-season receipt is retained in `.ai-audits/data-047-reviewed-chart.json`.
Full mandatory pre-push regression remains required. No push or release was performed;
browser play-test confirmation remains pending.

The updated real 1983 and unchanged 2024 released-chart audits both pass. The
reviewed allowance tests additionally check exact receipt hash values.
Automatic post-publication native verification now checks downloaded v1.10.5
assets for the corrected labels on every supported native target.

Broader validation found an existing frozen-launcher test trying to patch
`launcher.uvicorn` before that module was lazily imported. The test now patches
the imported uvicorn module directly; its API, model and fresh-game assertions
are unchanged. The initial backend environment also lacked the declared uvicorn
dependency. With uvicorn 0.27.0 installed in an isolated temporary environment,
all 450 backend tests pass (19 existing Pydantic deprecation warnings).
All 362 frontend tests and the production build pass; both retain the existing
outdated Browserslist data warning. Lint passes. Published native execution remains
pending a release; these checks do not claim Gatekeeper/signing acceptance.

The local Playwright run failed before any test actions: macOS denied Chromium
Mach-port registration (`MachPortRendezvousServer: Permission denied`). An
approved run outside the workspace sandbox encountered the same failure. All
18 browser cases therefore remain unverified; this is not a gameplay pass or a
reason to skip them. The owner was given the isolated-port terminal command to
run the complete browser regression. DATA-047 remains awaiting play-test evidence.

Independent review confirmed that the exact backend/tests/ subtree is pytest-only,
not packaged or imported by gameplay. The released gate now classifies that
subtree as tests, retaining every production module check, the separate readiness
inventory and mandatory backend regression. This explicitly reviewed correction
is covered by a failing-before/passing-after synthetic test and controls for
similarly named production paths; it is not a gameplay behavior allowance.

Final focused validation: 555 gate, artifact-harness, workflow, documentation,
tracker, release-target authoring and identity tests pass. Both real released-chart
gates and the standalone 90-team identity audit pass. Required core/backend/tests
lint and changed authoring/harness script lint pass. The index script retains
its pre-existing shebang/executable-mode and _day exception-type lint findings.

The broad coverage run was interrupted after subsequent implementation changes
made it unsuitable as a frozen final regression; it is not recorded as a full
suite pass. Full core coverage, clean tracked-only validation, historical games,
AI audits, fresh 1977 acceptance and the required complete browser regression
must still finish on the final release candidate before any push/tag.
No commit, push or publication was performed.

Owner terminal browser confirmation, November 10, 2026: the supplied isolated-port
command completed all 18 Playwright tests in 4.0 minutes. Both real-engine games
completed: game_9978541f finished 10–20 (154 executions, 8 kickoffs, one halftime,
6 defensive timeouts); game_3a8acda8 finished 38–37 (151 executions, 14 kickoffs,
one halftime, 6 defensive timeouts). Chart layouts, independent chart windows,
player help, all four two-point cases, season prohibition and offline guide checks
also passed. The existing outdated Browserslist data warning remained. This is
owner-supplied development browser evidence, not published native-install evidence.
It resolves the browser-launch verification gap for this working candidate; the
remaining full release regression and published-artifact checks are still required.

Release target is v1.10.5. Fresh versioned backend and frontend suites pass:
450 backend tests (18 existing Pydantic deprecation warnings), 362 frontend
tests, and the production build. The fresh full-season runner completes all
224 regular games and nine playoff games. Fresh public, generated-1983 and
private AI runs exactly match the independently reviewed game records and
summaries. The core coverage and clean tracked-only suites remain running.

The initial fresh 1977 acceptance attempt failed: Python 3.11 differs from the
saved Python 3.12 runtime identity, and the raw engine fingerprint includes the
two release-version strings. Python 3.12 reproduces the loaded runtime identity
exactly. Independent source review confirms every other fingerprinted file is
byte-identical to v1.10.4. Replacing only the two 1.10.5 literals with 1.10.4
reproduces the original complete file bytes. No statistical policy or evidence
has been changed. A proposed exact version-only compatibility allowance remains
subject to explicit owner authorization and test-first implementation; the failed
receipts remain retained and the release stays blocked meanwhile.

Final approved-candidate validation: all required command groups pass, with no
candidate-file changes during regression. The core suite passes all 11,195 tests
with 86% branch-inclusive coverage under Python 3.11; an independent Python 3.14
SysMonitor run also passes all 11,195 with 86% coverage. Neither run reports skips
or warnings. The clean tracked-files-only checkout passes all 11,195 tests too.
Backend: 450 passed with 18 existing Pydantic deprecation warnings. Frontend:
362 passed; build passes with the existing outdated Browserslist warning. Required
lint passes. All 14 standalone games, 224 regular games and nine playoff games
pass, with no tied playoff final. The historical runner also passes its sixteen
available private reproduction controls. AI report bytes exactly match the
independently reviewed reports; the AI-008/AI-029 comments retain their scoped
findings and no unsupported ticket closure is inferred.

The owner explicitly approved the exact 1.10.4-to-1.10.5 version-only allowance.
A fresh Python 3.12 1977 receipt passes, verifies all 55 source files (53 unchanged
and two exact hash-bound version edits), and retains the immutable policy/report.
The same four statistical misses remain disclosed and strict_fit_passed is false.
The gate's derived validation view and accepted full-file hashes are explicit in
the receipt. No fit tolerance, chart byte or gameplay implementation changed.

Receipts and detailed logs remain ignored under the approved-candidate audit
storage. The owner-supplied complete 18-case browser pass remains applicable:
subsequent changes affect version metadata, validation tools and documentation,
with no frontend or gameplay behavior change. Publication and downloaded native
acceptance remain subsequent requirements; this note does not claim them passed.

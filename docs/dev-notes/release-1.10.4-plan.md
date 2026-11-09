# Release 1.10.4 plan

Status: 1977 fit qualification blocked; integration/native verification continues.
Not ready for announcement.

The owner authorized autonomous completion, required regression, a new immutable
release tag, publication, and testing the downloaded published applications on
every supported platform and package form. No release has been tagged or pushed.
Use low reasoning for implementation and medium reasoning for actual Codex reviews.

## Intended scope

- Add the 1977 season only after reviewed source handling, independent
  reproduction, unchanged chart-fit gates and the correct historical calendar
  and eight-team/seven-game postseason pass. See the complete evidence and
  preserved candidate history in [1977 feasibility](1977-season-feasibility.md).
- Complete [VAL-023](issues/VAL/VAL-023.md) native Windows shutdown acceptance.
  The reviewed harness changes are committed locally; native proof remains
  outstanding. Do not publish merely to diagnose a harness problem.
- Preserve the published 1.10.3 missing-teams repair. AI-026 and unrelated AI
  experiments remain excluded. Newer live-season refresh ideas remain unscoped.

## 1977 current evidence

All 196 cached regular-season pages are identity checked. Reviewed, hash-bound
source handling preserves strict observations and separately records the 50/608
fumble fitting exclusions, one unsupported aborted snap gain, four contradictory
fumble boxes, one field-goal actor discrepancy, five PBP-versus-credited sack
counts and two known partial games. Historical source completeness is false;
no missing play, yardage or recovery is invented. No additional browser source
collection is needed for this candidate.

Candidate-05 uses the same global profile as candidate-04 plus one application
of the existing fixed complete-cohort gain-normalization recipe. All 28 teams
participate; there are no hand-edited team factors or coefficient sweeps. Event
probabilities, quarterback-time results, screen INT 5 support, defense and special
teams remain protected. Actual medium reviews are clean after receipt binding
was corrected. Independent generation reproduces all 84 chart CSVs exactly;
source/decoder/input/scope/reproduction checks pass with coverage limits explicit.

The separate 16-season diagnostic completes 3,136 games and passes all five league
and 140 team rate bounds. The full current-candidate Hard historical runner
completes 196 regular games and seven simulated playoff games. Neither is a
frequency guarantee or proof of official NFL tiebreak qualification.

The required 72-season run completes all 14,112 games and 1,008 team-games per
team. All league and 138/140 team metrics pass. Buccaneers and Redskins
interception rates miss their unchanged 0.010 bounds by 0.000267 and 0.000394,
respectively. Both boundary excesses are below 0.3 replication standard errors.
The fixed 144-total-season extension completes 28,224 games, retaining the first
72 replication summaries exactly. All five league and 139/140 team metrics pass;
Washington remains outside its interception bound: 0.0529739 versus 0.0417755,
absolute error 0.0111985 against 0.010. Numerical iteration stops. No 1977 charts
will be bundled or tagged as qualified. A concrete complete-cohort interception
allocation defect must be established test-first, or the owner must choose a
different release scope/explicit experimental-season policy; no silent waiver
or selected-team adjustment is authorized.

Scoring remains around 20.11 versus historical 17.18 per team-game. This is a
retained joint-behavior limitation, not a claim of historical scoring accuracy.
The prepared 1977 template supplies no historical named-player rosters. Do not
advertise complete historical commentary or force real playoff qualifiers.
1977 remains staged in ignored audit storage and has not been bundled.

## Integration and pre-push gates

After a qualified candidate and reviewed scope are frozen, update season
packaging, public validation/schedule metadata, attribution, player guidance and
consistent version metadata. Keep raw HTML, strict ledgers, intermediate charts
and narrative game logs ignored. Publish only reviewed generator outputs.

Run every current AGENTS.md regression command before every push, including tag
pushes; pytest alone is insufficient. Include the clean tracked-files-only unit
checkout, real-engine browser games, all existing historical/full-season games,
AI play-selection audits, and 1983/2024 source chart-quality checks. Disclose skips
and warnings. No urgent 1.10.3 waiver applies. Commit messages use v1.10.4 prefix.
Never reuse or replace a tag. Verify the next unused tag before publication.

### Current integration blocker

[VAL-024](issues/VAL/VAL-024.md) records a separate pre-push failure. Both required
1983/2024 strict source chart audits stop for missing current preparation.
Preserved source bundles have matching chart CSV hashes, but preparation
against the committed public manifests fails their original-manifest binding.
The public manifests intentionally omit the private source inventory. Existing
published accuracy exceptions are also disclosures, not strict fit passes.

No current checklist command is silently replaced or waived. Independent checks
continue, but a failed required command prevents the integration push and thus
updated upstream native Windows proof. Resolve the public/private validation
contract and owner policy for unchanged legacy accuracy exceptions before pushing;
this is not a missing token permission. The staged 1977 fit issue is separately
tracked as [DATA-046](issues/DATA/DATA-046.md).

## Native acceptance and publication

After the integrated main push, run the updated post-release smoke workflow on
unchanged v1.10.3 assets to establish VAL-023 Windows evidence. Require normal
zero exit, shutdown marker, port release and no surviving owned processes. Forced
cleanup fails. The explicit 1977 acceptance profile stays disabled for 1.10.3.

After exact-commit CI and the immutable next release build complete, download
actual published assets and test Windows portable and NSIS-installed applications,
Linux AppImage, Intel macOS and ARM macOS DMGs. Confirm artifact hashes, normal
entry point outside the checkout, all bundled season/team lists in API and UI,
new-game state and charts, request logs and normal shutdown. Enable the explicit
1977 profile only if qualified charts are actually bundled. Record fresh-download
macOS quarantine/signing/notarization limitations; CI success or asset presence
alone does not establish healthy installs. See [release testing](../release-testing.md).

## Completion report

Report release URL, immutable tag and commit, qualification and published-install
evidence, material source/fit/platform limits and a clear ready/not-ready status.
Do not post to Facebook or message outsiders. If a consequential owner decision
or access gap blocks completion, state the precise blocker and preserve all failed
evidence rather than claim the release is ready.

## Final bounded integration checkpoint

1977 remains unbundled and no tag, version bump or push occurred. Source/fit and
public/private pre-push policy blockers remain DATA-046 and VAL-024. Native
Windows proof remains pending because its reviewed workflow updates cannot be
pushed under the current failing checklist; access permissions are not the cause.

Independent checks pass: backend 450 tests (21 existing Pydantic deprecation
warnings), frontend 350 tests using the CI-pinned Node 24.22.1, frontend build,
Ruff, the fourteen-game runner, all 224 regular and nine playoff 1983 games plus
sixteen historical reproductions, and all 32 public/448 local AI audit games.
Public structural/decoder checks also pass for both currently bundled historical
seasons; they do not replace strict source qualification. Browserslist reports
its existing stale-data warning. An initial frontend run under local Node 26
fails because its experimental global localStorage interferes with the test
environment; the supported CI-pinned runtime passes without product changes.

The clean tracked-files-only unit run has 11,040 passes and one synthetic fixture
failure. Actual medium review confirms the old fixture relied on an unrelated
first player link despite a different named primary runner. The corrected fixture
retains both cross-team rejection assertions using a passer/receiver ownership
conflict, adds a paired matching-team control, and explicitly empties position
metadata. It covers the receiver/team branch, not independent leading-actor
rejection. No production behavior or source facts changed. All 175 focused
source/adapter tests pass; all 586 corrected source/documentation/tracker checks
pass in the tracked-only checkout. The old collected coverage run was stopped
after this finding at 2,665 passes/24%; a successful full coverage run is not
claimed. No further expensive regression is justified until the real push blockers
are resolved; the full checklist must still pass before any future push.

The required browser command fails because the installed Paydirt application
already owns port 8000. It was left running to avoid losing a possible unsaved
player game; no existing server was reused as a test backend. This is an explicit
uncompleted browser check, not a skip or passing result. All detailed logs,
receipts and compressed, hash-verified failed chart-fit evidence remain ignored.

### 2026-11-09 released-chart policy implementation checkpoint

Owner authorized VAL-024 tooling and AGENTS policy separation: exact published
1983/2024 inputs are regression-checked against immutable v1.10.3 commit
`1467b11e151fe9981177890e2a7a6b805402b3f0`; new or regenerated charts still
require strict source/reproduction and applicable minimum-sample fit. No 1977
exception is authorized by this policy. Candidate-05 remains preserved; the
separate owner-authorized one-shot interception diagnostic does not qualify it.

Both released-season identity/mechanics checks pass. The 1983 historical runner
passes 224 regular games, nine simulated playoff games and all 16 available
private reproductions. Backend tests pass (450; 20 existing Pydantic deprecation
warnings). Seventeen synthetic new-gate controls pass; integration controls and
medium actual review are continuing. Review caught Git replacement and output
path trust holes; failing controls reproduced them before fixes. The explicit released command inventory matches AGENTS. The existing frozen
candidate collector retains its strict default commands/source/output validator,
including its partial-64 negative control. Strict candidate sample/tolerance
assertions remain unchanged.

The new chart gate binds authoritative core/backend gameplay, not frontend byte
identity. It explicitly reports that limitation and never certifies a release.
Frontend changes require actual review and all real-engine browser regression.
The initial coverage attempt was stopped after concurrent source edits produced
four stale engine-fingerprint controls; it is not a complete regression result.
Freeze code after review before rerunning coverage and tracked-only tests. No
push, tag, publication or installed-app shutdown has occurred in this pass.

Root accepted the explicit core/backend identity boundary on 2026-11-09,
conditioned on actual review of this frontend diff as display/transport/test-port
changes and a complete frozen E2E pass. This does not exempt future UI gameplay
changes. The current frozen browser run remains pending; no release-ready claim
follows from the chart gate alone.

### Current owner authorization: finite search and disclosed accuracy exception

The [durable 1977 calibration/release goal](1977-calibration-release-goal.md)
supersedes earlier no-fit-exception checkpoints above. The owner authorized at
most five new adaptive global interception trials, counting candidate-07 as
trial one. The fixer owns paired diagnostic search/ranking. The release owner
regenerates the nominated profile canonically with normal retraining, independently
reproduces it and obtains an appropriate final minimum-sample report. Ignored
frozen-recipe wrappers remain diagnostics only.

If no ideal fit passes, the owner now permits shipping the best candidate with
an explicit, narrow, hash-bound statistical exception documenting actual metric
misses and authorization. Strict failed bounds remain failed; thresholds and
source facts are unchanged. Source/reproduction, era/calendar, mechanics,
screen-INT, gameplay, complete regression and downloaded native-install checks
are not waived. DATA-046 remains open for residual accuracy concerns. No 1977
season is bundled or release-certified by this authorization alone.

### First integration regression complete (2026-11-09)

All revised pre-push checks pass on the reviewed source state: core 11,060 tests,
86% coverage (38m28s); clean tracked-only 11,060 tests (11m30s), followed by 454
updated documentation/gate checks; backend 450 tests; frontend 361 tests/build;
frozen 18-browser-test run including both real-engine games; Ruff; all 14 private
integration games; 1983 actual calendar 224 regular/nine playoff games and 16
private reproductions; public/local AI audits (32/448 games), with the same three
legacy balanced long-third advisories reviewed. Both immutable released-season
chart regressions pass. Backend emits 20 existing Pydantic deprecation warnings;
frontend build retains the stale Browserslist-data advisory. Core reports no
skips or warnings. VAL-024 is closed for this specific verified local policy fix;
VAL-020 remains open. This checkpoint does not claim upstream/native success or
1977 release acceptance. The selected 1977 charts are still staged locally only.

# v1.10.2 scope and verification

Status: November 7, 2026 authorized implementation. Local checks below are
completed; hosted CI and automatic publication remain release gates. The owner
explicitly waived another full local historical regression in this release cycle;
focused test-first checks and the complete hosted workflow qualify this change.

| Issue | Result / release gate | Verification |
| --- | --- | --- |
| [DATA-043](issues/DATA/DATA-043.md) | Prevent cross-play interception-location allocation across offense/defense and audit all reachable support. | Synthetic/public regressions first; all-team weighted spot support and reachable outcomes, with interception and return distances separate. No arbitrary universal depth cap or claim that the Bowl Bound defect is already reproduced here. |
| [AI-028](issues/AI/AI-028.md) | Avoid a conservative fourth-down punt when the offense needs multiple scores and remaining possession opportunities demand urgency. | Failing public scenario plus nearby conservative controls; completed gameplay confirms score/time/timeout-aware behavior. No blanket always-go-for-it rule. |
| [VAL-020](issues/VAL/VAL-020.md) | Reduce core test runtime by removing redundant expensive fixture construction. | Record durations, identify actual hot spots, preserve assertions/cases/coverage, and compare equivalent hosted runs. Set a measurable target after profiling rather than promise an unsupported duration. |
| [VAL-021](issues/VAL/VAL-021.md) | Publish release assets automatically without the v1.10.1 manual-token fallback. | Diagnose the actual integration restriction, preserve exact tested-commit gating and immutable tags, and verify all five downloadable assets in the next authorized publication. |

The two player-facing items and the two delivery items form the authorized
bounded release. Interception findings may require reviewed regenerated charts;
do not regenerate unrelated cohorts or change historical fit targets by default.

## Diagnostic follow-up, not a promised broad fix

[DATA-042](issues/DATA/DATA-042.md) and [AI-030](issues/AI/AI-030.md) should get a
controlled measurement plan for pace/scoring and chart-focused versus Hard
policy. Do not tune individual teams to historical standings or fold a general
AI rewrite into this release without reviewing new evidence and scope.

The accepted v1.10.1 Ravens/49ers/Falcons fit exceptions and historical modeling
assumptions remain disclosed under DATA-018/DATA-030. They are not silently
resolved or mandatory recalibration work for this proposal.

Before implementation, reconcile stale issue states against shipped code and
existing play-test evidence. All behavior fixes require synthetic/public test-first
regressions, relevant focused checks and issue-specific gameplay verification.
Use the current repository validation instructions and any explicit user overrides;
this proposal creates no additional private-hosting release prerequisite.


## Local implementation evidence

AI-028 adds a bounded remaining-possession estimate for Q4 multi-score fourth
downs with two to five minutes left. Three new baseline failures (observed punt,
zero-timeout urgency and a useful field goal) and seven passing controls preceded
the change. All 91 computer-AI tests pass. Twenty independently seeded real-engine
CLI scenario continuations from down nine, 3:37, fourth-and-five at the own 16
all attempt a scrimmage play and terminate with reconciled scoring/period totals:
six convert, fourteen fail on downs. A favorable final score is not required.
The web API also executes both real-engine conversion and turnover consequences
for home/away CPU possession. New integration fixtures suppress the separately
covered five-yard OOB designation cost when isolating conversion accounting;
no existing expectation changed.

Public play-selection audits complete 32/32 Hard/balanced games (4,878 calls)
and 8/8 Medium games (1,152 calls, final seed 8306 replay), without concentration warnings. The largest
listed ordinary Hard share is 33.8% of 71 third-and-short calls (eight distinct
plays, longest comparable streak two). Balanced retains a 43.3% share in 30
third-and-long calls (three plays, streak three). These are observations, not
frequency limits or evidence that unrelated coaching questions are solved.

DATA-043 was reopened from its initial audit-only closure and now has a preventive fix. The owner's clarified
requirement is preventive behavior. A synthetic known 44-yard interception was
assigned to Screen in 56/1,000 seeds by PFR's completion/YAC-weighted heuristic;
absence of that cell in shipped charts was insufficient evidence of correctness.
Thirty-two behavioral regressions failed on the unchanged producer, with five
controls passing. All 37 now pass, alongside 218 existing generator/source tests.
No existing expectation changed. The first new sparse-calibration fixture called
a proposed keyword too early; it was replaced before production changes with a
public generator API regression that demonstrates lost event mass directly.

Known inferred interception catch depths now use the existing nflverse taxonomy:
at/before the line Screen, 1–9 Short, 10–19 Medium, 20+ Long. Explicit source
Screen calls retain their depth. Completion net gains retain the separate
YAC-aware classifier. Missing locations and aggregate models use per-call spots
Screen5/Short5/Medium12/Long20/TE8 instead of pooled labels or a universal INT10.
Defense retains its call-specific 5/5/12/18/8 model. Positive calibrated event mass
gets that call's fallback even when finite baseline and source omit an INT label.
Generation fails closed if offense introduces an INT location outside that exact
normalized source call's support and its modeled fallback; defense must use its
call-specific model. Normalized empirical input explicitly declares source call
attribution; adapters constrain inference before that boundary. This preserves
supported unusual observations without imposing an arbitrary universal cap.

The reusable exact weighted census retains each team, call and formation, combines
uniform cohort defenses through the priority table, and separates return distance.
Its initial all-60-team baseline found Screen support 5/12 in 1983 and 5 in 2024.
Reviewed regeneration now freezes existing gain multipliers instead of retraining
16 schedules per cohort or tuning teams. Private replay proof records old training
identity, current producer hashes and replay-script identity; all original source
games/rows/FG/fumble totals must remain unchanged. Full source requantization showed small unrelated event-mass drift, so it was
not adopted. A deterministic INT-only migration changes 151 cells in 28 historical
teams and 108 cells in 30 modern teams. Every physical row, event mass, non-INT
cell and defense/special/team file stays unchanged. Compact manifests explicitly
bind the original source proof plus the post-generation migration receipt; they
do not claim these bounded outputs equal a whole corrected-source requantization.

All 60 final teams pass structure, exact mechanics and decoder checks. All five
calls and six formations pass source/model support and weighted reachable census:

| Cohort | Screen | Short | Medium | Long | T/E S/L |
| --- | --- | --- | --- | --- | --- |
| 1983 | 5 | 5 | 12 | 18, 20 | 8 |
| 2024 | 5 | 5 | 12 | 18, 20, 24 | 8, 24, 25 |

Thirty complete real-engine games cover every team and validate scoring,
termination and selected-call accounting. This is bounded gameplay proof, not
new full source-fit qualification or a repeated-season forecast. The former
512-season findings belong to the v1.10.1 charts. A type-checker comparison finds
the same 22 existing diagnostics in these three producer modules before/after;
none is introduced by this change. Ruff passes.

VAL-020 moves completed synthetic visual-chart templates to a lazy session fixture;
every mutation case still copies its own files and owns fresh dictionaries.
Equivalent 118-case Python 3.12 runs: 158.06 seconds before, 27.54 after (82.6%
less elapsed time). Including all 27 preview-collector cases, 145 pass in 35.52s.
Cases/assertions remain intact; generator behavior tests still generate charts.
Hosted coverage now records its 30 slowest durations. Hosted full-suite cost must
be measured independently; this local result does not promise a 55-minute to
five-minute hosted change.

VAL-021 root cause: the v1.10.1 target 12c15dd contains a different release workflow
than the default branch after 2ab038f. GitHub's create-release endpoint requires
workflow-write authorization for such an explicit target, even when the version
tag exists; GITHUB_TOKEN cannot acquire that permission. See
[GitHub release API permissions](https://docs.github.com/en/rest/releases/releases#create-a-release).
The release job now rechecks that the existing tag still resolves to the exact
tested/build SHA, then omits redundant target_commitish metadata. Existing tags
select the source; API default-branch metadata does not move them. No token scope
or credential change. Five new workflow tests failed before this fix; all sixteen
now pass. Automatic publication and all five asset hashes remain required before
closure. A repository-settings API read was denied to the local token; no settings
or permissions were changed.

Local reports stay in ignored `.ai-audits/release-readiness/v1.10.2/`. Shipped
v1.10.1 source-fit exceptions and the separately tracked AI-029 last-possession
policy remain unchanged.


Corrective validation also passes 850 broader source/ledger/visual/documentation
checks and 142 release/packaging/AI checks. A fresh tracked-files-only snapshot
passes 624 focused tests and ruff, without ignored local source data. Both compact
public audit summaries bind refreshed full-report hashes and all 180 CSV hashes.
STAT-006 records the separately requested cumulative player-facing season stats
backlog; its implementation is outside this release.

Follow-up validation identifies the allocation gate’s synthetic 15-yard pass
profile explicitly as Medium, satisfying the new required call-specific model
argument. Its new regression fails against the old caller; all 49 allocation and
interception-policy tests pass after correction. The new fixture checks every
profile encountered by the real audit. No existing expectation changes, chart
regeneration or gameplay change is required for this caller correction.

VAL-020 also removes repeated source parsing/compilation from runtime identity
checks through a bounded content cache, while rereading bytes and inspecting all
live state every time. Nine new synthetic controls cover unchanged-source reuse,
same-size/same-mtime edits, live mutation and newly added dependencies; one reuse
regression fails on baseline and eight controls pass. The same 91 existing
engine-audit cases with coverage take 99.41s before and 11.90s after in cold local
Python 3.12 processes (88.0% less). No existing assertion/case changes or identity
result caching. Hosted overall runtime is reported separately when complete.

The runtime-cache correction also passes 387 related calibration/source/freeze/
reference-gate checks. Three initial local CLI JSON writes failed with ENOSPC;
retaining failure logs and cleaning disposable passed-test fixtures resolves
those environment failures without changing assertions. A clean tracked-only
snapshot passes 544 focused integrity/engine/allocation/policy/documentation/
tracker checks and ruff. Two runtime-identity type diagnostics match baseline.

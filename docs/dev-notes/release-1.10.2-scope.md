# v1.10.2 scope and verification

Status: November 7, 2026 authorized implementation. Local checks below are
completed; hosted CI and automatic publication remain release gates. The owner
explicitly waived another full local historical regression in this release cycle;
focused test-first checks and the complete hosted workflow qualify this change.

| Issue | Result / release gate | Verification |
| --- | --- | --- |
| [DATA-043](issues/DATA/DATA-043.md) | Audit interception locations by play type across offense/defense and correct any demonstrated allocation defect. | Synthetic/public regressions first; all-team weighted spot support and reachable outcomes, with interception and return distances separate. No arbitrary universal depth cap or claim that the Bowl Bound defect is already reproduced here. |
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
and 8/8 Medium games (1,195 calls), without concentration warnings. The largest
listed ordinary Hard share is 33.8% of 71 third-and-short calls (eight distinct
plays, longest comparable streak two). Balanced retains a 43.3% share in 30
third-and-long calls (three plays, streak three). These are observations, not
frequency limits or evidence that unrelated coaching questions are solved.

DATA-043 adds an exact weighted spot census inside the public chart audit. It
retains each team, pass call and formation, combines uniformly sampled cohort
defenses through the actual priority table, and separates catch depth from
return yards. All 28 1983 and 32 2024 committed charts pass. Reachable spot sets:

| Cohort | Screen | Short | Medium | Long | T/E S/L |
| --- | --- | --- | --- | --- | --- |
| 1983 | 5, 12 | 5, 12 | 5, 12 | 5, 12, 18 | 5, 8, 12 |
| 2024 | 5 | 5 | 5, 12 | 5, 18, 24 | 5, 8, 24, 25 |

No reachable Screen INT44 is present. Source adapters classify the pass family
before grouping outcomes; they do not pool interception locations across plays.
nflverse reads air yards and PFR estimates catch-minus-line depth, with a modeled
10-yard default when absent. Their return observations enter a separate special
column. The aggregate generator uses modeled INT5/12/20 for all passing columns;
empirical event calibration prefers those baseline labels when available. Defense
uses modeled call-specific 5/5/12/18/8 depths. This is an explicit source-fidelity
limitation, not proof of physically impossible support or a justified new cap.
No generator allocation, event mass, rates, protected mechanics or chart bytes
changed. Historical depth fidelity is not certified. New audit tests initially
used incorrect physical row weights; they were corrected to the actual 2/216
primary-row and 12/36 defensive-row mass before interpreting results. No existing
test assertion was weakened.

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

# 1977 season source feasibility

Recorded 2026-11-08 for the proposed v1.10.3 season addition. This is a
source-access checkpoint, not an implemented season or a release qualification.

The [Sports Reference announcement](https://www.sports-reference.com/blog/2026/08/1977-play-by-play-and-associated-stats-added-to-pro-football-reference/)
confirms that PFR added 1977 play-by-play on August 12, 2026. Its indexed primary
article explicitly identifies partial-game gaps: the final 1:30 of Washington at
Atlanta in Week 2, and the final 3:55 of the second quarter plus part of the fourth
quarter of St. Louis at Washington in Week 13. It also reports 185 fumbles with
unknown forced-fumble credit. That latter count concerns forced-fumble attribution;
it does not establish the number of unsupported generator gain/class/ownership
facts. Play-by-play is unofficial and can differ from corrected box-score totals.
The announcement therefore cannot establish complete source coverage.

## Bounded acquisition result

No 1977 raw-source cache or season template was found in the repository, its
ignored audit storage, the work tree or temporary storage. Direct public HTTP
requests for the 1977 schedule, a representative box score and Dallas team page
returned HTTP 403. Web retrieval of the schedule also returned 403. The existing
1983 set cites archived PFR HTML, but bounded Wayback CDX queries for the 1977
schedule in 2026 and the representative box score returned empty inventories;
a dated representative replay returned 404. These sampled checks do not prove
that no archive of any 1977 game exists. They do establish that the tested route
did not supply a usable input inventory.

The [official nflreadr loader](https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R)
requires seasons beginning in 1999. Its standard nflverse play-by-play feed cannot
supply 1977. No alternate complete, adapter-compatible public input was verified
in this bounded check. Search snippets are evidence about coverage, not raw
per-play inputs suitable for source hashing and generation.

## Decision and next dependency

Stop before generation. Reuse of `generate_pfr_charts.py` is plausible, but it
requires actual archived HTML, normalized team aggregates, a source-team map,
and a reviewed season template. Compatibility and coverage cannot be qualified
without those bytes. No charts, roster, era-rule assumptions, source contract,
calibration profile or historical-fit claim were created. No expensive tuning,
season campaign or generator changes were started.

The concrete next dependency is an accessible 1977 PFR HTML/source bundle with
provenance, or another reviewed compatible public feed. Then census all games
and required fields, retain the two announced gaps, and decide explicitly how
missing events enter the modeled scope before generating a candidate. The
existing fumble modeling/exclusion policies do not automatically resolve missing
stretches of ordinary play-by-play. An affordable addition still requires the
existing source/chart gates and complete historical season validation; do not
publish aggregate fallback as a reconstruction of unavailable play-by-play.

Local acquisition receipts remain in ignored
`.ai-audits/release-readiness/v1.10.3/1977-feasibility/`. No downloaded raw source
or historical narrative is committed. This note adds no player-facing behavior,
so player/API guides and packaging do not change.

## Follow-up: exact 1983 acquisition path and 1972 comparison

On November 8 the owner requested checking the PFR route for both years. The
bounded follow-up inspected the actual cached 1983 fetch script and retried its
Wayback `if_` replay method, rather than treating direct HTTP 403 as proof that
archival acquisition is impossible.

- A fresh replay of the known 1983 source `198309030sfo` returned HTTP 200;
  the existing PFR parser read 163 play rows. The replay method remains usable.
- A replay of the 1977 Denver–Kansas City box score `197711200kan` returned
  HTTP 200, but Wayback selected a January 15, 2026 snapshot. It has no `pbp`
  table and predates PFR's August 12, 2026 addition of 1977 play-by-play.
  Its latest exact-URL CDX capture is that same January snapshot.
- The 1977 schedule replay returned an October 6, 2025 capture. A schedule can
  identify games but cannot supply play outcomes. A post-August exact schedule
  inventory was empty; the broader post-August box-score prefix query timed out.
  This is not a complete archive census and does not exclude newer captures of
  other games. Sample exact-query results must not be generalized to the league.
- PFR's [coverage documentation](https://www.pro-football-reference.com/about/coverage.htm)
  states full play-by-play begins in 1977. Thus 1972 is not a like-for-like input
  for the existing PFR full-PBP generator. A sampled 1972 Miami–Kansas City
  box score `197209170kan` was accessible through an October 29, 2026 replay,
  but contained no `pbp` table. The current parser also rejected its team markup;
  changing markup parsing alone cannot recover the missing plays.
- Direct current-site schedule and representative box-score requests still
  returned HTTP 403. Search-indexed primary coverage and announcement text is
  useful evidence about availability, not a substitute for source HTML bytes.

1977 remains the stronger candidate for the existing pipeline, conditional on
access to recent PFR pages containing the PBP tables and a complete source census.
Its two documented partial-game gaps still need explicit treatment. 1972 could
use PFR aggregate statistics only via a separately reviewed modeled fallback or
additional historical sources; it is not equivalent to the 1983 PBP method and
no such chart-generation work was started here.

No heavy source reconstruction, all-team generation, production changes or season
simulation was run. Raw sample HTML and hashes/access receipts stay ignored in
`.ai-audits/pfr-feasibility-followup/`. The publicly maintained note contains only
source/access findings and links, not source narratives.

## Resumed v1.10.4 PFR pilot: compatibility passes, coverage remains open

The owner explicitly resumed the PFR approach for v1.10.4. A bounded fresh check
on November 8 recovered the historical schedule through the existing Wayback
`TIMESTAMPif_/originalURL` method. It identifies 196 regular-season game URLs.
Four actual archived 1977 PBP pages were downloaded, hashed and parsed with the
unchanged production PFR adapter:

| Game ID | Parsed source rows | Classified representations |
| --- | ---: | ---: |
| `197709180rai` | 171 | 177 |
| `197709250dal` | 202 | 210 |
| `197710230nwe` | 152 | 163 |
| `197712040min` | 177 | 183 |

These samples establish basic adapter compatibility, overturning any inference
that usable 1977 PFR HTML cannot be acquired. They do not establish source
completeness or fit. Diagnostics retain heuristic pass-depth/run-family choices,
unclassified rows, an unclassified sack, unknown recovery and an unreconciled
fumble box. Legacy classification's empty `unsupported_fields` lists do not
waive source audits or establish factual completeness. Representation counts may
exceed source rows because one event can support multiple chart representations.

A canonical `www.pro-football-reference.com/boxscores/1977` CDX prefix query for
captures from August 12 through November 8, 2026 returned 24 distinct URLs under a
250-row limit. Twenty-two match the 196 regular-season schedule IDs; 174 regular
games have no recent capture in that returned inventory. The other two represent
a January game from the prior season and a December postseason game. This query
is a reproducible coverage result for that route, not proof that no other archive
or legitimate source route contains the remaining games.

Replay URLs and raw bytes also require separate validation: the indexed September
capture of `197710230nwe` redirected an HTTPS-original replay to a January page
without PBP. The standard HTTP-original replay at that timestamp returned actual
PBP and parsed successfully. An archive index date alone therefore cannot pass
source qualification. Three contrasting HTTPS-original replays also returned PBP.

The initial pilot is complete; full generation remains blocked on obtaining and
reviewing the remaining regular-season source pages. No all-team generation,
aggregate fallback, calibration campaign, production changes or season simulation
has started. All raw HTML, schedule data, exact access URLs, hashes, parser
receipts and missing-ID inventory remain ignored under
`.ai-audits/chart-generation/1977-pfr-source/`. The two announced partial-game
gaps still require explicit treatment even if all 196 game pages are acquired.

## Owner-browser acquisition pilot

On November 8 the owner supplied a Chrome-saved view-source page for
`197709250dal`; its recovered source parsed 202 plays. A normal automated
Chromium session still received HTTP 403 with `cf-mitigated: challenge`.
However, ordinary tabs controlled through Apple Events in the owner's existing
Chrome browser successfully loaded two more regular-season games:
`197709180atl` (170 plays) and `197709180buf` (166 plays). No cookies were
exported and no challenge-solving, stealth settings or profile changes were used.

Rendered PFR DOM retains original commented tables after inserting live copies.
The local acquisition helper preserves raw DOM and removes only commented
table blocks whose table IDs already exist in the live DOM before passing HTML
to the unchanged core adapter. Four synthetic normalization controls passed;
the initial doubled counts of 340 and 332 were corrected to 170 and 166.
Raw and normalized hashes, source URLs and timestamps are retained locally.

A resumable background collection was started for the 196 regular-season game
IDs, excluding the four playoff URLs in the archived schedule inventory. It
uses a dedicated Chrome window, one page at a time, with at least 30 seconds
between games, and stops on a detected browser challenge or parser failure.
This establishes a working acquisition pilot, not complete season coverage,
chart qualification or resolution of PFR's two announced partial-game gaps.
The ignored helper, progress receipts and source pages are under
`.ai-audits/1977-browser-helper/`; no application code or charts were changed.

## Complete browser cache and first source-quality gate

The completed owner-browser collection now contains all 196 normalized regular-
season pages plus original rendered DOM. A fresh census verified both hashes for
all 196 receipts, parsed 33,658 rows and confirmed 28 teams with 14 games each.
The archived schedule independently agrees with all source team identities and
final PBP scores. Each game box reconciles gross passing yards minus sack yards
to net passing yards, and net passing plus rushing yards to total yards. These
checks establish input inventory and arithmetic, not full event coverage.

Normalized aggregate JSON files, the team map, calendar and a local 1977 rules
template are prepared under ignored `1977-reviewed/`. Rushing/passing totals come
from team boxes; return and kicking totals come from individual box rows. Missing
punt-block fields are not invented. The template uses the supported historical
sudden-death overtime and one-point conversion settings; it does not claim that
the engine independently reconstructs every pre-1978 NFL contact/blocking rule.
The [NFL chronology](https://edge-operations.nfl.com/media/nppjkdp1/2023-record-and-fact-book.pdf)
records the 1974 sudden-death, kickoff and missed-field-goal changes and the later
1978 contact/blocking changes.

The explicit version-2 historical fumble census initially found 50 unsupported
fumble projections and two other required-gain gaps, alongside five inconsistent
fumble boxes, one unreconciled field-goal box and other retained diagnostics.
One non-fumble gap was an adapter defect: a quarterback's explicit kicked PAT
was treated as a potential rush. Three synthetic PAT regressions failed with the
expected missing-rush-gain error while two scrimmage controls passed. The narrow
fix excludes explicit kicked PATs before quarterback rushing inference; all 80
PFR adapter tests pass. Actual Codex review found no actionable issue; its own
test attempt encountered the default incompatible Python, while the dedicated
release environment ran the passing suite. No existing test expectation changed.
The other gain gap is an aborted snap with no stated gain; its yardage remains
unknown, rather than inferred from the next field spot.

A neutral-profile generation attempt using the existing explicit version-2
fumble policy and fitting-exclusion policy stops at that unrelated required field.
The exclusion policy correctly refuses to suppress it. No charts were generated,
no source checks were relaxed and no calibration or season campaign was started.
The five fumble-box discrepancies remain separate blockers even if the aborted
snap is resolved. Full source receipts, per-game diagnostics and failed-command
logs stay ignored under `.ai-audits/chart-generation/1977-reviewed/`.

The announcement's away/home wording conflicts with both schedule and page
identities: Week 2 is Atlanta at Washington (`197709250was`), and Week 13 is
Washington at St. Louis (`197712100crd`). Do not silently transfer the quoted
venues into source identities. In the Week 2 page the last timed row is 1:53,
followed by three untimed plays ending Atlanta's drive; no subsequent Washington
possession is represented. In the Week 13 page only sparse kick/punt/score rows
bridge 3:55 to 0:34 of Q2, and Q4 includes an abrupt transition from a Washington
punt to a St. Louis third-down penalty with missing field position. These are
consistent with the announced incomplete stretches, but do not recover their
missing plays or establish an exact Q4 time interval. Sparse historical timing
alone cannot establish coverage. Keep these gaps explicit in any later modeled
scope decision; matching final scores does not close them.

### Unlinked primary actor correction and remaining blockers

A second adapter defect explains one of the five fumble-box discrepancies:
an unlinked primary runner name was ignored in favor of a linked defender.
Synthetic source regressions produced two expected attribution failures while a
linked-runner control passed. Name-based primary identity now uses known leading
names before later linked actors. Actual Codex review caught a duplicate-name
regression in the initial implementation; a new failing collision regression
required excluding ambiguous display names from lookup, preserving linked actor
identity. No previous test assertion was weakened or changed.

With the corrected runner attribution, the fresh census has 608 offensive fumble
events, 50 unresolved fumble projections, one other required gain gap, four
inconsistent fumble boxes and no declared source conflicts. The four remaining
box discrepancies are `197709250was`, `197710230chi`, `197712040min` and
`197712110nor`; the unreconciled field-goal box is `197710090tam`. These are
source-quality findings requiring review, not permission to force reconciled
counts or ignore the underlying events. A separate non-exclusion generator run
writes the full 196-game source ledger, then correctly fails on the inconsistent
fumble-box gate. The exclusion-enabled run stops at the unrelated required gain.
No chart candidate or historical-fit verdict exists.

The focused adapter, reconciliation, starter, historical-policy, command and
documentation suites pass 227 tests. Changed-file Ruff passes. No push or release
was attempted; complete regression and 1977-specific source/chart/full-season
validation remain outstanding. The current historical runner also needs reviewed
eight-team/seven-game postseason support before it can validate a 1977 season;
its existing ten-team and fourteen-team formats cannot substitute for that format.

### Reviewed modeled candidate (2026-11-08)

The approved continuation preserves the original strict source ledger and uses
`reviewed_historical_source_scope_v1` as a separate, hash-bound fitting sidecar.
All 196 input games apply exactly once. The strict ledger SHA256 remains
`1a143f47938ad4d1f5b365dd7ee86dbbb51750dfdd936e9fe2a2ed2c87b34ff6`.
The existing uniform historical fumble exclusion removes 50 of 608 events
(8.22%) from fitting; 558 remain. All six unknown recoveries are among the
excluded events. This selection is a material limitation, not complete source
coverage. No missing recovery, gain or possession fact was inferred.

A separate exact exclusion covers the Chicago aborted snap in
`197712180nyg`, source play 186: initial rushing gain is unknown. The raw event
and unsupported-field record remain in the strict ledger. Four fumble-box
contradictions are accepted only as individually reviewed diagnostics, without
rewriting either account. The `197710090tam` field-goal discrepancy concerns
kicker identity: complete team attempt/make totals reconcile, so team, distance
and outcome are retained without asserting which kicker attribution is correct.
Both previously announced partial-game gaps remain explicitly inventoried.

The scope is opt-in, requires the existing historical fitting policies, binds
source game/play hashes, and must match the validation contract and portable
source input contents. New problems or changed diagnostic counts still fail.
Test-first regressions include wrong hashes, unsupported scope, unexpected
fields/counts, mismatched input contents and field-goal team-count disagreement.
Actual Codex review identified an audit input/disclosure binding gap; its new
regression failed before the fix. The medium-reasoning re-review found no
remaining actionable defect. All 423 focused tests and changed-file Ruff pass.

Candidate-01 now generates all 28 team chart sets from the 196 cached games with
the prepared neutral profile. Candidate files and detailed receipts remain under
ignored `.ai-audits/chart-generation/1977-reviewed/candidate-01/`. Generation
success does not establish historical fit. Independent source/decoder checks,
correct eight-team postseason support, full-calendar validation and release
regression are still outstanding; no season files have been published or tagged.

### Eight-team runner and first independent checks

Four new synthetic regressions first failed because `eight_team` was unsupported.
The runner now supports three division winners and one wildcard per conference,
no wildcard round and seven total postseason games. Additional controls cover
both wildcard division relationships, relative playoff weeks and failure/tie
non-advancement. All 46 historical-runner tests and Ruff pass; actual medium
Codex review found no actionable defect. Existing ten-/fourteen-team fixtures
and behavior remain covered. Official source-year tiebreaks remain unverified;
these diagnostics continue using the declared regression tiebreaks.

Primary format evidence is the 1977 St. Louis Cardinals media guide, printed
page 116/PDF page 119, archived from
<https://library.sfo2.cdn.digitaloceanspaces.com/publications/football/yearbooks/FARICMG-1977-arizona-cardinals-media-guide.pdf>.
Its locally downloaded PDF SHA256 is
`6715f926b51fe184a3da79cbb1cb10112f1ef445d490bdc5d0eb7a6f73226de2`.
The independently cached PFR schedule supplies 196 regular and seven historical
postseason fixtures; its explicit 1977 membership/calendar passes the source
schedule validator. The candidate Hard season run uses those regular fixtures
and qualifies its own postseason entrants, without forced historical results.

The independent source audit passes chart structure/decoder, normalized
source denominators, raw hashes and exact reviewed-scope checks, but fails five
sack-count reconciliations (958 classified versus 955 box sacks). Three affected
games explicitly describe a zero-gain sack; one has a sack without distance;
one is the already announced partial Washington/St. Louis game, whose PBP has
one fewer sack than its box. The affected teams are Dallas, Chicago, San
Francisco, Minnesota and St. Louis. No source count, yardage or diagnostic was
rewritten to make this pass. Reproduction and historical-fit qualification are
still outstanding.

The first Hard calendar completes all 203 games with reconciled finals and no
errors. Dallas wins the simulated championship, but only three of its eight
qualifiers match the historical field; one seed is not a frequency estimate.
This completion check does not override source or fit failures.

A bounded four-repetition chart-focused diagnostic completes 784 games. It is
below the required 64 independent schedules and explicitly fails the sample
threshold. Its neutral-profile rates also show substantial drift: league pass
yards per attempt 4.21875 versus source 6.49847, completion rate 0.47711 versus
0.51318, and rushing yards per attempt 3.35084 versus 3.84983. Existing tolerances
are unchanged. This is evidence to plan a bounded calibration step, not a
qualified season or justification for repeatedly searching profiles. Detailed
reports remain ignored beside the candidate; no release regression, push, tag
or publication has occurred.

### Bounded continuation: credited sacks and fixed profile transfer

The five known sack-count differences are now separate reviewed source records,
not corrected play narratives. Each record binds the raw game hash, observed PBP
count and independently parsed `Sacked-Yards` box count. Generation checks both;
source auditing requires the exact per-team and league differences and retains
warning findings (958 PBP mechanisms versus 955 box credits). New or disappearing
differences fail. No missing play or loss yardage is invented. The new sidecar is
`reviewed-source-scope-v2.json`; candidate-01 and its original sidecar remain intact.

New synthetic source/audit positive controls failed before implementation.
Actual medium Codex review caught a case where a reviewed discrepancy could
disappear inside larger totals; a new failing control required exact
`official + reviewed difference` comparisons. Re-review is pending at this
checkpoint. The candidate-02 source audit passes with all six retained warning
findings (five teams plus league), raw input hashes, normalized denominators,
structure and decoder; independent candidate-02 reproduction is not yet supplied.
Historical source completeness remains false.

Before calibration, passing accounting was checked: every cached team box
reconciles gross passing yards minus sack loss to net passing yards, and net
passing plus rushing to total yards. The engine observer excludes sacks and
scrambles from pass attempts and reads engine gross passing yards with sack
loss/counts separate. Existing calibration/tuning regressions pass 42 tests.
No accounting change was needed or made. Neutral source-chart values require
measurement through the combined offense/defense engine rather than assuming
raw chart gain averages equal engine output.

One fixed candidate uses the already reviewed 1983 empirical calibration profile
unchanged: completion adjustment +0.049, interception adjustment +0.004,
passing-gain multiplier 1.37, rushing multiplier 1.0, pressure adjustment 0.
This reuses the documented calibration-profile mechanism, without searching
1977 coefficients or selecting teams. It is an explicit transfer hypothesis,
not proof that 1983 calibration applies to 1977. Candidate-02 uses the same four
seeded chart-focused source-calendar repetitions for a comparable pilot; no
additional profiles or broad tuning campaign are authorized by this pass.

#### Bounded pass result

The medium Codex re-review confirms the exact count comparisons and reports no
actionable defect. All 524 focused source/generator/audit/runner/calibration and
documentation tests pass; changed-file Ruff passes. Candidate-02 source auditing
passes with exact retained sack warning findings and explicit incomplete source
coverage. The strict original ledger remains unchanged. Candidate-02 has not
been independently regenerated; candidate-01's 84-file reproduction remains
available as earlier evidence only.

The same four source-calendar repetitions complete all 784 games. This remains
a pilot below the required 64 repetitions, with unchanged acceptance tolerances:

| Metric | Neutral candidate-01 | Fixed-profile candidate-02 | Source target |
| --- | ---: | ---: | ---: |
| Completion rate | 0.47711 | 0.51404 | 0.51318 |
| Interception rate | 0.05343 | 0.05788 | 0.05743 |
| Sack rate | 0.09321 | 0.09104 | 0.08891 |
| Passing yards/attempt | 4.21875 | 6.20190 | 6.49847 |
| Rushing yards/attempt | 3.35084 | 3.34552 | 3.84983 |
| Points/team-game | 13.26658 | 18.11926 | 17.17602 |

Team metric misses fall from 77 to 32. Passing misses the league tolerance of
0.25 by about 0.047 yards/attempt; rushing remains about 0.504 low against a
0.15 tolerance. The unchanged run multiplier explains why the transfer did not
address the systematic rushing shortfall. The 1983 profile repairs most passing
and scoring drift but is insufficient for 1977 qualification. No 64-repetition
run follows this failed pilot, and no second candidate/profile search was run.

The specific next engineering step is one prescribed global gain calibration
update through the existing profile controls, followed by the same pilot:
current observed/source ratios suggest roughly 1.15 for rushing and 1.44 for
passing (from 1.37), without changing completion, interception or sack settings.
These are proposed pilot values, not validated parameters. Review team-level
shape after that global update; the existing complete-cohort bounded gain
normalization is a separate possible follow-up if team residuals remain. Retain
all failed evidence and require unchanged fit bounds and full validation before
publishing. This checkpoint does not declare the 1977 season release-ready.

### Single prescribed global correction (candidate-03)

The owner authorized one additional global correction, followed by the same
inexpensive pilot and no further numerical iteration if it failed. Candidate-03
preserves candidates 01/02. The two derived ratios are
`1.0 * 3.8498293515 / 3.3455158169 = 1.1507431327` for rushing and
`1.37 * 6.4984671980 / 6.2018984201 = 1.4355120736` for passing. Rounded once,
the profile uses run 1.15/pass 1.44; completion +0.049, interception +0.004 and
pressure 0 remain unchanged. No team-specific coefficient, source fact or
tolerance changed.

All 784 games complete in the four-repetition comparable pilot:

| Metric | Candidate-02 | Candidate-03 | Source target | League tolerance |
| --- | ---: | ---: | ---: | ---: |
| Completion rate | 0.51404 | 0.51499 | 0.51318 | 0.015 |
| Interception rate | 0.05788 | 0.05776 | 0.05743 | 0.010 |
| Sack rate | 0.09104 | 0.09215 | 0.08891 | 0.010 |
| Passing yards/attempt | 6.20190 | 6.47602 | 6.49847 | 0.25 |
| Rushing yards/attempt | 3.34552 | 3.62384 | 3.84983 | 0.15 |
| Points/team-game | 18.11926 | 19.35204 | 17.17602 | diagnostic only |

All five league rate/gain targets except rushing are now within tolerance.
Team metric misses fall from 32 to 16: six rushing, two passing-yardage, five
interception, two completion and one sack metric. These are pilot observations,
not full-sample qualification. Largest remaining examples include Cleveland
rushing 3.527 versus 4.314, Miami rushing 3.906 versus 4.559, Dallas interception
rate 0.04545 versus 0.02688, and Pittsburgh passing 6.667 versus 7.718. Scoring
moves above the historical mean and needs continued joint review rather than
assuming higher offensive output is universally better.

The inspected run control does not uniformly scale all engine rushing: it scales
only resolved empirical observations for the four primary run families before
finite chart allocation. All 28 teams have only 1–8 explicit Draw observations,
below the 12-resolved-observation cutoff, so Draw uses aggregate fallback and
bypasses that empirical scaling. QB Time columns are also unchanged for all 28
teams. These are verified limits on the correction's reach, not proof that they
alone explain every rushing residual. Retained yards per Draw call stay roughly
3.87 to 3.81 in this pilot while Line Plunge, Off Tackle and End Run increase.
Selected-call averages include sacks/turnovers where applicable and are not
credited passing/rushing YPA.

The interception support review checks every offense/defense chart. All 111
screen interception cells remain `INT 5`; every pass family's permitted INT
spots and weighted INT cell masses are unchanged from candidate-02. These spots
are explicitly modeled support, not recovered historical air-depth facts.
Defense and special-teams CSVs are byte-identical for all 28 teams. Screen
retained-call interceptions are 326/8956 versus 331/9147; no pooled deep-screen
interception label appears. Large completed-screen gains remain possible through
yards after catch and are distinct from interception spot constraints.

The source/structure/decoder audit passes with the same retained source-scope
findings and incomplete coverage. The pilot still fails rushing, team metrics
and the required 64-repetition sample threshold. Therefore numerical iteration
stops here: no 64-repetition run, forced historical winners, target relaxation,
new accuracy exception or release claim. The next concrete engineering task is
to reconcile calibration coverage of sparse aggregate fallback families and
unaltered secondary rushing with the ordinary empirical gain control, using
synthetic tests and the existing post-allocation gain transformation where
appropriate. Measure the complete rushing mixture rather than applying another
unexplained coefficient bump. A standard bundled historical-season release is
not qualified under current fit/sample gates; calling it limited would not make
those failures pass. An experimental preview would require an explicit separate
policy decision rather than a silent waiver. Candidate-03 reproduction and full
release regression are also outstanding.

The existing chart-focused component validator additionally requires at least
1,000 team-games, alongside at least 64 repetitions. A 14-game schedule produces
896 team-games at 64 repetitions, so this unchanged gate would require at least
72 complete repetitions (1,008 team-games) for 1977. No threshold change or
larger run was made; this sample-plan detail is separate from the observed fit
failures and must be accounted for before eventual qualification.

Actual medium-reasoning Codex review of candidate-03's derivation, source-scope
checks, play-family/fallback evidence and interception review found no actionable
error or unsupported causal claim. No production code changed in this pass;
existing 524-test production validation remains the preceding checkpoint, and
the current documentation test passes. Detailed candidate identity and remaining
verification gaps are recorded in ignored `candidate-03/handoff-receipt.json`.

### Calibration coverage correction (candidate-04)

The owner authorized the concrete fallback coverage fix, with no further
coefficient change. The existing run control previously acted only on empirical
primary run observations. The generator now applies the same factor once to
aggregate fallback primary run columns absent from empirical input. Empirical
columns are not scaled again. Shared breakaways and QB Time are unchanged:
QB Time couples positive scrambles with negative sacks and requires separate
pressure/loss treatment rather than indiscriminate rushing scaling. Existing
numeric/fumble rounding, flags and direct-run caps are reused; event tokens and
physical masses remain protected. Both PFR and nflverse adapters pass their
existing profile factor to this fallback path. Standalone default factor 1
retains byte-identical output.

Four positive synthetic cases failed for the missing API before implementation.
Nine new controls now pass, including neutral byte identity, fallback response,
no empirical double scaling, flags/negative/fumble mass and physical caps. Two
initial new assertions incorrectly expected unchanged row positions; shared
layout can move unchanged cells, so these now require identical physical weighted
token distributions. No existing test expectation was weakened. The broader
focused generator/adapter/normalization suite passes 304 tests, with no reported
skips or warnings; actual medium Codex review finds no actionable defect.

Candidate-04 uses exactly candidate-03's source input hashes, profile, source
scope, seed family, schedule and four repetitions. Static comparison establishes
that only Draw's physical weighted distribution changes across all 28 teams;
all other offense distributions, all INT masses, and every defense/special CSV
are unchanged. Screen INT support stays at the reviewed INT 5. Runtime/engine
fingerprints correctly change because the identity includes generator code;
older reports remain historical comparison receipts, not fresh qualification.

All 784 pilot games complete. League metrics now all meet unchanged point-estimate
bounds: completion 0.51418 (target 0.51318), interceptions 0.06039 (0.05743),
sacks 0.09256 (0.08891), passing yards/attempt 6.47209 (6.49847), rushing
3.76217 (3.84983). The isolated fallback fix raises rushing from 3.62384 to
3.76217 without another multiplier increase. Scoring rises to 20.47577 per
team-game versus historical 17.17602; this diagnostic remains important even
though scoring is not one of the five fitted contract rates.

Fifteen team point estimates remain outside bounds: five passing-yardage, three
rushing, three completion, three interception and one sack metric. Only four
misses persist from candidate-03: Cincinnati rushing, Buffalo passing yardage,
Oakland completion and Pittsburgh passing yardage. Twelve previous misses
resolve and eleven different misses appear as game paths change. Four repetitions
are insufficient to decide how much of this variation is sampling/context versus
systematic conditional fit; do not chase every pilot miss with coefficients.
Examples include Buffalo passing 7.224 versus 6.120, Oakland completion 0.52373
versus 0.56790, Cincinnati rushing 3.289 versus 3.814 and Pittsburgh passing
6.810 versus 7.718. The remaining problem is team-level/conditional fit and joint
scoring, not the now-corrected Draw routing or interception-distance support.

Under the explicit exit rule, failed team point estimates stop progression to
72 repetitions. No further numerical iteration, changed tolerance, forced
historical qualifier, accuracy waiver or normal release claim follows this
pilot. The next bounded diagnostic should hold the charts fixed and examine the
four persistent team residuals in common play/defense contexts, distinguishing
chart allocation from schedule/situation mixture before changing any model.
Candidate-04 source/structure/decoder checks pass with the existing disclosed
source limitations. Independent reproduction, full-calendar revalidation for
this candidate and complete release regression remain outstanding. Nothing was
pushed, tagged, published or installed into distributed seasons.

### Fixed-chart diagnosis and sampling checkpoint

The owner authorized continuing finite evidence-supported diagnosis through a
reviewable candidate rather than pausing after each pilot. A paired controlled
comparison now covers 165,888 fresh-engine snap trials (41,472 distinct seeds
shared across four offenses), two first-and-ten field positions, three common
defenses, nine calls and six formations. Weighted normal-policy summaries are
conditional comparisons, not full-game/historical fit or independent-season
probabilities. Actual medium Codex review confirms arithmetic and seed separation;
shared offense seeds are explicitly paired rather than independent observations.

Cincinnati rushing is 4.106/4.000 in the two contexts versus source 3.814, so its
pilot shortfall does not persist in the pooled common situations. Buffalo passing
remains above Pittsburgh in both contexts (7.682/7.111 versus 7.136/6.386), despite
source targets 6.120 versus 7.718. Oakland completion is 0.537/0.548 versus source
0.568. These results support distinguishing conditional chart shape from schedule
and call mixture; they do not establish a single causal defect.

Sixteen additional fixed-chart source-calendar repetitions (3,136 games, all
complete) use the next independent seed family. All five league rate/gain point
bounds pass. Team point-estimate misses fall from 15 to seven: passing YPA for
Bears 5.982 versus 6.787, Bills 7.073 versus 6.120 and Steelers 6.357 versus
7.718; Dolphins rushing 4.105 versus 4.559; interception rates Broncos 0.05006
versus 0.03834, Chargers 0.06554 versus 0.05420 and Cowboys 0.03728 versus
0.02688. Cincinnati rushing and Oakland completion now pass. This remains below
the unchanged 64-repetition/1,000-team-game minimum and is diagnostic evidence,
not a merged or qualifying report.

Scoring remains high at 20.05 versus historical 17.18 per team-game. The preceding
four-repetition sample had similar total gross yards (309.47 versus 306.11) and
slightly lower play volume (63.31 versus 64.77), but more dropbacks (53.35% versus
42.30%) and field-goal attempts (2.40 versus 1.58 per team-game). These are policy
and game-context differences, not proof of a pace defect or an established scoring
cause. Historical dropback shares are not exact called-pass shares because
scrambles can be credited as rushing.

One further bounded application uses the existing documented complete-cohort
source-driven gain-normalization recipe: fixed sixteen training repetitions,
all 28 teams, the same global profile, source-only targets, existing shrinkage
and relative bounds. No selected-team factor, coefficient sweep, event-rate or
tolerance change is introduced. Candidate-04 and every earlier candidate remain
preserved. This method addresses stable gain allocation; interception residuals
and scoring remain separate risks. A comparable pilot must justify proceeding
to the required 72 repetitions; failure will be reported without a silent waiver.

### Complete-cohort gain recipe and qualification checkpoint

Candidate-05 applies the existing documented whole-cohort normalization once,
with unchanged candidate-04 global profile and event controls. All 56 derived
passing/rushing factors use the fixed source-attempt-weighted centering,
shrinkage 200 and bounds [0.8, 1.25]; none is hand edited. All 28 teams participate.
The source-only training contract has no circular output identities. Sixteen
training repetitions use the documented seed and end-zone interception-return
policy. The separate sixteen-schedule diagnostic uses the next independent seed
family, completes 3,136 games, and passes all five league and all 140 team rate
point bounds. Scoring remains 20.364 versus historical 17.176, a retained joint
behavior limitation rather than an asserted improvement.

Independent regeneration repeats training from source and reproduces all 84
chart CSVs byte-for-byte. Source consistency, decoder, raw hashes, normalized
counts, reviewed scope and reproduction checks pass; historical source
completeness remains explicitly false. Physical protected token masses and
quarterback-time values remain equal for all teams; all 56 defense/special files
are byte-identical and screen interception support remains INT 5. Actual medium
Codex review confirms fixed-recipe arithmetic. Its receipt-binding finding was
corrected with complete before/after file hashes, explicit per-file comparisons,
script identity and end-of-comparison input rechecks; re-review is clean.

The current candidate also completes the actual 196-game regular calendar plus
seven simulated postseason games under Hard AI, with no failure. This is a
single historical outcome diagnostic, not repeated-season qualification or
proof of official NFL tiebreaks. Historical player-name rosters are not supplied
by the prepared 1977 template; do not advertise complete named-player commentary.

The required 72-repetition run completes all 14,112 games (1,008 team-games per
team). All league rates and 138/140 team metrics pass. It still **fails** two
interception-rate bounds: Buccaneers 0.083191 versus source 0.093458 (error
0.010267, bound 0.010), and Redskins 0.052169 versus 0.041775 (error 0.010394).
Points/team-game remain high at 20.179 versus 17.176. No release qualification or
bundling claim follows this failure.

These two excesses beyond the boundary are less than 0.3 replication standard
errors. Tampa Bay has 30,496 attempts/2,537 interceptions; its across-repetition
SE is 0.001528 and approximate 95% t interval [0.080170, 0.086264]. Washington
has 30,152 attempts/1,573 interceptions, SE 0.001410 and interval
[0.049413, 0.055035]. Both intervals overlap their unchanged acceptable bands.
One predeclared extension to 144 total repetitions therefore retains the same
charts, master seed and all original 72 schedules. It is an uncertainty check,
not a search for a favorable independent seed or changed coefficient. If it
still fails, stop this numerical continuation and report the concrete residual;
no repeated extensions, event-rate adjustment or threshold waiver is implied.

### Final bounded 144-season result: one interception blocker

The predeclared extension completes all 28,224 games (2,016 team-games per team).
Its first 72 replication summaries exactly match the preserved earlier run;
no seed selection, coefficient change or tolerance relaxation occurred. All five
league metrics and 139/140 team metrics pass. Tampa Bay now clears its boundary.
Washington remains outside its interception-rate tolerance: 3,217 interceptions
on 60,728 attempts, rate 0.0529739165 versus source 0.0417754569, absolute error
0.0111984596 against 0.010. The across-repetition standard error is 0.000925;
the approximate 95% t interval is [0.051209, 0.054867]. This sampling interval
still overlaps the acceptable band, but it does not make the required point
bound pass. Scoring remains 20.1085 versus historical 17.1760 per team-game.

This ends the authorized numerical continuation. Candidate-05 is reproducible
and source-consistent within disclosed coverage, and all games complete, but it
is not fit-qualified for normal bundling. Do not publish it under an accuracy
claim, alter its source totals, loosen the tolerance, keep extending until a
favorable sample appears, or tune Washington alone. A subsequent engineering
investigation should examine the complete-cohort interception allocation and
source-to-engine event mapping under fixed contexts, with synthetic test-first
proof if a concrete defect is identified. Otherwise a different release scope
or explicitly experimental season policy requires a consequential owner decision.

The 72-season raw receipt is preserved losslessly as engine-fit-72.json.gz with
verified round-trip SHA-256 and a compact qualification summary. The 144-season
receipt and compact qualification summary preserve the final failure. No 1977
charts are copied into distributed seasons and no release version or tag is
created. Independent integration regression and native Windows acceptance can
still proceed on the reviewed source/runner/calibration infrastructure and
harness changes; those checks cannot waive the 1977 fit blocker.

### Candidate-06: isolated interception diagnostic, not qualification

The owner authorized one global interception adjustment experiment: +0.004 to
+0.0015, with the candidate-05 gain normalization, raw sources, template and era
rules frozen. Existing canonical generation deliberately couples the profile
hash and normalization training. An ignored, reviewed diagnostic wrapper permits
only this declared hash difference; it is not canonical reproduction or a
production qualification mechanism. Five synthetic controls and actual medium
review cover the wrapper. Independent wrapper generation matches all 84 CSVs;
candidate-05 remains preserved. No production generator code changed.

The paired held-out 16-repetition diagnostic (seed 24261120) completed all 3,136
games, 224 per team. All five league bounds pass; league interception rate fell
from 5.972% to 5.571%. Four team point estimates miss unchanged bounds:

| Team / metric | Observed | Target | Allowed interval | Attempts |
| --- | ---: | ---: | ---: | ---: |
| 49ers completion | 52.494% | 49.097% | 46.097–52.097% | 6,837 |
| Buccaneers completion | 44.243% | 40.810% | 37.810–43.810% | 6,844 |
| Chiefs interception | 5.932% | 6.952% | 5.952–7.952% | 6,642 |
| Jets interception | 6.023% | 7.222% | 6.222–8.222% | 7,040 |

The global rate reduction did not monotonically lower every team's realized
rate: Washington increased from 4.545% to 4.821% and Dallas from 3.279% to 3.671%
in this paired pilot. These are finite-game/context results, not proof of the
exact causal mechanism. Interception distances, defense and special charts are
unchanged. This pilot is neither enough samples for qualification nor a reason
to relax any bounds. No 72/144 extension or additional tuning was started.

Local evidence: `.ai-audits/chart-generation/1977-reviewed/candidate-06/`
contains `paired-comparison.json`, `paired-team-metrics.csv` (all 140 metrics and
denominators), `engine-fit-diagnostic-16.json`, static/method/generation receipts,
and wrapper review logs. `contract-diagnostic.json` binds diagnostic identity
only; it is not a qualifying source contract. Candidate-05's prior 144-run
Washington miss and source-coverage limitations remain unchanged.

### Finite global search completed: candidate-05 nominated

The owner-authorized five new adaptive trials are complete; no sixth trial was
started. Each uses the same 16-repetition/3,136-game paired screening schedule
(seed 24261120), with only the shared interception adjustment varied. Because
this batch was reused adaptively, it is selection evidence, not untouched
held-out qualification. Both earlier reference candidates remain in the ranking.
All seven values pass the five league bounds. Ranking uses failed team metrics,
then maximum and summed normalized error, rather than Washington alone:

| Candidate | INT adjustment | Team misses | Maximum normalized error | Points/team-game |
| --- | ---: | ---: | ---: | ---: |
| 05 (reference) | +0.004 | 0 | 0.928 | 20.364 |
| 10 (trial 4) | +0.00375 | 1 | 1.057 | 20.136 |
| 07 (trial 1) | +0.00275 | 2 | 1.100 | 20.161 |
| 08 (trial 2) | +0.003375 | 2 | 1.219 | 20.007 |
| 11 (trial 5) | +0.0035 | 3 | 1.191 | 19.863 |
| 09 (trial 3) | +0.00225 | 3 | 1.216 | 19.841 |
| 06 (reference) | +0.0015 | 4 | 1.199 | 20.065 |

These adjustment values are probability changes; +0.004 is +0.4 percentage
points, not the realized seasonal rate. Actual team rates can move differently
because the finite games and subsequent contexts change. No profile changes
interception distances, defense/special charts or source facts.

Canonical candidate-05 is nominated as the best overall evidence, retaining its
unaltered 144-repetition report: Washington 3,217 interceptions / 60,728 attempts
(5.297392%) versus a 4.177546% target and unchanged one-percentage-point tolerance.
Its strict fit remains FAIL. The source-era scoring diagnostic also remains high
(20.108 versus 17.176 points/team-game); passing the five league bounds does not
certify scoring pace. The release owner chooses the now-authorized transparent
statistical-exception route, rather than an optional new individual-team chart
transformation. No such transformation has been implemented.

Selection evidence is bound in local `finite-int-search-selection.json`, with
all seven values in `finite-int-search-ranking.csv` and every pre-run rationale
in `finite-int-search.json`. Final source/runtime identity, reproduction, policy
acceptance, integration and actual native packages still need verification. Old
report metadata must not be rewritten or called fresh execution. The separately
authorized one-batch unused-seed diagnostic is robustness context; it cannot erase
the retained 144-run miss or restart an adaptive search.

### Independent-seed robustness check: no individual chart edit

After finite selection, one predeclared unused master seed (20261109) ran 16
schedules / 3,136 games on the unchanged canonical candidate-05. The seed inventory
found no derived-seed collisions. All games completed and all five league bounds
pass. Three team INT point estimates miss bounds in this smaller batch:

| Team | Observed | Target | Upper bound | Attempts | Prior 144 result |
| --- | ---: | ---: | ---: | ---: | --- |
| Washington | 5.2278% | 4.1775% | 5.1775% | 6,695 | 5.2974%, FAIL |
| Dallas | 3.8897% | 2.6882% | 3.6882% | 6,530 | 3.6027%, PASS |
| Denver | 4.9223% | 3.8339% | 4.8339% | 6,176 | 4.6245%, PASS |

Washington's positive residual persists. Replication means are 5.2193% (new 16,
SE 0.2537 percentage points) and 5.3038% (prior 144, SE 0.0925 points); their
difference is 0.313 combined SE, consistent with ordinary between-batch variation.
This does not establish an exact chart-specific mechanism. Dallas/Denver's new
boundary crossings also show why a small pilot cannot replace the larger report.
No report was pooled, erased, extended or used to select a favorable replacement
seed. No individual-team correction is justified merely to flip these checks.

The new report retains the actual runtime fingerprint at execution; the prior
144 metadata remains untouched. Core loaded definitions and all chart/profile
inventories match. Local evidence is under
`candidate-05-independent-20261109/`, including `identity-preflight.json`,
`independent-comparison.json` and `all-team-metrics.csv`. This 224-team-game batch
is diagnostic robustness context, not the minimum-sample qualification campaign.
Both its extra misses and the retained primary 144-run Washington miss must be
disclosed in the final season notes and acceptance record.

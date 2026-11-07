# Public-only unit fixture cleanup

Release-verification component, 2026-11-06, under
[VAL-010](issues/VAL/VAL-010.md). This changes test fixtures only, not gameplay,
chart generation, chart data or player-facing behavior. It does not certify a
release or replace the full regression.

## Baseline and scope

The four assigned modules were copied with the current Python package and only
the public `seasons/2026/` sample into an ignored clean snapshot. They passed
137 tests and skipped 25. The usual local run skipped only eight because ignored
historical data supplied the other seventeen cases. No production behavior was
changed to create a failing baseline: the reproduced defect was missing unit
coverage when private data was absent.

The modules are `test_commentary.py`, `test_interactive_game.py`,
`test_season_rules.py` and `test_team_charts.py`. Their actual historical-file
dependencies and corresponding skip guards are removed. Fixtures are now
temporary, independently specified synthetic inputs, except that the modern
season-rule test still uses the public 2026 YAML. Mock team-selection strings
also use the public sample IDs; they do not load files.

## Existing expectation changes

- Roster loading now expects exactly `Fixture Runner` from a newly written
  roster, rather than a nonempty private roster. This strengthens the original
  file-loading assertion.
- Team/season discovery uses synthetic 2026/2027 directories and explicit team
  inventories, including an ignored non-year directory and a directory without
  a chart. It preserves newest-first ordering, season filtering, tuple shape and
  unprefixed names, while replacing potentially empty loops with exact results.
  The three mocked selection cases change only their year/team/path inputs from
  historical IDs to 2026 Ironclads/Thunderhawks; their call and return contracts
  remain asserted.
- Season-rule parsing uses independently written legacy-style configurations
  with deliberately synthetic years 2050/2051. Those year assertions replace
  1972/1983 fixture identities; no historical rule claim is implied. False
  two-point eligibility, sudden-death format, fifteen-minute periods, regular
  ties, serialization and overtime conversion retain their original checks.
  The modern public-2026 checks are retained.
- Chart parsing uses invented CSV files beneath a temporary `2026` directory.
  Directory names and short-name expectations change from historical clubs to
  explicit synthetic names. Separate checks cover generated fallback names and
  configured metadata distinguishing clubs with shared prefixes. The 28-team
  loading inventory is retained. The previous “more than five” fumble-range
  assertion is strengthened to the exact fourteen ranges written by the fixture.
- Extra-point tests retain both numeric `0`/`1` and text `NG`/blank encodings.
  Fixtures explicitly establish their failure rolls; assertions now check exact
  roll sets as well as known successful controls. Numeric encoding is checked on
  all 28 synthetic teams, and the text-encoding inventory asserts one configured
  failure per team instead of merely a non-null field. Historical format labels
  are removed because encoding, not season-specific chart contents, is tested.
- Defense parser checks use independently chosen numeric values and retain the
  exact populated-column sets, absent columns, parentheses and touchdown markers
  for B-3 and D-5, plus all thirty formation/subrow combinations. Offense values
  similarly change to declared synthetic values while retaining breakaway,
  negative gain, empty cell, BLACK, supplemental lookup and fumble-range checks.
  One additional test explicitly preserves a primary QT token and a sideline
  marker. No private chart cells were read or copied to make these fixtures.

No assertion was relaxed to accommodate a production failure, and no new skip
was added. Historical team-specific integration behavior belongs in the separate
private runners; these unit tests now test the loader and caller contracts.

## Verification

The revised four-module suite passes **163 tests with zero skips** in a new
public-only snapshot. This is the original 162 collected tests with their 25
skips restored, plus the new QT/sideline control. Focused Ruff and documentation
link validation pass. The ignored evidence lives in
`.ai-audits/release-readiness/public-unit-fixtures-01/`; before/after logs and
snapshot file hashes preserve the verification scope. Full-suite, backend,
browser, gameplay and chart-accuracy checks remain the parent release task.

No player guide update is needed because these changes affect only test inputs.

## Full core development checkpoint

On 2026-11-06, a separate intended-public snapshot captured 959 tracked and
intended new nonignored files using `git ls-files -c --others --exclude-standard`.
Original `seasons/1972/` and `seasons/1983/`, ignored private inputs, caches,
dependencies and Git internals were excluded. Public generated season directories
and the public 2026 samples were included. Every copied file matched its source
hash before and after capture. The captured inventory SHA-256 is
`66cd77566c5c014fde578e95c742fa54dd4d484f5c8290006427c3fcf675b8e9`.

The complete core command, `/opt/homebrew/bin/python3.11 -m pytest tests/ -q -o
addopts= --tb=short -rs`, completed with **9,633 passed, 170 failed and zero
skips** in 627.34 seconds. No warnings were reported. All 959 captured files
remained unchanged throughout the run. No failure concerned a missing private
chart or historical unit fixture. The failures were confined to the concurrent
fumble work: 36 in `test_reported_fumble_gain.py` and 134 in
`test_retained_fumble_incompletion.py`. They include pending reported-gain API
and fixture changes, retained-fumble fields and resolution, and untimed-try clock
behavior. These failures were retained, not skipped or weakened.

The ignored evidence directory is
`.ai-audits/release-readiness/public-unit-full-01/`: `run.json`, `pytest.log`,
`snapshot-01-manifest.json`, `failure-groups.json` and `live-drift.json` record
the command, result, file identities and failure groups. A comparison immediately
after the run found thirteen changed live files and three new files, including
the engine/source implementations and both failing test modules. Thus this is a
frozen development checkpoint, not a result for the moving working tree. A fresh
full candidate run remains required after the owners converge their changes;
this check does not replace backend, browser, gameplay or chart-accuracy gates.

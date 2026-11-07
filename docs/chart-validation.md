# Generated Chart Release Gate

[Documentation index](README.md) · [Development guide](development.md)

Pull-request and release CI validate both committed generated cohorts using only
public chart files. Release builds depend on this mandatory `chart-quality` job.
It checks the complete team count, chart structure, loadability, exact mechanics
and decoder coverage, and preserves its JSON report. It requires no private
source host, repository URL/SHA variables, network fetch or source archive.

```sh
python3 scripts/audit_public_charts.py --season-dir seasons/1983-generated \
  --expected-teams 28 --output .ai-audits/public-chart-quality-1983.json
python3 scripts/audit_public_charts.py --season-dir seasons/2024 \
  --expected-teams 32 --output .ai-audits/public-chart-quality-2024.json
```

These public checks do not claim source regeneration or historical accuracy.
Private source reproduction and the deeper 64-repetition accuracy measurement
remain local maintainer checks using `scripts/prepare_chart_sources.py` and
`scripts/audit_generated_charts.py`. Their original checks and accuracy bounds
remain intact. The corrected modeled 1983 candidate has local reproduction proof
and explicit completion-rate exceptions for the 49ers and Falcons; the corrected
2024 candidate has the disclosed Ravens rushing-fit exception. These exceptions
are reported to the owner, not converted to passing accuracy assertions.

The broader [owner acceptance charter](dev-notes/chart-confidence-agent-charter.md)
tracks additional research and reference comparisons. Public CI success is not a
claim that this larger charter or historical source truth has been established.

The raw `audit_chart_decoder(team_dir)` component in `paydirt.chart_audit` checks
the normalized CSV bytes before a reference comparison. It censuses 73 weighted
columns, rejects duplicate/invalid rows, lossy normalization and unsupported
consumer tokens, and reports missing rows, blank defaults and known B/QT random
fallbacks separately. Defense subrows use their 36 physical combinations; other
columns use 216. `fully_supported` is false when known defaults/fallbacks remain,
even if the census itself passes. This includes the legacy FG table-penalty
five-yard placeholder. Defensive return modifiers have separate weighted
categories for real-kick returns and the shared interception/fumble-advance
column. The result binds the three raw CSV hashes,
rechecks their bytes and retains `release_certified: false`. It is not a
standalone reference collector or an authored-game accuracy assessment. Private
reference inputs still require the declared stable freeze and local-only output
described in the [comparison protocol](dev-notes/chart-reference-comparison-protocol.md).

This census also runs inside the existing generated-source component for every
chart folder. Generated-source success requires a fully supported decoder
result: known defaults and random fallbacks remain visible census limitations
but block the generated-source check. The combined component gate independently
requires `checks.decoder: true`; a missing check cannot inherit a source pass.
Each source report retains the per-team raw hashes and weighted census.

The deterministic engine/observer controls now include a real punt, a punt snap
fumble and accepted/declined offensive and defensive punt-foul rerolls into a
snap fumble. Pending recovery does not consume dice or change state before the
choice; an accepted foul does not retain a fumble attempt. Saved decision
receipts retain the engine's `punt_snap_fumble` fact,
so a retained aborted snap counts as a rushing attempt rather than disappearing
from the offensive-play denominator. Four additional controls preserve accepted
return-penalty first-down rights on an own recovery, including fourth-down
rushing and punt snaps. The engine carries those rights with each assessed
penalty through live/nested settlement and into punt double-foul handling;
erasing them fails the gate. Four further controls identify actual fouling
teams across punt/return charts, enforce a single selected assessment, preserve
offset timing/period extension and keep a selected punt foul's first-down
rights. Mutants that erase timing or fouling-team identity, or borrow another
foul's first-down flag, fail these controls. Physical versus credited fumble
yardage, complete special-teams combination coverage and full-game confirmation
remain explicit limitations, not historical fit passes.
Another replay control preserves the next offensive decision after a return-only
offset, including a period-ending untimed down. Five retained-kick controls
verify fair-catch/downed markers, touchback foul choices and deferred blocked-
punt recovery with actual saved chart lookups. Replacing a blocked result with
numeric punt distance fails the gate. These extend the existing engine component.

## Run the gate

From the repository root, with Python and PyYAML installed:

```sh
python3 scripts/audit_generated_charts.py --season-dir seasons/1983-generated --contract config/chart-validation/1983.json --output .ai-audits/chart-quality-1983.json --repetitions 64 --workers 4 \
  --source-inputs /path/to/1983/source-inputs.json --source-stats-dir /path/to/1983/stats --reproduced-dir /path/to/1983/reproduced
python3 scripts/audit_generated_charts.py --season-dir seasons/2024 --contract config/chart-validation/2024.json --output .ai-audits/chart-quality-2024.json --repetitions 64 --workers 4 \
  --source-inputs /path/to/2024/source-inputs.json --source-stats-dir /path/to/2024/stats --reproduced-dir /path/to/2024/reproduced
```

Each command plays 64 repetitions of the public source's actual regular-season
schedule: 14,336 games and 1,024 team-games per team for 1983, and 17,408 games
and 1,088 team-games per team for 2024. The development master seed defaults to
20261108. Seeds derive as master + repetition index × 1,000,003 + game index ×
1,009. The chart-confidence charter separately reserves held-out master 20361108;
do not inspect it before freezing and announcing candidate fingerprints. The gate
requires local normalized source statistics, every declared raw generation input
and a separately regenerated chart directory. The input JSON maps the manifest's
portable input labels to paths, relative to that JSON's directory or absolute.
The gate rechecks actual bytes and rejects missing or changed inputs; the source
manifest's own success flags cannot substitute for this evidence. Keep source
materials local and ignored. Private imported developer charts are not inputs to
these source checks. Acquisition and independent regeneration happen before the
gate; the gate itself does not download source data.

You can prepare a reviewed local cohort bundle with the maintained tool:

```sh
python3 scripts/prepare_chart_sources.py --bundle /path/to/reviewed-public-bundle/2024 \
  --candidate-dir seasons/2024 --reproduced-dir .ai-audits/chart-sources/2024/2024-reproduced \
  --output .ai-audits/chart-sources/2024/source.json
```

The bundle contains a complete `inventory.json`, `recipe.json`, `contract.json`,
public `inputs/` and public rules/rosters under `template/`. The tool verifies the
actual input/candidate bindings, executes the existing generator and requires
identical CSVs, manifest, rules and metadata. It preserves the execution log and
status, rejects existing output paths, and binds both generator entry points and
all Python source adapters before and after generation. It writes a gate input
map only after success. This is local preparation; it performs no acquisition,
upload or game simulation, and does not establish upstream source truth.

When all three explicit source options are absent, the cohort gate discovers
`.ai-audits/chart-sources/SEASON/source.json`. Before starting games it revalidates
actual inputs, the supplied contract, candidate/reproduction fingerprints,
runtime/code inventory, producer command/status and retained log. Partial explicit
options cannot use discovery. Failed or stale preparation fails before simulation.
The independent source/statistics/mechanics checks still run. Output paths cannot
replace chart or source evidence, including when the receipt fails validation.

The `pack_chart_sources(bundle_dir, archive_path)` API creates a deterministic
local archive from the verified file inventory. Stage a separately approved,
pinned archive before preparation:

```sh
python3 scripts/stage_chart_sources.py --archive /path/to/approved-2024.tar.gz \
  --sha256 REVIEWED_64_CHARACTER_SHA256 --destination .ai-audits/chart-sources/2024/bundle
```

The staging command requires a new destination, verifies the archive digest and
complete file inventory, and rejects path traversal, duplicate members, links and
special files. A failed new directory remains diagnostic evidence; remove or
replace it deliberately before retrying at that path. Staging and preparation
always retain `release_certified: false`.

Private staging and preparation are local maintainer tools. CI does not download
or independently regenerate their source inputs, and no remote source hosting is
required for the release path. The byte-bound local proof remains in ignored
`.ai-audits/`; raw source and private provenance must not be uploaded as CI or
release artifacts. The combined local audit still requires successful current
preparation or all three explicit source paths. Every component report retains
`release_certified: false`; a component pass describes its stated checks, not an
owner release decision.

The audit defaults both teams to automatic touchback after an own-end-zone
interception. Add `--attempt-end-zone-interception-returns` to declare that both
physical teams attempt returns instead. This uses the core coaching preference;
it changes neither rules nor source targets. The Python `run_engine_audit` and
AI factory accept `attempt_end_zone_interception_returns=False` by default.
Worker tasks/results, report metadata and each game's home/away preferences bind
the declaration. Missing, nonboolean or inconsistent declarations fail validation.
When reusing `--engine-report`, request the same option as the saved report;
reports from the opposite mode are not interchangeable. This declaration supplies
no historical elections, conditional gain targets or recovery dice entitlements.

Reports collected with `--engine-only` are evidence, not release certification.
To reuse a saved report, pass `--engine-report path/to/report.json` to the full
command. The gate rejects changed engine/policy sources, chart inputs, schedule,
missing teams, unreconciled totals, impossible play denominators and fewer than
1,000 team-games per team. It separately requires at least 64 independent source
schedule repetitions; 59 repetitions across 17 appearances do not qualify even
though they exceed 1,000 team-games. Thirty-four controlled engine events also verify made and
missed field goals, zero-yard sacks, QT fumble sacks, rushing and ordinary
completed passes, and exclude offsetting no-plays while retaining credited
outcomes. Punt controls distinguish nominal foul size from assessed half-distance
yardage, verify both actual teams in the existing five-versus-fifteen exception,
and reject changed catch coordinates, missing assessments and erased declined-foul
annotations. Retained blocked-punt checks require the `blocked_kick` result
class and its completed clock receipt, and reject class substitution or an erased
trace. These controls preserve the existing exception; they do not establish
that every legacy special-teams policy matches the original board-game rules.
Loaded runtime definitions, module origins, internal aliases and literal policy
constants must match the current package source. Parent and workers check this
identity before and after execution; parallel runs use fresh spawned workers.
The report must retain matching worker identities. These are consistency checks
within a trusted process, not hostile-process attestation or a substitute for
the final clean-snapshot check.
Each report retains per-game seeds, matchups and counts, checks legal completion,
scoring and net yardage, and reconciles game receipts against aggregate totals.
Final scores, replication totals and uncertainty summaries are reconstructed
from those same receipts; altering a summary cannot hide behind valid aggregates.
Per-repetition metrics report ranges and between-repetition standard errors;
these describe simulation sampling, not historical model uncertainty.
Small `--repetitions` runs are useful diagnostics and fail the release sample
minimum. `--policy hard --engine-only` and `--policy balanced --engine-only`
require 128 team-games per team and validate mechanics separately from reference
fit, with at least eight independent source schedules. Balanced matches the legacy
auto-game policy, not web medium difficulty.
Bounded `run-heavy` and `pass-heavy` policies retain clock/endgame decisions and
use 95% of the declared normal-call weight on their named family; their minimum
is 16 team-games per team. Reports include ordered per-game call/result receipts,
selected defense, situation/call and outcome counts, and declared normal offense
and defense weights. Validation reconstructs distributions and comparable-
situation repetition from those receipts, and reconciles selected-call
denominators (including field goals) against each finalized game.
Repetition compares the next offensive choice for the same team/down/distance/
mode, regardless of selected defense, and resets between games. Distance bands
are 1–3, 4–7 and 8+ yards. Full call/outcome inventories retain defense separately.
Group reports include samples, call shares, distinct calls and longest streaks;
concentration needs review against chart strengths rather than a universal cap.
These policies cannot substitute for the declared calibration policy.

Nine additional `repeat-*` policies put all normal-context weight on one primary
call: `line-plunge`, `off-tackle`, `end-run`, `draw`, `screen`, `short-pass`,
`medium-pass`, `long-pass`, and `te-short-long`. For example,
`--policy repeat-screen --engine-only --repetitions 1` exercises repeated screens
while preserving legal clock, goal-line, fourth-down and special-teams decisions.
These stress reports require one complete source schedule and at least 16
team-games per team; historical fixed-mix fit does not apply. Their call receipts
must confirm the declared normal call. A completed game does not by itself
establish that repeatedly choosing the call has sensible yield or risk.

The `audit_campaign_bundle` API in `paydirt.chart_release_gate` requires both full
cohorts and all fifteen report families per cohort: training, held-out, Hard,
balanced, two family stresses and nine repeated calls. It validates current
runtime, declared policy/seed, exposure, accounting and applicable fit through
the existing engine validator. This census is a component, retains
`release_certified: false`, and does not yet load or certify the complete charter
artifact bundle.

Validate saved, hash-bound campaign files without starting new games:

```sh
python3 scripts/audit_generated_charts.py --campaign-bundle .ai-audits/chart-confidence/campaigns.json --output .ai-audits/chart-confidence/campaign-census.json
```

The schema-1 bundle contains `schema_version: 1` and a `cohorts` object with
exactly `1983-generated` and `2024`. Each entry declares `season_dir`, its current
`chart_fingerprint`, and `contract`, `training`, `held_out`, and `policies`.
Each contract/report reference is an object with `path` and `sha256` (64 lowercase
hex digits); policy keys name all thirteen nonreference policies above. Relative
paths resolve from the bundle directory. The validator reads actual bytes and
rejects changed files, duplicate JSON keys, nonfinite numbers and substituted
inventories. It loads reports one at a time. Output must be separate from bundle
inputs and candidate directories, including when validation fails. This mode
cannot be combined with cohort execution options and remains a noncertifying
component. See the [bundle design](dev-notes/chart-readiness-bundle-design.md)
for the full integration work still required.

The `readiness_file_inventory(root)` and `audit_readiness_freeze(root, freeze)`
APIs validate a separate frozen-byte component. Schema 1 binds `files` (the
independently discovered implementation inventory), `engine_fingerprint`, both
`cohorts`, and `reserved_families`. Each cohort binds `season_dir`, its
`chart_fingerprint`, a `{path, sha256}` contract and a `source_inputs` map using
every generation-manifest input label. Paths resolve from the supplied root.
Core resources, tests, generators, source adapters, UI/configuration/dependencies,
workflows and acceptance definitions are included; caches, installed dependencies
and local historical seasons are excluded. Changed or omitted files, source-label
substitutions and changes during validation fail. The reserved-master registration
does not prove non-observation. A parent freeze announcement, seed-use history and
the other acceptance components remain required; this API always retains
`release_certified: false` and starts no games.

The separate `audit_regression_evidence(root, freeze, evidence)` API checks
structured execution logs against that same unchanged freeze. Schema 1 contains
`schema_version`, `freeze_sha256` (SHA-256 of canonical sorted compact freeze JSON)
and `commands`. The command map requires all twelve AGENTS checklist identities;
`required_regression_commands()` supplies their exact argument lists and working
directories, using the current Python interpreter. Each entry binds a log by
`{path, sha256}`. A log must retain actual `argv`, absolute `cwd`, integer
`returncode`, `stdout` and `stderr`. Wrong/partial commands, nonzero or invalid
statuses, absent/changed logs and changed implementation/source/candidate bytes
fail. Existing skip/warning lines remain visible in the result and do not become
new skips or suppressed failures. The command inventory is checked against
`AGENTS.md` by a regression.

Use the maintained collector only against a stable frozen candidate:

```sh
python3 scripts/run_chart_regression.py --freeze .ai-audits/chart-confidence/freeze.json \
  --output .ai-audits/chart-confidence/final-regression-01
```

The destination must be new and under ignored `.ai-audits/`. Preflight verifies
the freeze, canonical `seasons/1983-generated`/`seasons/2024` fingerprints and
contracts, both current source-preparation receipts, and public/local AI inputs.
It refuses occupied review ports 8000/5173; follow the charter's parent-notification
and service-restoration procedure before the isolated browser run. It does not
stop services itself. The collector runs all twelve commands, records actual
argument lists, locations, status and stdout/stderr, and preserves failures while
continuing independent checks. It captures and hashes the five produced AI/chart
JSON/CSV artifacts; absent or unrefreshed artifacts fail rather than reusing old
evidence. It validates the logs against the unchanged freeze and independently
checks the actual outputs. `evidence.json`, `outputs.json` and `result.json`
retain the execution records, output bindings and both validation results.

`audit_regression_outputs(root, freeze, evidence)` checks schema-1 output evidence
with `schema_version`, `freeze_sha256`, `artifacts`, `ai_inputs` and
`source_receipts`. All five artifacts require `{path, sha256, original_path}`
bindings to the fixed commands' destinations. Source receipts require
`{path, sha256}` bindings to the standard preparation locations. AI input
fingerprints bind the actual public 2026 and local 1983 charts; private hashes
and reports stay in ignored storage. Both complete seed-8306, sixteen-week
Hard/balanced schedules must reconcile with their game receipts and current
Python version. Rebuild call totals, situation shares/streaks, warnings and
semantic coverage from the recorded calls; compare every local CSV row with
the JSON summary. Concentration remains advisory. For each chart report, require
the declared training policy/master, revalidate its source receipt, and rerun
the existing source/tactics/allocation/engine gate against its actual embedded
engine report and frozen contract. Contradictory stored component results fail.
Recheck outputs, source receipts, AI inputs and the freeze afterward.

The APIs and collector validate trusted local evidence consistency and do not
attest a hostile host. The legacy AI format records selected calls and legal
final-state flags, without complete box scores or loaded runtime identity;
actual execution and deterministic engine controls remain necessary. Complete
charter readiness remains separate. Results always retain
`release_certified: false`; collecting evidence is not final owner acceptance.

Collect the separate public unit snapshot with Git available:

```sh
python3 scripts/run_chart_public_snapshot.py --freeze .ai-audits/chart-confidence/freeze.json \
  --output .ai-audits/chart-confidence/final-public-units-01
```

The destination must be new and under ignored `.ai-audits/`. The collector checks
the freeze and canonical candidate fingerprints, then copies tracked and new
unignored working-tree files, including intended dirty changes. It rejects
symlinks and nonpublic season files; ignored historical data and Git metadata
are not copied. It runs `npm ci` and the complete core/backend/frontend unit
suites in that copy, with `PYTHONPATH` set to its root and user site imports
disabled. Dependency or command failures remain failures. All four execution
logs retain actual arguments, location, status, output and the isolated Python
path; warnings/skips, npm `warn` lines and dependency-audit summaries remain visible. Review services are not needed or changed.

`audit_public_snapshot(root, freeze, evidence)` independently validates this
schema-1 evidence: `schema_version`, `freeze_sha256`, `snapshot_dir`, the complete
`files` SHA-256 map and four `commands` log bindings. The snapshot must contain
exact intended public bytes and frozen candidates. Only generated test caches,
coverage artifacts and installed npm dependencies are excluded from its final
source inventory. Source, snapshot, freeze and log changes invalidate the result.
This is a public-unit evidence component, separate from the twelve-command full
regression and the complete readiness decision. Both retain noncertification.

## Required checks

- **Source consistency:** manifest arithmetic, source-derived counts and rates,
  reviewed profile, full CSV fingerprint inventory, schedule and team membership.
  Known classified-versus-official count discrepancies fail unless a reviewed
  reconciliation explains the exclusions. Saved normalized inputs and complete
  regeneration can also be checked with `scripts/audit_generated_sources.py`.
- **Weighted tactics:** every team's formations are combined with controlled
  offensive inputs through real priority and supplemental resolution, using
  physical dice probability. Declared formation benefits and costs are checked
  separately from exploratory directions. Stateful engine controls cross-check
  those resolver distributions. Unknown penalties/recoveries are explicit branches.
- **Exact mechanics:** every team and all 54 primary call/defense pairs use
  physical offense and defense mass, conditioned on B/QT supplemental outcomes.
  The report includes recovery probabilities, numeric gain tails and special
  column distributions, plus raw distance-dependent field-goal curves. Pending
  state, penalty, recovery and return effects stay explicit. Conditional known
  numeric means are not whole-play YPA. Generated B/QT and special columns must
  use symbols supported in their particular engine lookup; legacy random
  secondary fallback is measured for diagnosis and rejected for generation.
  Empirical manifests also disclose symbolic variants omitted by finite row
  allocation. Their inputs are modeled column populations, not raw event counts;
  a rare variant is never assigned extra mass merely to make it appear.
- **Allocation:** synthetic mixed-rate contexts must preserve protected results
  and choose the nearest attainable final event mass. An independent physical-row
  oracle checks the generator rather than calling its selector as its own proof.
- **Full engine:** all scheduled games must finish, totals must reconcile, and
  five source metrics must meet predeclared tolerances under the explicit
  chart-focused policy: completion, interception and sack rates, passing yards per
  attempt and rushing yards per attempt. Source targets and tolerances live in
  the reviewed contracts, separate from observed results.

The fixed policy controls normal play mix while retaining legal clock/endgame
decisions. It is a measurement policy, not recovered historical coaching. Hard
AI, situational play, scoring, pace and rare events need additional assessment.
Passing the gate would not establish historical tactical accuracy or validate
missing source annotations. The [audit findings](dev-notes/generated-chart-release-audit.md)
record current limitations and blockers; do not widen tolerances to hide them.

## Prove rejection before changing a check

Synthetic regressions require rejection of the repeated-pattern defect even
when CSV arrangements differ but weighted outcome distributions coincide. Other
negative controls cover lost event types, non-nearest allocations, mismatched
source facts, stale engine reports, missing samples and a failed component being
ignored by the combined gate. Unit fixtures use only synthetic or public 2026
teams. Promoted historical generated cohorts are exercised by the standalone
gate, outside unit-test collection.

When a gate fails, investigate and record the discrepancy in the developer
tracker. Generator, source or engine fixes need failing behavior regressions
before production changes, followed by fresh gate evidence. Review the resolved
tracker inventory after play/audit checks; unit tests alone cannot close an issue
that requires play-test confirmation.

## Saved browser-capture consistency

The existing gate can validate saved local preview captures against a frozen implementation and both public candidates:

```sh
python3 scripts/audit_generated_charts.py --visual-capture .ai-audits/visual/evidence.json --freeze .ai-audits/visual/freeze.json --output .ai-audits/visual-result.json
```

The result path must be new, under ignored `.ai-audits/`, and outside candidate/source directories. This mode starts no games or browser. It checks actual bound receipt/state/PNG files, all thirty ordered rows in every chart table, viewport fit without internal scrolling or overlapping offense/auxiliary tables, consistent local game/side URLs, browser errors, and unchanged state. It rechecks artifacts and the freeze after validation.

A pass establishes capture consistency only. The result keeps `release_certified=false`, `selection_validated=false` and `candidate_content_validated=false`. Add the content evidence below to check candidate/API/DOM correspondence. The charter's worst-outlier and strong/weak selection and independent visual review remain required. The [readiness bundle design](dev-notes/chart-readiness-bundle-design.md#bound-visual-capture-component) describes receipt fields and remaining scope. Historical captures cannot be relabeled as current evidence.

To compare every selected candidate table with the actual API and DOM observations, add `--visual-content`:

```sh
python3 scripts/audit_generated_charts.py --visual-capture .ai-audits/visual/evidence.json --visual-content .ai-audits/visual/content.json --freeze .ai-audits/visual/freeze.json --output .ai-audits/visual-content-result.json
```

The content manifest binds the exact capture manifest, all API book files and one DOM observation per view. The gate independently loads each frozen candidate and checks all four tables, call order/numbers/groups, defense rows, B/QT/fumble ranges, extra points and raw cell labels. It also compares DOM headings/captions, columns, row order, cell labels and API palette classes, then rechecks captures and every bound file. Successful correspondence sets `candidate_content_validated=true`; release and charter-selection certification remain false. Palette-class correspondence does not prove rendered pixel colors, historical accuracy or human approval.

Run the maintained collector to create fresh evidence in a separate public source copy:

```sh
python3 scripts/run_chart_preview.py --freeze .ai-audits/visual/freeze.json --selection .ai-audits/visual/selection.json --output .ai-audits/chart-previews/run-01
```

The selection is a schema-1 JSON object with `freeze_sha256` (the canonical freeze digest) and a nonempty `contexts` list. Each context has exactly `cohort`, `team`, `opponent` and `side` (`home` or `away`); both cohorts must appear, teams must exist in their frozen contracts and candidate directories, and each selected cohort/team appears once. This explicit list does not establish the charter's representative-selection criteria.

Install the backend requirements in the interpreter passed through `--backend-python`, and install Playwright Chromium as described in the [browser testing guide](../paydirt-web/frontend/e2e/README.md). The collector runs `npm ci` in its fresh frontend copy, launches owned services on ports 8004 and 5177 by default, and retains setup/browser logs including warnings. Override ports with `--backend-port` and `--frontend-port`; occupied ports and owner ports 8000/5173 fail preflight. It forwards only expected chart GETs to its isolated backend while preserving the frozen frontend source. It creates and deletes only its preview games, checks unchanged state, captures all three views and the offense auxiliary table, validates candidate/API/DOM correspondence, then stops its services. The output retains source copies, before/after loaded-runtime receipts, capture/content manifests and `result.json`. Screenshots remain available after services stop; these URLs are capture identities, not persistent owner-review links. Recheck the freeze after every implementation change. This component does not replace full-game browser regression, source reconciliation, charter selection or owner review.

Expected aborted chart fetches from the existing React cleanup are retained in `browser-result.json` as `canceled_chart_requests`; only exact chart GETs for the selected game/side qualify. Other network/browser errors fail. Complete rendered DOM and state evidence remain mandatory. Run the collector's isolated request-policy regressions with `node --test paydirt-web/frontend/e2e/collect-chart-preview.test.cjs`; they require only Node, and are separate from the full-game Playwright command.

## Charter preview-selection consistency

Add bound selection evidence to the saved-capture/content command:

```sh
python3 scripts/audit_generated_charts.py --visual-capture .ai-audits/visual/captures.json --visual-content .ai-audits/visual/content.json --visual-selection .ai-audits/visual/selection-evidence.json --freeze .ai-audits/visual/freeze.json --output .ai-audits/visual-selection-result.json
```

The selection-evidence object has exactly `schema_version: 1`, `freeze_sha256`, `captures_sha256`, `content_sha256` and `cohorts`. The three digests use canonical sorted compact JSON, as returned by `readiness_freeze_fingerprint`. Cohorts are exactly `1983-generated` and `2024`; each contains exactly `training` and `held_out`, both explicit `{path, sha256}` references to actual reports under ignored `.ai-audits/`. These references bind file bytes; they do not assert that a report passes.

The existing engine validator checks each report against its frozen candidate and contract, requiring the chart-focused policy, complete current evidence, 64 source schedules, at least 1,000 team-games, fixed league/team fit bounds and the charter masters 20261108/20361108. The selection component derives each cohort's worst normalized team/metric error across both families. It also chooses strong/weak source-offense representatives from the sum of average tied ranks for source passing and rushing yards per attempt. That explicit efficiency proxy selects a review sample; it does not establish standings or overall team quality. Exact outlier ties use team folder, training before held-out, then metric; source-score ties use folder. Indistinguishable source scores fail rather than inventing a contrast. Dolphins 1983 is mandatory, and overlapping roles can share one captured context.

Every required team must have complete validated chart captures and content. The result retains the source values, ranks, normalized errors and underlying campaign validations, then rechecks manifests, actual report files (including symlink replacement) and visual artifacts. A successful component sets `selection_validated=true` while keeping `source_accepted=false`, `ready_for_owner_review=false` and `release_certified=false`. Source reconciliation, the complete campaign census, independent reference/transfer review, full regression, persistent preview URLs and owner review remain separate. Implementing this validator does not authorize opening held-out outcomes before the announced final freeze.

## Local reference-corpus preflight

The private benchmark begins only after stable source and training evidence passes:

```sh
python3 scripts/audit_generated_charts.py --reference-corpus .ai-audits/chart-reference-comparison/declaration.json --freeze .ai-audits/readiness/freeze.json --output .ai-audits/chart-reference-comparison/census-result.json
```

The command starts no games. It revalidates the unchanged freeze, both prepared-source receipts and both complete chart-focused training reports (master 20261108, 64 schedules and at least 1,000 team-games), including fixed source/mechanics/allocation/fit checks. Any failed dependency prevents reading reference bytes. A previous PASS label cannot replace these independent checks. This preflight does not authorize opening private comparisons before the [stable-checkpoint protocol](dev-notes/chart-reference-comparison-protocol.md).

The strict schema-1 declaration has exactly `schema_version`, `freeze_sha256`, `source_receipts`, `training` and `corpus`. The digest uses canonical sorted compact JSON. Both report maps have exactly `1983-generated` and `2024`, each an actual `{path, sha256}` file reference under ignored `.ai-audits/`. The corpus contains exactly `directory` (a canonical root-relative local directory), `files` (every recursive file's relative path and SHA-256), `partition_method: "sha256-folder-order-alternating-v1"` and `teams`. Every frozen 1983 generated folder maps to exactly one reference folder via `{reference_folder, partition, inspected_before_freeze, prior_use}`; the last field is a nonempty account of earlier inspection.

Sort SHA-256 values of UTF-8 `paydirt-reference-partition-v1:` plus each generated folder name, with folder names breaking digest ties. Alternating entries begin with `development`, then `withheld`, giving fourteen teams each. Declare this before inspecting comparisons. Previously inspected withheld teams force the result's retrospective classification; a declaration cannot prove non-observation.

The census rejects missing/extra team folders, omitted/changed files, symlinks, incomplete charts, unreadable or unnamed metadata, differing source-year rules and decoder failures. It retains known defaults/fallbacks, loader warnings, unconsumed files and prior-use declarations. Files, directories, dependencies and manifest digests are checked again after processing. The CLI requires a new output under ignored `.ai-audits/chart-reference-comparison/`, protects corpus/source/candidate inputs and fails changed declaration/freeze files. Reference-derived reports and hashes stay private and local.

A successful census sets only `corpus_validated=true`. It keeps `benchmark_complete=false`, `source_accepted=false`, `ready_for_owner_review=false` and `release_certified=false`. Full weighted/crossed comparisons, 64 paired reference campaigns, material-outlier review, prospective transfer and independent review remain required. The component's synthetic/public tests do not establish that the real private corpus was inspected or that the candidate is stable.


## Exact weighted reference diagnostics

Add `--reference-weighted` to the reference-corpus command to compute exact pre-state diagnostics after the full preflight passes. The same declaration, freeze and new private output restrictions apply. The gate repeats the complete corpus/source/training/freeze preflight after comparison, including when a comparison fails. Changed inputs invalidate the result.

For each of the 28 mapped teams, the report retains R/R, G/R, R/G and G/G (reference/generated offense and defense) for all nine calls and six formations. Each opposing cohort is a uniform mixture of all 28 defenses, including the named team's own defense. This is exploratory conditioning, separate from source-schedule fit and stateful crossed games. Physical dice masses and core priority/secondary resolution determine the distributions; rearranging equal-mass cells preserves them, while unequal-mass changes and altered gain/OOB correlation remain visible.

The component reports reduced exact fractions for signed changes, total variation, four-combination interaction, secondary triggers/fallbacks, conditional known numeric yields/tails, recovery, EP misses, special lookup tokens and distance-dependent numeric FG coverage. Penalties, field-dependent touchdowns, recovery advances and other stateful branches stay explicitly pending. Numeric yield is conditional on resolved branches; it is not whole-play YPA. Special returns are conditional on their lookup, and the numeric FG curve precedes penalties, blocks, fumbles and re-kicks. Decoder preflight rejects signed defensive F forms because the core priority table only supports bare defensive F.

`weighted_validated=true` means the bound diagnostic was computed and reconciled. `behavior_matches_reference` is an exact equality observation, with no universal agreement threshold or historical-accuracy implication. Source accuracy, stateful crossed scenarios, paired campaigns, material-outlier review, transfer and independent/owner review remain required; `benchmark_complete`, `source_accepted`, `ready_for_owner_review` and `release_certified` remain false.

Missing and explicit-blank B/QT cells retain the same core uniform fallback distribution and exact fallback mass. They are decoder limitations, not observed historical gains or certain zero-yard plays.


## Stateful crossed reference contexts

Use `--reference-contexts` with the same `--reference-corpus`, `--freeze` and new private `--output` arguments. It is mutually exclusive with `--reference-weighted`. Both complete source/training preflights must pass before charts are loaded, and the entire preflight runs again after collection, including a failed collection. Changed declarations, files or dependencies invalidate the result.

The fixed census uses every ordered pair of distinct mapped teams, all nine primary calls and six formations, and six contexts: own 1, own 40 and opponent 2, each on first down (ten yards or goal to go) and fourth-and-one. Each trial repeats one call/formation for at most four calls, stopping at an engine-confirmed score, possession change or game end. All four R/R, G/R, R/G and G/G combinations receive the same initial seed. Seeds use SHA-256 of the versioned domain `paydirt-reference-context-v1`, training master 20261108 and the team/opponent/context/call/formation identifiers. Later RNG paths can diverge; caller RNG state is restored. The full 28-team census is 979,776 trials, with at most 3,919,104 selected calls.

The authoritative engine handles field clipping, first downs, turnovers, recovery/return credit, penalties and scoring under the chart's source-year rules and unmodified yardage factors. Pending penalties use the existing balanced, chart-blind chooser. Scores stop before conversions/kickoffs. Receipts reconcile selected and official calls, box-score yardage/turnovers, scoring logs and legal final state. Failures retain their seed and full context while collection continues for the remaining teams.

Reports retain trial/call denominators, sequence lengths, terminations, primary/secondary/tail observations, canonical receipt digests, empirical metric fractions, offense/defense/joint/interaction deltas, formation contrasts against A and strength rankings. These fractions describe this fixed sampled grid; they are not exact physical probabilities, full-game estimates or historical targets. A four-call probe cannot by itself rule out repeated-call exploits. Review concentrations, material outliers and source fit separately; no universal reference-agreement bound is imposed.

`contexts_validated=true` means the complete bound diagnostic census reconciled. `stateful_crossed_complete`, `benchmark_complete`, `source_accepted`, `ready_for_owner_review` and `release_certified` stay false pending the remaining reviewed evidence. This diagnostic uses no reserved comparison outcomes; the separate 64-repetition paired full-game comparison still requires master 20461108. Synthetic/public component tests do not establish that the actual private corpus was read.


## Paired reference full-game reports

After the stable checkpoint and complete reference collection, validate the two saved raw engine reports with:

```sh
python3 scripts/audit_generated_charts.py --reference-corpus .ai-audits/chart-reference-comparison/declaration.json --freeze .ai-audits/readiness/freeze.json --reference-paired .ai-audits/chart-reference-comparison/paired-declaration.json --output .ai-audits/chart-reference-comparison/paired-result.json
```

This command starts no games and cannot be combined with weighted/context component flags or cohort execution options. The strict paired declaration has exactly `schema_version: 1`, `freeze_sha256`, `reference_declaration_sha256`, `generated` and `reference`. The first two digests bind canonical sorted compact JSON of the freeze and reference declaration. Each report field is an exact `{path, sha256}` reference under ignored `.ai-audits/chart-reference-comparison/`. Original declaration bytes and every report digest are rechecked after processing. Outputs must be new canonical private files and cannot overwrite any input.

Both complete source/training/corpus preflights must pass before paired reports are read, and the full preflight repeats after successful or failed comparison. The main comparison requires master 20461108, the existing `master + repetition_index * 1000003 + game_index * 1009` derivation, the chart-focused normal policy, at least 64 complete source schedules per set and at least 1,000 appearances per mapped team. Every generated-folder/reference-folder pair uses the same actual schedule and initial game seeds under matching source-year rules. Later dice, calls and game paths may diverge. Team identifiers must match the actual loaded charts. No game or failed set is silently omitted.

The shared engine-report validator reconciles all raw receipts, official calls, replications, loaded runtime and chart fingerprints. It checks every derived rate from authoritative raw totals, including points/team-game, plays/team-game, fumble loss/play and field-goal rate. Both cohorts retain source-fit verdicts under unchanged league/team bounds. A source-fit failure stays visible even when mechanically valid paired diagnostics can be computed; agreement with the reference cannot grant source accuracy.

Reports distinguish aggregate metric deltas from the mean of paired repetition deltas. Standard error uses differences between independent source-schedule repetitions; individual plays are not independent samples. A one-repetition training diagnostic has no estimated standard error and cannot satisfy the main gate. Mapped game-pair seeds, score differences, complete exposures, policy-conditioned strength rankings, call/repetition summaries and retained-primary tail denominators support separate outlier review.

A successful CLI result sets only `paired_validated=true` and its corpus consistency verdict. `benchmark_complete`, `source_accepted`, `ready_for_owner_review` and `release_certified` remain false. Full weighted/stateful evidence, material-outlier/exploit adjudication, source fit, seed-use/announcement history, prospective transfer and independent/owner review remain required. Unit fixtures and scaled public gate stubs do not prove actual private or reserved campaigns ran.

## Corrected public release outputs

The maintained `seasons/1983-generated` and `seasons/2024` directories contain the
corrected reviewed CSV output. Their public release manifests bind every chart
hash, the original private generation-manifest hash and local reproduction-proof
hash. They are deliberately sanitized summaries, not portable raw-source manifests.
Team metadata and rosters are retained; raw source and private event reviews stay
local. CI validates these committed outputs without private hosting.

The 1983 model fits 712 of 727 retained fumble events; 15 are uniformly excluded
from fitting only (2.063%). Factual source completeness remains false. Its
unchanged completion-rate tolerance of 0.03 has two exceptions: 49ers 0.610006
versus 0.642045, Falcons 0.601726 versus 0.633136. The 2024 Ravens rushing
YPA absolute error is 0.417273 versus the unchanged 0.4 tolerance. These are
explicit release limitations, not waived measurements or passing fit assertions.

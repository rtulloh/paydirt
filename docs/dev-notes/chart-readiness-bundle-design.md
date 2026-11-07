# Charter readiness evidence bundle design

Development design under the [chart-confidence charter](chart-confidence-agent-charter.md).
This extends `chart_release_gate.py`; it is not a competing gate or a statement
that the current candidate passes. Release remains held.

## Campaign census

Before final readiness, require both complete cohorts (28 teams/1983 and 32/2024),
with training, held-out, Hard, legacy balanced, run-heavy and pass-heavy reports.
Also require nine normal-context repeated-call policies, one per primary call;
there are fifteen report families per cohort, thirty in total.
Pass every report through the existing current-engine validator. Training and
held-out require 64 independent source schedules, at least 1,000 team-games each,
the fixed chart-focused policy and all existing league/team fit limits. Hard and
balanced require eight schedules/128 team-games, and each family/repeated-call
stress requires one schedule/16 team-games. Nonreference policies require accounting, mechanics and
completion, without imposing reference-policy historical averages.

Training must identify master 20261108 and held-out 20361108. A report with the
wrong phase seed, missing or substituted policy, incomplete cohort, stale runtime,
failed team, missing family or contradictory success/errors cannot pass. Delegate
actual game/count/fingerprint checks to the existing validator rather than
reimplementing them. Preserve all campaign failures and inspect other evidence
even if one campaign raises. The campaign census is a component: it always
retains release_certified=false and cannot substitute for the remainder below.

## Complete readiness, still to integrate

The eventual single CLI bundle mode must load actual files with bound hashes,
then require source bytes/stats/reproduction and exact mechanics/allocation for
both cohorts, the campaign census above, a frozen input/code/policy/threshold
inventory, the full private 28-team benchmark, prospective source-only 2023
transfer, the whole AGENTS regression and clean public snapshot, a compact local
visual packet, and the parent's independent review. A self-declared PASS label
does not replace the underlying validation or a human review record.

Private reference artifacts stay in ignored local storage. Reference comparison
is not a historical truth threshold; validate inventory, declared partitions and
prior use, decoder coverage, weighted/crossed contexts, complete paired campaigns
and reviewed material outliers under the existing protocol. Transfer requires
the frozen reusable procedure and the reserved 20561108 family; no manual changes
based on transfer outcomes. Opening/retiring a reserved family must be recorded.

Regression receipts must bind the concrete commands, candidate snapshot,
exit codes and actual log/report hashes, disclose skips/warnings, and reject a
changed implementation or omitted required command. This is trusted local
evidence consistency, not hostile-host attestation. A final ready-for-owner-review
verdict must keep the separate publication/release decision explicit.

The campaign census, bound campaign files, freeze, source preparation, regression
logs/outputs and public snapshot components are implemented below. Complete
orchestration, benchmark/transfer/visual/review validation and approved remote
source distribution remain required; they cannot be silently treated as completed.

## Bound campaign-file slice

The next component accepts a schema-1 JSON bundle with both cohort entries. Each
entry names its candidate directory and current chart fingerprint, plus contract,
training, held-out and policy reports as explicit `{path, sha256}` objects. Paths
resolve relative to the bundle. Read actual bytes, verify each digest before
parsing, reject duplicate JSON keys/nonfinite values and retain binding failures
alongside census failures. Reject extra/missing cohort or policy identities rather
than silently treating an unrelated file as the required report. Changed candidate
bytes fail against the declared chart fingerprint. Delegate report semantics and
current runtime checks to the existing census/engine validator.

This slice loads only campaign evidence; source reproduction, complete freeze,
reference/transfer/regression/visual and independent review remain separate.
Both in-memory and file entry points must keep `release_certified=false`.
Artifact hashes establish trusted local consistency, not author identity or proof
that an arbitrary contract's targets are authoritative. The eventual full bundle
must still reconcile contracts against reviewed sources and frozen thresholds.

The regression execution-log component is also implemented in the existing gate.
It checks all twelve exact AGENTS command/working-directory identities against
actual strict-JSON execution logs, binds their hashes to an unchanged freeze,
retains skip/warning lines, and rejects failed, missing or changed evidence.
The API starts no processes and always retains noncertification. A maintained
`scripts/run_chart_regression.py` collector now executes the complete fixed list,
retains actual logs/statuses and copies/hashes produced artifacts. It checks
canonical chart fingerprints and refuses occupied review services, stale freezes,
existing destinations and unrefreshed artifacts. The collector has only been
exercised with synthetic execution at this development stage; the final actual
regression has not run. Its output component now independently checks actual
AI/CSV/chart artifacts, as described below. The rest of the complete readiness
bundle remains required.

`audit_regression_outputs` binds the five actual command outputs, both source
receipts and public/local AI chart fingerprints to the same freeze. It independently
rebuilds both complete seeded AI schedules and their call/situation/semantic
summaries, preserves advisory concentration warnings and reconciles every local
CSV row. Each chart output is checked through the existing source-preparation
reader and actual source/tactics/allocation/engine validators; stored component
labels cannot substitute for that recheck. Final bytes, inputs and the freeze are
checked again. The collector retains separate `outputs.json` evidence and rejects
an exit-zero command that emits empty, stale, truncated or contradictory output.
This validates trusted local consistency. The legacy AI format has selected calls
and legal final flags, without complete box scores or loaded runtime identity;
actual command execution and deterministic engine controls remain necessary.
This component never certifies readiness or starts games.

The public snapshot API and maintained `scripts/run_chart_public_snapshot.py`
collector are also implemented. Git discovers intended tracked and new unignored
working-tree bytes, preserving dirty changes while excluding ignored historical
inputs. The collector requires the unchanged freeze and matching canonical
candidates, copies only that public inventory, then runs npm dependency setup
and all three complete unit suites with the copy as the isolated Python path.
The API independently inspects every snapshot source file, rejects private season
directories and changed/missing/extra bytes, and checks actual bound execution
logs and implementation/candidate fingerprints again. Generated caches, coverage
and npm dependencies are excluded explicitly. This component remains
noncertifying. Synthetic execution tests cover failed/missing tools, source/copy/
freeze mutations and preflight preservation; an actual final-candidate run is
still required.

## Frozen implementation and input component

The next independent slice validates a schema-1 freeze inventory against actual
local bytes. Its implementation inventory covers the core, generators, scripts,
tests, backend, frontend source/browser tests/configuration/dependency locks,
workflow files, public validation contracts, AGENTS and the charter/reference
protocol. Discover this inventory independently; an omitted or newly added code
file must invalidate an earlier freeze. Ignore dependency/cache directories and
historical season data. Required implementation anchors prevent an empty or
incomplete repository from passing merely because its declared inventory is empty.

Bind both candidate directories, their chart/rule/metadata/profile fingerprints,
their contracts, and every generation-manifest input label to actual source bytes.
Reject omitted/substituted labels and mismatched manifest/source hashes. Check
loaded runtime and files again at completion to detect changes during validation.
Register the charter's unopened held-out/reference/transfer master families.
This registration is a local declaration, not proof of non-observation; the
parent's dated freeze announcement and later seed-use history remain necessary.

This component establishes consistency only. It does not establish upstream
truth, run campaigns, open reserved inputs, validate the private benchmark or
transfer, or certify readiness. The eventual bundle must bind this freeze before
those acceptance observations and independently validate every other component.

## Source staging still required

The checklist cohort invocations supply no raw/statistics/reproduction paths;
they require a current source-preparation receipt at the documented default
location. CI now stages and prepares those inputs first, but approved remote
distribution and repository variable configuration remain outstanding. Missing
or stale source bindings correctly fail before simulation. Do not restore a
metadata-only pass or add `--engine-only` to those release jobs.
Existing local generation helpers are not a portable CI acquisition procedure:
they rely on cached public HTML, normalized aggregate JSON and reviewed event
reconciliation evidence. Re-downloading arbitrary current pages cannot substitute
for the exact reviewed bytes or silently update declared hashes.

At the stable candidate, prepare a local, public-source-only input bundle with a
complete hash inventory, provenance and the exact generation recipe, then verify
extraction, all inputs and independent regeneration in an isolated environment.
Exclude original developer charts, private reference artifacts, narrative logs
and user data. A portable copy of reconciliation facts must retain evidence-byte
bindings without depending on this machine's absolute paths. CI must obtain that
same approved bundle, verify its pinned digest/inventory, regenerate independently,
and pass explicit actual-input/statistics/reproduction paths to the existing gate.
An unavailable or changed bundle is a failure, not a skip or permission to fall
back to manifest assertions.

Local assembly/validation is authorized; uploading a source bundle, configuring
remote distribution or publishing it is a separate owner decision. No upload or
remote configuration has occurred. The final handoff must make this staging and
publication boundary concrete, and must not claim a working source-backed CI
gate before its approved inputs can actually be obtained.

An earlier ignored portability prototype reproduced all 180 CSVs, both complete
manifests and both chart fingerprints from relocated public inputs in a code
snapshot without season/original-source directories. Reviewed reconciliation
evidence uses relative paths and retains its original bytes. This establishes
portability feasibility at that checkpoint, not current source acceptance.
The later ownership guards now reject four unsupported 2024 compound-fumble
sequences before fitting; only the 1983 candidate currently reproduces. The
[compound-event investigation](compound-fumble-source-reconciliation.md) records
the unresolved projection. Historical prototype passes cannot supersede this
source failure. The maintained staging tool is described below.

The maintained local preparation tool should accept one cohort bundle directory,
its actual candidate directory and a new reproduction destination. Schema 1 binds
an exact file inventory, a recipe naming only one of the two existing generator
scripts, all explicit generation arguments, declared input/CSV hashes, and the
source contract. Reject changed/missing/extra files, duplicate/nonfinite JSON,
unbound input labels, output paths inside inputs/candidate, existing output/log
paths, arbitrary scripts, unknown/duplicate flags and output-argument overrides.
Input arguments resolve within the bundle; only explicit output/audit placeholders
may name new external destinations. Validate actual candidate/manifest/contract
bindings before execution. Run the existing generator, retain its actual log and
status, and require identical CSVs, manifest, rules and metadata afterward.
Recheck inputs, candidate, both generator entry points, all Python source adapters and loaded runtime for changes during
preparation. A structured result supplies actual source/statistics/reproduction
paths to the existing gate and always retains noncertification. Unit tests use
synthetic/public fixtures; the real all-60-team portability check remains an
explicit ignored integration artifact.

This local preparation API and `scripts/prepare_chart_sources.py` are now
implemented. Successful receipts can be revalidated by `prepared_source_options`;
the cohort CLI discovers the standard `.ai-audits/chart-sources/SEASON/source.json`
only when all explicit source flags are absent. Discovery verifies actual source
inventory, contract, candidate/reproduction, generation-code/runtime, command,
status and log bindings before games. The source gate still independently checks
facts and mechanics. Its output guard harvests protected paths before semantic
validation so a failed receipt cannot cause evidence overwrites. Deterministic
archive packaging and digest/inventory-checked staging are implemented locally.
The two CI workflow definitions require approved per-cohort URL/SHA repository
variables, stage those pinned inputs and independently regenerate before the gate.
Missing approval bindings fail before download; there is no metadata fallback.
Approved distribution/configuration and actual remote validation remain required;
no remote bundle is published or repository variable changed.

## Bound visual-capture component

The next noncertifying slice validates trusted local browser-capture receipts against an unchanged freeze. Each selected public-contract team has three views (offense, defense, special teams); offense also includes the auxiliary special-plays table. Bind actual receipt, before/after state JSON and PNG bytes under ignored `.ai-audits/`. Require exact ordered thirty-row identities, finite viewport/layout measurements without clipping or internal overflow, local preview URLs with consistent game/side identity, successful HTTP status and no browser errors. Check screenshot viewport dimensions and all artifact/freeze hashes again at completion. Retain failures from every context.

This component deliberately leaves `selection_validated=false` and `candidate_content_validated=false`: it does not select the charter's worst outliers/strong and weak representatives, compare API/DOM cell contents to loaded candidate charts, prove browser execution on a hostile host, or replace independent visual review. Those checks and a maintained actual capture collector remain required before the complete visual packet can pass. Synthetic fixtures establish validator behavior only; no historical preview becomes current evidence by adopting this schema.

The capture API is now `audit_visual_capture_evidence(root, freeze, evidence)` in the existing gate. Schema 1 has exact `schema_version`, `freeze_sha256`, and `contexts` fields. Every context is `{cohort, team, capture: {path, sha256}}`; receipts retain the same freeze/runtime/chart identities, viewport, browser errors, before/after state bindings and three section records. Sections retain local URL, HTTP status, PNG binding and measured tables. The validator checks PNG chunk checksums, RGB/RGBA dimensions, termination and decompressed scanline lengths, then rechecks every file and the freeze. This is implemented capture consistency only; the selection/content and independent-review requirements above remain open.

Capture state must also identify the URL's game and selected home/away team's exact public-contract `id`; equality of two unrelated state files is insufficient. The auxiliary and main offense rectangles must not overlap. These identity/geometry checks still do not establish candidate cell contents or reviewed team selection.

## Candidate/API/DOM content component

`audit_visual_content_evidence(root, freeze, captures, evidence)` now binds a schema-1 content manifest to the canonical capture-manifest digest and the same freeze. It independently loads each selected frozen candidate and compares the API's four complete tables, including call order/number/group, defense formation/subrow, B/QT/fumble ranges, extra points and raw labels. It then compares actual DOM observations (heading, captions, columns, call numbers/groups, ordered row identities, raw cell labels and API palette classes) for every captured view, with the same URL identity. All actual bytes and complete capture evidence are checked again at completion. Failures are retained per context; release noncertification and unvalidated charter selection remain explicit. Colors are checked for API/DOM correspondence; source-driven statistical correctness, pixel appearance and human approval remain separate. A maintained real-browser collector and final current-freeze evidence remain required.

The exact manifest fields are `schema_version`, `freeze_sha256`, `captures_sha256`, and `contexts`. Each context has `cohort`, `team`, bound `api_book`, and `views` bindings for offense, defense and special teams. Each strict-JSON DOM observation retains its actual URL, heading and complete table observations: caption, displayed column names/numbers/groups, ordered row keys, raw cell labels and palette classes. The offense view includes auxiliary special plays. The helper in `chart_preview_audit.py` imports only the core chart model and standard library; root unit tests need no backend/Pydantic dependency. The existing CLI accepts `--visual-content` with its capture/freeze options and invalidates the content-validation flag if an input manifest changes after comparison.

## Maintained isolated preview collector

Implemented by `scripts/run_chart_preview.py`, its isolated backend bootstrap and `frontend/e2e/collect-chart-preview.cjs`. The collector copies intended public implementation bytes and independently bound frozen candidate overlays into a new ignored directory, installs the frozen frontend lockfile, launches and stops only its own loopback services, retains actual execution logs and backend loaded-runtime receipts, and creates display-only games for selected public-contract teams. All original season trees are excluded from the source copy; only frozen generated candidates are overlaid, with the 1983 public candidate served under the API's numeric season alias. The frozen hardcoded frontend API source stays intact: Playwright explicitly forwards only expected chart GETs to the isolated backend. Actual API/state/PNG/DOM bytes use the existing gate schemas; complete capture/content evidence is checked before and after shutdown alongside root files, source/copy candidates, freeze/selection files and backend identity. Expected canceled chart fetches are retained separately; other browser errors and unexpected requests fail. Invalid preflights start nothing and preserve inputs. This collector cannot certify charter representative selection, source acceptance, complete browser games or release readiness. See the [maintained command](../chart-validation.md#saved-browser-capture-consistency).

## Bound charter preview selection

Implemented as `audit_visual_selection_evidence` in the existing gate, with `--visual-selection` on the saved-visual CLI. A schema-1 selection-evidence object binds the canonical freeze, capture and content manifest digests, plus exactly training/held-out report references for both cohorts. Reports use canonical ignored local paths and actual SHA-256 bytes. Complete current-engine accounting, policy, 64-schedule/1,000-team-game samples and fixed league/team fit checks delegate to the existing validator; the charter's exact training and held-out masters are required. No reserved family was opened to implement or test this component.

Derive each cohort's worst outlier from the largest absolute error divided by the existing fixed team tolerance across all five metrics and both reference-policy families. Break exact ties by team folder, phase (training before held-out), then metric name. Derive strong/weak source-offense representatives by the sum of ascending average tied ranks for source passing and rushing yards per attempt; take the highest/lowest sum, breaking ties by folder. This transparent efficiency proxy is a compact review-selection rule, not standings, overall team quality or a new historical acceptance threshold. Require actual source contrast; identical rank scores cannot establish strong/weak coverage. Always include Dolphins from the 1983 cohort. Combine overlapping roles, retain every role's underlying values and reject omitted required contexts.

The component reuses complete capture/content validation and rechecks all bound campaign artifacts, manifest digests and the freeze after processing. Nested failure/contradictory labels and malformed values fail; one cohort's exception must not suppress the other's evidence. A consistent selection may set only `selection_validated=true`; source acceptance, full readiness and release remain false. Full campaign census, independent reference/transfer evidence, owner review and persistent preview URLs remain separate requirements. Synthetic tests use generated fixtures only; no real held-out output is created or read during implementation.

## Reference corpus preflight design

Implemented as `audit_reference_corpus_evidence` and `--reference-corpus` in the existing gate/CLI. This component validates the declared normalized local reference corpus before any weighted/crossed/paired comparison. It first revalidates the complete freeze, both actual prepared-source receipts and both 64-schedule, 1,000-team-game training reports with master 20261108 and the chart-focused policy. It delegates source, mechanics, allocation and report semantics to the existing component gate and validator. A failed or malformed dependency prevents reading reference bytes; it does not prevent reporting the other cohort's dependency failures. This implements the protocol's stable-candidate timing without opening reserved reference/held-out/transfer outcomes during development.

Schema 1 binds the canonical freeze digest, both source receipts and training reports, plus a corpus object containing its canonical root-relative directory, exact recursive file inventory and all 28 generated-to-reference folder mappings. Reference folders must be distinct, complete immediate children; every mapped team must contain all three normalized charts and readable named metadata. Reject omitted/extra teams, files, symlinks, missing inputs, changed bytes and rule differences. Recompute every raw decoder census with the existing decoder; retain unsupported symbols as failures and known defaults/fallbacks as explicit limitations. Recheck dependencies, manifests, reference inventory and freeze after processing, including changes during dependency revalidation. Bind complete campaign files without duplicating their full game receipts inside the census result. CLI outputs containing reference-derived hashes/decoder data must stay local under ignored `.ai-audits/chart-reference-comparison/`.

Before reading comparisons, assign partitions by sorting the SHA-256 of `paydirt-reference-partition-v1:` plus the generated folder name, then alternating development/withheld membership. This yields 14 teams per partition without selecting on results. Each mapping declares whether it was inspected before the freeze and explains prior use; any previously inspected withheld team makes the exercise retrospective cross-validation. These are trusted local declarations, not proof of non-observation, corpus ownership or mapping correctness. No source/fit limits change. Successful preflight establishes only declared corpus/decoder consistency, never a complete reference benchmark, transfer confidence, source acceptance, independent review or owner readiness.

## Exact weighted reference comparison design

Implemented by extending the existing exact chart-mechanics enumerator with exact out-of-bounds joint outcomes, primary B/QT trigger masses, special-team token/distance masses, recovery masses and extra-point miss mass. Existing fields remain. OOB flags follow the core priority and secondary parsers; they are pre-state chart flags, not final clock/scoring outcomes. Exact raw-token special distributions remain conditional on invoking that lookup, with unresolved block/foul/re-kick branches explicit.

For every mapped offense team and each of the nine calls/six defenses, compare all four generated/reference offense-defense combinations against the same uniform complete opposing-cohort mixture. This is an explicitly pre-state exploratory comparison, not the source-schedule policy or a replacement for matched engine field-position contexts. Recompute probabilities from nonnegative integer mass pairs, require exact mass one, and retain pending branches. Compare joint outcome distributions with exact signed differences and total variation; report offense-only, defense-only, joint and signed interaction contrasts. Keep known numeric yield contributions distinct from conditional known means and whole-play YPA. Compare special-team token masses, supported field-goal curves, recovery and extra points exactly. No universal reference-agreement threshold is invented: a difference is a diagnostic requiring later classification.

The existing gate revalidates the full reference-corpus preflight before reading/loading either set and after comparison. New `--reference-weighted` on the private `--reference-corpus` CLI retains bound input files and clears component flags if they change. Output remains in ignored local reference-comparison storage. Synthetic/public tests preceded production changes and cover unequal physical weights, OOB/yield correlation, overridden markers, independent secondary rolls, fallback mass, rare special events, malformed/missing exact mass and late evidence changes. Successful computation establishes only `weighted_validated=true`; stateful crossed contexts, paired campaigns, source fit, material-outlier review, transfer and full readiness remain required. No actual private corpus or reserved family is opened during implementation.


## Stateful crossed reference context design

The next component will execute matched engine contexts, separate from exact pre-state weighting and full reference campaigns. For each ordered pair of distinct mapped teams, all four R/R, G/R, R/G and G/G combinations use every nine primary calls/six formations at own 1, own 40 and opponent 2, each with first-and-distance-to-goal capped at ten or fourth-and-one. A trial repeats the selected call/formation up to four times, stopping on an engine-confirmed score, possession change or game end. The core owns clipping, down/first-down/recovery/return/scoring/penalty decisions. Touchdown trials stop before conversion/kickoff; full games remain separate.

Use training diagnostic master 20261108 with a versioned SHA-256 domain and sorted team identifiers/context/call/formation. Share each initial seed across the four chart combinations; later RNG paths may diverge. Retain and restore caller RNG state. A fixed chart-blind balanced penalty chooser delegates final choices to the existing auto-game resolver. Initial contexts are deliberate engine test setup; no chart mutation or field/scoring reinterpretation is allowed. Keep real source-year rules and chart yardage factors. Unit fixtures remain synthetic/public only, and no real private corpus or reserved-family outcomes are opened during implementation.

For each trial reconcile authoritative home/away box totals, selected/credited counts, scoring log, legal finite state and pending decisions. Preserve trial seed and context on failure and continue reporting other teams. Aggregate counts and canonical receipt digests by team/context/call/formation/scenario, retaining denominators and coverage. Report per-trial official net yards, points, first downs, turnovers, fourth-down failures, primary result/tail/secondary/recovery counts, sequence lengths and termination reasons. Exact fractions represent observed integer sample ratios, not analytical probabilities or historical truth. Report offense/defense/joint/interaction contrasts, formation contrasts to A, rankings and repeated-call diagnostics without an invented reference-agreement or play-frequency cap.

The existing gate will require and repeat the stable corpus/source/training/freeze preflight around collection, with no partial cohort mixture. New private-only `--reference-contexts` will be mutually exclusive with `--reference-weighted`. Complete context collection can set only `contexts_validated=true`; stateful outlier/exploit review, paired campaigns, source fit, transfer and full readiness remain required. Contexts do not consume the reserved paired-game master 20461108. Synthetic test-first controls will cover clipping/goal-line/safety, first/fourth downs, B/QT, own/lost recoveries and return scores, penalties, determinism, RNG/input preservation, complete four-combination coverage, malformed/failed evidence and dependency changes.


### Stateful context component implementation

The existing reference gate and CLI now expose `audit_reference_context_evidence` / `--reference-contexts`. A dedicated engine collector executes the fixed six-context, four-combination census described above; the gate independently reconciles every team/scenario/bucket, aggregate accounting, exact empirical denominators, sequence lengths, contrasts and rankings. It repeats complete dependency/corpus validation even after collection failure. Public synthetic boundary fixtures scale one two-team report solely to exercise the 28-team gate; they are explicitly not actual 28-team play evidence. No private reference or reserved outcomes are opened during implementation. The component leaves outlier/exploit review, paired campaigns, source/transfer validation and all acceptance flags outstanding.


## Paired full-game reference evidence design

The next component compares saved full-engine reports from the existing `run_engine_audit`, without implementing another game runner or opening actual reserved outcomes during development. Use the same actual source schedule, a complete generated-folder to reference-folder bijection, source-year rules, fixed chart-focused normal policy and initial master/repetition/game seed derivation. Main acceptance exposure remains master 20461108, 64 complete repetitions per set and at least 1,000 appearances per team; smaller explicitly training-seeded synthetic/public controls cannot meet this exposure. Equal initial seeds pair game identities, not later play paths.

Independently validate both complete raw reports against their actual directories, loaded runtime, policy, mapped schedules, seed receipts, ordered call/official accounting, replications and derived metrics. Preserve both failures when both sets are invalid. Retain each set's source-fit verdict under unchanged league/team bounds; reference agreement or a mechanically valid comparison cannot imply source acceptance. Missing teams, duplicate mappings, schedule changes, unequal repetition counts and invalid raw evidence fail rather than yielding a partial comparison.

Report aggregate deltas separately from the mean of paired repetition deltas. Estimate between-repetition standard error from those paired differences, never treating plays as independent; a single diagnostic repetition has no estimated standard error. Retain exact team/game counts, mapped game-pair seeds and score differences, policy-conditioned strength rankings, ordered-call/repetition summaries and retained-primary tail denominators. No universal reference-agreement bound or historical route truth is introduced.

Extend the existing gate and private CLI with a separate strict schema-1 paired declaration binding the freeze digest, canonical reference-declaration digest, and generated/reference report file paths/digests. Read reports only after the complete stable corpus/source/training/freeze preflight passes. Repeat that preflight after either a failed or successful comparison, then recheck all artifacts and original declaration bytes. Require complete main exposure to set `paired_validated`; keep benchmark/source/readiness/release completion false pending material outlier, transfer and independent review. The command validates saved evidence and starts no games; a maintained guarded collection workflow and explicit seed-use/announcement history remain necessary before actual reserved execution.

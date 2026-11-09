# Released chart regression

Unchanged published charts need a regression check against their published
identity. New or regenerated charts need source reproduction and historical-fit
qualification. These checks answer different questions.

## Immutable baseline

`python3 -m paydirt.released_chart_regression_audit --season 2024 --output .ai-audits/released-2024.json`

The only built-in baseline is tag `v1.10.3`, pinned to commit
`1467b11e151fe9981177890e2a7a6b805402b3f0`, for 1983-generated (28 teams) and
2024 (32 teams). The tag must still resolve to that commit. The tool reads trusted
Git objects, compares the complete season file inventory and validation contract,
and rejects changed or missing bytes, symlinks, extra files and self-declared
replacement provenance. Public sanitized manifests are compared as published;
raw private source inventories are neither needed nor emitted.

The public structure and actual chart decoders must pass. All gameplay Python
modules in the core package, backend and packaged launcher must match the trusted
release. Only the package version literal and the `FastAPI(version=...)` metadata literals
in the two existing API entry points may change. Their other AST behavior must
remain identical; this allowance cannot hide changes to rules or API behavior. Explicit
candidate-generation/source-validation tools are excluded because they do not
resolve player games; adding exclusions requires review. A gameplay change fails
closed pending reviewed paired baseline regression evidence. This initial gate
does not implement a statistical comparison for changed core/backend gameplay.

Frontend implementation identity is explicitly not checked by this chart gate.
The current release boundary is accepted only after the frontend diff is
reviewed as display/transport/test-port changes and the complete frozen
real-engine browser regression passes. This is not a permanent exemption for
UI gameplay behavior: future changes still require relevant review and
regression of submitted plays, modifiers, penalties, possession and displayed
engine results. Frontend changes require actual review and browser regression; the receipt cannot establish release readiness by itself. The core
engine remains authoritative for outcomes and rules. The receipt reports this
frontend limitation and `release_certified: false`.

The full engine, backend, browser, integration, historical calendar and AI audits
in AGENTS.md remain required. Exact chart and gameplay identity establishes that
these inputs have not worsened; it does not prove historical accuracy or replace
those functional checks. New random fit estimates are not compared naively against
old estimates.

## Existing limitations remain visible

Receipts explicitly set `strict_fit_passed`, `historical_accuracy_checked` and
`source_reproduction_checked` to false. Trusted contract exceptions are copied
without relabeling them as passes: 1983 49ers/Falcons completion-rate misses and
the 2024 Ravens rushing-efficiency miss remain documented exceptions. Consult the
trusted contracts for measured values and tolerances. Other contract limitations
and source coverage remain bound by the exact contract hash.

A passing released regression is neither a new-season certificate nor approval to
regenerate these charts with different inputs. New or changed charts, including
1977 candidates, retain strict source identity, independent reproduction, sample
requirements and unchanged fit tolerances. The owner separately authorized a
narrow 1977 statistical release exception after finite search and canonical final
characterization; it must bind exact inputs/reports and disclose every accepted
fit miss. That exception cannot turn a failed strict result into a pass, and
waives no source, mechanics, gameplay or native-install requirement. Run the
normal generated-chart audit and require all non-exempt source/reproduction and
nonstatistical checks to pass. Strict fit failures remain recorded failures; only
the exact reviewed, hash-bound 1977 authorization can accept its documented
statistical misses for release. There is no automatic fallback between gate types.

## Local evidence

Keep receipts under ignored `.ai-audits/`. The receipt hashes only public release
inputs and records the immutable baseline identity, retained exceptions, mechanics
and any failures. It does not export raw historical source inventories or logs.

The frozen new-candidate collector `scripts/run_chart_regression.py` remains a
strict source/fit workflow. Its default command inventory and output validator
still require private source receipts and engine evidence. It is not the
unchanged-public-release collector. `required_regression_commands(released_charts=True)`
exposes the explicit AGENTS inventory; the default remains strict for existing
candidate tooling. Run and retain every AGENTS result for the released route.

## Exact 1977 statistical acceptance

`scripts/audit_1977_release.py` invokes a separate, fail-closed acceptance gate.
It requires a reviewed policy pinned to an immutable Git commit and SHA-256;
a candidate cannot authorize its own replacement policy. The policy binds the
complete canonical and sanitized public inventories, source contract and raw
execution-report hash. The gate independently repeats source, reproduction,
decoder, mechanics, allocation, observer, runtime and accounting checks and
requires at least 72 repetitions and 1,000 games per team.

The public season must contain every canonical gameplay file. Its chart hashes,
accuracy flag and exact exception list must match independently measured results.
Private input inventories remain local. Strict failed bounds stay failed in the
receipt; `passed` describes only the exact reviewed release policy, and
`release_certified` remains false. Full regression and published native acceptance
remain separate requirements. A missing or unpinned policy never falls back to
this route automatically.

```sh
python3 scripts/audit_1977_release.py --root . \
  --season-dir CANONICAL --contract CONTRACT --engine-report REPORT.json.gz \
  --policy POLICY --public-season-dir seasons/1977 --stats-dir STATS \
  --reproduced-dir REPRODUCED --input-files SOURCE_MAP.json \
  --output .ai-audits/1977-release-acceptance.json
```

Uppercase paths refer to the reviewed local source bundle and canonical evidence,
not distributed raw source files. The source map contains logical source keys and
paths, with relative paths resolved against `--root`. The output must be new and
outside all input directories. Exit zero requires the independently computed
acceptance result to be exactly true.

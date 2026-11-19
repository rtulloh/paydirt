# v1.12.0 release qualification

Status: implementation and review in progress; no commit, push, tag, publication or remote preservation claimed by this note.

## Authorized scope

On November 19, 2026 the owner approved completion of the remaining team statistics, committing the integrated seasons/save-load work, full regression, ticket/play-test review, release preparation and preservation. v1.11.0 is already published, so the new feature release targets v1.12.0. The six season slices and subsequent owner-requested fixes remain in scope; individual player statistics and FLOW-035 narration remain excluded.

## Work allocation

- Core agent: authoritative retained-play team counters, pending-decision safety and typed special-team facts.
- Domain agent: optional metadata persistence, validation, max/additive aggregation and paired-input efficiency.
- Frontend agent: all thirteen ESPN-inspired team categories, compact accessible headers and overview leader cards.
- Root: independent integration review, metadata/packaging, release notes, complete regression/audit evidence, issue reconciliation and preservation.

Each implementation uses a goal and test-first regressions with public sample or synthetic fixtures. Production freeze must precede integrated full regression; changing source while a loaded audit is running invalidates runtime identity evidence.

## Required qualification

1. Complete focused tests and changed-module coverage; disclose deliberate gaps and test expectation changes.
2. Independently review engine capture, checkpoint/legacy behavior, aggregation definitions and display-only UI.
3. Stage only reviewed source/tests/docs; keep per-machine `.codex/config.toml` local and preserve it privately. Commit prefix: `v1.12.0:`.
4. Run `.venv/bin/python scripts/run_full_regression.py --clean-checkout` and investigate every failed gate. It includes both complete browser games, every actual-calendar game and simulated postseason, paired AI selection audits and released-chart identity/mechanics checks.
5. Inspect AI call distributions and warnings with sample counts; review resolved tickets individually for fresh relevant evidence. Do not close gameplay issues solely from unit tests.
6. Carry forward unchanged released 1977 data only under full-inventory byte identity against `88fd6ce4de042bb768933ef1e60cc9db55764e4a` and fresh public chart quality audit, retaining all statistical exceptions.
7. Build both native and browser distribution paths; verify actual Pyodide operations and packaged native application, including saves and all bundled seasons. Downloaded published packages require separate cross-platform smoke receipts after publication.
8. Before every push (including tag pushes) satisfy root AGENTS.md gates. Require successful exact-commit upstream Tests including coverage before a release tag. Record actual commit, workflow and receipts here.

## Initial evidence

- Existing remote main is `07a35df2c78449712d2bcbbc7083364d73bc1ab4`; GitHub repository is public and latest published release is v1.11.0.
- All 143 files under seasons/1977 were compared against immutable v1.10.6 inventory and bytes, including rejection of symlinks/missing/extra files. Identity passed. Fresh public 28-team chart audit passed. Receipts: ignored `.ai-audits/release-1.12.0/`.
- New v1.12.0 smoke-profile regression failed against the unchanged explicit profile allowlist as expected. After adding the reviewed 90-team release profile, all 78 smoke-harness cases passed. Existing older profiles are retained; the future-version rejection example advances from now-reviewed 1.12.0 to unreviewed 1.13.0. Native checks now include corrected 1983 labels for v1.12.0.
- Smoke harness coverage is 38% under its synthetic suite; uncovered paths are real OS installation/extraction, browser launch and downloaded-artifact CLI orchestration. Those require native artifact runners, not fabricated synthetic success. An initial module-qualified coverage invocation collected no data because the test imports the harness dynamically; a source-directory invocation measured the actual file.

## Preservation

Public source will be remotely preserved only after a qualified GitHub push and verification of exact remote commit. Private charts, raw sources, histories and audit evidence must never enter the public repository. Current local audit evidence is approximately 15 GB. Saved games/standings, original private chart packages under the configured native application data directory and per-machine configuration also need private preservation.

No Google Drive connector, synced folder, mount or configured upload client was found. The owner instructed that Codex create the archive locally and the owner will upload it. Stage a private, fully read-back-verified archive plus checksums under Desktop/Paydirt-private-backup-2026-11-19, with a final source/evidence supplement after qualification. Local staging alone does not satisfy the December 4 machine-reset requirement. Remote upload/verification remains an owner handoff; do not claim it complete without an actual destination and verification.

### Local archive verification

`/Users/rtulloh/Desktop/Paydirt-private-backup-2026-11-19/paydirt-private-data.tar.gz` was fully decompressed and every member checked against the captured SHA-256 inventory: 98,536 files, 9,026,145,793 compressed bytes. The adjacent private manifest and SHA256SUMS.txt record exact hashes and consistent SQLite snapshots. Remote upload and verification remain pending with the owner. A final source and qualification-evidence supplement is still required.

## Integrated review and focused validation

The owner requested removing duplicate Overview/Standings navigation. Overview is retained with all division standings and recent results; focused tests assert that the Standings tab is absent and navigation still works. All 42 SeasonDesk tests pass (91.24% lines, 89.01% branches). The production frontend build passes with existing Browserslist age and dynamic-import chunk warnings.

Domain/persistence: 122 focused core tests and 114 backend tests pass; measured coverage is campaigns 94%, save/load 79%, browser builder 100%, checkpoints 89%, campaign operations 88%. Remaining coverage gaps are existing catalog/error and legacy end-zone branches. All new paths have focused coverage.

Independent review checked checkpoint retained-decision context, legacy unknowns, paired rate/turnover coverage, signed returns, MAX aggregation and duplicate-decision suppression. It found a field-goal penalty first-down classification gap; review also found fumble-recovery automatic-first-down classification gaps. The initial full regression was deliberately interrupted before qualification so these could receive failing regressions and authoritative source corrections. No result from that interrupted run qualifies the final candidate.

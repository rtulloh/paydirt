# Numeric 1983 season directory

The public generated 1983 charts now live in `seasons/1983`, matching the numeric
names used by the other seasons and packaged applications. All 144 public files
are moved without changing bytes. Packaging, CI, source-audit commands and
maintained documentation use the numeric path. Private comparison charts are
retained locally at `.ai-audits/escrow/1983-private-charts/`, outside season
discovery; standalone private integration/reproduction runners use that path
explicitly so their original dice trajectories remain meaningful.

The released-chart auditor keeps the immutable v1.10.3 commit, original baseline
path, validation contract and complete file-byte comparisons. An explicit current
path mapping permits only the directory-prefix relocation. Historical audit cohort
IDs and immutable contract source-path bindings retain `1983-generated` for
evidence compatibility; they are not public season directory names.

## Test-first evidence

Before implementation, packaging/ignore checks and a synthetic relocated-release
control failed as intended (three failures, 32 passing controls). Synthetic changed
chart, extra-file and symlink cases still reject the relocated season. The private
replay path assertions also failed in all three injected-outcome modes before
fixing their path selection. No unit test reads historical season charts.

Existing expectations changed only for numeric packaging/CI paths, the public
ignore rule and explicit escrow replay paths. Regression-output fixtures now
model generated 1983 charts and the numeric AI audit directory as the same
synthetic cohort, preserving complete fingerprint and tamper checks. Clean-snapshot fixtures also
use the numeric public directory and keep forbidden private stand-ins separate;
the collectors map stable cohort IDs to numeric paths before comparing hashes.

## Validation

Focused packaging, release-gate, source-archive, replay, regression-evidence and
documentation checks pass (114 tests). Both actual released-chart gates pass.
Full pre-push regression receipts are retained under ignored
`.ai-audits/1983-directory-rename/`; publication remains conditional on every
mandatory command passing. This directory rename does not qualify new chart
statistics or change gameplay.

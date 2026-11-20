# v1.12.2 complete-package release qualification

Status: corrective candidate in preparation; not published.

The preferred play option is the [browser edition](https://rtulloh.github.io/paydirt/).
Desktop applications are optional alternatives. Browser games and seasons persist
in the same profile/site; export important saves for backup or transfer.

## Correction and immutable history

v1.12.0 packages failed startup because release dependency installation differed
from tested backend requirements; its macOS bundle resource seal was also invalid.
v1.12.1 repaired both defects and four actual native packages passed functional
acceptance, but an NSIS service error was allowed to omit the Windows installer.
Both earlier tags and their assets are retained; neither establishes complete
five-package release acceptance. See [FLOW-040](issues/FLOW/FLOW-040.md),
[FLOW-041](issues/FLOW/FLOW-041.md) and [FLOW-042](issues/FLOW/FLOW-042.md).

The new correction must fail before publication if any required package is absent,
retain exact-commit CI qualification, and verify all five actual published packages.
No released charts or gameplay rules are changed. The owner-requested
[STAT-007](issues/STAT/STAT-007.md) yardage-heading cleanup and
[DATA-051](issues/DATA/DATA-051.md) kicking-chart review are follow-up tickets.

## Qualification requirements

Require test-first workflow/profile regressions, all thirteen local gates including
the clean candidate export, fresh released-1977 byte identity/public chart audit,
AI distribution and per-issue review, and green exact-commit upstream CI before
tagging. After publication, verify downloaded asset identity, native normal-entry
launch, every bundled season in API/UI, new games with both chart books, clean
logs/browser and normal shutdown on all five supported package targets.

macOS ad-hoc resource sealing is separate from Developer ID signing/notarization.
The fresh Safari v1.12.1 download passed strict signature verification but was
blocked by Gatekeeper without a security override. Record a fresh security check
for this version and retain that limitation; do not infer Gatekeeper approval
from native functional checks. Updated browser-first guides in the candidate must
also be included in its newly built application.

## Focused test-first evidence

The mandatory-package workflow baseline failed twelve intended cases with
twenty-two controls passing. All 42 workflow/packaging cases pass after removing
allowed NSIS failures, executing the exact five-package inventory gate, and
requiring matched uploads. Synthetic positive/missing/empty/symlink/stale-DMG
cases execute every guard statement and branch across the suite. No NSIS retry
or relaxed completion policy was introduced.

The new v1.12.2 native smoke profile failed nine intended cases with twenty-three
passing controls before the version was supported; 114 final smoke tests pass.
Smoke-driver statement coverage is 43.8% and branch coverage 49.1%; changed profile
and identity guards are exercised. Platform extraction, download and normal process
paths remain subject to actual native published-package verification. Prior release
profiles remain intact. Browser-first and storage guides were updated together;
individual player statistics remain excluded.

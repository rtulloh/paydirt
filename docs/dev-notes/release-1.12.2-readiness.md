# v1.12.2 complete-package release qualification

Status: [published v1.12.2](https://github.com/rtulloh/paydirt/releases/tag/v1.12.2) at `2618016116f4bf4489924aa63e6ca528d3332cce`; all five actual downloaded native functional checks pass. Mac first-launch restrictions remain explicit below.

The preferred play option is the [browser edition](https://rtulloh.github.io/paydirt/).
Desktop applications are optional alternatives. Browser games and seasons persist
in the same profile/site; export important saves for backup or transfer.

## Correction and immutable history

v1.12.0 packages failed startup because release dependency installation differed
from tested backend requirements; its macOS bundle resource seal was also invalid.
v1.12.1 repaired both defects and four actual native packages passed functional
acceptance, but an NSIS service error was allowed to omit the Windows installer.
Both earlier tags and their assets are retained; neither establishes complete
five-package release acceptance. See [FLOW-040](https://github.com/rtulloh/paydirt/issues/160),
[FLOW-041](https://github.com/rtulloh/paydirt/issues/161) and [FLOW-042](https://github.com/rtulloh/paydirt/issues/162).

The new correction must fail before publication if any required package is absent,
retain exact-commit CI qualification, and verify all five actual published packages.
No released charts or gameplay rules are changed. The owner-requested
[STAT-007](https://github.com/rtulloh/paydirt/issues/206) yardage-heading cleanup and
[DATA-051](https://github.com/rtulloh/paydirt/issues/119) kicking-chart review are follow-up tickets.

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

## Final source and published-package qualification — 2026-11-19

The immutable tag binds `2618016116f4bf4489924aa63e6ca528d3332cce`.
All thirteen sequential pre-tag gates pass with zero failures/skips: core and clean
tracked export 12,029 tests each, backend 682, frontend 593/build, all 39 real-engine
browser cases, lint, fourteen-game runner, all 224 regular/nine playoff games,
both AI audits and released 1983/2024 chart checks. Backend retains 519 dependency
deprecation warnings; build advisories remain in its log. Fresh 1977 inventory
checks all 143 files byte-identical to the immutable v1.10.6 baseline; the public
chart audit passes without claiming fresh statistical fit. AI totals reconcile:
public 32/32 games (4,896 calls), local 448/448 (65,793 calls). Only the two known
36-call balanced third-and-long concentration advisories remain; Hard has neither.
The 77 resolved-ticket criteria were reviewed without inferring rare-case proof
from broad game completion.

[Tests 44668355000](https://github.com/rtulloh/paydirt/actions/runs/44668355000) and
[Browser 44668354907](https://github.com/rtulloh/paydirt/actions/runs/44668354907)
pass on that exact commit. Python 3.10 passes 12,029 tests with 87% package coverage;
reviewed unchanged coverage gaps remain in defensive branches/platform entry paths.
The [release workflow 44674721368](https://github.com/rtulloh/paydirt/actions/runs/44674721368)
passes all builds, exact inventory publication and all five actual downloaded-native
checks. Each package exposes all 90 teams in API/UI, starts distinct 2026 and 1977
games with both chart books, has no browser/application errors and shuts down normally.
These smokes do not claim complete native games. Independent receipt/digest verification
passes for release ID `452271063`:

| Actual published asset | SHA-256 |
| --- | --- |
| `PaydirtSetup.exe` | `72533846257953c8cf4902379c2d6bb0fd782db1d437c8be78a2205bc21dc5e5` |
| `paydirt.exe` | `ffdc7707e35fd327503d2b61b08f941e319fda2c2b0dc23070cab77db322705a` |
| `Paydirt-x86_64.AppImage` | `6acd7dc783fbd03a11323a6231f87bfef7f9a4919fcfed9ae3a02b02b988497b` |
| `Paydirt-1.12.2-x86_64.dmg` | `260e5d6a18eb4624bfba2f09ddedcee0e50c501415c25bc3d2bf0a698a4c8fb3` |
| `Paydirt-1.12.2-arm64.dmg` | `72ea95514afe0a7ce1e842f7a3e40da6a591ab1c5e301ee43702d7f3d699e9a4` |

Both actual downloaded Mac bundles pass deep strict signature verification. The
first local helper rejected a `/var` versus `/private/var` mount alias; canonical
path reconciliation passes on the same unmodified bytes, and the failed helper
receipt is retained. Fresh browser-downloaded Apple Silicon DMG identity/quarantine
and its bundle seal pass, but Gatekeeper assessment rejects launch and no API
becomes available. No quarantine removal, signing alteration or security override
was used for that first-launch check. These are ad-hoc sealed applications, not
Developer ID signed or notarized; hosted native runtime success does not remove
this limitation. Browser play remains the preferred option.

Ignored evidence under `.ai-audits/release-1.12.2/`: `pre-tag/summary.json`,
`pre-tag/ai-review.json`, `pre-tag/resolved-ticket-review.json`, fresh 1977 receipts,
`tests-coverage-review.json`, `published-verification.json`, the five
`published-receipts/` native receipts/logs, `published-independent-review.json`,
`macos-published-seals-canonical/receipt.json` and `macos-fresh-download-security.json`.
Private paths, saved games and narrative logs are not published.

FLOW-036/040/041/042 close from this actual evidence. DATA-047 also closes after
actual downloaded ARM corrected-label selection, scoreboard, both chart books,
kickoff and scrimmage checks for Chargers/Cardinals and Raiders/Chargers, with no
JavaScript/request errors. All five native API profiles confirm SD/STL/LA; the
additional targeted receipt is `data047-published-browser-ready-controls/receipt.json`
under the same ignored evidence directory. It is not a full-game or first-launch
security claim. DATA-051 retains its bounded kicker-calibration follow-up and
STAT-007 its yardage-heading cleanup; both remain open. Earlier v1.12.0 startup/seal and v1.12.1 missing-installer failures remain
immutable and documented. Local private archives are readback verified; the owner
reports upload complete, while independent remote readback is unavailable.

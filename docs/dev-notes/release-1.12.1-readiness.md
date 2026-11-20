# v1.12.1 corrective release qualification

Status: local correction and qualification in progress; not published.

## Published defect and immutable history

The v1.12.0 tag binds commit `205fbaec47ebe247ecac11378e2aa2592751621b`.
Its source passed all thirteen local gates, a clean tracked checkout, the
11970-test upstream Python 3.10 suite (87% coverage), and both complete browser
workflows. Post-publication workflow [44656259329](https://github.com/rtulloh/paydirt/actions/runs/44656259329)
then failed actual downloaded-package startup on all five supported targets.
The bundled, unbounded FastAPI dependency no longer exposed the startup-handler
method used by the native library guard. The development environment and backend
CI used the pinned backend requirements, exposing a packaging dependency mismatch.
The failed release is marked prerelease with a prominent do-not-install notice;
its tag and assets are retained. Browser play was unaffected.

A fresh Safari download of the Apple Silicon disk image retained quarantine and
matched its published digest. Strict signature verification also found that the
completed app bundle lacked a valid resource seal. Re-signing an isolated copy
with an ad-hoc identity repaired that seal; this is not Developer ID signing or
notarization and does not establish Gatekeeper approval.

## Correction scope and required evidence

FLOW-040 makes release builds consume the pinned backend requirements, checks
dependency consistency and retains the resolved package inventory. FLOW-041 seals
and strictly verifies the completed macOS bundle before disk-image staging.
The published-package driver explicitly reviews the same 90-team inventory and
corrected 1983 labels for v1.12.1 while preserving all historical profiles.
Version metadata is incremented; released chart bytes and statistical tolerances
are unchanged.

Qualification requires a fresh isolated packaged build and actual API/browser
startup, all thirteen regression gates with a clean tracked checkout, fresh 1977
identity and AI/issue review, and green exact-commit upstream CI before tagging.
After publication require all five actual downloads, digest-bound native receipts,
and a fresh macOS first-launch security check. Do not infer release health from
source tests, artifact presence, successful builds, or ad-hoc signature validity.

## Local correction evidence

The dependency workflow regression first failed once with 21 passing controls,
then passed after consuming the pinned requirements. The isolated Python 3.10
package contains FastAPI 0.109.0, Pydantic 2.5.0, Starlette 0.35.1 and Uvicorn
0.27.0; dependency consistency passes. Its normal executable launched outside
the checkout on an isolated port: all 90 API/UI teams, corrected 1983 labels,
new 2026/1977 games with both chart books, error-free browser and normal shutdown
passed. This local candidate is not published-artifact acceptance.

Mac assembly regressions first failed in two cases; three final cases execute
the assembly with success and injected signing/verification failures, requiring
that no disk image is staged after either failure. An isolated copy of the actual
v1.12.0 app fails strict verification before repair, passes after the new ad-hoc
seal, rejects tampered resources, and passes again with original bytes restored.
No quarantine removal or security override was used. The unchanged Python
packaging module retains 100% focused statement/branch coverage; shell behavior
is verified by execution rather than attributed to Python coverage.

The v1.12.1 smoke profile first failed nine cases with 89 passing controls,
then all 98 passed. Smoke-driver coverage is 45%; download, extraction and
platform process paths require native artifact integration. Existing immutable
profiles remain covered, and no test assertions or skips were weakened.
Full current-source regression and exact-commit CI remain pending.

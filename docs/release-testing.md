# Testing Published Applications

[Documentation index](README.md) · [Development guide](development.md)

The **Published application native runtime smoke** workflow tests existing release-page downloads. The release workflow calls it automatically after publication and waits for every native target; a failed verification leaves the release workflow failed, even though published assets remain available. It never rebuilds an executable, publishes a release or changes an immutable tag. A release is not verified until these checks pass. Manual dispatch remains available for existing immutable releases:

```sh
gh workflow run post-release-smoke.yml --ref main -f release_tag=v1.10.3
gh run list --workflow post-release-smoke.yml --limit 1
```

The workflow uses native hosted Windows, Linux x86_64, Intel Mac and Apple Silicon Mac runners. Windows separately tests the portable executable and an isolated silent installation of the published NSIS installer. The installed executable must also match the published portable executable's digest. Linux extracts the actual AppImage and launches its AppRun entry point, avoiding a runner FUSE dependency; this launch method is recorded. Each Mac mounts the published DMG, copies its app to an isolated directory and launches its normal executable.

Every downloaded asset must match GitHub's published size and SHA-256 digest before execution. The application runs outside the source checkout with Python import overrides removed. Windows/Linux use isolated application-data directories; fresh hosted Mac user data and the exact season inventory prevent local data from masking missing bundled teams. No local developer application or port is touched by dispatching the workflow.

The base acceptance profile covers the three bundled seasons in v1.10.3: 1983 has 28 teams, 2024 has 32, and public sample 2026 has two. The actual packaged API must report the requested version, expose all team lists, create a fresh Ironclads–Thunderhawks game and return populated home/away chart books. A headless Chromium browser must render each season’s full team grid, select both public teams and reach the new game’s coin-toss screen without browser or failed local asset requests. Inspect application logs and require bounded shutdown.

The explicit `include_1977` profile is reviewed for v1.10.4 and the next corrective target v1.10.5 (28 additional teams). The automatic release call requires it because current builds bundle 1977. Manual verification may omit it only for releases without that season; the exact packaged season inventory must still match. The v1.10.3 profile cannot opt in, and later versions need an explicit profile review. For a manual verification of the corrective release after publication, use `-f release_tag=v1.10.5 -f include_1977=true`. Both API and browser use the same selected counts; unexpected or missing seasons fail. The 1977 opt-in also creates a separate game using two IDs returned by that season’s packaged team list, verifies fresh game state and loads populated home/away chart books. The public 2026 game remains mandatory. The additional game must have a distinct identifier, and returned game/chart season and team identities must match the requested teams. Receipts retain each season’s verified IDs, game identifier and chart results.

For v1.10.5, packaged 1983 team identifiers must be unique and the API must expose Chargers `SD '83`, Cardinals `STL '83`, and Raiders `LA '83`. Missing teams and stale geographic labels fail even when team counts are correct. The receipt retains the verified labels. The v1.10.3/v1.10.4 historical checks retain their existing profiles; this correction does not rewrite acceptance of immutable older assets.

Each job preserves `receipt.json`, native application logs, a browser screenshot and release metadata as workflow artifacts, including when checks fail. A failed job prevents an all-clear; inspect its retained error and identify application, acquisition or harness failures before a justified rerun. Application repairs require a new immutable version, not replacing an existing asset. Synthetic identity/API corruption controls verify the harness without historical fixtures or local application access.

This is focused packaged-runtime acceptance. It supplements full regression and browser gameplay checks. Headless browser execution does not prove desktop default-browser behavior on every OS, older supported OS compatibility, signing/notarization, SmartScreen or browser-quarantine/Gatekeeper first-launch acceptance. Record those limits separately. See AGENTS.md's required post-publication artifact checks and the release's maintained validation record.

Before any push or tag, complete the full AGENTS.md regression. [Released-chart regression](released-chart-regression.md) requires immutable published inputs, the exact owner-reviewed DATA-047 metadata corrections where applicable, and unchanged gameplay; new or regenerated charts retain strict source, reproduction and applicable fit gates. Published-asset acceptance supplements both.

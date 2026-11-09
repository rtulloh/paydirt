# Testing Published Applications

[Documentation index](README.md) · [Development guide](development.md)

The manual **Published application native runtime smoke** workflow tests existing release-page downloads. It never rebuilds an executable, publishes a release or changes an immutable tag. Run it after publication, before declaring the packaged runtime verified across supported platforms:

```sh
gh workflow run post-release-smoke.yml --ref main -f release_tag=v1.10.3
gh run list --workflow post-release-smoke.yml --limit 1
```

The workflow uses native hosted Windows, Linux x86_64, Intel Mac and Apple Silicon Mac runners. Windows separately tests the portable executable and an isolated silent installation of the published NSIS installer. The installed executable must also match the published portable executable's digest. Linux extracts the actual AppImage and launches its AppRun entry point, avoiding a runner FUSE dependency; this launch method is recorded. Each Mac mounts the published DMG, copies its app to an isolated directory and launches its normal executable.

Every downloaded asset must match GitHub's published size and SHA-256 digest before execution. The application runs outside the source checkout with Python import overrides removed. Windows/Linux use isolated application-data directories; fresh hosted Mac user data and the exact season inventory prevent local data from masking missing bundled teams. No local developer application or port is touched by dispatching the workflow.

The current acceptance profile covers the three bundled seasons in v1.10.3: 1983 has 28 teams, 2024 has 32, and public sample 2026 has two. The actual packaged API must report the requested version, expose all team lists, create a fresh Ironclads–Thunderhawks game and return populated home/away chart books. A headless Chromium browser must render each season’s full team grid, select both public teams and reach the new game’s coin-toss screen without browser or failed local asset requests. Inspect application logs and require bounded shutdown. Adding a bundled season requires an explicit profile/test update; do not silently accept unexpected or missing data.

Each job preserves `receipt.json`, native application logs, a browser screenshot and release metadata as workflow artifacts, including when checks fail. A failed job prevents an all-clear; inspect its retained error and identify application, acquisition or harness failures before a justified rerun. Application repairs require a new immutable version, not replacing an existing asset. Synthetic identity/API corruption controls verify the harness without historical fixtures or local application access.

This is focused packaged-runtime acceptance. It supplements full regression and browser gameplay checks. Headless browser execution does not prove desktop default-browser behavior on every OS, older supported OS compatibility, signing/notarization, SmartScreen or browser-quarantine/Gatekeeper first-launch acceptance. Record those limits separately. See AGENTS.md's required post-publication artifact checks and the release's maintained validation record.

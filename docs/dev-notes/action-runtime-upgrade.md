# GitHub Actions Node 24 runtime upgrade

Prepared 2026-10-26; local validation complete, upstream validation pending.
This is CI maintenance, not a gameplay or dependency-vulnerability fix.

## Migration review

- Verified released action manifests for checkout 7.0.1, setup-python and
  setup-node 7.1.0, upload-artifact 7.0.2, download-artifact 8.0.2,
  Codecov 7.1.1, and action-gh-release 3.0.3. All JavaScript actions use
  node24. Codecov is composite; its pinned github-script v8 uses node24 too.
- Checked every configured `with` input against those published manifests.
- Renamed Codecov `file` to `files`, keeping coverage upload optional.
- Disabled setup-node automatic caching in standalone builds; retained the
  explicit browser npm cache/lockfile. No registry/auth-token inputs are used.
- Reviewed checkout credential relocation and privileged fork restrictions;
  no Docker actions or privileged fork-checkout triggers are used here.
- Kept zipped artifact defaults and named download directories; release asset
  paths, build matrix, runner selections, Python versions, Node 24.22.1, and
  tag-only release guard are unchanged.

## Validation

- Test-first workflow baseline: four expected failures, five passing controls.
  All nine now pass; no existing test expectations changed.
- Core: 5,448 passed, eight existing skips; 76% branch-inclusive coverage.
- Backend: 218 passed, existing Pydantic deprecation warnings.
- Frontend: 255 passed, one existing skip; production build and both real-browser
  checks passed using Node 24.22.1. Existing stale Browserslist warning remains.
- Ruff passed. Standalone integration runner passed; historical cases 12/12;
  generated regular season 224/224 (13 overtime games, five valid ties);
  playoffs 9/9 with no ties. No standings persisted.
- Audits: public 32/32 (3,930 calls, 199 groups), local 448/448 (52,681 calls,
  3,066 groups). Call totals, group counts, and distinct calls reconcile.
  Reviewed down/distance/mode shares and comparable-situation streaks: no Hard
  concentration warning; one previously documented legacy-balanced advisory.
  AI-009 remains confirmed closed; other resolved issues lack issue-specific
  evidence for closure from these runs. Reports remain ignored/local.
- Clean tracked-source-only snapshot: 5,431 core passed, 25 existing missing-
  private-data skips; 218 backend passed. No private charts were copied.
- The previously reported 17 npm vulnerabilities are not remediated here.

## Publication gates

Ask the user before pushing. Then verify the hosted test matrix and manually
dispatch standalone builds for Linux, Windows, macOS ARM64, and macOS Intel.
Manual dispatch must not publish a release. A future release/tag requires
separate approval and all required pre-push checks; local checks alone cannot
prove action execution on hosted runners.

# Paydirt Release Notes

## v1.10.2

- Improve late multi-score fourth-down urgency using scoring possessions, clock, field position and remaining timeouts.
- Prevent inferred deep interception locations from entering Screen plays; use call-specific modeled fallbacks and enforce source/model support during chart generation. Refresh 259 modeled INT cells while preserving event probabilities and all other outcomes; audit catch locations separately from return yards.
- Speed up validation by reusing unchanged runtime-source expectations and isolated synthetic chart templates, preserving live integrity checks, cases and assertions.
- Publish verified existing release tags without requesting unavailable workflow-write token permissions.

The v1.10.1 historical-source modeling and fit exceptions below remain applicable.

## v1.10.1

- Replace the packaged 1983 and 2024 charts with corrected generated candidates.
- Add chart viewing and gameplay, clock, penalty, and fumble corrections.
- Validate committed charts in CI without requiring hosted private source data.
- Both updated cohorts completed 256 simulated seasons each (132,608 games total).

Known limitations: 1983 uses disclosed modeling assumptions for incomplete records;
712 of 727 fumble events are fitted, with 15 retained but excluded from fitting.
Its strict historical-source completeness remains false. Fixed-bound development
audits retain small completion-rate misses for the 1983 49ers (0.610006 versus
0.642045) and Falcons (0.601726 versus 0.633136), against tolerance 0.03; 2024
Ravens rushing averages 5.339045 versus 5.756318 yards, against tolerance 0.4.
These exceptions remain disclosed; accuracy tolerances have not been widened.
Simulated postseason frequencies are diagnostics, not forecasts or forced results.

## v1.10.0

### Generated Season Charts

- Include all 32 teams from 2024 and all 28 teams from 1983, independently generated from play-by-play and season statistics, alongside the fictional 2026 sample.
- Present the bundled seasons consistently as `seasons/1983`, `seasons/2024`, and `seasons/2026`.
- Distribute concise source, license, and non-endorsement attribution without bundling raw play-by-play or original developer charts.

### Chart Generation and Tuning

- Add play-by-play adapters for nflverse and archived Pro Football Reference records, opponent adjustments, and separate generation and engine-based tuning tools.
- Preserve out-of-bounds markers and special-teams fouls; improve breakaway runs, passing results, sacks, turnovers, and distance-based kicking inputs.
- Document the two-phase generation, tuning, and validation workflow for future seasons. The generated charts are statistical reconstructions, not a guarantee of historical standings or scores.

### Gameplay and Coaching

- Improve CPU penalty choices when a retained gain already earns a first down, and use conversion-specific play selection for two-point attempts.
- Correct incomplete-pass and flagged-play timing, natural out-of-bounds clock stops, spike down costs, and defensive timeout priority.
- Correct modified-overtime matching-field-goal handling, era-dependent missed-field-goal possession, and return-fumble recovery/down handling.
- Improve kickoff and return penalty enforcement, penalty previews, clock evidence, and return-foul narration.

### Browser Reliability and Validation

- Prevent duplicate and stale CPU fourth-down decision requests; preserve the required punt/field-goal confirmation when a decision arrives after a defense click.
- Reject invalid API play calls and conversion attempts without a pending try; correct random-opponent team assignment.
- Expand unit, complete-game, full-season, and AI play-selection regression coverage, including two complete real-engine browser games with a forced fourth-down handoff.
- Synchronize package, API, frontend, and installer version metadata to 1.10.0.

### Validation

- Full local regression passes: 6,776 core tests, 6,759 clean-checkout tests, 280 backend tests, 267 frontend tests, frontend build, both browser checks, and Ruff.
- All fourteen standalone games, fifteen historical reproductions, 224 generated regular-season games, nine untied playoff games, and public/local AI audits (32/32 and 448/448 games) pass. Reviewed play-selection distributions retain the known legacy-balanced advisory on AI-008.
- Existing skips remain: eight in the local core suite, 25 in the clean checkout, and one frontend test. Existing Pydantic deprecations and browser-tooling warnings remain.

## v1.9.5

### Build Reliability and Developer Validation

- Build the frontend with Node.js 24.22.1 and use native Node 24 GitHub Actions.
- Pin test jobs to Ubuntu 24.04 to retain Python 3.9 matrix availability and Playwright support; show dependency installation failures in separate steps.
- Clear the Python lint backlog and add DEBUG traceback diagnostics at optional-operation fallback boundaries, without changing intended gameplay.
- Retain all previous historical regression games and add two corrected-dice supplements that must award and play untimed downs.
- Add scoped OpenCode validation permissions, with pushes requiring approval and destructive commands blocked.
- Synchronize package, API, frontend, and installer version metadata to 1.9.5.

### Validation

- Before release metadata changes, upstream tests and all four standalone builds passed on `254746e` (runs #82 and #97).
- Release-metadata regression: core 5,448 passed (8 existing skips), backend 218, frontend 255 (1 existing skip), build, both browser checks, and Ruff passed. Clean tracked-source checks passed 5,431 core (25 existing private-data skips) and 218 backend.
- All 12 historical cases, 224 regular-season games, nine playoffs, and public/local AI audits (32/32 and 448/448 games) passed; no Hard concentration warning and one existing legacy-balanced advisory. No standings persisted.
- Existing private-data skips, Pydantic deprecations, stale Browserslist data, and npm vulnerabilities remain; dependency vulnerability remediation is not included in this release.

## v1.9.2

### Trace Accuracy and Developer Validation

- Preserve raw punt-return chart cells, so punt-return fumbles display the actual `R:<die>→"F"` result rather than a blank placeholder.
- Preserve the defense-chart row in ordinary fumble traces and omit `Ret:0→0` when no fumble-return chart roll occurred.
- Correctly retain punt-return metadata when resolving a penalty decision after a return fumble.
- Define a full test run in the contributor guide as including the full-season runner and both public and local AI audits, not pytest alone.

### Validation

- Core: 5,420 passed, 8 existing local-data skips; backend: 218; frontend: 255 passed, 1 existing skip; build and Playwright browser games passed.
- Full game runner: 14/14; generated season: 224/224 regular-season games and 9/9 playoff games; historical reproductions: 10/10.
- AI audits reconciled: public 32/32 with no concentration warnings and local 448/448 with four advisory concentration warnings. Private charts and audit reports remain local.

`1.9.2` is a bug-fix and trace-correctness release. The existing `v1.9.1` tag is preserved as immutable history.

## v1.9.1

### Return Rules and Special Teams

- Roll kickoff distance and kickoff return separately; traces now show the real `KO:` and `RT:` rolls, including return rerolls and `RT:none` when a kick is not returned.
- Apply OFF/DEF return-chart penalties consistently across kickoff, punt, interception, fumble-advance, and blocked-kick returns. Return penalties are automatically enforced from the end of the return, with half-the-distance handling and no penalty touchdown.
- Resolve return fumbles with recovery rolls and support chained kickoff/interception/fumble returns. Recovery rolls 17–19 and 37–39 use the interception-return chart; ordinary fumble recovery 39 is no longer an automatic touchdown.
- Nullify offsetting return fouls correctly: re-kick kicks, replay turnover/blocked-kick downs from the previous spot, and consume ten seconds.

### Halftime, Web Flow, and Data Quality

- Make halftime and second-half kickoff ownership engine-owned across CLI, resume, web API, and browser UI; persist the opening kicker in saves and surface `halftime_pending` in web state.
- Correct web kickoff and penalty-decision flows, including final-try game endings and engine-generated return previews.
- Normalize stray source-workbook characters when extracting special-teams CSV cells; blank cells such as the Cardinals Int. Return backtick become zero-yard results with a loader warning.
- Replace the monolithic developer tracker with per-issue files, generated status index, priorities, links, timestamps, resolved/closed lifecycle, and validation tests.

### Validation

- Core: 5,417 passed, 8 existing skips; backend: 218; frontend: 254 passed, 1 existing skip; build and Playwright browser games passed.
- Full game runner: 14/14; generated season: 224/224 regular-season games and 9/9 playoff games; historical reproductions: 10/10.
- AI audits reconciled: public 32/32 and local 448/448. Private charts and play-test logs remain local and are not included in release artifacts.

`1.9.1` is a bug-fix and rules-correctness release; the existing `v1.9.0` tag is preserved as immutable history.

## v1.8.1

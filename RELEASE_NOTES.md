# Paydirt Release Notes

[Play Paydirt in your browser](https://rtulloh.github.io/paydirt/) as the primary
play option; desktop downloads are optional alternatives. Browser games and
seasons save locally in the same browser profile and site. Export important
saves for backup or transfer; internet access is needed to load the engine.

## v1.12.3 — Browser game layout and controls

- The browser game puts play selection, the play log, and game controls in three
  columns on wide screens and stacks them on narrow screens.
- Defense buttons use larger, high-contrast labels. Game controls show a blue
  check for active options, and the play log can expand to show complete history.
- Kickoff and regular-play dice animations take 0.9 seconds.
- Developer issue tracking and release planning now use GitHub.

## v1.12.2 — Complete Windows release packaging

- Require successful Windows installer tooling and package creation before publishing a complete desktop release. The v1.12.1 release omitted `PaydirtSetup.exe` after its installer-tool download failed; its original tag and assets remain unchanged.
- Retain the pinned desktop runtime dependencies and macOS bundle-signature correction from v1.12.1, with the same 90 public teams and browser-first play option. No chart files or gameplay policies change.

The four assets published for v1.12.1 passed their native runtime checks, but
that does not qualify the missing Windows installer. All five actual v1.12.2
downloads now pass native API/UI inventory, independent new-game/chart, clean-log
and shutdown checks. Both Mac bundle resource seals pass, but a fresh quarantined
Apple Silicon download is rejected by Gatekeeper without an override. Applications
remain ad-hoc signed, not Developer ID signed or notarized. Browser play remains
primary; see [verified release qualification](docs/dev-notes/release-1.12.2-readiness.md).

## v1.12.1 — Desktop packaging correction

- Bundle the pinned backend dependencies used by tested installations, correcting the desktop startup failure in v1.12.0.
- Seal and verify the completed macOS app bundle before creating its disk image. This corrects its invalid ad-hoc signature; Developer ID signing and notarization remain unavailable.
- Retain persistent seasons, mixed-year teams, durable saves, sortable team statistics and the kickoff-touchdown recovery improvements described below.

The v1.12.0 desktop packages failed downloaded-artifact startup verification and
remain immutable history. Use the verified v1.12.2 correction. Browser play was unaffected by the dependency mismatch.


## v1.12.0 — Persistent seasons and team statistics

Desktop packages failed post-publication startup verification. Use the corrective
v1.12.2 release with its verified complete package set; the original tag and assets remain immutable.

- Continue to the extra-point choice after kickoff touchdowns, including fumble recoveries; recover an owed try from affected saved games without replaying the touchdown.

- Create and switch between independent seasons, use historical schedules, or build custom leagues with teams from different years. Review division standings, play fixtures, simulate unplayed games and seed postseason brackets from campaign results.
- Save and resume games and seasons across browser sessions, with portable import/export. Installed applications keep their library in application data; browser games use storage for that browser profile and site.
- Choose your coaching side and CPU difficulty before starting a season fixture. Recover pending decisions, possession changes and final results through engine checkpoints without counting a final twice.
- Review sortable team offense, defense and special-teams statistics with compact headers and top-five leader cards. Player statistics are not tracked.

Campaign ranking uses the documented simulated-season tiebreaks, rather than the
complete official NFL procedure. Browser play still requires internet access to
load Python and its packages; browser storage can be cleared by browser settings,
so export important games and seasons. Older saved games can lack newly introduced
statistic counters, which remain unknown rather than becoming fabricated zeros.

No released charts are regenerated or recalibrated. Existing historical accuracy
limitations and the [1977 statistical exceptions](seasons/1977/NOTES.md) remain
applicable. Release qualification includes full gameplay and browser regression,
exact-commit CI, and checks of downloaded published packages. See the
[release evidence](docs/dev-notes/release-1.12.0-readiness.md) for results and
verification limits.

## v1.11.0

- [Play Paydirt directly from GitHub Pages](https://rtulloh.github.io/paydirt/) using the existing Python game engine in your browser. Includes all 90 public teams from 1977, 1983, 2024 and the fictional 2026 sample (FLOW-033).
- Switch seasons without selecting stale teams, and retry failed catalog loads directly from the team-selection screen.
- Resolve human penalty choices before another play can start, including CPU punts and kickoff decisions.
- Preserve the new period's clock and timeout budgets when a late timeout cannot retain playable time in the old period, preventing a skipped third quarter (RULE-032).

Browser play is experimental and requires internet access to load Python and its
packages. Keep the tab open: refreshing or closing it loses the current game.
Browser saves, replays and offline play are not included; use the installed app
for its existing save features. See the [browser guide](docs/web-interface.md).

All released chart files remain unchanged. Existing historical accuracy
limitations and the [1977 statistical exceptions](seasons/1977/NOTES.md) remain
disclosed; this feature does not regenerate or recalibrate seasons.

## v1.10.6

- Make saved-score resume engine-owned: a save records whether a try or free kick is still owed, and resuming never adds touchdown or safety points again. A completed score stays complete, and a kick is consumed only when it is actually taken (FLOW-006).
- Use chart-weighted field-goal make probabilities on the actual kicking chart, combined with situation and season aggression, and keep precision noise out of gameplay dice (AI-024, AI-034).
- Take clock-stopping last-possession fourth downs when trailing late, with overtime and compact-field handling (AI-029).
- Compare offensive fouls against the retained play and enforce made-kick field-goal fouls correctly, with clock-aware penalty previews (AI-002, AI-017, AI-031, AI-033).
- Choose end-zone interception returns during play after the catch location is known, and defer Hail Mary defensive timeouts with that choice (FLOW-023, FLOW-026, FLOW-030, FLOW-031, FLOW-032).
- Resolve safety free-kick penalties before possession, attribute reported defensive timeouts correctly, and distinguish released chart integrity from engine evolution (FLOW-024, FLOW-029, VAL-027).

No charts changed in this cycle. The reviewed 1977 season and its disclosed statistical exceptions remain unchanged, as do the 1983 and 2024 chart bytes. Existing historical accuracy limitations remain disclosed in the season notes.

## v1.10.5

- Correct 1983 geographic labels: San Diego Chargers (`SD`), St. Louis Cardinals (`STL`), and Los Angeles Raiders (`LA`).
- Qualify only those three exact metadata corrections against the immutable v1.10.3 baseline; retain chart, gameplay, source and statistical acceptance requirements.
- Automatically verify downloaded release applications after publication across Windows installer/portable, Linux, and both Mac architectures, including the corrected packaged 1983 labels.
- Add optional `--target-release` issue scheduling and a target-release column in the developer tracker.

Existing historical accuracy limitations remain disclosed in the season notes.
Publication and successful builds alone do not establish native-install acceptance;
review the retained verification receipts and first-launch security limitations.

## v1.10.4

- Add all 28 teams from 1977, generated from reviewed historical records, with era rules and the actual 14-game calendar/eight-team postseason validation.
- Publish explicit source-modeling and accuracy limitations for the new season. The final 72-repetition sample completes all 14,112 games; four team fit misses and elevated scoring remain disclosed in the [1977 season notes](seasons/1977/NOTES.md). Historical winners are never forced.
- Preserve the released 1983/2024 chart bytes and their existing documented exceptions; distinguish unchanged-chart regression from new-chart qualification.
- Strengthen downloaded-package checks for teams, new games, chart identities and normal process shutdown across all five package forms. Restore the missing browser football icon.

The 1977 statistical release exception does not waive source reproduction, chart mechanics, Screen interception constraints, gameplay regression or published-install checks. DATA-046 remains open for historical accuracy work.

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

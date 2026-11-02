---
id: DATA-014
title: Comprehensive chart audit exposes lost source features and biased empirical quantization
status: closed
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - chart-generator
  - reproduced
  - audit
links:
  - DATA-006
  - DATA-011
  - DATA-013
---

## Description

A complete comparison of all 28 generated and locally installed developer 1983 teams identified
several defects that isolated score and season-total checks had missed. Numeric quantiles were
sorted as text, calibrated resolved samples could truncate the season prefix, observed foul types
were replaced by generic penalties, and B reconstruction could drop clock markers or relocate a
fumble into the shared Breakaway chart. Calibrated passing cells could exceed the field length.

Both source adapters could reverse the team charged with a kickoff foul without a return, or
mistake a return ending out of bounds for an illegal kickoff. The nflverse adapter included zero
return placeholders for fair catches and touchbacks in the return distribution. Penalty conversion
lost automatic first downs and treated half-distance enforcement yards as nominal foul yardage.
Supplied blocked-field-goal counts were ignored during chart creation.

The archived 1983 source has no explicit offensive out-of-bounds, fair catch,
blocked field goal, or special snap-fumble annotations. Treating those omissions as zero probability
removes playable mechanisms. This is a source limitation; missing events cannot be reconstructed
as observed plays.

## Resolution / verification

Fix the confirmed transformations and add an automatic structural and feature audit to both source
generation commands. Preserve known inputs; use explicitly recorded modeling defaults for absent
season-wide annotations. The defaults are estimates whose rates are written in the manifest,
not inferred historical event records or copied developer chart cells.

The reusable `python3 -m paydirt.chart_audit` command checks all offense and special-teams columns,
defensive formations/sub-rows, symbols, physical ranges, and touchdown conventions. It reports
weighted feature distributions and all 54 offense-play/defense-formation combinations through the
core priority rules. Reference mode treats legacy blank cells as the engine's zero defaults.
Detailed local comparisons remain ignored. See
[completeness audit](../../generated-chart-completeness-audit.md).

Keep the issue open until the fix is committed. Current season calibration and policy sensitivity
are recorded with DATA-011; DATA-006 preserves the earlier completed input and measurement fixes.
Functional completeness does not establish statistical equivalence.

## Comments

--- 2026-11-02 08:00 ---
Synthetic/public regressions reproduced the conversion, quantization, physical-limit, special-event,
source-foul, and audit-gate defects before implementation. An eight-season matched pilot completed
7,168 actual-schedule games: developer and generated charts, both Hard and balanced policies, using
the same seeds within each comparison. All games completed. Generated Hard output was 24.84 points
and 353.71 yards per team-game versus 19.32 and 288.91 with developer charts. These are policy-dependent
simulation outcomes, not a claim that either set exactly matches the historical season.

--- 2026-11-02 08:50 ---
The complete core suite passed 6,394 tests with eight existing local-data skips. Four additional
failing regressions showed that the new audit initially accepted overlapping, uncovered, reversed,
or out-of-range fumble intervals; the audit now rejects all four. Passing controls include complete
retention/loss and reference blanks with independently complete recovery metadata. The blank-row
fixture now supplies recovery comments so deleting an offense row tests only the intended missing
primary result, rather than also deleting the recovery outcome for roll 39. No expectation was
weakened. Zero-rate controls use matching R/L rows because the engine loader derives absent ranges
from those rows.

Both final chart sets pass structural audits with zero errors or feature-coverage advisories.
All five efficiency targets passed fresh 64-season training, supplying 1,024 games per 1983 team
and 1,088 per 2024 team. The 1983 completion/run profile was slightly adjusted after the pilot;
the 2024 profile was retained. Historical-schedule Hard sanity runs completed 224+9 and 272+13
regular/postseason games respectively, with no tied playoff final.

The generated-schedule play-selection audit completed 448/448 games and reconciled 61,834 calls,
covering scoring penalty choices, incompletions, fumbles and QB-scramble touchdown accounting.
One legacy-balanced third-and-11+ advisory remains under AI-003. Hard had none. Detailed reports
and private reference comparisons remain ignored; held-out 256-season assessments are separate.

--- 2026-11-02 08:59 ---
Final held-out Hard validation completed all 57,344 games for 1983 and 69,632 for 2024,
with 4,096 and 4,352 team-games per team. The verified chart files, manifests, and automatic audit
reports are promoted to seasons/1983-generated and seasons/2024. A fresh source/profile regeneration
reproduces all 180 chart CSVs byte for byte. Only reviewed chart/metadata files were copied;
actual-game sources and private reference artifacts remain ignored.

The final matched developer/generated comparison covers 7,168 games across Hard and balanced
policies using matching seeds. Both fresh 64-season training samples pass all five existing
statistical tolerances. Hard still differs: 1983 scoring/turnovers are 24.50/1.42 per team-game;
2024 is 24.30/0.87. Neither chart set passes every training tolerance under Hard. The completeness
report explicitly retains penalty-frequency, primary pass, B-frequency, QT-fumble, source-annotation,
and coaching-policy limitations. These are not hidden by the structural pass.

Reviewed the resolved-ticket inventory after the audits. The structured generator/AI evidence does
not newly establish the outstanding issue-specific browser, resumed-CLI, commentary, or special
recovery scenarios, so no unrelated resolved ticket is closed from unit tests or ordinary games.
DATA-014 remains open until commit; no commit or push is performed in this audit.

--- 2026-11-02 10:15 ---
Completed manual audit reconciles both teams' scrimmage yardage, sacks, first downs, score, and lost-fumble totals. The single breakaway is non-scoring; all actual touchdowns arise from sufficient yards or genuine return advances rather than field-independent run TD cells. Special-teams fouls occur in both kick and return phases. New engine findings RULE-023/RULE-024, the kickoff preview AUD-026, and unexplained penalty-total gap STAT-005 must be kept separate from generator completeness. No chart or generator changes made during this audit; keep open while uncommitted. See ../../game-audit-2026-11-02.md.

--- 2026-11-02 10:50 ---
Prepared for commit with the documented source/profile regeneration, test-first
regressions and full-game evidence. The November 2 completed manual audit
confirms the relevant generated-chart mechanisms: no field-independent run
TDs, ordinary breakaway resolution, no concentrated interception recurrence,
and both kick and return fouls. Close this specific transformation/coverage
issue on that evidence; statistical fit and coaching limitations remain
documented. The new engine timing changes do not establish a fresh 64/256-season
fit; DATA-011 explicitly distinguishes the earlier fitting evidence.

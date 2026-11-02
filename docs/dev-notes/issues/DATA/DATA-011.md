---
id: DATA-011
title: Chart generation needs a reproducible engine tuning tool
status: resolved
priority: High
created-at: 2026-11-01
resolved-at: 2026-11-02
closed-at:
tags:
  - chart-generator
  - calibration
  - simulation
links:
  - DATA-015
  - DATA-009
  - DATA-010
  - AI-024
  - DATA-012
  - DATA-014
---

## Description

The source generators already accept manual engine-calibration offsets, and the engine exposes a
calibration observer, but the current workflow depends on ad hoc local batch scripts and manual
parameter selection. It is difficult to reproduce, audit, or apply consistently to another season.

Separate baseline chart generation from engine tuning. Source adapters should preserve normalized
play-by-play evidence without translating every source touchdown into a guaranteed chart `TD`.
A second tool should generate candidates, run deterministic engine batches, compare them with
supplied target metrics, select bounded parameter updates, and write a reusable calibration profile.

## Resolution / verification

Implement a standard-library `tune_charts.py` command driven by a local JSON configuration. It
must invoke the PFR or nflverse generator, run a chart-focused pilot policy and held-out Hard-vs-Hard
validation, retain all candidate profiles and metrics, and write the selected profile into the final
generation manifest. Add synthetic/public-2026 unit and integration coverage. Verify the workflow
on 1983 and 2024 local data, then run the final 256-season 2024 assessment before closing.

## Comments

--- 2026-11-01 22:50 ---
The developer-chart audit showed that direct numeric passing gains reach 99 yards while literal
passing `TD` cells are rare and are not explained by a fixed source-yardage threshold. The Colts'
only Short Pass `TD` is a 1/216 cell even though several teams have higher inferred short-pass
touchdown rates. This confirms that guaranteed touchdown symbols belong to residual engine tuning,
not direct source classification.

--- 2026-11-01 22:55 ---
Implemented the first reproducible tuning layer. Both play-by-play generators now accept a JSON
calibration profile, explicit flags override individual profile fields, and manifests record the
effective profile. `tune_charts.py` enforces complete per-team samples, evaluates tolerance-scaled
engine metrics, makes one bounded coordinate-descent update at a time, retains candidate history,
and validates the best candidate with a separate seed. The standard plan is 64 training seasons
(1,024 team-games for 1983; 1,088 for 2024) and 256 held-out validation seasons. The issue remains
open pending the local chart-focused and Hard-vs-Hard 1983/2024 runs and sparse touchdown-symbol
work.

--- 2026-11-01 22:58 ---
The new profile, tuner, observer, generator-command, documentation, and tracker tests pass. The
complete core unit suite also passes: 6,349 passed and 8 existing data-dependent skips. Ruff and
`git diff --check` pass for the tuning changes. No 64-season training or 256-season held-out
historical run has been performed yet, so DATA-011 remains open.


--- 2026-11-01 23:35 ---
Historical verification is complete. The tuner ran 64 chart-focused training seasons and 256
held-out Hard-vs-Hard validation seasons for both 1983 and 2024, providing 1,024/1,088 training
team-games and 4,096/4,352 validation team-games per team. All configured training metrics met
tolerance and every validation game completed. The selected profiles are recorded in the promoted
generation manifests. Hard strategy produced material policy sensitivity, especially fewer 1983
interceptions and sacks and higher 2024 passing yardage; those differences remain diagnostics rather
than additional chart targets.

The promoted sets pass result-symbol validation, contain no direct run gain above 18 yards, and
completed focused historical-schedule sanity runs: 224 regular-season plus nine postseason games for
1983, and 272 plus 13 for 2024. Manual playtesting may begin. Keep this issue open until the current
implementation and generated outputs are committed; sparse guaranteed touchdown-symbol tuning also
remains intentionally deferred.

--- 2026-11-02 08:50 ---
The comprehensive DATA-014 generator corrections required renewed calibration rather than relying
on the previous profile's evidence. Fresh 64-season chart-focused training passes all five existing
tolerances for both final candidates: 1,024 team-games per 1983 team and 1,088 per 2024 team.
The revised 1983 completion adjustment is -0.06 and rushing multiplier 1.025; its other parameters
and the full 2024 profile are unchanged. Separate 256-season Hard validation is being recorded with
the completeness audit. Scoring and pace remain diagnostics and AI-024 still tracks era-sensitive
field-goal decisions. Keep open pending commit.

--- 2026-11-02 08:59 ---
Renewed held-out validation is complete for the final DATA-014 candidates: 57,344 Hard
games in 1983 and 69,632 in 2024, with complete 4,096/4,352 per-team samples. Both fresh 64-season
training reports pass their existing five tolerances. All final chart files reproduce from source
and profile, and both historical-schedule postseason sanity runs complete. The selected files are
promoted, but Hard event rates and efficiency do not all meet the chart-focused tolerances.
Remaining measured differences are listed in the completeness audit; passing sample counts is not
a claim of historical fit. Keep open pending commit, with the documented calibration limitations.

--- 2026-11-02 10:50 ---
The reproducible tuning tool and promoted source/profile outputs are prepared for commit. The intentionally deferred sparse symbolic-TD experiment is now DATA-015. The recorded 64/256-season fitting evidence predates the new RULE-022/RULE-023 engine timing; it remains historical evidence, not a fresh fit claim for the current engine. Current full-game and AI audits validate completion and selection, not renewed season-statistic tolerances.

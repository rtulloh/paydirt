---
id: DATA-032
title: Punt snap-fumble routing fixed; final closing review pending
status: resolved
priority: High
created-at: 2026-11-06
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
  - chart-audit
links:
  - DATA-034
---


## Current audit — 2026-11-08

The committed engine routes original punt F tokens through snap-fumble resolution, including the first nonpenalty reroll after a kick foul; pending choices preserve the result and resolve it only when appropriate. Current punt snap-fumble regressions pass. Earlier recorded natural-game campaigns include 496-game cohorts and the larger exposure census, so this is no longer an unimplemented forty-yard fallback defect. Mark resolved, not closed pending a current issue-specific final play-test/binding review. Statistical-credit fidelity and broad source-fit acceptance remain separate DATA-030 concerns; do not reimplement the routing fix.

The original investigation and checkpoints below are retained as history.

## Description

The raw decoder investigation exposes a missing consumer branch: a punt-column
`F` or signed `F` token reaches numeric conversion, fails, and becomes a normal
40-yard punt. A positive sign can additionally be mistaken for a downed marker.
This discards the fumble location, recovery, fourth-down result and possible
score. All 60 current public generated candidates contain modeled punt snap
fumbles. Across equally weighted team charts, the exact physical exposure is
75/6,048 (1983, 28 teams) and 94/6,912 (2024, 32 teams) per punt lookup. These
are chart probabilities, not observed game frequencies or historical targets.

The existing generated-source check verifies symbol presence, but does not
exercise this actual consumer. Its earlier component passes therefore do not
establish punt-fumble mechanics. Old simulation reports preserve the defective
behavior and cannot certify the corrected runtime.

## Resolution / verification

Route the original token to the shared fumble resolver before stripping punt
markers or applying coffin-corner distance. Verify own/lost recovery, downs,
ordinary fumble returns, scoring, nullified return fouls and real-punt controls.
Track the aborted snap as a scrimmage rushing attempt rather than a punt-return
event. Keep physical movement distinct from the still-open statistical-credit
question; the existing board-game fumble convention does not establish exact
NFL credited rushing/fumble yardage or individual recovery identity.

The [NFL statistician guide](https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf),
pages 19 and 27–28, separates an actual punt from an aborted snap and distinguishes
rushing credit from loose-ball movement. This source does not itself establish
historical board-game token semantics or resolve the broader credit design.

## Comments

--- 2026-11-06 01:31 ---
Test-first baseline: 26 expected gameplay failures and 125 passing controls,
including eight new real-punt controls and the existing punt suite. Fixtures use
public 2026 teams with synthetic cells only. Full local evidence and candidate
hashes remain in ignored chart-confidence storage. No prior test expectation or
skip was changed. Release remains held; no new reference or reserved-seed data
was opened.

--- 2026-11-06 01:38 ---
Initial snap-fumble routing now passes 175 focused punt/fumble tests. The engine
preserves the original signed token, uses the shared recovery resolver and emits
an explicit snap-fumble fact. The observer counts a retained aborted snap as one
rushing attempt; pending/nullified plays do not count. No general fumble-yardage
credit design is changed. The special punt branch does not credit loose-ball
movement as rushing/passing yards; unknown individual recovery identity remains
a statistical limitation, not an accurate-NFL-credit claim.

Gate controls for real punts and snap fumbles reject an erased count and a
restored forty-yard fallback. Four expected gate failures precede the fix; all
160 directly affected gate/calibration/punt tests then pass. An initial fixture
attempt patched runtime code and was correctly rejected by the loaded-identity
guard; the corrected fixture changes synthetic chart bytes before execution.
The existing conformance-count assertion changes from 12 to 14 because two
meaningful controls were added, without changing their expected behavior.

Fresh training-only play confirmation completes 224/272 games, with 31/46
retained punt snap fumbles and 71,346 ordered calls. All game/accounting checks
pass at runtime `820c4fc3…`. This is one schedule per cohort, below final exposure,
and does not certify the pending statistical-credit design or historical fit.
The current charts are unchanged; previous runtime reports remain historical.

A separate synthetic diagnostic confirms the kick-foul reroll loop still skips
a snap-fumble reroll and substitutes later numeric punt distance, after either
OFF or DEF. This is additional required work under this issue. Accepted/declined
kick fouls, remaining snap-credit interpretation, full regression and final
review prevent closure. The 32 resolved and 42 closed records were reviewed;
the new ordered receipts do not independently confirm unrelated narrative,
interactive or rare-event closure criteria. No additional ticket is closed.

--- 2026-11-06 01:56 ---
The additional foul-reroll branch is now corrected locally. Its test-first
baseline had 28 expected failures and 117 passing punt controls. The first
nonpenalty fumble is retained as the pending choice; no recovery, possession,
score or clock change occurs before that choice. Declining resolves the stored
fumble. Accepting enforces the original foul through the shared penalty resolver,
reports the applied penalty, and preserves defensive untimed-down handling.
The engine supplies both choice previews; the CLI displays them directly.

Further failing controls exposed missing half-extension handling, missing choice
previews, an incorrect negative-punt headline, and provisional turnover flags.
All 397 directly affected gameplay/display/audit tests now pass. The conformance
count increases from 14 to 18 for four accepted/declined OFF/DEF controls. The
only changes to prior test expectations are the added conformance-case counts
(12 to 14 to 18); existing behavior assertions and skips remain intact. Two new
fixtures were corrected to use legal goal-to-go distance and the established
`2nd & 13` formatting. Formatter compatibility failures against existing mock
fixtures were fixed in production code without changing those tests.

A fresh training-only schedule at runtime `1bfd47d6…` completes all 224/272
games with 34/48 retained snap fumbles. Both strict game/accounting validations
pass. The earlier 496-game report at `820c4fc3…` remains historical evidence,
not current-runtime validation. This is still one repetition per cohort, below
the charter's required exposure. Full core regression is running; backend tests
pass 322 with 21 existing Pydantic deprecation warnings. Physical versus credited
fumble yardage and other kick branches remain open; do not infer closure or
historical accuracy from these mechanism checks.

--- 2026-11-06 02:17 ---
The subsequent return-penalty first-down correction changes runtime to
`871af55a…`. The expanded 1,063-case focused suite includes the snap and foul-
reroll cases and passes. Fresh source-schedule play again completes all 496
games, with 82 retained snap fumbles and reconciled accounting; prior runtime
reports stay historical. Source reproduction/raw decoding also passes all 60
unchanged candidates with new current bindings. This remains one training
repetition, not final statistical exposure. RULE-027 tracks newly reproduced
cross-chart punt-foul choice/replay-timing gaps. Full regression on the eventual
stable runtime and the remaining credit/combination work prevent closure.

--- 2026-11-06 02:38 ---
Fresh runtime `671f712b…` completes all 496 development games with 83 retained natural punt snap fumbles and reconciled accounting. The core checkpoint passes 8,405/eight existing skips (83% coverage), and backend passes 322 with 20 existing Pydantic warnings. Keep open through DATA-034 retained-kick combinations, remaining foul mechanics, final exposure and DATA-030 credit review; the new test/data coverage does not close those requirements.

--- 2026-11-06 03:43 ---
A fixed 64-repetition current development census completes all 14,336/17,408
games with reconciled full-game accounting and 4,702/3,714 own-fumble advances.
Four advances short of the sticks preserve accepted defensive first-down rights,
including two decisive second-down examples; DATA-033 records that targeted proof.
This read-only wrapped census adds no dice or state changes, but is not final
unwrapped worker attestation, source-credit reconciliation or final source fit.
DATA-030's model review remains pending, and DATA-035 independently exposes five
interception-return fumbles misattributed by the modern source adapter. Keep this
broader source/credit acceptance issue open. Original runtime for these games is
`f0cfc25a…`; subsequent adapter changes require fresh candidate bindings.

--- 2026-11-08 17:08 ---
The committed engine routes original punt F tokens through snap-fumble resolution, including the first nonpenalty reroll after a kick foul; pending choices preserve the result and resolve it only when appropriate. Current punt snap-fumble regressions pass. Earlier recorded natural-game campaigns include 496-game cohorts and the larger exposure census, so this is no longer an unimplemented forty-yard fallback defect. Mark resolved, not closed pending a current issue-specific final play-test/binding review. Statistical-credit fidelity and broad source-fit acceptance remain separate DATA-030 concerns; do not reimplement the routing fix.

Reviewed current committed implementation and existing issue evidence. Fresh
focused validation: 239 gameplay/ownership/source/runner/standings checks and
417 parser/reconciliation/generation/source-bundle checks pass, without skips
or warnings. These focused checks are not full regression or new season runs.
See [high-priority audit](../../high-priority-issue-audit-2026-11-08.md).

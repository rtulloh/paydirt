---
id: DATA-046
title: 1977 candidate misses Washington interception fit and overstates scoring
status: open
priority: Medium
created-at: 2026-11-08
resolved-at:
closed-at:
tags:
  - reproduced
  - v1.10.4
---

## Description

The staged 1977 candidate-05 is reproducible and source-consistent within its
explicit incomplete-source scope, but is not qualified for normal bundling.
A fixed 144-repetition source-calendar chart-focused run completes all 28,224
games and 2,016 team-games per team. All five league metrics and 139/140 team
metrics pass unchanged bounds. Washington throws 3,217 interceptions on 60,728
attempts: rate 0.0529739165 versus source 0.0417754569, error 0.0111984596
against the existing 0.010 tolerance. The first 72 replication summaries exactly
match the preserved prior run; no favorable-seed selection or threshold change
occurred. Tampa Bay's earlier near-boundary miss clears at the larger sample.

Joint scoring is also elevated at 20.1085 versus historical 17.1760 points per
team-game. Scoring is currently diagnostic, not one of the five fitted rates.
Similar yardage and slightly lower play volume in earlier comparisons do not
establish a pace defect; the chart-focused policy's passing/field-position mix
requires separate analysis. Do not infer that this already proves a gameplay bug.

See [1977 feasibility](../../1977-season-feasibility.md) and the current
[release plan](../../release-1.10.4-plan.md). Detailed receipts, source pages,
strict ledgers and narrative logs remain ignored under `.ai-audits/`.

## Resolution / verification

Do not publish this candidate as fit-qualified, waive the unchanged bound,
hand-tune Washington, force historical qualifiers, or keep increasing sample
sizes until a favorable result appears. The bounded numerical pass has ended.
Investigate complete-cohort interception allocation and source-to-engine event
mapping under fixed situations, distinguishing finite allocation, play/defense
mixture and source coverage. Establish any concrete production defect with
synthetic/public-2026 failing tests before changing behavior. Preserve event
probabilities and interception-distance constraints unless an explicitly tested,
reviewed correction is justified. Re-run independent source/reproduction,
unchanged fit qualification and complete historical calendar after a correction;
review scoring and team ordering without forcing historical outcomes.

A different release scope or explicitly experimental-season policy is a
consequential owner decision, not an implicit accuracy exception.

## Comments

--- 2026-11-08 22:29 ---
Recorded final bounded candidate result. No 1977 files bundled, no release tag
created, and no source facts or acceptance thresholds changed. Independent
integration regression and native Windows verification continue separately.

--- 2026-11-09 04:15 ---

Candidate-06's owner-authorized global interception-only diagnostic completed
3,136 games (16 repetitions / 224 team-games). All five league bounds pass and
league INT fell 5.972% to 5.571%, but four team estimates miss unchanged bounds:
49ers/Buccaneers completion high; Chiefs/Jets interception low. Exact values,
attempt denominators and methodological limits are in the
[canonical feasibility note](../../1977-season-feasibility.md#candidate-06-isolated-interception-diagnostic-not-qualification).
The ignored wrapper preserves candidate-05's gain recipe and source identity,
with medium review and five synthetic controls, but is not a canonical source
qualification mechanism. Candidate-05 remains unchanged. No further tuning or
72/144 extension started; DATA-046 remains open. No new season is qualified.

--- 2026-11-09 04:34 ---
Finite global search finished at five new trials. Candidate-05 remains best
including both references (zero team misses in the shared 16-repetition screening
batch); no new trial beats it. Its retained 144-run Washington miss still FAILS
strict fit, and elevated scoring remains a diagnostic limitation. The owner now
permits a hash-bound, disclosed statistical release exception after all other
requirements; this does not resolve DATA-046's underlying accuracy concerns.
No individual-team transformation or extra global trial was implemented. See the
[complete ranking/method/status](../../1977-season-feasibility.md#finite-global-search-completed-candidate-05-nominated)
and [owner goal](../../1977-calibration-release-goal.md). An unused-seed diagnostic
is separate robustness context, not a new qualification loop.

--- 2026-11-09 04:38 ---
One predeclared unused-seed batch (20261109), unchanged candidate-05, completed
3,136 games. Washington INT remains high (5.2278% versus 4.1775% target±1pp);
Dallas/Denver also cross upper bounds in this smaller 224-team-game diagnostic,
although they pass in the retained 144-run report. Washington's new/prior means
differ by 0.313 combined SE. This is robustness context, not replacement
qualification or a proven chart-specific mechanism. No chart edit, pooling,
extension or seed shopping was performed. Both reports remain immutable and the
full table/uncertainty is in the
[canonical record](../../1977-season-feasibility.md#independent-seed-robustness-check-no-individual-chart-edit).
Underlying accuracy work remains open despite authorized disclosed release
acceptance. No individual correction is justified just to flip a test.

--- 2026-11-09 05:15 ---
Final current-runtime canonical regeneration and independent reproduction match
all 84 CSVs and the full manifest, with unchanged candidate-05 chart bytes. The
predeclared seed 20261110 / 72 repetitions completed 14,112 games (1,008 per team).
All source, reproduction, mechanics, allocation, observer and nonstatistical
requirements pass; all five league fit metrics pass. Strict fit retains four
misses: Tampa Bay completion 43.9668% versus 40.8100% ±3pp; Tampa Bay INT 8.2150%
versus 9.3458% ±1pp; Dallas INT 3.7742% versus 2.6882% ±1pp; Washington INT 5.2661%
versus 4.1775% ±1pp. Scoring remains elevated at 20.1034 versus 17.1760 historical
points per team game. The earlier 144/independent reports remain preserved, not
replaced or pooled. No chart correction or further tuning was applied. The
owner-authorized exact release exception is being reviewed; this ticket remains
open because releasing with disclosed limits does not resolve accuracy.

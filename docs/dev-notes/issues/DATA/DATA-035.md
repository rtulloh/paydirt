---
id: DATA-035
title: Interception-return fumbles are credited to the original offense
status: open
priority: High
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - source-coverage
links:
  - DATA-030
  - DATA-036
---

## Description

The nflverse adapter records a retained scrimmage row's global fumble flag as an
offensive passing/rushing fumble before inspecting interception-return ownership.
Five public 2024 interception rows explicitly name the return team as the fumbling
team, but can enter original-offense passing-fumble calibration. Their actual
interception/return representations must remain intact; excluding these facts
from offensive calibration is separate from DATA-030's physical/credited gain
model. Unknown or multiple-side ownership must remain unsupported rather than
being silently attributed to the original offense.

## Resolution / verification

Add synthetic regressions before production changes for known returners, absent
return-team labels with defensive-team fallback, known retained/lost recovery,
missing/contradictory ownership and multiple-fumble sequences. Preserve ordinary
rushing/completion/sack fumbles. Reconcile every affected public source event,
calibration counts and regenerated candidate/provenance impact. Refresh relevant
source and engine evidence before closure; a shared-source count match alone is
not independent event truth.

## Comments

--- 2026-11-06 03:41 ---
The first new test draft produces eleven failures and three ordinary-fumble
controls. Four failures stop on an incorrect draft Short Pass expectation for
12 air yards; the established heuristic selects Medium Pass. Correct that new
fixture before recording the actual ownership baseline. No production code or
existing test expectation has changed. The source-credit proxy proposal remains
unimplemented and pending review.

--- 2026-11-06 03:43 ---
After correcting the new draft's pass-family expectation, the unchanged parser
fails all eleven ownership/unsupported-sequence cases with three ordinary-fumble
controls passing. All four returner controls first preserve their exact existing
INT and return-F representations, then fail on false offensive attribution.
The raw public census confirms all five erroneous offensive entries, one falsely
lost; the old offensive ledger contains 536 events. Four additional non-INT rows
contain multiple fumbles and remain a separate multiplicity/credit review, not a
single-fumble empirical truth claim. The narrow correction now excludes only
explicitly identified interception-return fumbles from offensive calibration;
unknown or compound interception-fumble sequences are unsupported. Recovery
capability checks remain intact. Regeneration/impact and validation are pending.

--- 2026-11-06 03:48 ---
The first post-fix source/generator suite passes 126 checks. Reclassification of
the actual unchanged public input removes exactly five false offensive events
(536 to 531), including one false offensive loss, and preserves every affected
INT/return representation. DATA-036 then independently blocks the four compound
rows rather than claiming a complete calibrated total from a partial ledger.
The combined ownership/guard/source preparation suite passes 275 checks; no
existing behavioral expectation changes. Full core refresh is pending. Current
2024 maintained source preparation correctly exits one with four ownership
support failures, so byte reproduction/regeneration cannot yet be claimed.
Keep this ticket open through the corrected source/generation checkpoint.

--- 2026-11-06 03:57 ---
The stable current-adapter core regression passes 8,904 tests with 83% coverage
and eight existing data-dependent skips. Ruff passes and all 275 focused source
checks pass. Actual public-input review names the original offense as the first
fumbler for each of the 527 accepted partial-ledger entries. This strengthens the
ownership correction without certifying gain/credit or the four excluded compound
rows. Corrected 2024 generation remains blocked before fitting; keep open.

--- 2026-11-06 04:12 ---
The stable name-marker follow-up runtime passes the complete core suite: 8,920
tests, eight existing data-dependent skips, 83% coverage, 462.53 seconds. The 291
focused source checks and Ruff pass; all 43 ownership checks pass in a fresh
public-only copy. Fresh 1983 source preparation reproduces 84 CSVs. Fresh 2024
preparation still fails on four compound rows, so corrected all-team regeneration
and this ticket's closing checkpoint remain unmet. No model approval or release.


--- 2026-11-06 11:19 ---

The historical four-compound checkpoint above is superseded by the complete
five-play screen. The ordered ledger now records the interception-return origin
and its fumble separately; a synthetic diagnostic control allocates that fumble
once to the shared population, with no original-offense passing fumble. The
five compound plays and a blocked-return fumble have eleven reviewed diagnostic
events, but the shared chart's actual consumer exposures and residual review
remain outstanding. The five-compound generation guard stays closed. Source
component tests do not supply fresh all-team or full-game closing evidence, so
this issue stays open.

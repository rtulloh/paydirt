---
id: RULE-030
title: Own-end-zone interceptions lack the permitted coaching return choice
status: open
priority: High
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-audit
---

## Description

Rule VI-12-F-i permits a team gaining possession in its own end zone to elect
an automatic touchback or attempt a return while counting end-zone depth.
The interception handler always took the touchback, so that legal choice
was unavailable to either coach. F-ii also prohibits return or recovery after
the ball reaches the own end line; an end-line return fumble previously drew
recovery dice.

## Resolution / verification

The local implementation uses a pre-game preference for each team, defaulting
to automatic touchback. Browser setup and the new-game API expose human and
CPU preferences; core and browser saves preserve the mapped home/away choices.
Attempts use the existing return chain, nine-yard catch cap, recovery and
foul procedures. Own-end-line fumbles stop before recovery dice. Raw
interceptions on the offense end line remain the separate RULE-029 safety.

Keep open pending issue-specific play-test evidence and the required final
frozen-candidate regression. Representing this rule does not establish which
historical interceptions elected a return, supply missing dice entitlements,
accept source fits, or determine unknown conditional gain/loss targets.

## Comments

--- 2026-11-06 19:10 ---
Test-first public/synthetic baselines: 73 failures with 43 passing core/boundary
controls; eight API failures with one legacy-save control; four isolated
end-line fumble failures with two live end-zone recovery controls. Nine further
setter/failed-escape foul tests failed for the absent setter and forced
touchback. The initial focused core suite passed 131 cases and the API suite
passed nine, with no existing expectation or skip changed at that stage.

Further test-first cache checks reproduced 20 failures with eight controls:
zero-gain numeric caches rerolled, and net yards discarded resolved fumble
possession or foul counters. The result now keeps its complete typed return
chain; rollback/reapply preserves the chain and counters. Four additional
idempotence assertions reproduced duplicate narration before correction.
The focused boundary/return/save suite now passes 360 cases, and the new API
suite passes ten, including live pending serialization and completed replay
round trips. Unresolved penalty choices are not persisted by existing save
formats; this change adds no pending-save resume claim.

Five parameter cases in test_blocked_kick_return_fumble_safety_propagates_to_outcome
(punt 17/37, field_goal 17/37, snap 37) removed only the final recovery die after
an out-of-play end-line fumble. Their previous draw expectation contradicted
VI-12-D-iii/F-ii; scoring, possession, spot and narration assertions stay.
The backend modifier fixture now uses a deterministic public-team kickoff to
establish its required offense state rather than failing randomly on a kickoff
foul/turnover. Its offense assertion stays. No skips added.

The partial full core run was interrupted before final integration and does
not qualify the final runtime. The final full regression remains the owner's
integration step after all production edits converge. Historical source census
and exposure receipts stay untouched and retain their original runtime hashes.
Receipts stay ignored under release-readiness/end-zone-interception-policy-01
and return-model-resolution-01. No new full-game evidence authorizes closing
this or unrelated issues.

--- 2026-11-06 19:29 ---
Qualification ownership clarification: the parent agent performs the remaining
integrated regression, frozen-candidate audit campaigns, binding refresh and
issue-specific play-test confirmation after production edits converge. The
phrase "owner's integration step" above refers to that parent-agent work, not
an exhaustive validation assignment for the human owner. The human owner gets
the compact visual review and release decision. Existing receipts remain
immutable, and this clarification supplies no new fit or closure evidence.

# November 6 web game audit

Status: local observations and public-policy reproductions; no gameplay changes
or release qualification. Private play records remain in ignored `.ai-audits/`.

The owner's completed, resumed Medium-opponent game ended 19–10, Q4, zero time,
with no pending PAT or kickoff. Its browser contains 162 display entries: 105
loaded and 57 resumed, including decisions and special teams. These are not
162 scrimmage plays. No full-game statistics reconciliation is claimed.

## Timeout finding

The trailing CPU had no timeouts on its final possession with 44 seconds left.
It used all three on defense, on plays starting at 3:28, 3:18 and 3:08 in Q4;
the third completed with 2:58 exposed by the API. Three descriptions explicitly
report defensive timeouts and the final backend budget is zero. The human
budget remains three; the scoreboard displays only the human budget.

This confirms [AI-027](issues/AI/AI-027.md)'s defensive timeout integration for
this game. The final-minute absence is consistent with the exhausted budget;
it does not prove every timeout timing choice is optimal.

## Coaching findings

- Down nine with 3:37 remaining, the CPU punted on fourth-and-five at its own
  16. The 2–5-minute fourth-down branch falls through to conservative punting
  here. Matching public-2026 Medium probes returned punt for all 100 seeds.
  This repeats the own-territory urgency concern in
  [AI-003](issues/AI/AI-003.md) and [AI-006](issues/AI/AI-006.md), without
  establishing a universal go-for-it rule or conversion probabilities.
  The individual follow-up is [AI-028](issues/AI/AI-028.md).
- Down nine with 18 seconds left, it selected Line Plunge on fourth-and-two at
  its own 28, gained five yards and ran out of time. The conversion mixture
  runs before the two-minute-drill branch without assessing the distance
  needed for the remaining scores. Public probes reproduce that mixture:
  78 runs and 22 short passes in 100 seeds. These are selection counts, not
  winning probabilities or a required replacement distribution.
  The individual follow-up is [AI-029](issues/AI/AI-029.md).
- At 4:40, down nine, an ordinary second-down selection did not conserve time.
  Public modern behavior settings give `_needs_hurry_up=True` and
  `_is_two_minute_drill=False`; all 100 probes leave no-huddle false. This
  independently reproduces [AI-020](issues/AI/AI-020.md). The controller cannot
  forward an option the AI never sets.

On the final possession, each of two incompletions is followed five seconds
later, and an eight-yard completion is followed 16 seconds later. These
intervals do not indicate an unspent timeout or the old full-runoff
incompletion defect.

## Save/resume and evidence limits

The loader creates a fresh engine with partial restoration, so final engine
statistics describe the resumed portion rather than the entire browser history.
The backend replay export contains only the 105 loaded entries; the browser
holds 162. This adds real-game evidence to [FLOW-008](issues/FLOW/FLOW-008.md).
A display log does not satisfy [TRACE-005](issues/TRACE/TRACE-005.md)'s
deterministic replay requirements.

A retained QB-fumble case has consistent negative net yardage, named recovery
spots and a correct detailed net-loss explanation, but its short headline uses
unsigned yardage. The wording ambiguity is recorded under
[AUD-005](issues/AUD/AUD-005.md); no engine yardage correction is inferred.

## Ticket review and validation

[AI-005](issues/AI/AI-005.md) remains resolved pending broader difficulty
comparison; one Medium game confirms only the observed timeout accounting.
AI-006 remains resolved rather than closed because the urgency concern
persists. AUD-005 remains resolved pending broader wording confirmation.
AI-027 has issue-specific play-test confirmation but remains open while its
local fix is uncommitted and publication checks remain outstanding. Policy
probes alone close no ticket.

This audit changes documentation only. Player guides require no update because
no supported controls, rules or behavior changed. Documentation and tracker
checks validate this note and its comments; they do not qualify a release.

---
id: RULE-023
title: Numeric defensive adjustments suppress natural out-of-bounds clock stops
status: closed
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - reproduced
  - clock
---

## Description

The latest completed manual game contains two marked in-bounds-to-sideline
run results inside Q4's last five minutes whose numeric defensive adjustments
do not overrule the offensive result. Their two-yard gains consume 29 and
35 seconds rather than the documented ten-second out-of-bounds charge.
The final yardage does not include the five-yard in-bounds designation cost.
Original narrative and charts remain local.

Both `run_play` and `_apply_play_result` clear `is_out_of_bounds` whenever
`result.defense_modifier` is nonempty, including an ordinary numeric addition
or subtraction. The marker survives the priority resolver, but its clock
effect is removed. `_apply_requested_spike` repeats the same nonempty-string
test when deciding whether a natural clock stop made a spike unnecessary.

## Resolution / verification

The priority resolver retains sideline markers only when the offensive
result survives; numeric defensive additions/subtractions preserve them.
Both engine execution paths and spike eligibility now consume that retained
marker instead of treating any nonempty defensive cell as an overrule.

Test-first baseline: 34 expected failures and 31 passing controls. Coverage
includes direct/procedure/declined choices, both teams, actual overruling
categories, half windows and warnings. The two former tests that expected
an overruling result to retain the offensive marker were corrected. The
64-game public audit observed 68 retained late-window sideline stops with
synthetic marked run cells. Flagged plays follow RULE-022 action time.

## Comments

--- 2026-11-02 10:15 ---
Confirmed during the complete manual audit. Two captured late-quarter
examples independently demonstrate the issue; public synthetic positive
and negative controls isolate the cause. Keep open pending test-first fix,
commit, and issue-specific full-game confirmation.

--- 2026-11-02 10:50 ---
Included in the pending local fix commit. Issue-specific full-game evidence
is recorded above; private charts and narrative logs remain ignored.

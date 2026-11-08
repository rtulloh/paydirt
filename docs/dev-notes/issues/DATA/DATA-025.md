---
id: DATA-025
title: Opponent adjustment treats return and sack prose as primary passing gains
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
---

## Description

Independent Astra review reproduced narrative contamination in `_result_yards`.
Two synthetic offenses each face two defenses with twenty ten-yard completions
and twenty interceptions per matchup. Changing only one defense's interception
return description from zero to eighty yards changes adjusted completion results
from forty ten-yard gains per offense to twenty 25-yard and twenty minus-five-yard
gains. Primary QT sack prose similarly enters the completion yard model as an
unsigned gain. Both source generators call this opponent-adjustment path.

## Resolution / verification

Seven new regressions fail before the first local guard; ten controls pass.
The controls preserve signed numeric QB Time gains/losses, primary fumble initial
gains, and existing additive-model behavior. A first symbol-family guard passes
94 focused tests including source classification and gate checks. This does not
resolve unknown primary TD/B gain support: arbitrary return/recovery/penalty prose
must not become initial gain, and unknown retained completion yards must not be
coerced to zero in official passing-YPA fitting. Further regressions precede that
follow-up. Preserve official targets, event counts and fixed acceptance bounds.

Full source regeneration, exact reproduction, larger training and the complete
charter remain required. No gain normalization or chart-layout implementation is
authorized by this finding; no public candidate promotion. Keep open.

## Comments

--- 2026-11-05 21:12 ---
The follow-up now accepts only normalized numeric/initial-fumble gains (plus
explicit zero-yard sacks), with INC/INT contributing zero credited pass yards.
Arbitrary TD/B/recovery/return/penalty prose is never a gain fallback. Unknown
retained TD/B initial gains fail explicitly. Twelve further expected baseline
failures preceded this guard; 136 integrated focused tests passed afterward.
The just-added prose-only TD expectation changed from 25 to unknown; a numeric
25-yard TD control preserves supported source behavior. Final regeneration and
whole-engine fit remain outstanding.

--- 2026-11-05 21:00 ---
Parent independently reproduced the same two-offense/two-defense contamination.
This is a confirmed modeling defect, distinct from the proposed source-driven
gain normalization and from final historical accuracy. Reserved seeds and the
prospective transfer season remain unopened.

--- 2026-11-05 21:50 ---
A separate PFR source-layer reproduction finds recovery-return yards replacing
missing or explicit-zero initial fumble gain. Rushing events mentioning a return
TD also lose their fumble occurrence because the touchdown branch wins first.
Eight new cases fail with 85 passing PFR controls (including a root command that
incorrectly issues a manifest despite missing required initial gain). Initial
extraction now stops before fumble/recovery/enforcement text; completed/rushing
fumble occurrences survive unknown gain and return scores. Missing required gain
is retained as a typed unsupported identity and blocks root generation, rather
than becoming a return-yard token or silently disappearing. All 93 focused PFR
cases pass. No existing expectation or target changes; fresh whole-source and
integrated checks are recorded separately.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Initial-gain fitting/parsing guards are committed and unknown required gains fail explicitly; complete source/integrated confirmation remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

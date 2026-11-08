---
id: DATA-037
title: Reference decoder accepts signed defensive fumbles absent from priority table
status: resolved
priority: Medium
created-at: 2026-11-06
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - chart-audit
---

## Description

The normalized reference decoder reports signed defensive F tokens as supported.
The core priority table has defensive entries for bare F only. Categorizing
synthetic defensive `F + 3` or `F - 3` therefore reaches the missing-pair offense
fallback; for example offensive `INT 10` becomes a numeric ten-yard result.
Recognizing the token grammar does not establish supported fumble semantics.
This finding uses synthetic cells only; no private corpus incidence is claimed.

## Resolution / verification

Reject signed defensive F cells in reference decoder preflight. Preserve signed
offensive F and bare defensive F, whose pending spot uses the offensive gain.
Do not invent signed defensive game rules or change gameplay priority without
a reviewed rule and test-first engine regressions. A full actual corpus audit
must establish decoder coverage before reference acceptance. Keep open pending
that integration evidence and review of any actual unsupported cells.

## Comments

--- 2026-11-06 05:34 ---
Two new decoder regressions fail on the unchanged decoder, with ten exact
enumerator controls passing. The preflight now rejects both signed defensive
forms. One newly added synthetic exact-enumerator fixture had assumed a signed
defensive rule and a minus-three-yard fumble spot; it is corrected to bare F and
the core's offensive ten-yard pending spot. No existing repository expectation
is changed. This correction does not certify actual private charts or gameplay.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Signed defensive F rejection is committed in reference-decoder preflight; complete actual-corpus integration remains pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

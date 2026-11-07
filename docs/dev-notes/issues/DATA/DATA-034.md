---
id: DATA-034
title: Punt-foul rerolls discard retained kick classes and markers
status: closed
priority: High
created-at: 2026-11-06
resolved-at: 2026-11-06
closed-at: 2026-11-06
tags:
  - reproduced
  - chart-audit
links:
  - DATA-032
  - RULE-027
---

## Description

After a punt-chart foul, the first nonpenalty kick result must retain its
meaning. The numeric-distance reroll path strips a fair-catch marker without
updating return eligibility, and skips a blocked kick in favor of a later
numeric punt. The corrected snap-fumble branch does not certify these other
classes. A receiving-team kick foul is also silently lost when its rerolled
distance reaches a touchback.

## Resolution / verification

Add synthetic/public regressions before the production change. Cover accepted
and declined foul choices, exact saved dice/results, fair catch/downed markers,
blocked-kick recovery/returns, touchbacks, both actual teams and both starting
possession sides. Accepting the kick foul must cancel the retained play without
recovery, scoring or statistics; declining must resolve the saved result once.
Preserve clock, period-extension and first-down rights. Reuse the authoritative
kick/return machinery instead of approximating a result as numeric distance.
Validate through current full-game checks before closing.

## Comments

--- 2026-11-06 02:35 ---
Read-only public/synthetic diagnostics at runtime `671f712b…` reproduce three
branches. A DEF 5 followed by a 40-yard fair catch rolls a punt return anyway;
an OFF 5 followed by a blocked punt consumes another kick result and offers a
numeric punt instead. A DEF 5 followed by a 70-yard punt from the 40 switches
possession at a touchback without any penalty choice or assessment. The
diagnostic is retained in ignored chart-confidence storage. No production fix
for these combinations is claimed. RULE-027 separately retains the offset and
legacy double-foul enforcement findings. No chart bytes or acceptance bounds
changed; release remains held.

--- 2026-11-06 02:50 ---
The first public/synthetic baseline has 48 failures and five passing controls. Production now preserves markers, retains a receiving-team foul choice on a touchback, defers a blocked-punt recovery until the decision, and resolves the saved blocked result without another kick lookup. No-return outcomes retain the actual saved roll/raw cell; KEEP and decline controls agree. The saved result is passed back through the existing punt handler, rather than duplicating blocked recovery logic. The shared pending-result helper also preserves the existing snap-fumble controls.

A separate parser baseline exposes spaced/case-varied blocked yardage falling back to a ten-yard loss. It fails three spellings, with the compact spelling passing; the expanded spacing/gate baseline has six failures/55 controls. The parser now reads the signed numeric value consistently. An introduced uninitialized no-return value is corrected without changing test expectations. All 66 focused retained-kick checks pass; the broader affected suite passes 820 before the final five controls are appended. Five new conformance cases and a numeric-substitution mutant cover the retained classes.

At runtime `f8b9af98…`, all 496 development games complete with reconciled accounting and 84 retained punt snap fumbles. The outcome review finds 110 declined marked-punt annotations with no return result, but no qualifying blocked-punt foul/recovery example. Its filter can also miss an original foul annotation on a declined generic retained kick. This is partial full-game evidence, below final exposure; keep the issue open for complete rare-branch/trace confirmation and remaining RULE-027 work. No chart bytes or source facts are changed.

--- 2026-11-06 03:06 ---
A 24-failure/66-control baseline exposes the missing declined-foul annotation
on retained snap fumbles, blocked punts and touchbacks. Final descriptions now
retain the foul alongside the saved kick and synchronize the result description.
An erased-annotation gate mutant fails first, then is rejected by the expanded
existing control. The 224 focused new foul/retained checks pass before the
shared half-distance expansion.

The current 496-game replay includes one qualifying saved blocked punt:
Bengals/Browns seed 20289360, from the 30, OFF 10 declined, saved BK -5 roll 13,
kicker recovery roll 14 at the 25 and turnover on downs. It preserves one
physical recovery, receiving position 75 and unchanged assessed penalty counts.
The 111 marked outcomes have no invented return roll. The final-outcome filter
still does not claim every intermediate rolled cell.

This also reveals remaining pre-existing blocked-punt receipt limitations:
the generic parser labels BK as BREAKAWAY and this handler supplies no outcome
clock trace, despite charging the correct live clock. Keep this issue open for
those class/trace gaps and the remaining special-teams review. The observed
physical result is not a complete result-schema certification.

--- 2026-11-06 03:24 ---
The blocked-punt metadata baseline has 94 expected failures and 94 passing
controls. Physical recovery, scoring, possession and roll counts pass before the
class assertion; separate controls reproduce the missing clock and completed
description, and the gate initially accepts class/clock erasure. The parser now
distinguishes numeric BK from B as `BLOCKED_KICK`, preserving signed gain and raw
lookup; the completed punt carries the final description and actual clock trace.
Existing retained gate cases check both fields and reject both mutants, keeping
34 total cases. The first post-fix suite exposed a missing `asdict` import in the
new gate assertion (60 failures/508 controls); that setup error is fixed without
changing expectations. The rerun passes all 568 focused checks; Ruff passes.

Fresh current development games finish all 224/272 games with full accounting,
including 85 retained snap fumbles. The expanded final-outcome review inspects
464 outcomes, including all 41 completed blocked punts; their class, synchronized
description and clock start/end checks pass. This includes the previously
identified retained-foul recovery. Both legacy exception assessments still pass.
All 496 game scores and team box statistics match the preceding runtime; ordered
receipt comparison identifies class and initial-gain metadata changes, including
19 blocked field goals parsed by the same numeric BK parser. This is development
mechanics evidence, not final fit or release certification. The refreshed core
checkpoint remains active; retain the open status until it completes.

--- 2026-11-06 03:34 ---
The current `f0cfc25a…` core suite completes with 8,873 passed, eight existing
data-dependent skips and 83% coverage. The full-game review05 verifies all 41
completed blocked punts, including the saved OFF 10 / BK -5 recovery after a
declined foul, and all 111 marked no-return outcomes. Class, signed initial gain,
saved dice/raw result, synchronized description and actual clock receipts now
agree with physical recovery, possession, scoring and accounting. All 496
current development games complete; current standalone, historical, generated
season and playoff integrations also pass. Close the retained-result/marker/trace
scope on this targeted full-game proof. The implementation remains local and
uncommitted; no release or publication is approved. RULE-027 remains open for
its separate legacy double-foul policy review.

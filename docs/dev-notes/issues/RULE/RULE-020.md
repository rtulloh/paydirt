---
id: RULE-020
title: Kickoff with kick-chart and return-chart fouls by the same team is treated as offsetting with no re-kick
status: resolved
priority: High
created-at: 2026-10-27
resolved-at: 2026-10-28
closed-at:
tags:
  - reproduced
links:
  - TRACE-004
commits:
---

## Description

When the kickoff chart yields a penalty and the return chart also yields a penalty, `paydirt/game_engine.py:544-581` hands both to `_handle_double_foul_penalty` (`:289-363`), which never compares the fouling teams. Synthetic reproduction: kick cell `OFF 10` → reroll `60`, return cell `OFF 15`. Result: "OFFSETTING PENALTIES: OFF 10 and OFF 15. Down replayed.", **no re-kick is performed**, the kicking team keeps the ball 1st-and-10 at its own 35, `pending_penalty_decision` is False and `field_position_after` is "pending". Three dice were consumed. The trace prints `R:10` although the return roll was 12 because `:563-564` pass the kick roll as both `punt_roll` and `return_roll`, and it uses punt-style `P:`/`R:` labels on a kickoff. Team attribution is inconsistent: `:622` calls a kick-chart OFF a receiving-team foul while `_handle_double_foul_penalty` labels it "Kicking Team". Controls: a kick-chart penalty alone produces the correct pending decision; two return-chart fouls by opposite teams produce a proper offsetting re-kick through `_resolve_return_chain`.

## Resolution / verification

- Failing regressions: same-team double foul enforces both or offers the correct choice per the rulebook and never leaves the kicking team with the ball; opposite-team fouls offset and re-kick; trace shows the actual kick and return rolls with kickoff labels.
- Compare fouling teams before treating fouls as offsetting; pass the real return roll to the trace.

## Comments

--- 2026-10-27 18:00 ---
Found during the Bowl Bound 2026-10-27 full review cross-check; reproduced in Paydirt with public 2026 sample fixtures and synthetic chart cells only. No private charts or logs were used.

--- 2026-10-28 07:21 ---
Implemented locally, validation in progress. Test-first baseline: 18 expected
failures and one plain-kickoff control passing. Kick and return phases now
identify the actual fouling teams before offsetting. Preserve the established
kickoff convention (OFF receiving / DEF kicking): same-team cross-chart fouls
leave a kick-chart re-kick decision; declining it resolves/enforces the return
through the shared resolver. Opposite-team fouls actually re-kick after ten
seconds, without phantom possession/pending final state. Preserve the existing
5-versus-15 catch-enforcement exception only for opposite teams; preserve X
markers, including on kick penalty rerolls. Count the enforced foul against
the correct team with effective yardage. All cross-chart paths retain original
KO, distance rerolls, actual RT and subsequent re-kick traces, not punt labels.

27 synthetic/public regressions cover both kicking sides, same/opposite fouls,
accept/decline, TD/fumble rerolls, stats, full roll consumption, half distance,
both directions of the 5-versus-15 exception, X suppression, and subsequent
return offsets. Additional test-first cases exposed lost offset trace and
ignored X markers. Existing expectation changes: three kick-phase offended-
team labels now use the receiving-team-as-offense convention used by every
consumer (the previous inverted labels were wrong); the offset integration
fixture now supplies a fresh kick/return and asserts real possession/spot and
five rolls instead of merely a false "Down replayed" announcement. No skips
added and all previous 5-versus-15 spot expectations retained.

Player guidance updated in docs/playing.md; guide navigation/API shapes and
packaging are unchanged. A real full-game replay completed all 13 historical,
224 generated and nine playoff games and inspected 1,860 kickoff calls. It
did not naturally encounter a cross-chart foul, so this is NOT sufficient
issue-specific play-test evidence for closure. Nothing pushed.

--- 2026-10-28 07:23 ---
Validation finding: the first full core run had 5,876 passes/eight existing
skips and one failure in unchanged test_resolve_extra_point_high_success
(90 successes in 100 attempts, assertion >90). Both that test and its extra-
point implementation are byte-identical to HEAD; random seed 400 independently
reproduces exactly 90 successes. This is an existing unseeded statistical test,
not evidence of a kickoff regression. No assertion, RNG behavior, or skip was
changed to hide it. A full-suite rerun is required and reported separately.
Backend 218 passed with existing Pydantic warnings; frontend 255 passed/one
existing skip, build, both complete Hard browser games and offline guide passed
(existing stale Browserslist warning). Standalone/full-season/playoff runners
and both reviewed full AI audits passed.

--- 2026-10-28 07:25 ---
Full core rerun passes unchanged: 5,877 passed, eight existing skips, 76%
coverage. Clean staged-only snapshot: 5,844 core passed / 25 existing skips,
218 backend passed (existing Pydantic warnings), project Ruff passed with Git
ignore context. Focused documentation/guide checks pass. Marked resolved with
the scoped local fix commit; keep open for case-specific play-test confirmation
(no cross-chart foul occurred naturally in the 1,860 observed kickoffs).
The earlier statistical-test failure remains disclosed above, not suppressed.
Local permission changes are separate/unpublished. Nothing pushed.

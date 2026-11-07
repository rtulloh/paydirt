---
id: RULE-027
title: Cross-chart punt fouls conflate teams and omit replay timing
status: open
priority: High
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-audit
links:
  - DATA-033
  - DATA-034
  - RULE-028
---

## Description

The punt chart names the kicking team as offense; the return chart names the
returning team as offense. `_handle_punt` sends both chart fouls to its double-
foul handler without first comparing the actual fouling teams. A kicking-team
OFF foul followed by a return-chart DEF foul is therefore called offsetting,
although both fouls are against the kicking team. The offended team should be
able to choose one foul instead of losing the return to an invented double foul.

For an actual opposite-team offset, the branch announces a replay but does not
set `result.replay_down`, charge ten seconds or apply defensive untimed-down
handling. This makes ordered retained-play evidence and game timing incorrect.

## Resolution / verification

Write synthetic/public regressions before changing production code. Cover both
actual fouling teams, both starting possession sides, accepted/declined choices,
recovery/return chains, zero double-counting, ordinary replay timing and an
offset reaching the end of a half. Preserve the individual penalty's first-down
rights and choose one foul, never combine unrelated yardage or flags. Reuse the
core return/penalty machinery and update the existing gate controls.

## Comments

--- 2026-11-06 02:12 ---
Read-only public/synthetic diagnostic at runtime `871af55a…`: from HOME 40,
fourth-and-eight, both the same-team and opposite-team examples announce
offsetting. Each leaves the clock at ten minutes, sets no pending choice and
leaves `replay_down` false. The same-team example should not offset; the real
offset should charge ten seconds and preserve an end-of-half untimed down.
Evidence is retained in ignored chart-confidence storage. DATA-033's corrected
first-down flag transport exposes this existing combination problem; its
passing single-return and own-recovery controls do not certify this branch.
Release remains held. No private/reference data or reserved seed was opened.

--- 2026-11-06 02:32 ---
Test-first correction now compares actual fouling teams before invoking the
legacy double-foul policy. Same-team cases retain a pending choice between the
kick foul and the already-resolved return; keeping the latter never adds the
kick foul's yards or flags. Genuine kick-chart/cross-chart offsets use one core
ten-second replay outcome and preserve a defensive period extension. Four more
failing controls expose a retained return's missing defensive extension; four
offensive-foul controls already pass. The retained-return timing is corrected.

The first 97-case baseline has 80 behavior failures, 16 fixture failures and
one ordinary-punt control passing. The fixture incorrectly expected recovery
35 to roll an advance; 37 is the advancing lost-recovery case. Both now have
separate controls. A live returner foul is correctly declined when keeping the
lost-fumble recovery; the initial new expectation of one assessed penalty in
that case was wrong and now requires exactly zero. Original reports are kept.
Two older integration expectations incorrectly treated punt DEF plus return
OFF as opposite-team fouls. They now verify one receiving-team assessment;
direct double-foul policy controls are retained.

The same review finds punt-reroll metadata mixing and previous-spot enforcement
defects. The corrected baseline has 38 failures and three controls; an earlier
draft incorrectly invented a DEF 15Y override and is preserved separately.
Production reuses the existing penalty parser/resolver, keeps the chosen
foul's metadata together, preserves early downs and credits actual first downs.
Two existing fourth-down tests omitted their setup down; setting fourth down
explicitly preserves their assertions, while new second-down controls prevent
the old forced-fourth behavior. Explicit decline-option selection and actual
fumble-recoverer previews have separate failing baselines.

All 176 new foul/selection checks pass. The focused existing-engine suite passes
455 before the last two negative controls are added; conformance now has 26
real-engine controls. The complete core suite, fresh training replay and source
reproduction are being refreshed at runtime `671f712b…`. Keep this issue open
through current full-game review and remaining special-teams combinations;
these focused controls do not certify all legacy five-versus-fifteen, marker,
blocked-kick, return-chain or no-return punt branches. No chart bytes, target,
profile, reserved family or private reference changed. Release remains held.

--- 2026-11-06 02:35 ---
Further read-only combination diagnostics confirm two additional enforcement
gaps outside the corrected replay helper. A genuine opposite-team OFF 5 kick /
OFF 15 return pair from the 40 produces a receiving position of 65 using the
punter's landing coordinate, records no penalty statistic and leaves
`penalty_applied` false despite announcing fifteen-yard enforcement. This is
wrong even under the retained legacy five-versus-fifteen policy; its policy and
all return/fumble combinations need separate explicit controls.

A return-chart-only offset with three seconds left consumes ten seconds,
advances to the third quarter and automatically executes another punt. It
preserves no defensive untimed down. The ordinary auto-rekick passing control
does not cover this boundary. Both examples are retained with the DATA-034
diagnostics, and require test-first corrections. Keep this ticket open; neither
the passing focused suite nor legally completed training games closes it.

--- 2026-11-06 02:34 ---
The current read-only full-game replay completes all 496 development games and
reviews all 426 recorded punt-foul events. Four naturally occurring same-team
cross-chart cases retain one assessment without an invented offset; all ten
recorded genuine replay outcomes carry ten-second clock traces. Three natural
five-versus-fifteen cases independently confirm missing assessment metadata and
statistics (1983 Cardinals/Buccaneers, seed 20347882; 2024 Chiefs/Falcons,
20306513; Commanders/Giants, 20392278). These seeds derive from development
master 20261108, not a reserved family. The issue remains open for those defects
and the period-boundary combinations; no unit-only closure is made.

Backend validation exposes one obsolete handmade pending-state fixture: it
uses a display string as the engine's numeric prior position and a UI label as
the raw penalty. It now uses the real engine schema, sets its intended fourth
down, and preserves every state assertion. Its description assertion now
requires the core's explicit "Replay the down" instruction; no new punt has
already been executed. A separate halftime test randomly rolled a kickoff
foul while assuming a completed kickoff. Its synthetic kick/return dice are
now fixed, preserving both receiving-team assertions. Neither fixture repair
changes production to bypass a real foul or weakens a rule assertion.

--- 2026-11-06 02:50 ---
The return-chart-only offset is now corrected test-first. Its baseline has 34 failures and 31 existing passes. A canceled punt returns a ten-second replay outcome and preserves the next offensive decision, including an untimed down at expiry. One existing test incorrectly demanded an immediate second punt and eighteen seconds; its new expectation is the original spot/down and ten seconds. That change follows the replay rule and common engine offset behavior, rather than weakening an enforcement assertion. New controls cover all four quarters, both possession sides and both play entry points. The next explicitly chosen punt can then consume the untimed down and reach halftime normally.

Runtime `f8b9af98…` passes 820 affected checks and 32 conformance cases after the retained-kick expansion. Current development replay completes 496 games and reviews 414 finalized outcomes annotated with a foul/replay. Nine genuine replays have ten-second traces; two natural legacy five-versus-fifteen cases still omit assessment metadata/statistics (Cardinals/Buccaneers seed 20347882 and Chiefs/Falcons seed 20306513). Keep open for that enforcement defect and remaining combinations. Declined generic retained kicks can omit their original foul annotation, so this outcome filter does not claim a census of every rolled foul. No reserved family or private reference is used.

--- 2026-11-06 03:06 ---
The existing five-versus-fifteen exception now retains the actual fifteen-yard
fouler and receiving catch coordinate, records one effective assessment and
sets the penalty flag. Nominal foul size travels separately from assessed
half-distance yards. The canceled return cannot retain a score, recovery or
resolved-fumble result. Period rights follow the actual accepted foul.
The corrected synthetic baseline has 128 behavior failures/two controls; draft
field-name/case mistakes were repaired before production. A second baseline
has 75 failures/58 controls for canceled-fumble projection and missing gate/
mutant coverage. Existing conformance count changes from 32 to 34 for two new
real-engine cases, rather than dropping any prior case.

Current runtime 52d48a1f… completes all 496 development games. Both previously
failing natural examples now pass actual-team, catch, half-distance, metadata
and one-assessment checks: Cardinals/Buccaneers seed 20347882 ends at the
receiver's 14 with 13 assessed; Chiefs/Falcons 20306513 ends at the 13 with 13
assessed. All eight recorded genuine replay traces request ten seconds.
RULE-028 isolates the shared half-distance defect exposed between these two
fixes. The first fresh full core run was intentionally stopped incomplete on
that new finding; a new run is active.

The implementation preserves the repository's legacy exception. The original
board-game double-foul wording and some legacy special-teams policies still
need explicit review; this is not a claim that every combination matches the
rulebook. Keep this issue open through that review and remaining combinations.
No chart/source/target/profile/bound or reserved/private input changed.

--- 2026-11-06 03:35 ---
Read-only review of the [reprinted board-game rules](https://www.rulespal.com/paydirt/rulebook)
finds VI-4(A)(ii)'s canceled-play/replay procedure and VI-4(C)'s half-distance,
returning-team identity and period-extension provisions. No five-versus-fifteen
exception appears in those provisions. This is a support gap, not authority to
replace the existing repository policy without reconciling its intended rule
source and season applicability. Current enforcement receipts pass at `f0cfc25a…`;
the separate legacy-policy question stays open. No production rule changes follow
from this read-only review.

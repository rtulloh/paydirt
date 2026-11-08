---
id: RULE-027
title: Review legacy punt double-foul enforcement and ambiguous penalty classification
status: open
priority: Medium
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

The original same-team/offsetting identity and replay-clock defects have committed
repairs. The remaining open work is a rule/model decision about the legacy
five-versus-fifteen exception and the timing/type of generic chart penalties.
Earlier findings and test-first evidence remain below as investigation history.

Current behavior compares actual fouling teams across the Punt and Punt Return
charts, whose OFF/DEF labels are relative to each chart owner. Same-team fouls
do not invent an offset. Genuine opposite-team offsets ordinarily cancel the
play and produce a ten-second replay with the applicable period-extension rights.
However, a five-yard and fifteen-yard pair without automatic-first-down flags
uses the retained legacy exception: disregard the five-yard foul, cancel the
return, and enforce the fifteen-yard foul from the catch (with applicable
half-distance treatment), leaving the receiving team in possession.

Recorded development games confirm repaired team identity, replay timing and
assessment accounting. They do not establish that this blanket exception matches
Paydirt or every historical NFL rule. Paydirt VI-4(A)(ii) specifies a canceled
play and ten-second replay for offsetting penalties. NFL enforcement additionally
depends on possession changes, foul timing/type and applicable rules. Generic
OFF/DEF yardage cells do not supply all those facts.

Priority is Medium: the demonstrated broad implementation errors have been
repaired; the remaining narrow special-teams policy/model ambiguity warrants
follow-up without retaining the original High defect framing. Frequency and
season-level impact have not been quantified, so this is not a claim of zero
impact or a measured rarity. No new release blocker or rule change is created.

## Resolution / verification

Write synthetic/public regressions before changing production code. Cover both
actual fouling teams, both starting possession sides, accepted/declined choices,
recovery/return chains, zero double-counting, ordinary replay timing and an
offset reaching the end of a half. Preserve the individual penalty's first-down
rights and choose one foul, never combine unrelated yardage or flags. Reuse the
core return/penalty machinery and update the existing gate controls.

## Options for consideration — not approved behavior

The owner is considering an engine-owned penalty classification rather than
relying only on ambiguous chart yardage. No implementation or preferred policy
has been selected.

- Distinguish a pre-snap whistle-stopping foul, an at-snap/live kick foul, a
  return foul, and a post-play/dead-ball foul. Enforcement from the previous
  spot does not by itself mean the whistle stopped play before the snap.
- False start, play-clock expiration before snap, encroachment and qualifying
  neutral-zone infractions are candidates for explicit pre-snap handling. No
  kick/return is resolved; enforce the foul and preserve the down, subject to
  an earned first down and applicable clock rules. Do not assume no clock
  adjustment in every end-of-half situation.
- Ordinary illegal formation/motion/shift can be live-ball fouls. Roughing or
  running into the kicker happens after the snap. Do not classify these as
  immediate pre-snap stoppages merely because enforcement uses the previous spot.
- OFF/DEF identifies the fouler relative to the chart owner, not an absolute
  offense/defense identity. Punt OFF plus Return OFF names opposite teams;
  Punt OFF plus Return DEF names the same kicking team.
- Paydirt already supports X/Y enforcement information; these modifiers do not
  uniquely identify foul timing or type. Yardage, chart phase, team and modifiers
  can constrain a classification, but cannot prove an unspecified foul's identity.
- For a generic Punt OFF 5, consider predefined engine subtypes such as false
  start (no snap) or illegal shift (live kick/return), rather than treating all
  five-yard fouls alike. This is an explicit model assumption, not recovered
  historical source evidence. A predefined deterministic mapping or declared
  probability mixture would need review; no percentages have been chosen.
- Preserve explicit PBP foul identity when suitable source evidence exists.
  Generic legacy charts need a disclosed fallback. Source flags, original cells
  and inferred subtype/provenance should remain distinguishable.
- Select any modeled subtype before resolving the subsequent kick/return and
  independently of whether that outcome would favor either team. Preserve the
  chart event probability; disclose any intentional change to downstream clock,
  possession, penalty rates, return exposure or statistics. Keep coaching fairness.
- Keep subtype, phase and enforcement in authoritative engine-owned results,
  saves and logs; make inference reproducible without UI rule logic. Do not add
  a casual random draw that invisibly perturbs unrelated dice/coaching streams.
- Consider season configuration for genuine historical changes, including
  kick-foul keep-ball/tack-on choices and post-scrimmage-kick enforcement. Verify
  effective years and detailed conditions before encoding them; the owner's
  supplied dates and examples are research leads, not verified specifications.
- Alternative: follow Paydirt's explicit canceled-play/replay procedure for
  genuine chart offsets and remove the blanket legacy exception. Compare this
  bounded approach with richer NFL-style classification before choosing scope.

Future implementation must be test-first with synthetic/public fixtures. Cover
both chart owners and possession sides; pre-snap fouls with no return consultation;
live kick/return and same/opposite-team fouls; five/fifteen with X/Y controls;
clock/end-of-half behavior; half-distance, choices, accounting and reproducibility.
Require issue-specific play testing before closure. Do not invent source facts,
force favorable outcomes, or make unknown legacy timing look historically exact.

Research references:

- [Reprinted Paydirt rulebook, V and VI-4](https://www.rulespal.com/paydirt/rulebook).
- [Official NFL rules and approved rulings, Rules 4, 7 and 14](https://media.nfl.com/content/dam/communications/Official%20Playing%20Rules/2026%20Official%20Playing%20Rules.pdf).
  Modern rules are not proof of identical 1983 enforcement.

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

--- 2026-11-08 17:03 ---
Owner requested recording the penalty-classification/season-policy discussion
and a priority assessment. Updated the current description and title, retained
original implementation evidence, and lowered High to Medium because the broad
team-identity/replay/accounting repairs are committed. The remaining policy/model
decision keeps this ticket open, rather than resolved. No rules or gameplay code
changed, no inference mixture selected, and no historical change date certified.

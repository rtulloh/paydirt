---
id: STAT-005
title: Scrimmage return narration omits assessed penalties and hides their rerolls
status: closed
priority: Medium
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - reproduced
  - audit-evidence
---

## Description

The latest completed manual game reports four accepted home-team penalties
for 45 yards. The visible enforcements account for three penalties for 30:
one ten-yard scrimmage foul, one fifteen-yard kickoff-return foul at the
second-half kickoff, and one five-yard kicking-team foul followed by a
re-kick. The away team's three accepted penalties for 22 effective yards
reconcile, including both half-distance assessments. Two declined scrimmage
fouls correctly appear separately from accepted totals.

The initial audit could not explain the extra fifteen yards. Follow-up found
that the third-quarter lost scrimmage fumble's compact trace labels the first
return roll with the **net** advance. That generated return-chart cell contains
`OFF 15`; its enforcement and reroll were present in the core description and
transaction but omitted by the compact display. This explains the previously
unreported fourth foul without evidence of duplicate statistics.

## Resolution / verification

The engine now supplies the return-chain evidence through `rule_explanation`,
which both CLI layouts already display. This covers interception returns,
defensive fumble returns and offensive recovery advances. Existing offensive
recovery explanations retain their location/down information and append the
enforcement and rerolls. Statistics, field position and dice are unchanged.

No complete RNG state/build was captured for the manual game. The original log
is unchanged; the synthetic numeric reroll is explicit test input, not a claim
to recover a missing original die. Its six-yard net return after a fifteen-yard
assessment is consistent with the observed position and final penalty total.

A read-only public/synthetic replay of the visible return foul alone charges
one penalty for fifteen yards and produces the correct receiving spot.
A separate kick-chart/re-kick reproduction charges one penalty for five
yards. Neither isolated case reproduces the unexplained extra fifteen yards.
The valid test-first baseline has 72 missing-explanation failures and 36 clean
controls. New regressions use only public samples and synthetic cells across
both sides, direct/procedure/declined flows, both CLI layouts, returning-team
and opposing-team fouls, and half-distance enforcement. The focused set passes
208 tests. A fixture initially expected the full opposing-team fifteen yards
near the goal; it was corrected to ten, and the baseline rerun against the
unchanged engine before applying the fix. No existing expectation was weakened.

Issue-specific complete-game confirmation: 64 public/synthetic seeded games
finish successfully, displaying 84 interception-return fouls, four lost-fumble
return fouls and three retained-fumble advance fouls in both CLI layouts. The
display leaves statistics and gameplay RNG untouched. Reports remain ignored
under `.ai-audits/release-readiness/`. This confirms the presentation fix; it
is not a historical statistical-fit experiment.

## Comments

--- 2026-11-02 10:15 ---
Final and halftime tables, all displayed scrimmage decisions, and all
kickoff/return traces were inspected. The halftime home total is one for
ten; the visible second-half additions are fifteen and five. Other principal
yardage, sack, first-down, turnover, and score totals reconcile independently.
Keep this discrepancy separate from the older punt-double-foul omission.

--- 2026-11-02 10:50 ---
Two passing public lifecycle controls include the first-half scrimmage foul,
halftime return foul, later accepted kickoff foul/re-kick and repeated stale
decision. They reconcile to three accepted fouls for thirty yards on either
side. A separate 64-game public audit reconciles 576 narrated scrimmage
penalty increments; it is not an exact replay or complete special-teams
accounting oracle. The uncaptured manual game's extra fifteen yards remains
unexplained. No statistics mutation is changed without a causal failing
regression. Keep open; do not report this investigation as a fix.

--- 2026-11-02 11:09 ---
The missing return-chain explanation is causally reproduced and fixed, with
the complete-game confirmation above. The previously visible three-for-thirty
total excluded one automatically assessed fifteen-yard fumble-return foul.
Close after issue-specific play-test evidence; no accounting mutation was
changed and no missing original reroll is invented.

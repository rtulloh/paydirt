---
id: DATA-012
title: Defensive interception calibration concentrates risk in a high-mass Short Pass row
status: closed
priority: High
created-at: 2026-11-01
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - chart-generator
  - play-test
  - calibration
  - reproduced
links:
  - DATA-011
  - AI-019
---

## Description

A manual Hard-AI game using the calibrated generated 1983 Eagles and Cowboys finished 27-3 with
seven Philadelphia turnovers: five interceptions and two lost fumbles. All five interceptions came
from Dallas defensive chart results rather than Philadelphia offensive interception cells.

The game exposed a coarse defensive-interception rule in `_generate_defense()`. A defense allowing
an interception rate of at least 3.5% replaces the Short Pass result in formation D, sub-row 2 with
`INT 5`. That sub-row carries 11/36 of the defensive dice mass. Formation D already contains a
Short Pass interception in sub-row 4, so this one threshold changes the call-specific interception
probability from 3/36 (8.33%) to 14/36 (38.89%). Twenty-two of the 28 generated 1983 teams receive
the high-risk version; the other six remain at 8.33%.

Philadelphia called Short Pass against formation D five times in the supplied game and threw three
interceptions on those calls. Its other two interceptions came from one Long Pass against C and one
against E, both low-frequency defensive interception rows. Across all 47 Philadelphia pass calls,
the Dallas defense chart contributed an expected 2.5 interceptions; five or more has a 6.84% tail
probability. Philadelphia's calibrated offensive pass columns contain no direct interception cells,
so interception risk is both shifted to defense and highly concentrated by formation and play.

The same game produced three fumbles in six QT resolutions, compared with a generated Eagles QT
fumble mass of 14.81%; that tail is 4.58%. Two of the three fumbles were lost against a 37.5%
recovery-loss interval. This is an unusual but plausible secondary run of dice. The defensive
interception concentration is the reproducible chart defect.

## Resolution / verification

The generator now replaces the binary high-interception threshold with a weighted allocation that
expresses team differences through sub-row-five cells. Each source-strength adjustment changes one
play-and-formation matchup by at most 1/36, while the original tactical template remains intact.
The existing selected profiles still satisfy the combined offense-plus-defense chart-focused
calibration targets.

Verification covers:

- a small change around the current 3.5% source threshold cannot create a 30.56 percentage-point
  jump in one call-specific interception probability;
- stronger interception defenses receive more combined weighted interception mass than weaker
  defenses without relying on one high-mass sub-row;
- generated offense and defense charts retain the intended league interception rate together;
- the Hard play-selection path cannot hide concentrated human-call risk in the league aggregate;
- regenerated 1983 and 2024 charts pass the reported manual call-mix audit plus chart-focused and
  Hard validation.

Keep the supplied game log local and ignored. Verification notes may report aggregate counts and
probabilities without copying private chart contents or narrative play text.

## Comments

--- 2026-11-01 23:58 ---
The final game totals reconcile: five interceptions plus two lost fumbles equal seven turnovers. A
third fumble was recovered by Philadelphia and was correctly excluded. Three turnovers led directly
to 17 Dallas points, while two later turnovers ended Philadelphia possessions inside the Dallas
20. No duplicate turnover or scoring-log defect was found.

--- 2026-11-02 00:17 ---
Test-first regressions reproduced the old 30.56 percentage-point D/Short jump when the source rate
crossed 3.5%. The implementation distributes additions and removals over low-mass sub-row-five
cells. Focused generator tests, the broader 59-test chart-generation suite, and Ruff all pass.

--- 2026-11-02 00:18 ---
Regenerated 1983 and 2024 candidates retained their selected tuning profiles. All five metrics in
each 64-season chart-focused run remained within tolerance, with 1,024 team-games per 1983 team and
1,088 per 2024 team. The held-out 256-season Hard runs completed 57,344 and 69,632 games. The 1983
Hard interception rate rose from 1.25% to 1.96%; the 2024 Hard rate changed from 1.30% to 1.11%,
while its chart-focused rate improved from 3.12% to 2.79% against a 2.17% target.

--- 2026-11-02 00:19 ---
For the exact 47-pass call mix from the reported Eagles-Cowboys game, Dallas defensive-chart
expected interceptions fell from 2.50 to 1.58. The probability of at least five fell from 6.84% to
1.87%, and D/Short fell from 38.89% to 11.11%. Historical-schedule sanity runs completed all 224
regular-season and nine postseason games for 1983 and all 272 plus 13 for 2024. Every promoted team
chart loads, no direct run exceeds 18 yards, and generated CSVs contain no CRLF lines. The fix is
implemented and verified; the issue remains open until the change is committed under the tracker
status convention.

--- 2026-11-02 06:36 ---
A second manual Eagles-Cowboys play test did not reproduce the old concentrated D/Short defect.
Philadelphia called Short Pass against D twice: one play was incomplete and the other used the
unchanged tactical sub-row-four interception. Of the six interceptions in the game, only one came
from a newly allocated low-mass DATA-012 row.

The game finished with seven official giveaways (four Dallas interceptions, two Philadelphia
interceptions, and one Philadelphia lost QT fumble), plus three Philadelphia turnovers on downs.
For the exact observed play/formation call mix, the generated charts expected 3.76 pass-call lost
turnovers; seven or more has a 7.36% tail probability. Dallas's four interceptions were the larger
single-team outlier at 3.87%, while Philadelphia's three pass-call turnovers had a 30.43% tail.

Philadelphia completed 16 of 41 statistical pass attempts, with 23 incompletions. Its call mix
expected 18.84 incompletions, making 23 or more an 11.75% outcome. Across both teams, however, the
32 observed incompletions nearly equal the generated expectation of 32.38; the game split them
unevenly between Philadelphia and Dallas.

Replaying the same pass choices, primary offensive rolls, and defensive sub-rows against the local
developer charts changes the immediate primary results from 32 incompletions and six interceptions
to 24 incompletions and four interceptions. The developer rows also produce ten penalty cells, two
TD cells, two QT cells, and one fumble cell at those exact rolls. A complete final-result replay is
not possible where the charts diverge into penalty, QT, fumble, or B branches because the original
game did not roll or print the additional branch dice that the alternate chart would require. This
comparison is therefore valid for primary chart results and call-mix probabilities, not a fabricated
alternate final score.

--- 2026-11-02 10:15 ---
The latest completed generated-chart game contains zero interceptions. Four giveaways reconcile to lost fumbles: three away, one home; the retained one-yard QT fumble is not a giveaway. Passing reconstruction yields 14/32 for Philadelphia (43.8%) and 18/31 for Dallas (58.1%), with four Philadelphia sacks totaling 37 yards and gross/net pass yards reconciled. This is no repeat of the former concentrated interception burst, but one game cannot validate chart interception or completion distributions. Keep open while the generator changes remain uncommitted; see ../../game-audit-2026-11-02.md.

--- 2026-11-02 10:50 ---
Prepared for commit with the documented source/profile regeneration, test-first
regressions and full-game evidence. The November 2 completed manual audit
confirms the relevant generated-chart mechanisms: no field-independent run
TDs, ordinary breakaway resolution, no concentrated interception recurrence,
and both kick and return fouls. Close this specific transformation/coverage
issue on that evidence; statistical fit and coaching limitations remain
documented. The new engine timing changes do not establish a fresh 64/256-season
fit; DATA-011 explicitly distinguishes the earlier fitting evidence.

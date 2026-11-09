# Historical season validation

Run the selected year's actual regular-season calendar with available engine
charts. The maintained fixture sets cover 1983 (28 teams, 224 regular games and
nine historical playoff fixtures) and 2024 (32 teams, 272 regular games and
thirteen historical playoff fixtures).

```bash
python3 tests/run_full_season.py 1983 --charts seasons/1983-generated
python3 tests/run_full_season.py 2024 --charts seasons/2024
```

No argument selects 1983. Chart selection prefers `seasons/YEAR-generated`,
then `seasons/YEAR`; `--charts` selects an explicit directory. The selected
directory must contain every mapped team and matching source-year rules. Missing
fixtures, results, teams, charts or rules fail before games start. There is no
generated-calendar or guessed-membership fallback. Developer charts are optional
and are not required to compare generated-chart results with historical scores.

The default policy is Hard for both teams. Use `--policy balanced` for the
legacy balanced policy. `--seed` selects the development master (default
20261108); game seeds are master plus execution index times 1009. A single run is
a development diagnostic, not a repeated-season estimate or a source-fit gate.

## Two distinct postseason modes

The default `--postseason-mode simulated` qualifies entrants from the simulated
regular standings. The 1983 format has three division winners and two wildcards
per conference; division opponents cannot meet in the divisional round. The 2024
format has four division winners and three wildcards per conference, one bye per
conference and divisional reseeding. Higher seeds host conference rounds. A failed
game never advances either participant; dependent games remain unplayed and the
command fails.

The runner also accepts an explicit `eight_team` source schedule for the 1977
format: three division winners and one wildcard per conference, four divisional
games, two conference games and one championship, with no wildcard round.
The top two division winners host; the wildcard visits the highest-ranked
winner outside its division. The remaining division winners meet in the other
game. A surviving division winner hosts the conference final. This structure
is documented in the [1977 Cardinals media guide](https://library.sfo2.cdn.digitaloceanspaces.com/publications/football/yearbooks/FARICMG-1977-arizona-cardinals-media-guide.pdf),
printed page 116 (PDF page 119). Eight-team support does not supply a reviewed
1977 fixture set or qualify candidate charts; those are separate inputs/checks.

Qualification currently uses declared **regression tiebreaks**: winning fraction
(ties count as half a win), point differential, points scored, then team name.
Reports list equal-record groups. These are not the complete official NFL
tiebreaks. Their consequences have not yet been quantified; official source-year
qualification and final probability studies remain **UNVERIFIED**.

Use `--postseason-mode historical` to replay the actual historical playoff
fixtures instead. These fixed participants and historical fixture identities do
not change when a replay produces another winner. The report labels this mode
`historical_fixture_replay` and does not claim a simulated bracket champion.
Never use that mode to estimate counterfactual qualification probabilities.

## Evidence and limitations

Reports retain source game IDs, dates, weeks, scores, membership, source hash,
chart hashes, policy/master, loaded-core identity, selected-action before/after
state and boxes, final boxes, period scores and scoring logs. Engine checks
reconcile offensive totals and final scoring, require legal completion, and reject
tied playoff finals or kickoffs after game end. Source and chart bytes are checked
again after execution. Reports and failures use new files under ignored
`.ai-audits/`; `--output PATH` selects a new report there.

Historical comparisons retain team wins/losses/ties, points and differences,
score error and exact-score-match counts. Matching every historical result or
champion is not a pass condition. One season has substantial sampling variation;
these differences do not establish accuracy, intrinsic strength or calibrated
qualification probabilities. Separate fixed-chart policy comparisons from
fixed-policy chart comparisons.

Selected-action callbacks omit intervening conversion and kickoff transitions.
Final scoring/box checks do not independently prove every play-by-play rule.
Browser qualification, source support, fixed chart-fit bounds, repeated-season
uncertainty and independent review remain separate requirements.

All sixteen existing 1983 private-chart game reproductions run additionally when
their original local charts are present, retaining both mandatory untimed-down
scenarios. Their absence is reported as `not_applicable`, rather than blocking
the source-only audit. Keep their logs local. The previous rotating-calendar
regression remains available only as the explicit additional
`--generated-regression` mode; it is not the historical calendar.

## Fixture provenance

Normalized fixtures live in `config/season-schedules/YEAR.json`, with raw-public
source hashes and attribution. The 1983 calendar/results come from archived
[Pro Football Reference](https://www.pro-football-reference.com/years/1983/games.htm);
the 2024 set comes from [nflverse nfldata](https://github.com/nflverse/nfldata/blob/master/data/games.csv).
Membership is reviewed against NFL season standings. The 1983 neutral Super Bowl
home/away orientation follows the source display order; independently verified
designated-home status remains a recorded source limitation. Raw play-by-play,
developer charts and historical narrative logs are not included.

See [development validation](development.md), the
[staged qualification plan](dev-notes/game-to-season-qualification-plan.md) and
[VAL-019](dev-notes/issues/VAL/VAL-019.md) for outstanding qualification work.

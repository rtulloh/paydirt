# Denver 1983 unresolved source coverage

Development evidence under the [chart-confidence charter](chart-confidence-agent-charter.md).
This is not a source correction, historical accuracy claim or release approval.
The source criterion remains unmet; official counts and fixed tolerances remain unchanged.

## Facts and conflicting annotations

The official [NFL player log](https://www.nfl.com/players/john-elway/stats/logs/1983/)
records five sacks for 38 yards and three rushes for 23 yards on December 11.
The cached public [PFR game](https://www.pro-football-reference.com/boxscores/198312110den.htm)
has four eligible explicit Denver sacks totaling 36 yards. A fifth explicit sack
annotation is nullified by an accepted no-play foul; it must remain excluded.

Two other Elway events are described as no-gain QB fumbles: source play 85 is
lost near the goal line; 167 is recovered by Elway. The latter starts second-and-two
at Baltimore's 24, followed immediately by third-and-four at Baltimore's 26.
This state chain supports a two-yard loss despite the conflicting no-gain and
recovery annotations. It does not independently establish a dropback sack.
No raw annotation, nullified foul or statistical target has been overwritten.
The primary gamebook has now been located; see the subsequent reconciliation
below. Earlier counterfactuals remain labeled as such and are not rewritten as
observations.

Across the complete 224-game cohort, official sack occurrences total 1,215;
the observed eligible event classification totals 1,214. Eleven classified sack
occurrences lack loss yardage and deliberately supply no invented QT gain.
All official interception counts (620) and field-goal attempts (771) reconcile
after separate test-first corrections and game/player box reconciliation.
Four conflicting field-goal descriptions retain an unknown underlying mechanism.

## Counterfactual sensitivity, not source correction

Both candidate-event interpretations were evaluated with the unchanged baseline
profile and generator seed 8306. Each assumes a two-yard sack loss at either 85
or 167, changes its fumble accounting family and adds a primary QT sample using
a declared heuristic pass family. These assumptions are explicitly marked in
ignored manifests and must never be promoted as observed historical facts.

Both interpretations generate identical chart CSVs. Only Denver offense changes:
10 short-pass cells (physical row mass 88/216), three QB-time cells (9/216) and
one T/E short-long cell (9/216). Repacking is not a simple one-cell perturbation:
short-pass fumble mass changes from 6/216 to 7/216. The maximum exact pre-state
outcome total variation across 54 Denver call/formation pairs is 0.101541.
No other team's chart, defense or special column changes. This demonstrates why
one event divided by a league denominator is an inadequate sensitivity bound.

Paired training-only replays use master 20261108 and two complete schedules
(448 games per variant). All complete with legal/scoring/count identities.
Relative to baseline, league completion changes +0.000392, interception
+0.000035, sack -0.000252, passing YPA -0.007327 and rushing YPA +0.009001.
Denver's corresponding changes are +0.008122, -0.008857, -0.000067, -0.029714
and +0.200414. These finite shared-seed differences include changed game paths;
they are not acceptance evidence, confidence intervals or proof of a small true
effect. The small team sample cannot certify the fixed team bounds.

## Reproduction and decision boundary

Ignored evidence lives under `.ai-audits/chart-confidence/`:

- `source-trace-after.json` preserves public source events and box differences.
- `classified-source-accounting/1983/source-ledger.json` binds raw game hashes,
  event representations, source conflicts and occurrence counts.
- `sack_counterfactuals.py` generates explicitly hypothetical candidates.
- `run_sack_sensitivity.py` produces exact and paired engine comparisons.
- `sack-counterfactual-impact.json` contains all changed cells/masses and team deltas.
- `sack-sensitivity-{baseline,85,167}.json` contains seeds and individual game receipts.

An independently supported event reconciliation would allow a tested source
correction. Alternatively the parent may review a precise observed-coverage
contract that preserves the official target, separately labels unresolved event
identity/loss and prevents claims of complete event recovery. That would revise
an unmet acceptance criterion and requires explicit parent review. A text-only
review allowlist cannot make the current count discrepancy pass the gate.

## Parent review, 2026-11-05

No 1983 source exception was approved. The two initial scenarios both happened
to receive the heuristic short-pass family, so their identical CSVs are
conditional on that assignment. They do not bound unknown primary-family
placement. Extend sensitivity to all plausible passing families and separately
label initial-loss versus recovery interpretations. The finite replay deltas
remain diagnostics and must not be presented as bounds on the true effect.
The parent authorized independent 2024 calibration once its source/mechanics
controls pass; the global objective continues to require both cohorts.

## Expanded conditional sensitivity

The follow-up covers sixteen declared hypotheses: either source event, each of
Screen/Short/Medium/Long, and either initial F0 or F−2. Recovery movement stays
unknown. The frozen pre-calibration model first reproduces all 84 baseline CSVs
byte for byte, isolating these assumptions from subsequent generator changes.
The two event identities remain equivalent conditional on family and initial
loss, producing eight distinct CSV sets.

| Assumed family | Changed cells, F0 / F−2 | Maximum pre-state outcome TV, F0 / F−2 |
| --- | ---: | ---: |
| Screen | 4 / 7 | .009204 / .013716 |
| Short | 11 / 14 | .097778 / .101541 |
| Medium | 18 / 21 | .127025 / .130939 |
| Long | 15 / 18 | .127025 / .130939 |

Medium hypotheses also change the Patriots offense through opponent adjustment;
the original Denver-only observation applies only to the initial Short scenarios.
The other hypotheses change only Denver offense. Defenses and special teams
remain identical. The TV values compare modeled pre-state outcome classes;
pending fumble recoveries are unresolved, and conditional known-yard means are
not whole-play YPA. These finite hypotheses neither exhaust nor bound unknown
source truth. No additional source reconciliation or exception is established.
Reproduce with ignored `expanded_sack_counterfactuals.py`; its full cell inventory
and exact comparisons are in `sack-expanded/report.json`.

## Official gamebook located, 2026-11-06 03:28 UTC

The [NFL gamebook for Baltimore at Denver](https://www.nflgsis.com/1983/Reg/15/14403/Gamebook.pdf)
is a twelve-page scan. Page 3 identifies December 11, 1983 at Mile High and
records Denver's five sacks/38 lost yards, twelve rushes/45 yards, and three
fumbles/two lost. Page 9 independently identifies the second-and-two play at
Baltimore's 24: Elway fumbles the snap, finishes two yards behind the line, and
the scorer explicitly labels it a sack. The next play starts third-and-four at
the 26. This identifies the missing credited sack as the PFR play-167 event,
rather than the earlier lost fumble or the nullified illegal-contact sack.

This is new primary event evidence, not a count allowlist or permission to use
an arbitrary narrative loss. A source correction still needs typed provenance,
the unchanged raw-PFR identity and failing synthetic controls before production.
The play's final credited loss does not by itself establish a physical F−2
initial cell: the fumble occurs on the snap, and initial loose-ball/recovery
movement and credited sack loss remain distinct (DATA-030). Do not invent the
missing physical facts or revise official targets. The adapter/gate criterion
remains unmet until the reconciliation is implemented and regenerated.

The PDF, SHA-256 receipt, rendered pages and OCR remain in ignored
`.ai-audits/chart-confidence/gsis-1983-week15/`; critical page-3/page-9 facts were
visually checked against the scan rather than accepted from OCR alone.

## Typed reconciliation checkpoint

The bounded [source-fact capability](pfr-event-reconciliation-proposal.md) is now
implemented locally. The unchanged raw HTML, every parsed event field and the
reviewed gamebook bytes/pages are bound by hashes; a generic optional PFR CLI
input carries the facts rather than a team/count exception. The real 224-game
classification now records 1,215 sacks, 620 interceptions and 771 field-goal
attempts. Event 167 contributes a credited sack and an own-recovered passing
fumble, without a fabricated initial QT result. Twelve sack occurrences now have
unknown conditional severity. The remaining 39 unresolved recovery identities
still prevent PFR generation; this source-count checkpoint is not chart or
release acceptance. Official targets and bounds remain unchanged.

# Generated defense engine and release-gate audit

Investigation and local gate implementation, 2026-11-05. This extends the
[visual similarity audit](generated-defense-similarity-audit.md) using Paydirt's
own probability weights, priority rules and engine. No chart generator, core
engine or team data was changed by this audit.

## Blocking finding: selected fumble becomes an interception

A synthetic offense `F + 2` against defensive `INT 5` produces the following:

- `apply_priority_chart()` selects `PriorityResult.FUMBLE`, with two yards before
  the fumble. Its description says `FUMBLE!`.
- Both `resolve_play()` and `resolve_play_with_penalties()` classify the selected
  result as `ResultType.INTERCEPTION`. They inspect whether either original raw
  string contains `INT` instead of honoring the selected fumble priority.
- The full stateful engine then applies an interception and changes possession.
  In the controlled fixture the offense recovers every possible fumble roll, so
  retaining fumble priority would preserve possession.

The classification branches are in
[`play_resolver.py`](../../paydirt/play_resolver.py), immediately after B/QT
resolution in both resolver functions (original investigation lines 1004–1008
and 1509–1514). The stateful engine calls the penalty-procedure resolver and
applies the resulting type in `_apply_play_result()`.

This is confirmed unintended outcome displacement after priority selection.
It is distinct from Bowl Bound's confirmed zero tactical-profile defect.
`audit_priority_resolution()` rejects all three synthetic offense forms (`F`,
`F + 2`, `F - 2`) through both resolver routes and the full engine: nine blocking
findings in the unchanged engine. No production correction was made here.

## Tactical contrast survives in the promoted generated defenses

All 28 promoted `1983-generated` teams and all 32 `2024` teams retain tactical
contrast after their team-strength transformations and real resolver rules.
For each team, identical ordinary offense columns containing 4, 10 or 18 yards
produce six distinct A–F distributions on plays 1–7 and 9. Long Pass has five
because Standard and Spread coincide there. This is an equality of full weighted
outcomes, not merely a comparison of means or CSV uniqueness.

Every one of these 60 defenses also passed the stateful engine controls:
6 offense controls × 9 plays × 6 formations × 5 weighted defensive subrows =
1,620 engine calls per team, or 97,200 total. The controls are ordinary 4/10/18,
B, QT and protected `(7)`. They start first-and-10 at the offense's own 40, with
100% yardage factors, constant B=25 and QT=-6 tables, zero-yard returns and an
ordinary first-quarter clock. They compare actual engine outcomes with exact
priority/secondary distributions. They do not assert that protected offense must
vary across formations.

For example, with neutral source rates and ordinary 10-yard offense:

| Call | Standard | Short Yardage |
| --- | ---: | ---: |
| Line Plunge, expected credited gain | 9.222 | 2.528 |
| Draw, expected credited gain | 10.278 | 12.806 |

Thus Short Yardage buys a clear Line Plunge benefit and pays a Draw cost. No
turnover/TD branch occurs in these two controls, so these are full expected gains.
Other comparisons explicitly retain interception and touchdown probabilities.

The synthetic strength-order control holds disruption rates fixed and changes
allowed rushing/passing averages from 5.0/8.5 to 3.3/5.5. Across all 162 ordinary
4/10/18 × play × formation comparisons, the stronger defense has lower conditional
known nonturnover gain, with no ties or inversions. This is a controlled model
ordering check, not a total ranking of real teams with mixed strengths.

## Directional limitation kept visible

The gate sweeps all three ordinary offense controls for its declared directional
benefit/cost contracts; it does not narrow the sweep to hide failures. The player
[guide](../playing.md) describes Short Yardage as defending short runs, Short Pass
as defending quick passes, Long Pass as defending deep routes, and Blitz as
pressure with coverage risk. Concrete comparisons in the audit pin the tested
benefit/cost pairs relative to Standard.

Spread is described only as spread coverage. A universal promise that Spread
beats Standard against every Screen result would be invented. The audit therefore
reports that exploratory expectation separately. At neutral strength with an
ordinary four-yard Screen, Spread allows 26/9 = 2.889 yards versus Standard's
17/6 = 2.833. Parenthesized overrides replace the offensive value whereas ordinary
adjustments add to it; that nonlinearity can reverse the comparison for small
initial gains. The same direction fails in 25/28 promoted 1983 teams and all
32/32 2024 teams at that control. Every occurrence remains in the report. It is
not reported as identical formations, and it is not evidence of a universally
superior formation.

Passing controls use **conditional known nonturnover gain**, excluding unresolved
penalties, fumble recovery, interception gains/returns and touchdown yardage from
both numerator and denominator. Incompletions remain known zero-yard outcomes.
This conditional statistic is not unconditional expected yards per play. Full
weighted signatures still retain distinct event types and their probability
mass; unknown branches are never silently added as zero-yard samples.

## Reusable gate and regression evidence

[`chart_tactics_audit.py`](../../paydirt/chart_tactics_audit.py) exports:

- `resolved_outcome_distribution()`: exact primary and conditional B/QT weights,
  using the real core resolver; unresolved choices are explicit pending outcomes.
- `audit_defense_tactics()`: ordinary-control distribution contrast and declared
  directional checks, with exploratory directions separately reported.
- `audit_engine_controls()`: stateful engine agreement for the 324 distributions
  and 1,620 calls described above.
- `audit_priority_resolution()`: selected-fumble classification and possession
  controls, currently blocking.
- `audit_strength_order()`: checks an explicitly source-ordered synthetic pair.
- `audit_generated_strength_order()`: generates strong/neutral/weak and independent
  run/pass strength profiles with fixed disruption rates, checks five ordered
  pairs, and runs all three combined profiles through the stateful engine.

The physical defensive subrow masses are 12, 11, 9, 3, 1 out of 36; primary and
secondary chart rolls use the actual 216-face weights. Raw-equal offensive or
secondary cells are grouped while retaining their exact probability mass. The
scoped RNG patches are intended for a standalone, single-threaded audit.

The synthetic regressions include a mutant with six different printed formations
but equal weighted distributions: a +1 on row 1 has the same mass as +1 on rows 2
and 5 (12 = 11 + 1). That mutant is rejected. Removing Short Yardage's Draw cost
is also rejected, as is injected stateful gain drift and reversed declared
strength ordering. Mixed QT rows verify the actual secondary 216-face weights;
protected `(7)` is allowed to erase contrast. Pending fumbles and penalties retain
unknown gain. The priority mutant is rejected, while a corrected-classification
control passes both direct resolver and stateful routes.

Test-first baselines: two expected gate failures with eight passing controls for
weighted repetition and missing cost; one expected stateful-drift failure with
12 passing controls; one expected selected-fumble-displacement failure with
14 passing controls; a failing reversed-strength case; and a failing generator mutant that erases
all team-strength transformations while retaining the tactical template. The initial missing
module collection attempt was not counted as behavioral baseline evidence.
No existing test expectation was weakened. The new Spread/Screen diagnostic
explicitly corrects the initial unstated universal-screen-benefit assumption.

Run the public fixture gate:

```bash
python3 scripts/audit_generated_defense_tactics.py \
  --output .ai-audits/public-defense-tactics.json
```

Run the promoted public-provenance sets locally:

```bash
python3 scripts/audit_generated_defense_tactics.py \
  --season-dir seasons/1983-generated --season-dir seasons/2024 \
  --engine-checks all --output .ai-audits/generated-defense-tactics.json
```

The runner accepts public 2026 fixtures or reviewed-source generation manifests;
it refuses imported historical roots without public generation provenance.
The current gate exits nonzero because the global selected-fumble check fails,
even though each promoted team's tactical and stateful ordinary/B/QT/protected
controls passes. The saved promoted report composes the completed 60-team batch
with the subsequently added global priority check; no model/engine/data changed
between those checks. Reports remain ignored under `.ai-audits/`.

These controls do not establish historical accuracy, empirical formation effects,
all field-position/clock contexts, penalty decisions, return/recovery distributions
or whole-season balance. They supplement the full release regression and source
calibration audits. No imported private charts were read or exported. Tracker
review/closure remains with the parent investigation; this engine finding is open,
and no unrelated issue closure is justified by these controls.

Focused validation: 18 synthetic gate regressions plus 38 existing generator
regressions pass. The standalone public gate is expected to fail on RULE-026;
passing unit tests demonstrate detection, not permission to release the bad engine.

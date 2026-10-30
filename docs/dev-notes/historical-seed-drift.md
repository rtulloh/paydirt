# Historical regression seed drift after corrected offensive dice

Developer-only investigation; not a gameplay change or a historical-results comparison.

## Root cause

The local full-season runner retained event requirements for seeds `19831127` and
`19831624` after the offensive-dice correction in `1d34a45`. Both games still
complete and pass normal final-state/scoring validation, but no longer award an
untimed down. This failure predates the Node upgrade and lint cleanup.

A controlled in-memory comparison kept the current engine, CLI, AI, private local
data, and seeds fixed, replacing only the three offensive-dice functions with
their implementations from `1d34a45^`. Both original seeds then awarded and
announced an untimed down again (Q2 and Q1 respectively). With corrected dice,
neither did. Instrumentation also confirmed no pending extension on their
period-ending plays; this was not merely a missing announcement. The old dice
were used only for diagnosis and are not restored in the code.

## Fix and expectation changes

Retain all ten prior complete-game scenarios. Add same-matchup supplements
`19831141` (Q2) and `19831631` (Q3), independently observed to award **and play**
real untimed downs under the corrected dice, then finish without a pending
extension. The runner still requires the untimed-down announcement in both
supplements and validates every game normally. It does not search for replacement
seeds at runtime or skip a missing event.

The previous requirement that the two old seeds still exercise an extension was
incorrect after the dice distribution changed. Unit expectations now require all
12 games, with failures if either new supplement misses its event. Counts change
from 10/10 to 12/12 (one injected failure: 11/12; both missing events: 10/12).
These unit checks mock the runner and load no private charts.

Test-first baseline before changing the runner: **8 expected failures, 47 passing
controls** across `test_full_season_runner.py` and `test_untimed_down_flow.py`.
No gameplay rules, probabilities, AI policy, or final-state assertions change.
Private charts and narrative logs remain local; standings persistence is disabled.

## Validation (2026-10-26 23:27)

- Focused runner/untimed-down/documentation checks: **56 passed**.
- Real local runner: **12/12 historical reproductions, 224/224 regular-season
  games, 9/9 playoffs**, exit zero. Five regular-season ties are allowed; no
  playoff ties. Standings persistence disabled.
- Ruff passes. Fix remains uncommitted at this checkpoint.

## Punt-return recovery rolls (RULE-019, 2026-10-28)

Routing punts through the shared return resolver consumes the previously omitted
recovery dice. Seed `19831631` still completes normally but no longer awards an
untimed down. Instrumentation observed no pending untimed play, not just a missing
announcement. Retain that complete game and add same-matchup seed `19831660`,
independently observed to announce **and play** a Q2 untimed down, finish cleanly,
and pass final-state/scoring checks. Seed `19831141` remains mandatory. No runtime
seed search, altered dice, skipped games, or changed live AI.

Runner unit expectations now require all 13 games and both mandatory events:
13/13 normally, 12/13 with one injected exception, 11/13 with both events absent.
The old event requirement on `19831631` was tied to the incorrect punt dice
consumption. Test-first baseline: **8 expected failures, 47 passing controls**.
Synthetic runner tests load no private charts; private narrative logs stay local.

## Clock and AI changes (2026-10-30)

The full-season pre-push regression found that required supplements `19831141`
and `19831660` still completed but no longer exercised an untimed down after
later clock and AI changes. The 224 generated regular-season games and all
nine playoff games passed; the runner correctly failed its two historical
event requirements. Current-dice supplements `19831154` (Raiders/Eagles) and
`19831673` (Chiefs/Giants) were independently run through the complete CLI
flow. Each announced the extension, played the extra down, finished with no
pending untimed down, and passed normal score/period validation. The runner
keeps thirteen games and requires those two events. No dice, engine rules,
private charts or narrative logs were changed or exported.

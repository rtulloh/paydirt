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

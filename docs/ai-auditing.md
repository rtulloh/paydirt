# AI Play-Selection and Balance Audits

[Documentation index](README.md) · [Development guide](development.md) · [AI policy](ai-difficulty.md)

## Separation of Concerns

The testing-only harness configures production AIs, observes decisions, and reports
patterns. The AI chooses calls; the core engine resolves them. It reuses the
complete `paydirt/auto_game.py` orchestration, including penalty decisions/rerolls,
clock modifiers, scoring/kickoff chains, halftime, overtime, and untimed downs.
It does not implement another game loop, change chart odds, or save standings.
Normal `--auto` and season-management defaults remain unchanged.

This audits **live auto-game coaching**, not every interactive coaching feature.
Existing auto mode uses extra-point kicks after touchdowns and does not introduce
new two-point or explicit defensive-timeout policies here. No persistent opponent
learning file is loaded or saved, and the harness does not add opponent-tendency
observations absent from existing auto mode. Game-local executed-call history still applies.

## Commands

Run from the repository root with the normal test dependencies installed (including
pytest). The default is Hard-vs-Hard. A single public-team game:

```sh
python3 tests/run_ai_audit.py 2026/Ironclads 2026/Thunderhawks --seed 8306
```

Repeated matchup, independent game seeds, asymmetric difficulties, and CSV summary:

```sh
python3 tests/run_ai_audit.py 2026/Ironclads 2026/Thunderhawks --games 20 --away-difficulty hard --home-difficulty medium --seed 8306 --output .ai-audits/matchup.json --csv .ai-audits/matchup.csv
```

Generated season across all teams in a local season directory:

```sh
python3 tests/run_ai_audit.py --season 2026 --weeks 16 --seed 8306 --compare-balanced --output .ai-audits/public-season.json
```

The circle-method schedule uses every team once per week, alternating hosting
direction between weeks. It requires an even number of distinct teams. It is a
generated **regular season**, not the historical NFL schedule or a postseason.
Two public teams produce 16 games; 28 local teams produce 224 games. The optional
balanced comparison repeats the whole schedule, doubling those totals.
`--difficulty balanced` matches legacy auto AI; `medium` additionally enables the
production Medium team-strength adjustment, so the two are not synonymous.

For a private local season, substitute its year. Never add private charts to tests
or commit the resulting local reports. `.ai-audits/` is ignored. Reports omit
chart cells, roster names, absolute chart paths, dice details, and narrative logs.
Aggregate diagnostics derived from private data still belong locally.

## Evidence and Interpretation

JSON contains configuration, per-game seed/status/final score, and each selected
call. Its `before` record captures team/difficulty, quarter/time, score margin,
down/distance, field position, coaching mode, and selected play **before resolution**.
Ordinary Hard calls include normalized selection weights, not conversion odds.
Hurry-up primary calls also include their actual urgency-adjusted weights at every
difficulty; Hail Mary and other special decisions retain their mode without those
mixture weights. Compare clock/deficit/down/distance contexts, not only total pass share.
Unrevealed defensive selections are not supplied to offense analysis.

The separate `result` is captured after all penalty decisions, before subsequent
PAT/kickoff chains. Each selected call counts once; rerolls are not new selections.
PATs/kickoffs are game flow, not independently selected offensive calls. Preview
queries are not part of this harness and never add executed-call history.

Reports group by team, difficulty, coaching mode, down, and distance band
(1–3, 4–6, 7–10, 11+; goal-to-go distance zero shares the short band). Inspect:

- Call counts/shares, including zero shares for all nine primary plays.
- Largest-play share and distinct-play count with the sample count.
- Longest repeated-call streak within a comparable situation; intervening other
  situations do not reset it, but a different call in that situation does. Streaks
  reset at game boundaries. These are not necessarily consecutive snaps.
- Hard versus balanced groups, retaining special situations separately. Matching
  seeds do not guarantee identical game states once policies diverge.
- Pre-play probabilities/context separately from outcomes: a good choice can fail.

Groups under 30 calls are labeled small samples. Ordinary groups with at least
30 calls and a largest share of at least 50% receive an **observational warning**.
These review thresholds are reporting heuristics, not AI restrictions or universal
quality standards. Unique team strengths can justify concentration. No requirement
forces every play to appear or declares a team balanced just because it won.

`summary.calls` includes partial failed games for reconciliation;
`summary.balance_calls` and situation distributions include only completed,
validated games. A zero exit status means games/evidence passed validation, **not**
that every decision was sensible. Review warnings and record findings in the
[issue tracker](dev-notes/issue-tracker.md). CSV is a situation summary; use JSON
for per-call evidence.

## Reproducibility and Regression

Each game uses a stable SHA-256-derived seed independent of batch execution order.
The report records the derived seed; `tests.ai_audit.audit_game(GameSpec(...))` can
rerun that exact matchup directly. The CLI seed is the **master seed**, not a
recorded game seed. Configured Easy/Medium/Hard runs also seed separate offense/defense
streams per team. The balanced comparison retains plain auto's lazy stream initialization
from the game seed so observation does not change its baseline results.
Reproduction requires the same code, data, Python environment, and options; retain
the git revision alongside local reports. This is not a replay format. Runs restore
the caller's gameplay RNG, execute serially, and are not safe to run concurrently
in threads in the same process. Use separate processes for independent audits.

Missing teams/data, incomplete evidence, inconsistent scoring totals, pending
untimed downs, or reaching `--play-limit` fail the audit. Failures retain partial
evidence and exception class without exporting potentially private exception text.
A failed game does not stop later independent games. Inspect the matchup/seed
locally to diagnose errors; do not publish private chart logs.

The [mandatory full-regression checklist](../AGENTS.md#required-full-regression-before-any-push)
includes public and local full-season play-selection/balance audits **and human
review of the evidence**, in addition to unit/browser and existing postseason
checks. Unit regressions use only synthetic/public fixtures and assert policy
contracts; real-season concentration remains observational.

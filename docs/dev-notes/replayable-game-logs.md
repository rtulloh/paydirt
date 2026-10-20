# Follow-up: Replayable Game Logs for Debugging

Status: full replay work remains deferred; the narrow QB-time dice visibility fix below is queued for the next round of changes.

See the [issue files](issues/README.md) for individual priorities, status, and resolutions.

## Goal

Reproduce a reported game through the authoritative core engine from its log,
with identical state after every action and identical final statistics. Logging
all dice and decisions was intended to support this debugging workflow. Human
readable commentary alone is not a sufficient replay record.

## Evidence and current limitation

A local TB–GB historical log probe matched the opening kickoff and six following
plays using original local charts, recorded chart-row totals, and observed elapsed
time. It stopped at Q1 12:09 because the subsequent QB-time roll was missing.
This was a partial chart-input replay, not an exact RNG replay or a verification
of the final box score. No absent roll was inferred from its outcome.

Other observed gaps include:

- Missing secondary QB-time rolls, including a QB-time fumble.
- Fumble traces displaying `D:?` instead of the defensive row.
- Punt-return penalty rerolls absent from the compact trace.
- An offsetting-penalty play without its roll/reroll trace.
- Random clock samples absent; displayed timestamps only provide elapsed time.

Private logs and historical charts must remain local, ignored, and unexported.
Do not commit them or make unit tests depend on them.

## Next round: expose secondary QB-time dice

- [ ] Preserve and display the actual secondary QB-time roll and its resolved
  result, not just the initial `QT` chart entry. The current live play-test
  produced a sack/safety whose secondary roll could not be audited from the log.
- Capture the roll in the resolver/engine as structured data; CLI compact and
  normal views should display it without parsing commentary or rerolling dice.
- Test first with synthetic/public-team cases for QB-time sacks (including a
  safety), scrambles, and fumbles, plus controls for plays without QB-time rolls.
  Verify the trace agrees with the engine outcome, no unused roll is fabricated,
  and dice consumption, RNG state, and gameplay outcomes remain unchanged.
- Keep this fix independent of full replay infrastructure, AI strategy changes,
  and any attempt to reconstruct missing rolls in older logs.

## Required replay record

Prefer a versioned, structured event stream alongside human-readable output.
The engine should capture inputs at their source; UI rendering must not lose
events or infer rules from descriptions. Record:

1. Initial setup: teams, chart identifiers/content hashes, season rules, engine
   version, initial state, coin toss, possession and half-opening choices.
2. Every gameplay random input: offensive/defensive dice and row totals,
   penalties and all rerolls, QB-time, breakaway, fumble recovery/advancement,
   interceptions and returns, kicks, kick returns, and special-play rolls.
3. Every decision: play/formation calls, accepted/declined penalties and selected
   option, timeouts, no-huddle, spike, in/out-of-bounds designations, punt options,
   onside kicks, conversions, and overtime choices.
4. Clock inputs and adjustments: random time samples, timeout/spike effects,
   warnings, period transitions, overtime, and untimed downs.
5. Ordered action/event identifiers and state checkpoints sufficient to report
   the first divergence precisely, including statistical and scoring state.

Decouple gameplay replay inputs from commentary/AI randomness. Record actual
chosen inputs so replay does not depend only on a seed or unchanged RNG call
order. Define compatibility and chart/rules-version mismatch behavior explicitly.
Do not embed private chart content in exported replay records.

## Acceptance criteria and test-first workflow

- First add failing, self-contained regressions for every observed missing trace.
- Use synthetic charts or public sample teams in unit tests.
- Run a game, save its record, replay it through the real engine, and compare
  every action checkpoint plus final score, scoring log, clock/period flags,
  possession, down/distance, and all team statistics.
- Cover penalties and offsetting rerolls, QB-time sacks/fumbles, turnovers,
  special teams, scoring, clock modifiers, half transitions, overtime and
  untimed downs, in compact and normal display paths.
- Missing, malformed, duplicated, out-of-order, unused, or incompatible inputs
  must fail clearly with action/context; never silently guess or draw randomness.
- Distinguish partial legacy-log reconstruction from a fully verified replay.
- Keep private historical replay checks in standalone local integration scripts.
- Never save standings or mutate the source log/charts during replay.

## Scope note

This is separate from the current box-score accounting fixes. The existing web
saved-replay feature must be evaluated separately: saving displayed history is
not automatically a deterministic CLI-log replay facility.

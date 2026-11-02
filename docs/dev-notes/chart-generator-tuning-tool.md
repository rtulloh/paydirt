# Chart Generator Tuning Tool

Status: initial orchestration and metric-tuning implementation completed; historical 1983 and 2024 calibration runs remain local verification work tracked by DATA-011.

## Purpose

Chart creation uses two tools with different responsibilities:

1. The source generator converts aggregate statistics and complete play by play into a deterministic baseline chart set.
2. [`tune_charts.py`](../../tune_charts.py) measures generated candidates through the real game engine and produces a reproducible calibration profile for another generator run.

The tuning tool adjusts generator parameters. It never edits generated CSV cells directly. Given the same source files, profile, and seed, the source generator reproduces the same charts.

## Why a Second Tool Is Needed

An offense never runs without a defense, and chart symbols interact with field position, play selection, penalties, clock rules, and the defense chart. Matching an isolated offense-column mean cannot establish that the combined engine produces realistic football.

The developer-created 1983 charts also show that source outcomes do not map literally to chart symbols:

- Run columns and Breakaway contain no `TD` cells.
- Pass columns contain only 27 `TD` cells across 28 teams, although the season contained hundreds of touchdown passes.
- Direct numeric pass gains reach 77 on Screen, 35 on Short, 46 on Medium, 99 on Long, and 68 on T/E S/L.
- Kickoff Return and Punt Return contain no `TD` or `B` cells.
- Interception Return contains 17 `TD` cells and no `B`; large numeric interception returns can also score through field position.

The baseline adapters therefore preserve observed yardage for scoring plays. Sparse guaranteed-touchdown symbols are a residual engine-calibration decision, not a direct transcription of the source touchdown flag.

## Sample Size

Use complete regular seasons and count only regular-season team-games toward the calibration minimum. Each repetition must replay the actual regular-season schedule so the opponent and home/away weighting agrees with the play-by-play source. Random pairings would tune a different matchup distribution; a balanced round robin is useful only as a separate schedule-sensitivity diagnostic. Playoff appearances are unequal and must not increase one team's training weight.

The standard plan is:

| Phase | Seasons | 1983 team-games (16 games/season) | 2024 team-games (17 games/season) | Purpose |
|---|---:|---:|---:|---|
| Pilot | 16 | 256 | 272 | Confirm commands, reports, and broad direction |
| Training | 64 | 1,024 | 1,088 | Select generator adjustments |
| Held-out validation | 256 | 4,096 | 4,352 | Measure the selected profile on unused seeds |

About 1,000 games per team is the primary tuning target. It stabilizes common completion, yardage, sack, turnover, scoring, and play-volume metrics without making every candidate a 256-season run. Rare chart cells still require league-wide pooling. A 1/216 cell needs roughly 6,500 calls of that specific play family to produce about 30 observations, so literal pass `TD` and interception-return `TD` mass should not be estimated independently for every team.

The engine report records `team_games` for every team. The tuner rejects a candidate if even one team is below `training_seasons * games_per_team_per_season`. Validation applies the same check with the held-out season count.

## Commands

Both play-by-play generators accept a JSON profile:

```sh
python generate_nflverse_charts.py \
  ... \
  --calibration-profile /path/to/profile.json \
  --output /path/to/candidate
```

Explicit adjustment flags override the corresponding profile values for focused experiments. The effective profile is written to `generation-manifest.json`.

Run the tuner with a new empty workspace:

```sh
python tune_charts.py \
  --config /path/to/2024-tuning.json \
  --workspace .ai-audits/chart-tuning/2024 \
  --training-seasons 64 \
  --validation-seasons 256
```

The configuration uses command arrays rather than shell strings. Supported placeholders are:

- `{profile}`: candidate calibration-profile JSON.
- `{candidate}`: candidate output directory.
- `{report}`: engine calibration report that the simulation command must write.
- `{seasons}`: training or validation season count.
- `{seed}`: phase-specific master seed.
- `{phase}`: `training` or `validation`.
- `{iteration}`: numeric candidate or `selected`.
- `{workspace}`: tuning workspace.

Example configuration shape:

```json
{
  "games_per_team_per_season": 17,
  "training_seed": 8306,
  "validation_seed": 908306,
  "max_iterations": 24,
  "initial_profile": {
    "run_yard_multiplier": 1.0,
    "pass_completion_adjustment": 0.0,
    "pass_interception_adjustment": 0.0,
    "pass_pressure_adjustment": 0.0,
    "pass_yard_multiplier": 1.0
  },
  "targets": {
    "completion_rate": {"value": 0.6529, "tolerance": 0.005},
    "interception_rate": {"value": 0.0233, "tolerance": 0.002},
    "sack_rate": {"value": 0.067, "tolerance": 0.004},
    "yards_per_pass_attempt": {"value": 7.13, "tolerance": 0.15},
    "rushing_yards_per_attempt": {"value": 4.4, "tolerance": 0.12},
    "points_per_team_game": {"value": 22.9, "tolerance": 0.6}
  },
  "bounds": {
    "pass_completion_adjustment": {"minimum": -0.08, "maximum": 0.08, "step": 0.005},
    "pass_interception_adjustment": {"minimum": -0.03, "maximum": 0.03, "step": 0.001},
    "pass_pressure_adjustment": {"minimum": -0.04, "maximum": 0.04, "step": 0.002},
    "pass_yard_multiplier": {"minimum": 0.75, "maximum": 1.3, "step": 0.02},
    "run_yard_multiplier": {"minimum": 0.75, "maximum": 1.3, "step": 0.02}
  },
  "generator_command": [
    "python3", "generate_nflverse_charts.py", "...",
    "--calibration-profile", "{profile}", "--output", "{candidate}"
  ],
  "training_command": [
    "python3", "/path/to/local-calibration-runner.py",
    "--season-dir", "{candidate}", "--seasons", "{seasons}",
    "--seed", "{seed}", "--policy", "chart-focused", "--output", "{report}"
  ],
  "validation_command": [
    "python3", "/path/to/local-calibration-runner.py",
    "--season-dir", "{candidate}", "--seasons", "{seasons}",
    "--seed", "{seed}", "--policy", "hard", "--output", "{report}"
  ]
}
```

Historical play by play, private charts, actual-game files, and full simulation reports remain local and ignored.

## Tuning Loop

For each candidate profile, the tool:

1. Writes the profile into a fresh candidate directory.
2. Invokes the configured source generator.
3. Runs the configured 64-season training command with deterministic seeds.
4. Rejects incomplete per-team samples.
5. Compares engine observations with target league metrics using tolerance-normalized squared error.
6. Updates one bounded calibration family at a time in the documented order.
7. Retains every attempted profile, metric assessment, proposal, command log, and candidate report.
8. Selects the lowest-loss candidate seen, even when the iteration limit is reached.
9. Runs the selected candidate through a separate 256-season command and unused seed.
10. Writes `selected-profile.json`, `validation-report.json`, and `tuning-report.json`.

Coordinate descent is intentionally conservative and visible. Each proposal names the metric, parameter, old value, and new value.

## Calibration Order

Tune parameters in this order because later metrics depend on earlier ones:

1. Completion probability.
2. Interception probability.
3. Pressure and sack probability.
4. Resolved passing yardage.
5. Resolved rushing yardage and breakaway behavior.
6. Fumble-loss and field-goal rates when source-derived values are insufficient.
7. Sparse symbolic passing-touchdown mass after yardage and turnover rates are stable.
8. Sparse guaranteed pick-six mass only if numeric interception returns still underproduce defensive scores.

The implemented profile currently covers the first five generator controls. Symbolic touchdown controls should be added only with engine observations and bounds that distinguish ordinary scoring from guaranteed chart symbols.

Play volume and clock behavior are reported, but a chart parameter must not compensate for an engine clock defect. Standings, playoff qualification, and Super Bowl pairs are validation outputs rather than direct optimization targets.

## Play Selection

The training simulation command should use deterministic, team-independent but situation-aware play selection. It should retain ordinary down, distance, field-position, fourth-down, and clock decisions while disabling team-strength and Hard chart-analysis coaching. This prevents a team's own chart strength from choosing its sample while preserving a plausible mix of calls and defenses.

A 2026-11-01 pilot showed why a fixed random play-family mix is unsuitable: the same generated charts produced materially different completion, interception, and sack rates under a fixed mix, generic situation-aware policy, and Hard analysis. The held-out validation command therefore uses Hard-vs-Hard play selection and reports policy sensitivity instead of assuming one strategy-independent rate.

These policies belong in the simulation harness configured by the tuner. They are not player-facing AI difficulty modes. The complete command sequence is documented in the [two-phase operator workflow](../chart-generation-workflow.md).

## Acceptance Checks

A selected profile must satisfy its configured chart-boundary tolerances for completion rate, yards per pass attempt, rushing efficiency, sacks, and interceptions under the training policy. Fumble losses and field-goal success must match their supplied source rates when those inputs are available. Scoring, turnovers, total yards, and offensive play volume remain required diagnostics; a chart parameter must not compensate for a clock, pace, fourth-down, or AI-policy defect. Every game must finish, and every playoff game used for the separate season assessment must produce a winner.

The final season assessment should also include team-level win, points-for, and points-against correlations; playoff overlap; champion counts; and unique Super Bowl pair counts. These results show whether team strengths trend correctly without requiring exact historical reproduction.


## 2026-11-01 Historical Verification

The complete 64-season training and 256-season held-out validation workflow finished for 1983 and
2024. The selected profiles were:

- 1983: run yard multiplier `1.0`, completion adjustment `-0.05`, interception adjustment `-0.07`,
  pressure adjustment `-0.07`, pass yard multiplier `1.55`.
- 2024: run yard multiplier `1.0`, completion adjustment `0.02`, interception adjustment `-0.06`,
  pressure adjustment `-0.02`, pass yard multiplier `1.30`.

The chart-focused training policy met every configured target tolerance. The Hard validation policy
completed every game but showed meaningful strategy sensitivity, especially the low 1983
interception and sack rates and high 2024 pass yardage. The selected chart profile therefore remains
the chart-focused result; the Hard report is retained as evidence for later AI and engine assessment.
Focused full-season runs and symbol audits passed after promotion. Manual playtesting can use
`seasons/1983-generated` and `seasons/2024`.

### Defensive interception concentration

A later manual Eagles-Cowboys playtest found that the original defensive calibration crossed a
source interception-rate threshold by replacing one formation-D Short Pass result on an 11/36
sub-row. That raised the call-specific defensive interception probability from 3/36 to 14/36 and
made a single tactical matchup dominate the game even though league averages could look plausible.

The generator now allocates defensive interception strength across sub-row-five cells. Each added
or removed cell changes one specific play-and-formation matchup by only 1/36. The two-phase process
must therefore audit both aggregate interception rates and the largest call-specific probability
change; aggregate validation alone cannot detect a concentrated chart trap. DATA-012 records the
manual evidence and the post-fix calibration results.

The 2026-11-02 rerun retained both selected profiles. All five 64-season chart-focused targets
remained within tolerance. The 256-season Hard validation completed every game; 1983 interceptions
increased from 1.25% to 1.96%, while 2024 changed from 1.30% to 1.11%. For the original 47-pass
Eagles call mix, Dallas-chart expected interceptions fell from 2.50 to 1.58 and the five-or-more
tail probability fell from 6.84% to 1.87%. Historical-schedule runs and generated-chart loading
checks passed before the corrected defenses were promoted.

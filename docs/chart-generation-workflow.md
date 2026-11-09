# Two-Phase Chart Generation Workflow

[Documentation index](README.md) · [Chart generator reference](chart-generator.md) · [Calibration process and reference profiles](chart-calibration.md)

Use this workflow for every generated historical season. It keeps source conversion separate from
engine calibration and leaves an audit trail that another developer can reproduce.

## Inputs

Prepare these files outside the published tree:

- Complete regular-season play by play when a suitable source exists.
- One normalized aggregate-stat JSON file per team.
- A source abbreviation to team-directory JSON map.
- A template season containing the year rules file, team metadata, and optional rosters.
- The historical regular-season schedule for simulation.
- League target metrics calculated from the same source season.

Keep downloaded pages, raw datasets, schedules, classified audit rows, and simulation reports in an
ignored directory such as `.ai-audits/chart-generation/`. Only reviewed generated charts and their
manifest are promoted into `seasons/`.

The generated season directory must begin with its year: `1983` and named variants such as
`1983-trial-01` both load `1983.yaml` from their root. The engine rejects a numeric candidate
directory such as `/000` when its YAML declares season 1983. The examples below use year-only
directories to keep packaging paths consistent.

## Phase 1: Generate the Source Baseline

Start with a neutral calibration profile:

```json
{
  "run_yard_multiplier": 1.0,
  "pass_completion_adjustment": 0.0,
  "pass_interception_adjustment": 0.0,
  "pass_pressure_adjustment": 0.0,
  "pass_yard_multiplier": 1.0
}
```

For archived Pro Football Reference HTML:

```sh
python3 generate_pfr_charts.py \
  --html-dir /path/to/pfr-html \
  --stats-dir /path/to/team-stats \
  --template-season /path/to/template/1983 \
  --team-map /path/to/pfr-team-map.json \
  --output .ai-audits/chart-generation/baseline/1983 \
  --audit-dir .ai-audits/chart-generation/baseline/classified-1983 \
  --through-date 19831219 \
  --seed 8306 \
  --calibration-profile /path/to/neutral-profile.json
```

For nflverse data:

```sh
python3 generate_nflverse_charts.py \
  --pbp /path/to/play_by_play_2024.csv.gz \
  --stats-dir /path/to/team-stats \
  --template-season /path/to/template/2024 \
  --team-map /path/to/nflverse-team-map.json \
  --output .ai-audits/chart-generation/baseline/2024 \
  --audit-dir .ai-audits/chart-generation/baseline/classified-2024 \
  --seed 8306 \
  --calibration-profile /path/to/neutral-profile.json
```

The nflverse adapter excludes explicitly identified interception-return fumbles from
original-offense passing/rushing-fumble calibration, preserving the interception
and return representations. Unknown interception-fumble ownership and multiple-
fumble sequences require separate supported event facts; generation stops before
fitting and records them in `unsupported-source-fields.json`. A global fumble/lost
flag does not establish each fumbler's credited class or recovery.

Both generators accept an explicit experimental `--fumble-gain-policy`:
`known_physical_v1` requires reviewed physical initial gain;
`credited_fumble_proxy_v1` may use known credited yards when that physical fact
is unknown; `source_reported_gain_proxy_v1` also allows an actor-bound, explicitly
scoped reported primary gain when individual credit remains unknown. Each model
keeps reported, credited and physical facts separate. Supported physical evidence
wins, then reviewed credit, then the explicit reported proxy. Unknown class,
recovery or required number remains unsupported. Bare exchanges, return numbers,
QB position and box residuals cannot fill a missing originating fact.

The separately selected `historical_fumble_class_proxy_v1` adds user-authorized
modeled role assumptions after supported source facts. An identified QB gain in
[-1,1] models a rushing snap; a gain below -1 models a sack. For an unknown role,
below -1 models a QB sack, [-1,1] a QB snap, (1,5] a running back, and above five a
receiver. Known non-QB positions without supported class and positive QB gains
above one remain unsupported. The primary gain must still belong to the same
actor; recovery movement cannot supply it. Projections keep inferred class/role
outside source facts. PFR manifests and portable source contracts bind the exact
version-1 `modeled_fumble_assumptions` metadata and counts with unverified-truth
flags. This policy does not establish the former strict source-completeness claim
or historical fit; see the [current boundary](dev-notes/historical-source-completion-boundary.md).

Explicit policies also preserve a supported retained fumble followed by an
incomplete pass as `F INC`. This joint subtype has zero passing credit and no
modeled physical gain; it is excluded from ordinary F/QT and stochastic recovery
allocation. Unsupported compound sequences still block fitting. Omitting the flag
retains the legacy path and does not opt into these experiments.

The nflverse audit directory retains `fumble-gain-projections.json`, including
partial supported projections when generation stops. PFR retains projections in
its classification ledger; schema-3 reviewed event sidecars carry the credited
class/yards alongside the existing raw-play and official-document bindings. Optional
`loose_ball_yards` and `recovery_advance_yards` are separately reviewed signed
integers or null; omission means no review, while null means reviewed but unknown.
Movement uses the original offense's direction as positive; an opponent return
has negative advance. These fields do not replace physical initial gain or alter
the credited-yard proxy.
Schema-4 sidecars may separately bind an originating class while leaving both
credited fields null. Only the reported-proxy policy can combine that reviewed
class with an unambiguous actor-bound source number. Reviewed aborted-field-goal
records also preserve no-kick snap events, separate fumbling and credited actors,
and nullable movement. With an explicit credited or reported proxy policy, reviewed
zero rushing credit and known individual ownership support `F SNAP KEEP 0` or
`F SNAP LOST 0` in the field-goal column. These consume a rushing snap without a
kick attempt or recovery reroll. Zero is a credited-gain proxy, not inferred physical
movement. Missing credit or ownership, nonzero credit, and physical-policy-only
requests remain unsupported and block fitting.
Schema-5 `reported_primary_yards` may bind an independently reviewed scoped
number when the raw primary clause is malformed. Exact actor/team, primary class
and one same-actor occurrence are required; supported raw-number conflicts and
lateral/compound scope stay rejected. This supplies reported proxy gain only,
never missing physical or official credited gain.
Manifests record the policy, and portable source recipes must request the exact
same policy. Partial ledgers and matching source counts do not establish chart
accuracy or readiness. See the [bounded experiment](dev-notes/fumble-source-credit-proposal.md)
for its current evidence and unresolved source/model limits.
Review `generation-manifest.json` before simulation. Confirm the expected team and game counts,
classified-outcome count, fallback columns, source diagnostics, and effective neutral profile. Audit
run cells for direct gains above 18, and audit offense, defense, and return charts for unexpected
`TD`, `B`, `QT`, or invalid symbols.

## Pilot: Measure the Neutral Boundary

Run 16 complete regular seasons before choosing tuning values. Replay the season's actual
regular-season schedule on every repetition. This preserves the opponent frequencies, home/away
exposure, and schedule weighting represented in the source play by play. Random pairing and a
balanced round robin may be used as schedule-sensitivity diagnostics, but they are not tuning
targets. Every team must receive the complete historical sample: 256 team-games for a 16-game
season or 272 for a 17-game season.

Freeze and disclose the training policy before fitting. The current
[release gate](chart-validation.md) fixes normal offense/defense weights while
retaining legal situational, fourth-down and clock decisions, without Hard-mode
chart analysis. Different policies can materially change interceptions and sacks;
Hard and legacy balanced replays measure sensitivity separately. For the active
chart-confidence assignment, its fixed seed, sample and held-out contract takes
precedence over the illustrative tuner configuration below.

The simulation command configured for the tuner must write this shape:

```json
{
  "league": {
    "completion_rate": 0.65,
    "interception_rate": 0.02,
    "sack_rate": 0.07,
    "yards_per_pass_attempt": 7.1,
    "rushing_yards_per_attempt": 4.4
  },
  "teams": {
    "Example": {"team_games": 272}
  }
}
```

Include raw counts and the other observer metrics in the real report. The tuner checks
`team_games` for every team and rejects partial samples.

## Phase 2: Train and Validate

Create a local JSON configuration for [`tune_charts.py`](../tune_charts.py). Generator output must
include the year below each candidate directory:

```json
{
  "games_per_team_per_season": 17,
  "training_seed": 241000,
  "validation_seed": 249000,
  "max_iterations": 12,
  "initial_profile": {
    "run_yard_multiplier": 1.0,
    "pass_completion_adjustment": 0.0,
    "pass_interception_adjustment": 0.0,
    "pass_pressure_adjustment": 0.0,
    "pass_yard_multiplier": 1.0
  },
  "generator_command": [
    "python3", "generate_nflverse_charts.py", "...",
    "--calibration-profile", "{profile}",
    "--output", "{candidate}/2024"
  ],
  "training_command": [
    "python3", "/path/to/calibration-runner.py",
    "--season-dir", "{candidate}/2024",
    "--seasons", "{seasons}",
    "--seed", "{seed}",
    "--policy", "chart-focused",
    "--output", "{report}"
  ],
  "validation_command": [
    "python3", "/path/to/calibration-runner.py",
    "--season-dir", "{candidate}/2024",
    "--seasons", "{seasons}",
    "--seed", "{seed}",
    "--policy", "hard",
    "--output", "{report}"
  ]
}
```

The complete configuration also supplies target values, tolerances, and bounds for each profile
field; see the [tuning tool design note](dev-notes/chart-generator-tuning-tool.md).

Run the standard sample plan in a new empty workspace:

```sh
python3 tune_charts.py \
  --config /path/to/season-tuning.json \
  --workspace .ai-audits/chart-generation/tuning/2024 \
  --training-seasons 64 \
  --validation-seasons 256
```

Training gives at least about 1,000 team-games per team. Validation uses unused seeds and 4,096
team-games per team for 1983 or 4,352 for 2024. Preserve `tuning-report.json`,
`selected-profile.json`, all candidate reports, and command logs locally.

Tune completion, interceptions, pressure, passing yardage, and rushing yardage in that order. Review
points, total yards, play volume, turnovers, field goals, standings, and playoffs as diagnostics.
Do not change chart strength to hide an engine clock, pace, fourth-down, or AI policy problem.
Differences between the chart-focused and Hard policies are evidence that must be reported, even
when the chart-focused candidate meets its target tolerances.

## Promotion and Playtest Readiness

A season is ready for manual playtesting after all of these checks complete:

1. The baseline manifest has complete expected source coverage and no unexplained fallbacks.
2. Symbol and direct-yard audits pass. Every team has at least one penalty result in each of the
   kickoff, kickoff-return, punt, punt-return, interception-return, and field-goal columns.
3. Defensive interception audits show no source-rate threshold that changes one call-specific
   result by more than one 1/36 sub-row unit.
4. Every team meets the 64-season training minimum.
5. The selected profile completes the 256-season held-out Hard run without incomplete games.
6. The selected profile is recorded in the generated `generation-manifest.json`.
7. A focused full-season sanity run completes and reports standings, playoffs, scoring, and team
   statistics.
8. The selected year directory is copied into its final published location while preserving
   `ATTRIBUTION.md` and the season rules file.

Use numeric season directories in both source and packaged builds: `seasons/1983`
and `seasons/2024`. Keep private comparison charts in ignored local audit storage
outside `seasons/`. Never promote an intermediate candidate or raw source artifact.

After promotion, start with a few manual games that exercise strong and weak offenses, turnovers,
long runs, pass depth, field goals, punts, and overtime. Record any chart or engine findings in the
developer issue tracker before changing the profile again.

The dated reference runs below describe earlier generator/runtime versions. Their selected
coefficients are historical experiment records; use the [verified released-profile table](chart-calibration.md#released-starting-profiles)
when choosing a current starting point, and revalidate it for the new season.

## 2026-11-01 Reference Run

The first complete use of this workflow selected these profiles:

| Season | Completion | Interception | Pressure | Pass yards | Run yards |
|---|---:|---:|---:|---:|---:|
| 1983 | -0.05 | -0.07 | -0.07 | 1.55 | 1.00 |
| 2024 | +0.02 | -0.06 | -0.02 | 1.30 | 1.00 |

The 64-season training samples provided 1,024 team-games per 1983 team and 1,088 per 2024 team.
The 256-season held-out samples provided 4,096 and 4,352 team-games per team respectively. All
five configured training metrics met tolerance, and every validation game completed. Hard play
selection materially reduced 1983 interceptions and sacks and increased 2024 pass yardage, so the
reports retain both policies rather than treating the Hard distribution as a second chart target.

The promoted charts passed the result-symbol validator and direct rushing gains remained capped at
18 yards. A focused historical-schedule sanity run completed 224 regular-season and nine postseason
games for 1983, plus 272 regular-season and 13 postseason games for 2024. The reviewed outputs are
`seasons/1983` and `seasons/2024`; they are ready for manual playtesting.

## 2026-11-02 DATA-012 Validation

After defensive interceptions were distributed across low-mass sub-row-five cells, the same
selected profiles again passed all five 64-season chart-focused tolerances. Each 1983 team supplied
1,024 training team-games and each 2024 team supplied 1,088. The held-out 256-season Hard runs
completed 57,344 and 69,632 games with 4,096 and 4,352 team-games per team.

The 1983 Hard interception rate rose from 1.25% to 1.96%, with scoring and volume at 23.76 points
and 61.45 plays per team-game. The 2024 Hard interception rate changed from 1.30% to 1.11%, with
22.14 points and 61.22 plays per team-game. The 2024 chart-focused interception rate moved closer
to its source target, from 3.12% to 2.79% against 2.17%. The historical-schedule sanity runners
again completed 224 regular-season plus nine postseason games for 1983 and 272 plus 13 for 2024.
All generated teams loaded successfully, no direct run exceeded 18 yards, and generated CSV files
used LF line endings.

## Completeness gate after generator corrections

Both source generators now write `chart-audit.json` and record observed versus modeled source
features in the manifest. Review the [completeness audit](dev-notes/generated-chart-completeness-audit.md)
and all 54 combined primary play/formation rates before promotion. A clean structural audit verifies
mechanisms, not historical calibration. Corrections to sampling, quantization, or source coverage
require a fresh calibration assessment; previously recorded training/validation results apply to
the earlier charts.

The November 2 DATA-014 review renewed 64-season training for both seasons without widening any
of the five configured tolerances. The 1983 profile changed to -0.06 completion adjustment and
1.025 rushing-yard multiplier; the other settings and the 2024 profile remain as listed above.
The final matched comparison covers eight actual seasons per chart set and policy. The renewed
256-season held-out Hard assessments cover 57,344 games for 1983 and 69,632 for 2024, with complete
per-team samples and no incomplete games. Their event and efficiency rates still differ materially
from the chart-focused targets; passing every game is not a statistical fit under both policies.
Keep source defaults, penalty-frequency differences, scoring,
and pace limitations visible in the completeness report. These checks establish readiness for a
mechanics playtest rather than historical equivalence.

The subsequent RULE-022/RULE-023 clock fixes change play volume and seeded
trajectories. The fitting results above describe the earlier engine; current
game-completion and AI audits do not renew those statistical tolerances. Run
the documented training/held-out workflow again before claiming a fit under
the revised clock. Sparse symbolic passing-TD experiments remain deferred
under DATA-015; the current profiles preserve numeric scoring yardage.

The versioned historical option `historical_fumble_class_proxy_v2` additionally
models known RB/FB, C and WR/TE roles and positive QB rushes, while preserving
observed-class precedence. Its optional `--fumble-exclusion-policy
historical_isolated_fumble_exclusions_v1` retains unresolved events in the source
ledger but omits them uniformly from fitting. Portable manifests and contracts
must bind the exact assumption and exclusion disclosures, including full/fitted
counts, event hashes, reasons and team impacts. This modeled scope never asserts
complete historical source facts or changes accuracy tolerances. See the
[historical completion boundary](dev-notes/historical-source-completion-boundary.md).

CI validates the committed output through `scripts/audit_public_charts.py` with
expected cohort counts. This source-free check covers structure, actual decoder
coverage, loadability and exact mechanics. It does not regenerate historical
sources or certify historical accuracy. Private source reproduction and deeper
64-repetition fit checks remain local maintainer evidence; remote source hosting
and repository URL/SHA variables are not release requirements. Keep raw source
and local provenance archives out of CI/release artifacts.

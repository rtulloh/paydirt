# Chart Generation and Excel Import

[Documentation index](README.md) · [Seasons and file formats](seasons.md)

Paydirt has two separate chart tools:

- [`generate_charts.py`](../generate_charts.py) creates a new statistical estimate from
  normalized season totals and optional classified play outcomes.
- [`extract_charts.py`](../extract_charts.py) converts an existing formatted Excel chart.

Both write the same game CSV format. Generate into a staging directory because existing
files are overwritten.

Before choosing a historical season, consult the [source coverage reference](dev-notes/source-season-coverage.md) for provider ranges, access limits and known gaps.

## Generate a Statistical Chart

The statistical generator uses the real chart dice distribution: rows 10 through 39
represent 216 equally likely three-die combinations with unequal row weights. Season rates
set symbolic outcome frequency and numeric strength. Symbolic outcome classes reserve distinct
rows, and a subset-sum allocator chooses the closest available dice probability without allowing
later classes to overwrite earlier ones. A stable generation seed makes an invocation
reproducible, including finite quantile assignment. Changing it can change weighted
gains; it is not a layout-only transformation.

The allocator compares attainable mass directly with the unrounded target.
Equivalent masses reserve rows for later event families. QT and QT* share one
pressure allocation before their variants are distributed. Empirical generation
reports requested and represented symbolic variants, including omissions below
finite resolution, in `generation-manifest.json`; these are modeled column
inputs rather than raw source event counts.

A supported retained fumble followed by an incomplete pass uses `F INC` in a
primary passing column. Its joint occurrence stays separate from ordinary F and
QT allocation, while remaining one incomplete attempt. It does not contribute to
the stochastic fumble-recovery denominator. The source ledger retains the event
and leaves internal physical movement unknown. Finite representation is disclosed
alongside other variants; fumble priority can suppress defensive INT, QT and TD
outcomes, so preserving incomplete mass does not establish unchanged engine risk.

After quantization, `exact-token-mass-primary-exchanges-v1` corrects constrained
primary masks using exchanges of up to three rows of one complete token against
up to three rows of another, with exactly equal physical mass on both sides.
This preserves each raw value and flag variant's calibrated probability exactly,
while allowing its printed count and weight-group inventory to change. BLACK
positions and all dependent tables stay fixed. The original empirical quantizer
remains the probability target; this step changes no source or calibration target.
Its joint objective includes exact tokens, families, flags, numeric bands and the
actual viewer color unions. It records every exchange and exact mass checks
under `primary_layout.allocation`.

Then `equal-weight-primary-outcome-dispersion-v3` first reduces
contiguous BLACK runs and blocks in the nine primary offense columns, then
freezes that BLACK map and jointly disperses exact tokens, result families,
penalties, viewer colors, sideline/replacement flags and numeric gain/loss bands. The second
stage minimizes frequency-normalized runs, aligned rows across every call pair,
and adjacent 2-by-2-block costs.
It swaps whole tokens only between rows with exactly equal physical dice weight,
preserving every value and marker at its original probability. Supplements,
recovery data, defense and special teams stay fixed. Because feature frequencies
and neighboring columns are scored across the whole primary grid, changing one
input column can relocate tokens in another column. The unaffected column's
quantized full-token probability distribution stays identical; printed row
positions and weight-group inventories need not. Existing empirical pooling into
TE Short/Long still applies.
Each team's manifest records both stages' metrics, swap counts and the exact
per-weight token-inventory check against the corrected allocation under
`primary_layout`. Each search reaches a
local optimum; fixed-weight rows and competing features can leave clusters, and
an individual category need not improve on every step. There is no universal run
cap. Retained patterns and per-category tradeoffs require review; a lower total
cost alone cannot clear them. This placement check does not establish historical accuracy or change the
chart-confidence release hold.

Aggregate totals provide a fallback estimate when complete play-by-play is unavailable. They
do not uniquely determine an original chart. For example, one passing total does not reveal
which attempts were screens, short passes, medium passes, long passes, or tight-end passes.
When a complete, suitable play-by-play source is available, use classified full-season outcomes
as the primary input and retain aggregate totals for calibration and sparse-column fallback.

Create a JSON file such as `team-stats.json`:

```json
{
  "season": 2026,
  "team_name": "Example Foxes",
  "short_name": "FOX '26",
  "offense": {
    "rushing": {
      "attempts": 480, "yards": 2160, "touchdowns": 18,
      "fumbles": 12, "fumbles_lost": 6, "out_of_bounds": 38
    },
    "passing": {
      "attempts": 520, "completions": 338, "yards": 4056,
      "touchdowns": 30, "interceptions": 12, "sacks": 32, "sack_yards": 220,
      "fumbles": 4, "fumbles_lost": 2, "out_of_bounds": 66
    }
  },
  "defense": {
    "rushing": {"attempts": 440, "yards": 1760, "touchdowns": 12},
    "passing": {
      "attempts": 560, "completions": 336, "yards": 3920,
      "touchdowns": 24, "interceptions": 16, "sacks": 40, "sack_yards": 280
    }
  },
  "special_teams": {
    "kickoff_return": {"attempts": 54, "yards": 1188},
    "punt": {"attempts": 72, "yards": 3024, "blocked": 1},
    "punt_return": {"attempts": 38, "yards": 380},
    "interception_return": {"attempts": 16, "yards": 192},
    "field_goal": {"attempts": 32, "made": 25, "long": 52},
    "field_goal_by_distance": [
      {"distance": 30, "attempts": 10, "made": 9},
      {"distance": 45, "attempts": 12, "made": 9},
      {"distance": 55, "attempts": 10, "made": 7}
    ],
    "extra_point": {"attempts": 30, "made": 29}
  }
}
```

Run the generator from the repository root:

```sh
python generate_charts.py team-stats.json --output /path/to/staging/2026/Foxes
```

To keep a generated historical comparison set beside its source charts, use a suffixed season
directory such as `seasons/1983-gen/`, copy the base `1983.yaml` rules file into it, and invoke
auto games with the complete team paths. See [Seasons and team data](seasons.md#adding-a-season).

### Classified Full-Season Outcomes

For closer team-specific results, normalize play-by-play or reviewed film into a CSV with
`unit`, `chart`, and `result` columns:

```csv
unit,chart,result
offense,line_plunge,3
offense,line_plunge,F
offense,screen,BLACK
offense,screen,12
special_teams,punt,42
special_teams,punt,BK -10
```

Valid offense chart names are `line_plunge`, `off_tackle`, `end_run`, `draw`, `screen`,
`short_pass`, `medium_pass`, `long_pass`, `te_short_long`, `breakaway`, and `qb_time`.
Valid special-teams names are `kickoff`, `kickoff_return`, `punt`, `punt_return`,
`interception_return`, and `field_goal`.

Each supplied column replaces its aggregate estimate. Unspecified columns still use season
totals. When classified short, medium, or long passes are available without a separately
classified `te_short_long` sample, the generator builds that route column from the combined
observed pass outcomes. The generator validates every normalized result before generation,
preserves numeric out-of-bounds markers such as `4*`, approximates symbolic frequencies with
whole chart-row weights, and fills unmarked numeric rows from the observed yardage distribution.
Primary rushing columns cap direct numeric gains at 18 yards. For empirical columns, gains of
19 yards or more determine the rare `B` trigger frequency, while the separate Breakaway column
is learned from the full distribution of observed gains of 10 yards or more. Aggregate fallback
columns apply the same direct-gain cap to their modeled distribution. This keeps ordinary long
gains field-position aware and uses the two-stage chart mechanism for exceptional runs.

When empirical QB Time outcomes and pass-event calibration are supplied, primary
QT allocation uses that team's physical conditional sack/scramble mix. It reserves
the neutral defense's QT contribution and uses core priority survival, including
protected primary fumbles. The reference mix is the declared chart-focused pass
and defense mix, not recovered historical route intent. Numeric zero is a scramble;
`SACK 0` in QB Time explicitly records a nonfumble sack with zero yards lost;
`SACK 0*` retains its sideline marker. This token is invalid in primary,
Breakaway and special-teams columns. QT F0 is a real sack fumble before any
recovery movement. Official sack rate excludes
scrambles from attempts plus sacks. Infeasible targets and missing conditional
sack support raise an error instead of inventing negative QT yards. Full engine
replay remains the fit measurement.

```sh
python generate_charts.py team-stats.json \
  --plays classified-plays.csv \
  --output /path/to/staging/2026/Foxes \
  --seed 8306
```

The input boundary is source neutral. A Pro-Football-Reference, Stathead, nflverse, official
gamebook, or film workflow must first decide which Paydirt play column and result each play
represents. Keep licensed or private source data outside the repository.

### Play-by-Play Source Policy

Use complete regular-season play-by-play whenever a suitable source is available. The source
adapter must retain opponent identity, accepted penalties, field-goal distance and result,
fumble-loss events, empirical out-of-bounds markers, and observed yardage, including the yardage
of scoring plays. For kickoff, kickoff-return, punt, punt-return, interception-return, and
field-goal charts, retain both accepted and declined non-offsetting fouls: a chart penalty cell
represents a called foul, and the engine decides whether the resulting penalty is accepted. Assign
the result relative to the chart owner (`OFF` for that team and `DEF` for its opponent). The
baseline generator does not translate a source touchdown flag directly into
a guaranteed chart `TD`. High numeric gains remain field-position aware and can score normally.
Aggregate-only generation is an explicit fallback for a season without complete play-by-play or
for empirical columns below the minimum sample threshold.

Chart creation uses two tools. The source generator produces a deterministic baseline from the
source evidence. [`tune_charts.py`](../tune_charts.py) measures candidates through multi-seed engine replays and
writes a calibration profile that the source generator applies on the next run. Use 64 complete
regular seasons for tuning, which produces 1,024 team-games in a 16-game season or 1,088 in a
17-game season. Validate the selected profile with 256 additional seasons and unused seeds. Match
completion, yardage, sacks, turnovers, play volume, and scoring together; matching isolated chart
averages is insufficient. Sparse literal `TD` cells, when required after numeric gains are
calibrated, belong to this second stage. Record the effective profile in
`generation-manifest.json`. See the [two-phase operator workflow](chart-generation-workflow.md) and the
[chart generator tuning tool](dev-notes/chart-generator-tuning-tool.md).

The PFR and nflverse adapters apply `run_yard_multiplier` once to each primary
run family. Empirical observations are scaled before allocation; a family with
insufficient empirical support instead has its aggregate fallback numeric and
fumble gains scaled before final probability allocation/layout, with existing
flags and direct-run caps preserved. Neutral multiplier 1 is byte-identical.
Already calibrated empirical columns are not scaled again. Shared breakaways
are not independently scaled a second time. QB Time remains separate: its
negative sacks and positive scrambles are coupled pressure outcomes, so the
ordinary run control does not alter them. Calibration must measure the complete
engine rushing mixture rather than assuming a proportional response.

### Generate from Pro Football Reference Play by Play

[`generate_pfr_charts.py`](../generate_pfr_charts.py) provides a source adapter for saved
Pro Football Reference boxscore HTML. It parses the full play-by-play table, classifies each
regular-season result, enriches field-goal and fumble inputs, and then uses the same aggregate
and empirical generator described above.

```sh
python generate_pfr_charts.py \
  --html-dir /path/to/pfr-boxscores \
  --stats-dir /path/to/team-stat-json \
  --template-season /path/to/template-season \
  --team-map /path/to/pfr-team-map.json \
  --output /path/to/staging/1983-pbp \
  --audit-dir /path/to/local-audit \
  --through-date 19831219 \
  --calibration-profile /path/to/profile.json \
  --seed 8306
```

The team map is a JSON object from PFR abbreviations to template directory names. The command
writes a `generation-manifest.json` with source-row counts, classification diagnostics, per-team
field-goal and fumble counts, empirical outcomes used, and columns that fell back to aggregate
generation. The audit directory contains source rows for local review. Keep downloaded HTML,
audit rows, historical templates, and intermediate generated seasons local and ignored. A reviewed
final chart set may be published without those source materials under the publication policy below.

For an independently reviewed missing sack annotation, optionally pass
`--event-reconciliations /path/to/reviewed-event-facts.json`. The version-1 input
contains an `events` array: each event declares `game_id`, `play_number`,
`raw_game_sha256`, `raw_play_sha256`, `credited_sack: true`, nullable
`credited_sack_loss` and nullable `initial_gain`. Compute the parsed-play hash
with `paydirt.pfr_event_reconciliation.play_fingerprint`. Each event requires
`evidence` entries with a relative `file`, its `sha256`, a public HTTPS `url`
and positive reviewed `pages`. The loader checks actual local evidence bytes,
raw-event identity, duplicates and unused records; it rejects nullified events.
Keep this reviewed source input and its documents local and ignored.

Schema 4 additionally supports field-specific `originating_kind` on a fumble
record (`rushing`, `receiving`, `sack`, `kickoff_return` or `punt_return`). With both credited fields null, this
records reviewed class support only. The explicit reported-gain policy can
combine it with an unambiguous same-actor primary number in the unchanged source;
it does not establish official credited yards or physical movement. Conflicting
explicit source classes are rejected. The stricter physical/credited policies
still require their original gain evidence.

An optional schema-4 `originating_player_id` / `originating_team` pair records
independently reviewed primary-actor team support when player metadata is absent.
Both fields are required together. The bound actor must be the source's exact
primary named and linked player, and the team must be in that game. Known
conflicting metadata is rejected; a recovering player's team does not supply
the missing fact. Raw player metadata, credited gain and physical gain are not
rewritten by this review.

Schema 5 may add `reported_primary_yards` when an independently reviewed book
supplies a scoped primary number that the secondary feed's malformed clause
cannot parse. It requires an exact actor/team pair and primary originating class,
one same-actor fumble and signed integer yards (nonpositive for a sack). The raw
row and evidence hashes remain bound. A different supported raw primary number,
compound occurrence or lateral scope is rejected. This field supplies only
reported proxy gain; credited and physical yards remain separately nullable,
and the stricter policies cannot use it as their missing evidence.

Standalone `returned by` rows require a reviewed kick-return family and the
actor/team pair. Their unambiguous same-player number before the fumble can
supply `return_before_fumble` reported gain under the explicit reported proxy.
It remains separate from official statistical credit and physical movement.
The adapter emits one special-team return F and excludes it from primary
rushing/passing fumble calibration. Missing gains and recovery-only numbers
remain unsupported. The kick family is not guessed from the standalone row.

Starter-table home/visitor identities resolve after the entire HTML is read,
so table order does not erase a starter's explicit team. Conflicting starter
sides or known team metadata are rejected.

Schema 4 `kind: "aborted_field_goal"` records retain a reviewed bad snap that
the secondary feed labels as a missed kick. They declare `offense_team`,
`fumbling_player_id`, nullable `recovering_team` and `individual_lost`, nullable
paired `credited_player_id`/`credited_rushing_yards`, and nullable
`physical_initial_yards`, with the same identity/evidence bindings. A recovering
player's statistical credit is distinct from the snapper's fumble. The adapter
excludes the reviewed nonattempt from field-goal attempts while retaining its
snap event and unsupported projection identity. These records currently block
generation: the engine's existing field-goal F path forces opponent recovery
and does not supply a general snap-credit/movement model. They cannot erase an
independently credited kicker's attempt or bypass source-fit requirements.

Credited sack loss does not establish physical initial fumble yardage. An unknown
`initial_gain` preserves the credited occurrence and known fumble ownership but
supplies no invented numeric QT sample. The ledger records all applied facts,
fumble events and unsupported required-field identities. Unknown ownership or
missing required completion/run gain prevents generation. Recovery-return and
penalty yardage cannot fill an absent initial gain; known zero stays zero. The manifest hashes the sidecar and evidence documents. These checks
verify identity and consistency; they do not read scans or certify their review.
See the [reconciliation design](dev-notes/pfr-event-reconciliation-proposal.md)
for scope and limitations.

Schema 2 also accepts `kind: "fumble"` records with the same identity/evidence
fields, boolean `fumble_lost` and `out_of_bounds`, and an optional nullable
`initial_gain`. Omitting that field retains the parsed gain; an explicit null
keeps severity unknown. Conflicting known ownership/gain is rejected. This
bounded capability supports ordinary retained or lost recoveries and retained
out-of-bounds fumbles; an out-of-bounds touchback needs separate review.
Schema-1 sack records remain valid in either schema.

For a reviewed own-recovered fumble preceding an incomplete pass on the same
snap, schema 2 accepts `kind: "prepass_fumble"`, `continuation_play_number` and
`continuation_play_sha256`, with the common identity/evidence fields. Both raw
rows must be adjacent and agree on actor, quarter, clock, down, distance and
location. The classifier keeps one passing fumble occurrence and one incomplete
pass, without adding a rush or sack. The `unmodeled_prepass_fumbles` diagnostic
discloses that a BLACK chart outcome cannot reproduce that earlier fumble.
Likewise, reviewed out-of-bounds F events retain their source facts but still
use the engine's generic F recovery model. Neither capability proves exact
conditional physical behavior or resolves credited-versus-initial yardage.

A complete PFR `Fumbles-Lost` team box can also determine unknown loss ownership
when every feasible assignment agrees. Exhausted known loss credit proves the
remaining events retained; proving all unknowns lost additionally requires the
observed fumbles to equal the complete team box. Mixed assignments remain unknown.
The ledger retains the exact integer constraints for each deduction. Missing or
invalid boxes supply no implicit zero; contradictory known counts prevent
generation. These deductions identify loss credit, not a recoverer name or
physical initial gain. See the [constraint rules and controls](dev-notes/pfr-fumble-recovery-constraints.md).


The adapter fits a league-wide additive model that separates relative offense and defense effects
under an explicit average-defense-zero constraint. Every offensive audit row therefore includes
its opponent. Offense outcomes are translated to a league-average defense, while fitted defense
residuals replace schedule-biased allowed rates before the defense template is generated. A ridge
pseudo-count, configurable with `--opponent-shrinkage`, partially pools small samples.

Opponent gain adjustment reads normalized numeric/initial-fumble tokens, never
interception return or sack prose as primary passing gains. Actual source scoring
gains remain numeric; unsupported bare TD/B initial gains fail explicitly.
Incomplete and intercepted retained pass attempts contribute zero passing yards;
unknown completed gains do not. QB Time severity adjustment preserves the source
sack/scramble class, including typed zero-yard sacks. Recorded constraints and
source/adjusted/selected class distributions expose finite/model changes.

When fitted category totals change, midpoint quantiles of the entire adjusted
conditional population replace chronological-prefix sampling. Ordering retains
complete result tokens and attached flags. Each team/chart/category manifest
records sample counts, result histograms, gain means/ranges and omitted variants.
A small sample may omit a rare tail; the method does not force extra probability.
These adjusted conditional diagnostics are distinct from raw source event rates.
Missing required nflverse gains and unknown fumble recoveries remain unsupported,
and actual generation refuses them rather than substituting zero/retention.
Conversion procedures are separately inventoried, including credited offensive
attempts, voided fouls and defensive returns; they supply no ordinary chart samples.

Pass event families use the aggregate generator's engine-calibrated baseline by default, while
empirical play by play supplies resolved yard distributions, scoring-play yardage, fumbles, and
clock-stop markers. Quantization preserves the combined mass of fumble, interception, penalty, and marked
numeric families before selecting individual variants. Optional replay-derived adjustments are
available as `--run-yard-multiplier`, `--pass-completion-adjustment`,
`--pass-interception-adjustment`, `--pass-pressure-adjustment`, and
`--pass-yard-multiplier`. Leave them neutral unless a matched multi-season engine replay justifies
a change, and record non-neutral values in the manifest.

Historical PFR descriptions usually identify run direction, sacks, turnovers, penalties, kicks,
and observed yardage, but usually omit pass depth and defensive alignment. The adapter therefore
uses a deterministic pass-family heuristic and estimates relative defense effects from matched
league-wide residuals rather than attempting to reconstruct unobserved formations.

### Generate from nflverse Play by Play

[`generate_nflverse_charts.py`](../generate_nflverse_charts.py) reads a regular-season nflverse
CSV or gzip-compressed CSV and feeds the same opponent-adjusted empirical pipeline. nflverse air
yards distinguish screens, short, medium, and long passes more directly than historical narrative
heuristics. Run gaps and locations select run columns; sacks also populate quarterback-time;
interceptions produce both pass results and return outcomes.

```sh
python generate_nflverse_charts.py \
  --pbp /path/to/play_by_play_2024.csv.gz \
  --stats-dir /path/to/2024-team-stat-json \
  --template-season /path/to/2024-template \
  --team-map /path/to/nflverse-team-map.json \
  --output /path/to/staging/2024 \
  --audit-dir /path/to/local-audit \
  --seed 8306
```

The command accepts the same opponent and pass calibration controls as the PFR adapter plus
`--run-yard-multiplier`. Leave all multipliers at `1.0` and rate adjustments at `0.0` until a
matched engine replay demonstrates a systematic boundary error. The manifest records source
coverage, diagnostics, fallback columns, and all calibration values.
A minimum sample threshold prevents a penalty-only or otherwise sparse empirical column from
replacing its aggregate fallback. Every special-teams family also has a deterministic fallback
penalty profile, so a resolved empirical sample cannot erase foul risk merely because no foul was
observed in that small sample. Observed special-teams penalties replace that fallback distribution
when present. Field-goal accuracy is calibrated only across numeric cells because the engine
rerolls penalty cells; accepted field goals marked `no play` are excluded from kick calibration.
Review the manifest, including `special_teams_penalties`, before using the charts.

#### Diagnostic ordered fumble projection

The opt-in `--fumble-projection-mode ordered_ledger_v1` requires
`--fumble-gain-policy source_reported_gain_proxy_v1`. It preserves one primary
origin and ordered conditional fumbles, including a separately credited actor
after an aborted punt. Retained `F INC` stays outside stochastic recovery-range
calibration. Normal generation keeps its existing unsupported-compound guard.

`--fumble-loss-reviews PATH` accepts a JSON list of typed individual-loss
reviews. Each review binds the raw play hash, event ordinal, fumbling team and
player ID, loss flag, evidence hash/page and relative `evidence_file`. The adapter
checks the actual PDF bytes and page, exact event association and duplicate or
unapplied reviews; a review label supplies no missing gain or physical movement.

`--shared-return-exposures PATH` additionally enables the diagnostic shared
return-column allocation. Its JSON wrapper binds `source_sha256`, a relative
`measurement_file` and its hash, complete `terminal_exposures_by_team`, and frozen
`fumble_ranges_by_team`. The measurement must complete every game in each
declared source schedule, have no unresolved retention, and agree on exposures
and ranges. Counts represent outcome-bearing nonfoul terminal segments rather
than raw lookups or recovery counts. The generator deduplicates INT-return F
events, allocates the joint column once, preserves baseline penalty mass and the
declared ranges, and records quantization and scoped-gain diagnostics.

For ordered generation, `--fumble-range-policy measured_diagnostic_v1` preserves
that measured recovery-range prior and remains the default. Explicit
`--fumble-range-policy source_primary_v1` instead applies recovery ranges from
the corrected primary source fumble counts through the existing generator.
Both modes still require and validate the full source-bound exposure receipt,
including its complete measured range pairs; selecting source ranges never
bypasses measurement hashes, schedule completion, retention or source checks.
The ordered manifest and joint ledger record `range_policy`, while each team's
range inputs retain the measured prior, source-derived pairs and actual
`applied_range_cells`. Shared/combined losses are not refit. An explicit range
selection requires ordered projection; unsupported modes fail without fallback.
Portable source recipes bind this scalar flag to the manifest's range policy;
a source-primary candidate requires its explicit matching flag. Legacy recipes
with no declaration retain only the measured diagnostic default. Both modes
preserve the same complete typed source/evidence validators.

These switches implement a local diagnostic experiment. Non-F conditional gain
targets and unknown physical gains remain null; the manifest reports
`fit_accepted: false`. Candidate exposures must be measured again after repair,
and the all-consumer residuals require review before accepting the shared model.
They do not certify source fit or chart release readiness. See the
[source/model decisions](dev-notes/chart-source-model-review-decisions.md) and
[recorded recipe](dev-notes/compound-fumble-projection-proposal.md#recorded-diagnostic-allocation-recipe).

The source approach is informed by the archived
[Data-Driven Football design process](https://web.archive.org/web/20250524072210/http://www.datadrivenfootball.com/designprocess.html),
which describes parsing every regular-season gamebook, reviewing every record, adding information
from video, and validating with at least 100 simulated seasons. PFR-only classification implements
the database portion of that approach; it does not supply the film review or manual chart-design
judgment described there.

### Optional source-driven gain normalization

Both play-by-play commands accept `--gain-normalization-contract PATH`. This
opt-in model adjustment regenerates the complete unnormalized cohort, runs
sixteen source-calendar repetitions with the fixed chart-focused policy and
development seed `20261108`, then derives one passing and one rushing factor
for every team. Both physical teams attempt end-zone interception returns in
this measurement. Existing command behavior is unchanged without the option.

Use a separate source-only JSON contract containing `season`, `schedule` and
`targets`, with the same facts as the release validation contract. The schedule
uses objects such as `{"away": "Ironclads", "home": "Thunderhawks"}`. It must
cover the complete supplied cohort and match the adapter's source-game count.
Do not include `chart_hashes`, `generation_manifest_sha256` or
`generation_profile`: output identities would create a circular input recipe.
Use the public 2026 teams or synthetic inputs when developing fixtures.

For each metric the procedure uses the official source attempts and yards and
the pooled credited engine attempts and yards. It subtracts the source-attempt
weighted cohort mean of `log(source mean / engine mean)`, shrinks each residual
by `attempts / (attempts + 200)`, bounds its logarithm to factors `[0.8, 1.25]`,
and applies the derived factor once. It does not accept hand-edited team factors.
Only ordinary primary numeric gains and numeric rushing breakaway gains change.
Fumble and quarterback-time outcomes, event probabilities, recovery ranges,
defense and special teams are preserved. Transformation follows probability
allocation and precedes final layout; numeric rounding and caps are recorded.

The audit directory retains `gain-normalization-baseline/YYYY/`,
`gain-normalization-classified/` and `gain-normalization-training.json`. Use a
fresh audit directory for each generation; existing training evidence is never
reused or overwritten. The final manifest binds the training, source contract,
complete derivation and per-team transformation diagnostics. Portable source
bundles include the contract under `inputs/normalization_contract/` and bind the
same command option. Independent regeneration reruns training rather than trusting
cached coefficients. Preserve the interpreter/runtime identity when freezing a
recipe; this procedure does not promise identical training receipts across Python
versions.

This is a deterministic model allocation, not proof of historical play intent or
chart accuracy. Training legality/accounting must pass; its pre-adjustment fit
is diagnostic. Final source reconciliation, unchanged accuracy bounds, reserved
validation and release gates still apply. No existing cohort is certified merely
by enabling this option. Keep source inputs and narrative training reports in
ignored local audit storage; do not publish raw or private source material.

### Publication Policy

Publish only reviewed chart files generated by this repository. Include the concise notice in
[CHART_ATTRIBUTION.md](../CHART_ATTRIBUTION.md), and keep raw play-by-play, downloaded pages,
aggregate source tables, audit rows, templates, original developer charts, and replay reports out
of the release. The accepted 1983 generator output is stored as `seasons/1983-generated` so it can
coexist with ignored private comparison charts; release packaging maps it to `seasons/1983`. The
2024 and fictional 2026 sets already use their final numeric directory names.

### What Can Be Recovered

- Punt and return columns track their corresponding season distributions closely.
- Rushing and passing totals produce cohort-calibrated column strengths.
- Defensive rushing and passing efficiency shift a complete tactical formation template.
  Fractional shifts are distributed across defense sub-rows according to the actual red/green
  dice probabilities. Defensive interception strength is allocated across sub-row-five cells,
  limiting any one play-and-formation adjustment to 1/36 while preserving team differences; sack
  rates alter separate rare pressure outcomes. The interception queue preserves parenthesized
  Screen counterplay in B/C/F, assigning those formations' later strength tiers to existing
  BLACK coverage cells instead. Pressure relocation reserves those destinations. This is a
  modeled allocation across calls, not recovered formation-specific turnover rates; fixed
  interception depths 5/12/18/8 remain modeled support and require renewed source-fit review.
- Classified plays preserve team-specific distributions that aggregate totals discard.

Exact reproduction still needs charting judgment. Historical descriptions often identify run
direction and receiver but omit pass depth, route, coverage, or designed play. When
`field_goal_by_distance` is supplied, each distance is interpreted as the statistical kick
distance and the generator builds a nonincreasing success curve; aggregate field-goal totals
remain a fallback. Supplied offensive fumbles and fumbles lost determine the chart's weighted
recovery interval. Penalty, breakaway, and formation conventions can still differ between chart
designers.

Aggregate passing symbols are allocated against the same denominators used by the engine:
completion and interception rates apply to resolved pass attempts, while quarterback-time and
penalty rows sit outside that attempt denominator. Passing yardage, pressure, and the template's defensive interception contribution use
engine-observed calibration factors rather than matching offense-column averages in isolation.
The defensive contribution is expressed through multiple low-mass cells instead of changing one
high-mass sub-row at a source-rate threshold. Supplied `out_of_bounds` counts mark weighted
numeric run and pass outcomes with `*`; omitted counts preserve the previous unmarked fallback.

The 2026-11-01 two-phase reference run used 64 chart-focused training seasons and 256 held-out
Hard-vs-Hard validation seasons for both 1983 and 2024. The selected 1983 profile applies
completion, interception, pressure, and passing-yard adjustments of `-0.05`, `-0.07`, `-0.07`,
and `1.55`; its rushing multiplier remains `1.0`. The selected 2024 values are `0.02`, `-0.06`,
`-0.02`, `1.30`, and `1.0` respectively. Every training and validation game completed.

Under the team-independent situation-aware training policy, all five configured chart-boundary
metrics met tolerance for both seasons. Hard play selection produced a separate distribution:
1983 completion rose to 60.86% versus 56.90% actual while interceptions and sacks fell to 1.25%
and 4.31% versus 4.41% and 7.96%; 2024 completion was 64.86% versus 65.29%, passing yardage was
7.81 versus 7.13 yards per attempt, and sacks were 4.96% versus 6.87%. The 2024 Hard run still
finished near actual scoring and volume at 22.16 versus 22.91 points and 61.16 versus 62.15 plays
per team-game. These policy differences are reported diagnostics. Chart tuning must not force one
profile to cancel the strategic choices made by every AI policy.

A 2026-11-02 DATA-012 rerun replaced the old binary defensive-interception threshold with the
low-mass allocation described above. The existing profiles still met all five 64-season training
tolerances. The 1983 Hard interception rate increased from 1.25% to 1.96%; 2024 moved from 1.30%
to 1.11%, while its chart-focused rate improved from 3.12% to 2.79% against a 2.17% source rate.
The specific Dallas D/Short matchup found in manual testing fell from 38.89% to 11.11%. For the
47-pass call mix in that game, expected defensive interceptions fell from 2.50 to 1.58 and the
probability of at least five fell from 6.84% to 1.87%.

The original historical workbooks examined during development contain chart-entry formatting
and quantitative audit formulas. They do not contain a hidden season-statistics-to-chart formula.

## Import an Existing Excel Chart

### What the Importer Does

[`extract_charts.py`](../extract_charts.py) generates game CSV charts from existing Excel workbooks.
It is a **converter**, not a tool that derives new team ratings from football statistics.
Run it from a source checkout; it is not a browser menu feature or separately packaged executable.

| Output | Contents |
|--------|----------|
| `offense.csv` | Offensive dice rows 10–39, nine play columns, breakaway, QB-time, and fumble entries |
| `defense.csv` | Formations A–F, sub-rows 1–5, and play columns 1–9 |
| `special.csv` | Kickoffs, returns, punts, field goals, and extra points |

It reads BLACK cell backgrounds, RED extra-point backgrounds (written as `NG`),
parentheses-style defense number formats, and fumble recovered/lost ranges from offense column Q.
Numeric extra-point cells are written blank for a good kick; RED cells mark misses.

### Requirements and Input Layout

Install the importer's optional dependency in your active Python environment:

```sh
python -m pip install xlrd==1.2.0
python extract_charts.py --help
```

`xlrd` is needed for importing, not ordinary gameplay. Use **Excel 97–2003 `.xls`** files,
one workbook per team, with sheets named exactly **OFFENSE** and **DEFENSE**.
The importer expects the original chart layout, not arbitrary spreadsheets:

- Offense dice values in B; nine offensive play columns in C–K.
- Offense special columns N–P: breakaway, QB-time, and fumble; fumble-range text in Q.
- Defense formation/sub-row labels on the left and numbered play columns in the chart header.
- Special teams on the DEFENSE sheet in N–T; T supplies dice rows and extra-point color.

Preserve colors and number formats. Converting to CSV first loses that information.
Renaming an `.xlsx` file to `.xls` does not convert it.

### Convert Workbooks

From the repository root, always supply **both** paths:

```sh
# All .xls workbooks in a directory
python extract_charts.py -i /path/to/workbooks -o /path/to/staging/2026

# One workbook, filename relative to the input directory
python extract_charts.py -i /path/to/workbooks -o /path/to/staging/2026 -t DemoTeam.xls
```

| Option | Meaning |
|--------|---------|
| `-i`, `--input` | Workbook directory |
| `-o`, `--output` | Destination season directory |
| `-t`, `--team` | One workbook filename |

Default paths are developer-specific historical download locations; do not rely on them.
Batch discovery selects lowercase `.xls` filenames. Team folder names come from workbook filenames,
with legacy 1972/1983 prefixes removed and a few legacy mappings applied.
For other years, use `DemoTeam.xls` rather than assuming a year prefix is stripped.

**Generate into staging first.** Existing CSVs are overwritten without confirmation,
and errors can leave partial output. Per-team errors are caught and processing continues:
**zero exit status does not prove every import succeeded**. Check `ERROR processing` messages and row counts.

### Synthetic Workbook Example

This optional example uses constant-value synthetic data, not private charts or a realistic team.
Install `xlwt` only to create this example:

```sh
python -m pip install xlwt==1.3.0
```

Save the following as `make_demo_workbook.py` in a scratch directory outside the repository and run it there:

```python
from pathlib import Path
import xlwt

Path("workbooks").mkdir(exist_ok=True)
book = xlwt.Workbook()
offense = book.add_sheet("OFFENSE")
defense = book.add_sheet("DEFENSE")
for play in range(1, 10):
    offense.write(1, play + 1, play)
    defense.write(1, play + 2, play)
for index, roll in enumerate(range(10, 40)):
    row = index + 2
    offense.write(row, 1, roll)
    for column in range(2, 11):
        offense.write(row, column, 3)
    for column in (13, 14):
        offense.write(row, column, 0)
    offense.write(row, 15, "R")
    defense.write(row, 0, "ABCDEF"[index // 5])
    defense.write(row, 1, index % 5 + 1)
    for column in range(3, 12):
        defense.write(row, column, 0)
    for column, value in enumerate((60, 20, 40, 5, 0, "1-40", roll), start=13):
        defense.write(row, column, value)
offense.write(0, 16, "Fumble Recovered 10-29; Lost Ball 30-39")
book.save("workbooks/DemoTeam.xls")
```

Return to the repository root and import using those scratch paths:

```sh
python extract_charts.py -i /path/to/scratch/workbooks -o /path/to/scratch/2026 -t DemoTeam.xls
```

Expect 30 offense, 30 defense, and 30 special-teams rows in `2026/DemoTeam/`.
Row counts are useful controls, not complete semantic validation.

## Validate and Install

1. Check all three CSVs, their headers, and row counts.
2. Compare representative entries to the workbook: gains/losses, BLACK, parentheses, fumbles,
   special-teams ranges, missed extra points, and empty cells.
3. Load the staged chart from the source checkout:

   ```sh
   python -c "from paydirt.chart_loader import load_team_chart; load_team_chart('/path/to/scratch/2026/DemoTeam'); print('Chart files loaded')"
   ```

4. Add `2026.yaml` beside the team directories. For this demo, copy the public
   `seasons/2026/2026.yaml`. Chart loading alone does not validate season rules.
5. Optionally add fictional `team.yaml` and `roster.json` files using [these formats](seasons.md).
6. Back up existing data, then copy the reviewed season to the [appropriate location](seasons.md#season-data-locations).
7. Select the team and inspect its charts and a practice game. In a source checkout with the demo installed:

   ```sh
   python -m paydirt --play --compact --home 2026/DemoTeam --away 2026/Ironclads
   ```

Do not overwrite the distributed Thunderhawks or Ironclads when experimenting.

## Troubleshooting and Limitations

- **Unknown empirical chart:** use the normalized names listed above; source play labels are
  not interpreted automatically.
- **Aggregate chart differs from a historical chart:** add classified plays for the affected
  columns. Season totals cannot recover information that was aggregated away.
- **Field-goal column looks generic:** provide normalized empirical field-goal results derived
  from attempts by distance. Made/attempted and longest-made totals are insufficient.

- **Missing xlrd:** install 1.2.0 with the interpreter used for the script.
- **Missing sheet / index errors:** verify exact sheet names, columns, header placement, and original layout.
- **No teams found:** check `-i` and lowercase `.xls` extensions.
- **Empty formula cells:** `xlrd` does not evaluate formulas. Recalculate/save usable cached results in a spreadsheet application,
  or replace formulas with verified literal values in a copy preserving formatting. Inspect the CSV afterward.
- **Wrong BLACK/extra-point entries:** verify solid BLACK/RED fills survived editing.
- **Stray characters in result cells:** a source cell holding only a backtick or quote mark is a
  blank (zero-yard) result. The generator drops such characters when writing `special.csv`, and the
  game loader does the same with a warning naming the column and dice roll, so existing CSVs do not
  need to be regenerated to play correctly.
- **Partial output:** repair only the affected staged team, rerun, and review every message.
- **Team missing in the app:** check rules YAML and source-versus-bundled data locations.

The workbook extractor has no general chart-validity report, dry-run, overwrite protection, or
metadata generator. Loading successfully is not an accuracy guarantee. Import only authorized workbooks;
keep private sources, extracted charts, intermediate generations, and replay artifacts local.
Only reviewed generator outputs intended for a release belong in the public season directories,
and historical release charts remain outside unit fixtures.

### Automatic completeness audit

PFR classification requires explicit scramble or sack evidence before assigning
a quarterback run to QB Time. Quarterback position alone does not establish a
dropback: a run with no observed direction/design uses the declared line-plunge
fallback and increments `heuristic_quarterback_run_family`. Explicit direction
and draw descriptions keep their observed family. This prevents a zero/negative
rushing fumble from becoming a sack merely because the runner is a quarterback;
it does not resolve credited yardage versus physical fumble-spot uncertainty.

Both source-cohort commands prepare all teams before writing charts and derive
one shared neutral pressure model from their source constraints. When the default
defensive QT floor makes an official sack target unattainable, the bounded
procedure swaps QT into lower-probability subrows of the same formation/column,
preserving tokens and protected strength cells. Offense overlap allocation and
defense generation use that same model. An infeasible protected layout fails;
targets are never clamped. `generation-manifest.json` records the constraints,
resolved cells, moves and unsupported teams under `neutral_pressure_model`.
Missing empirical QT observations retain an explicitly disclosed default; they
do not establish conditional source accuracy. Standalone aggregate generation
retains its default model. See the
[pressure design and limitations](dev-notes/source-constrained-pressure-proposal.md).

Both PBP generation commands write `chart-audit.json` and reject invalid or incomplete generated
charts. The audit checks all primary and secondary columns, result symbols, physical yardage limits,
fumble recovery coverage, and scoring conventions; it also measures the combined primary offense/defense result probabilities
for all 54 play/formation combinations. `generation-manifest.json` records source annotation counts
and explicitly modeled fallback features and rates. A missing season-wide annotation is not
interpreted as evidence that its probability was zero.

Saved historical sources can omit clock stops, fair catches, illegal kickoffs, blocked field goals,
and special snap fumbles. Documented modeling defaults preserve those engine mechanisms when the
whole season contains no corresponding observations. These estimates are distinct from source
evidence and still need sensitivity and historical validation. The full findings and repeatable
comparison command are in the [completeness audit](dev-notes/generated-chart-completeness-audit.md).

Explicit PFR descriptions of kicked extra points are excluded from rushing
classification even when the kicker is also listed as a quarterback.
Known leading PFR player names can identify an unlinked ball carrier before
linked defenders. Duplicate display names are excluded from name lookup, preserving
explicit player links instead of selecting an arbitrary namesake.

### Reviewed historical source scope

`generate_pfr_charts.py --source-scope /path/to/reviewed-source-scope.json`
provides an explicit, hash-bound fitting scope for reviewed historical source
limitations. It requires `historical_fumble_class_proxy_v2` and
`historical_isolated_fumble_exclusions_v1`; the default remains strict.
The versioned sidecar identifies exact source games and events, records reasons,
and declares `historical_source_complete: false`. Supported scope is limited to
an unresolved aborted-snap rushing gain, reviewed fumble-box conflicts, and
field-goal actor conflicts whose complete team attempt/make totals reconcile.
It also inventories known partial games. Optional `reviewed_sack_counts`
records bind exact PBP mechanism counts and independently parsed team-box sack
credits to each raw game hash. Each reviewed difference is exactly one occurrence;
the original descriptions, credited totals and missing information remain separate.
Generation checks both accounts against the source. Source audits retain explicit
findings and require the precise team and league differences; new discrepancies
still fail. No missing sack play, yardage, player identity, recovery or possession
is manufactured.

The raw classified ledger retains unsupported fields and diagnostic counts.
Only a fitting copy excludes the individually identified aborted snap; the
existing uniform fumble-exclusion policy remains separate. Every sidecar entry
must match its source hash and apply exactly once. Generation records the
sidecar input hash and complete disclosure. Source audits require identical
contract opt-in and exact diagnostic counts, and portable source bundles bind
both the supplied sidecar contents and reproduction command. New or changed
source problems fail rather than inheriting a general waiver.

A passing scoped audit establishes consistency with this disclosed fitting
population. It does not establish complete historical coverage, unbiased
fumble selection, or historical outcome accuracy. Retain per-team excluded
counts and validate generated charts and season outcomes separately.

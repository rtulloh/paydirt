# Paydirt game-to-season qualification plan

Owner-requested staged execution companion, 2026-11-06. Agents run the tests and
retain receipts; no community volunteers or exhaustive owner play-testing are
required. This extends the [chart-confidence charter](chart-confidence-agent-charter.md),
not its source targets, fit bounds, seed history or release permissions.
No commit, push, tag, publication or final release approval is authorized.

BB owns its corresponding plan at
`/private/tmp/bb-chart-confidence-plan/docs/dev-notes/game-to-season-qualification-plan.md`.
Share public-safe findings and methodology. NFL and college counting, selection,
rules and postseason formats must be validated separately.

## Decisions and evidence

Each stage reports **GO**, **NO-GO**, **UNVERIFIED** or **NOT RUN**, its exact
scope, candidate/runtime/source/policy identities, command, seeds, complete
expected-versus-observed inventory, failures, warnings, skips and issue links.
GO applies to that evidence and version only. Missing/failed games are failures,
never dropped observations. A code/chart/source/policy change invalidates its
dependent evidence. Tooling tests or a successful negative preflight do not
establish that actual charts or games passed.

There are two dependencies: mechanics checks can progress on public 2026 fixtures
or existing local integration charts while generated-source qualification is
blocked; final generated-cohort accuracy and probability studies cannot. Record
that distinction. Never run a large invalid campaign to manufacture activity.

## Stage 0 — trustworthy measurement and source support

Require observer/core conformance, complete event/count/scoring receipts, actual
loaded-runtime identity, source capability/provenance and deterministic candidate
reproduction. Include rejecting controls for stale imports, omitted teams/games,
changed policies/targets, erased FG counts, missing fields, source ownership,
priority/allocation defects and probability/flag-changing layout mutants.
Use synthetic/public 2026 fixtures in collected tests only.

Source facts, official credited statistics, unknown physical contact spots and
modeled chart gains must remain distinct. Resolve or explicitly review source
projection choices before fit calibration; preserve unknowns and all event IDs.
Four compound fumble rows and credited-versus-physical gain remain substantive
source/model questions, not reasons to widen tolerances or keep adding tools.

Finish bounded in-progress components, then prioritize blocker decisions and
actual Stage 1/2 execution. All-60 source reproduction and the fixed acceptance
contract remain required before final generated-cohort campaigns. Current source
readiness is **NO-GO**; a fresh measurement checkpoint is **UNVERIFIED** here.

## Stage 1 — complete games with play-by-play accounting

Use existing full-game runners and targeted real-engine scenarios before new
infrastructure. Retain typed action/state/box/scoring receipts; narrative is a
presentation check, not the oracle for statistical counts. Review every retained
transition in the selected full-game set automatically, with failure excerpts
that identify the matchup, seed and first inconsistent event.

Required invariants include possession/field position/down/clock transitions;
accepted/declined/offsetting fouls and replayed snaps; scoring logs and final
scores; pass/rush/sack and completion/INT identities; fumble ownership and initial
versus subsequent movement; FG/PAT/punt/kickoff counts; halftime, warnings,
timeouts/spikes, untimed downs, overtime and legal final termination. Reuse
synthetic forced-branch regressions for rare cases; a random full game is not
evidence that every rare branch occurred.

Run `python3 tests/run_all_games.py` (14 local games), the existing historical
reproductions through the full-season runner, and required browser full games.
Use the charter's snapshot and runtime protections. The browser suite must
complete home/receiving then away/kicking with clean new-game state. Notify the
parent before stopping owner services on 8000/5173 and restore them afterward.

GO: every expected game completes and all receipts reconcile; all relevant
forced-branch tests pass. New behavior defects get test-first fixes and tickets,
then invalidate and repeat affected evidence. Historical/private logs stay in
ignored `.ai-audits/`. Latest fresh checkpoint: **NOT RUN under this plan**.

## Stage 2 — one complete regular season and postseason

Run `python3 tests/run_full_season.py [YEAR]` using actual selected-year regular
fixtures and available generated charts; see the [runner guide](../historical-seasons.md).
The implemented source sets contain 224/272 regular fixtures for 1983/2024 and
nine/thirteen historical playoff fixtures. Default simulated postseason entrants
come from simulated standings. Historical playoff replay is explicitly separate
and does not calculate counterfactual qualification. All sixteen existing private
1983 reproductions remain additional checks when their original charts exist.
Missing developer charts is not applicable to the source-only historical audit.

The 1983 ten-team and 2024 fourteen-team formats now have synthetic/public controls
for membership, byes, reseeding, failed-game advancement and complete rounds.
Official NFL tiebreaks remain UNVERIFIED: current regression ranking uses winning
fraction, point differential, points scored and name. Reports retain tied-record
groups; consequences still require measurement before probability claims. Require
source-year overtime, full typed transition accounting and all other applicable
criteria before a complete Stage 2 GO.

Fresh actual-calendar development runs complete 224+9 games for 1983 and 272+13
for 2024 with Hard AI, master 20261108 and generated candidates. Both pass their
existing final box/scoring/termination checks with unchanged input/runtime bytes.
This is GO for that bounded runner scope; complete Stage 2 qualification remains
UNVERIFIED. No repeated probability or reserved family is opened.

The owner subsequently requested replacement of the generated schedule and a
year-selected historical runner, tracked in [VAL-019](issues/VAL/VAL-019.md).
The preceding description identifies the current implementation, not the desired
end state. The replacement must use actual regular-season fixtures/results and
membership, selected-year rules and a postseason seeded from simulated standings.
The fixture inventory includes the whole regular calendar, including games
between conferences; a conference-only subset cannot qualify a full season.
Any replay of actual historical postseason fixtures is a distinct benchmark;
forcing historical entrants would invalidate qualification-probability estimates.
Missing historical inputs must fail clearly without a synthetic fallback.
Developer-chart absence is N/A for that additional baseline comparison, not a
blocker for auditing an otherwise supported generated season against history.

## Stage 3 — frozen repeated seasons and probability estimates

Prerequisites: Stages 0–2, source-year support, all fixed chart-fit training and
held-out requirements, and a declared immutable candidate. Existing masters stay
unchanged: 20261108 development; 20361108 held-out fit; 20461108 private reference;
20561108 prospective 2023 transfer. Register additional probability-study master
**20661108**, unopened until those prerequisites and the final study specification
are met. If outcomes prompt changes, retire the family into development and
register another untouched family; do not reset the existing ones.

Complete available developer-reference mechanism and material-outlier review
under a stable training freeze **before opening final fit or probability
families**. If that review changes the candidate, re-freeze and retire any opened
evaluation families as specified in the reference protocol. For seasons without
developer charts, that comparison is N/A; supported historical-source validation
still applies. Final probability execution requires actual GO for both required
fit families and all applicable source, reference and prospective-transfer
criteria, not merely an approved contract or a passing preflight.

Reuse the required 64 training regular-season repetitions where their actual
schedule/receipts match the study. Add correctly seeded postseason games to each;
do not merely reuse unbound aggregate standings. Freeze forecasts from those
training seasons before the probability family opens. Then run **512 independent
complete seasons per claimed cohort** with derived season/game/postseason seeds,
fixed source-year schedule and declared policy. Run a small development smoke
first; no final 512-season run on failed mechanics/source preflight. This is an
additional study, not a replacement for the charter's held-out fit campaigns.

For every team report expected wins/ties, point differential and distributions,
division title, playoff qualification, conference title and Super Bowl win rates.
Report denominators and marginal 95% Wilson intervals for per-season indicators;
512 independent seasons gives a worst-case interval half-width below five
percentage points. Verify the actual bound, and label these as marginal Monte
Carlo intervals, not simultaneous historical-accuracy guarantees. Use independent
season clusters for means, policy contrasts and prediction comparisons.

Probability accounting must reconcile fixed qualification slots, exactly one
champion and two conference champions each season, including nested event
probabilities. All source-year required rounds must appear. Never interpret
zero sampled championships as impossibility.

Predeclare strength/forecast diagnostics without fitting to final outcomes:

- Rank training expected win fractions under the declared schedule/policy;
  compare final expected wins, point differential, rank correlation and quartiles.
  This measures schedule-dependent simulated strength, not intrinsic truth.
- Forecast each postseason event using `(training_count + baseline_rate) / 65`:
  one exchangeable pseudo-season, with baseline rate fixed by the eligible field
  and event slots. This preserves slot totals; use conference-specific eligibility
  for conference titles. Retain raw training frequencies alongside forecasts.
- Compare final Brier scores against those exchangeable baseline forecasts,
  with paired season-cluster uncertainty. Disclose weak/unverified predictive
  separation rather than requiring a historical champion or imposing rank caps.
- Use synthetic equal-team/renamed-team/home-away controls and controlled
  strength differences to reject bookkeeping bias and unexplained reversals.
  Investigate persistent counterintuitive cohort results against chart tradeoffs,
  schedule, policy and uncertainty before claiming predictive validity.

GO means complete lawful seasons, reconciled probabilities, declared precision,
valid controls and reviewed explanations of material anomalies. It qualifies the
simulation's estimates conditional on the model; it cannot establish real-world
championship probabilities. Source-fit, transfer and reference requirements stay
separate. Current study status: **NOT RUN**.

## Stage 4 — complete chart and release-readiness evidence

Complete the unchanged charter: exact weighted/tactical controls, all-team fit,
64 complete repetitions per required family, Hard/balanced/repeated-call and
run/pass stress audits, full private 1983 comparison, retrospective outlier
review, prospective source-only 2023 transfer, and probability-preserving visual
dispersion with persistent owner preview. No Razzle-Dazzle behavior is required
in Paydirt. Owner review can be a small visual set; agents own exhaustive checks.

Run every current `AGENTS.md` regression command, including both 64-repetition
generated-chart gates, clean public-files unit snapshot, frontend/build/browser,
backend, lint, integration/season and both AI audits. Do not count an older green
run as evidence for changed code. Bind all required reports in the final readiness
inventory. Inspect issue-specific verification criteria after each play-test;
close only tickets with newly confirmed required evidence. Record every existing
skip/warning. Final readiness is currently **NO-GO**.

The implementation agent sends a concise stage table and exact failure tickets
after each checkpoint. The parent reviews the decisions and shares public-safe
findings with BB. A release decision follows final evidence and owner review;
this plan itself is not that decision.

## Initial execution receipt — 2026-11-06 06:14 CST

Parent ran a bounded public-2026 selected-call smoke: Ironclads/Thunderhawks in
both directions, Hard and legacy balanced, development master 20261108. Four of
four games finish legally; 594 selected calls and 182 situation summaries
reconcile against independently rebuilt summaries. There are no observational
concentration warnings; comparable streak maxima are five/three. Engine source
fingerprints remain `64660a464ea4b253816f6f86721f36fb59417eec6ff19c30cb4400f6c70e18dd`
before/after. Ignored receipts: `.ai-audits/staged-qualification/root-public-01/`.

This is **GO for that bounded selected-call check only**. The existing report
does not retain complete boxes, every play-by-play transition or executed-runtime
attestation. QB-scramble touchdowns were unobserved. Full Stage 1, browser and
Stage 2 current-checkpoint evidence remain NOT RUN here. Review of resolved
tickets adds limited AI-008 evidence and closes none. Generated accuracy and final
release readiness remain NO-GO; this sample does not open reserved families.

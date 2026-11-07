# Chart confidence implementation goal and acceptance criteria

Owner-authorized assignment, 2026-11-05. This is a work plan and acceptance
contract, not a statement that current charts pass. The owner requested this
definition before starting the implementation agent. Current release status is
**held**. The owner will review the resulting charts before publication.

Assigned background task: **Paydirt chart confidence candidate**,
`01a1ae4d-2d05-7d73-867b-33f5cd0badba` (started after this contract was written).

Local environment: `python3` currently selects Python 3.9; use
`/opt/homebrew/bin/python3.11` for the existing pytest environment. The backend
and frontend review servers currently listen on ports 8000 and 5173. Preserve
their sessions until the isolated browser regression requires a restart.

## Goal and deliverable

Produce a reproducible, independently reviewable chart candidate for all 60
public-generated teams (28 in `1983-generated`, 32 in `2024`), with corrected
source/generator/engine defects, automated behavioral evidence, a working local
chart preview, and an explicit account of unsupported historical assumptions.
The owner's work should be a small visual/usability review, not exhaustive
manual games or a substitute for missing automated evidence.

Passing this contract means ready for owner review and a separate release
decision. It does not mean an exact reconstruction of private developer charts
or proof of historically correct route intentions. Do not claim either.

## Work order and boundaries

1. Read repository `AGENTS.md`, `docs/chart-validation.md`, the combined
   `generated-chart-release-audit.md`, the focused
   `generated-offense-black-cell-audit.md`, and issues DATA-016 through DATA-020
   and RULE-026. Inspect current dirty files before editing. Preserve all
   existing chart UI and defensive-timeout work; do not reset/stash/switch away
   from the owner's worktree or broadly rewrite unrelated changes.
2. Establish failing synthetic/public-2026 regressions before every production
   behavior change. Correct selected-priority semantics (RULE-026), finite-row
   allocation (DATA-016), and source discrepancies (DATA-017) before calibration
   (DATA-018). Verify the already-local observer fixes (DATA-019/020).
3. Reconcile individual source events and definitions. An allowlist or changing
   official targets to match extraction is not reconciliation. Preserve public
   provenance and regenerate from reviewed inputs; stage candidates in ignored
   storage before replacing promoted public files.
4. Extend the existing gate rather than introducing a competing authority.
   Add exact weighted offense/supplemental/special-teams diagnostics and source-
   supported checks, stateful scenarios, team-level fit and policy sensitivity.
   Distinguish exact invariants, empirical fit, exploratory diagnostics and
   inherently unsupported claims.
5. Calibrate only after the preceding defects are corrected. Freeze inputs,
   profiles, engine, observer, policy, metric definitions and thresholds before
   held-out runs. Retain baseline comparisons and investigate mechanisms rather
   than fitting a single league mean or masking conditional gain distributions.
6. Run final checks, create fresh local review contexts that load the candidate,
   update documentation/tracker evidence, and hand off the review packet.

No commit, push, tag, release publication, private-chart export or cross-project
source mutation is authorized by this assignment. Local implementation,
generation, dependency setup and validation are authorized. A release task is
separate and remains on hold. Keep raw sources, private integration output,
simulation logs and large reports under ignored `.ai-audits/`. New development
notes belong only in `docs/dev-notes/`.

## Required evidence: source, mechanics and distribution

- All team/chart inventory, source hashes, profiles, aggregate identities and
  source-versus-official event counts reconcile. Document any legitimate
  definition difference with event evidence and regression coverage. Unknown
  route depth or missing annotations stay explicitly modeled; do not invent
  source facts. A known unexplained count discrepancy is a failure.
- Regenerating each candidate from its declared inputs reproduces every
  offense/defense/special CSV byte for byte. Keep attribution and reviewed
  metadata. Update chart/profile fingerprints only for reviewed regenerated
  candidates; do not alter target facts to accommodate observed output.
- All 60 teams, nine primary calls and six defenses receive physical-probability
  checks across the 216 offense and 36 defense combinations. Include normalized
  priority semantics and B/QT/fumble/return branches. Use exact analytical
  conditioning where full secondary enumeration would be redundant; verify
  that conditioning with real-engine controls and report remaining unknown
  branches explicitly. Do not call conditional known-yard means whole-play YPA.
- Check probability conservation, attainable allocation, protected event
  preservation, completion/turnover/pressure tradeoffs, gain distributions,
  explosive tails and expected formation costs/benefits. Cover special teams
  and distance-dependent field goals where supported. Unavailable route- or
  distance-specific historical truth cannot receive a fabricated accuracy pass.
- Any visual redistribution of BLACK cells preserves full dice-weighted
  behavior. An unrestricted shuffle over unequal-weight rows is unacceptable.
  Matching a private reference's visible cell pattern is not a fit objective.
- The gate must reject deliberate mutants: repeated weighted defensive
  distributions despite different arrangements, erased strength, displaced
  result classes, rare allocation error, selected-fumble/INT misclassification,
  corrupted observer counts, voided-play credit, changed/stale evidence,
  missing/short samples, ignored component failures, and a bad individual team
  hidden by a passing league average. Show failing baselines and passing controls.

## Required evidence: scripted situations and engine integration

Use synthetic/public fixtures for stateful controls covering offense backed up,
midfield and red zone/goal line; ordinary and fourth-down decisions; B/QT,
own/lost recoveries and return scores; accepted/declined/offsetting penalties;
retained versus nullified statistics; conversions, kickoffs and special teams;
two-minute warning, spike/timeout order, halftime, untimed downs and overtime.
Reuse existing meaningful regressions and integration scenarios. Add cases for
uncovered relevant branches rather than duplicating every existing test.

Every recorded game must finish legally, reconcile scoring and official box
totals, and preserve measurement identities. NFL-style offensive play counts
must equal pass attempts + rushing attempts + sacks. Completion and interception
counts must be valid subsets of attempts. No missing or failed game may be
silently discarded. Store reproducible seeds/matchups for failures.

## Fixed quantitative finish line

These are engineering acceptance bounds, not claims of confidence intervals or
historical certainty. Keep source metrics and denominators explicit. If a
criterion is scientifically inapplicable, bring the evidence to the parent
before revising the contract; it remains unmet until that review. Do not widen
bounds after seeing a candidate miss them.

Use the existing five league tolerances, unchanged, and add the following
team-level bounds under the declared chart-focused reference policy:

| Metric | League absolute tolerance | Each team's absolute tolerance |
| --- | ---: | ---: |
| Completion rate | 1.5 percentage points | 3 percentage points |
| Interception rate | 1 percentage point | 1 percentage point |
| Sack rate | 1 percentage point | 1.5 percentage points |
| Passing yards per attempt | 0.25 yards | 0.75 yards |
| Rushing yards per attempt | 0.15 yards | 0.40 yards |

All source-supported team targets and both league contracts must pass; an
unexplained team failure cannot be canceled by another team's error. Report
sample sizes, sampling uncertainty, maximum errors and distribution/tail
diagnostics alongside means. Source-supported play-family checks should use
independently observed family definitions, not the historical heuristic labels
as independent ground truth.

- Development/calibration seed family: master **20261108**, derived independent
  game/repetition seeds. Other exploratory seeds must be declared as training.
- Reserved held-out family: master **20361108**, using the same documented
  derivation. Do not inspect this family's outcomes while tuning. Freeze the
  candidate and announce its fingerprints to the parent before opening it.
- Final reference-policy evidence: **64 complete source-schedule repetitions per
  cohort per family**, giving at least 1,000 team-games per team in both training
  and held-out evidence. Existing pre-fix reports cannot certify the candidate.
- Held-out outcomes are for acceptance. If a failure leads to a new change,
  that family becomes development evidence; reserve a new untouched master
  before the next final evaluation and record the history. Never choose a seed
  because it happens to pass.
- Policy sensitivity: at least eight complete source-schedule repetitions per
  cohort for Hard and legacy balanced AI (at least 128 team-games/team), plus
  bounded run-heavy/pass-heavy stress scenarios. These must pass mechanics,
  accounting, finite-state and completion checks. Report play mix, repetition,
  team rankings, yield/turnover distributions, score and pace differences.
  Deliberately different call mixes need not reproduce the same aggregate
  historical averages. Investigate material unexplained pathologies and test
  exploitative repeated calls; do not impose arbitrary frequency caps.
- For source-supported metrics beyond the existing contracts, define the
  denominator, finite-row resolution and acceptance rule before candidate
  tuning. Missing historical support is disclosed as unverified; it is not
  silently treated as an empirical pass. Describe how remaining uncertainty
  limits the eventual release's claims.

## Developer-reference comparison at the stable checkpoint

The owner subsequently requested a complete comparison against the local 1983
developer charts once the model is stable, and the analogous 2007/2008 Mayfield
comparison in BB. Follow the [reference comparison protocol](chart-reference-comparison-protocol.md)
before the final owner review. This extends the work with a full-corpus local
benchmark, weighted behavior, crossed offense/defense checks, paired games and
private visual comparisons. Reference agreement is not substituted for source
accuracy. Keep original charts and reference-derived reports private/local;
do not add historical unit fixtures or copy original cells into generation.
Existing quantitative source acceptance limits remain unchanged.

The owner's further clarification makes **generator transfer confidence** part
of the goal: use reference-corpus findings to validate a reusable method, not
just fit the current charts. Follow the protocol's additional withheld-team,
frozen-procedure and prospective 2023 source-only transfer evaluation. Fresh dice
seeds alone are insufficient. Hand-authored team/season fitting tables are not
an acceptable replacement for a general source-driven generation procedure.

## Chart layout and play experience

The owner observed that generated outcome cells form deliberate clusters,
especially large contiguous BLACK regions on passing charts, while the original
charts intersperse good and bad outcomes. The charts should feel like playable
game components and support that visual variety. Treat dispersion as an explicit
secondary generation objective, subject to the existing accuracy constraints.

Investigate a deterministic placement procedure that reduces unnecessary runs
and blocks of like outcomes while preserving the exact physical-weighted
distribution of result values and relevant joint/core behavior. First establish
which rolls and supplemental lookups are independent or coupled; a simple
unrestricted cell shuffle is not an acceptable assumption. Equal-weight rows
offer possible placements but do not guarantee every cluster can be removed.
Do not change outcome incidence to improve appearance, reorder displayed dice
labels, or hide unfavorable cells. Retain reproducible generation and private
data boundaries.

Before production changes, propose the placement objective, scope, invariants,
feasibility limits and automated visual measures. Add synthetic/public failing
regressions and passing controls under the test-first rule. Include deliberate
probability/correlation corruption that the invariants reject. The owner-provided
images inform the visual requirement now; conduct the full private reference
comparison at the stable checkpoint under its existing protocol. Exact
statistical correctness and a smaller owner visual review remain separate
acceptance requirements.

## Full regression and independent review

Run the complete `AGENTS.md` regression checklist against the final frozen
candidate, including root/backend/frontend tests, build, real-engine browser
games, lint, all-games runner, full generated season plus nine playoff games,
both public/private AI audits and both generated-chart gates. Respect isolated
browser-service requirements; notify the parent before stopping the local review
servers and restore them afterward. Verify the intended candidate in a clean
checkout/snapshot containing only intended public/tracked files and required new
files, with no ignored historical data masking unit behavior. Record existing
skips/warnings; add no skips or weaker expectations. The final test evidence
must identify the candidate fingerprint to avoid certifying an earlier version.

The parent will independently inspect changes, source reconciliations, negative
controls, metric definitions, evidence fingerprints and held-out results before
calling the candidate ready for the owner's release decision. A successful
simulation count by itself does not satisfy this review.

Read the [first independent review and parent follow-up steering](chart-confidence-independent-review.md).
Resolve its confirmed findings with separate test-first evidence; its initial
checkpoint and narrow rechecks are not a final acceptance certificate.

## Owner review packet and reporting

Deliver a short ready/not-ready verdict backed by one reproducible gate command
and machine-readable reports. Include before/after metrics for both leagues,
all-team worst-case results, notable tails/special teams, source reconciliation,
changed files, fresh fingerprints, exact validation commands, warnings/skips,
open limitations and remaining issues. Provide working chart URLs and a compact
visual review set: Dolphins 1983, the worst statistical outlier per cohort,
representative strong/weak teams and all chart sections. Overlapping selections
may be combined so the owner need not inspect all 60 teams.

Post milestone updates to the parent Paydirt session
`01a1ac6f-523a-7103-b693-b01d7f61351e`. Keep the authorized BB exchange informed
through the existing shared findings mechanism, limited to public aggregate
findings. BB's priority rules and sack-count identities differ; never transfer
them into Paydirt without checking this engine's authority.

Persist toward the complete acceptance contract. Do not replace implementation
with another findings-only report or call a failing candidate ready. If evidence
establishes an irreducible source/model limitation, present the precise unmet
criterion and options to the parent, preserving the release hold. The goal's
status must describe actual achievement, not elapsed effort.

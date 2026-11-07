---
id: DATA-018
title: Promoted generated cohorts fail fresh current-engine accuracy gate
status: open
priority: High
created-at: 2026-11-05
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-audit
links:
  - DATA-019
  - VAL-019
---

## Description

Final corrected-observer evidence covers 64 source-schedule repetitions per
public-generated cohort: 14,336 games/1,024 team-games per 1983 team and 17,408
games/1,088 per 2024 team. All measurement conformance controls, complete samples,
raw totals and play-denominator identities pass. Earlier observer-derived values
were superseded after DATA-019 and DATA-020; use the
[final audit](../../generated-chart-release-audit.md).

1983 completion 53.58% misses 56.90%, and passing YPA 7.84 misses 7.18.
2024 completion 61.95% misses 65.29%, INT 3.26% misses 2.17%, and passing YPA 7.95
misses 7.13. Existing tolerances are unchanged. Other core measured metrics pass.

The former ignored batch helper defined ChartFocusedAI but instantiated base
ComputerAI. Its label does not prove that the declared fixed mix was used.
Policy and engine changes preclude attributing the new deltas to one parameter.
Source/priority/allocation defects remain independent blockers; do not retune
around unresolved RULE-026 outcome classification.

## Resolution / verification

Resolve source and engine blockers first, then recalibrate generated outputs
through the tracked runner and a declared policy. Use independent validation
seeds and preserve source tolerances. Verify per-team effects, special teams,
scoring/pace and coaching sensitivity rather than optimizing league means
alone. Rerun the automated release gate with complete fresh samples.

## Comments


--- 2026-11-05 16:35 ---
Opened from the user-requested generated-chart accuracy and release-gate audit.
The gate records the defect; no production/chart-data correction or push occurred.

--- 2026-11-05 16:54 ---
Complete corrected-observer gate evidence is recorded. No stale/sample/count
failure remains; both cohorts still fail the source accuracy tolerances. See
the final audit for exact metrics, fingerprints and the six existing blocker
issues, including the two verified-uncommitted observer corrections.

--- 2026-11-05 18:14 ---
Owner visual review: Dolphins offense black-cell trace. Regeneration of the public Dolphins offense is byte-identical.
The apparent black block is enlarged by allocating a common symbolic family
onto early low-mass rows; 20/30 Long cells carry 130/216 probability (60.19%).
The existing profile substitutes aggregate-model pass-event rates, applies a
-0.06 completion adjustment and 1.55 gain multiplier. Final conditional numeric
Long mean is 66.13 yards, not whole-play YPA. Under the final measurement policy
Dolphins completion is 53.58% versus 57.47% source, YPA 7.78 versus 7.32.
No single causal fix or chart superiority is established. See the
[focused investigation](../../generated-offense-black-cell-audit.md).
No chart bytes or production behavior changed; keep open.

--- 2026-11-05 22:49 ---
Fresh staged source components pass for all 60 teams, including independent
reproduction of all 180 CSVs, and both cohorts pass exact tactics/mechanics and
allocation components. Engine-fit acceptance still fails. Four neutral-profile
1983 schedules finish 896 games/64 games per team: completion .525558 versus
.569018 and passing YPA 5.104051 versus 7.184595; other league metrics pass.
Four unchanged-profile 2024 schedules finish 1,088 games with twelve team misses.
A larger sixteen-schedule 2024 run finishes 4,352 games/272 per team: all five
league metrics and every team's completion/INT/sack checks pass, but Packers
passing 7.457652/8.223382, Ravens passing 7.899740/8.781971 and rushing
5.185344/5.756318, and Vikings passing 7.212748/7.990876 miss fixed bounds.
The larger run is still below final exposure. No target, bound, profile or
reserved seed changes follow. Source-schedule gain/coverage decomposition is
being measured before a general correction; the gain-normalization proposal
remains unimplemented.

--- 2026-11-05 23:38 ---
Current-runtime sixteen-schedule 2024 training again completes 4,352 games with
the same four team-yard misses; no target or bound changes. Existing shared
controls give a separate 1983 diagnostic: +.045 completion, neutral INT/pressure,
1.3 pass yards, 1.0 run yards. All 84 CSVs reproduce and source/mechanics/allocation
pass. Sixteen schedules complete 3,584 games with every league bound passing,
but six team misses remain (Bears/Packers pass YPA, Falcons completion,
Colts/Saints/Steelers INT). The next declared global trial adjusts completion to
.049, INT to +.003 and pass yards to 1.37. These are development diagnostics,
not the final transferable procedure or minimum acceptance exposure. The general
gain extension remains unimplemented pending parent review; reserved/private
benchmark/2023 inputs are unopened. Release remains held.

--- 2026-11-06 00:18 ---
A third declared 1983 shared-control development profile changes only INT +.003
→ +.004. All 84 CSVs reproduce and actual source checks pass (266 inputs);
source/tactics/allocation pass at the sixteen-schedule checkpoint. It then
completes the full 64-schedule training exposure: 14,336 games/1,024 appearances
per team. Every league and team completion/INT/sack bound passes. Three fixed
checks fail: Cowboys rush 3.673698/4.078998, Jets pass 7.542358/6.694097 and
Packers pass 7.967789/8.912548. Maximum pass/rush errors are .944759/.405300.

Current-runtime 2024 training likewise reaches 64 schedules: 17,408 games/1,088
appearances per team. Every league and team completion/INT/sack bound passes.
Four yard checks fail: 49ers pass 7.487650/8.300188, Packers pass
7.457809/8.223382, Ravens pass 7.866283/8.781971 and rush 5.204515/5.756318.
Maximum pass/rush errors are .915687/.551802. No target or tolerance changes.

All 31,744 finals, official game/team totals, offensive-play identities and
4,590,012 ordered calls reconcile. All 4,420 situation groups are reviewed;
normal-context largest supported shares are 26.6% (192 calls, nine alternatives,
streak two) and 35.9% (78/nine/two), with longest ordinary streaks eight/nine.
These are fixed chart-focused measurements, not Hard predictability tests or
universal caps. The resolved inventory is inspected; no pending manual/rare
closure criterion is supplied. Full combined-component checks are being renewed
with these saved reports. The gain extension remains unimplemented pending
parent review; reserved/private/2023 inputs remain unopened and release held.

--- 2026-11-06 00:24 ---
Both combined gates finish against the complete 64-schedule training reports.
Source, exact tactics/mechanics and allocation components pass for all 60 teams.
The engine component rejects solely on the seven recorded team yard bounds;
there are no remaining sample, runtime, completion or accounting errors in
these reports. Earlier policy/snapshot evidence has its own older identity and
is not substituted for final validation. Keep the fit issue and release held.

--- 2026-11-06 00:40 ---
The full-exposure training review now attaches each failing metric's clustered
between-repetition standard error and margin above its unchanged point bound.
Three of seven gaps are smaller than one reported SE; Cowboys rushing exceeds
the bound by .005300 (SE .024939). Larger residuals include 1983 Packers passing
(.194759 beyond the bound, SE .057748) and 2024 Ravens rushing (.151802, SE
.033229). All seven remain failures: uncertainty does not replace charter point
acceptance. Full-exposure linearized uniform-scale screens retain opposing team
constraints for 1983 passing and 2024 passing/rushing, without assuming real
engine response is linear. The proposal records these limits and the outstanding
automatic shared-profile selection procedure needed before prospective transfer.
No normalization, new profile, source/target edit or reserved-family observation
follows. The existing tuner is not invoked: it would automatically run its
configured validation command and is not the final training-only procedure.

--- 2026-11-06 00:49 ---
Current Hard/balanced/family/repeated-call reviews pass mechanics/accounting for
13,392 games; historical fit is not imposed on those distinct policies. Repeated
normal Long Pass produces 63.16/53.76 points per team-game under the declared
fixed defense mixture, with visible explosive tails. An exploratory all-E counter
lowers passing YPA from 13.46/12.43 to 6.67/5.22 and scoring to 38.00/28.94; this
custom-AI diagnostic is not strict acceptance or proof of optimal coaching.

Source-distance FG inspection covers all 771 reviewed 1983 attempts: direct
nonfoul lookups project 545.07 makes against 551 actual (.707/.715), without a new
accuracy bound or pass. The full-game percentage .594 uses a different attempt
context: 2.135 attempts/1.269 makes per team-game versus source 1.721/1.230.
Finite pooling, modeled mishaps and penalty/state effects limit interpretation;
no causal conclusion follows from league FG percentage alone. The original
unconditioned draft is retained as superseded. Seven yardage misses, DATA-030,
frozen automatic calibration, reference/transfer and final review remain unmet.

--- 2026-11-06 01:15 ---
Current shared03 1983/trial07 2024 candidates reproduce all 180 CSVs through the
maintained locally pinned archive/staging/preparation path. All 301 public input
hashes and chart fingerprints remain unchanged. Fresh component rechecks with
these relocated inputs pass source/tactics/allocation; engine fit retains the
identical three/four team-yardage failures. A bound comparison confirms every
league/team fit metric and exact error list matches the earlier 64-repetition
training evidence. No new games, gain calibration, private reference opening,
reserved-family observation or target changes occur. Gain-method/DATA-030 review
and the automatic frozen transfer procedure remain unresolved; release stays held.

--- 2026-11-06 04:36 ---
The new visual-content validator and a read-only actual-preview check establish selected candidate/API/DOM value correspondence only: 18 views, 24 complete tables and 5,220 cells, with unchanged game states. The existing preview is still the older f0 checkpoint, and both candidate fingerprints are unchanged. This is not statistical fit, current source acceptance, reviewed representative selection or independent owner approval. The four 2024 compound-fumble source rows remain unsupported; requested credit/gain-model reviews and final frozen campaigns remain unmet. Keep open; no targets, tolerances or source facts were changed. Local evidence: `.ai-audits/chart-confidence/visual-content-preview-01/report.json`.

--- 2026-11-06 04:53 ---
The maintained isolated collector passes current-runtime selected display correspondence (18 views / 24 tables / 5,220 cells), unchanged six-game states, post-shutdown artifact checks and matching runtime receipts. Focused public-only checks pass 166 Python and 11 Node tests without ignored historical data. No gameplay fit, source facts, targets, tolerances, candidate CSVs or reserved-family observations change. Four compound-fumble rows still block current 2024 source acceptance; requested source-credit/gain modeling and final frozen campaigns remain unresolved. Keep open. Local evidence: `.ai-audits/chart-previews/prototype-03/result.json`; this is not charter selection or owner approval.

--- 2026-11-06 05:07 ---
Preview selection now requires complete current reference-policy fit/exposure for both seed families and derives worst normalized team errors without changing tolerances. An actual current-capture run retains a 5,220-cell content pass while rejecting old one-schedule training and missing held-out reports for both cohorts; display evidence cannot substitute for fit. The 61 new selection regressions/controls pass in a fresh public-only copy. Four unsupported 2024 compound rows and the pending source-credit/gain model decisions remain unresolved; no candidate/source targets or reserved outcomes change. Keep open. Evidence: `.ai-audits/chart-previews/selection-negative-02/review.json`.

--- 2026-11-06 05:22 ---
The new reference-corpus preflight independently revalidates source/mechanics and complete training evidence before reading declared reference charts. All 95 new synthetic/public regressions pass within 480 related checks; 184 focused checks pass in a fresh public-only copy. The actual CLI correctly refuses both cohorts' stale/failed source preparation and old short training records, retaining both failures and `reference_bytes_read=false`. No real private corpus, reserved outcomes, new source model or final fit acceptance was supplied. This strengthens stable-checkpoint enforcement; it does not resolve the compound source projection or empirical fit misses. Keep open. Local expected-failure evidence: `.ai-audits/chart-reference-comparison/preflight-negative-01/review.json`.


--- 2026-11-06 05:42 ---
Exact weighted reference tooling now computes four pre-state combinations, joint OOB/secondary/special distributions and exact deltas after a complete stable-candidate preflight, then rechecks dependencies. All 67 new cases pass within 466 related checks, with 251 passing in a fresh public-only copy. Synthetic review also corrects signed-defensive-F decoder acceptance (DATA-037) and missing-secondary false zeroes (AUD-029), both kept open pending integration. Actual weighted CLI evidence rejects both cohorts' stale/failed source and old short training before corpus access. No actual reference corpus, reserved outcomes, current source acceptance or empirical fit improvement is supplied. Four compound rows and pending source-credit/gain decisions remain unresolved; no targets, bounds or candidate CSVs change. Keep open. Local expected-failure evidence: `.ai-audits/chart-reference-comparison/weighted-negative-02/review.json`.


--- 2026-11-06 06:00 ---
Stateful crossed reference tooling now executes bounded matched engine contexts and independently reconciles its complete census, accounting and contrasts, with full stable-dependency checks before and after collection. All 78 new synthetic/public cases pass within the initial 101-check context/weighted-gate run; 329 checks pass in a fresh public-only copy without historical inputs. Actual context CLI evidence retains both cohorts' stale/failed source and old short training failures before corpus access. No actual private benchmark, reserved outcomes, source acceptance or empirical fit improvement is supplied. Four unsupported compound rows and pending source-credit/gain decisions remain unresolved; no target, bound or candidate CSV changes. Keep open. Expected-failure evidence: `.ai-audits/chart-reference-comparison/contexts-negative-01/review.json`.


--- 2026-11-06 06:25 ---
Paired saved-report tooling passes 164 focused public/synthetic checks, including
twelve baseline-derived-rate corruptions now rejected by AUD-030's shared
validator correction. The broader run has 998 passing checks and two concurrent
tracker-format/link failures retained for correction. The first copied-public
run passes all 493 checks but rejects source stability after parent documentation
edits; it is not a stable snapshot pass. Actual existing integration passes
14/14 games, 16/16 historical reproductions, 224/224 generated regular games and
9/9 playoffs with unchanged current loaded runtime and integration charts. These
are existing regression checks, not actual-year fixture/result validation or
final source fit. VAL-019 now owns the requested historical year-selected runner.
Proxy experimentation is approved within its recorded boundary; compound
projection and ordinary-gain normalization are not approved. No private reference
or reserved outcomes are opened, and no empirical fit or release pass follows.

--- 2026-11-06 21:38 ---

A fresh modern source-primary diagnostic now has a complete 64-schedule training
measurement: 17,408 games and 1,088 team-games for each of 32 teams. It uses the
unchanged frozen five-field profile, current engine, current allocation/layout,
complete selected ordered-source projection, source-primary recovery ranges and
fresh exposures with both physical teams explicitly attempting own-end-zone
interception returns. Independent saved-game arithmetic reconciles every score,
fixture, seed, raw total and all five rates. There are no incomplete-sample or
structural-accounting errors. All five league metrics pass the fixed bounds.

Three team metrics still fail: 49ers passing YPA 7.439699 versus 8.300188
(tolerance 0.75); Ravens passing YPA 7.976335 versus 8.781971 (0.75); Ravens rushing
YPA 5.251884 versus 5.756318 (0.4). The earlier 16-schedule Chiefs passing miss
clears at the full sample, while the 49ers miss appears; the full result
supersedes the smaller sample for current training-fit findings. No target,
tolerance, per-team coefficient or chart cell was changed in response. This
measurement does not isolate a causal parameter and does not justify manual
team patches. The independent arithmetic passes; the accuracy gate fails.

The diagnostic is separate from reviewed service 8160 and maintained packaged
charts. Historical source completeness (180 unsupported events), shared-return
conditional assumptions, retained placement findings, independent qualification
families, reference/transfer evidence and final release regression remain open.
Reserved seeds were not opened and no candidate was promoted. Ignored handoff:
`.ai-audits/release-readiness/modern-policy-source-01/HANDOFF.md`. Training report
SHA-256: `96fe975a9be0ccc6911c2d01836cac49aad862140697a458058395699369d912`.

--- 2026-11-06 21:48 ---
Read-only decomposition of the latest modern 64-schedule report independently
reconstructs its saved call/outcome inventories from all 2,498,102 ordered
decisions across 32 teams, with voided-yard, initial/net, negative/zero and empty
controls. No games rerun and no parameters derived. Baltimore's retained called
runs average 5.429928 net in normal mode (19,587 decisions), 5.180231 while
clock-killing (11,452), and 2.043777 at the goal line (1,165). These selected-call
outcome means are descriptive, not credited rushing YPA or a causal allocation
of the official-target residual; QB scrambles, fouls, recoveries and procedures
require separate accounting. San Francisco and Baltimore passing inventories
likewise retain each call/result/mode and initial-versus-net gain difference.
Receipt 27b6a777dd92eb5129e680183708be37d672597ad57415df1706533608a93907
binds the unchanged failed64 report and its independent accounting receipt.
All three fixed-bound failures remain. No adjusted target, manual coefficient,
normalization implementation, held-out opening or closure.

--- 2026-11-07 09:55 ---
An ignored exploratory modern-cohort experiment applies the already-tested
unwired gain helper once to all 32 teams, using the proposal's fixed weighted
anchor, pseudo-count 200 and [.8, 1.25] bounds. It derives adjustments from
the earlier 16-schedule engine baseline; no team-specific knob, source target
or tolerance changes. Protected probability mass, F/QT outcomes, defense
and special teams remain unchanged. No production generator or packaged
chart is changed.

Current-runtime development measurements complete 4,352 games (16 schedules)
and then 17,408 games (64 schedules) on the same transformed candidate. The
64-schedule report passes every existing team/league fit bound, with maximum
team errors .028220 completion, .005498 INT, .003991 sack, .462796 passing
YPA and .362991 rushing YPA. This is promising mechanism evidence, not
source acceptance or release qualification. The derivation reuses an earlier
runtime diagnostic; final reproducible generator integration, fresh eligible
training receipts, source coverage, untouched validation and complete charter
checks remain pending. Historical source holds and browser validation are
unresolved. Keep open. Immutable local receipts are under ignored
release-readiness/push-release-20261107/normalization-experiment/.

--- 2026-11-07 10:29 ---
Inspected the frozen corrected 512-season campaign (256 per cohort), all
132,608 games complete and all final checks pass. Current packaged 1983 charts
qualify actual playoff teams Denver only 7/256 and Seattle 43/256, while actual
nonqualifier Cincinnati qualifies 188/256. All sixty teams are reported in the
ignored campaign report; no incomplete seasons were excluded. These frequencies
are chart/model diagnostics under Hard AI and declared regression tiebreaks,
not requirements to force historical results or evidence for team-specific
tuning. Pending regenerated charts remain separately unqualified.

The owner explicitly accepts the known modern normalized-candidate Ravens
rushing error for this release investigation: 0.417273 exceeds the unchanged
0.4 tolerance. The original failed 64-schedule result is retained; this is an
accepted known issue, not an accuracy pass or a global tolerance change. Work
now prioritizes completing the historical source/model population.

--- 2026-11-07 10:36 ---
Continued 1983 primary-source reconciliation across all 224 raw games. Fourteen
of the original 180 held events now project from explicit official gamebook
rushing/sack credits, including aborted-play credits with different physical
and statistical actors. All 547 previously accepted projections are unchanged.
The full census retains all 727 originating fumble events: 561 project (515
reported proxies, 45 credited proxies, one retained incompletion), 166 remain
unsupported, and there are zero source conflicts. Independent physical movement,
loose-ball movement and recovery advances stay unknown where not established;
statistical zero is not presented as physical zero.

Ignored source-census-20 binds every new sidecar and recounts every game. No
corrected 1983 cohort has yet been frozen, fitted, promoted or certified. Remaining
work includes source association/action gaps and explicit snap events without
independent credited class/gain; four reviewed aborted field-goal snaps require
a model that preserves ownership and avoids recording a kick attempt. Historical
playoff-frequency differences are deferred until corrected-chart qualification;
the 512-season packaged-chart campaign is a baseline, not evidence for updated
charts or a reason to tune team strengths.

--- 2026-11-07 18:08 UTC ---

The typed owned zero-credit aborted-field-goal model now preserves recovery
ownership without rerolling, counts a rushing snap, and records no kick attempt.
The complete 224-game recount supports three additional events: 727 events,
564 projections, 163 held and zero conflicts. All previous 561 projection values
are preserved; ordinary serialized facts gain an explicit false subtype marker.
The fourth reviewed aborted field goal lacks the required credit and stays held.
Ignored evidence: `historical-completion-20261107/source-census-21-owned-fg.json`
under `.ai-audits/release-readiness/`. No corrected cohort has been generated,
fitted, frozen or qualified. Keep open. The
[completion boundary](../../historical-source-completion-boundary.md) records the
remaining evidence categories and an unaccepted bounded missing-data proposal.

--- 2026-11-07 18:39 UTC ---

The user authorized explicit historical role/class assumptions. The implemented
`historical_fumble_class_proxy_v1` preserves all 727 source events and supports
675 projections (564 unchanged source-tier projections and 111 modeled classes),
with 52 held and zero conflicts across all 224 games. Modeled additions comprise
76 identified-QB snaps, nine identified-QB sacks, eighteen unknown-role snaps and
eight unknown-role sacks. These are modeled statistical categories, not verified
official credit or physical gain. The remaining holds comprise 29 known non-QB
class gaps, eighteen incomplete/ambiguous primary-gain clauses, three positive-QB
gains unsupported by the sack model, one unidentified primary actor, and one
aborted-field-goal credit gap. Terminal recovery positions are not used as initial
gain proxies. Portable source contracts now bind exact versioned assumption
metadata and reconcile modeled class counts. Focused source/model/contract/docs
validation passes 488 tests; no fit, candidate, accuracy qualification or ticket
closure follows. See the updated [completion boundary](../../historical-source-completion-boundary.md).


2026-11-07: User-authorized version-2 role extensions plus five unambiguous
reordered sack losses yield 712 projections from all 727 retained source events,
zero source conflicts. The uniform fitting-only exclusion policy retains 15
unresolved events with hashes/reasons/team/mechanism counts: 14 primary-gain
issues and one unknown-credit aborted field goal. Known lost counts are 420 full
versus 415 fitted; one unknown recovery is excluded. Strict factual completeness
remains false. Focused synthetic and adapter/portable-contract regression: 450
passed. No full local regression, push, or historical outcome deletion.


2026-11-07: Corrected modeled 28-team/224-game candidate generated from the
712-event supported fitting population with all727events retained. Fixed source
normalization completed. Separate64-repetition measurement has two completion
exceptions under unchanged0.03bounds: SF0.610006vs0.642045; ATL0.601726vs0.633136.
Other declared team metric bounds passed. Do not represent this as an accuracy
pass. Fresh256-season outcome report is being run against the frozen candidate;
source reproduction is in progress. No team tuning or relaxed test expectations.

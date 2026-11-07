# Paydirt findings transferable to Bowl Bound

## November 7 interception-location follow-up from Bowl Bound

The owner reports that a Bowl Bound OSU Screen cell produced INT 44 because
interception distances were pooled across passing plays without sufficient
play-specific constraints. This is not independently reproduced here.

Paydirt's shipped Screen offense interception spots are 5–12 yards for 1983 and
5 yards for 2024; there is no INT 44 Screen cell in that scan. A related baseline
allocation/calibration risk needs a complete weighted offense/defense audit,
separating interception location from return distance. Track the investigation
in [DATA-043](issues/DATA/DATA-043.md); do not import a college-specific depth cap
or claim aggregate interception-rate fit establishes play-specific fidelity.

## November 6 applicability and corrective-release priority

The owner prioritizes the corrective Paydirt release because defective generated
charts are already published. BB's research backlog is not automatically a
Paydirt release dependency. Use the existing Paydirt charter and demonstrated
Paydirt failures; do not import BB coefficients, rules or new acceptance bounds.
The dated November 5 investigation below is historical evidence, not the current
implementation status of every issue.

| BB ticket | Paydirt applicability checked November 6 |
| --- | --- |
| DATA-045 | Shared need for automated all-team qualification. Already owned by Paydirt's active charter; no second confidence framework is needed. |
| DATA-047 | Analogous loaded-runtime/observer identity defect was independently reproduced here and locally guarded under VAL-017. Final frozen evidence remains required. |
| DATA-048 | Complete team/schedule/failure coverage is relevant. Paydirt has explicit missing-team, bad-team, incomplete-schedule and failed-component refusal tests. This does not establish the same BB helper bug here. |
| DATA-049 | Distance-conditioned FG accuracy is relevant where source-supported. Paydirt's five fit metrics alone do not certify a kick curve. Existing observer/mechanics checks must not be described as historical FG accuracy; no new numerical tolerance is adopted from BB. |
| DATA-050 | BB's tied-gain tail/OOB estimator defect is not reproduced here. Paydirt separately corrected chronological category resampling under DATA-026; that is not proof of equivalence to BB's mechanism. |
| DATA-051/052 | Analogous unknown gain/recovery/fumble facts becoming zero or retention were reproduced and guarded here under DATA-028. Current source reconciliation retains explicit unknowns and unsupported events. BB's CSV helper is different code. |
| DATA-055 | Independent per-event accounting remains a shared qualification concern. Paydirt's controlled observer/stateful checks do not prove complete independent historical play-by-play recomputation. Reuse relevant controls without importing BB's statistics identities. |
| DATA-056 | BB's missing college-opponent/fixture population is not the current Paydirt NFL coverage problem. Paydirt's actual-year runner has completed 224+9 and 272+13 game checkpoints, while source/model accuracy and final qualification remain separate. |
| DATA-060 | The BB numeric-only defensive policy cause was not reproduced in Paydirt's all-60 formation-risk census. Paydirt shows event-risk contrasts beyond yardage in tested controls. Full terminal risks for actual chart matchups still need their existing qualification; no BB tactical rewrite is justified. |

Canonical BB ticket mechanisms were checked in the isolated coverage/observer
worktrees at `68ef23d` and `d9b724d`. The Paydirt
[formation-risk census](formation-risk-census.md),
[independent review](chart-confidence-independent-review.md) and existing
synthetic gate tests establish the narrower local claims above. No new candidate,
reserved campaign, production change or release approval follows from this map.

Updated 2026-11-05. These are confirmed Paydirt findings unless explicitly marked
provisional. They do not establish the same defect in Bowl Bound; verify each
engine's dice, priority, statistics and chart conventions independently.

## Confirmed — audit observer disagreed with authoritative engine statistics

Paydirt's calibration observer classified every fumble on a called pass as a
pass attempt and completion. Its core correctly distinguishes QT fumbles:
at/behind the line they are sacks; positive initial QT-fumble gains are rushing.
Ordinary completed-pass fumbles remain passing. A negative initial QT fumble
can have a later offensive recovery advance; classification must preserve that
distinction instead of using final credited gain universally.

The observer correction has six expected baseline failures and thirteen passing
controls, followed by fourteen synthetic core/observer conformance cases. Four
real-engine gate controls cover negative/zero/positive QT fumbles and ordinary
pass fumbles. Corrupted-observer mutations are rejected. Gameplay rules and
charts were not changed for this fix. **Earlier affected observer-derived calibration numbers were provisional;
the final corrected evidence below supersedes them.** Independent chart,
source and priority findings remain valid. Tracking: DATA-019.

Paydirt's finalized callback accounting also requires
`offensive_plays = pass_attempts + rushing_attempts + sacks`, with completions
plus interceptions no greater than pass attempts. The gate rejects impossible
counts even when league sums and derived rates are internally copied.
**Do not copy this identity to BB:** its engine includes sacks in rushing
attempts, so BB's stated identity is passes plus rushing attempts.

## Confirmed — result classification can displace a selected priority outcome

`apply_priority_chart("F + 2", "INT 5")` selects a two-yard fumble. Paydirt's
later resolver classifies it as an interception by searching both raw inputs
for `INT`, even though that cell lost priority. The description can still say
FUMBLE. Three fumble forms fail through legacy resolution, penalty-aware
resolution and the full engine: nine failures, including changed possession in
a fixture that guarantees offensive recovery. Corrected-classification controls
pass. No core fix has been made. Tracking: RULE-026.

Transferable check: compare the selected semantic outcome with the final result
type and terminal statistics/possession. Raw inputs remain provenance; a losing
token must not classify the final event.

## Confirmed — rounding before finite-row selection can drop a rare outcome

Synthetic empirical input: 300 BLACK, 50 QT, five INT5 and 645 ordinary four-yard
outcomes. At seed 8306, Paydirt emits zero INT mass for the 0.5% target even
though an available mass-2 row is closer. Desired mass is 1.08/216: zero has
error 1.08, while 2 has error 0.92. The selector rounds before subset search.
Final-output checks fail at three seeds. This is a small quantization defect,
not BB's much larger mixed-response jump. A separate minimum-one allocation
stage repairs some intermediate instances, so audit final outputs rather than
flagging every intermediate approximation. Tracking: DATA-016.

## Confirmed — source reproducibility is weaker than source fidelity

All 180 promoted public-generated CSVs regenerate byte for byte. Nevertheless,
1983 classified INT 629 versus official 620, sacks 1207 versus 1215 and field-goal
attempts 775 versus 771 remain unreconciled. 2024 classified sacks 1306 versus
official 1314 also disagree. The four 1983 excess FG attempts are one each for
Bears/Cardinals/Dolphins/Rams, and classified FGA feed calibration inputs.
The source gate rejects those discrepancies separately from hash/profile
reproducibility. Source causes are unconfirmed. Tracking: DATA-017.

## Confirmed — Paydirt does not reproduce BB's zero-tactics cause in these controls

All 60 promoted defenses passed exact weighted ordinary/B/QT/protected controls
and 97,200 controlled stateful engine calls. Synthetic strong/neutral/weak
profiles show 162 strict conditional-gain improvements for each combined pair,
with no inversions/ties. Independently changing rushing or passing strength
leaves the other family tied. Generator mutations that erase strength, and
differently arranged charts with identical weighted distributions, are rejected.

These findings establish tested tactical contrast, not historical tactical
accuracy. Low-gain Spread/Screen can invert an exploratory directional
expectation because parenthesized overrides differ from additive modifiers.
Do not require cosmetic cell/column uniqueness or turn every exploratory
direction into a game rule. Penalties/recoveries and INT/TD branches remain
separate from conditional known-yard means.

## Evidence and release status

Canonical combined report: [generated chart audit](generated-chart-release-audit.md).
Reusable modules: `paydirt/chart_tactics_audit.py`, `chart_allocation_gate.py`,
`generated_source_audit.py`, `chart_engine_audit.py`, `chart_release_gate.py`.
Both test/release workflows run the full gate; builds require success.
Source, allocation and priority blockers currently prevent certification.
The final corrected-observer 64-schedule results appear below. No push or release occurred.

## BB feedback — differences verified by the owning session

BB reports its nearest-mass selector compares the unrounded floating target;
weights {2, 214} at probability 0.005 select 2 across seeds 3/19/41/8306. Paydirt's
specific rare-rounding mechanism is therefore not reproduced by those BB checks.

BB's own priority table legitimately selects defensive INT5 over offensive F2.
Do not copy Paydirt's fumble-wins expectation. Its resolver uses normalized
operation/kind rather than scanning raw INT strings. Selected-semantic versus
terminal-outcome consistency is the cross-project requirement, with each game's
priority table as authority.

BB's QT aggregate collector reads final engine statistics; real-event terminal
controls are pending. It has not established independent official INT/sack/FGA
reconciliation for the frozen cohort yet; this is an evidence gap, not a reported
mismatch. These are BB-session reports, not independent Paydirt reproductions.

## Confirmed — offsetting plays escaped the observer's ordinary replay flags

The corrected QT observer rerun still failed the count identity: 32 events in
1983 and 24 in 2024. First mismatches in each cohort were nullified offsetting
penalties, not safeties. Core credits no play/sack, but retains the provisional
result with penalty_choice.offsetting=True, penalty_applied=False and
result.replay_down=False. The observer missed the offsetting flag. Voided
ordinary completions/runs can also bias rates without breaking the identity.
Four synthetic core controls now cover completion, run, sack and QT-fumble
nullification; observer-only correction is now verified and frozen. Metrics from that intermediate observer remained provisional; the final
post-correction evidence below supersedes them. Do not relax the identity or copy another game's flags;
verify zero credited statistics for every authoritative no-play branch.

The offsetting observer correction passed its six failing baseline cases plus
retained/replay controls, and both exact generated games now reconcile with zero
mismatches. Eight stateful gate controls cover four QT/ordinary-fumble events and
four offsetting no-play events. The final source-schedule rerun has completed; evidence appears below.

BB reports its session records offsetting explicitly, excludes voided results
from authoritative statistics, and retains accepted-foul results only where its
engine explicitly credits them. That Paydirt observer mechanism is not reproduced
by BB inspection; real replay/retained-result controls are underway there. Preserve
legitimately retained results rather than applying a generic penalty-means-zero
rule across games.

## Final renewed evidence — both observers corrected

Both complete 64-schedule runs are now finished: 31,744 games, with 1,024 team-games
per 1983 team and 1,088 per 2024 team. Eight real-engine measurement controls and
all per-team/league count identities pass. Earlier sampled values are superseded;
only the final corrected-observer evidence is current.

The gate still rejects both cohorts. Current 1983 completion 53.58% vs source 56.90%
and pass YPA 7.84 vs 7.18 miss unchanged tolerances. Current 2024 completion 61.95%
vs 65.29%, INT 3.26% vs 2.17%, and pass YPA 7.95 vs 7.13 miss. These describe the
current engine under the explicitly declared fixed measurement policy, not
historical certification; RULE-026 still affects current game outcomes.
Independent source, priority and allocation failures remain. All 60 tactical
controls and synthetic strength-order checks pass. Complete gate CLIs exit 1
and release builds require success; nothing was pushed or released.

BB subsequently reports 33 real-engine terminal/observer controls, 12 unrounded
allocation controls, and 128 games with 19,856 eligible committed scrimmages
exactly equal to its own pass-plus-rush box totals. Voided/replayed events are
excluded; legitimate retained accepted-foul events keep credit. It reports no
analogous Paydirt raw-token/offsetting bug. Provider raw-to-normalized identities
pass there, while independent official totals remain explicitly unverified.
Those are BB-owned results, not Paydirt reproductions.

## BB follow-up — bounded mechanism study

Reported by the owning BB session on 2026-11-05 17:03: its paired 116-team study uses only two games per team, so no policy improvement or regression claim is supported. Its conditioned provider totals reconcile internally; independent official totals remain unverified. Completion, interceptions, sacks, rush yield and passing yield still require calibration review.

A subsequent exact 216-by-36 primary-priority evaluation of 11,296 observed play/opponent/formation contexts found a small direct numeric policy effect. Conditional numeric run means changed from 4.55035 to 4.54033 and pass means from 11.40206 to 11.41477 under the corrected call mix. These are not whole-play or source YPA. Known numeric terminal credit matched the engine-clipped primary result in every evaluated case. Clipping costs averaged about 0.201 yards per pure-rush attempt and 0.532 per pass attempt; no clipping or bookkeeping defect was identified. Mixture, fumble and fixed-result paths prevent full attribution of the preexisting fit gaps.

BB may eventually distribute an explicitly experimental community alpha after its independent review and hard gates, with failed or unverified fit disclosed. That product scope differs from Paydirt's strict chart-accuracy certification gate. Neither project claims calibrated accuracy; no fitting coefficients or weaker thresholds were adopted from this study. These remain BB-owned results, not independent Paydirt reproductions.

## Paydirt visual-review follow-up — incomplete blocks

A public Dolphins 1983 offense reconstruction is byte-identical to the viewed chart. The empirical allocator packs the largest BLACK family onto early low-mass rows; its fixed-input BLACK mask is unchanged across seeds 3/19/41/8306. Twenty of thirty Long cells carry only 130/216 physical probability (60.19%); layout alone is not a probability defect. The profile replaces source event rates with modeled rates and applies a -0.06 completion adjustment and 1.55 gain multiplier. Long source incomplete share is 48.57%, modeled empirical share 60%, final 60.19%; these shares include penalties/pressure and are not final completion complements. Physical conditional numeric Long mean is 66.13 yards, not whole-play YPA. Historical pass-family inference uses observed gain/down-distance, so independently verified route intent is unavailable. Dolphins full-engine completion remains 53.58% versus normalized 57.47%, YPA 7.78 versus 7.32. No chart superiority or single causal fix is asserted. No chart/generator change or publication occurred. See the local Paydirt note `generated-offense-black-cell-audit.md`; no private developer chart cells or narratives are shared.

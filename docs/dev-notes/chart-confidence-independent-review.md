# Independent chart-confidence review follow-up

Owner-requested independent review, 2026-11-05. **Not ready for release.**
This note records analysis and follow-up; it does not qualify chart accuracy or
promote charts. The implementation agent owns separate test-first corrections.

## Independence and evidence

The reviewer was launched separately with requested model `gpt-6-astra`, with a
review-only remit and no checkout edits. Its task-visible identity exposed
Codex/GPT-6, without independently exposing the Astra deployment label. It did
not open reserved seed families, prospective 2023 data or export private charts.
It independently ran 82 focused priority/allocation/engine-evidence tests and
four existing empirical-adjustment tests: 86 passed, no skips or warnings.
This was not a new full regression or a frozen final-candidate review.

The checkout changed during review as the implementation agent addressed
findings. HEAD remained `76edd82dc4fc3da45d9abca226cb76966c6047e2`; HEAD alone does
not identify the dirty candidate. The review's closing file-hash inventory is
retained in ignored `.ai-audits/chart-confidence/independent-review/closing-hashes.json`,
SHA-256 `95665cf20c0124e4d96bf6c484550d6f860796dc6233654f6b4e6ff4cda88397`.
These hashes identify a review checkpoint, not later fixes or executed objects.

The reviewer reconciled trial04's 4,352 game receipts, replications and uncertainty
at that report's recorded runtime identity. Four team yardage checks missed
fixed bounds; 272 appearances per team were below final required exposure.
Subsequent source and adjustment changes make trial04 stale for final acceptance.

## Confirmed generator and source findings

1. **P1: narrative return/sack yards contaminated opponent gain adjustment.**
   `paydirt/empirical_adjustment.py` accepted an arbitrary `for N yards` phrase
   for INT/QT tokens. Two synthetic offenses against two defenses each had
   40 ten-yard completions and 40 interceptions. Changing only one defense's
   interception-return prose from zero to 80 yards changed completion tokens
   from all 10 to equal counts of 25 and -5. Defense passing YPA was affected
   too. The parent independently reproduced it. A subsequent normalized-token
   correction passes this reproduction, also independently rechecked by the
   reviewer; no full chart/game validation follows from that narrow result.
   Unknown initial gains must fail explicitly rather than become zero.

2. **P1/P2: category resampling discarded chronological tails.**
   `_adjust_chart` kept `sources[index % len(sources)]` after changing category
   counts. For A's 20 zero-yard and 20 eighty-yard gains, with B's 40 BLACK
   outcomes against one defense, the adjusted numeric mean was 30. Reversing
   the same A multiset changed it to 50, with category counts unchanged.
   The parent reproduced both. A subsequent representative midpoint-quantile
   correction gives mean 40 in both orders in the same case. Its finite tail,
   variant and flag preservation still needs broader evidence and disclosure.

3. **P1/P2: QB-time gain adjustment crossed engine event classes.**
   The same numeric/fumble adjustment can turn a sack into a scramble or the
   reverse. Independently reproduced example: each of two teams has 20 QT -1
   outcomes against X and 20 QT +1 against Y; adjustment produces only QT 0.
   Paydirt treats numeric QT zero as a scramble. Additional reviewer examples
   cross numeric zero, negative numeric, positive F and F zero boundaries.
   Conditioning later pressure allocation on the changed mix does not establish
   source-mechanism validity. Class-preserving adjustment is being tested
   separately; its clamps and conditional mix require explicit evidence.

4. **P1: missing gain/recovery capability can become favorable known facts.**
   In `paydirt/nflverse_play_by_play.py`, a flagged sack with blank
   `yards_gained` emits primary QT and secondary numeric zero, with a sack count
   and no missing-yard diagnostic. The parent reproduced this. Missing run or
   completion gain can similarly become zero. Blank fumble-loss information can
   become false. In `paydirt/pfr_play_by_play.py`, missing/unrecognized recovery
   identity can become retained possession, and calibration can overwrite known
   loss totals. Existing INT/sack/FGA count checks do not certify gain/recovery
   capability. Missing values, real zeroes and known retained recovery require
   separate controls. Actual cohort prevalence and each fix's impact must be
   measured; malformed-input reproductions alone do not prove prevalence.

The implementation agent additionally reports actual zero-yard sacks in 2024
source data. This is a distinct representation issue, not missing data. Numeric
QT zero currently means scramble; inventing a negative yard or fumble would be
incorrect. A source-informed representation design and test-first engine checks
are required. This inventory is implementation-reported, not independently
reproduced by the first reviewer.

## Validation gaps and qualification limits

- **P1 provenance gap in an engine-report component.**
  `paydirt/chart_engine_audit.py` hashes current disk files before/after the run,
  without binding that identity to executed observer objects. A reviewer mutant
  wrapped the observer, then erased FG counters after the original callback.
  Two public 2026 games originally had eight attempts/four makes; the mutant
  recorded zero/zero. Both retained 68 total points and identical five required
  source-fit metrics. With a synthetic contract using the original five league
  targets and minimum exposure two, `validate_engine_report` accepted the mutant
  under the same disk fingerprint. Observer conformance passed after restoration.
  This demonstrates execution mislabeling at that component. **The reviewer did
  not run a complete release gate with the mutant**, and found no evidence that
  retained campaigns were mixed or that a normal fresh CLI was compromised.
  Proportionate protections include fresh workers from an immutable snapshot,
  import-origin/loaded-identity receipts and direct FG observer conformance.

- **P2 evidence completeness.** Deleting `call_mix` or `outcome_distributions`,
  or changing declared normal offense weights, was accepted by the engine-report
  validator in a small public reproduction. Situation keys also omit selected
  defense and repetition/streak details. Require receipt-reconciled evidence
  and declared policy, rather than relying on the five aggregate fit metrics.

- **P2 readiness coverage.** The combined gate's four components are narrower
  than the full owner charter. Source byte/reproduction checks can be optional,
  and a single engine report is not the required training/held-out/policy bundle.
  A minimum game count does not enforce 64 independent schedules: for example,
  59 appearances across 17 repetitions exceed 1,000 appearances. A component
  PASS must not be presented as charter readiness. Final readiness needs a
  reviewed, fingerprinted inventory of every required evidence family, source
  reconciliation, reproduction, reference comparison, transfer and regression.

- Numerical point tolerances are engineering bounds, not sampling confidence
  intervals. Source sample shrinkage is not simulator precision. Report clustered
  replication uncertainty and do not claim precision from play counts alone.

## Layout, calibration and transfer recommendations

Paydirt currently has no Razzle-Dazzle select-after-roll path. It selects the play
column first; B/QT lookups use fresh rolls. Post-allocation permutations within
equal-weight primary rows can therefore preserve ordinary distributions. Preserve
the **entire token and its flags**, including OOB. Existing resolved-outcome maps
can erase OOB differences and are insufficient as the only equivalence proof.
Leave recovery roll identities/ranges and supplemental aliases fixed: those
rolls also select special return/automatic-TD branches. Changing a generation
seed is not a layout-only transformation; the reviewer reproduced changed
weighted means when seeded quantile assignment changed row mass. No arrangement
change was performed by the reviewer.

Keep the proposed gain normalization unimplemented until source/adjustment fixes
are measured. Its source-count shrinkage is a model choice; the weighted log
anchor does not conserve arithmetic league YPA after unequal shrinkage, caps and
rounding. Scaling primary runs while leaving QT unchanged cannot generally reach
an aggregate target from a simple target/model ratio. Measure attainable response,
caps, tails and classes; freeze B triggers before scaling. Re-run whole-engine
measurement rather than treating initial gain as final credited yardage.

The full 28-team four-way reference comparison is a useful retrospective
mechanism benchmark, not independent historical truth. Audit decoder/fallback
coverage first and use identical rules, policy and source targets, with paired
replication uncertainty. Identical seeds do not guarantee identical game paths.
Freeze the entire source/schema/normalization/pool/anchor/policy/bounds procedure
before prospective 2023 evaluation. Fresh dice seeds alone do not test transfer.

Final 64-repetition evidence families, current policy sensitivity, the private
benchmark, prospective transfer, all-source support and a clean/public full
regression remain outstanding under the unchanged
[charter](chart-confidence-agent-charter.md). This bounded review did not audit
every source row, every legacy decoder branch, all packaging/browser behavior or
future fixes. The release hold remains in force.

## Parent steering for runtime follow-up

The parent approves a bounded test-first implementation of the proposed runtime
identity guard: fresh spawned workers from an immutable candidate, actual module
and code origins, and loaded-definition receipts at parent/worker start and end.
Reject missing or stale identity in final acceptance. This protects against the
demonstrated stale-import/replaced-observer problem; it does not attest a hostile
process. Keep implementation maintainable rather than building a generic Python
attestation framework.

Compiled-definition checks must account for legitimate decorators, descriptors,
defaults and closures without a blind `__wrapped__` bypass. Include replaced
observers, misleading filenames/wrappers, stale internal aliases, outside origins
and missing receipts as rejecting controls; genuine fresh public runs and spawned
workers must pass. Mocked unit collection can be separate from strict candidate
acceptance, but final acceptance must not opt out. Record the actual coverage and
remaining limitations. Full readiness-bundle and policy-receipt checks remain
separate requirements. Cross-task delivery of this steering failed during an app
server shutdown; this local note preserves it for resumption.

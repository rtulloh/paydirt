# General chart placement audit

Status: read-only census recorded November 6, 2026, generalized at the owner's
request after a penalty cluster was observed in the review UI. That census changed
no generator, chart CSV, game rule, source fact or promoted artifact. Its starting
[primary layout procedure](primary-chart-dispersion-proposal.md) optimized BLACK
placement only. The later local v2 implementation is described in that procedure;
this historical census does not qualify it. Follow-up: [DATA-039](issues/DATA/DATA-039.md).

## Scope and method

The census covers all four rendered chart tables for all 60 displayed generated
teams, plus a separate 32-team modern diagnostic candidate. It measures 6,808
column contexts: 828 primary offense, 4,968 defense formation/column contexts,
276 supplemental/recovery and 736 special-team contexts. Defense runs restart
within each five-row formation; other tables use their 30 printed dice rows.
The special-team display includes the shared interception/fumble return mapping;
those two columns are not independent source observations.

Every raw token receives an exact-token census, a lexical result-family census,
actual viewer color and applicable sideline/replacement flags. Numeric entries
also receive explicit sign and magnitude bands. All observed tokens are classified.
The audit measures vertical runs, vertical adjacency, horizontal adjacency and
2-by-2 blocks. It records physical dice mass separately from printed cell counts.
Numeric bands and runs of three are descriptive inspection aids, not statistical
acceptance thresholds or proof of a gameplay defect.

For primary offense only, 128 deterministic independent whole-token permutations
within equal physical-weight groups provide a descriptive reference. This is not
a historical fit test, formal significance test or globally optimal layout.
Multiple comparisons and deliberately BLACK-optimized starting layouts preclude
treating reference-tail counts as a release gate.

A stricter feasibility check examines individual equal-weight swaps that retain
every existing BLACK position. Each reported improving swap passes the existing
whole-token invariant checker. A witness establishes that one cluster can shrink;
it does not establish that all other cluster metrics improve simultaneously.
Protected defense, supplemental, recovery and special-team tables receive
measurement only, without an assertion that their entries may be permuted.

## Findings in the displayed 60-team primary charts

The following categories overlap. Counts refer to column/category contexts.

| Category | Contexts with runs of at least three | Longest run | Contexts with a verified improving swap preserving BLACK |
| --- | ---: | ---: | ---: |
| All penalties | 101 | 9 | 99 |
| Sideline markers | 80 | 12 | 80 |
| Numeric gains 1–4 | 165 | 7 | 127 |
| Numeric gains 5–9 | 83 | 7 | 78 |
| Breakaway family | 5 | 4 | 5 |
| Fumble family | 2 | 3 | 2 |
| Numeric zero | 2 | 3 | 2 |
| Numeric losses | 2 | 4 | 2 |

All 60 teams place every Line Plunge and Off Tackle penalty in rows 10–17.
Across all nine primary calls, 54 teams have a penalty run of at least three.
Those eight rows contain 682 of 1,221 primary penalty cells (55.9%) but only
38.7% of their summed physical penalty mass. The band itself contains 33 of
216 dice faces. None of these aggregates is a policy-weighted engine penalty rate.

Examples of verified one-swap improvements include the largest penalty run
9 to 4, sideline-marker runs 12 to 6, a small-gain run 7 to 3, a breakaway run
4 to 2, and fumble/zero runs 3 to 1. Complete tokens, flags and physical mass
remain unchanged in these in-memory demonstrations. No demonstration is written
back to the review service.

The issue includes two-dimensional placement: 40 of 60 primary grids contain a
2-by-2 penalty block, up to five blocks per grid; 17 contain a 2-by-2 sideline-marker
block, up to seven. Exact repeated tokens also form runs, including repeated
numeric values and individual foul codes.

Long same-color regions require context: primary green runs reach 18 cells,
but positive results occupy much of many rushing columns. Eliminating all green
runs would be an inappropriate objective. BLACK runs reach six; the stricter
swap witnesses deliberately freeze BLACK geometry and therefore make no claim
that those runs are globally unavoidable or should be changed.

## Separate diagnostic candidate and other tables

The independent 32-team modern diagnostic is not a qualified replacement.
It still has primary penalty runs of at least three in 21 teams, sideline-marker
runs up to 12, and QB-time family runs up to seven. Of its 69 QB-time contexts
with runs of at least three, 58 have a verified one-swap improvement with BLACK
fixed. This establishes that the general concern extends beyond the older UI
model, without asserting that both candidates have identical patterns.

Other tables also contain visible blocks: displayed special-team penalty runs
reach 13 and fumble runs reach eight; supplemental QB-time fumble runs reach 11.
Recovery ranges, nearly certain kick success and positive breakaway regions can
be contiguous by construction. Defense signs/replacement entries group within
formations. These measurements require semantic review before any redistribution:
the primary offense invariant must not be extended automatically to dependent
lookups, recovery thresholds, formation rows or distance-dependent kick behavior.

## Follow-up and evidence

Define one general placement policy that inspects all result families, exact
tokens, flags, numeric bands and both vertical and cross-column patterns.
Use frequency-aware feasibility bounds and disclose tradeoffs rather than
introducing a universal cap on every result run. Preserve complete per-weight
whole-token inventories and protected dependencies, retain existing BLACK
improvements, and bind before/after receipts to every generated team.

Before production changes, add failing synthetic/public-2026 cases covering
non-BLACK clusters and conflicting objectives, with unchanged/fixed controls.
Then implement within the existing layout path, regenerate all 60 candidate
teams, verify exact invariants and repeat candidate mechanics/qualification.
Do not solve this through independent class-specific patches or unrestricted
row shuffles.

Ignored evidence lives under
`.ai-audits/release-readiness/general-placement-01/`: the reproducible census,
report, independent raw-CSV verifier and receipt. Report SHA-256:
`633eefe1b61a0a7c4828beb8336839889fe2c52b639abee4848c993000076bc3`.
The verifier checked all 276 CSVs, 6,808 contexts, 106,814 entries and 2,159
individual improving-swap witnesses; it reconciled all 828 earlier penalty
contexts. All checks passed. No game simulations or fresh browser checks were
performed, and no source/model fit or release acceptance is claimed.

The resolved-ticket list was reviewed. This placement-only audit supplies no
new play-test closure evidence; no resolved ticket was closed. Maintained player
guides need no change because gameplay and controls did not change.

The owner requested a BB-session warning. Direct cross-session delivery was
rejected by the messaging tool's approval policy, so the handoff was saved
locally. The owner subsequently supplied BB's acknowledgment: it found and read
the handoff in this repository and shared the concern with its chart audit,
generation and season-validation agents. BB will extend its placement audit and
preserve its own weighted outcomes and dependent lookups, especially
Razzle-Dazzle's shared-roll choices. Receipt is confirmed by the owner's relayed
acknowledgment, not by a successful direct messaging-tool call.


## Retained allocator constraint found during current review

On November 6, the owner identified QT blocks in the new 2024 Bears offense.
The frozen CSV and actual HTTP chart book have QT/QT* at the same twelve rows in
all five passing columns: 10–13, 16–20, 28–29 and 39. Each column assigns 37/216
physical mass to the primary QT lookup. This is not the team's sack probability.
All rows of weight one through five are QT, with none in higher weight groups;
therefore a QT/non-QT equal-weight swap is impossible even without BLACK protection.

The v2 objective includes the pooled QT family, but the inherited per-weight token
inventory freezes that mask. Its exact QT/QT* arrangement improves while pooled
QT geometry remains 32 two-by-two blocks, 48 horizontal pairs and longest run five.
The upstream empirical variant allocator's preference for small row weights is a
separate constraint requiring review, not evidence of globally unavoidable football
structure. [DATA-041](issues/DATA/DATA-041.md) tracks the source of this constraint,
all-family saturation census and test-first allocation follow-up. The protected
supplemental QB Time lookup remains separate. No chart bytes changed for this finding.


## Owner-confirmed scope and disposition requirements

The November 6 follow-up explicitly includes B, QT, BLACK, INT, yellow cells and
unusually repetitive green/red cells. Audit exact symbols, normalized families,
actual rendered colors, flags and numeric bands separately in all four tables.
Inspect vertical runs, cross-column blocks, aligned rows across calls/formations
and repeated masks across teams. Report printed counts and physical dice weights;
colors and raw row counts alone do not establish a gameplay-frequency error.

For each flagged pattern, record the relevant source/model constraint, dependency,
allocation feasibility and explicit disposition or corrective ticket. A lower
combined objective cannot clear an unchanged family pattern. A saturated weight
group means the current layout pass cannot change it; it does not establish global
impossibility or source support. Protected tables remain in the audit even when
redistribution requires a separate semantic proof.

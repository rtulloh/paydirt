# Historical source completion boundary

Status: November 7, 2026 implemented, user-authorized modeling assumptions.
The owned zero-credit field-goal subtype and the explicit
`historical_fumble_class_proxy_v1` policy are implemented locally. No corrected
1983 cohort has been generated or qualified by this work.

The complete 224-game source census preserves 727 fumble events. After fourteen
reviewed official-credit corrections and three supported aborted-field-goal
projections, the strict source-tier model supports 564 and holds 163. The new
class proxy adds 111 explicitly modeled classifications, producing 675 projections
and 52 held events, with zero source conflicts. All 564 prior projection values
are preserved apart from their declared policy name. The modeled additions are
76 identified-QB snap assumptions, nine identified-QB sack assumptions, eighteen
unknown-role snap assumptions, and eight unknown-role sack assumptions.
Private source documents, review packets and census receipts remain ignored.

The new field-goal tokens require reviewed zero rushing credit and known individual
ownership. They preserve separate fumbling and credited actors and unknown
physical movement. The engine consumes a rushing snap with no kick attempt and no
recovery reroll. A fourth reviewed aborted field goal remains held because the
required credit is unknown. These facts do not establish population completeness
or historical fit.

The version-1 census had 52 holds, including 29 known non-QB positions lacking supported class
(13 RB, seven FB, seven C, one WR, one TE); eighteen incomplete or mismatched
primary-gain clauses; three identified QBs with positive gains above one; one
unidentified primary actor; and the field-goal credit gap. These counts describe
the current bound input census, not a universal missing-data distribution.

## Version-1 class assumptions (superseded for the modeled candidate)

Reviewed and explicit source classifications take precedence. When only an
actor-bound primary gain is available, an identified QB within [-1,1] is modeled
as a snap fumble; a QB below -1 is modeled as a sack fumble. A positive QB gain
above one remains held because the current sack representation cannot carry
positive gain. Known non-QB positions do not enter the unknown-role assumptions.

For an actor whose position is unknown, gain below -1 is modeled as a QB sack,
[-1,1] as a QB snap, (1,5] as a running back, and above five as a receiver. The
initial proposed running-back range [-5,5] was superseded by the user's explicit
negative/near-line QB decision; boundary test expectations changed accordingly.

The policy keeps source class, individual credit and physical gain unknown when
unknown. A separate modeled class, assumed role and class-basis label identify
each inference. Known ownership is still mandatory. Supported physical gain wins
over credit and actor-bound reported gain. Loose-ball and recovery advances remain
separate facts; terminal recovery position is not currently authorized as a gain
proxy. A snap assumption uses the existing rushing statistical category: one
offensive play/rush, with no pass attempt, completion or sack. A sack assumption
uses the existing passing/QT supplement: one sack/dropback, no pass attempt or
completion. A receiver assumption uses a completed-pass category. These are model
categories, not new official individual credits.

Portable PFR ledgers and manifests declare the policy, contract version 1,
modeled class counts and false source-class/physical-truth flags. A portable recipe
must select the exact policy; its source contract must bind the manifest's exact
`modeled_fumble_assumptions` object. Source preparation rejects changed versions,
truth claims, unreconciled counts and implicit policy substitutions. Schema-2
projection receipts preserve original source facts alongside modeled fields.

Under version 1, the 52 remaining events blocked corrected generation. This modeling decision
does not pass the former strict source-completeness claim, waive fit requirements,
authorize missing ownership, or widen accuracy tolerances. Keep all 727 source
events and their byte bindings; do not substitute the old cohort for a corrected
candidate. Further gain/actor decisions must remain explicit and versioned.

## Authorized modeled scope, version 2

`historical_fumble_class_proxy_v2` extends the explicit version-1 policy: known
RB/FB positions use rushing, known centers use the rushing snap category, known
WR/TE positions use completed-pass/receiving, and identified QB gains above one
use rushing. Explicit observed actions, reviewed classes and official credits
continue to take precedence. Five reordered sack clauses now retain their
unambiguous same-actor source loss; no terminal recovery position supplies gain.
These are modeled statistical categories, not recovered historical facts.

The current complete census retains 727 events: 564 previous supported
projections, 143 role assumptions and five reordered source sack losses, leaving
15 unresolved. The role assumptions comprise 76 QB snaps, nine QB sacks, three QB
rushes, eighteen unknown-role snaps, eight unknown-role sacks, twenty known RB/FB
rushes, seven center snaps, and two known WR/TE receptions. Source conflicts: zero.

The user authorized uniform fitting-only omission of isolated unresolved events.
`historical_isolated_fumble_exclusions_v1` excludes every remaining unresolved
fumble projection, independent of team or measured chart fit. It retains the full
ledger, raw game/play hashes, reasons, event IDs, ownership and team/mechanism
counts. Fourteen exclusions lack supported primary gain/actor interpretation;
one is the reviewed Chicago aborted field goal with unknown credit. The detached
Dave Brown event is excluded rather than converted to an offensive rush. No
historical game result, failed check or official source total is removed.

The fitting population is 712 of 727 events (15 excluded, 2.063%). Known lost
fumbles change from 420 to 415; the single unknown-ownership event is excluded.
The 712 fitted events all have known ownership. Exclusion counts are CLE/DET two
each; ATL, BAL, CHI, DEN, GNB, MIA, NYG, NYJ, RAI, RAM and SEA one each; fifteen
other teams zero. Full and fitted denominators and per-team lost counts remain
bound in the portable manifest and source contract. These omissions affect rare
fumble/lost-fumble fitting numerators; their small cohort share does not establish
that any individual team's rate or historical outcome is unaffected.

Portable recipes must explicitly select both policies and bind the exact
`modeled_fumble_assumptions` and `fumble_fitting_policy` disclosures. Factual
historical completeness remains false; modeled-scope eligibility is a distinct
claim. Source conflicts and unrelated required-field gaps cannot be suppressed.
Existing accuracy tolerances remain unchanged. Candidate generation and fresh
accuracy/simulation measurements are required before claiming corrected fit.

The corrected 28-team modeled candidate completed fixed 16-repetition source
normalization and a separate 64-repetition engine measurement under unchanged
bounds. Two completion-rate exceptions remain: 49ers 0.610006 versus 0.642045
(tolerance 0.03), Falcons 0.601726 versus 0.633136 (tolerance 0.03). All other
measured team metric bounds passed. This is an explicit exception report, not a
passing accuracy verdict or a reason to widen tolerances. The fresh 256-season
historical outcome run uses these frozen corrected chart bytes.

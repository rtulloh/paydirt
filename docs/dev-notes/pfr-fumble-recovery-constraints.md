# Uniquely determined PFR fumble-loss ownership

Development proposal under the [chart-confidence charter](chart-confidence-agent-charter.md).
Implemented locally after the test-first baseline below. No favorable recovery default, target-count
exception or release approval is proposed.

The full team-game box reports total fumbles and losses, including events absent
from the current offensive subset. Known source recoveries are a subset of those
counts. Missing recovery ownership can be determined only when every feasible
assignment has the same result. If known losses already exhaust the box losses,
all unknown and unseen events must be retained. This does not require observed
fumble completeness. If observed fumbles exactly equal the full box count and
remaining losses equal the number of unknowns, all unknowns must be lost. Other
cases remain unknown; never select one event to fill a residual loss count.

Before inference, require a complete, valid two-team `Fumbles-Lost` box row,
unique source-event keys, observed event count no greater than the box total,
known losses no greater than official losses, and known retentions no greater
than official retentions. Invalid/contradictory counts cannot support inference.
An absent box supplies no implicit zero. The source subset need not include
returns, all retained fouls or every fumble, so partial coverage cannot support
the all-unknown-lost inference. Known identities remain unchanged.

Record the method and all pre-inference integer constraints for each resolved
event in the source ledger. Original narrative and parsed boxes remain unchanged;
raw HTML hashes already bind both. Report unresolved ownership and source-box
conflicts, and refuse generation when either remains. This is a logical deduction
from reviewed source counts, not an observed recoverer name or physical gain.

Synthetic baselines will cover uniquely retained/lost cases, missing events,
mixed ambiguous assignments, missing/malformed/duplicate boxes, contradictory
counts, and both teams/units. A source inventory suggests 31 of 40 unknowns are
uniquely determined under these rules; this is feasibility evidence, not the
production result. Remaining events and required gains need independent evidence.

## Implementation evidence

Fourteen new cases first fail (four direct ownership behaviors and ten missing
box/receipt/consistency capabilities), with 59 PFR controls passing. Separate
root and source-gate contradiction mutants each fail first with three and two
passing controls. The implementation retains all ambiguous assignments, records
integer proof receipts, and refuses source-box contradictions. Two additional
controls verify both teams/units and reject duplicate source-event keys. All
165 PFR/provenance/source-gate tests pass; lint passes.

Fresh 224-game classification resolves exactly 31 recoveries (29 retained, two
lost), leaving nine unknowns across eight team-games. No contradictory source box
is observed in this cohort. The total is 713 fumbles and 417 known losses; this
is the current classified subset, not a full official fumble-count claim. All 28
teams still reconcile sack/INT/FGA targets and two runs reproduce the ledger byte
for byte. Two required gains and 25 sack severities remain unknown. Source
chart generation and release remain blocked; the inference does not determine
physical initial gain or a recoverer name.

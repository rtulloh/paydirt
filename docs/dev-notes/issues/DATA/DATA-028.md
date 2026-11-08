---
id: DATA-028
title: Unknown required source facts remain explicit; qualification pending
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
---

## Current audit — 2026-11-08

The committed adapters preserve unknown recovery as None, inventory missing required gains and reject unsupported required fields instead of manufacturing zero gain or retention. The source gate checks required-field coverage and ledger identity. Reviewed 1983 source facts and explicitly opted-in modeled fitting exclusions are separate from fabricating facts. Current parser, calibration and gate controls pass. Mark resolved, not closed: final source/candidate and play-test review remains required. Physical-versus-credited movement and compound-event modeling stay separately tracked under DATA-030 and DATA-036.

The original investigation and checkpoints below are retained as history.

## Description

Independent reviewer and parent reproduce nflverse flagged sacks with blank gain
becoming primary QT plus numeric-zero scramble, while sack occurrence remains
one and no missing-gain diagnostic is recorded. Blank completed/run gains also
become zero. Blank fumble-loss flags become false. PFR missing recovery actors and
unrecognized names similarly become retained fumbles. Calibration can replace an
existing one-of-one official loss with zero losses and an always-retained range.

## Resolution / verification

Twenty new classification/calibration/root-command cases fail; four known-zero
and loss controls pass. Unknown gain must produce no fabricated chart result and
retain its source occurrence/provenance. Unknown recovery is `None`, never false;
actual generators and source gates must refuse unsupported required fields before
issuing a candidate manifest. A known zero gain or retained fumble remains valid.
Record source identities and unsupported fields in ignored audit evidence.

A retained touchdown also must not erase a known fumble occurrence merely because
the touchdown branch executes first. This is occurrence evidence, separate from
reconciling initial versus net recovery movement (tracked independently).

Fresh source regeneration and full acceptance evidence are required; keep open.
No official target or fixed bound changes. The zero-yard-sack representation is a
separate confirmed capability gap, not permission to fabricate negative loss/F.

## Comments

--- 2026-11-05 21:12 ---
The local adapters retain unknown recovery as `None`, emit unsupported required
gain/recovery identities, preserve known fumble occurrence on retained TDs, and
refuse generation rather than invent facts. Source acceptance rejects the new
diagnostics. Twenty initial expected failures and three TD/gate follow-ups
preceded correction; 182 focused tests passed. A separate manifest-coverage
hardening check remains to be added before final source acceptance.

--- 2026-11-05 21:21 ---
Five required-field coverage mutants were accepted by the intermediate source
gate: absent declaration, unknown/nonzero unsupported counts, missing hash and a
nonempty-ledger hash declared with zero unsupported fields. The gate now requires
the nflverse generator's zero-count/canonical-empty-ledger declaration; 54 focused
source/root-command tests pass. The conversion coverage fixture now supplies this
additional valid declaration; its prior assertions remain. Raw-input byte checks
and independent regeneration are still separate final requirements.

--- 2026-11-05 21:20 ---
The current 2024 retained ordinary pass/run sample has no missing required gain
or unknown fumble-loss flag in the initial inventory. Synthetic failures still
matter for the reusable procedure and prospective transfer. They do not prove
current-cohort contamination from missing values; source zero-sack and initial/net
fumble distinctions are separately confirmed.

--- 2026-11-05 21:37 ---
The 224-game regular-season PFR inventory exposes a separate parser capability
bug: four-letter historical field codes cause a known recoverer's location to
become part of the name. Eight synthetic cases first produce four expected
failures and four passing short-code controls. The bounded location correction
reduces unknown recovery identities from 163 to 42 across 696 fumbles. The
remaining inventory exposes initials being truncated at a period and a known
name followed by an incomplete location. Six additional regressions fail with
43 controls passing; whole known-name matching now retains initials and requires
an explicit clause boundary, with unknown names/prefix extensions still unknown.
The fresh inventory has 39 unresolved recoveries and 402 known losses. These
are descriptive source counts, not a historical-count acceptance result; unknown
recoveries still block PFR generation. Full source reconciliation remains open.

--- 2026-11-05 21:50 ---
The new typed primary-source path preserves a known sack fumble even when its
physical initial severity is unknown. Two root-ledger cases fail before every
fumble event (including unknown ownership) is exposed in the ignored ledger.
The integrated source/generator/engine suite passes 257 tests. A subsequent
source-gain regression independently finds PFR missing completion/run severity
being dropped or filled from recovery returns; the new required-field ledger and
root refusal pass 93 PFR cases after eight expected failures. Existing canonical
F formatting and error capitalization corrected two newly added test assertions;
no existing test expectation is weakened. Actual source inventories remain
required before calibrating or clearing this issue.

--- 2026-11-05 21:55 ---
A reviewed subset/whole-box constraint now resolves ownership only when every
feasible assignment agrees. Fourteen initial expected failures/59 controls and
separate root/source-gate contradiction mutants precede implementation; 165
focused cases pass, including both teams/units and duplicate identity controls.
The fresh 224-game ledger resolves 31 recoveries (29 retained/two lost), leaving
nine unknowns. There are no source-box contradictions in this cohort. Original
narratives and known identities remain unchanged; each deduction records its
integer proof and byte-bound source. Two required initial gains remain unsupported
and 25 counted sacks lack severity. Generation remains blocked; keep open.

--- 2026-11-05 22:16 ---
Official gamebooks resolve the nine remaining ownership gaps and both required
gain/split-row gaps through byte-bound reviewed facts. Ten expected capability
failures and three later semantic mutants precede the schema-2 extension; 340
integrated cases pass with lint. The fresh 224-game classification reproduces
byte for byte, has zero unknown recoveries/missing required completion-run gains,
and preserves all 28 teams' sack/INT/FGA counts. Thirty further ownership facts
still follow unique team-box constraints. Twenty-five sacks lack physical
severity; out-of-bounds and prepass fumbles expose model limitations. Keep open
for these distinctions and final play-test confirmation; no candidate promoted.

--- 2026-11-06 00:05 ---
The maintained public-source archive/staging/preparation chain reproduces both
full cohorts (84/96 CSVs), complete generation manifests and chart fingerprints
from relocated actual inputs. This supplies fresh source reproducibility,
not final source-fit/held-out or complete play-test acceptance. Representation
and source-model distinctions remain explicit; retain open pending the remaining
charter validation. No private reference inputs are opened or exported.

--- 2026-11-08 17:08 ---
The committed adapters preserve unknown recovery as None, inventory missing required gains and reject unsupported required fields instead of manufacturing zero gain or retention. The source gate checks required-field coverage and ledger identity. Reviewed 1983 source facts and explicitly opted-in modeled fitting exclusions are separate from fabricating facts. Current parser, calibration and gate controls pass. Mark resolved, not closed: final source/candidate and play-test review remains required. Physical-versus-credited movement and compound-event modeling stay separately tracked under DATA-030 and DATA-036.

Reviewed current committed implementation and existing issue evidence. Fresh
focused validation: 239 gameplay/ownership/source/runner/standings checks and
417 parser/reconciliation/generation/source-bundle checks pass, without skips
or warnings. These focused checks are not full regression or new season runs.
See [high-priority audit](../../high-priority-issue-audit-2026-11-08.md).

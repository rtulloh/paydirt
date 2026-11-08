---
id: DATA-021
title: Generated supplemental columns contain symbols that invoke unintended engine fallback
status: closed
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at: 2026-11-08
tags:
  - reproduced
  - regression-test
---

## Description

Generated QB-time columns contain OFF/DEF penalty cells on 53 of the 60 promoted
public-generated teams (23/28 in 1983-generated, 30/32 in 2024). The core's
`resolve_qb_scramble` accepts numeric/OOB and fumble results; unsupported symbols
invoke uniform random yardage from -5 through 10. The foul is therefore not
resolved as a foul. The adapters' accepted-penalty branches incorrectly place QB
run penalties into the conditional supplemental sample. B and special columns
also need column-specific compatibility checks rather than a shared permissive
result grammar. Historical source classification and engine representation must
remain distinguishable.

## Resolution / verification

Add rejecting generated-symbol checks and synthetic regression controls first.
Represent source fouls in primary play samples with declared heuristic family
assignment when the call is unobserved. Keep raw source details and event IDs,
report this normalization, and do not silently discard fouls or invent secondary
penalty rules. Generic generation rejects unsupported conditional input. Preserve
the legacy engine fallback for legacy charts. Regenerate staged candidates and
check physical mass, event preservation and downstream metrics before review.

## Comments

--- 2026-11-05 18:56 ---
Newly confirmed by the exact mechanics implementation and independently checked
by the parent. The analytical audit measures existing fallback behavior for the
baseline; measuring it does not grant generated compatibility acceptance.
Release remains held. See the [implementation record](../../chart-confidence-implementation.md).

--- 2026-11-08 16:38 ---
Follow-up review corrects the overly conservative November 8 reconciliation.
This specific compatibility defect is fixed in the shipped v1.10.2 source:
column-specific supported_generated_cell guards reject unusable empirical QT/B
and special-team symbols; PFR/nflverse regressions preserve QB fouls as primary
samples rather than conditional QB-time penalties. The legacy engine fallback
is intentionally retained and is not itself an unresolved generated-chart bug.

Fresh scan of all 60 shipped teams finds zero OFF/DEF penalty cells in either
B or QT (formerly 53 affected teams). Both complete public season audits pass
structure/consumer compatibility with no errors, including special columns.
Fifteen focused producer/adapter/column-guard regressions pass; 189 unrelated
cases were deselected. Existing release evidence includes reproduced source
cohorts and the v1.10.2 all-60-team mechanics/decoder checks and thirty complete
real-engine games, followed by successful hosted qualification. The INT-only
1.10.2 migration preserved B/QT and special-team files. Combined with the
fresh complete artifact inspection, this satisfies the narrow compatibility
finding beyond unit tests alone; broader source-model and fit tickets remain
open. No historical accuracy, new full regression or general release
certification is claimed by the public component audits.

Receipts remain ignored under .ai-audits/issue-reconciliation-20261108/.
See [published scope/evidence](../../release-1.10.2-scope.md) and the updated
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

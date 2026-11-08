---
id: DATA-026
title: Opponent adjustment reduces outcome categories with chronological prefixes
status: resolved
priority: High
created-at: 2026-11-05
resolved-at: 2026-11-07
closed-at:
tags:
  - reproduced
  - regression-test
---

## Description

Independent Astra review identified `_adjust_chart` selecting
`sources[index % len(sources)]` when fitted category counts differ from observed
counts. Reducing forty gains (twenty zero, then twenty eighty) to thirty-two gains
retains a chronological prefix with mean thirty. Reversing the identical source
multiset produces mean fifty. Counts, fitted opponent effects and source strength
are unchanged. Downstream resampling cannot recover the discarded distribution.

## Resolution / verification

Synthetic controls require source-order invariance, representative conditional
bimodal sampling, identical category totals, and a flat out-of-bounds control.
A general deterministic representative selection must operate on adjusted source
outcomes, preserve symbols/flags, and disclose finite-sample tail or variant
omission rather than forcing an unattainable rare event. No team-specific gain
normalization or source target change is a solution to this defect.

Regeneration, source reproduction, larger training and the full charter remain
required. No public charts are promoted; keep open pending that evidence.

## Comments

--- 2026-11-05 21:12 ---
Deterministic midpoint quantiles now sample the full adjusted conditional
population after gain adjustment. The forward/reverse reproduction both yield
mean 40 with unchanged fitted category totals. Whole tokens/flags and explicit
source/selected result counts, ranges, means and omitted variants are reported.
Three initial expected failures plus a separate diagnostics failure preceded
the correction. Sixty-six focused tests passed, including CDF-error, balanced
support replication and a rare-tail omission disclosure. This is finite modeled
sampling evidence, not proof of exact raw-source tail preservation.

--- 2026-11-05 21:05 ---
Independent-review reproduction is synthetic and public-safe. Reserved seeds and
prospective transfer data remain unopened. Original source rows remain intact.

--- 2026-11-08 16:48 ---
Owner-requested implementation-status reconciliation: Representative midpoint-quantile selection is committed in empirical_adjustment.py; regenerated source/population and independent validation remain pending.

The implementation was integrated into the shipped release line by November 7;
older uncommitted/keep-open checkpoint wording is superseded for status only.
Mark resolved because the code fix is committed, and retain empty closed-at
until the recorded issue-specific play/audit/review requirements are met.
No gameplay, tolerance, source model or test expectation changed. General green
CI or unit tests alone are not used to close this ticket. See the
[reconciliation](../../open-issue-reconciliation-2026-11-08.md).

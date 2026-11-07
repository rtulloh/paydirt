---
id: DATA-039
title: Primary chart dispersion scores BLACK only and leaves other reducible result clusters
status: open
priority: Low
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-layout
  - investigating
links:
  - DATA-040
  - DATA-041
---

## Description

The owner observed clustered penalties and requested an audit of other teams and
all other result types. The 60-team review layout puts every Line Plunge and Off
Tackle penalty in rows 10–17. Primary penalty runs reach nine, sideline-marker
runs twelve and small-gain bands seven. Breakaway, fumble, zero and repeated-token
clusters also occur. The audit-time layout objective scored only BLACK geometry,
so it could not detect or improve these other patterns. The separate 32-team
diagnostic also retained reducible non-BLACK clusters.

This is demonstrated placement debt, not evidence by itself that event
frequencies or gameplay are wrong. Full scope, protected-table findings,
overlapping counts, limitations and receipts are in the
[general placement audit](../../general-chart-placement-audit.md).

## Resolution / verification

Generalize the existing placement policy and evidence across exact tokens,
families, flags, numeric bands, colors and two-dimensional blocks. Establish
test-first synthetic/public-2026 cases and passing controls before production
changes. Preserve per-weight whole-token inventories, dependent lookup semantics
and existing BLACK improvements. Avoid universal run caps or unequal-weight
shuffles; disclose feasible tradeoffs and constrained placements.

Regenerate and validate all 60 candidate teams after implementation. Keep source,
fit, mechanics and release qualification separate from layout diagnostics.
Do not redistribute protected defense/recovery/special columns without an
independent semantic proof. The original census itself implemented no fix; see
the local v2 checkpoint below.

## Comments

--- 2026-11-06 16:43 ---

The read-only generalized census covers all four tables for 60 displayed teams
and a separate 32-team diagnostic: 6,808 contexts. An independent raw-CSV check
passes all 276 files, 106,814 category entries, 2,159 improving equal-weight
swap witnesses preserving every BLACK position, and all 828 earlier penalty
contexts. These are overlapping per-category witnesses, not a jointly optimized
candidate. No chart bytes changed; no game or browser qualification is claimed.
The resolved tracker was reviewed without new closure evidence.

--- 2026-11-06 20:10 ---

Local `equal-weight-primary-outcome-dispersion-v2` is implemented: retain the
BLACK-first pass, freeze its map, then jointly minimize frequency-normalized
exact-token/family/flag/numeric-band run and cross-column costs. Whole tokens
move only within the same physical-weight group; protected tables stay fixed.
Grid-wide normalization and neighbor costs deliberately allow a source change
in one column to alter another column's printed positions without changing its
allocation or weighted behavior. The empirical-column regression now proves
exact pre-layout unaffected allocations, complete per-weight token inventories,
protected tables and typed resolved distributions in both resolver routes; its
old post-layout Line Plunge row-identity expectation was incorrect. Existing TE
pooling and Short Pass rate/mean assertions remain unchanged.

The interrupted worker's unchanged-production baseline log was not recovered.
An explicitly labeled in-process BLACK-only control fails all six non-BLACK
family regressions with 17 controls passing. Current v2 passes; 113 focused
layout/generator/allocation/pressure tests and 375 documentation/tracker tests
pass. Public controls cover all nine primary calls plus QB Sneak. Bounded cost
accounting agrees for six synthetic and both public-2026 teams, with exact
invariants, BLACK-map protection, deterministic repeatability and idempotence.
Receipt/handoff: ignored `.ai-audits/release-readiness/data039-primary-resume-01/`.
No review-service chart bytes were replaced and no release or historical-fit
acceptance is claimed. Keep DATA-039 open pending all-team candidate evidence
and integrated qualification, which the parent agent owns; the human owner's
remaining work is a compact visual/usability review and release decision.


--- 2026-11-06 20:24 ---

The owner reaffirmed the audit scope: B, QT, BLACK, INT, all yellow cells and unusually repetitive green/red cells. Report exact tokens, pooled result families and actual viewer colors separately across all four displayed tables. Examine runs, two-dimensional blocks, matching rows across calls/formations and repeated patterns across teams, with printed counts and physical dice mass. Preserve lookup dependencies; distinguish the primary QT trigger from its supplemental lookup and shared-return display aliases from independent observations. Every flagged pattern needs evidence and an explicit disposition or corrective ticket; lower aggregate layout cost alone does not clear a category. The current Bears QT family is a concrete remaining allocator constraint, tracked in DATA-041, and is not fixed by the v2 equal-weight layout pass.

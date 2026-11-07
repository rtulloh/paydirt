---
id: DATA-021
title: Generated supplemental columns contain symbols that invoke unintended engine fallback
status: open
priority: High
created-at: 2026-11-05
resolved-at:
closed-at:
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

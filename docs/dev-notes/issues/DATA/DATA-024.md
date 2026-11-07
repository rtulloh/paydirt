---
id: DATA-024
title: Two-point rushing attempts contaminate regular nflverse chart inputs
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

The 2024 nflverse regular-season population includes 135 conversion attempts:
99 passing rows were reported as unclassified and 36 rushing rows became
ordinary zero/two-yard rush samples. Conversion attempts belong outside the
regular chart/stat population. Their foul, turnover, sack and fumble flags must
not contaminate ordinary samples or recovery budgets.

## Resolution / verification

Seven synthetic behavior cases fail before exclusion; thirteen existing controls
pass. The local fix excludes conversions before regular classification. Further
controls require game/play exclusion provenance, explicit missing-capability
reporting, ordinary two-yard touchdown retention and text-marked conversions
when a structured flag is unavailable. Eleven ledger/schema controls fail before
that follow-up. Five source-gate mutants fail while the declared-coverage control
passes. Incomplete/conflicting conversion coverage cannot certify a source.

Keep excluded event identities and detail hashes in an ignored audit ledger,
bound to the public manifest by SHA-256. Counts remain explained rather than
silently discarded. Official statistical targets stay fixed. Regeneration,
reproduction, all-team training and the full charter remain required; keep open.

## Comments

--- 2026-11-05 20:39 ---
Found during source/QB residual decomposition before any per-team calibration.
Raw credited totals reconcile all 32 official team targets after excluding
conversions and adding lateral rushing credits to team rushing yards. Those
credits add no ordinary attempt or invented chart call. The generator already
uses full physical `yards_gained`, which is distinct from individual yard credit.
See [nflfastR field documentation](https://nflfastr.com/reference/fast_scraper.html)
for the individual/lateral rushing-yard distinction. No public data promotion,
commit, push, tag or release is authorized. Prospective 2023 remains unopened.

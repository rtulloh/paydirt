# Independent chart confidence review request

Owner-requested review and analysis only. The reviewer must not edit code,
tests, documentation, contracts, charts, thresholds, source data or seeds; must
not commit, push, tag, publish or run an automatic fixer; and must not delegate
implementation. Return findings and recommendations in the review thread.

## Purpose and current status

Assess whether Paydirt's generated-chart method and its acceptance evidence can
support a future release, including seasons without developer reference charts.
The current candidate is work in progress and release remains held. Public chart
CSVs have not been promoted. Passing mechanics tests is not historical accuracy.

Read the repository's `AGENTS.md` and these development records:

- `docs/dev-notes/chart-confidence-agent-charter.md` — fixed acceptance scope,
  metrics, regression requirements and end state.
- `docs/dev-notes/chart-confidence-implementation.md` — implementation evidence
  and its limitations; independently verify claims rather than adopting them.
- `docs/dev-notes/chart-reference-comparison-protocol.md` — full 1983 baseline
  comparison and prospective source-only transfer validation.
- `docs/dev-notes/generated-offense-black-cell-audit.md` — original visual concern.
- `docs/dev-notes/chart-source-denver-1983-coverage.md` — unresolved source sack.
- `docs/dev-notes/source-driven-gain-normalization-proposal.md` — proposal only,
  not implemented or approved. Conversion corrections must be measured first.

The implementation task is `01a1ae4d-2d05-7d73-867b-33f5cd0badba`; coordinating
parent is `01a1ac6f-523a-7103-b693-b01d7f61351e`. Work from this checkout:
`/Users/rtulloh/work/paydirt`. It contains owner work and evolving agent changes.
Record HEAD, actual imported module paths, and SHA-256 identities for reviewed
files, recheck them when reporting, and disclose changes during review. This is
an independent design/current-code review, not a frozen final release approval.

## Review questions

1. Are source occurrence counts, eligible populations, missing values, penalty
   representations, conversions, lateral yards, and provenance handled honestly?
   Can a missing/ambiguous source fact silently become a valid zero or target?
2. Do physical dice weights, finite row allocation, priority rules, joint INT/QT
   exposure, supplemental outcomes and observer definitions match the real core
   engine? Are fixes general rather than tuned to observed clubs or reference
   cells? Examine omitted variants, rare events, tails and capacity conflicts.
3. Can the acceptance gates pass incomplete teams, omitted metrics, failed games,
   stale reports, mixed runtime identities, altered source targets, precision
   too low for a claim, or a deliberately reintroduced repeated-pattern defect?
   Distinguish point-error engineering bounds from statistical precision claims.
4. Do engine receipts, per-team results, league summaries, legal game completion,
   replication uncertainty and policy sensitivity actually reconcile? Identify
   any untested stateful path or unsupported assertion of accuracy.
5. Is the full 1983 developer-corpus comparison fair and useful without copying
   reference cells? Does the prospective 2023 protocol test transfer of the
   frozen source-driven procedure? Distinguish seed, team and season validation.
6. Critique the unimplemented gain-normalization proposal, including source
   sample shrinkage, cohort anchor, numerical caps, B-trigger preservation,
   fumble classification, tails, quantization and pre-state versus engine means.

Inspect implementation and existing regressions directly, especially
`paydirt/chart_generator.py`, `paydirt/play_resolver.py`, source adapters,
`paydirt/chart_calibration.py`, audit/gate modules, their scripts, configuration,
tests and CI. Independently reproduce a small number of high-value claims with
synthetic/public fixtures if useful. Use `/opt/homebrew/bin/python3.11` for tests.
Avoid parallel broad suites while implementation validation runs. Put incidental
test output/cache in a temporary directory; add no files to this checkout.

## Boundaries and deliverable

Do not open or run reserved final seed families 20361108, 20461108 or 20561108;
do not fetch/inspect prospective 2023 source data or generated outputs. Do not
alter the fixed acceptance criteria. Do not copy/export private developer
charts, raw source data, reference-derived reports or narrative logs. Existing
local evidence may be read; any examples returned must be synthetic or public.

BB's independent Astra review found analogous *research* risks around hashing
checkout bytes instead of imported runtime, omitted empty teams/failed games in
a statistical helper, precision not used by a tolerance helper, and an FG
tolerance without a corresponding source target. These are review prompts, not
proof of equivalent Paydirt defects.

Return severity-ranked actionable findings with file/line references, reasoning
or reproduction evidence, assumptions and uncertainty. Separate confirmed bugs,
validation gaps, model limitations and optional improvements. Identify which
claims are supported today, release blockers, and concrete evidence needed to
close them. State the actual model used and reviewed fingerprints. No fixes.

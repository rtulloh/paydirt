# Generated source consistency audit — 2026-11-05

This investigation covers the promoted independent public-source reconstructions
under `seasons/1983-generated` and `seasons/2024`. Imported private historical
charts were excluded. The fictional public 2026 teams supply unit-test fixtures;
they are not evidence of historical accuracy.

## Reproducibility and source identities

Both sets were regenerated independently from the saved public statistical/PBP
inputs, using each promoted manifest's seed, calibration profile and source
selection. All **180 chart CSV files reproduced byte for byte**: 84 in 1983 and
96 in 2024. Both existing structural gates passed. Detailed classified outputs
and reports remain in ignored `.ai-audits/generated-source-audit-uno04786/`.

Normalized source offense/defense league totals agree exactly in both seasons
for rushing attempts/yards/touchdowns and passing attempts/yards/touchdowns,
completions, interceptions, sacks and sack yards. Team identities and seasons,
nonnegative counting fields, completion/interception denominators and fumble-loss
bounds pass validation. Reproduction and internal agreement do not establish
upstream accuracy or resolved engine fit.

Compact reviewed contracts in
[`1983`](../../config/chart-validation/1983.json) and
[`2024`](../../config/chart-validation/2024.json) retain the public
regular-season schedules (224/272 games), aggregate and per-team statistical
counts/rates, attribution, the selected profiles, input identifiers/SHA-256
hashes, manifest hashes and chart file fingerprints. They contain no raw PBP or
original game charts. The five tolerances are the previously declared calibration
tolerances, not selected after inspecting new engine results. Reusing them does
not establish scoring, pace, team-level or policy-independent accuracy.
Field-goal attempts/makes remain reviewed source facts and their resolved
accuracy remains a diagnostic; no field-goal fit tolerance was invented or
certified by the five-metric gate.

## Blocking source discrepancies

The stricter gate intentionally fails both promoted sets until the classified
source events are reconciled with their official aggregate counts:

| Set | Event | Classified | Official aggregate | Difference |
| --- | --- | ---: | ---: | ---: |
| 1983 | Interceptions | 629 | 620 | +9 |
| 1983 | Sacks | 1,207 | 1,215 | −8 |
| 1983 | Field-goal attempts | 775 | 771 | +4 |
| 2024 | Sacks | 1,306 | 1,314 | −8 |

The 1983 field-goal difference is one extra classified attempt each for the
Bears (26 versus 25), Cardinals (29/28), Dolphins (28/27) and Rams (21/20).
`calibrate_stats_from_pbp()` consumes classified field goals, so this discrepancy
affects generated inputs rather than merely a printed diagnostic. Its cause is
not yet established. The diagnostic interception/sack count differences also
require event-level reconciliation rather than assumptions about exclusions.
No reconciliation was invented or added to pass this audit.

These discrepancies are distinct from malformed or duplicated output charts:
the files reproduce consistently from their existing inputs. A source change
must be reviewed, independently regenerated and measured through the engine.

## Disclosed modeling and evidence limits

The 1983 manifest records 16,141 heuristic pass-depth classifications and 1,128
penalties with an unknown play family. Six season-wide missing annotation
families use declared modeling defaults: offensive out-of-bounds markers, punt
fair catches, field-goal blocks, field-goal/punt snap fumbles and interception-
return fumbles. The 2024 manifest has 99 unclassified passes and two modeled
snap-fumble families. Such assumptions cannot be recovered by additional seeded
simulations alone.

Neither promoted manifest originally stored cryptographic input hashes. The new
contracts fingerprint the locally reviewed normalized inputs; that identifies
the reviewed files without independently authenticating their upstream content.
Missing ignored raw files in a clean checkout remain explicitly unverified;
reviewed contract checks do not silently turn them into verified raw evidence.

The saved final 64-season training and 256-season held-out reports reconcile all
raw league counts to their team totals. Training samples are 1,024/1,088 games
per team; held-out samples are 4,096/4,352. However, the ignored batch script's
`chart-focused` label instantiated `ComputerAI`, not its defined
`ChartFocusedAI`. These reports establish completed counts under the actual
generic policy, not a fixed tactical policy. They also predate subsequent engine
timing changes. Their historical fit evidence must not substitute for the new
explicit-policy/current-engine assessment.

## Automated consistency gate

[`audit_generated_source()`](../../paydirt/generated_source_audit.py) returns
`passed`, `errors`, `warnings`, `checks` and structured `findings`. It checks
manifest arithmetic/inventory, normalized source fields when supplied, declared
source hashes when available, strict chart structure and independent regeneration
when supplied. A reviewed contract additionally enforces manifest/profile/chart
fingerprints, schedule/game counts, per-team and league source-rate arithmetic,
and source-derived targets. Classified-source discrepancies are errors; an exact
reviewed league reconciliation with a stated reason remains visibly recorded.
Team discrepancies cannot cancel silently at the league level.

```bash
python3 scripts/audit_generated_sources.py --season 1983 \
  --stats-dir .ai-audits/chart-generation/1983-stats \
  --reproduced-dir .ai-audits/generated-source-audit-uno04786/1983 \
  --output .ai-audits/generated-source-audit-uno04786/source-1983.json
```

The command exits **1** for the unresolved discrepancies above; the corresponding
2024 command also exits 1. Missing optional raw/reproduction evidence is a warning
with a false check rather than a claim of verification. Release orchestration
must require its selected evidence and real-engine checks as well.

Test-first validation: the original structural-only gate produced 11 expected
source-consistency failures and three passing controls. Contract controls first
demonstrated the missing contract API, then passed after implementation. Three
additional mutants exposed undetected team cancellation, changed normalized
counts and manifest metadata drift; all failed before hardening. All 29
synthetic/public-fixture regressions then passed. No existing test expectation was
weakened and no generator, core-engine or team chart data changed in this audit.
Two further failing mutants exposed impossible field-goal counts and a malformed
contract crash; both now produce failing reports. The suite contains 31 cases.

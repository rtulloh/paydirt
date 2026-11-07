# Generated defense similarity audit

Read-only investigation completed 2026-11-05. This records generator limitations,
not a new gameplay feature or a claim of historical accuracy.

## Finding

Every team in the promoted generated sets has a distinct defense. Their repeated
appearance comes from a shared tactical template: most result mechanisms occupy
the same positions even when numeric values differ. A few team pairs are nearly
identical; this is not true of every pair.

| Generated set | Teams / unique defenses | Median pairwise exact agreement | Median nearest-team agreement | Teams with a nearest match of at least 90% |
| --- | ---: | ---: | ---: | ---: |
| `1983-generated` | 28 / 28 | 51.5% | 79.1% | 2 |
| `2024` | 32 / 32 | 55.2% | 87.2% | 6 |

All 60 promoted defenses are distinct, including cross-season comparisons.
The closest 1983 pair, Bengals/Raiders, differs in 9 of 270 cells (96.7%
agreement; 99.13% when weighted by defensive dice probability). The closest
2024 pair, 49ers/Titans, differs in just 2 cells (99.26%; 99.79% weighted).

Classifying cells as ordinary numbers, parenthesized overrides, interceptions,
incompletions, pressure or touchdowns gives 252/270 invariant positions across
the 1983 cohort and 254/270 across 2024. Median pairwise mechanism agreement is
98.15% and 98.52%, respectively. These are result mechanisms, not cell colors.

The public fictional 2026 preview teams are also distinct: Ironclads and
Thunderhawks differ in 111/270 cells, while their mechanism arrangement agrees
in 97.8% of positions. Thus the preview demonstrates the same visual pattern.

## Cause and practical limits

[`chart_generator.py`](../../paydirt/chart_generator.py) defines one
`_DEFENSE_TEMPLATE` with six formations. `_generate_defense()` varies it with
four team inputs: rushing efficiency, passing efficiency, interception rate and
sack rate. Fractional efficiency shifts are distributed deterministically over
dice subrows. Interceptions use fixed ordered low-probability positions; pressure
uses only the 4% and 8% sack-rate thresholds. Empirical offense generation still
uses this defense generator.

There are meaningful numeric differences. Weighted numeric-cell means span
approximately 2.31 yards for running and 1.45 for passing in 1983, and 2.36 / 1.30
in 2024. The run portions have 22 distinct patterns among 28 teams and 20 among
32; each team's full passing portion is distinct. These figures are raw chart
effects, not resolved yards allowed. Offense, priority rules and secondary charts
also contribute to engine results.

The existing [generator note](statistical-chart-generator.md) already documents
the limited efficiency/disruption dimensions. Richer defensive identities would
require additional modeling inputs and validation through the current engine;
rearranging the display cannot supply that information.

## Scope and verification

The delegated audit examined 60 public-provenance generation manifests and
1,800 defense-chart instances: 30 variants of each historical season. Every
individual set had 28/28 or 32/32 distinct defenses. The table above describes
the two promoted sets; the remaining 58 are experimental outputs, including
`1983-pbp-joint-final` and 57 ignored audit sets. Imported private historical
charts were excluded. The public 2026 fixtures were checked separately.

Comparisons flattened columns 1–9 over the 30 formation/subrows, counted unique
tuples and compared every team pair. Probability-weighted comparisons used
`defense_subrow_weights()` from
[`play_resolver.py`](../../paydirt/play_resolver.py): 12, 11, 9, 3, 1. The parent
agent independently reproduced uniqueness, pairwise/nearest medians and closest
pairs for both promoted sets and the public preview.

Five existing synthetic generator regressions passed:

```bash
python3 -m pytest tests/test_chart_generator.py -q -o addopts= --tb=short \
  -k 'generated_defense_keeps_tactical_structure or generated_defense_preserves_close_efficiency_differences or generated_charts_depend_on_rates_not_season_length or defensive_interception_strength_uses_distributed_low_mass_rows or defensive_interception_threshold_has_no_large_call_specific_jump'
```

No generator, chart data or test expectations changed for this investigation.
No season replay or AI play-selection audit ran. Uniqueness does not establish
historical fit. [DATA-004](issues/DATA/DATA-004.md) remains closed: its original
duplicate-chart defect has not recurred. The findings provide no new play-level
closure evidence for other resolved tickets, including DATA-011's retained
calibration caveat, and no evidence of DATA-012's concentrated interception
regression.

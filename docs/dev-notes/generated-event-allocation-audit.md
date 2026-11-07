# Generated event allocation audit

Developer investigation and release-gate component, 2026-11-05. This uses only
synthetic statistics; it changes no existing generator, engine or team data.
The audit detects probability-allocation errors and unintended result replacement.
It does not certify historical accuracy or formation tradeoffs after engine rules.

## Confirmed final-output discrepancy

`_nearest_roll_mass()` rounds the target probability to an integer physical mass
before choosing the closest attainable subset. With gaps in the remaining row
masses, that preliminary rounding can select a subset farther from the requested
probability than another available subset.

This synthetic empirical column reproduces the discrepancy:

```python
from paydirt.chart_generator import _empirical_column

outcomes = (
    ["BLACK"] * 300 + ["QT"] * 50 + ["INT 5"] * 5 + ["4"] * 645
)
column = _empirical_column(outcomes, seed=8306)
assert not any(cell.startswith("INT") for cell in column.values())
```

After earlier families are allocated, the smallest remaining row has probability
2/216. The interception target is 5/1000, or 1.08 physical units. The selector
first rounds that to one unit, then resolves the equal-distance tie between zero
and two units in favor of zero. Relative to the original target, however, two
units are closer: absolute error 0.92 rather than 1.08 units. The resulting chart
omits the requested 0.5% interception event; the closest available allocation is
0.926%. The same case reproduces at all three audit seeds because family mass
allocation is deterministic.

This is a small finite-row fidelity defect, distinct from Bowl Bound's reported
larger allocation and tactical issues. It does not show that the promoted teams
have identical defenses or that their resolved turnover rates are zero. No
generator correction or regeneration is included here.

## Gate implementation and controls

[`chart_allocation_gate.py`](../../paydirt/chart_allocation_gate.py) exports:

- `check_symbolic_allocation(before, after, target_rate, allocated_results,
  minimum_one=False)`: checks complete physical rows, existing-symbol
  preservation, allowed replacements, and the closest attainable final mass.
- `audit_allocations(seeds=(8306, 9241, 11713))`: exercises actual generator
  operations with controlled synthetic inputs and returns `passed`, `errors`,
  `checks` and `diagnostics` for the enclosing release gate.

The independent feasibility oracle enumerates attainable subset masses using
the engine's actual physical weights. It uses the original fractional target,
not the generator's selector as its own oracle, and has no arbitrary percentage
tolerance. A declared `minimum_one=True` policy is evaluated as a constrained
positive allocation. Intermediate empty selections repaired by that policy are
not incorrectly reported as final-output failures.

Coverage includes 243 mixed passing contexts, 108 running contexts, three
special-team contexts, mixed empirical families at two sample sizes, the sparse
interception case, complete synthetic generation with missing-annotation
defaults, and 282 defensive-rate contexts. The gate also verifies symbolic cells
after final numeric transformations. It does not interpret secondary B/QT
triggers as final outcomes; the separate tactical/engine audit owns those rules.

The complete audit performs **2,928 checks**. Its three current errors are the
sparse empirical case, once per seed. Other tested event allocations preserve
existing symbolic results and use nearest attainable masses. Varying defensive
interception rate changes only numeric/override/incomplete versus interception
cells; varying sack rate changes only numeric versus pressure cells. No unintended
interception-to-pressure or touchdown displacement was found in those sweeps.

Declared rare-event presence can have a larger percentage error than unconstrained
rounding: the largest local final allocation error in this expanded run is
0.426 percentage points for a required fumble mechanism. That is a documented
minimum-positive-row policy, not evidence of an unintended overwrite.

## Repeatable commands and test-first evidence

```sh
python3 scripts/audit_chart_allocations.py \
  --output .ai-audits/chart-generation/allocation-gate.json
python3 -m pytest tests/test_chart_allocation_gate.py tests/test_chart_generator.py \
  -q -o addopts= --tb=short
```

The first command currently exits **1**, correctly rejecting the unrepaired
nearest-mass discrepancy. The second passes **49 tests**: 11 gate tests and the
existing 38 generator regressions. Tests deliberately corrupt an allocator,
erase a symbol after allocation, replace a protected result, and choose a worse
attainable probability; each defect is rejected. A narrowly repaired selector
fixture is a passing control without changing production generation.

Tests were added first. The initial missing module caused collection failure;
an inert API scaffold then established six expected behavioral failures and two
passing controls. After the first implementation, the narrower audit passed.
Adding the final sparse empirical case exposed a previously untested defect:
its new gate regression failed while ten controls passed. The earlier expectation
that the current generator audit would pass was replaced explicitly because the
broader coverage disproved it. No generator regression was weakened or skipped.
Ruff passes for the new module, script and tests.

## Source-fidelity limits retained

The promoted public-provenance manifests distinguish observed annotations from
defaults. The 1983-generated set models missing offensive clock stops, punt fair
catches, field-goal blocks and special fumble annotations. The 2024 set retains
observed modern annotations but still models missing field-goal and punt snap
fumbles. Those estimates are not recovered historical events. Their provenance
and the existing held-out policy-dependent fit discrepancies remain documented
in [the completeness audit](generated-chart-completeness-audit.md).

These local allocation checks establish neither historical field-goal success,
resolved turnover totals, nor policy-independent statistical fit. Current-engine
cohort replay and source reconciliation are separate requirements of the larger
accuracy audit. No private imported historical chart was read by this component.

"""Describe absent source annotations without representing estimates as observations."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .chart_generator import _MISSING_OOB_RATES, _MISSING_SPECIAL_PROFILES


def source_feature_coverage(
    rows: Iterable[Mapping[str, Any]], field_goal_blocks: int = 0,
) -> dict[str, Any]:
    """Count source annotations and declare the explicit model fallbacks needed.

    Counts apply to the whole source season: an individual team's zero count
    does not establish that the underlying source omits a feature.
    """
    counts = {
        'offense_oob': 0, 'punt_fair_catch': 0, 'kickoff_out': 0,
        'field_goal_block': field_goal_blocks, 'field_goal_fumble': 0,
        'punt_fumble': 0, 'interception_return_fumble': 0,
    }
    for row in rows:
        result = str(row['result'])
        if row['unit'] == 'offense' and result.endswith(('*', '†')):
            counts['offense_oob'] += 1
        if row['unit'] == 'special_teams' and row['chart'] == 'punt' and result.endswith('*'):
            counts['punt_fair_catch'] += 1
        if row['unit'] == 'special_teams' and row['chart'] == 'kickoff' and result in {'OB', 'OUT'}:
            counts['kickoff_out'] += 1
        if row['unit'] == 'special_teams' and result.startswith('F'):
            key = {'field_goal': 'field_goal_fumble', 'punt': 'punt_fumble',
                   'interception_return': 'interception_return_fumble'}.get(str(row['chart']))
            if key:
                counts[key] += 1
    return {
        'observed_annotations': counts,
        'model_defaults': {
            'offense_oob': _MISSING_OOB_RATES,
            'punt_fair_catch': .25,
            'kickoff_out': .01,
            **{name: {'chart': chart, 'rate': rate, 'result': result}
               for name, (chart, rate, result) in _MISSING_SPECIAL_PROFILES.items()},
        },
        'modeled_missing_features': sorted(key for key, count in counts.items() if not count),
        'interpretation': 'Zero season-wide observations trigger modeling defaults, not inferred events.',
    }

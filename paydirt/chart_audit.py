"""Audit chart structure, engine symbols, physical ranges, and feature coverage.

Reports contain aggregate distributions rather than original cells. Historical
comparisons and source material should still be kept in ignored local storage.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .chart_generator import (
    _OFFENSE_EMPIRICAL_RESULT,
    _OFFENSE_NAMES,
    _SPECIAL_EMPIRICAL_RESULT,
    _SPECIAL_NAMES,
)
from .chart_loader import TeamChart, load_team_chart
from .play_resolver import chart_roll_weights, defense_subrow_weights
from .priority_chart import apply_priority_chart


def feature(cell: str) -> str:
    """Classify a result by its engine mechanism, grouping numeric variants."""
    value = cell.strip().upper()
    if value.startswith('(') and value.endswith(')'):
        return 'override_' + feature(value[1:-1])
    if value in {'*', '†'}:
        return 'marked'
    if re.fullmatch(r'[+-]?\d+[*†]?', value):
        return 'marked' if value.endswith(('*', '†')) else 'numeric'
    if value in {"BLACK", "INC"}:
        return "incomplete"
    for prefix, name in (
        ('OFF', 'penalty'), ('DEF', 'penalty'), ('PI', 'penalty'),
        ('INT', 'interception'), ('BK', 'blocked'), ('QT', 'pressure'),
        ('F', 'fumble'), ('B', 'breakaway'),
    ):
        if value.startswith(prefix):
            return name
    return {'TD': 'touchdown',
            'OB': 'kick_out', 'OUT': 'kick_out', 'TB': 'touchback'}.get(value, value)


def _combined_primary_rates(charts: list[TeamChart]) -> dict[str, dict[str, float]]:
    """Combine uniform league matchups through the actual priority rules.

    B and QT remain secondary triggers here; full engine replays separately
    measure their resolved outcomes, field position, coaching, and scoring.
    """
    offense_weights = chart_roll_weights()
    defense_weights = defense_subrow_weights()
    result = {}
    for column, name in enumerate(_OFFENSE_NAMES[:9], 1):
        offense: Counter = Counter()
        for chart in charts:
            for roll, weight in offense_weights.items():
                value = getattr(chart.offense, name).get(roll, '0')
                offense[value] += weight
        for formation in 'ABCDEF':
            defense: Counter = Counter()
            for chart in charts:
                for sub, weight in defense_weights.items():
                    defense[chart.defense.modifiers.get((formation, sub), {}).get(column, '0')] += weight
            totals: Counter = Counter()
            for off, off_mass in offense.items():
                for defensive, def_mass in defense.items():
                    combined = apply_priority_chart(off, defensive, is_passing_play=column >= 5)
                    if feature(off) == 'penalty' or feature(defensive) == 'penalty':
                        category = 'penalty'
                    elif combined.use_qt_column:
                        category = 'pressure'
                    elif combined.use_breakaway:
                        category = 'breakaway'
                    elif combined.is_incomplete:
                        category = 'incomplete'
                    elif combined.is_touchdown:
                        category = 'touchdown'
                    elif combined.is_turnover:
                        category = 'interception' if 'INT' in off + defensive else 'fumble'
                    elif feature(off) == 'fumble':
                        category = 'fumble'
                    else:
                        category = 'yards'
                    totals[category] += off_mass * def_mass
            total = sum(totals.values())
            if total:
                result[f'{name}/{formation}'] = {key: value / total for key, value in totals.items()}
    return result


def audit_season(path: Path, strict: bool = True) -> dict[str, Any]:
    """Validate a candidate season and measure weighted features in every column.

    Args:
        path: Season directory containing team folders.
        strict: Require complete generated rows. False permits legacy blanks,
            whose effective engine value is zero, when comparing reference sets.

    Returns:
        Errors, advisory coverage warnings, and aggregate feature probabilities.
    """
    weights = chart_roll_weights()
    defense_weights = defense_subrow_weights()
    legacy_blank_cells = 0
    loaded: list[TeamChart] = []
    errors: list[str] = []
    warnings: list[str] = []
    totals: dict[str, Counter] = defaultdict(Counter)
    ranges: dict[str, list[int]] = defaultdict(list)
    team_names = sorted(p.name for p in path.iterdir() if p.is_dir()
                        and (p / 'offense.csv').exists())
    if not team_names:
        errors.append('No teams found')
    for name in team_names:
        try:
            chart = load_team_chart(path / name)
        except (ValueError, KeyError, OSError, IndexError) as error:
            errors.append(f'{name}: cannot load charts: {error}')
            continue
        loaded.append(chart)
        for unit, names, pattern in (
            ('offense', _OFFENSE_NAMES, _OFFENSE_EMPIRICAL_RESULT),
            ('special_teams', _SPECIAL_NAMES, _SPECIAL_EMPIRICAL_RESULT),
        ):
            for column in names:
                cells = getattr(getattr(chart, unit), column)
                label = f'{unit}.{column}'
                missing = set(weights) - set(cells)
                legacy_blank_cells += len(missing)
                if missing and strict:
                    errors.append(f'{name} {label}: missing rows {sorted(missing)}')
                effective = {roll: cells.get(roll, '0') for roll in weights}
                effective.update(cells)
                for roll, value in effective.items():
                    validation_value = value if strict else re.sub(r"\s+([XY])$", r"\1", value)
                    if not pattern.fullmatch(validation_value) and (strict or value not in {'*', '†'}):
                        errors.append(f'{name} {label}: invalid result {value!r}')
                    if roll not in weights:
                        errors.append(f'{name} {label}: invalid roll {roll}')
                        continue
                    if unit == 'offense' and column in (*_OFFENSE_NAMES[:4], 'breakaway') and value == 'TD':
                        errors.append(f'{name} {label}: guaranteed run touchdown')
                    if unit == 'special_teams' and column in {'kickoff_return', 'punt_return'} and value == 'TD':
                        errors.append(f'{name} {label}: unconditional return touchdown')
                    totals[label][feature(value)] += weights[roll]
                    numeric = re.fullmatch(r'([+-]?\d+)[*†]?', value)
                    if numeric:
                        yards = int(numeric[1])
                        ranges[label].append(yards)
                        maximum = 109 if unit == 'special_teams' and column.endswith('return') else 99
                        if abs(yards) > maximum:
                            errors.append(f'{name} {label}: impossible yardage {yards}')
                        if unit == 'offense' and column in _OFFENSE_NAMES[:4] and yards > 18:
                            errors.append(f'{name} {label}: direct run {yards} exceeds 18')
        expected = {(formation, sub) for formation in 'ABCDEF' for sub in defense_weights}
        if strict and set(chart.defense.modifiers) != expected:
            errors.append(f'{name}: incomplete defense formation/sub-row coverage')
        for formation, sub in sorted(expected):
            cells = chart.defense.modifiers.get((formation, sub), {})
            legacy_blank_cells += len(set(range(1, 10)) - set(cells))
            if strict and set(cells) != set(range(1, 10)):
                errors.append(f'{name} defense {formation}/{sub}: missing play columns')
            for column in range(1, 10):
                cell = cells.get(column, '0')
                normalized = cell.strip('()')
                if normalized and not _OFFENSE_EMPIRICAL_RESULT.fullmatch(normalized):
                    errors.append(f'{name} defense {formation}/{sub}/{column}: invalid {cell!r}')
                totals[f'defense.{column}'][feature(cell)] += defense_weights.get(sub, 0)
        for column in _SPECIAL_NAMES:
            if not any(feature(value) == 'penalty'
                       for value in getattr(chart.special_teams, column).values()):
                warnings.append(f'{name} {column}: no penalty exposure')
        for label, cells in (
            ('offense clock stops', dict(enumerate(
                value for column in _OFFENSE_NAMES
                for value in getattr(chart.offense, column).values()
            ))),
            ('punt fair catches', chart.special_teams.punt),
        ):
            if not any(re.fullmatch(r'[+-]?\d+[*†]', value) for value in cells.values()):
                warnings.append(f'{name}: no {label}')
        if set(chart.special_teams.extra_point_no_good) - set(weights):
            errors.append(f'{name}: invalid extra-point miss roll')
        recovery_rolls = []
        for low, high in (chart.peripheral.fumble_recovered_range,
                          chart.peripheral.fumble_lost_range):
            rolls = set(range(low, high + 1)) if (low, high) != (0, 0) else set()
            if (low, high) != (0, 0) and (low > high or rolls - set(weights)):
                errors.append(f'{name}: invalid fumble recovery range {low}-{high}')
            recovery_rolls.append(rolls)
        retained, lost = recovery_rolls
        if retained & lost or retained | lost != set(weights):
            errors.append(f'{name}: fumble recovery ranges must partition all physical rolls')
        if chart.peripheral.year <= 0:
            errors.append(f'{name}: invalid season year')
    return {
        'legacy_blank_cells': legacy_blank_cells,
        'passed': not errors, 'team_count': len(team_names), 'teams': team_names,
        'errors': errors, 'warnings': warnings,
        'features': {label: {key: value / sum(counts.values())
                             for key, value in sorted(counts.items())}
                     for label, counts in sorted(totals.items())},
        'combined_primary_rates': _combined_primary_rates(loaded),
        'numeric_ranges': {label: [min(values), max(values)] for label, values in ranges.items()},
    }


def main(argv: list[str] | None = None) -> int:
    """Write a local candidate audit and optional reference feature comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season-dir', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_season(args.season_dir)
    if args.reference:
        reference = audit_season(args.reference, strict=False)
        result['reference'] = reference
        result['missing_reference_features'] = {
            label: sorted(set(features) - set(result['features'].get(label, {})))
            for label, features in reference['features'].items()
            if set(features) - set(result['features'].get(label, {}))
        }
        result['reference_team_mismatch'] = sorted(set(reference['teams']) ^ set(result['teams']))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(f"{result['team_count']} teams; {len(result['errors'])} errors; "
          f"{len(result['warnings'])} advisories; {args.output}")
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

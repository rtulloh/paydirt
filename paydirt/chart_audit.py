"""Audit chart structure, engine symbols, physical ranges, and feature coverage.

Reports contain aggregate distributions rather than original cells. Historical
comparisons and source material should still be kept in ignored local storage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import warnings as runtime_warnings
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

from .chart_generator import (
    _OFFENSE_EMPIRICAL_RESULT,
    _OFFENSE_NAMES,
    _SPECIAL_EMPIRICAL_RESULT,
    _SPECIAL_NAMES,
    supported_generated_cell,
)
from .chart_loader import TeamChart, load_team_chart
from .play_resolver import (
    _parse_column_value,
    _parse_qb_time_value,
    chart_roll_weights,
    defense_subrow_weights,
)
from .priority_chart import PriorityResult, ResultCategory, apply_priority_chart, categorize_result


def _decoder_cell_class(unit: str, column: str, token: str) -> str:
    """Identify accepted syntax at the actual consumer, including known fallbacks."""
    if token.strip().upper() == "F INC":
        return ("supported" if supported_generated_cell(unit, column, token) else "unsupported")
    if unit == "offense" and column in {"breakaway", "qb_time"}:
        parsed = _parse_qb_time_value(token) if column == "qb_time" else _parse_column_value(token)
        if parsed is None:
            return ("secondary_random_fallback" if not token or _OFFENSE_EMPIRICAL_RESULT.fullmatch(token)
                    else "unsupported")
        return "ignored_secondary_fumble" if column == "breakaway" and parsed.is_fumble else "supported"
    if not token:
        return "engine_default"
    if unit in {"offense", "defense"}:
        if not (_OFFENSE_EMPIRICAL_RESULT.fullmatch(token)
                or re.fullmatch(r"(?:\(-?\d+\)|\[-?\d+\]|\(TD\)|-?\d+(?:\.\d*)?\*?)", token)):
            return "unsupported"
        category, yards = categorize_result(token)
        if unit == "defense" and category in {ResultCategory.FUMBLE_PLUS, ResultCategory.FUMBLE_MINUS}:
            # The priority table has only bare defensive F; signed F silently
            # falls back to the offense instead of selecting a fumble.
            return "unsupported"
        if category == ResultCategory.WHITE_NUMBER and yards is None:
            return "unsupported"
        if re.fullmatch(r"-?\d+\.\d+\*?", token) and float(token.rstrip("*")) != yards:
            return "numeric_truncation"
        return "supported"
    if column == "extra_point":
        return "supported" if token in {"0", "1", "NG"} else "unsupported"
    fumble = r"F(?:\s*[+-]\s*\d+)?"
    numeric_penalty = r"(?:OFF|DEF)\s*\d+"
    if column == "kickoff":
        supported = (token.isdigit() or token == "OB" or token.upper() in {"OUT", "TB"}
                     or re.fullmatch(numeric_penalty + "X?", token, re.IGNORECASE))
    elif column == "punt":
        supported = (re.fullmatch(r"-?\d+[*†+]?|BK\s*[+-]?\s*\d+", token)
                     or re.fullmatch(f"{fumble}|{numeric_penalty}X?", token, re.IGNORECASE))
    elif column == "field_goal":
        if re.fullmatch(r"(?:OFF|DEF)\s*[SR][XY]?", token, re.IGNORECASE):
            return "penalty_placeholder"
        supported = supported_generated_cell("special_teams", column, token)
    else:
        if column in {"kickoff_return", "punt_return"} and re.fullmatch(
            r"DEF\s*\d+[XY]", token, re.IGNORECASE,
        ):
            # These columns follow a real kick, so even a retained fumble chain
            # starts a new series. The shared INT/fumble-advance column does not.
            return "new_series_penalty_modifier"
        if column == "interception_return" and re.fullmatch(r"DEF\s*\d+[XY]", token, re.IGNORECASE):
            return "preserved_series_penalty_modifier"
        supported = re.fullmatch(f"[+-]?\\d+[*†]?|TD|{fumble}|{numeric_penalty}", token, re.IGNORECASE)
    return "supported" if supported else "unsupported"


def audit_chart_decoder(team_dir: Path) -> dict[str, Any]:
    """Census raw normalized CSVs before a private reference comparison.

    This checks decoder coverage, not authored-game or historical accuracy.
    Known B/QT random fallbacks and legacy defaults are explicit limitations.
    Never publish reference-derived results; the maintained collector requires
    ignored local output and a declared freeze before reading reference bytes.
    """
    directory = Path(team_dir)
    errors: list[str] = []
    limitations: list[str] = []
    loader_warnings: list[str] = []
    hashes: dict[str, str] = {}
    columns: dict[str, dict] = {}
    raw: dict[str, dict[Any, list[str]]] = {}
    try:
        if directory.is_symlink():
            raise ValueError("Decoder inputs must use regular local directories/files")
        for filename, minimum, maximum in (("offense.csv", 12, 13), ("defense.csv", 12, 12), ("special.csv", 8, 8)):
            path = directory / filename
            if path.is_symlink():
                raise ValueError("Decoder inputs must use regular local directories/files")
            data = path.read_bytes()
            hashes[filename] = hashlib.sha256(data).hexdigest()
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.reader(stream))
            if not rows or not minimum <= len(rows[0]) <= maximum or rows[0][0].strip() != "#":
                errors.append(f"{filename}: missing or incomplete positional header")
            raw[filename] = {}
            for number, row in enumerate(rows[1:], 2):
                if not row or not any(value.strip() for value in row):
                    continue
                if row[0].strip().startswith("#"):
                    if row[0].strip() not in {"# Recovered", "# Lost"}:
                        limitations.append(f"{filename} line {number}: comment ignored by the chart loader")
                    continue
                try:
                    if len(row) > maximum and any(value.strip() for value in row[maximum:]):
                        raise ValueError("nonempty cells outside the consumed columns")
                    if filename == "defense.csv":
                        key = (row[1].strip(), int(row[2]))
                        if key[0] not in "ABCDEF" or len(key[0]) != 1 or key[1] not in defense_subrow_weights():
                            raise ValueError("invalid defensive formation/subrow")
                    else:
                        key = int(row[0])
                        if key not in chart_roll_weights():
                            raise ValueError("row is outside the physical dice domain")
                    if key in raw[filename]:
                        errors.append(f"{filename} line {number}: duplicate physical row {key}")
                    raw[filename][key] = row
                except (ValueError, IndexError) as error:
                    errors.append(f"{filename} line {number}: {error}")
            if not raw[filename]:
                errors.append(f"{filename}: no physical chart rows")
        with runtime_warnings.catch_warnings(record=True) as captured:
            runtime_warnings.simplefilter("always")
            chart = load_team_chart(str(directory))
        loader_warnings = [str(warning.message) for warning in captured]

        def measure(label: str, filename: str, column: int, cells: dict, weights: dict,
                    unit: str, name: str, formation: str | None = None) -> None:
            counts: Counter[str] = Counter()
            missing = blank = normalization = 0
            denominator = sum(weights.values())
            for roll, weight in weights.items():
                key = (formation, roll) if formation is not None else roll
                row = raw[filename].get(key)
                value = row[column].strip() if row is not None and len(row) > column else ""
                if row is None:
                    missing += weight
                elif not value:
                    blank += weight
                if name == "fumble_recovery":
                    retained = chart.peripheral.fumble_recovered_range
                    lost = chart.peripheral.fumble_lost_range
                    recovered = retained != (0, 0) and retained[0] <= roll <= retained[1]
                    fumbled = lost != (0, 0) and lost[0] <= roll <= lost[1]
                    status = "recovered" if recovered else "lost"
                    if recovered == fumbled or value.upper() not in {"", "R" if recovered else "L"}:
                        status = "unsupported"
                else:
                    effective = cells.get(roll, "")
                    if unit == "special_teams" and name != "extra_point" and effective != value:
                        normalization += weight
                        errors.append(f"{label} roll {roll}: loader normalization changes the raw token")
                    status = _decoder_cell_class(unit, name, effective if unit == "special_teams" and name != "extra_point" else value)
                counts[status] += weight
                if status in {"unsupported", "ignored_secondary_fumble", "numeric_truncation"}:
                    errors.append(f"{label} roll {roll}: {status}")
                elif status == "secondary_random_fallback":
                    limitations.append(f"{label} roll {roll}: core random fallback, not an authored known gain")
                elif status == "penalty_placeholder":
                    limitations.append(f"{label} roll {roll}: core uses a five-yard placeholder instead of the penalty table")
            if missing:
                limitations.append(f"{label}: missing physical rows use the core's column-specific default")
            if blank and name != "extra_point":
                limitations.append(f"{label}: blank cells use the core's column-specific default")
            columns[label] = {
                "physical_denominator": denominator,
                "exact_masses": {key: [Fraction(mass, denominator).numerator, Fraction(mass, denominator).denominator]
                                 for key, mass in sorted(counts.items())},
                "missing_row_probability": missing / denominator,
                "blank_cell_probability": blank / denominator,
                "normalization_probability": normalization / denominator,
            }

        for index, name in enumerate(_OFFENSE_NAMES, 1):
            measure(f"offense.{name}", "offense.csv", index, getattr(chart.offense, name), chart_roll_weights(), "offense", name)
        measure("offense.fumble_recovery", "offense.csv", 12, {}, chart_roll_weights(), "offense", "fumble_recovery")
        for formation in "ABCDEF":
            for column in range(1, 10):
                cells = {row: chart.defense.modifiers.get((formation, row), {}).get(column, "") for row in defense_subrow_weights()}
                measure(f"defense.{formation}.{column}", "defense.csv", column + 2, cells,
                        defense_subrow_weights(), "defense", str(column), formation)
        for index, name in enumerate(_SPECIAL_NAMES, 1):
            measure(f"special_teams.{name}", "special.csv", index, getattr(chart.special_teams, name),
                    chart_roll_weights(), "special_teams", name)
        measure("special_teams.extra_point", "special.csv", 7, {}, chart_roll_weights(), "special_teams", "extra_point")
    except (ValueError, KeyError, TypeError, OSError, IndexError, OverflowError, csv.Error) as error:
        errors.append(str(error))
    for filename, expected in hashes.items():
        try:
            if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != expected:
                errors.append(f"{filename}: input changed during decoder census")
        except OSError as error:
            errors.append(f"{filename}: input changed during decoder census: {error}")
    return {"passed": not errors, "release_certified": False, "fully_supported": not errors and not limitations,
            "errors": errors, "limitations": limitations, "loader_warnings": loader_warnings,
            "files": hashes, "columns": columns,
            "aliases": {"special_teams.fumble_return": "special_teams.interception_return"},
            "scope": "Raw normalized-CSV decoder census only; defaults/fallbacks do not prove authored-game "
                     "accuracy. Weighted/crossed stateful behavior, paired games, source fit and human review remain required."}


def feature(cell: str) -> str:
    """Classify a result by its engine mechanism, grouping numeric variants."""
    value = cell.strip().upper()
    if value == "F INC":
        return "retained_incompletion"
    if value.startswith('(') and value.endswith(')'):
        return 'override_' + feature(value[1:-1])
    if value in {'*', '†'}:
        return 'marked'
    if re.fullmatch(r'[+-]?\d+[*†]?', value):
        return 'marked' if value.endswith(('*', '†')) else 'numeric'
    if re.fullmatch(r"SACK\s+0\*?", value):
        return "sack"
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
                        category = ('interception' if combined.priority in
                                    (PriorityResult.INT, PriorityResult.D_INT) else 'fumble')
                    elif feature(off) == 'fumble':
                        category = 'fumble'
                    else:
                        category = 'yards'
                    totals[category] += off_mass * def_mass
            total = sum(totals.values())
            if total:
                result[f'{name}/{formation}'] = {key: value / total for key, value in totals.items()}
    return result


def _exact_team_mechanics(chart: TeamChart, opponents: list[TeamChart]) -> dict[str, Any]:
    """Condition exact physical mass on B/QT without inventing terminal gains.

    Opponents form a uniform cohort mixture, an exploratory chart diagnostic.
    It is distinct from the source-schedule measurement policy and fit targets.
    Identical printed values are grouped only after adding their physical mass.
    """
    weights = chart_roll_weights()

    def column_mass(cells: dict[int, str], default: str = "0") -> Counter[str]:
        counts: Counter[str] = Counter()
        for roll, mass in weights.items():
            counts[cells.get(roll, default)] += mass
        return counts

    plays = {}
    secondary_scale = 216 * 208  # LCM(16 QT fallback values, 26 B fallback values).
    denominator = 216 * 36 * len(opponents) * secondary_scale
    for column, name in enumerate(_OFFENSE_NAMES[:9], 1):
        offense = column_mass(getattr(chart.offense, name))
        for formation in "ABCDEF":
            defense: Counter[str] = Counter()
            for opponent in opponents:
                for row, mass in defense_subrow_weights().items():
                    defense[opponent.defense.modifiers.get((formation, row), {}).get(column, "0")] += mass
            outcomes: Counter[str] = Counter()
            joint: Counter[str] = Counter()
            triggers: Counter[str] = Counter()
            fallback_mass = 0

            def record(kind: str, mass: int, out_of_bounds: bool = False,
                       outcome_counts: Counter[str] = outcomes, joint_counts: Counter[str] = joint) -> None:
                outcome_counts[kind] += mass
                joint_counts[f"{kind}|oob={int(out_of_bounds)}"] += mass
            for raw, off_mass in offense.items():
                for modifier, def_mass in defense.items():
                    mass = off_mass * def_mass
                    combined = apply_priority_chart(raw, modifier, is_passing_play=column >= 5)
                    if feature(raw) == "penalty" or feature(modifier) == "penalty":
                        record("pending_penalty", mass * secondary_scale)
                    elif combined.use_qt_column or combined.use_breakaway:
                        triggers["qt" if combined.use_qt_column else "breakaway"] += mass * secondary_scale
                        secondary = chart.offense.qb_time if combined.use_qt_column else chart.offense.breakaway
                        for cell, secondary_mass in column_mass(secondary, default="").items():
                            parsed = (_parse_qb_time_value(cell) if combined.use_qt_column
                                      else _parse_column_value(cell))
                            if parsed is None:
                                # Match the real resolver's random fallback for
                                # nonnumeric secondary cells, including QT fouls.
                                low, high = (-5, 10) if combined.use_qt_column else (15, 40)
                                fallback_mass += mass * secondary_mass * 208
                                for yards in range(low, high + 1):
                                    kind = (f"{'sack' if yards < 0 else 'scramble'}:{yards}"
                                            if combined.use_qt_column else f"breakaway:{yards}")
                                    record(kind, mass * secondary_mass * (208 // (high - low + 1)))
                                continue
                            if parsed.is_fumble and combined.use_qt_column:
                                kind = f"pending_qt_fumble:{parsed.yards}"
                            elif combined.use_breakaway:
                                kind = f"breakaway:{parsed.yards}"
                            else:
                                kind = f"{'sack' if parsed.is_sack or parsed.yards < 0 else 'scramble'}:{parsed.yards}"
                            record(kind, mass * secondary_mass * 208, parsed.out_of_bounds and not parsed.is_fumble)
                    elif combined.is_turnover:
                        kind = ("pending_interception" if combined.priority in
                                (PriorityResult.INT, PriorityResult.D_INT) else "pending_fumble")
                        record(f"{kind}:{combined.final_yards}", mass * secondary_scale)
                    elif combined.is_touchdown:
                        record("pending_touchdown_distance", mass * secondary_scale)
                    elif combined.is_incomplete:
                        kind = "retained_fumble_incomplete" if combined.retained_fumble_incompletion else "incomplete"
                        record(f"{kind}:0", mass * secondary_scale)
                    else:
                        record(f"yards:{combined.final_yards}", mass * secondary_scale, combined.out_of_bounds)
            total = sum(outcomes.values())
            known: Counter[int] = Counter()
            for kind, mass in outcomes.items():
                if kind.split(":")[0] in {"yards", "breakaway", "scramble", "sack"}:
                    known[int(kind.split(":")[1])] += mass
            known_mass = sum(known.values())
            plays[f"{name}/{formation}"] = {
                "probabilities": {kind: mass / denominator for kind, mass in sorted(outcomes.items())},
                "exact_masses": {kind: [mass, denominator] for kind, mass in sorted(outcomes.items())},
                "exact_joint_masses": {kind: [mass, denominator] for kind, mass in sorted(joint.items())},
                "trigger_exact_masses": {kind: [triggers[kind], denominator] for kind in ("qt", "breakaway")},
                "secondary_fallback_exact_mass": [fallback_mass, denominator],
                "exact_total_mass": [Fraction(total, denominator).numerator,
                                     Fraction(total, denominator).denominator],
                "conditional_known_numeric_mean": (sum(yards * mass for yards, mass in known.items())
                                                   / known_mass if known_mass else None),
                "known_numeric_probability": known_mass / denominator,
                "secondary_fallback_probability": fallback_mass / denominator,
                "known_numeric_tail_20": sum(mass for yards, mass in known.items() if yards >= 20) / denominator,
                "known_numeric_tail_40": sum(mass for yards, mass in known.items() if yards >= 40) / denominator,
            }
    special = {}
    for name in (*_SPECIAL_NAMES, "fumble_return"):
        counts = column_mass(getattr(chart.special_teams, name))
        special[name] = {"probabilities": {cell: mass / 216 for cell, mass in sorted(counts.items())},
                         "exact_masses": {cell: [mass, 216] for cell, mass in sorted(counts.items())}}
        if name == "field_goal":
            # Raw numeric FG cells specify distance from the goal line, not
            # goalpost distance. The engine adds 17 yards for the snap/kick.
            special[name]["by_distance"] = {
                str(distance): sum(mass for cell, mass in counts.items()
                                   if re.fullmatch(r"\d+", cell) and int(cell) >= distance - 17) / 216
                for distance in range(18, 76)
            }
            special[name]["exact_by_distance"] = {
                str(distance): [sum(mass for cell, mass in counts.items()
                                    if re.fullmatch(r"\d+", cell) and int(cell) >= distance - 17), 216]
                for distance in range(18, 76)
            }
    retained = sum(mass for roll, mass in weights.items()
                   if chart.peripheral.fumble_recovered_range[0] <= roll
                   <= chart.peripheral.fumble_recovered_range[1])
    lost = sum(mass for roll, mass in weights.items()
               if chart.peripheral.fumble_lost_range[0] <= roll
               <= chart.peripheral.fumble_lost_range[1])
    return {
        "plays": plays, "special_teams": special,
        "physical_primary_combinations": 54 * 216 * 36 * len(opponents),
        "recovery": {"retained": retained / 216, "lost": lost / 216},
        "exact_recovery": {"retained": [retained, 216], "lost": [lost, 216]},
        "extra_point_exact_miss_mass": [sum(weights.get(roll, 0)
                                            for roll in chart.special_teams.extra_point_no_good), 216],
        "extra_point_miss_probability": sum(weights.get(roll, 0)
                                            for roll in chart.special_teams.extra_point_no_good) / 216,
        "interpretation": "Exact pre-state chart probabilities against a uniform cohort defense mixture. "
                          "Numeric means are conditional, not whole-play YPA. Penalty choice, recovery "
                          "advances, return clipping, touchdown distance and stateful scoring remain "
                          "explicitly pending. Special return columns are conditioned on a return lookup. "
                          "FG curves retain penalty/block/fumble mass as unresolved and precede re-kicks. "
                          "Unparseable B/QT cells use the core's uniform random fallback; its probability "
                          "is reported separately and is not historical evidence. "
                          "No independent historical route or distance accuracy is asserted.",
    }


def retained_incompletion_priority_deltas(charts: list[TeamChart]) -> dict[str, Any]:
    """Compare F INC with BLACK in the same cells, using exact cohort dice mass.

    This diagnostic holds every other cell fixed. It exposes the priority choice;
    it does not replace whole-engine stateful qualification or a previous candidate.
    """
    columns: dict[str, dict[str, Any]] = {}
    denominator = 216 * 36 * len(charts) ** 2

    def category(combined: Any, modifier: str) -> str:
        if feature(modifier) == "penalty":
            return "pending_penalty"
        if combined.retained_fumble_incompletion:
            return "retained_incompletion"
        if combined.use_qt_column:
            return "pressure"
        if combined.use_breakaway:
            return "breakaway"
        if combined.is_incomplete:
            return "incomplete"
        if combined.is_touchdown:
            return "touchdown"
        if combined.is_turnover:
            return ("interception" if combined.priority in
                    (PriorityResult.INT, PriorityResult.D_INT) else "pending_fumble")
        return "numeric"

    for column, name in enumerate(_OFFENSE_NAMES[4:9], 5):
        joint_mass = sum(
            weight for chart in charts for roll, weight in chart_roll_weights().items()
            if getattr(chart.offense, name).get(roll, "").strip().upper() == "F INC"
        )
        for formation in "ABCDEF":
            defense: Counter[str] = Counter()
            for chart in charts:
                for row, weight in defense_subrow_weights().items():
                    defense[chart.defense.modifiers.get((formation, row), {}).get(column, "0")] += weight
            actual: Counter[str] = Counter()
            counterfactual: Counter[str] = Counter()
            known_yard_delta = 0
            for modifier, weight in defense.items():
                mass = joint_mass * weight
                retained = apply_priority_chart("F INC", modifier, is_passing_play=True)
                black = apply_priority_chart("BLACK", modifier, is_passing_play=True)
                retained_kind, black_kind = category(retained, modifier), category(black, modifier)
                actual[retained_kind] += mass
                counterfactual[black_kind] += mass
                known_yard_delta += mass * (
                    (retained.final_yards if retained_kind == "numeric" else 0)
                    - (black.final_yards if black_kind == "numeric" else 0)
                )
            signed = {key: actual[key] - counterfactual[key]
                      for key in sorted(actual.keys() | counterfactual.keys())}
            columns[f"{name}/{formation}"] = {
                "physical_denominator": denominator,
                "joint_input_mass": joint_mass * 36 * len(charts),
                "actual_event_mass": dict(sorted(actual.items())),
                "black_counterfactual_event_mass": dict(sorted(counterfactual.items())),
                "signed_event_mass": signed,
                "known_numeric_yard_mass_delta": known_yard_delta,
            }
    return {
        "comparison": "Same cells changed from F INC to BLACK; all other inputs fixed",
        "opponent_mixture": "uniform complete cohort, before state and secondary procedures",
        "columns": columns,
        "limitation": "Returns, penalties, QT, touchdown distance and stateful terminal gains need engine replay",
    }


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
                    zero_sack = (unit == "offense" and column == "qb_time"
                                 and re.fullmatch(r"SACK\s+0\*?", validation_value, re.IGNORECASE))
                    joint = (validation_value.strip().upper() == "F INC"
                             and supported_generated_cell(unit, column, validation_value))
                    if not pattern.fullmatch(validation_value) and not zero_sack and not joint and (strict or value not in {'*', '†'}):
                        errors.append(f'{name} {label}: invalid result {value!r}')
                    if strict and not supported_generated_cell(unit, column, value):
                        errors.append(f"{name} {label}: unsupported generated symbol {value!r}")
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
    exact = {name: _exact_team_mechanics(chart, loaded)
             for name, chart in zip((Path(chart.team_dir).name for chart in loaded), loaded)}
    for name, evidence in exact.items():
        for call, values in evidence["plays"].items():
            if values["exact_total_mass"] != [1, 1]:
                errors.append(f"{name} {call}: exact probability mass does not reconcile")
            if "unsupported_secondary" in values["probabilities"]:
                errors.append(f"{name} {call}: unsupported secondary branch")
    return {
        'legacy_blank_cells': legacy_blank_cells,
        'passed': not errors, 'team_count': len(team_names), 'teams': team_names,
        'errors': errors, 'warnings': warnings,
        'features': {label: {key: value / sum(counts.values())
                             for key, value in sorted(counts.items())}
                     for label, counts in sorted(totals.items())},
        'combined_primary_rates': _combined_primary_rates(loaded),
        'exact_mechanics': exact,
        'retained_incompletion_priority_deltas': retained_incompletion_priority_deltas(loaded),
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

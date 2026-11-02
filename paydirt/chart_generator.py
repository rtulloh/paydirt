"""Generate statistically calibrated Paydirt team charts.

The original chart workbooks contain formatting and audit macros, but no formulas
that derive chart cells from season totals.  This module implements the part that
can be reproduced: map season rates and empirical distributions onto the 216
offensive dice combinations represented by chart rows 10 through 39.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Any

from .play_resolver import chart_roll_weights, defense_subrow_weights

_ROLL_WEIGHTS = chart_roll_weights()
_TOTAL_WEIGHT = sum(_ROLL_WEIGHTS.values())
_ROLLS = tuple(sorted(_ROLL_WEIGHTS))
_DEFENSE_SUBROW_WEIGHTS = defense_subrow_weights()
_PASS_COMPLETION_CALIBRATION = 0.02
_PASS_DEFENSE_INTERCEPTION_ALLOWANCE = 0.006
_PASS_PENALTY_RATE = 0.055
_PASS_PRESSURE_MULTIPLIER = 1.70
_PASS_YARDAGE_CALIBRATION = 1.28
_OFFENSE_NAMES = (
    "line_plunge",
    "off_tackle",
    "end_run",
    "draw",
    "screen",
    "short_pass",
    "medium_pass",
    "long_pass",
    "te_short_long",
    "breakaway",
    "qb_time",
)
_SPECIAL_NAMES = (
    "kickoff",
    "kickoff_return",
    "punt",
    "punt_return",
    "interception_return",
    "field_goal",
)
_OFFENSE_EMPIRICAL_RESULT = re.compile(
    r"^(?:[+-]?\d+[*†]?|INC|BLACK|B\*?|TD|QT\*?|F(?:\s*[+-]\s*\d+)?|"
    r"INT\s*-?\d+|PI\s*\d+|OFF\s*(?:\d+|S|R)|"
    r"DEF\s*(?:\d+|S|R)(?:X|Y)?|[+-]?(?:DS|X|T1|T2|T3))$",
    re.IGNORECASE,
)
_SPECIAL_EMPIRICAL_RESULT = re.compile(
    r"^(?:[+-]?\d+[*†]?|TD|F(?:\s*[+-]\s*\d+)?|"
    r"(?:OFF|DEF)\s*(?:\d+|S|R)(?:X|Y)?|OB|OUT|TB|BK\s*-?\s*\d+|NG)$",
    re.IGNORECASE,
)
_DEFENSE_TEMPLATE = {
    "A": (
        ("0", "0", "0", "0", "(4)", "-2", "-3", "-4", "-2"),
        ("-1", "0", "0", "1", "-1", "-3", "-4", "-6", "-3"),
        ("-1", "-1", "0", "0", "-2", "BLACK", "-3", "-7", "-4"),
        ("-2", "-1", "-1", "0", "-3", "-4", "BLACK", "-9", "-3"),
        ("-2", "-2", "-2", "-1", "-4", "INT 5", "-7", "INT 18", "QT"),
    ),
    "B": (
        ("(0)", "(1)", "-1", "3", "(9)", "1", "4", "8", "4"),
        ("(1)", "(0)", "-2", "2", "(8)", "-1", "3", "6", "3"),
        ("-3", "-3", "-3", "4", "(10)", "-2", "2", "5", "2"),
        ("-4", "-4", "-4", "2", "(7)", "BLACK", "-1", "(TD)", "1"),
        ("(-1)", "(-1)", "-2", "1", "(6)", "INT 5", "(TD)", "BLACK", "QT"),
    ),
    "C": (
        ("1", "1", "2", "-2", "(3)", "-3", "-3", "-4", "-2"),
        ("0", "1", "1", "-1", "(2)", "-4", "-5", "-6", "-3"),
        ("1", "0", "1", "-2", "(4)", "BLACK", "-4", "-7", "-4"),
        ("-1", "0", "0", "-3", "(3)", "-5", "BLACK", "-9", "-5"),
        ("-2", "-1", "-1", "-4", "(1)", "INT 5", "-7", "INT 18", "QT"),
    ),
    "D": (
        ("1", "1", "2", "1", "-1", "-3", "-4", "3", "-3"),
        ("1", "2", "2", "2", "-2", "BLACK", "BLACK", "5", "BLACK"),
        ("0", "1", "1", "1", "-3", "-4", "-5", "4", "-4"),
        ("0", "0", "1", "0", "BLACK", "INT 5", "-6", "6", "QT"),
        ("-1", "0", "0", "-1", "-4", "BLACK", "INT 12", "8", "BLACK"),
    ),
    "E": (
        ("1", "2", "2", "2", "2", "1", "-3", "BLACK", "-1"),
        ("2", "2", "3", "3", "3", "2", "-5", "-9", "1"),
        ("1", "1", "2", "2", "1", "-1", "BLACK", "QT", "BLACK"),
        ("0", "1", "1", "1", "0", "BLACK", "-7", "INT 18", "QT"),
        ("-1", "0", "0", "0", "-1", "INT 5", "INT 12", "BLACK", "-5"),
    ),
    "F": (
        ("4", "4", "5", "5", "(14)", "3", "4", "QT", "3"),
        ("-3", "-3", "-2", "3", "(10)", "-3", "QT", "-9", "-3"),
        ("-4", "-4", "-3", "-2", "(6)", "QT", "-6", "INT 18", "QT"),
        ("-5", "-5", "-4", "-4", "(TD)", "INT 5", "QT", "QT", "INT 8"),
        ("-6", "-6", "-5", "6", "(18)", "BLACK", "INT 12", "(TD)", "QT"),
    ),
}


@dataclass(frozen=True)
class StatLine:
    """A flexible counting-stat line used by chart generation."""

    attempts: int = 0
    yards: int = 0
    touchdowns: int = 0
    fumbles: int = 0
    fumbles_lost: int = 0
    out_of_bounds: int = 0
    completions: int = 0
    interceptions: int = 0
    sacks: int = 0
    sack_yards: int = 0
    made: int = 0
    long: int = 0
    blocked: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> StatLine:
        """Create a stat line, ignoring unknown source fields."""
        source = data or {}
        return cls(**{name: int(source.get(name, 0) or 0) for name in cls.__dataclass_fields__})

    @property
    def average(self) -> float:
        """Return yards per attempt, or zero when there were no attempts."""
        return self.yards / self.attempts if self.attempts else 0.0

    @property
    def completion_rate(self) -> float:
        """Return completions per pass attempt."""
        return self.completions / self.attempts if self.attempts else 0.0


@dataclass(frozen=True)
class UnitStats:
    """Rushing and passing statistics for one side of the ball."""

    rushing: StatLine = field(default_factory=StatLine)
    passing: StatLine = field(default_factory=StatLine)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> UnitStats:
        """Create unit statistics from a mapping."""
        source = data or {}
        return cls(
            rushing=StatLine.from_dict(source.get("rushing")),
            passing=StatLine.from_dict(source.get("passing")),
        )


@dataclass(frozen=True)
class FieldGoalDistanceStats:
    """Field-goal results for one statistical kick distance."""

    distance: int
    attempts: int
    made: int
    blocked: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FieldGoalDistanceStats:
        """Create one distance bucket and reject impossible counting totals."""
        result = cls(
            distance=int(data["distance"]),
            attempts=int(data.get("attempts", 0) or 0),
            made=int(data.get("made", 0) or 0),
            blocked=int(data.get("blocked", 0) or 0),
        )
        if result.distance <= 0:
            raise ValueError("Field-goal distance must be positive")
        if result.attempts < 0 or result.made < 0 or result.blocked < 0:
            raise ValueError("Field-goal counts cannot be negative")
        if result.made > result.attempts:
            raise ValueError("Field-goal makes cannot exceed attempts")
        return result


@dataclass(frozen=True)
class SpecialTeamsStats:
    """Statistics used by the six special-teams chart columns."""

    kickoff: StatLine = field(default_factory=StatLine)
    kickoff_return: StatLine = field(default_factory=StatLine)
    punt: StatLine = field(default_factory=StatLine)
    punt_return: StatLine = field(default_factory=StatLine)
    interception_return: StatLine = field(default_factory=StatLine)
    field_goal: StatLine = field(default_factory=StatLine)
    extra_point: StatLine = field(default_factory=StatLine)
    field_goal_by_distance: tuple[FieldGoalDistanceStats, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> SpecialTeamsStats:
        """Create special-teams statistics from a mapping."""
        source = data or {}
        stat_names = (
            "kickoff",
            "kickoff_return",
            "punt",
            "punt_return",
            "interception_return",
            "field_goal",
            "extra_point",
        )
        return cls(
            **{name: StatLine.from_dict(source.get(name)) for name in stat_names},
            field_goal_by_distance=tuple(
                FieldGoalDistanceStats.from_dict(bucket)
                for bucket in source.get("field_goal_by_distance", ())
            ),
        )


@dataclass(frozen=True)
class TeamSeasonStats:
    """Season totals accepted by the chart generator."""

    season: int
    team_name: str
    short_name: str
    offense: UnitStats
    defense: UnitStats
    special_teams: SpecialTeamsStats = field(default_factory=SpecialTeamsStats)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TeamSeasonStats:
        """Create normalized season statistics from JSON-compatible data."""
        return cls(
            season=int(data["season"]),
            team_name=str(data["team_name"]),
            short_name=str(data.get("short_name") or data["team_name"][:3].upper()),
            offense=UnitStats.from_dict(data.get("offense")),
            defense=UnitStats.from_dict(data.get("defense")),
            special_teams=SpecialTeamsStats.from_dict(data.get("special_teams")),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> TeamSeasonStats:
        """Load season statistics from a JSON file."""
        with Path(path).open(encoding="utf-8") as source:
            return cls.from_dict(json.load(source))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return asdict(self)


@dataclass(frozen=True)
class GeneratedCharts:
    """In-memory chart cells written by :func:`generate_team_charts`."""

    offense: dict[str, dict[int, str]]
    defense: dict[tuple[str, int], dict[int, str]]
    special_teams: dict[str, dict[int, str]]


@dataclass(frozen=True)
class EmpiricalPassCalibration:
    """Engine-level offsets applied to empirical pass chart generation."""

    completion_rate_adjustment: float = 0.0
    interception_rate_adjustment: float = 0.0
    pressure_rate_adjustment: float = 0.0
    resolved_yard_multiplier: float = 1.0

    def __post_init__(self) -> None:
        """Reject calibration values that cannot describe a probability model."""
        for name in (
            "completion_rate_adjustment",
            "interception_rate_adjustment",
            "pressure_rate_adjustment",
        ):
            if not -1.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be between -1 and 1")
        if self.resolved_yard_multiplier <= 0:
            raise ValueError("resolved_yard_multiplier must be positive")


@dataclass(frozen=True)
class EmpiricalChartData:
    """Classified full-season outcomes used instead of aggregate estimates.

    Each outcome is already normalized to a Paydirt chart result such as ``4``,
    ``BLACK``, ``F``, or ``INT 12``. Source-specific play-by-play parsing and
    subjective play classification deliberately happen before this boundary.
    """

    offense: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    special_teams: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Iterable[Mapping[str, Any]]) -> EmpiricalChartData:
        """Create empirical chart data from normalized row mappings.

        Args:
            rows: Mappings containing ``unit``, ``chart``, and ``result``.

        Returns:
            Outcomes grouped by chart column.

        Raises:
            ValueError: If a unit, chart name, or result is invalid.
        """
        grouped: dict[str, dict[str, list[str]]] = {
            "offense": {},
            "special_teams": {},
        }
        valid_names = {
            "offense": set(_OFFENSE_NAMES),
            "special_teams": set(_SPECIAL_NAMES),
        }
        for line_number, row in enumerate(rows, start=2):
            unit = str(row.get("unit", "")).strip().lower()
            chart = str(row.get("chart", "")).strip().lower()
            result = str(row.get("result", "")).strip()
            if unit not in grouped:
                raise ValueError(f"Unknown empirical unit {unit!r} on row {line_number}")
            if chart not in valid_names[unit]:
                raise ValueError(f"Unknown {unit} chart {chart!r} on row {line_number}")
            if not result:
                raise ValueError(f"Empty empirical result on row {line_number}")
            result_pattern = (
                _OFFENSE_EMPIRICAL_RESULT
                if unit == "offense"
                else _SPECIAL_EMPIRICAL_RESULT
            )
            if not result_pattern.fullmatch(result):
                raise ValueError(
                    f"Invalid empirical result {result!r} on row {line_number}"
                )
            grouped[unit].setdefault(chart, []).append(result)
        return cls(
            offense={name: tuple(values) for name, values in grouped["offense"].items()},
            special_teams={
                name: tuple(values) for name, values in grouped["special_teams"].items()
            },
        )

    @classmethod
    def from_csv(cls, path: str | Path) -> EmpiricalChartData:
        """Load normalized classified outcomes from a CSV file."""
        with Path(path).open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            required = {"unit", "chart", "result"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError("Empirical CSV must contain unit, chart, and result columns")
            return cls.from_rows(reader)


def _rate(numerator: int, denominator: int, default: float = 0.0) -> float:
    """Return a bounded-input ratio, using a caller-provided zero-denominator default."""
    return numerator / denominator if denominator else default


def _seed_for(seed: int, *parts: str) -> int:
    """Derive a stable independent random seed for one team and chart column."""
    text = "\0".join((str(seed), *parts)).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "big")


def _nearest_roll_mass(target_rate: float, candidates: Sequence[int]) -> set[int]:
    """Choose chart rows whose combined dice mass is nearest the target rate."""
    target = round(max(0.0, min(1.0, target_rate)) * _TOTAL_WEIGHT)
    subsets: dict[int, tuple[int, ...]] = {0: ()}
    for roll in candidates:
        weight = _ROLL_WEIGHTS[roll]
        for mass, selected in tuple(subsets.items()):
            combined = mass + weight
            if combined <= _TOTAL_WEIGHT and combined not in subsets:
                subsets[combined] = (*selected, roll)
    best_mass = min(subsets, key=lambda mass: (abs(mass - target), mass))
    return set(subsets[best_mass])


def _adjust_numeric_mean(column: dict[int, str], target: float, minimum: int) -> None:
    """Move numeric cells by single yards until their weighted mean approaches a target."""
    numeric: list[tuple[int, int]] = []
    for roll, cell in column.items():
        match = re.fullmatch(r"([+-]?\d+)\*?", cell)
        if match:
            numeric.append((roll, int(match.group(1))))
    if not numeric:
        return
    denominator = sum(_ROLL_WEIGHTS[roll] for roll, _ in numeric)
    target_sum = round(target * denominator)
    current_sum = sum(_ROLL_WEIGHTS[roll] * value for roll, value in numeric)
    delta = target_sum - current_sum
    ordered = sorted(numeric, key=lambda item: (_ROLL_WEIGHTS[item[0]], item[0]))
    for _ in range(1000):
        if delta == 0:
            break
        best: tuple[int, int, int] | None = None
        for roll, value in ordered:
            step = 1 if delta > 0 else -1
            if value + step < minimum:
                continue
            change = _ROLL_WEIGHTS[roll] * step
            score = abs(delta - change)
            if best is None or score < best[0]:
                best = (score, roll, value)
        if best is None or best[0] >= abs(delta):
            break
        _, roll, value = best
        step = 1 if delta > 0 else -1
        suffix = "*" if column[roll].endswith("*") else ""
        column[roll] = f"{value + step}{suffix}"
        delta -= _ROLL_WEIGHTS[roll] * step
        ordered = [(r, value + step if r == roll else v) for r, v in ordered]


def _numeric_column(
    mean: float,
    spread: float,
    rng: random.Random,
    minimum: int = -20,
) -> dict[int, str]:
    """Create a shuffled normal-like numeric distribution over all chart rolls."""
    order = list(_ROLLS)
    rng.shuffle(order)
    normal = NormalDist()
    column: dict[int, str] = {}
    for rank, roll in enumerate(order):
        quantile = (rank + 0.5) / len(order)
        value = max(minimum, round(mean + spread * normal.inv_cdf(quantile)))
        column[roll] = str(value)
    _adjust_numeric_mean(column, mean, minimum)
    return column


def _replace_rate(
    column: dict[int, str],
    rate: float,
    value_factory: str | Sequence[str],
    rng: random.Random,
) -> None:
    """Replace weighted chart rows to approximate the requested symbolic outcome rate."""
    available = [
        roll
        for roll, cell in column.items()
        if re.fullmatch(r"[+-]?\d+\*?", cell)
    ]
    rng.shuffle(available)
    chosen = _nearest_roll_mass(rate, available)
    values = [value_factory] if isinstance(value_factory, str) else list(value_factory)
    for index, roll in enumerate(sorted(chosen)):
        column[roll] = values[index % len(values)]


def _mark_numeric_out_of_bounds(
    column: dict[int, str],
    rate: float,
    resolved_play_mass: float,
    rng: random.Random,
) -> None:
    """Mark numeric cells so resolved plays reproduce a supplied clock-stop rate."""
    available = [
        roll
        for roll, cell in column.items()
        if re.fullmatch(r"[+-]?\d+", cell)
    ]
    rng.shuffle(available)
    chosen = _nearest_roll_mass(rate * resolved_play_mass, available)
    for roll in chosen:
        column[roll] = f"{column[roll]}*"



def _empirical_event_category(result: str) -> str:
    """Classify engine-level pass events separately from resolved outcomes."""
    normalized = result.strip().upper()
    if normalized in {"BLACK", "INC"}:
        return "incomplete"
    if normalized.startswith("INT "):
        return "interception"
    if normalized.startswith("QT"):
        return "pressure"
    if normalized.startswith(("OFF ", "DEF ", "PI ")):
        return "penalty"
    return "resolved"



def _scale_empirical_resolved_yards(result: str, multiplier: float) -> str:
    """Scale resolved numeric and fumble yards while preserving chart markers."""
    numeric = re.fullmatch(r"([+-]?\d+)([*†]?)", result.strip())
    if numeric:
        return f"{round(int(numeric.group(1)) * multiplier)}{numeric.group(2)}"
    fumble = re.fullmatch(
        r"F(?:\s*([+-])\s*(\d+))?", result.strip(), re.IGNORECASE
    )
    if fumble and fumble.group(2):
        value = int(fumble.group(2)) * (-1 if fumble.group(1) == "-" else 1)
        scaled = round(value * multiplier)
        if scaled == 0:
            return "F"
        return f"F {'+' if scaled > 0 else '-'} {abs(scaled)}"
    return result

def _calibrate_empirical_pass_events(
    outcomes: Sequence[str],
    baseline: Mapping[int, str],
    calibration: EmpiricalPassCalibration,
) -> tuple[str, ...]:
    """Apply engine-calibrated pass event rates to empirical resolved outcomes.

    Aggregate season statistics already encode completion, interception, sack,
    and penalty rates in the baseline column. Empirical data supplies the shape
    of resolved gains, touchdowns, fumbles, and out-of-bounds markers. Combining
    them prevents the average defense chart from being counted twice.
    """
    if not outcomes:
        return ()
    event_names = ("incomplete", "interception", "pressure", "penalty")
    baseline_sources: dict[str, list[str]] = {name: [] for name in (*event_names, "resolved")}
    baseline_mass: Counter[str] = Counter()
    for roll, result in baseline.items():
        category = _empirical_event_category(result)
        weight = _ROLL_WEIGHTS.get(roll, 0)
        baseline_mass[category] += weight
        baseline_sources[category].extend([result] * weight)

    empirical_sources: dict[str, list[str]] = {name: [] for name in (*event_names, "resolved")}
    for result in outcomes:
        empirical_sources[_empirical_event_category(result)].append(result)

    total = len(outcomes)
    rates = {
        name: baseline_mass[name] / _TOTAL_WEIGHT
        for name in event_names
    }
    rates["incomplete"] = max(
        0.0,
        rates["incomplete"] - calibration.completion_rate_adjustment,
    )
    rates["interception"] = max(
        0.0,
        rates["interception"] + calibration.interception_rate_adjustment,
    )
    rates["pressure"] = max(
        0.0,
        rates["pressure"] + calibration.pressure_rate_adjustment,
    )
    event_mass = sum(rates.values())
    if event_mass > 1.0:
        rates = {name: rate / event_mass for name, rate in rates.items()}
    exact = {name: rates[name] * total for name in event_names}
    counts = {name: int(value) for name, value in exact.items()}
    remaining_events = min(total, round(sum(exact.values()))) - sum(counts.values())
    order = sorted(
        event_names,
        key=lambda name: (-(exact[name] - counts[name]), name),
    )
    for name in order[:remaining_events]:
        counts[name] += 1

    calibrated: list[str] = []
    for name in event_names:
        sources = baseline_sources[name] or empirical_sources[name]
        if not sources:
            continue
        calibrated.extend(sources[index % len(sources)] for index in range(counts[name]))
    resolved_count = total - len(calibrated)
    resolved_sources = empirical_sources["resolved"] or baseline_sources["resolved"]
    if not resolved_sources:
        resolved_sources = ["0"]
    scaled_sources = [
        _scale_empirical_resolved_yards(
            result, calibration.resolved_yard_multiplier
        )
        for result in resolved_sources
    ]
    calibrated.extend(
        scaled_sources[index % len(scaled_sources)] for index in range(resolved_count)
    )
    return tuple(calibrated)

def _empirical_symbol_family(cell: str) -> str:
    """Group variants that share one empirical probability mass."""
    normalized = cell.upper()
    if normalized.startswith("F"):
        return "fumble"
    if normalized.startswith("INT "):
        return "interception"
    if normalized.startswith(("OFF ", "DEF ", "PI ")):
        return "penalty"
    numeric = re.fullmatch(r"[+-]?\d+([*†])", cell)
    if numeric:
        return f"marked_numeric_{numeric.group(1)}"
    return f"exact_{cell}"


def _assign_empirical_variants(
    column: dict[int, str],
    rolls: Sequence[int],
    values: Sequence[str],
    seed: int,
) -> None:
    """Assign family variants by their empirical quantiles over chosen dice mass."""
    if not rolls or not values:
        return
    ordered_values = sorted(values)
    ordered_rolls = list(rolls)
    random.Random(seed).shuffle(ordered_rolls)
    total_mass = sum(_ROLL_WEIGHTS[roll] for roll in ordered_rolls)
    cumulative = 0
    for roll in ordered_rolls:
        weight = _ROLL_WEIGHTS[roll]
        quantile = (cumulative + weight / 2) / total_mass
        index = min(len(ordered_values) - 1, int(quantile * len(ordered_values)))
        column[roll] = ordered_values[index]
        cumulative += weight


def _empirical_column(outcomes: Sequence[str], seed: int) -> dict[int, str]:
    """Quantize classified outcomes onto the 216 equally likely dice results."""
    if not outcomes:
        raise ValueError("An empirical chart column must contain at least one outcome")
    numeric_values: list[int] = []
    symbolic_families: dict[str, list[str]] = {}
    for outcome in outcomes:
        cell = str(outcome).strip()
        match = re.fullmatch(r"([+-]?\d+)([*†]?)", cell)
        if match and not match.group(2):
            numeric_values.append(int(match.group(1)))
        else:
            symbolic_families.setdefault(_empirical_symbol_family(cell), []).append(cell)

    available = set(_ROLLS)
    column: dict[int, str] = {}
    total_samples = len(outcomes)
    ordered_families = sorted(
        symbolic_families.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    for family, values in ordered_families:
        chosen = _nearest_roll_mass(len(values) / total_samples, tuple(available))
        _assign_empirical_variants(
            column,
            tuple(chosen),
            values,
            _seed_for(seed, family),
        )
        available.difference_update(chosen)

    if not available:
        return column
    if not numeric_values:
        fallback_values = max(symbolic_families.values(), key=len)
        fallback = Counter(fallback_values).most_common(1)[0][0]
        column.update({roll: fallback for roll in available})
        return column

    _assign_empirical_variants(
        column,
        tuple(available),
        tuple(str(value) for value in numeric_values),
        seed,
    )
    return column


def _run_column(
    mean: float,
    attempts: int,
    touchdowns: int,
    fumbles: int,
    out_of_bounds: int,
    rng: random.Random,
    style: str,
) -> dict[int, str]:
    """Generate one rushing column from team efficiency and event rates."""
    offsets = {"line": -0.10, "tackle": -0.10, "end": -0.85, "draw": -0.50}
    spreads = {"line": 3.2, "tackle": 3.8, "end": 5.0, "draw": 4.2}
    target = max(0.0, mean + offsets[style])
    column = _numeric_column(target, spreads[style], rng, minimum=-15)
    _replace_rate(column, min(0.06, _rate(fumbles, attempts)), ("F", "F + 2", "F - 1"), rng)
    explosive_rate = max(0.01, min(0.06, _rate(touchdowns, attempts) * 0.85))
    _replace_rate(column, explosive_rate, ("B", "B*"), rng)
    _replace_rate(column, _PASS_PENALTY_RATE, ("OFF 5", "OFF 10", "DEF 5"), rng)
    _adjust_numeric_mean(column, target, -15)
    _mark_numeric_out_of_bounds(
        column,
        _rate(out_of_bounds, attempts),
        1.0 - _PASS_PENALTY_RATE,
        rng,
    )
    return column


def _pass_pressure_rate(stats: StatLine) -> float:
    """Return offense-chart QT mass needed to reproduce supplied sack pressure."""
    dropbacks = stats.attempts + stats.sacks
    return min(0.18, _rate(stats.sacks, dropbacks) * _PASS_PRESSURE_MULTIPLIER)


def _pass_column(
    stats: StatLine,
    completion_delta: float,
    completed_yards: float,
    spread: float,
    rng: random.Random,
) -> dict[int, str]:
    """Generate one passing column with rates conditional on resolved attempts."""
    completion = max(
        0.12,
        min(
            0.88,
            stats.completion_rate
            + completion_delta
            + _PASS_COMPLETION_CALIBRATION,
        ),
    )
    interception = min(
        0.09,
        max(
            0.0,
            _rate(stats.interceptions, stats.attempts)
            - _PASS_DEFENSE_INTERCEPTION_ALLOWANCE,
        ),
    )
    pressure = _pass_pressure_rate(stats)
    attempt_mass = max(0.0, 1.0 - pressure - _PASS_PENALTY_RATE)
    completion = min(completion, 1.0 - interception)
    interception_mass = interception * attempt_mass
    touchdown_mass = min(
        completion, min(0.06, _rate(stats.touchdowns, stats.attempts))
    ) * attempt_mass
    incomplete_mass = max(0.0, 1.0 - completion - interception) * attempt_mass

    column = _numeric_column(completed_yards, spread, rng, minimum=-8)
    _replace_rate(
        column,
        interception_mass,
        ("INT 5", "INT 12", "INT 20"),
        rng,
    )
    _replace_rate(column, touchdown_mass, "TD", rng)
    _replace_rate(column, pressure, ("QT", "QT*"), rng)
    _replace_rate(
        column,
        _PASS_PENALTY_RATE,
        ("OFF 5", "OFF 10", "DEF 5X", "PI 12"),
        rng,
    )
    _replace_rate(column, incomplete_mass, "BLACK", rng)
    _adjust_numeric_mean(column, completed_yards, -8)
    _mark_numeric_out_of_bounds(
        column,
        _rate(stats.out_of_bounds, stats.attempts),
        attempt_mass,
        rng,
    )
    return column


def _generate_offense(stats: TeamSeasonStats, seed: int) -> dict[str, dict[int, str]]:
    """Generate all offense chart columns from normalized season statistics."""
    rushing = stats.offense.rushing
    passing = stats.offense.passing
    result: dict[str, dict[int, str]] = {}
    for name, style in (
        ("line_plunge", "line"),
        ("off_tackle", "tackle"),
        ("end_run", "end"),
        ("draw", "draw"),
    ):
        rng = random.Random(_seed_for(seed, stats.team_name, name))
        result[name] = _run_column(
            rushing.average,
            rushing.attempts,
            rushing.touchdowns,
            rushing.fumbles,
            rushing.out_of_bounds,
            rng,
            style,
        )

    yards_per_completion = passing.yards / passing.completions if passing.completions else 10.0
    pass_profiles = {
        "screen": (0.13, max(4.0, yards_per_completion * 0.63), 6.0),
        "short_pass": (0.08, max(5.0, yards_per_completion * 0.59), 6.0),
        "medium_pass": (-0.05, max(9.0, yards_per_completion * 1.15), 9.0),
        "long_pass": (-0.25, max(18.0, yards_per_completion * 2.75), 18.0),
        "te_short_long": (0.02, max(7.0, yards_per_completion * 0.97), 8.0),
    }
    pass_profiles = {
        name: (delta, mean * _PASS_YARDAGE_CALIBRATION, spread)
        for name, (delta, mean, spread) in pass_profiles.items()
    }
    for name, (delta, mean, spread) in pass_profiles.items():
        rng = random.Random(_seed_for(seed, stats.team_name, name))
        result[name] = _pass_column(passing, delta, mean, spread, rng)

    result["breakaway"] = _numeric_column(
        max(14.0, rushing.average * 4.45),
        10.0,
        random.Random(_seed_for(seed, stats.team_name, "breakaway")),
        minimum=4,
    )
    sack_average = _rate(passing.sack_yards, passing.sacks, 7.0)
    result["qb_time"] = _numeric_column(
        -max(2.0, sack_average * 0.45),
        7.0,
        random.Random(_seed_for(seed, stats.team_name, "qb_time")),
        minimum=-25,
    )
    pressure_rate = _pass_pressure_rate(passing)
    pass_fumble_rate = _rate(passing.fumbles, passing.attempts + passing.sacks)
    qt_fumble_rate = min(0.45, _rate(pass_fumble_rate, pressure_rate))
    _replace_rate(
        result["qb_time"],
        qt_fumble_rate,
        ("F", "F - 5"),
        random.Random(_seed_for(seed, stats.team_name, "qb_time_fumbles")),
    )
    return result


def _shift_defense_cell(cell: str, shift: int) -> str:
    """Shift a numeric defense modifier while preserving parenthesized notation."""
    match = re.fullmatch(r"(\()?([+-]?\d+)(\))?", cell)
    if not match:
        return cell
    value = int(match.group(2)) + shift
    if match.group(1):
        return f"({value})"
    return str(value)


def _nearest_defense_subrows(target_rate: float, candidates: Sequence[int]) -> set[int]:
    """Choose defense sub-rows whose dice mass best approximates a target rate."""
    available = tuple(sorted(candidates))
    total = sum(_DEFENSE_SUBROW_WEIGHTS[subrow] for subrow in available)
    target = max(0.0, min(1.0, target_rate)) * total
    best_rows: tuple[int, ...] = ()
    best_difference = abs(target)
    for mask in range(1, 1 << len(available)):
        rows = tuple(
            subrow for index, subrow in enumerate(available) if mask & (1 << index)
        )
        mass = sum(_DEFENSE_SUBROW_WEIGHTS[subrow] for subrow in rows)
        difference = abs(mass - target)
        if (difference, rows) < (best_difference, best_rows):
            best_rows = rows
            best_difference = difference
    return set(best_rows)


def _apply_defense_efficiency_shift(
    defense: dict[tuple[str, int], dict[int, str]],
    columns: range,
    raw_shift: float,
) -> None:
    """Apply a continuous efficiency shift through weighted defense dice rows."""
    whole_shift = int(raw_shift)
    fractional_shift = raw_shift - whole_shift
    fractional_step = 1 if fractional_shift > 0 else -1

    for formation in _DEFENSE_TEMPLATE:
        for subrow in _DEFENSE_SUBROW_WEIGHTS:
            row = defense[(formation, subrow)]
            for column in columns:
                row[column] = _shift_defense_cell(row[column], whole_shift)

        if fractional_shift == 0:
            continue
        for column in columns:
            numeric_subrows = [
                subrow
                for subrow in _DEFENSE_SUBROW_WEIGHTS
                if re.fullmatch(
                    r"(\()?([+-]?\d+)(\))?", defense[(formation, subrow)][column]
                )
            ]
            selected = _nearest_defense_subrows(abs(fractional_shift), numeric_subrows)
            for subrow in selected:
                row = defense[(formation, subrow)]
                row[column] = _shift_defense_cell(row[column], fractional_step)


def _generate_defense(stats: TeamSeasonStats) -> dict[tuple[str, int], dict[int, str]]:
    """Adjust the tactical defense template for team efficiency and disruption rates."""
    rushing = stats.defense.rushing
    passing = stats.defense.passing
    run_shift = (rushing.average - 4.1) * 1.5
    pass_shift = (passing.average - 7.2) * 0.8
    sack_rate = _rate(passing.sacks, passing.attempts + passing.sacks)
    interception_rate = _rate(passing.interceptions, passing.attempts)
    defense: dict[tuple[str, int], dict[int, str]] = {}
    for formation, rows in _DEFENSE_TEMPLATE.items():
        for sub, template_row in enumerate(rows, start=1):
            row = {column: cell for column, cell in enumerate(template_row, start=1)}
            defense[(formation, sub)] = row

    _apply_defense_efficiency_shift(defense, range(1, 5), run_shift)
    _apply_defense_efficiency_shift(defense, range(5, 10), pass_shift)

    if interception_rate >= 0.035:
        defense[("D", 2)][6] = "INT 5"
    elif interception_rate <= 0.015:
        defense[("C", 5)][6] = "BLACK"
    if sack_rate >= 0.08:
        defense[("D", 3)][8] = "QT"
    elif sack_rate <= 0.04:
        defense[("F", 2)][7] = str(4 + round(pass_shift))
    return defense


def _special_column(mean: float, spread: float, seed: int, minimum: int = 0) -> dict[int, str]:
    """Generate one deterministic numeric special-teams column."""
    return _numeric_column(mean, spread, random.Random(seed), minimum=minimum)


def _monotonic_field_goal_rates(
    buckets: Sequence[FieldGoalDistanceStats],
) -> list[tuple[int, float]]:
    """Pool distance buckets into a nonincreasing field-goal success curve."""
    grouped: dict[int, list[int]] = {}
    for bucket in buckets:
        totals = grouped.setdefault(bucket.distance, [0, 0])
        totals[0] += bucket.attempts
        totals[1] += bucket.made
    blocks: list[dict[str, Any]] = []
    for distance, (attempts, made) in sorted(grouped.items()):
        if attempts == 0:
            continue
        blocks.append(
            {
                "distances": [distance],
                "attempts": attempts,
                "made": made,
                "rate": made / attempts,
            }
        )
        while len(blocks) >= 2 and blocks[-2]["rate"] < blocks[-1]["rate"]:
            right = blocks.pop()
            left = blocks.pop()
            attempts = left["attempts"] + right["attempts"]
            made = left["made"] + right["made"]
            blocks.append(
                {
                    "distances": left["distances"] + right["distances"],
                    "attempts": attempts,
                    "made": made,
                    "rate": made / attempts,
                }
            )
    return [
        (distance, block["rate"])
        for block in blocks
        for distance in block["distances"]
    ]


def _field_goal_column(
    buckets: Sequence[FieldGoalDistanceStats], seed: int
) -> dict[int, str]:
    """Generate maximum-distance results from observed makes and attempts by distance."""
    rates = _monotonic_field_goal_rates(buckets)
    if not rates:
        raise ValueError("Field-goal distance data must contain at least one attempt")
    shortest_needed = max(0, rates[0][0] - 17)
    column = {roll: str(max(0, shortest_needed - 1)) for roll in _ROLLS}
    successful_rolls = set(_ROLLS)
    rng = random.Random(seed)
    for statistical_distance, success_rate in rates:
        candidates = list(successful_rolls)
        rng.shuffle(candidates)
        successful_rolls = _nearest_roll_mass(success_rate, candidates)
        chart_distance = max(0, statistical_distance - 17)
        for roll in successful_rolls:
            column[roll] = str(chart_distance)
    return column


def _generate_special(stats: TeamSeasonStats, seed: int) -> dict[str, dict[int, str]]:
    """Generate all special-teams columns from return, punt, and kicking statistics."""
    special = stats.special_teams
    result = {
        "kickoff": _special_column(
            special.kickoff.average or 60.0, 7.0, _seed_for(seed, stats.team_name, "kickoff"), 35
        ),
        "kickoff_return": _special_column(
            (special.kickoff_return.average or 20.0) * 1.10,
            9.0,
            _seed_for(seed, stats.team_name, "kickoff_return"),
            0,
        ),
        "punt": _special_column(
            special.punt.average or 40.0, 7.0, _seed_for(seed, stats.team_name, "punt"), 15
        ),
        "punt_return": _special_column(
            (special.punt_return.average or 8.0) * 1.18,
            9.0,
            _seed_for(seed, stats.team_name, "punt_return"),
            -5,
        ),
        "interception_return": _special_column(
            (special.interception_return.average or 8.0) * 1.45,
            12.0,
            _seed_for(seed, stats.team_name, "interception_return"),
            -10,
        ),
    }
    field_goal_seed = _seed_for(seed, stats.team_name, "field_goal")
    if special.field_goal_by_distance:
        result["field_goal"] = _field_goal_column(
            special.field_goal_by_distance, field_goal_seed
        )
    else:
        field_goal_mean = max(18.0, min(45.0, (special.field_goal.long or 45) * 0.58))
        result["field_goal"] = _special_column(field_goal_mean, 9.0, field_goal_seed, 5)
    if special.punt.blocked:
        _replace_rate(
            result["punt"],
            _rate(special.punt.blocked, special.punt.attempts),
            "BK -10",
            random.Random(_seed_for(seed, stats.team_name, "punt_block")),
        )
        _adjust_numeric_mean(result["punt"], special.punt.average or 40.0, 15)
    return result


def weighted_chart_mean(column: Mapping[int, str]) -> float:
    """Return the dice-weighted mean of simple numeric cells.

    Symbolic cells are excluded, matching the quantitative audit convention used
    by the historical workbook for conditional numeric yardage.
    """
    numerator = 0
    denominator = 0
    for roll, cell in column.items():
        match = re.fullmatch(r"([+-]?\d+)\*?", str(cell).strip())
        if not match:
            continue
        weight = _ROLL_WEIGHTS.get(int(roll), 0)
        numerator += int(match.group(1)) * weight
        denominator += weight
    return numerator / denominator if denominator else 0.0


def weighted_chart_rate(column: Mapping[int, str], result: str) -> float:
    """Return the dice-weighted probability of one exact chart result."""
    matching = sum(
        _ROLL_WEIGHTS.get(int(roll), 0)
        for roll, cell in column.items()
        if str(cell).strip() == result
    )
    return matching / _TOTAL_WEIGHT


def _fumble_ranges(stats: TeamSeasonStats) -> tuple[tuple[int, int], tuple[int, int]]:
    """Choose contiguous recovery and loss ranges nearest the supplied loss rate."""
    fumbles = stats.offense.rushing.fumbles + stats.offense.passing.fumbles
    lost = stats.offense.rushing.fumbles_lost + stats.offense.passing.fumbles_lost
    if fumbles <= 0:
        return (10, 39), (0, 0)
    target_recovery_mass = round((1.0 - _rate(lost, fumbles)) * _TOTAL_WEIGHT)
    candidates = [(0, 0, 0)]
    mass = 0
    for end in _ROLLS:
        mass += _ROLL_WEIGHTS[end]
        candidates.append((10, end, mass))
    start, end, _ = min(
        candidates,
        key=lambda candidate: (
            abs(candidate[2] - target_recovery_mass),
            -candidate[2],
            candidate[1],
        ),
    )
    recovered = (start, end)
    if recovered == (0, 0):
        return recovered, (10, 39)
    if recovered == (10, 39):
        return recovered, (0, 0)
    return recovered, (end + 1, 39)


def _write_offense(
    path: Path,
    offense: Mapping[str, Mapping[int, str]],
    recovered_range: tuple[int, int],
    lost_range: tuple[int, int],
) -> None:
    """Write offense columns and the calibrated fumble recovery ranges."""
    headers = (
        "#",
        "Line Plunge",
        "Off Tackle",
        "End Run",
        "Draw",
        "Screen",
        "Short",
        "Med",
        "Long",
        "T/E S/L",
        "B",
        "QT",
        "Fumble",
    )
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target)
        writer.writerow(headers)
        for roll in _ROLLS:
            writer.writerow(
                [
                    roll,
                    *(offense[name][roll] for name in _OFFENSE_NAMES),
                    (
                        "R"
                        if recovered_range != (0, 0)
                        and recovered_range[0] <= roll <= recovered_range[1]
                        else "L"
                    ),
                ]
            )
        writer.writerow(["# Recovered", f"{recovered_range[0]}-{recovered_range[1]}"])
        writer.writerow(["# Lost", f"{lost_range[0]}-{lost_range[1]}"])


def _write_defense(path: Path, defense: Mapping[tuple[str, int], Mapping[int, str]]) -> None:
    """Write the six defense formations and their five weighted sub-rows."""
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target)
        writer.writerow(("#", "Formation", "Sub", *range(1, 10)))
        for formation in "ABCDEF":
            for sub in range(1, 6):
                cells = defense[(formation, sub)]
                writer.writerow(
                    (
                        f"{formation}-{sub}",
                        formation,
                        sub,
                        *(cells.get(column, "") for column in range(1, 10)),
                    )
                )


def _write_special(
    path: Path,
    special: Mapping[str, Mapping[int, str]],
    extra_point: StatLine,
) -> None:
    """Write special-teams columns and quantize the extra-point miss rate."""
    misses = max(0, extra_point.attempts - extra_point.made)
    miss_rate = _rate(misses, extra_point.attempts)
    miss_rolls = _nearest_roll_mass(miss_rate, _ROLLS)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target)
        writer.writerow(
            (
                "#",
                "Kickoff",
                "Kickoff Return",
                "Punt",
                "Punt Return",
                "Int. Return",
                "Field Goal",
                "Extra Point",
            )
        )
        for roll in _ROLLS:
            writer.writerow(
                (
                    roll,
                    special["kickoff"][roll],
                    special["kickoff_return"][roll],
                    special["punt"][roll],
                    special["punt_return"][roll],
                    special["interception_return"][roll],
                    special["field_goal"][roll],
                    "NG" if roll in miss_rolls else "",
                )
            )


def _write_team_yaml(path: Path, stats: TeamSeasonStats) -> None:
    """Write minimal team metadata beside the generated chart CSV files."""
    team_name = stats.team_name.replace("\n", " ").replace("\r", " ")
    short_name = stats.short_name.replace("\n", " ").replace("\r", " ")
    path.write_text(
        f"team_name: {json.dumps(team_name)}\nshort_name: {json.dumps(short_name)}\nnickname: {json.dumps(team_name.split()[-1])}\n",
        encoding="utf-8",
    )


def generate_team_charts(
    stats: TeamSeasonStats,
    output_dir: str | Path,
    seed: int = 8306,
    empirical: EmpiricalChartData | None = None,
    calibrate_empirical_pass_events: bool = False,
    empirical_pass_calibration: EmpiricalPassCalibration | None = None,
) -> GeneratedCharts:
    """Generate and write offense, defense, and special-teams charts.

    Args:
        stats: Normalized full-season statistics.
        output_dir: Team directory that will receive the chart CSV files.
        seed: Stable seed used only to distribute outcomes among equivalent rows.
        empirical: Optional classified full-season outcomes. Supplied columns
            replace aggregate estimates; other columns keep their estimates.
        calibrate_empirical_pass_events: Preserve aggregate engine calibration
            for pass events while using empirical resolved-yard distributions.
        empirical_pass_calibration: Optional offsets found through engine replay.

    Returns:
        The generated chart cells.
    """
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    offense = _generate_offense(stats, seed)
    defense = _generate_defense(stats)
    special = _generate_special(stats, seed)
    if empirical is not None:
        for name, outcomes in empirical.offense.items():
            calibrated_outcomes = outcomes
            if calibrate_empirical_pass_events and name in {
                "screen",
                "short_pass",
                "medium_pass",
                "long_pass",
            }:
                calibrated_outcomes = _calibrate_empirical_pass_events(
                    outcomes,
                    offense[name],
                    empirical_pass_calibration or EmpiricalPassCalibration(),
                )
            offense[name] = _empirical_column(
                calibrated_outcomes,
                _seed_for(seed, stats.team_name, "empirical", name),
            )
        for name, outcomes in empirical.special_teams.items():
            special[name] = _empirical_column(
                outcomes, _seed_for(seed, stats.team_name, "empirical", name)
            )
    recovered_range, lost_range = _fumble_ranges(stats)
    _write_offense(destination / "offense.csv", offense, recovered_range, lost_range)
    _write_defense(destination / "defense.csv", defense)
    _write_special(destination / "special.csv", special, stats.special_teams.extra_point)
    _write_team_yaml(destination / "team.yaml", stats)
    return GeneratedCharts(offense=offense, defense=defense, special_teams=special)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the season-stat chart generator command line interface."""
    parser = argparse.ArgumentParser(
        description="Generate Paydirt charts from normalized full-season statistics."
    )
    parser.add_argument("stats", help="JSON file containing normalized team season totals")
    parser.add_argument(
        "--output",
        required=True,
        help="Destination team directory for offense.csv, defense.csv, and special.csv",
    )
    parser.add_argument(
        "--plays",
        help="Optional normalized full-season play outcomes CSV",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=8306,
        help="Stable result-placement seed (default: 8306)",
    )
    args = parser.parse_args(argv)
    stats = TeamSeasonStats.from_json(args.stats)
    empirical = EmpiricalChartData.from_csv(args.plays) if args.plays else None
    generate_team_charts(stats, args.output, seed=args.seed, empirical=empirical)
    print(f"Generated charts for {stats.team_name} in {Path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Evaluate engine calibration reports and propose bounded chart-generator updates."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class CalibrationProfile:
    """Generator controls that may be tuned from engine simulation evidence."""

    run_yard_multiplier: float = 1.0
    pass_completion_adjustment: float = 0.0
    pass_interception_adjustment: float = 0.0
    pass_pressure_adjustment: float = 0.0
    pass_yard_multiplier: float = 1.0

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> CalibrationProfile:
        """Build a validated profile from decoded JSON values.

        Args:
            values: Field names and numeric profile values.

        Returns:
            A validated immutable calibration profile.

        Raises:
            ValueError: If a field is unknown or a value is invalid.
        """
        fields = set(cls.__dataclass_fields__)
        unknown = sorted(set(values) - fields)
        if unknown:
            raise ValueError(f"Unknown calibration profile field: {unknown[0]}")
        numeric: dict[str, float] = {}
        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"Calibration profile field {name} must be numeric")
            numeric[name] = float(value)
        profile = cls(**numeric)
        profile.validate()
        return profile

    def validate(self) -> None:
        """Reject non-finite values and nonpositive yardage multipliers."""
        for name, value in asdict(self).items():
            if not math.isfinite(value):
                raise ValueError(f"Calibration profile field {name} must be finite")
        if self.run_yard_multiplier <= 0 or self.pass_yard_multiplier <= 0:
            raise ValueError("Yardage multipliers must be positive")

    def to_dict(self) -> dict[str, float]:
        """Return a JSON-serializable profile in stable field order."""
        return asdict(self)


def load_calibration_profile(path: Path | None) -> CalibrationProfile:
    """Load one JSON profile, or return defaults when no path is supplied.

    Args:
        path: Optional calibration profile path.

    Returns:
        The decoded and validated profile.
    """
    if path is None:
        return CalibrationProfile()
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load calibration profile {path}: {error}") from error
    if not isinstance(values, Mapping):
        raise TypeError("Calibration profile must be a JSON object")
    return CalibrationProfile.from_mapping(values)


def apply_profile_overrides(
    profile: CalibrationProfile,
    overrides: Mapping[str, float | None],
) -> CalibrationProfile:
    """Apply explicitly supplied command-line values over a base profile.

    Args:
        profile: Base profile loaded from JSON or defaults.
        overrides: Supported field names whose ``None`` values are ignored.

    Returns:
        A validated profile with explicit overrides applied.
    """
    unknown = sorted(set(overrides) - set(CalibrationProfile.__dataclass_fields__))
    if unknown:
        raise ValueError(f"Unknown calibration profile field: {unknown[0]}")
    values = {name: value for name, value in overrides.items() if value is not None}
    updated = replace(profile, **values)
    updated.validate()
    return updated


@dataclass(frozen=True)
class MetricTarget:
    """Expected league metric with an absolute tolerance and relative weight."""

    value: float
    tolerance: float
    weight: float = 1.0

    def __post_init__(self) -> None:
        """Validate numeric target configuration."""
        if not all(math.isfinite(value) for value in (self.value, self.tolerance, self.weight)):
            raise ValueError("Metric target values must be finite")
        if self.tolerance <= 0:
            raise ValueError("Metric tolerance must be positive")
        if self.weight <= 0:
            raise ValueError("Metric weight must be positive")


@dataclass(frozen=True)
class TuningBounds:
    """Allowed interval and coordinate-descent step for one profile field."""

    minimum: float
    maximum: float
    step: float

    def __post_init__(self) -> None:
        """Validate an ordered finite interval and positive step."""
        if not all(math.isfinite(value) for value in (self.minimum, self.maximum, self.step)):
            raise ValueError("Tuning bounds must be finite")
        if self.minimum > self.maximum:
            raise ValueError("Tuning minimum cannot exceed maximum")
        if self.step <= 0:
            raise ValueError("Tuning step must be positive")

    def move(self, value: float, direction: int) -> float:
        """Move one step in a signed direction without leaving the interval."""
        candidate = value + self.step * direction
        return min(self.maximum, max(self.minimum, candidate))


@dataclass(frozen=True)
class MetricAssessment:
    """Observed value and tolerance-scaled difference for one league metric."""

    observed: float
    target: float
    tolerance: float
    difference: float
    normalized_error: float
    within_tolerance: bool
    weight: float

    def to_dict(self) -> dict[str, float | bool]:
        """Return JSON-ready metric evidence."""
        return asdict(self)


@dataclass(frozen=True)
class CalibrationAssessment:
    """Complete quality assessment for one simulated candidate profile."""

    metrics: dict[str, MetricAssessment]
    loss: float
    within_tolerance: bool
    minimum_team_games: int

    def to_dict(self) -> dict[str, object]:
        """Return JSON-ready candidate assessment evidence."""
        return {
            "loss": self.loss,
            "within_tolerance": self.within_tolerance,
            "minimum_team_games": self.minimum_team_games,
            "metrics": {
                name: metric.to_dict() for name, metric in self.metrics.items()
            },
        }


@dataclass(frozen=True)
class ProfileProposal:
    """One auditable coordinate-descent update and its resulting profile."""

    metric: str
    parameter: str
    previous_value: float
    next_value: float
    profile: CalibrationProfile

    def to_dict(self) -> dict[str, object]:
        """Return JSON-ready proposal evidence."""
        return {
            "metric": self.metric,
            "parameter": self.parameter,
            "previous_value": self.previous_value,
            "next_value": self.next_value,
            "profile": self.profile.to_dict(),
        }


@dataclass(frozen=True)
class SamplePlan:
    """Recommended pilot, training, and held-out validation sample sizes."""

    games_per_team_per_season: int
    pilot_seasons: int
    training_seasons: int
    validation_seasons: int
    pilot_team_games: int
    training_team_games: int
    validation_team_games: int

    def to_dict(self) -> dict[str, int]:
        """Return JSON-ready sample-size guidance."""
        return asdict(self)


_CALIBRATION_RULES = (
    ("completion_rate", "pass_completion_adjustment"),
    ("interception_rate", "pass_interception_adjustment"),
    ("sack_rate", "pass_pressure_adjustment"),
    ("yards_per_pass_attempt", "pass_yard_multiplier"),
    ("rushing_yards_per_attempt", "run_yard_multiplier"),
)


def recommended_sample_plan(games_per_team_per_season: int) -> SamplePlan:
    """Return the standard 16/64/256 season calibration plan.

    Args:
        games_per_team_per_season: Regular-season games played by each team.

    Returns:
        Team-game totals for pilot, training, and validation phases.
    """
    if games_per_team_per_season < 1:
        raise ValueError("Games per team per season must be positive")
    pilot, training, validation = 16, 64, 256
    return SamplePlan(
        games_per_team_per_season=games_per_team_per_season,
        pilot_seasons=pilot,
        training_seasons=training,
        validation_seasons=validation,
        pilot_team_games=pilot * games_per_team_per_season,
        training_team_games=training * games_per_team_per_season,
        validation_team_games=validation * games_per_team_per_season,
    )


def assess_calibration_report(
    report: Mapping[str, object],
    targets: Mapping[str, MetricTarget],
    *,
    minimum_team_games: int,
) -> CalibrationAssessment:
    """Compare an engine observer report with configured league targets.

    Args:
        report: Engine calibration report containing ``league`` and ``teams``.
        targets: Ordered target metrics used for loss calculation.
        minimum_team_games: Required completed games for every included team.

    Returns:
        Tolerance-scaled evidence and aggregate weighted squared loss.

    Raises:
        ValueError: If report structure, sample size, or metrics are invalid.
    """
    if minimum_team_games < 1:
        raise ValueError("Minimum team games must be positive")
    league = report.get("league")
    teams = report.get("teams")
    if not isinstance(league, Mapping) or not isinstance(teams, Mapping) or not teams:
        raise ValueError("Calibration report must contain league metrics and team totals")
    for team, totals in sorted(teams.items(), key=lambda item: str(item[0])):
        if not isinstance(totals, Mapping):
            raise TypeError(f"Calibration totals for {team} must be an object")
        team_games = totals.get("team_games")
        if isinstance(team_games, bool) or not isinstance(team_games, (int, float)):
            raise TypeError(f"Calibration totals for {team} lack numeric team_games")
        if team_games < minimum_team_games:
            raise ValueError(
                f"Team {team} has {int(team_games)} games; {minimum_team_games} required"
            )

    metrics: dict[str, MetricAssessment] = {}
    loss = 0.0
    for name, target in targets.items():
        observed = league.get(name)
        if isinstance(observed, bool) or not isinstance(observed, (int, float)):
            raise TypeError(f"Calibration report lacks numeric league metric {name}")
        observed_value = float(observed)
        if not math.isfinite(observed_value):
            raise ValueError(f"Calibration metric {name} must be finite")
        difference = observed_value - target.value
        normalized = difference / target.tolerance
        metric = MetricAssessment(
            observed=observed_value,
            target=target.value,
            tolerance=target.tolerance,
            difference=difference,
            normalized_error=normalized,
            within_tolerance=abs(difference) <= target.tolerance,
            weight=target.weight,
        )
        metrics[name] = metric
        loss += target.weight * normalized * normalized
    return CalibrationAssessment(
        metrics=metrics,
        loss=loss,
        within_tolerance=all(metric.within_tolerance for metric in metrics.values()),
        minimum_team_games=minimum_team_games,
    )


def propose_next_profile(
    profile: CalibrationProfile,
    assessment: CalibrationAssessment,
    bounds: Mapping[str, TuningBounds],
) -> ProfileProposal | None:
    """Propose one bounded update in the documented calibration order.

    Args:
        profile: Current generator profile.
        assessment: Candidate metrics measured through the engine.
        bounds: Tunable profile fields with interval and step configuration.

    Returns:
        One profile change, or ``None`` when no configured move is possible.
    """
    for metric_name, parameter in _CALIBRATION_RULES:
        metric = assessment.metrics.get(metric_name)
        if metric is None or metric.within_tolerance:
            continue
        parameter_bounds = bounds.get(parameter)
        if parameter_bounds is None:
            continue
        previous = getattr(profile, parameter)
        direction = 1 if metric.difference < 0 else -1
        next_value = parameter_bounds.move(previous, direction)
        if next_value == previous:
            return None
        next_profile = replace(profile, **{parameter: next_value})
        next_profile.validate()
        return ProfileProposal(
            metric=metric_name,
            parameter=parameter,
            previous_value=previous,
            next_value=next_value,
            profile=next_profile,
        )
    return None


@dataclass(frozen=True)
class TuningRunConfig:
    """Commands, targets, bounds, and seeds for one reproducible tuning run."""

    games_per_team_per_season: int
    training_seed: int
    validation_seed: int
    max_iterations: int
    targets: dict[str, MetricTarget]
    bounds: dict[str, TuningBounds]
    generator_command: tuple[str, ...]
    training_command: tuple[str, ...]
    validation_command: tuple[str, ...]
    initial_profile: CalibrationProfile = CalibrationProfile()

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> TuningRunConfig:
        """Decode and validate a local JSON tuning configuration.

        Args:
            values: Decoded JSON object.

        Returns:
            A complete immutable tuning run configuration.
        """
        required = {
            "games_per_team_per_season",
            "training_seed",
            "validation_seed",
            "max_iterations",
            "targets",
            "bounds",
            "generator_command",
            "training_command",
            "validation_command",
        }
        optional = {"initial_profile"}
        missing = sorted(required - set(values))
        unknown = sorted(set(values) - required - optional)
        if missing:
            raise ValueError(f"Missing tuning configuration field: {missing[0]}")
        if unknown:
            raise ValueError(f"Unknown tuning configuration field: {unknown[0]}")

        targets_value = values["targets"]
        bounds_value = values["bounds"]
        if not isinstance(targets_value, Mapping) or not targets_value:
            raise ValueError("Tuning targets must be a nonempty object")
        if not isinstance(bounds_value, Mapping) or not bounds_value:
            raise ValueError("Tuning bounds must be a nonempty object")
        targets: dict[str, MetricTarget] = {}
        for name, target_value in targets_value.items():
            if not isinstance(target_value, Mapping):
                raise TypeError(f"Target {name} must be an object")
            try:
                targets[str(name)] = MetricTarget(
                    value=float(target_value["value"]),
                    tolerance=float(target_value["tolerance"]),
                    weight=float(target_value.get("weight", 1.0)),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid target {name}: {error}") from error
        bounds: dict[str, TuningBounds] = {}
        profile_fields = set(CalibrationProfile.__dataclass_fields__)
        for name, bound_value in bounds_value.items():
            if name not in profile_fields:
                raise ValueError(f"Unknown calibration profile field: {name}")
            if not isinstance(bound_value, Mapping):
                raise TypeError(f"Bounds for {name} must be an object")
            try:
                bounds[str(name)] = TuningBounds(
                    minimum=float(bound_value["minimum"]),
                    maximum=float(bound_value["maximum"]),
                    step=float(bound_value["step"]),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid bounds for {name}: {error}") from error

        profile_value = values.get("initial_profile", {})
        if not isinstance(profile_value, Mapping):
            raise TypeError("Initial profile must be an object")
        profile = CalibrationProfile.from_mapping(profile_value)
        for name, bound in bounds.items():
            current = getattr(profile, name)
            if current < bound.minimum or current > bound.maximum:
                raise ValueError(f"Initial profile field {name} is outside its bounds")

        return cls(
            games_per_team_per_season=_positive_int(
                values["games_per_team_per_season"], "games_per_team_per_season"
            ),
            training_seed=_integer(values["training_seed"], "training_seed"),
            validation_seed=_integer(values["validation_seed"], "validation_seed"),
            max_iterations=_positive_int(values["max_iterations"], "max_iterations"),
            targets=targets,
            bounds=bounds,
            generator_command=_command(values["generator_command"], "generator_command"),
            training_command=_command(values["training_command"], "training_command"),
            validation_command=_command(values["validation_command"], "validation_command"),
            initial_profile=profile,
        )


    def to_dict(self) -> dict[str, object]:
        """Return a complete JSON-ready audit snapshot of the tuning configuration."""
        return {
            "games_per_team_per_season": self.games_per_team_per_season,
            "training_seed": self.training_seed,
            "validation_seed": self.validation_seed,
            "max_iterations": self.max_iterations,
            "initial_profile": self.initial_profile.to_dict(),
            "targets": {
                name: asdict(target) for name, target in self.targets.items()
            },
            "bounds": {
                name: asdict(bound) for name, bound in self.bounds.items()
            },
            "generator_command": list(self.generator_command),
            "training_command": list(self.training_command),
            "validation_command": list(self.validation_command),
        }


def _integer(value: object, name: str) -> int:
    """Return one non-Boolean integer configuration value."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _positive_int(value: object, name: str) -> int:
    """Return one positive integer configuration value."""
    result = _integer(value, name)
    if result < 1:
        raise ValueError(f"{name} must be positive")
    return result


def _command(value: object, name: str) -> tuple[str, ...]:
    """Return a nonempty shell-free command array."""
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(part, str) or not part for part in value)
    ):
        raise ValueError(f"{name} must be a nonempty array of strings")
    return tuple(value)


def load_tuning_config(path: Path) -> TuningRunConfig:
    """Load a tuning run configuration from JSON."""
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load tuning configuration {path}: {error}") from error
    if not isinstance(values, Mapping):
        raise TypeError("Tuning configuration must be a JSON object")
    return TuningRunConfig.from_mapping(values)


def _format_command(command: tuple[str, ...], context: Mapping[str, object]) -> list[str]:
    """Expand documented placeholders in one command array without a shell."""
    try:
        return [part.format_map(context) for part in command]
    except KeyError as error:
        raise ValueError(f"Unknown tuning command placeholder: {error.args[0]}") from error


def _default_execute(command: list[str], log_path: Path) -> None:
    """Run one command, retain bounded process evidence, and fail on nonzero exit."""
    import subprocess

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    log_path.write_text(
        json.dumps(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if completed.returncode:
        raise RuntimeError(
            f"Tuning command failed with exit code {completed.returncode}; see {log_path}"
        )


def _read_report(path: Path) -> Mapping[str, object]:
    """Load one engine calibration report written by a configured runner."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load calibration report {path}: {error}") from error
    if not isinstance(report, Mapping):
        raise TypeError(f"Calibration report {path} must be a JSON object")
    return report


def run_tuning(
    config: TuningRunConfig,
    *,
    workspace: Path,
    training_seasons: int,
    validation_seasons: int,
    execute=None,
) -> dict[str, object]:
    """Generate, train, select, and validate chart profiles through external commands.

    Args:
        config: Validated tuning commands, targets, bounds, and seeds.
        workspace: New directory for candidate charts and audit reports.
        training_seasons: Seasons per candidate, normally 64.
        validation_seasons: Held-out seasons for the selected candidate, normally 256.
        execute: Optional test executor accepting ``(command, log_path)``.

    Returns:
        Complete JSON-ready tuning history and held-out validation result.
    """
    if training_seasons < 1 or validation_seasons < 1:
        raise ValueError("Training and validation seasons must be positive")
    workspace.mkdir(parents=True, exist_ok=True)
    if any(workspace.iterdir()):
        raise ValueError(f"Tuning workspace must be empty: {workspace}")
    candidates_dir = workspace / "candidates"
    candidates_dir.mkdir()
    command_executor = execute or _default_execute
    minimum_training_games = training_seasons * config.games_per_team_per_season
    minimum_validation_games = validation_seasons * config.games_per_team_per_season

    profile = config.initial_profile
    history: list[dict[str, object]] = []
    best: tuple[tuple[int, float], CalibrationProfile, Path] | None = None
    seen: set[tuple[float, ...]] = set()
    for iteration in range(config.max_iterations):
        fingerprint = tuple(profile.to_dict().values())
        if fingerprint in seen:
            break
        seen.add(fingerprint)
        candidate = candidates_dir / f"{iteration:03d}"
        candidate.mkdir()
        profile_path = candidate / "calibration-profile.json"
        profile_path.write_text(
            json.dumps(profile.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        report_path = candidate / "training-report.json"
        context = {
            "candidate": str(candidate),
            "iteration": iteration,
            "phase": "training",
            "profile": str(profile_path),
            "report": str(report_path),
            "seasons": training_seasons,
            "seed": config.training_seed,
            "workspace": str(workspace),
        }
        generator_command = _format_command(config.generator_command, context)
        training_command = _format_command(config.training_command, context)
        command_executor(generator_command, candidate / "generator-command.json")
        command_executor(training_command, candidate / "training-command.json")
        assessment = assess_calibration_report(
            _read_report(report_path),
            config.targets,
            minimum_team_games=minimum_training_games,
        )
        proposal = propose_next_profile(profile, assessment, config.bounds)
        history.append(
            {
                "iteration": iteration,
                "candidate": str(candidate),
                "profile": profile.to_dict(),
                "assessment": assessment.to_dict(),
                "proposal": proposal.to_dict() if proposal is not None else None,
            }
        )
        selection_key = (0 if assessment.within_tolerance else 1, assessment.loss)
        if best is None or selection_key < best[0]:
            best = (selection_key, profile, candidate)
        if assessment.within_tolerance or proposal is None:
            break
        profile = proposal.profile

    if best is None:
        raise RuntimeError("Tuning produced no candidate assessments")
    _, selected_profile, selected_candidate = best
    selected_path = workspace / "selected-profile.json"
    selected_path.write_text(
        json.dumps(selected_profile.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    validation_report_path = workspace / "validation-report.json"
    validation_context = {
        "candidate": str(selected_candidate),
        "iteration": "selected",
        "phase": "validation",
        "profile": str(selected_path),
        "report": str(validation_report_path),
        "seasons": validation_seasons,
        "seed": config.validation_seed,
        "workspace": str(workspace),
    }
    validation_command = _format_command(config.validation_command, validation_context)
    command_executor(validation_command, workspace / "validation-command.json")
    validation = assess_calibration_report(
        _read_report(validation_report_path),
        config.targets,
        minimum_team_games=minimum_validation_games,
    )
    result = {
        "configuration": config.to_dict(),
        "sample_plan": {
            "games_per_team_per_season": config.games_per_team_per_season,
            "training_seasons": training_seasons,
            "training_team_games": minimum_training_games,
            "validation_seasons": validation_seasons,
            "validation_team_games": minimum_validation_games,
        },
        "training_seed": config.training_seed,
        "validation_seed": config.validation_seed,
        "selected_candidate": str(selected_candidate),
        "selected_profile": selected_profile.to_dict(),
        "training_history": history,
        "validation": validation.to_dict(),
    }
    (workspace / "tuning-report.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result

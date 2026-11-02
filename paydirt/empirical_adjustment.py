"""Separate offensive and defensive effects in matched empirical play data.

A play result is jointly produced by an offense and a defense. This module fits
regularized additive effects across the league, defines the average defense as
zero, and translates each offense's observed outcomes to that reference defense.
It also exposes defense residuals in the aggregate rates consumed by the existing
defense chart generator.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from math import isfinite

from .chart_generator import StatLine, TeamSeasonStats, UnitStats
from .pfr_play_by_play import EmpiricalPlay

_RUN_CHARTS = frozenset(("line_plunge", "off_tackle", "end_run", "draw"))
_PASS_CHARTS = frozenset(("screen", "short_pass", "medium_pass", "long_pass"))
_NUMERIC_RESULT = re.compile(r"^([+-]?\d+)([*†]?)$")
_FUMBLE_RESULT = re.compile(r"^F(?:\s*([+-])\s*(\d+))?$", re.IGNORECASE)
_DETAIL_YARDS = re.compile(r"\bfor\s+(-?\d+)\s+yards?\b", re.IGNORECASE)
_PENALTY_PREFIXES = ("OFF ", "DEF ", "PI ")
_DEFAULT_RUN_AVERAGE = 4.1
_DEFAULT_PASS_AVERAGE = 7.2
_DEFAULT_COMPLETION_RATE = 0.57
_DEFAULT_INTERCEPTION_RATE = 0.03
_DEFAULT_SACK_RATE = 0.065


@dataclass(frozen=True)
class AdditiveEffects:
    """Regularized league baseline plus offense and defense deviations."""

    baseline: float
    offense_effects: Mapping[str, float]
    defense_effects: Mapping[str, float]

    def predict(self, offense: str, defense: str | None = None) -> float:
        """Predict an outcome for an offense against a defense or league average."""
        result = self.baseline + self.offense_effects.get(offense, 0.0)
        if defense is not None:
            result += self.defense_effects.get(defense, 0.0)
        return result


@dataclass(frozen=True)
class DefenseProfile:
    """Opponent adjusted rates used by the tactical defense chart generator."""

    rushing_yards_per_attempt: float
    passing_yards_per_attempt: float
    completion_rate: float
    interception_rate: float
    sack_rate: float


@dataclass(frozen=True)
class AdjustedEmpiricalSeason:
    """Adjusted offense samples and fitted defense residual profiles."""

    plays_by_team: Mapping[str, tuple[EmpiricalPlay, ...]]
    defense_profiles: Mapping[str, DefenseProfile]


def fit_additive_effects(
    observations: Iterable[tuple[str, str, float]],
    shrinkage: float = 24.0,
    iterations: int = 100,
) -> AdditiveEffects:
    """Fit ``value = baseline + offense + defense`` by ridge coordinate descent.

    The weighted mean of each effect family is constrained to zero. This makes
    the baseline the league-average matchup and makes offense-only predictions
    interpretable as performance against an average defense.

    Args:
        observations: Offense, defense, and numeric outcome triples.
        shrinkage: Ridge pseudo-count applied to every team effect.
        iterations: Maximum coordinate-descent passes.

    Returns:
        Fitted baseline and centered team effects.

    Raises:
        ValueError: If input is empty, invalid, or contains no matched teams.
    """
    rows = tuple((str(offense), str(defense), float(value)) for offense, defense, value in observations)
    if not rows:
        raise ValueError("Additive effect fitting requires at least one observation")
    if shrinkage < 0:
        raise ValueError("Additive effect shrinkage cannot be negative")
    if iterations <= 0:
        raise ValueError("Additive effect iterations must be positive")
    if any(not offense or not defense or not isfinite(value) for offense, defense, value in rows):
        raise ValueError("Additive effect observations require matched teams and finite values")

    offense_rows: dict[str, list[tuple[str, float]]] = defaultdict(list)
    defense_rows: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for offense, defense, value in rows:
        offense_rows[offense].append((defense, value))
        defense_rows[defense].append((offense, value))

    baseline = sum(value for _, _, value in rows) / len(rows)
    offense_effects = {team: 0.0 for team in offense_rows}
    defense_effects = {team: 0.0 for team in defense_rows}

    for _ in range(iterations):
        previous = (
            baseline,
            tuple(sorted(offense_effects.items())),
            tuple(sorted(defense_effects.items())),
        )
        for offense, matches in offense_rows.items():
            residual = sum(value - baseline - defense_effects[defense] for defense, value in matches)
            offense_effects[offense] = residual / (len(matches) + shrinkage)
        offense_mean = sum(
            offense_effects[team] * len(matches) for team, matches in offense_rows.items()
        ) / len(rows)
        baseline += offense_mean
        offense_effects = {
            team: effect - offense_mean for team, effect in offense_effects.items()
        }

        for defense, matches in defense_rows.items():
            residual = sum(value - baseline - offense_effects[offense] for offense, value in matches)
            defense_effects[defense] = residual / (len(matches) + shrinkage)
        defense_mean = sum(
            defense_effects[team] * len(matches) for team, matches in defense_rows.items()
        ) / len(rows)
        baseline += defense_mean
        defense_effects = {
            team: effect - defense_mean for team, effect in defense_effects.items()
        }

        current = (
            baseline,
            tuple(sorted(offense_effects.items())),
            tuple(sorted(defense_effects.items())),
        )
        maximum_change = max(
            abs(left - right)
            for left, right in zip(_flatten_fit(previous), _flatten_fit(current))
        )
        if maximum_change < 1e-10:
            break

    return AdditiveEffects(baseline, offense_effects, defense_effects)


def _flatten_fit(
    fit: tuple[float, tuple[tuple[str, float], ...], tuple[tuple[str, float], ...]],
) -> tuple[float, ...]:
    """Flatten one coordinate-descent state for a convergence comparison."""
    baseline, offense, defense = fit
    return (baseline, *(value for _, value in offense), *(value for _, value in defense))


def _category(result: str) -> str:
    """Map a Paydirt result symbol to one mutually exclusive outcome family."""
    normalized = result.strip().upper()
    if normalized.startswith(_PENALTY_PREFIXES):
        return "penalty"
    if _NUMERIC_RESULT.fullmatch(normalized):
        return "numeric"
    if normalized.startswith("F"):
        return "fumble"
    if normalized in {"TD", "B", "B*"}:
        return "touchdown"
    if normalized.startswith("INT "):
        return "interception"
    if normalized.startswith("QT"):
        return "pressure"
    if normalized in {"BLACK", "INC"}:
        return "incomplete"
    return "other"


def _result_yards(play: EmpiricalPlay) -> float | None:
    """Extract observed yards from a numeric, fumble, or touchdown result."""
    result = play.result.strip()
    numeric = _NUMERIC_RESULT.fullmatch(result)
    if numeric:
        return float(numeric.group(1))
    fumble = _FUMBLE_RESULT.fullmatch(result)
    if fumble:
        if not fumble.group(2):
            return 0.0
        value = int(fumble.group(2))
        return float(-value if fumble.group(1) == "-" else value)
    detail = _DETAIL_YARDS.search(play.detail)
    if detail:
        return float(detail.group(1))
    return None


def _format_adjusted_result(play: EmpiricalPlay, value: float) -> str:
    """Replace the yard component of a result while preserving its marker."""
    rounded = round(value)
    numeric = _NUMERIC_RESULT.fullmatch(play.result.strip())
    if numeric:
        return f"{rounded}{numeric.group(2)}"
    if _FUMBLE_RESULT.fullmatch(play.result.strip()):
        if rounded == 0:
            return "F"
        sign = "+" if rounded > 0 else "-"
        return f"F {sign} {abs(rounded)}"
    return play.result


def _allocate_counts(probabilities: Mapping[str, float], total: int) -> dict[str, int]:
    """Convert probabilities to deterministic integer counts by largest remainder."""
    if total <= 0:
        return {category: 0 for category in probabilities}
    bounded = {category: max(0.0, value) for category, value in probabilities.items()}
    mass = sum(bounded.values())
    if mass <= 0:
        first = min(bounded)
        return {category: total if category == first else 0 for category in bounded}
    scaled = {category: value * total / mass for category, value in bounded.items()}
    counts = {category: int(value) for category, value in scaled.items()}
    remaining = total - sum(counts.values())
    order = sorted(
        scaled,
        key=lambda category: (-(scaled[category] - counts[category]), category),
    )
    for category in order[:remaining]:
        counts[category] += 1
    return counts


def _adjust_chart(
    chart_plays: Sequence[EmpiricalPlay],
    shrinkage: float,
) -> dict[str, tuple[EmpiricalPlay, ...]]:
    """Build each offense's chart sample as if it faced an average defense."""
    teams = sorted({play.team for play in chart_plays})
    categories = sorted({_category(play.result) for play in chart_plays})
    category_models = {
        category: fit_additive_effects(
            (
                (
                    play.team,
                    play.opponent,
                    1.0 if _category(play.result) == category else 0.0,
                )
                for play in chart_plays
            ),
            shrinkage=shrinkage,
        )
        for category in categories
    }
    yard_plays = [play for play in chart_plays if _result_yards(play) is not None]
    yard_model = (
        fit_additive_effects(
            (
                (
                    play.team,
                    play.opponent,
                    _result_yards(play) or 0.0,
                )
                for play in yard_plays
            ),
            shrinkage=shrinkage,
        )
        if yard_plays
        else None
    )
    league_sources: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    team_sources: dict[str, dict[str, list[EmpiricalPlay]]] = defaultdict(lambda: defaultdict(list))
    team_counts: dict[str, int] = defaultdict(int)
    for play in chart_plays:
        category = _category(play.result)
        league_sources[category].append(play)
        team_sources[play.team][category].append(play)
        team_counts[play.team] += 1

    adjusted: dict[str, tuple[EmpiricalPlay, ...]] = {}
    for team in teams:
        counts = _allocate_counts(
            {category: model.predict(team) for category, model in category_models.items()},
            team_counts[team],
        )
        outcomes: list[EmpiricalPlay] = []
        for category in categories:
            sources = team_sources[team].get(category) or league_sources[category]
            for index in range(counts[category]):
                source = sources[index % len(sources)]
                result = source.result
                yards = _result_yards(source)
                if yard_model is not None and yards is not None:
                    result = _format_adjusted_result(
                        source,
                        yards - yard_model.defense_effects.get(source.opponent, 0.0),
                    )
                outcomes.append(replace(source, team=team, result=result))
        adjusted[team] = tuple(outcomes)
    return adjusted


def _metric_model(
    plays: Sequence[EmpiricalPlay],
    value_for_play: Callable[[EmpiricalPlay], float | None],
    shrinkage: float,
) -> AdditiveEffects | None:
    """Fit one defense-profile metric from eligible matched plays."""
    observations = []
    for play in plays:
        value = value_for_play(play)
        if value is not None:
            observations.append((play.team, play.opponent, float(value)))
    if not observations:
        return None
    return fit_additive_effects(observations, shrinkage=shrinkage)


def _defense_profiles(
    plays: Sequence[EmpiricalPlay],
    shrinkage: float,
) -> dict[str, DefenseProfile]:
    """Estimate defense rates after controlling for the opposing offenses."""
    run_plays = [
        play
        for play in plays
        if play.chart in _RUN_CHARTS and not play.result.upper().startswith(_PENALTY_PREFIXES)
    ]
    pass_plays = [
        play
        for play in plays
        if play.chart in _PASS_CHARTS and not play.result.upper().startswith(_PENALTY_PREFIXES)
    ]
    pass_attempts = [play for play in pass_plays if _category(play.result) != "pressure"]

    run_yards = _metric_model(run_plays, _result_yards, shrinkage)
    pass_yards = _metric_model(
        pass_attempts,
        lambda play: _result_yards(play) or 0.0,
        shrinkage,
    )
    completion = _metric_model(
        pass_attempts,
        lambda play: 1.0 if _category(play.result) in {"numeric", "fumble", "touchdown"} else 0.0,
        shrinkage,
    )
    interception = _metric_model(
        pass_attempts,
        lambda play: 1.0 if _category(play.result) == "interception" else 0.0,
        shrinkage,
    )
    sack = _metric_model(
        pass_plays,
        lambda play: 1.0 if _category(play.result) == "pressure" else 0.0,
        shrinkage,
    )
    defenses = sorted({play.opponent for play in plays if play.opponent})

    def prediction(model: AdditiveEffects | None, defense: str, default: float) -> float:
        if model is None:
            return default
        return model.baseline + model.defense_effects.get(defense, 0.0)

    return {
        defense: DefenseProfile(
            rushing_yards_per_attempt=max(0.0, prediction(run_yards, defense, _DEFAULT_RUN_AVERAGE)),
            passing_yards_per_attempt=max(0.0, prediction(pass_yards, defense, _DEFAULT_PASS_AVERAGE)),
            completion_rate=min(1.0, max(0.0, prediction(completion, defense, _DEFAULT_COMPLETION_RATE))),
            interception_rate=min(1.0, max(0.0, prediction(interception, defense, _DEFAULT_INTERCEPTION_RATE))),
            sack_rate=min(0.5, max(0.0, prediction(sack, defense, _DEFAULT_SACK_RATE))),
        )
        for defense in defenses
    }


def scale_empirical_run_yards(
    plays: Sequence[EmpiricalPlay],
    multiplier: float,
) -> tuple[EmpiricalPlay, ...]:
    """Scale resolved rushing yards for engine-level chart calibration.

    Numeric and fumble results retain their out-of-bounds or turnover markers.
    Penalties, touchdowns, passes, and special-teams outcomes remain unchanged.

    Args:
        plays: Opponent-adjusted empirical outcomes.
        multiplier: Positive factor applied to resolved run yardage.

    Returns:
        Calibrated copies of the supplied outcomes.

    Raises:
        ValueError: If the multiplier is not positive.
    """
    if multiplier <= 0:
        raise ValueError("Empirical run-yard multiplier must be positive")
    calibrated: list[EmpiricalPlay] = []
    for play in plays:
        yards = _result_yards(play)
        if (
            play.unit == "offense"
            and play.chart in _RUN_CHARTS
            and yards is not None
            and not play.result.upper().startswith(_PENALTY_PREFIXES)
        ):
            calibrated.append(
                replace(play, result=_format_adjusted_result(play, yards * multiplier))
            )
        else:
            calibrated.append(play)
    return tuple(calibrated)



def adjust_empirical_offense(
    plays: Sequence[EmpiricalPlay],
    shrinkage: float = 24.0,
) -> AdjustedEmpiricalSeason:
    """Translate matched offense outcomes to an average-defense reference.

    Args:
        plays: Classified plays carrying offense and opponent identifiers.
        shrinkage: Ridge pseudo-count controlling partial pooling.

    Returns:
        Per-team adjusted offense samples and fitted defense profiles.

    Raises:
        ValueError: If an offense outcome lacks its opposing defense.
    """
    offense_plays = tuple(play for play in plays if play.unit == "offense")
    if any(not play.opponent for play in offense_plays):
        raise ValueError("Opponent adjustment requires an opponent for every offense play")
    by_chart: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for play in offense_plays:
        by_chart[play.chart].append(play)
    by_team: dict[str, list[EmpiricalPlay]] = defaultdict(list)
    for chart in sorted(by_chart):
        for team, adjusted in _adjust_chart(by_chart[chart], shrinkage).items():
            by_team[team].extend(adjusted)
    return AdjustedEmpiricalSeason(
        plays_by_team={team: tuple(team_plays) for team, team_plays in by_team.items()},
        defense_profiles=_defense_profiles(offense_plays, shrinkage),
    )


def calibrate_defense_stats(
    stats: TeamSeasonStats,
    profile: DefenseProfile,
) -> TeamSeasonStats:
    """Replace raw defense rates with opponent adjusted league residual rates."""
    rushing = stats.defense.rushing
    passing = stats.defense.passing
    adjusted_rushing = replace(
        rushing,
        yards=round(profile.rushing_yards_per_attempt * rushing.attempts),
    )
    sacks = round(
        profile.sack_rate * passing.attempts / max(1e-9, 1.0 - profile.sack_rate)
    )
    sack_average = passing.sack_yards / passing.sacks if passing.sacks else 7.0
    adjusted_passing = replace(
        passing,
        yards=round(profile.passing_yards_per_attempt * passing.attempts),
        completions=round(profile.completion_rate * passing.attempts),
        interceptions=round(profile.interception_rate * passing.attempts),
        sacks=sacks,
        sack_yards=round(sack_average * sacks),
    )
    return replace(
        stats,
        defense=UnitStats(rushing=adjusted_rushing, passing=adjusted_passing),
    )

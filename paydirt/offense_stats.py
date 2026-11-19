"""Team offensive attempts and weighted efficiency from engine-owned counters."""
from typing import Any

from .play_resolver import PlayType, ResultType

OFFENSIVE_ATTEMPT_FIELDS = ("passing_attempts", "passing_completions", "passing_touchdowns", "rushing_attempts")
PASS_PLAYS = {PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS,
              PlayType.SCREEN, PlayType.TE_SHORT_LONG, PlayType.HAIL_MARY, PlayType.SPIKE_BALL}
RATE_INPUTS = {
    "completion_percentage": ("passing_completions", "passing_attempts"),
    "passing_yards_per_attempt": ("passing_yards", "passing_attempts"),
    "rushing_yards_per_attempt": ("rushing_yards", "rushing_attempts"),
    "passer_rating": ("passing_completions", "passing_attempts", "passing_yards", "passing_touchdowns", "interceptions_thrown"),
}


def validate_offensive_attempt_stats(value: Any, *, interceptions: int | None = None) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - set(OFFENSIVE_ATTEMPT_FIELDS):
        raise ValueError("Invalid offensive attempt statistics")
    if any(type(number) is not int or not 0 <= number <= 1_000_000_000 for number in value.values()):
        raise ValueError("Invalid offensive attempt counter")
    for key in ("passing_completions", "passing_touchdowns"):
        if key in value and "passing_attempts" in value and value[key] > value["passing_attempts"]:
            raise ValueError("Passing counter exceeds attempts")
    if all(key in value for key in ("passing_completions", "passing_touchdowns")) and value["passing_touchdowns"] > value["passing_completions"]:
        raise ValueError("Passing touchdowns exceed completions")
    if interceptions is not None and "passing_attempts" in value and interceptions + value.get("passing_completions", 0) > value["passing_attempts"]:
        raise ValueError("Completions and interceptions exceed passing attempts")
    return dict(value)


def record_offensive_attempt(stats: Any, play: PlayType, result: Any, *, touchdown: bool = False) -> None:
    counters = stats._offensive_attempt_stats
    if counters is None or result.replay_down or result.result_type in (ResultType.PASS_INTERFERENCE, ResultType.PENALTY_OFFENSE, ResultType.PENALTY_DEFENSE):
        return
    qt_fumble = result.result_type == ResultType.FUMBLE and result.qb_scramble_dice > 0
    sack = (result.result_type == ResultType.SACK
            or result.result_type == ResultType.QB_SCRAMBLE and result.yards < 0
            or qt_fumble and result.yards <= 0)
    if sack:
        return
    rush = play not in PASS_PLAYS or result.result_type == ResultType.QB_SCRAMBLE or qt_fumble
    if rush:
        keys = ("rushing_attempts",)
    else:
        complete = result.result_type in (ResultType.YARDS, ResultType.BREAKAWAY, ResultType.TOUCHDOWN, ResultType.FUMBLE)
        # A completed reception followed by a fumble can produce a team recovery
        # touchdown; that score is not a touchdown pass.
        passing_touchdown = complete and touchdown and result.result_type != ResultType.FUMBLE
        keys = ("passing_attempts",) + (("passing_completions",) if complete else ()) + (("passing_touchdowns",) if passing_touchdown else ())
    for key in keys:
        if key in counters:
            counters[key] += 1


def efficiency(rate: str, values: list[int]) -> float | None:
    """Calculate rates once from a common fully recorded subset, never game averages."""
    if rate == "passer_rating":
        completions, attempts, yards, touchdowns, interceptions = values
        if not attempts:
            return None
        components = ((completions / attempts - .3) * 5, (yards / attempts - 3) * .25,
                      touchdowns / attempts * 20, 2.375 - interceptions / attempts * 25)
        return sum(min(2.375, max(0, part)) for part in components) / 6 * 100
    numerator, attempts = values
    return numerator / attempts * (100 if rate == "completion_percentage" else 1) if attempts else None

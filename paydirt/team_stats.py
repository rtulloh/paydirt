"""Authoritative optional team counters, committed at retained-play boundaries."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from .offense_stats import PASS_PLAYS
from .play_resolver import PlayType, ResultType

MAX_FIELDS = frozenset(
    (
        "longest_pass",
        "longest_rush",
        "longest_reception",
        "longest_field_goal",
        "longest_kickoff_return",
        "longest_punt_return",
        "longest_punt",
    )
)
SIGNED_TEAM_FIELDS = frozenset(
    ("kickoff_return_yards", "punt_return_yards", "punt_return_yards_allowed", "punt_yards")
)
EXTENDED_TEAM_FIELDS = (
    "longest_pass",
    "longest_rush",
    "longest_reception",
    "rushing_touchdowns",
    "rushing_fumbles",
    "rushing_fumbles_lost",
    "receiving_fumbles",
    "receiving_fumbles_lost",
    "first_downs_rushing",
    "first_downs_passing",
    "first_downs_penalty",
    "third_down_attempts",
    "third_down_conversions",
    "fourth_down_attempts",
    "fourth_down_conversions",
    "extra_points_made",
    "extra_points_attempted",
    "longest_field_goal",
    "kickoff_returns",
    "kickoff_return_yards",
    "longest_kickoff_return",
    "kickoff_return_touchdowns",
    "punt_returns",
    "punt_return_yards",
    "longest_punt_return",
    "punt_return_touchdowns",
    "punt_return_fair_catches",
    "punts",
    "punt_yards",
    "longest_punt",
    "punts_blocked",
    "punts_inside_20",
    "punt_touchbacks",
    "punt_fair_catches",
    "punts_returned",
    "punt_return_yards_allowed",
)


def empty_extended_team_stats() -> dict[str, int]:
    return dict.fromkeys(EXTENDED_TEAM_FIELDS, 0)


def validate_extended_team_stats(value: Any) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - set(EXTENDED_TEAM_FIELDS):
        raise ValueError("Invalid extended team statistics")
    for key, number in value.items():
        if (
            type(number) is not int
            or not (-1_000_000_000 if key in SIGNED_TEAM_FIELDS else 0) <= number <= 1_000_000_000
        ):
            raise ValueError("Invalid extended team counter")
    for small, large in [
        ("third_down_conversions", "third_down_attempts"),
        ("fourth_down_conversions", "fourth_down_attempts"),
        ("extra_points_made", "extra_points_attempted"),
        ("rushing_fumbles_lost", "rushing_fumbles"),
        ("receiving_fumbles_lost", "receiving_fumbles"),
        ("punts_blocked", "punts"),
    ]:
        if small in value and large in value and value[small] > value[large]:
            raise ValueError("Extended team counters disagree")
    return dict(value)


def add(stats: Any, key: str, value: int = 1) -> None:
    counters = stats._extended_team_stats
    if counters is not None and key in counters:
        counters[key] = max(counters[key], value, 0) if key in MAX_FIELDS else counters[key] + value


def _stats(engine: Any, home: bool) -> Any:
    return engine.state.home_stats if home else engine.state.away_stats


def _commit(engine: Any, context: dict, outcome: Any) -> None:
    result = outcome.result
    if result.replay_down:
        return
    home = context["home"]
    stats = _stats(engine, home)
    penalty = context.get("enforced_foul", False) or result.result_type in (
        ResultType.PENALTY_OFFENSE,
        ResultType.PENALTY_DEFENSE,
        ResultType.PASS_INTERFERENCE,
    )
    first_downs = max(0, stats.first_downs - context["first_downs"])
    if penalty:
        add(stats, "first_downs_penalty", first_downs)
        return
    penalty_first_downs = min(first_downs, context.get("penalty_first_downs", 0))
    add(stats, "first_downs_penalty", penalty_first_downs)
    first_downs -= penalty_first_downs
    play = outcome.play_type
    if play not in (PlayType.PUNT, PlayType.KICKOFF, PlayType.FIELD_GOAL):
        qt = result.result_type == ResultType.FUMBLE and result.qb_scramble_dice > 0
        sack = (
            result.result_type == ResultType.SACK
            or result.result_type == ResultType.QB_SCRAMBLE
            and result.yards < 0
            or qt
            and result.yards <= 0
        )
        rush = play not in PASS_PLAYS or result.result_type == ResultType.QB_SCRAMBLE or qt
        complete = not rush and result.result_type in (
            ResultType.YARDS,
            ResultType.BREAKAWAY,
            ResultType.TOUCHDOWN,
            ResultType.FUMBLE,
        )
        yards = max(-context["ball"], min(result.yards, 100 - context["ball"]))
        actual_yards = (
            stats.rushing_yards - context.get("rushing_yards", stats.rushing_yards)
            if rush
            else stats.passing_yards - context.get("passing_yards", stats.passing_yards)
        )
        yards = (
            actual_yards if result.result_type == ResultType.TOUCHDOWN else min(yards, actual_yards)
        )
        if not sack:
            if rush:
                add(stats, "longest_rush", yards)
                if (
                    outcome.touchdown
                    and not outcome.turnover
                    and result.result_type != ResultType.FUMBLE
                ):
                    add(stats, "rushing_touchdowns")
            elif complete:
                add(stats, "longest_pass", yards)
                add(stats, "longest_reception", yards)
        if result.result_type == ResultType.FUMBLE and not sack:
            category = "rushing" if rush else "receiving"
            add(stats, category + "_fumbles")
            if not result.fumble_recovered:
                add(stats, category + "_fumbles_lost")
        first_down_rush = rush or (
            result.result_type == ResultType.FUMBLE
            and result.yards < context.get("yards_to_go", 1)
            and result.fumble_return_yards > 0
        )
        add(stats, "first_downs_rushing" if first_down_rush else "first_downs_passing", first_downs)
        if context["down"] in (3, 4):
            prefix = "third" if context["down"] == 3 else "fourth"
            add(stats, prefix + "_down_attempts")
            if first_downs or outcome.touchdown and not outcome.turnover:
                add(stats, prefix + "_down_conversions")
    for spike in context.get("spikes", []):
        if spike["down"] in (3, 4):
            add(
                _stats(engine, spike["home"]),
                ("third" if spike["down"] == 3 else "fourth") + "_down_attempts",
            )
    facts = context.get("punt")
    if play == PlayType.PUNT and facts and not result.punt_snap_fumble:
        kicker = _stats(engine, facts["home"])
        add(kicker, "punts")
        if facts.get("blocked"):
            add(kicker, "punts_blocked")
        else:
            distance = max(-facts["ball"], min(facts["distance"], 100 - facts["ball"]))
            add(kicker, "punt_yards", distance)
            add(kicker, "longest_punt", distance)
            if facts.get("touchback"):
                add(kicker, "punt_touchbacks")
            # Later fumble-recovery scores do not change the first return's end.
            elif 100 - facts["ball"] - distance + context.get("return", {}).get("yards", 0) < 20:
                add(kicker, "punts_inside_20")
            if facts.get("fair"):
                add(kicker, "punt_fair_catches")
                add(_stats(engine, not facts["home"]), "punt_return_fair_catches")
    returned = context.get("return")
    if returned and play in (PlayType.PUNT, PlayType.KICKOFF) and not returned.get("cancelled"):
        receiver = _stats(engine, returned["home"])
        prefix = "punt" if play == PlayType.PUNT else "kickoff"
        add(receiver, prefix + "_returns")
        add(receiver, prefix + "_return_yards", returned["yards"])
        add(receiver, "longest_" + prefix + "_return", returned["yards"])
        if returned["touchdown"]:
            add(receiver, prefix + "_return_touchdowns")
        if prefix == "punt":
            kicker = _stats(engine, not returned["home"])
            add(kicker, "punts_returned")
            add(kicker, "punt_return_yards_allowed", returned["yards"])


def capture_team_play(method: Callable) -> Callable:
    """Commit one outermost retained action, preserving pending context in saves."""

    @wraps(method)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        if self._team_stats_depth:
            return method(self, *args, **kwargs)
        pending = bool(self._team_stats_context.get("pending"))
        if not pending:
            self._team_stats_context = {
                "home": self.state.is_home_possession,
                "ball": self.state.ball_position,
                "down": self.state.down,
                "yards_to_go": self.state.yards_to_go,
                "first_downs": self.state.offense_stats.first_downs,
                "passing_yards": self.state.offense_stats.passing_yards,
                "rushing_yards": self.state.offense_stats.rushing_yards,
            }
        context = self._team_stats_context
        resolving = method.__name__.startswith("apply_")
        was_pending = (
            pending
            or bool(args and getattr(args[0], "pending_penalty_decision", False))
            or self.has_pending_end_zone_interception
        )
        if method.__name__ in ("apply_penalty_decision", "apply_fg_penalty_decision") and not (
            kwargs.get("accept_play", args[1] if len(args) > 1 else True)
        ):
            context["enforced_foul"] = True
        existing = tuple(self.play_log)
        self._team_stats_depth = 1
        try:
            outcome = method(self, *args, **kwargs)
        finally:
            self._team_stats_depth = 0
        if (
            outcome.pending_penalty_decision
            or outcome.pending_end_zone_interception_return_decision
        ):
            context["pending"] = True
        else:
            if (not resolving or was_pending) and (
                pending or not any(outcome is item for item in existing)
            ):
                _commit(self, context, outcome)
            self._team_stats_context = {}
        return outcome

    return wrapped


def record_return(engine: Any, *, home: bool, chain: Any, cancelled: bool = False) -> None:
    """Capture typed first-return segment, excluding later fumble-return chains."""
    engine._team_stats_context["return"] = {
        "home": home,
        "yards": chain.yards,
        "touchdown": chain.touchdown
        and chain.possession_home == home
        and not chain.fumbled
        and not chain.td_wiped,
        "cancelled": cancelled or chain.offsetting,
    }


def validate_team_stats_context(value: Any) -> dict:
    """Validate the closed primitive retained-play context used by checkpoint imports."""

    def integer(number: Any, low: int, high: int) -> bool:
        return type(number) is int and low <= number <= high

    required = {"home", "ball", "down", "first_downs", "passing_yards", "rushing_yards"}
    optional = {
        "pending",
        "enforced_foul",
        "spikes",
        "punt",
        "return",
        "yards_to_go",
        "penalty_first_downs",
    }
    if type(value) is not dict:
        raise ValueError("Invalid team statistics context")
    if not value:
        return value
    if not required <= value.keys() or value.keys() - required - optional:
        raise ValueError("Invalid team statistics context fields")
    if (
        type(value["home"]) is not bool
        or not integer(value["ball"], 0, 100)
        or not integer(value["down"], 1, 4)
        or not integer(value["first_downs"], 0, 1_000_000_000)
        or any(
            not integer(value[key], -1_000_000_000, 1_000_000_000)
            for key in ("passing_yards", "rushing_yards")
        )
    ):
        raise ValueError("Invalid team statistics context values")
    if "penalty_first_downs" in value and not integer(value["penalty_first_downs"], 0, 1):
        raise ValueError("Invalid penalty first-down context")
    if "yards_to_go" in value and not integer(value["yards_to_go"], 1, 100):
        raise ValueError("Invalid team statistics line to gain")
    for key in ("pending", "enforced_foul"):
        if key in value and type(value[key]) is not bool:
            raise ValueError("Invalid team statistics context flag")
    if "punt" in value:
        punt = value["punt"]
        fields = {"home", "ball", "blocked", "distance"}
        if (
            type(punt) is not dict
            or not fields <= punt.keys()
            or punt.keys() - fields - {"fair", "touchback"}
            or type(punt["home"]) is not bool
            or type(punt["blocked"]) is not bool
            or not integer(punt["ball"], 0, 100)
            or not integer(punt["distance"], -100, 200)
            or any(type(punt[key]) is not bool for key in ("fair", "touchback") if key in punt)
        ):
            raise ValueError("Invalid punt statistics context")
    if "return" in value:
        returned = value["return"]
        if (
            type(returned) is not dict
            or set(returned) != {"home", "yards", "touchdown", "cancelled"}
            or any(type(returned[key]) is not bool for key in ("home", "touchdown", "cancelled"))
            or not integer(returned["yards"], -110, 110)
        ):
            raise ValueError("Invalid return statistics context")
    if "spikes" in value:
        spikes = value["spikes"]
        if (
            type(spikes) is not list
            or len(spikes) > 1
            or any(
                type(spike) is not dict
                or set(spike) != {"home", "down"}
                or type(spike["home"]) is not bool
                or not integer(spike["down"], 1, 4)
                for spike in spikes
            )
        ):
            raise ValueError("Invalid spike statistics context")
    return value

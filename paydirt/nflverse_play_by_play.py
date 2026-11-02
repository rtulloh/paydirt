"""Classify nflverse play-by-play rows into empirical Paydirt outcomes."""

from __future__ import annotations

import csv
import gzip
import hashlib
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .pfr_play_by_play import (
    EmpiricalPlay,
    FieldGoalAttempt,
    FumbleEvent,
    normalized_penalty_result,
)

_PASS_CHARTS = ("screen", "short_pass", "medium_pass", "long_pass")
_PENALTY_CHARTS = (
    "line_plunge",
    "off_tackle",
    "end_run",
    "draw",
    "screen",
    "short_pass",
    "medium_pass",
    "long_pass",
)


@dataclass(frozen=True)
class ClassifiedNflverseSeason:
    """Normalized outcomes and audit evidence from an nflverse season file."""

    plays: tuple[EmpiricalPlay, ...]
    field_goals: tuple[FieldGoalAttempt, ...]
    fumbles: tuple[FumbleEvent, ...]
    diagnostics: Mapping[str, int]
    source_rows: int
    games: int


def _text(row: Mapping[str, object], name: str) -> str:
    """Return one source value as stripped text, treating missing values as empty."""
    value = row.get(name, "")
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"nan", "none"} else text


def _number(row: Mapping[str, object], name: str) -> float | None:
    """Parse one optional numeric source value."""
    text = _text(row, name)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _integer(row: Mapping[str, object], name: str, default: int = 0) -> int:
    """Parse an integer-like source value with a caller supplied default."""
    value = _number(row, name)
    return round(value) if value is not None else default


def _flag(row: Mapping[str, object], name: str) -> bool:
    """Interpret nflverse zero/one and Boolean fields consistently."""
    text = _text(row, name).casefold()
    if text in {"true", "yes"}:
        return True
    value = _number(row, name)
    return bool(value) if value is not None else False


def _play_number(row: Mapping[str, object], fallback: int) -> int:
    """Return the stable nflverse play identifier used in audit output."""
    value = _number(row, "play_id")
    return round(value) if value is not None else fallback


def _marked_numeric(yards: int, out_of_bounds: bool) -> str:
    """Format observed yards and retain the empirical out-of-bounds marker."""
    return f"{yards}{'*' if out_of_bounds else ''}"


def _fumble_result(yards: int) -> str:
    """Format a fumble while preserving yards gained before recovery."""
    if yards > 0:
        return f"F + {yards}"
    if yards < 0:
        return f"F - {abs(yards)}"
    return "F"


def _return_result(row: Mapping[str, object]) -> str:
    """Translate a return while preserving the chart family's touchdown convention."""
    yards = _integer(row, "return_yards")
    if _flag(row, "fumble"):
        return _fumble_result(yards)
    return _marked_numeric(yards, _flag(row, "out_of_bounds"))


def _has_kick_return(row: Mapping[str, object]) -> bool:
    """Exclude zero placeholders on nonreturn kicks from the return sample."""
    if any(_flag(row, key) for key in (
        "touchback", "punt_fair_catch", "punt_out_of_bounds", "punt_downed", "punt_blocked",
    )) or "no play" in _text(row, "desc").casefold():
        return False
    return _number(row, "return_yards") is not None


def _run_chart(row: Mapping[str, object]) -> str | None:
    """Map nflverse run direction and gap fields to a Paydirt run family."""
    description = _text(row, "desc").casefold()
    if _flag(row, "qb_kneel") or _flag(row, "qb_spike"):
        return None
    if _flag(row, "qb_scramble") or "scramble" in description:
        return "qb_time"
    if "draw" in description:
        return "draw"
    gap = _text(row, "run_gap").casefold()
    location = _text(row, "run_location").casefold()
    if gap == "end" or "left end" in description or "right end" in description:
        return "end_run"
    if gap == "tackle" or "left tackle" in description or "right tackle" in description:
        return "off_tackle"
    if gap == "guard" or location == "middle" or "up the middle" in description:
        return "line_plunge"
    if location in {"left", "right"}:
        return "off_tackle"
    return "line_plunge"


def _pass_chart(row: Mapping[str, object]) -> str:
    """Map structured pass depth to the closest Paydirt pass family."""
    description = _text(row, "desc").casefold()
    if "screen" in description:
        return "screen"
    air_yards = _number(row, "air_yards")
    if air_yards is not None:
        if air_yards <= 0:
            return "screen"
        if air_yards <= 9:
            return "short_pass"
        if air_yards <= 19:
            return "medium_pass"
        return "long_pass"
    pass_length = _text(row, "pass_length").casefold()
    if pass_length == "deep":
        return "long_pass"
    if pass_length == "short":
        return "short_pass"
    return "short_pass" if _integer(row, "ydstogo", 10) <= 10 else "medium_pass"


def _unknown_penalty_chart(row: Mapping[str, object], seed: int) -> str:
    """Assign a pre-snap penalty without a recorded call to a stable play family."""
    identity = "\0".join(
        (
            str(seed),
            _text(row, "game_id"),
            _text(row, "play_id"),
            _text(row, "desc"),
        )
    )
    selection = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], "big")
    return _PENALTY_CHARTS[selection % len(_PENALTY_CHARTS)]


def _scrimmage_chart(row: Mapping[str, object], seed: int) -> str | None:
    """Determine the called chart family for a scrimmage or no-play row."""
    play_type = _text(row, "play_type").casefold()
    description = _text(row, "desc").casefold()
    if play_type == "run" or _flag(row, "rush_attempt") or any(
        term in description for term in (" left end", " right end", " guard ", " tackle ", "scramble")
    ):
        return _run_chart(row)
    if play_type == "pass" or _flag(row, "pass_attempt") or " pass " in f" {description} ":
        return _pass_chart(row)
    if play_type == "no_play":
        return _unknown_penalty_chart(row, seed)
    return None


def _penalty_result(
    row: Mapping[str, object], offense: str, *, include_declined: bool = False
) -> str | None:
    """Return an engine-valid nflverse foul relative to the chart's offense."""
    if not _flag(row, "penalty"):
        return None
    description = _text(row, "desc").casefold()
    if "offsetting" in description or ("declined" in description and not include_declined):
        return None
    penalty_type = _text(row, "penalty_type").casefold()
    penalty_team = _text(row, "penalty_team").upper()
    yards = abs(_integer(row, "penalty_yards"))
    if "defensive pass interference" in penalty_type or (
        "pass interference" in penalty_type and penalty_team != offense
    ):
        return f"PI {max(1, yards)}"
    if yards <= 0:
        yards = 5 if any(term in penalty_type for term in ("offside", "false start")) else 10
    return normalized_penalty_result(penalty_type, penalty_team == offense, yards)


def _empirical_play(
    row: Mapping[str, object],
    team: str,
    unit: str,
    chart: str,
    result: str,
    fallback_number: int,
    opponent: str = "",
) -> EmpiricalPlay:
    """Construct one normalized outcome with nflverse source provenance."""
    return EmpiricalPlay(
        team=team,
        unit=unit,
        chart=chart,
        result=result,
        game_id=_text(row, "game_id"),
        play_number=_play_number(row, fallback_number),
        detail=_text(row, "desc"),
        opponent=opponent,
    )


def classify_nflverse_rows(
    rows: Iterable[Mapping[str, object]],
    seed: int = 8306,
) -> ClassifiedNflverseSeason:
    """Classify regular-season nflverse rows into empirical chart outcomes."""
    plays: list[EmpiricalPlay] = []
    field_goals: list[FieldGoalAttempt] = []
    fumbles: list[FumbleEvent] = []
    diagnostics: Counter[str] = Counter()
    games: set[str] = set()
    source_rows = 0

    for fallback_number, row in enumerate(rows, 1):
        if _text(row, "season_type").upper() != "REG":
            continue
        source_rows += 1
        game_id = _text(row, "game_id")
        if game_id:
            games.add(game_id)
        play_type = _text(row, "play_type").casefold()
        description = _text(row, "desc").casefold()
        offense = _text(row, "posteam").upper()
        defense = _text(row, "defteam").upper()

        if "offsetting" in description and _flag(row, "penalty"):
            diagnostics["offsetting_penalties"] += 1
            continue

        if play_type == "field_goal":
            distance = _integer(row, "kick_distance")
            result = _text(row, "field_goal_result").casefold()
            penalty_result = _penalty_result(row, offense, include_declined=True)
            if (
                offense
                and distance > 0
                and result in {"made", "missed", "blocked"}
                and "no play" not in description
            ):
                field_goals.append(
                    FieldGoalAttempt(
                        offense,
                        distance,
                        result == "made",
                        game_id,
                        _play_number(row, fallback_number),
                        blocked=result == "blocked",
                    )
                )
                diagnostics["field_goal_attempts"] += 1
            if offense and penalty_result is not None:
                plays.append(
                    _empirical_play(
                        row,
                        offense,
                        "special_teams",
                        "field_goal",
                        penalty_result,
                        fallback_number,
                    )
                )
                diagnostics["special_teams_penalties"] += 1
            continue

        if play_type == "kickoff":
            kicking_team = defense
            receiving_team = offense
            has_return = _has_kick_return(row)
            if _flag(row, "kickoff_out_of_bounds") or "kickoff out of bounds" in _text(row, "penalty_type").casefold():
                plays.append(_empirical_play(row, kicking_team, "special_teams", "kickoff", "OB", fallback_number))
                diagnostics["kickoff_out_of_bounds"] += 1
                continue
            penalty_result = _penalty_result(
                row, receiving_team if has_return else kicking_team, include_declined=True
            )
            if penalty_result is not None and (kicking_team or receiving_team):
                plays.append(
                    _empirical_play(
                        row,
                        receiving_team if has_return else kicking_team,
                        "special_teams",
                        "kickoff_return" if has_return else "kickoff",
                        penalty_result,
                        fallback_number,
                    )
                )
                diagnostics["special_teams_penalties"] += 1
                continue
            if kicking_team:
                kick_out = _flag(row, "kickoff_out_of_bounds") or (
                    "out of bounds" in description and not has_return
                )
                result = "OB" if kick_out else str(_integer(row, "kick_distance"))
                plays.append(
                    _empirical_play(row, kicking_team, "special_teams", "kickoff", result, fallback_number)
                )
            if receiving_team and has_return:
                plays.append(
                    _empirical_play(
                        row,
                        receiving_team,
                        "special_teams",
                        "kickoff_return",
                        _return_result(row),
                        fallback_number,
                    )
                )
            continue

        if play_type == "punt":
            return_team = _text(row, "return_team").upper() or defense
            has_return = _has_kick_return(row)
            penalty_result = _penalty_result(
                row,
                return_team if has_return else offense,
                include_declined=True,
            )
            if penalty_result is not None and (offense or return_team):
                plays.append(
                    _empirical_play(
                        row,
                        return_team if has_return else offense,
                        "special_teams",
                        "punt_return" if has_return else "punt",
                        penalty_result,
                        fallback_number,
                    )
                )
                diagnostics["special_teams_penalties"] += 1
                continue
            if offense:
                punt_result = "BK -5" if _flag(row, "punt_blocked") else str(_integer(row, "kick_distance"))
                if _flag(row, "punt_fair_catch"):
                    punt_result += "*"
                elif any(
                    _flag(row, name)
                    for name in ("touchback", "punt_out_of_bounds", "punt_downed")
                ):
                    punt_result += "†"
                plays.append(
                    _empirical_play(row, offense, "special_teams", "punt", punt_result, fallback_number)
                )
            if return_team and has_return:
                plays.append(
                    _empirical_play(
                        row,
                        return_team,
                        "special_teams",
                        "punt_return",
                        _return_result(row),
                        fallback_number,
                    )
                )
            continue

        if not offense or not defense:
            diagnostics["unattributed_rows"] += 1
            continue

        interception_return_penalty: str | None = None
        if (
            _flag(row, "interception")
            and _text(row, "return_team")
            and _number(row, "return_yards") is not None
            and not any(
                term in _text(row, "penalty_type").casefold()
                for term in (
                    "pass interference",
                    "roughing the passer",
                    "defensive holding",
                    "illegal contact",
                )
            )
        ):
            interception_return_penalty = _penalty_result(
                row,
                _text(row, "return_team").upper(),
                include_declined=True,
            )

        penalty_result = _penalty_result(row, offense)
        if penalty_result is not None and interception_return_penalty is None:
            chart = _scrimmage_chart(row, seed)
            if chart:
                plays.append(
                    _empirical_play(
                        row,
                        offense,
                        "offense",
                        chart,
                        penalty_result,
                        fallback_number,
                        defense,
                    )
                )
                diagnostics["accepted_penalties"] += 1
            else:
                diagnostics["unclassified_penalties"] += 1
            continue

        if play_type in {"qb_kneel", "qb_spike", "no_play"}:
            diagnostics["ignored_no_play"] += 1
            continue

        if _flag(row, "sack"):
            chart = _pass_chart(row)
            yards = _integer(row, "yards_gained")
            plays.append(
                _empirical_play(row, offense, "offense", chart, "QT", fallback_number, defense)
            )
            qb_result = _fumble_result(yards) if _flag(row, "fumble") else str(yards)
            plays.append(
                _empirical_play(
                    row,
                    offense,
                    "offense",
                    "qb_time",
                    qb_result,
                    fallback_number,
                    defense,
                )
            )
            if _flag(row, "fumble"):
                fumbles.append(FumbleEvent(offense, "passing", _flag(row, "fumble_lost"), game_id, _play_number(row, fallback_number)))
            diagnostics["sacks"] += 1
            continue

        if play_type == "pass" or _flag(row, "pass_attempt"):
            chart = _pass_chart(row)
            if _flag(row, "interception"):
                depth = max(0, _integer(row, "air_yards", 10))
                result = f"INT {depth}"
                return_team = _text(row, "return_team").upper() or defense
                plays.append(
                    _empirical_play(
                        row,
                        return_team,
                        "special_teams",
                        "interception_return",
                        interception_return_penalty or _return_result(row),
                        fallback_number,
                    )
                )
                if interception_return_penalty is not None:
                    diagnostics["special_teams_penalties"] += 1
                diagnostics["interceptions"] += 1
            elif _flag(row, "incomplete_pass"):
                result = "BLACK"
            elif _flag(row, "complete_pass"):
                yards = _integer(row, "yards_gained")
                if _flag(row, "fumble"):
                    result = _fumble_result(yards)
                    fumbles.append(FumbleEvent(offense, "passing", _flag(row, "fumble_lost"), game_id, _play_number(row, fallback_number)))
                else:
                    result = _marked_numeric(yards, _flag(row, "out_of_bounds"))
            else:
                diagnostics["unclassified_passes"] += 1
                continue
            plays.append(
                _empirical_play(row, offense, "offense", chart, result, fallback_number, defense)
            )
            continue

        if play_type == "run" or _flag(row, "rush_attempt"):
            chart = _run_chart(row)
            if chart is None:
                diagnostics["ignored_runs"] += 1
                continue
            yards = _integer(row, "yards_gained")
            if _flag(row, "touchdown"):
                # Preserve goal-line context instead of making the score automatic.
                result = _marked_numeric(yards, _flag(row, "out_of_bounds"))
            elif _flag(row, "fumble"):
                result = _fumble_result(yards)
                fumbles.append(FumbleEvent(offense, "rushing", _flag(row, "fumble_lost"), game_id, _play_number(row, fallback_number)))
            else:
                result = _marked_numeric(yards, _flag(row, "out_of_bounds"))
            plays.append(
                _empirical_play(row, offense, "offense", chart, result, fallback_number, defense)
            )
            continue

        diagnostics["ignored_rows"] += 1

    return ClassifiedNflverseSeason(
        plays=tuple(plays),
        field_goals=tuple(field_goals),
        fumbles=tuple(fumbles),
        diagnostics=dict(diagnostics),
        source_rows=source_rows,
        games=len(games),
    )


def _open_csv(path: Path) -> TextIO:
    """Open plain or gzip-compressed nflverse CSV data as UTF-8 text."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open("r", newline="", encoding="utf-8")


def load_nflverse_play_by_play(
    path: str | Path,
    seed: int = 8306,
) -> ClassifiedNflverseSeason:
    """Read and classify regular-season rows from one nflverse CSV file."""
    source_path = Path(path)
    with _open_csv(source_path) as source:
        return classify_nflverse_rows(csv.DictReader(source), seed=seed)

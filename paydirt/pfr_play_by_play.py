"""Parse historical Pro Football Reference play-by-play into chart outcomes.

The parser is intentionally separate from the statistical chart generator.  It
turns one source format into normalized empirical rows that
:class:`paydirt.chart_generator.EmpiricalChartData` already validates and uses.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .chart_generator import TeamSeasonStats

_PASS_CHARTS = ("screen", "short_pass", "medium_pass", "long_pass")
_PLAYER_HREF = re.compile(r"/players/[^/]+/([^/.]+)\.htm")
_YARDS = re.compile(r"\bfor (-?\d+) yards?\b", re.IGNORECASE)
_LOSS_YARDS = re.compile(r"\bfor (?:a )?loss of (\d+) yards?\b", re.IGNORECASE)
_FIELD_POSITION = re.compile(r"\b([A-Z]{2,3})\s*(\d{1,2})\b")
_FIELD_GOAL = re.compile(r"\b(\d+) yard field goal (good|no good|blocked)\b", re.IGNORECASE)
_PENALTY = re.compile(
    r"Penalty on ([^:]+): ([^,.(]+)(?:, (\d+) yards?)? \((accepted|declined)\)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PfrPlay:
    """One play row parsed from a PFR full play-by-play table."""

    game_id: str
    number: int
    quarter: int | None
    time_remaining: str
    down: int | None
    yards_to_go: int | None
    location: str
    away_score: int | None
    home_score: int | None
    detail: str
    player_ids: tuple[str, ...]


@dataclass(frozen=True)
class PfrGame:
    """Parsed source data needed to classify one PFR game."""

    game_id: str
    away_team: str
    home_team: str
    player_teams: Mapping[str, str]
    player_positions: Mapping[str, str]
    player_names: Mapping[str, str]
    plays: tuple[PfrPlay, ...]


@dataclass(frozen=True)
class EmpiricalPlay:
    """One normalized chart outcome attributed to a team and source play."""

    team: str
    unit: str
    chart: str
    result: str
    game_id: str
    play_number: int
    detail: str
    opponent: str = ""

    def to_row(self) -> dict[str, str | int]:
        """Return a CSV-compatible row accepted by ``EmpiricalChartData``."""
        return {
            "team": self.team,
            "unit": self.unit,
            "chart": self.chart,
            "result": self.result,
            "game_id": self.game_id,
            "play_number": self.play_number,
            "detail": self.detail,
            "opponent": self.opponent,
        }


@dataclass(frozen=True)
class FieldGoalAttempt:
    """A field-goal attempt retained for distance-bucket calibration."""

    team: str
    distance: int
    made: bool
    game_id: str
    play_number: int
    blocked: bool = False


@dataclass(frozen=True)
class FumbleEvent:
    """One offensive fumble and whether the opponent recovered it."""

    team: str
    unit: str
    lost: bool
    game_id: str
    play_number: int


@dataclass(frozen=True)
class ClassifiedGame:
    """Normalized empirical outcomes and audit counts from one game."""

    plays: tuple[EmpiricalPlay, ...]
    field_goals: tuple[FieldGoalAttempt, ...]
    fumbles: tuple[FumbleEvent, ...]
    diagnostics: Mapping[str, int]


class _PfrBoxscoreParser(HTMLParser):
    """Collect PFR player metadata and full play-by-play rows from HTML."""

    _PLAYER_TABLES: ClassVar[frozenset[str]] = frozenset({
        "player_offense",
        "player_defense",
        "returns",
        "kicking",
        "home_starters",
        "vis_starters",
    })

    def __init__(self, game_id: str) -> None:
        """Initialize parser state for one source game identifier."""
        super().__init__(convert_charrefs=True)
        self.game_id = game_id
        self.current_table = ""
        self.current_row: dict[str, object] | None = None
        self.current_cell = ""
        self.current_cell_parts: list[str] = []
        self.current_player_id = ""
        self.away_team = ""
        self.home_team = ""
        self.player_teams: dict[str, str] = {}
        self.player_positions: dict[str, str] = {}
        self.player_names: dict[str, str] = {}
        self.plays: list[PfrPlay] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record table, row, cell, and player-link boundaries."""
        attributes = {name: value or "" for name, value in attrs}
        if tag == "table":
            self.current_table = attributes.get("id", "")
            return
        if tag == "tr" and self.current_table:
            self.current_row = {"_player_ids": []}
            return
        if tag in {"th", "td"} and self.current_row is not None:
            self.current_cell = attributes.get("data-stat", "")
            self.current_cell_parts = []
            self.current_player_id = attributes.get("data-append-csv", "")
            if self.current_table == "pbp":
                if self.current_cell == "pbp_score_aw" and attributes.get("aria-label"):
                    self.away_team = attributes["aria-label"].strip().upper()
                elif self.current_cell == "pbp_score_hm" and attributes.get("aria-label"):
                    self.home_team = attributes["aria-label"].strip().upper()
            return
        if tag == "a" and self.current_row is not None and self.current_cell == "detail":
            match = _PLAYER_HREF.search(attributes.get("href", ""))
            if match:
                player_ids = self.current_row.setdefault("_player_ids", [])
                if isinstance(player_ids, list):
                    player_ids.append(match.group(1))

    def handle_data(self, data: str) -> None:
        """Append text inside the active table cell without altering punctuation."""
        if self.current_cell:
            self.current_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finalize cells, rows, and tables as their closing tags arrive."""
        if tag in {"th", "td"} and self.current_row is not None and self.current_cell:
            text = "".join(self.current_cell_parts).strip()
            self.current_row[self.current_cell] = text
            if self.current_player_id:
                self.current_row["_player_id"] = self.current_player_id
                self.current_row["_player_name"] = text
            self.current_cell = ""
            self.current_cell_parts = []
            self.current_player_id = ""
            return
        if tag == "tr" and self.current_row is not None:
            self._finish_row(self.current_row)
            self.current_row = None
            return
        if tag == "table":
            self.current_table = ""

    def _finish_row(self, row: Mapping[str, object]) -> None:
        """Store one completed metadata or play row."""
        if self.current_table in self._PLAYER_TABLES:
            player_id = str(row.get("_player_id", ""))
            if not player_id:
                return
            team = str(row.get("team", "")).strip().upper()
            if not team and self.current_table == "home_starters":
                team = self.home_team
            elif not team and self.current_table == "vis_starters":
                team = self.away_team
            if team:
                self.player_teams[player_id] = team
            position = str(row.get("pos", "")).strip().upper()
            if position:
                self.player_positions[player_id] = position
            player_name = str(row.get("_player_name", "")).strip()
            if player_name:
                self.player_names[player_name.casefold()] = player_id
            return
        if self.current_table != "pbp":
            return
        detail = str(row.get("detail", "")).strip()
        if not detail or detail == "Detail":
            return
        player_ids = row.get("_player_ids", [])
        ids = tuple(str(value) for value in player_ids) if isinstance(player_ids, list) else ()
        self.plays.append(
            PfrPlay(
                game_id=self.game_id,
                number=_play_number(detail, len(self.plays) + 1),
                quarter=_optional_int(row.get("quarter")),
                time_remaining=str(row.get("qtr_time_remain", "")).strip(),
                down=_optional_int(row.get("down")),
                yards_to_go=_optional_int(row.get("yds_to_go")),
                location=str(row.get("location", "")).strip(),
                away_score=_optional_int(row.get("pbp_score_aw")),
                home_score=_optional_int(row.get("pbp_score_hm")),
                detail=detail,
                player_ids=ids,
            )
        )


def _optional_int(value: object) -> int | None:
    """Convert a populated table value to an integer."""
    text = str(value or "").strip()
    return int(text) if re.fullmatch(r"-?\d+", text) else None


def _play_number(detail: str, fallback: int) -> int:
    """Return a stable fallback number when anchor markup carries no text."""
    del detail
    return fallback


def parse_pfr_boxscore(html: str, game_id: str) -> PfrGame:
    """Parse one PFR boxscore HTML document.

    Args:
        html: Full HTML containing player tables and the PBP table.
        game_id: Stable source identifier, normally the boxscore filename stem.

    Returns:
        Parsed game metadata and play rows.

    Raises:
        ValueError: If the document does not identify both teams or has no plays.
    """
    parser = _PfrBoxscoreParser(game_id)
    expanded_html = re.sub(
        r"<!--(.*?)-->",
        lambda match: match.group(1) if "<table" in match.group(1) else "",
        html,
        flags=re.DOTALL,
    )
    parser.feed(expanded_html)
    if not parser.away_team or not parser.home_team:
        raise ValueError(f"PFR boxscore {game_id} does not identify away and home teams")
    if not parser.plays:
        raise ValueError(f"PFR boxscore {game_id} has no play-by-play rows")
    return PfrGame(
        game_id=game_id,
        away_team=parser.away_team,
        home_team=parser.home_team,
        player_teams=dict(parser.player_teams),
        player_positions=dict(parser.player_positions),
        player_names=dict(parser.player_names),
        plays=tuple(parser.plays),
    )


def _opponent(game: PfrGame, team: str) -> str:
    """Return the other team in a parsed game."""
    return game.home_team if team == game.away_team else game.away_team


def _first_actor_team(game: PfrGame, play: PfrPlay, current_team: str | None) -> str | None:
    """Infer the acting team from linked players, falling back to possession state."""
    for player_id in play.player_ids:
        team = game.player_teams.get(player_id)
        if team:
            return team
    return current_team


def _other_linked_team(game: PfrGame, play: PfrPlay, team: str) -> str | None:
    """Find the first linked player belonging to the opponent."""
    for player_id in play.player_ids:
        candidate = game.player_teams.get(player_id)
        if candidate and candidate != team:
            return candidate
    return None


def normalized_penalty_result(name: str, offense_foul: bool, observed_yards: int) -> str:
    """Encode nominal foul yardage; let the engine apply current field position.

    Half-distance enforcement is evidence of a foul, not a smaller foul that
    should be enforced again at every future field position.
    """
    lower = name.casefold()
    yards = observed_yards
    if "holding" in lower:
        yards = 5 if "defensive holding" in lower else 10
    elif any(term in lower for term in (
        "offside", "false start", "encroachment", "neutral zone", "delay of game",
        "illegal contact", "illegal formation", "illegal shift", "illegal motion",
        "running into", "too many", "illegal substitution", "ineligible",
    )):
        yards = 5
    elif any(term in lower for term in (
        "roughing", "unnecessary roughness", "personal foul", "unsportsmanlike",
        "face mask", "facemask", "clipping", "chop block", "horse collar",
    )):
        yards = 15
    elif any(term in lower for term in ("block in the back", "offensive pass interference")):
        yards = 10
    if yards <= 0:
        yards = 10
    automatic = not offense_foul and any(term in lower for term in (
        "defensive holding", "illegal contact", "roughing the passer", "roughing the kicker",
    ))
    return f"{'OFF' if offense_foul else 'DEF'} {yards}{'X' if automatic else ''}"


def _penalty_result(
    game: PfrGame,
    play: PfrPlay,
    offense: str,
    *,
    include_declined: bool = False,
) -> tuple[str, str] | None:
    """Translate a source foul into a chart symbol relative to one offense."""
    match = _PENALTY.search(play.detail)
    if not match:
        return None
    offender_name, penalty_name, yards_text, status = match.groups()
    if status.casefold() != "accepted" and not include_declined:
        return None
    yards = int(yards_text or 0)
    offender_key = offender_name.strip()
    player_id = game.player_names.get(offender_key.casefold())
    offender_team = game.player_teams.get(player_id or "")
    if offender_key.upper() in {game.away_team, game.home_team}:
        offender_team = offender_key.upper()
    penalty_lower = penalty_name.casefold()
    if "defensive pass interference" in penalty_lower:
        return status.casefold(), f"PI {max(1, yards)}"
    if yards <= 0:
        yards = 5 if any(name in penalty_lower for name in ("offside", "false start")) else 10
    return status.casefold(), normalized_penalty_result(
        penalty_name, offender_team == offense, yards
    )


def _yards(detail: str) -> int | None:
    """Extract scrimmage or return yards from a play description."""
    loss = _LOSS_YARDS.search(detail)
    if loss:
        return -int(loss.group(1))
    match = _YARDS.search(detail)
    if match:
        return int(match.group(1))
    if "for no gain" in detail.casefold():
        return 0
    return None


def _marked_numeric(yards: int, detail: str) -> str:
    """Format yardage and preserve an empirical out-of-bounds marker."""
    marker = "*" if "out of bounds" in detail.casefold() else ""
    return f"{yards}{marker}"


def _fumble_result(yards: int) -> str:
    """Format a fumble while retaining yardage before the recovery roll."""
    if yards > 0:
        return f"F + {yards}"
    if yards < 0:
        return f"F - {abs(yards)}"
    return "F"


def _run_chart(game: PfrGame, play: PfrPlay) -> str | None:
    """Classify a source rush into the closest offensive chart family."""
    detail = play.detail.casefold()
    if "kneels" in detail or "spike" in detail:
        return None
    if "draw" in detail:
        return "draw"
    if "left end" in detail or "right end" in detail:
        return "end_run"
    if "left tackle" in detail or "right tackle" in detail:
        return "off_tackle"
    if re.search(r"\b(?:left|right) for\b", detail):
        return "off_tackle"
    if any(term in detail for term in ("up the middle", "left guard", "right guard")):
        return "line_plunge"
    first_id = play.player_ids[0] if play.player_ids else ""
    if game.player_positions.get(first_id) == "QB" or "scrambles" in detail:
        return "qb_time"
    if _yards(play.detail) is not None:
        return "line_plunge"
    return None


def _field_coordinate(location: str, offense: str) -> int | None:
    """Convert a team-yard location to yards from the offense's own goal line."""
    match = _FIELD_POSITION.search(location)
    if not match:
        return None
    side, yard_text = match.groups()
    yard = int(yard_text)
    return yard if side == offense else 100 - yard


def _interception_depth(play: PfrPlay, offense: str) -> int | None:
    """Estimate interception depth from line and defensive catch locations."""
    marker = play.detail.casefold().find("intercepted by")
    if marker < 0:
        return None
    catch = _FIELD_POSITION.search(play.detail[marker:])
    line = _field_coordinate(play.location, offense)
    if not catch or line is None:
        return None
    catch_coordinate = int(catch.group(2)) if catch.group(1) == offense else 100 - int(catch.group(2))
    return max(0, catch_coordinate - line)


def _pass_chart(play: PfrPlay, observed_yards: int | None, seed: int) -> tuple[str, bool]:
    """Choose a pass family, reporting whether a depth heuristic was required."""
    detail = play.detail.casefold()
    if "screen" in detail:
        return "screen", False
    if observed_yards is not None:
        if observed_yards <= 3:
            weights = (28, 60, 12, 0)
        elif observed_yards <= 9:
            weights = (25, 60, 15, 0)
        elif observed_yards <= 19:
            weights = (12, 15, 73, 0)
        elif observed_yards <= 29:
            weights = (8, 5, 77, 10)
        else:
            weights = (5, 0, 5, 90)
    else:
        to_go = play.yards_to_go or 10
        if to_go <= 3:
            weights = (25, 45, 25, 5)
        elif to_go <= 7:
            weights = (15, 45, 30, 10)
        elif to_go <= 12:
            weights = (10, 35, 35, 20)
        else:
            weights = (5, 20, 35, 40)
    digest = hashlib.sha256(
        f"{seed}\0{play.game_id}\0{play.number}\0{play.detail}".encode()
    ).digest()
    selection = int.from_bytes(digest[:8], "big") % sum(weights)
    running = 0
    for chart, weight in zip(_PASS_CHARTS, weights):
        running += weight
        if selection < running:
            return chart, True
    return "medium_pass", True


def _penalty_chart(play: PfrPlay, seed: int) -> str:
    """Spread unknown pre-snap penalty calls across primary play families."""
    charts = (
        "line_plunge",
        "off_tackle",
        "end_run",
        "draw",
        "screen",
        "short_pass",
        "medium_pass",
        "long_pass",
    )
    digest = hashlib.sha256(
        f"{seed}\0penalty\0{play.game_id}\0{play.number}\0{play.detail}".encode()
    ).digest()
    return charts[int.from_bytes(digest[:8], "big") % len(charts)]


def _recovery_team(game: PfrGame, play: PfrPlay, offense: str) -> str | None:
    """Resolve the recovery credit following a fumble description."""
    match = re.search(
        r"recovered by (.+?)(?: at [A-Z]{2,3}\d+| at [A-Z]{2,3} \d+|\.|,|$)",
        play.detail,
        re.IGNORECASE,
    )
    if not match:
        return None
    recovered_by = match.group(1).strip()
    if recovered_by.upper() in {game.away_team, game.home_team}:
        return recovered_by.upper()
    player_id = game.player_names.get(recovered_by.casefold())
    return game.player_teams.get(player_id or "") or offense


def _empirical_play(
    team: str,
    unit: str,
    chart: str,
    result: str,
    play: PfrPlay,
    opponent: str = "",
) -> EmpiricalPlay:
    """Construct one normalized outcome while retaining matchup provenance."""
    return EmpiricalPlay(
        team, unit, chart, result, play.game_id, play.number, play.detail, opponent
    )


def _return_result(detail: str) -> str:
    """Translate a return while preserving the chart family's touchdown convention."""
    lower = detail.casefold()
    marker = lower.find("returned")
    return_yards = _yards(detail[marker:]) if marker >= 0 else None
    yards = return_yards if return_yards is not None else 0
    if "fumble" in lower:
        return _fumble_result(yards)
    return _marked_numeric(yards, detail)


def classify_pfr_game(game: PfrGame, seed: int = 8306) -> ClassifiedGame:
    """Classify one parsed PFR game into empirical chart outcomes.

    PFR's historical descriptions identify run direction and observed results,
    but usually omit pass depth. Completed passes use observed gain bands; other
    passes use a deterministic down-and-distance allocation and are counted in
    diagnostics so the uncertainty remains visible.

    Args:
        game: Parsed PFR game.
        seed: Stable seed used for unknown pass-depth assignment.

    Returns:
        Classified outcomes, field-goal attempts, and audit counters.
    """
    outcomes: list[EmpiricalPlay] = []
    field_goals: list[FieldGoalAttempt] = []
    fumbles: list[FumbleEvent] = []
    diagnostics: Counter[str] = Counter()
    current_team: str | None = None

    for play in game.plays:
        detail = play.detail
        lower = detail.casefold()
        team = (
            current_team
            if lower.startswith("penalty on ") and current_team
            else _first_actor_team(game, play, current_team)
        )
        if not team:
            diagnostics["unattributed_rows"] += 1
            continue

        penalty_match = _PENALTY.search(detail)
        if penalty_match:
            status = penalty_match.group(4).casefold()
            diagnostics[f"{status}_penalties"] += 1
        if "offsetting" in lower:
            diagnostics["offsetting_penalties"] += 1
            continue

        if "kicks off" in lower:
            current_team = _opponent(game, team)
            has_return = "returned by" in lower
            if "kickoff oob" in lower:
                outcomes.append(_empirical_play(team, "special_teams", "kickoff", "OB", play))
                diagnostics["kickoff_out_of_bounds"] += 1
                continue
            penalty = _penalty_result(
                game, play, current_team if has_return else team, include_declined=True
            )
            if penalty is not None:
                outcomes.append(
                    _empirical_play(
                        current_team if has_return else team,
                        "special_teams",
                        "kickoff_return" if has_return else "kickoff",
                        penalty[1],
                        play,
                    )
                )
                diagnostics["special_teams_penalties"] += 1
                continue
            if "out of bounds" in lower and not has_return:
                kick_result = "OB"
            else:
                match = re.search(r"kicks off (\d+) yards?", detail, re.IGNORECASE)
                if not match:
                    diagnostics["unclassified_kickoffs"] += 1
                    continue
                kick_result = match.group(1)
            outcomes.append(_empirical_play(team, "special_teams", "kickoff", kick_result, play))
            if "returned by" in lower:
                return_team = _other_linked_team(game, play, team) or current_team
                outcomes.append(
                    _empirical_play(
                        return_team, "special_teams", "kickoff_return", _return_result(detail), play
                    )
                )
            continue

        field_goal_match = _FIELD_GOAL.search(detail)
        if field_goal_match:
            penalty = _penalty_result(game, play, team, include_declined=True)
            if "no play" in lower:
                diagnostics["nullified_field_goals"] += 1
            else:
                distance = int(field_goal_match.group(1))
                made = field_goal_match.group(2).casefold() == "good"
                field_goals.append(
                    FieldGoalAttempt(
                        team,
                        distance,
                        made,
                        play.game_id,
                        play.number,
                        blocked=field_goal_match.group(2).casefold() == "blocked",
                    )
                )
                diagnostics["field_goal_attempts"] += 1
            if penalty is not None:
                outcomes.append(
                    _empirical_play(
                        team, "special_teams", "field_goal", penalty[1], play
                    )
                )
                diagnostics["special_teams_penalties"] += 1
            continue

        if "punts" in lower:
            current_team = _opponent(game, team)
            has_return = "returned by" in lower
            penalty = _penalty_result(
                game,
                play,
                current_team if has_return else team,
                include_declined=True,
            )
            if penalty is not None:
                outcomes.append(
                    _empirical_play(
                        current_team if has_return else team,
                        "special_teams",
                        "punt_return" if has_return else "punt",
                        penalty[1],
                        play,
                    )
                )
                diagnostics["special_teams_penalties"] += 1
                continue
            if "punts blocked" in lower:
                punt_result = "BK -5"
            else:
                punt_match = re.search(r"punts (\d+) yards?", detail, re.IGNORECASE)
                if not punt_match:
                    diagnostics["unclassified_punts"] += 1
                    continue
                punt_result = punt_match.group(1)
                if "fair catch" in lower:
                    punt_result += "*"
                elif any(term in lower for term in ("touchback", "downed", "out of bounds")):
                    punt_result += "†"
            outcomes.append(_empirical_play(team, "special_teams", "punt", punt_result, play))
            if "returned by" in lower:
                return_team = _other_linked_team(game, play, team) or current_team
                outcomes.append(
                    _empirical_play(
                        return_team, "special_teams", "punt_return", _return_result(detail), play
                    )
                )
            continue

        offense = team
        opponent = _opponent(game, offense)
        current_team = offense
        interception_return_penalty: tuple[str, str] | None = None
        if "intercepted by" in lower and "returned" in lower:
            penalty_match = _PENALTY.search(detail)
            penalty_name = penalty_match.group(2).casefold() if penalty_match else ""
            if not any(
                term in penalty_name
                for term in (
                    "pass interference",
                    "roughing the passer",
                    "defensive holding",
                    "illegal contact",
                )
            ):
                return_team = _other_linked_team(game, play, offense) or opponent
                interception_return_penalty = _penalty_result(
                    game,
                    play,
                    return_team,
                    include_declined=True,
                )

        penalty = _penalty_result(game, play, offense)
        if penalty is not None and interception_return_penalty is None:
            if lower.startswith("penalty on "):
                chart = _penalty_chart(play, seed)
                diagnostics["unknown_penalty_play_family"] += 1
                heuristic = False
            else:
                chart, heuristic = (
                    _pass_chart(play, None, seed)
                    if "pass" in lower
                    else (_run_chart(game, play), False)
                )
            if heuristic:
                diagnostics["heuristic_pass_depth"] += 1
            if chart:
                outcomes.append(_empirical_play(offense, "offense", chart, penalty[1], play, opponent))
            else:
                diagnostics["unclassified_penalties"] += 1
            continue

        if "sacked by" in lower:
            sack_yards = _yards(detail)
            if sack_yards is None:
                diagnostics["unclassified_sacks"] += 1
                continue
            chart, heuristic = _pass_chart(play, None, seed)
            if heuristic:
                diagnostics["heuristic_pass_depth"] += 1
            outcomes.append(_empirical_play(offense, "offense", chart, "QT", play, opponent))
            qt_result = _fumble_result(-abs(sack_yards)) if "fumble" in lower else str(-abs(sack_yards))
            outcomes.append(_empirical_play(offense, "offense", "qb_time", qt_result, play, opponent))
            if "fumble" in lower:
                recovery = _recovery_team(game, play, offense)
                fumbles.append(
                    FumbleEvent(offense, "passing", recovery not in {None, offense}, play.game_id, play.number)
                )
            diagnostics["sacks"] += 1
            continue

        if "pass" in lower:
            interception = "intercepted by" in lower
            observed_yards = _yards(detail) if "complete" in lower else None
            depth = _interception_depth(play, offense) if interception else None
            chart, heuristic = _pass_chart(play, depth if interception else observed_yards, seed)
            if heuristic:
                diagnostics["heuristic_pass_depth"] += 1
            if interception:
                result = f"INT {depth if depth is not None else 10}"
                defense = _other_linked_team(game, play, offense) or _opponent(game, offense)
                outcomes.append(
                    _empirical_play(
                        defense,
                        "special_teams",
                        "interception_return",
                        (
                            interception_return_penalty[1]
                            if interception_return_penalty is not None
                            else _return_result(detail)
                        ),
                        play,
                    )
                )
                if interception_return_penalty is not None:
                    diagnostics["special_teams_penalties"] += 1
                current_team = defense
                diagnostics["interceptions"] += 1
            elif "incomplete" in lower:
                result = "BLACK"
            elif observed_yards is not None:
                if "fumble" in lower:
                    result = _fumble_result(observed_yards)
                    recovery = _recovery_team(game, play, offense)
                    fumbles.append(
                        FumbleEvent(offense, "passing", recovery not in {None, offense}, play.game_id, play.number)
                    )
                else:
                    result = _marked_numeric(observed_yards, detail)
            else:
                diagnostics["unclassified_passes"] += 1
                continue
            outcomes.append(_empirical_play(offense, "offense", chart, result, play, opponent))
            continue

        run_chart = _run_chart(game, play)
        if run_chart:
            run_yards = _yards(detail)
            if run_yards is None:
                diagnostics["unclassified_runs"] += 1
                continue
            if "touchdown" in lower:
                # A short goal-line score is still a short gain when replayed
                # elsewhere on the field; the engine converts gains at the goal line.
                run_result = _marked_numeric(run_yards, detail)
            elif "fumble" in lower:
                run_result = _fumble_result(run_yards)
                recovery = _recovery_team(game, play, offense)
                fumbles.append(
                    FumbleEvent(offense, "rushing", recovery not in {None, offense}, play.game_id, play.number)
                )
            else:
                run_result = _marked_numeric(run_yards, detail)
            outcomes.append(_empirical_play(offense, "offense", run_chart, run_result, play, opponent))
            continue

        if any(
            term in lower
            for term in ("extra point", "timeout", "coin toss", "end of", "kneels")
        ):
            diagnostics["ignored_markers"] += 1
        else:
            diagnostics["unclassified_rows"] += 1

    return ClassifiedGame(
        tuple(outcomes), tuple(field_goals), tuple(fumbles), dict(diagnostics)
    )


def calibrate_stats_from_pbp(
    stats: TeamSeasonStats,
    team: str,
    field_goals: Sequence[FieldGoalAttempt],
    fumbles: Sequence[FumbleEvent],
) -> TeamSeasonStats:
    """Add distance kicking and fumble-loss evidence to aggregate team stats.

    Args:
        stats: Aggregate season totals used as the generation baseline.
        team: PFR abbreviation whose events should be applied.
        field_goals: Classified attempts from all parsed games.
        fumbles: Classified offensive fumbles from all parsed games.

    Returns:
        A copy of the team statistics with observed calibration fields replaced.
    """
    from .chart_generator import FieldGoalDistanceStats, TeamSeasonStats

    team_fumbles = [event for event in fumbles if event.team == team]
    rushing_events = [event for event in team_fumbles if event.unit == "rushing"]
    passing_events = [event for event in team_fumbles if event.unit == "passing"]

    rushing = stats.offense.rushing
    if rushing_events:
        rushing = replace(
            rushing,
            fumbles=len(rushing_events),
            fumbles_lost=sum(event.lost for event in rushing_events),
        )
    passing = stats.offense.passing
    if passing_events:
        passing = replace(
            passing,
            fumbles=len(passing_events),
            fumbles_lost=sum(event.lost for event in passing_events),
        )

    attempts = [attempt for attempt in field_goals if attempt.team == team]
    special_teams = stats.special_teams
    if attempts:
        by_distance: dict[int, list[int]] = {}
        for attempt in attempts:
            totals = by_distance.setdefault(attempt.distance, [0, 0, 0])
            totals[0] += 1
            totals[1] += int(attempt.made)
            totals[2] += int(attempt.blocked)
        buckets = tuple(
            FieldGoalDistanceStats(distance, counts[0], counts[1], counts[2])
            for distance, counts in sorted(by_distance.items())
        )
        made_distances = [attempt.distance for attempt in attempts if attempt.made]
        field_goal = replace(
            special_teams.field_goal,
            attempts=len(attempts),
            made=sum(attempt.made for attempt in attempts),
            blocked=sum(attempt.blocked for attempt in attempts),
            long=max(made_distances, default=special_teams.field_goal.long),
        )
        special_teams = replace(
            special_teams,
            field_goal=field_goal,
            field_goal_by_distance=buckets,
        )

    return TeamSeasonStats(
        season=stats.season,
        team_name=stats.team_name,
        short_name=stats.short_name,
        offense=replace(stats.offense, rushing=rushing, passing=passing),
        defense=stats.defense,
        special_teams=special_teams,
    )

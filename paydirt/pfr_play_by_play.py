"""Parse historical Pro Football Reference play-by-play into chart outcomes.

The parser is intentionally separate from the statistical chart generator.  It
turns one source format into normalized empirical rows that
:class:`paydirt.chart_generator.EmpiricalChartData` already validates and uses.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from typing import TYPE_CHECKING, ClassVar

from .fumble_source import (
    FumbleGainFacts,
    FumbleGainProjection,
    inferred_rushing_chart,
    project_fumble_gain,
    validate_fumble_gain_policy,
)
from .pfr_event_reconciliation import (
    AbortedFieldGoalFact,
    EventFact,
    FumbleEventFact,
    PrepassFumbleFact,
    SackEventFact,
    play_fingerprint,
)
from .pfr_fumble_source import extract_reported_primary_gain, extract_reported_return_gain

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
    # Complete kicking-box rows: player ID -> (team, attempts, makes). None
    # means unavailable/incomplete evidence, never an implied zero.
    field_goal_box: Mapping[str, tuple[str, int, int]] | None = None
    # Whole-team game totals include fumbles outside the offensive subset.
    fumble_box: Mapping[str, tuple[int, int]] | None = None


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
    lost: bool | None
    game_id: str
    play_number: int
    retained_incompletion: bool = False
    field_goal_snap_result: str = ""


@dataclass(frozen=True)
class ClassifiedGame:
    """Normalized empirical outcomes and audit counts from one game."""

    plays: tuple[EmpiricalPlay, ...]
    field_goals: tuple[FieldGoalAttempt, ...]
    fumbles: tuple[FumbleEvent, ...]
    diagnostics: Mapping[str, int]
    source_conflicts: tuple[Mapping[str, object], ...] = ()
    event_counts: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    unsupported_fields: tuple[Mapping[str, object], ...] = ()
    fumble_reconciliations: tuple[Mapping[str, object], ...] = ()
    fumble_gain_projections: tuple[FumbleGainProjection, ...] = ()


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
        self.starter_sides: dict[str, set[str]] = {}
        self.plays: list[PfrPlay] = []
        self.field_goal_box: dict[str, tuple[str, int, int]] = {}
        self.field_goal_box_valid = True
        self.fumble_box_sides: tuple[tuple[int, int], ...] | None = None
        self.fumble_box_valid = True
        self.fumble_box_seen = False

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
        if self.current_table == "team_stats" and row.get("stat") == "Fumbles-Lost":
            matches = [re.fullmatch(r"(\d+)-(\d+)", str(row.get(side, "")).strip())
                       for side in ("vis_stat", "home_stat")]
            if self.fumble_box_seen or any(match is None for match in matches):
                self.fumble_box_valid = False
            else:
                self.fumble_box_sides = tuple(tuple(map(int, match.groups())) for match in matches)
                if any(lost > count for count, lost in self.fumble_box_sides):
                    self.fumble_box_valid = False
            self.fumble_box_seen = True
            return
        if self.current_table in self._PLAYER_TABLES:
            player_id = str(row.get("_player_id", ""))
            if not player_id:
                return
            team = str(row.get("team", "")).strip().upper()
            if self.current_table == "kicking":
                attempts, made = row.get("fga"), row.get("fgm")
                if (not team or attempts is None or made is None
                        or not re.fullmatch(r"\d*", str(attempts))
                        or not re.fullmatch(r"\d*", str(made))):
                    self.field_goal_box_valid = False
                else:
                    credit = (team, int(str(attempts) or 0), int(str(made) or 0))
                    if credit[2] > credit[1] or player_id in self.field_goal_box:
                        self.field_goal_box_valid = False
                    self.field_goal_box[player_id] = credit
            if self.current_table in {"home_starters", "vis_starters"}:
                self.starter_sides.setdefault(player_id, set()).add(self.current_table)
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
    # Starter tables commonly precede the PBP team headers. Their explicit
    # home/visitor identity survives table ordering; a position or later
    # recovering player's team is never a substitute for this source fact.
    for player_id, sides in parser.starter_sides.items():
        if len(sides) != 1:
            raise ValueError(f"PFR starter {player_id} has conflicting home/visitor identities")
        team = parser.home_team if "home_starters" in sides else parser.away_team
        if parser.player_teams.get(player_id) not in {None, team}:
            raise ValueError(f"PFR starter {player_id} has conflicting team metadata")
        parser.player_teams[player_id] = team
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
        field_goal_box=(dict(parser.field_goal_box)
                        if parser.field_goal_box_valid and parser.field_goal_box else None),
        fumble_box=(dict(zip((parser.away_team, parser.home_team), parser.fumble_box_sides))
                    if parser.fumble_box_valid and parser.fumble_box_sides is not None else None),
    )


def _reconcile_field_goal_box(
    game: PfrGame, attempts: list[FieldGoalAttempt], diagnostics: Counter[str],
) -> tuple[list[FieldGoalAttempt], tuple[Mapping[str, object], ...]]:
    """Separate conflicting descriptions only after exact per-player box fit.

    A complete set of identified attempts must independently account for every
    official attempt and make. Excess/short samples for an actual credited
    kicker are ambiguous; no arbitrary subset is selected to force a match.
    Uncredited descriptions retain event provenance and unknown mechanism.
    """
    box = game.field_goal_box
    if box is None:
        diagnostics["unverified_field_goal_box"] += 1
        return attempts, ()
    plays = {play.number: play for play in game.plays}
    identified: dict[str, list[FieldGoalAttempt]] = {}
    unmatched: list[tuple[FieldGoalAttempt, str]] = []
    unknown = False
    box_teams = {credit[0] for credit in box.values()}
    for attempt in attempts:
        ids = plays[attempt.play_number].player_ids
        actor = ids[0] if ids else ""
        if not actor or attempt.team not in box_teams:
            unknown = True
        if actor in box and box[actor][1] > 0:
            if box[actor][0] != attempt.team:
                unknown = True
            identified.setdefault(actor, []).append(attempt)
        else:
            unmatched.append((attempt, actor))
    for actor, (_team, count, made) in box.items():
        observed = identified.get(actor, [])
        if len(observed) != count or sum(attempt.made for attempt in observed) != made:
            unknown = True
    if unknown:
        diagnostics["unreconciled_field_goal_box"] += 1
        return attempts, ()
    conflicts = tuple({
        "game_id": attempt.game_id, "play_number": attempt.play_number,
        "team": attempt.team, "player_id": actor,
        "source_category": "field_goal_description", "official_attempt": False,
        "category": "description_without_official_attempt_credit", "mechanism": "unknown",
        "box_attempts_and_makes_reconciled": True,
    } for attempt, actor in unmatched)
    diagnostics["field_goal_descriptions_without_box_credit"] += len(conflicts)
    retained = [attempt for values in identified.values() for attempt in values]
    retained.sort(key=lambda attempt: attempt.play_number)
    diagnostics["field_goal_attempts"] = len(retained)
    return retained, conflicts


def _reconcile_fumble_box(
    game: PfrGame, fumbles: list[FumbleEvent], diagnostics: Counter[str],
) -> tuple[list[FumbleEvent], tuple[Mapping[str, object], ...]]:
    """Resolve ownership only when every assignment fits the same loss credit.

    The box covers all fumbles; the observed offense is a potentially incomplete
    subset. Exhausted loss credit implies retention even with unseen events.
    Assigning every unknown a loss additionally requires a complete inventory.
    """
    if game.fumble_box is None:
        diagnostics["unverified_fumble_box"] += 1
        return fumbles, ()
    result = list(fumbles)
    receipts = []
    for team, (box_count, box_lost) in game.fumble_box.items():
        events = [(index, event) for index, event in enumerate(fumbles) if event.team == team]
        known_lost = sum(event.lost is True for _, event in events)
        known_retained = sum(event.lost is False for _, event in events)
        unknown = [(index, event) for index, event in events if event.lost is None]
        keys = {(event.game_id, event.play_number) for _, event in events}
        if (len(events) > box_count or known_lost > box_lost
                or known_retained > box_count - box_lost or len(keys) != len(events)):
            diagnostics["unreconciled_fumble_box"] += 1
            continue
        if not unknown:
            continue
        if known_lost == box_lost:
            lost = False
        elif len(events) == box_count and box_lost - known_lost == len(unknown):
            lost = True
        else:
            continue
        for index, event in unknown:
            result[index] = replace(event, lost=lost)
            receipts.append({
                "game_id": event.game_id, "play_number": event.play_number,
                "team": team, "unit": event.unit, "lost": lost,
                "method": "unique-team-fumble-loss-constraint",
                "box_fumbles": box_count, "box_lost": box_lost,
                "observed_fumbles": len(events), "known_lost": known_lost,
                "known_retained": known_retained, "unknown_recoveries": len(unknown),
            })
            diagnostics["box_reconciled_fumble_recoveries"] += 1
    return result, tuple(receipts)


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
    # Only the current ball-carrying phase supplies its gain. Recovery returns
    # and enforcement must not fill an absent initial gain, including known zero.
    detail = re.split(r"\bfumbles?\b|\brecovered by\b|\bpenalty on\b",
                      detail, maxsplit=1, flags=re.IGNORECASE)[0]
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


def _run_chart(
    game: PfrGame, play: PfrPlay, diagnostics: Counter[str] | None = None,
) -> str | None:
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
    if "scrambles" in detail or "sacked by" in detail:
        return "qb_time"
    if game.player_positions.get(first_id) == "QB":
        # A position is not evidence of a dropback. Aborted exchanges and
        # unspecified QB runs must not become QT sacks, especially F0/F-minus.
        if diagnostics is not None:
            diagnostics["heuristic_quarterback_run_family"] += 1
        return "line_plunge"
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
    match = re.search(r"recovered by\s+", play.detail, re.IGNORECASE)
    if not match:
        return None
    recovery = play.detail[match.end():].strip().casefold()
    actors = {name: game.player_teams.get(player_id)
              for name, player_id in game.player_names.items()}
    actors.update({team.casefold(): team for team in (game.away_team, game.home_team)})
    # Resolve the whole known name before looking for clause punctuation:
    # periods inside initials and an absent field location do not erase identity.
    for actor in sorted(actors, key=lambda name: (-len(name), name)):
        if recovery.startswith(actor) and re.match(
            r"(?:$|[.,](?:\s|$)| at(?:\s|$)| and returned(?:\s|$))",
            recovery[len(actor):],
        ):
            return actors[actor]
    return None


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


def _reviewed_fumble_lost(
    game: PfrGame, play: PfrPlay, offense: str, fact: FumbleEventFact | None,
) -> bool | None:
    if fact is not None:
        return fact.fumble_lost
    recovery = _recovery_team(game, play, offense)
    return None if recovery is None else recovery != offense


def _reviewed_initial_gain(play: PfrPlay, fact: FumbleEventFact | None) -> int | None:
    if fact is not None and fact.initial_gain_reviewed:
        return fact.initial_gain
    return _yards(play.detail)


def _project_reviewed_fumble(
    game: PfrGame, play: PfrPlay, offense: str, fact: EventFact | None, policy: str,
    reconciled_recovery: FumbleEvent | None = None,
) -> FumbleGainProjection:
    """Project distinct reviewed and reported tiers, never infer class from QB position."""
    if policy in {"historical_fumble_class_proxy_v1", "historical_fumble_class_proxy_v2"}:
        if fact is not None and fact.raw_play_sha256 != play_fingerprint(play):
            raise ValueError("Reviewed fumble credit source identity differs")
        try:
            return replace(_project_reviewed_fumble(
                game, play, offense, fact, "source_reported_gain_proxy_v1", reconciled_recovery), policy=policy)
        except ValueError:
            # Reviewed classifications and credited numbers always take precedence;
            # an assumption must not conceal contradictory or incomplete review.
            if (isinstance(fact, SackEventFact) or isinstance(fact, FumbleEventFact)
                    and (fact.credited_kind is not None or fact.originating_kind is not None)):
                raise
        from .historical_fumble_proxy import project_historical_fumble

        lost = _reviewed_fumble_lost(
            game, play, offense, fact if isinstance(fact, FumbleEventFact) else None)
        basis = "reviewed" if isinstance(fact, FumbleEventFact) else "reported_identity"
        if lost is None and reconciled_recovery is not None:
            lost, basis = reconciled_recovery.lost, "unique_team_loss_constraint"
        facts = FumbleGainFacts(
            f"{play.game_id}:{play.number}", play_fingerprint(play), None, None,
            fact.initial_gain if isinstance(fact, FumbleEventFact) and fact.initial_gain_reviewed else None,
            lost, fact.loose_ball_yards if isinstance(fact, FumbleEventFact) else None,
            fact.recovery_advance_yards if isinstance(fact, FumbleEventFact) else None,
            recovery_basis=basis,
        )
        return project_historical_fumble(game, play, offense, facts, policy=policy)
    kind, credit, physical = None, None, None
    loose_ball, recovery_advance = None, None
    if isinstance(fact, SackEventFact):
        kind = "sack"
        credit = -fact.credited_sack_loss if fact.credited_sack_loss is not None else None
        physical = fact.initial_gain
    elif isinstance(fact, FumbleEventFact):
        kind, credit = fact.credited_kind, fact.credited_yards
        physical = fact.initial_gain if fact.initial_gain_reviewed else None
        loose_ball, recovery_advance = fact.loose_ball_yards, fact.recovery_advance_yards
    if fact is not None and fact.raw_play_sha256 != play_fingerprint(play):
        raise ValueError("Reviewed fumble credit source identity differs")
    lower = play.detail.casefold()
    if (kind == "rushing" and any(text in lower for text in ("sacked by", "pass complete"))
            or kind == "receiving" and "pass complete" not in lower):
        raise ValueError("Reviewed credited class conflicts with retained source context")
    lost = _reviewed_fumble_lost(
        game, play, offense, fact if isinstance(fact, FumbleEventFact) else None)
    reported = None
    recovery_basis = "reviewed" if isinstance(fact, FumbleEventFact) else "reported_identity"
    if policy == "source_reported_gain_proxy_v1":
        try:
            if isinstance(fact, FumbleEventFact) and fact.reported_primary_yards is not None:
                from .pfr_fumble_source import ReportedPrimaryGain

                reported = ReportedPrimaryGain(
                    fact.originating_kind, fact.reported_primary_yards,
                    fact.originating_player_id, fact.originating_team,
                    "reviewed source evidence")
            elif isinstance(fact, FumbleEventFact) and fact.originating_kind in {
                    "kickoff_return", "punt_return"}:
                reported = extract_reported_return_gain(
                    game, play, offense, reviewed_kind=fact.originating_kind,
                    reviewed_actor=fact.originating_player_id)
            else:
                reported = extract_reported_primary_gain(
                    game, play, offense,
                    reviewed_kind=fact.originating_kind if isinstance(fact, FumbleEventFact) else None,
                    reviewed_actor=fact.originating_player_id if isinstance(fact, FumbleEventFact) else None)
        except ValueError:
            if kind is None or credit is None:
                raise
        if lost is None and reconciled_recovery is not None:
            lost = reconciled_recovery.lost
            recovery_basis = "unique_team_loss_constraint"
    return project_fumble_gain(FumbleGainFacts(
        f"{play.game_id}:{play.number}", play_fingerprint(play), kind, credit, physical, lost,
        loose_ball, recovery_advance,
        reported_kind=reported.kind if reported else None,
        reported_yards=reported.yards if reported else None,
        reported_scope=("return_before_fumble" if reported.kind in {
            "kickoff_return", "punt_return"} else "primary_before_fumble") if reported else None,
        reported_actor=reported.actor if reported else None,
        reported_team=reported.team if reported else None,
        recovery_basis=recovery_basis,
    ), policy=policy)


def classify_pfr_game(
    game: PfrGame, seed: int = 8306, *,
    event_facts: Mapping[int, EventFact] | None = None,
    fumble_gain_policy: str | None = None,
) -> ClassifiedGame:
    """Classify one parsed PFR game into empirical chart outcomes.

    PFR's historical descriptions identify run direction and observed results,
    but usually omit pass depth. Completed passes use observed gain bands; other
    passes use a deterministic down-and-distance allocation and are counted in
    diagnostics so the uncertainty remains visible.

    Args:
        game: Parsed PFR game.
        seed: Stable seed used for unknown pass-depth assignment.
        event_facts: Validated primary-source facts bound to unchanged raw events.
        fumble_gain_policy: Explicit experimental gain policy; None retains legacy classification.

    Returns:
        Classified outcomes, field-goal attempts, and audit counters.
    """
    validate_fumble_gain_policy(fumble_gain_policy)
    projections: list[FumbleGainProjection] = []
    outcomes: list[EmpiricalPlay] = []
    field_goals: list[FieldGoalAttempt] = []
    fumbles: list[FumbleEvent] = []
    diagnostics: Counter[str] = Counter()
    event_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    unsupported_fields: list[Mapping[str, object]] = []
    reviewed_snap_receipts: list[Mapping[str, object]] = []
    current_team: str | None = None
    reconciled_recoveries: dict[int, FumbleEvent] = {}
    recovery_receipts: tuple[Mapping[str, object], ...] = ()
    if fumble_gain_policy in {"source_reported_gain_proxy_v1", "historical_fumble_class_proxy_v1", "historical_fumble_class_proxy_v2"}:
        # Reuse the complete existing loss-constraint inventory. This read-only
        # pass supplies recovery support only, never legacy gain/class inference.
        recovery_inventory = classify_pfr_game(game, seed=seed, event_facts=event_facts)
        recovery_receipts = recovery_inventory.fumble_reconciliations
        reconciled_recoveries = {event.play_number: event for event in recovery_inventory.fumbles
                                if event.lost is not None}
    modeled_continuations = {
        fact.continuation_play_number: fact for fact in (event_facts or {}).values()
        if isinstance(fact, PrepassFumbleFact) and fumble_gain_policy is not None
    }
    for play in game.plays:
        detail = play.detail
        lower = detail.casefold()
        fact = (event_facts or {}).get(play.number)
        sack_fact = fact if isinstance(fact, SackEventFact) else None
        fumble_fact = fact if isinstance(fact, FumbleEventFact) else None
        team = (
            current_team
            if lower.startswith("penalty on ") and current_team
            else _first_actor_team(game, play, current_team)
        )
        if isinstance(fact, AbortedFieldGoalFact):
            team = fact.offense_team
        elif fumble_fact is not None and fumble_fact.originating_team is not None:
            team = fumble_fact.originating_team
        if not team:
            diagnostics["unattributed_rows"] += 1
            continue

        if isinstance(fact, AbortedFieldGoalFact):
            # A reviewed bad snap is an event even when the secondary feed labels
            # it a missed kick. Its credited runner need not be the fumbler.
            # Only explicit zero credit and ownership authorize the typed proxy;
            # unknown physical movement remains a separate nullable fact.
            current_team = fact.offense_team
            projection = None
            reason = "requires explicit zero rushing credit, ownership and a supported gain policy"
            if fumble_gain_policy is not None:
                try:
                    projection = project_fumble_gain(FumbleGainFacts(
                        f"{play.game_id}:{play.number}", play_fingerprint(play),
                        "rushing" if fact.credited_player_id is not None else None,
                        fact.credited_rushing_yards, fact.physical_initial_yards,
                        fact.individual_lost, recovery_basis="reviewed",
                        aborted_field_goal=True,
                    ), policy=fumble_gain_policy)
                except ValueError as error:
                    reason = str(error)
            fumbles.append(FumbleEvent(
                fact.offense_team, "field_goal_snap", fact.individual_lost,
                play.game_id, play.number,
                field_goal_snap_result=projection.chart_result if projection else ""))
            diagnostics["reconciled_aborted_field_goals"] += 1
            event_counts[fact.offense_team]["aborted_field_goals"] += 1
            receipt = {
                **fact.to_dict(), "method": "reviewed-aborted-field-goal",
                "possession_changed": (None if fact.recovering_team is None else
                                       fact.recovering_team != fact.offense_team),
                "official_attempt": False,
            }
            reviewed_snap_receipts.append(receipt)
            if projection is not None:
                projections.append(projection)
                diagnostics[f"fumble_gain_basis_{projection.modeled_gain_basis}"] += 1
                outcomes.append(_empirical_play(
                    team, "special_teams", "field_goal", projection.chart_result, play))
            else:
                unsupported_fields.append({
                    "game_id": play.game_id, "play_number": play.number, "team": fact.offense_team,
                    "field": "aborted_field_goal_projection", "reason": reason,
                })
            continue

        if play.number in modeled_continuations:
            current_team = team
            chart, heuristic = _pass_chart(play, None, seed)
            diagnostics["heuristic_pass_depth"] += int(heuristic)
            outcomes.append(_empirical_play(
                team, "offense", chart, "F INC", play, _opponent(game, team)))
            continue
        if isinstance(fact, PrepassFumbleFact):
            current_team = team
            modeled = fumble_gain_policy is not None
            fumbles.append(FumbleEvent(
                team, "passing", False, play.game_id, play.number,
                retained_incompletion=modeled))
            diagnostics["reconciled_prepass_fumbles"] += 1
            if modeled:
                projections.append(project_fumble_gain(FumbleGainFacts(
                    f"{play.game_id}:{play.number}", play_fingerprint(play),
                    "incomplete", 0, None, False,
                    recovery_basis="reviewed_prepass", retained_incompletion=True,
                ), policy=fumble_gain_policy))
                diagnostics["fumble_gain_basis_retained_incompletion"] += 1
            else:
                # Legacy BLACK preserves the attempt but cannot carry the occurrence.
                diagnostics["unmodeled_prepass_fumbles"] += 1
            continue
        if fumble_fact is not None:
            diagnostics["reconciled_fumble_recoveries"] += 1
            diagnostics["reconciled_fumble_out_of_bounds"] += int(fumble_fact.out_of_bounds)

        penalty_match = _PENALTY.search(detail)
        if penalty_match:
            status = penalty_match.group(4).casefold()
            diagnostics[f"{status}_penalties"] += 1
        if "offsetting" in lower or "(offset)" in lower:
            diagnostics["offsetting_penalties"] += 1
            continue

        if fumble_fact is not None and fumble_fact.originating_kind in {
                "kickoff_return", "punt_return"}:
            return_kind = fumble_fact.originating_kind
            fumbles.append(FumbleEvent(team, return_kind, fumble_fact.fumble_lost,
                                       play.game_id, play.number))
            try:
                if fumble_gain_policy is not None:
                    projected = _project_reviewed_fumble(
                        game, play, team, fumble_fact, fumble_gain_policy)
                    projections.append(projected)
                    diagnostics[f"fumble_gain_basis_{projected.modeled_gain_basis}"] += 1
                    cell = projected.chart_result
                else:
                    reported = extract_reported_return_gain(
                        game, play, team, reviewed_kind=return_kind,
                        reviewed_actor=fumble_fact.originating_player_id)
                    cell = _fumble_result(reported.yards)
            except ValueError as exc:
                unsupported_fields.append({
                    "game_id": play.game_id, "play_number": play.number, "team": team,
                    "field": "fumble_gain_projection", "reason": str(exc)})
                continue
            outcomes.append(_empirical_play(team, "special_teams", return_kind, cell, play))
            diagnostics["reconciled_kick_return_fumbles"] += 1
            current_team = _opponent(game, team) if fumble_fact.fumble_lost else team
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
        if "intercepted by" in lower and "returned" in lower and "no play" not in lower:
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
        credited_sack = ("sacked by" in lower or sack_fact is not None
                         or fumble_fact is not None and (
                             fumble_fact.credited_kind == "sack"
                             or fumble_fact.originating_kind == "sack")) and "no play" not in lower
        if credited_sack:
            diagnostics["sacks"] += 1
            event_counts[offense]["sacks"] += 1
            if sack_fact is not None:
                diagnostics["reconciled_sacks"] += 1
        if penalty is not None and interception_return_penalty is None:
            if credited_sack:
                diagnostics["sacks_with_retained_penalty"] += 1
            run_diagnostics: Counter[str] = Counter()
            if lower.startswith("penalty on "):
                chart = _penalty_chart(play, seed)
                diagnostics["unknown_penalty_play_family"] += 1
                heuristic = False
            else:
                chart, heuristic = (
                    _pass_chart(play, None, seed)
                    if "pass" in lower
                    else (_run_chart(game, play, run_diagnostics), False)
                )
            if chart == "qb_time" or run_diagnostics["heuristic_quarterback_run_family"]:
                # A foul is a primary procedure, never a terminal QT lookup.
                # Only explicit dropback evidence supports a pass-only family.
                if credited_sack or "sacked by" in lower or "scrambl" in lower:
                    chart, heuristic = _pass_chart(play, None, seed)
                else:
                    chart, heuristic = _penalty_chart(play, seed), False
                    diagnostics["unknown_penalty_play_family"] += 1
                diagnostics["supplemental_penalties_as_primary"] += 1
            if heuristic:
                diagnostics["heuristic_pass_depth"] += 1
            if chart:
                outcomes.append(_empirical_play(offense, "offense", chart, penalty[1], play, opponent))
            else:
                diagnostics["unclassified_penalties"] += 1
            continue

        if "no play" in lower:
            diagnostics["nullified_scrimmages"] += 1
            continue

        if fumble_gain_policy is not None and "fumble" in lower and "intercepted by" not in lower:
            kind = ("sack" if sack_fact is not None else
                    fumble_fact.credited_kind if fumble_fact is not None else None)
            unit = "rushing" if kind == "rushing" else "passing" if kind in {"sack", "receiving"} else (
                "passing" if credited_sack or "pass complete" in lower else "rushing")
            lost = _reviewed_fumble_lost(game, play, offense, fumble_fact)
            fumbles.append(FumbleEvent(offense, unit, lost, play.game_id, play.number))
            try:
                projected = _project_reviewed_fumble(
                    game, play, offense, fact, fumble_gain_policy,
                    reconciled_recoveries.get(play.number))
            except ValueError as exc:
                diagnostics["unsupported_fumble_gain_projections"] += 1
                diagnostics["missing_required_gains"] += 1
                unsupported_fields.append({
                    "game_id": play.game_id, "play_number": play.number, "team": offense,
                    "field": "fumble_gain_projection", "reason": str(exc),
                })
                continue
            projections.append(projected)
            kind = projected.originating_kind
            if projected.modeled_class_basis is not None:
                diagnostics["modeled_fumble_classes"] += 1
                diagnostics[f"modeled_fumble_class_{projected.modeled_class_basis}"] += 1
            fumbles[-1] = replace(fumbles[-1], unit="rushing" if kind == "rushing" else "passing",
                                   lost=projected.source_facts.lost)
            if kind in {"sack", "receiving"}:
                chart, heuristic = _pass_chart(play, None, seed)
                diagnostics["heuristic_pass_depth"] += int(heuristic)
                if kind == "sack":
                    outcomes.append(_empirical_play(offense, "offense", chart, "QT", play, opponent))
                    chart = "qb_time"
            else:
                chart = _run_chart(game, play, diagnostics)
                if chart not in {"line_plunge", "off_tackle", "end_run", "draw"}:
                    chart = inferred_rushing_chart(projected.source_facts.source_event_id, seed)
                    diagnostics["inferred_primary_rushing_fumble_family"] += 1
            outcomes.append(_empirical_play(
                offense, "offense", chart, projected.chart_result, play, opponent))
            diagnostics[f"fumble_gain_basis_{projected.modeled_gain_basis}"] += 1
            continue

        if credited_sack:
            # Sack occurrence and known loss yardage are separate source facts.
            # Missing historical yards must not erase a counted sack or invent
            # a supplemental gain for it.
            if "fumble" in lower:
                fumbles.append(
                    FumbleEvent(offense, "passing", _reviewed_fumble_lost(game, play, offense, fumble_fact),
                                play.game_id, play.number)
                )
            sack_yards = sack_fact.initial_gain if sack_fact is not None else _reviewed_initial_gain(play, fumble_fact)
            if sack_yards is None:
                diagnostics["unclassified_sacks"] += 1
                continue
            chart, heuristic = _pass_chart(play, None, seed)
            if heuristic:
                diagnostics["heuristic_pass_depth"] += 1
            outcomes.append(_empirical_play(offense, "offense", chart, "QT", play, opponent))
            qt_result = (_fumble_result(-abs(sack_yards)) if "fumble" in lower else
                         "SACK 0" + ("*" if "out of bounds" in lower else "") if sack_yards == 0
                         else _marked_numeric(-abs(sack_yards), detail))
            outcomes.append(_empirical_play(offense, "offense", "qb_time", qt_result, play, opponent))
            continue

        if "pass" in lower:
            interception = "intercepted by" in lower
            observed_yards = _reviewed_initial_gain(play, fumble_fact) if "complete" in lower else None
            if "fumble" in lower and "complete" in lower and "incomplete" not in lower and not interception:
                fumbles.append(
                    FumbleEvent(offense, "passing", _reviewed_fumble_lost(game, play, offense, fumble_fact),
                                play.game_id, play.number)
                )
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
                event_counts[offense]["interceptions"] += 1
            elif "incomplete" in lower:
                result = "BLACK"
            elif observed_yards is not None:
                if "fumble" in lower:
                    result = _fumble_result(observed_yards)
                else:
                    result = _marked_numeric(observed_yards, detail)
            else:
                diagnostics["unclassified_passes"] += 1
                if "complete" in lower:
                    diagnostics["missing_required_gains"] += 1
                    unsupported_fields.append({"game_id": play.game_id, "play_number": play.number,
                                               "team": offense, "unit": "passing", "field": "initial_gain"})
                continue
            outcomes.append(_empirical_play(offense, "offense", chart, result, play, opponent))
            continue

        run_chart = _run_chart(game, play, diagnostics)
        if run_chart:
            if "fumble" in lower:
                fumbles.append(
                    FumbleEvent(offense, "rushing", _reviewed_fumble_lost(game, play, offense, fumble_fact),
                                play.game_id, play.number)
                )
            run_yards = _reviewed_initial_gain(play, fumble_fact)
            if run_yards is None:
                diagnostics["unclassified_runs"] += 1
                diagnostics["missing_required_gains"] += 1
                unsupported_fields.append({"game_id": play.game_id, "play_number": play.number,
                                           "team": offense, "unit": "rushing", "field": "initial_gain"})
                continue
            if "fumble" in lower:
                run_result = _fumble_result(run_yards)
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

    fumbles, fumble_reconciliations = _reconcile_fumble_box(game, fumbles, diagnostics)
    if reviewed_snap_receipts:
        fumble_reconciliations = (*fumble_reconciliations, *reviewed_snap_receipts)
    if recovery_receipts:
        receipts = {receipt["play_number"]: receipt for receipt in recovery_receipts}
        receipts.update({receipt["play_number"]: receipt for receipt in fumble_reconciliations})
        fumble_reconciliations = tuple(receipts[number] for number in sorted(receipts))
        diagnostics["box_reconciled_fumble_recoveries"] = sum(
            receipt.get("method") == "unique-team-fumble-loss-constraint"
            for receipt in fumble_reconciliations)
    diagnostics["unknown_fumble_recoveries"] += sum(event.lost is None for event in fumbles)
    field_goals, conflicts = _reconcile_field_goal_box(game, field_goals, diagnostics)
    for attempt in field_goals:
        event_counts[attempt.team]["field_goal_attempts"] += 1
    return ClassifiedGame(
        tuple(outcomes), tuple(field_goals), tuple(fumbles), dict(diagnostics), conflicts,
        {team: dict(counts) for team, counts in event_counts.items()},
        tuple(unsupported_fields),
        fumble_reconciliations,
        tuple(projections),
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
    if any(event.lost is None for event in team_fumbles):
        raise ValueError(f"Cannot calibrate {team}: unknown fumble recovery")
    rushing_events = [event for event in team_fumbles if event.unit == "rushing"]
    passing_events = [event for event in team_fumbles if event.unit == "passing"]
    retained_incompletions = [event for event in passing_events if event.retained_incompletion]
    stochastic_passing = [event for event in passing_events if not event.retained_incompletion]

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
            fumbles=len(stochastic_passing),
            fumbles_lost=sum(event.lost for event in stochastic_passing),
            retained_fumble_incompletions=len(retained_incompletions),
        )

    attempts = [attempt for attempt in field_goals if attempt.team == team]
    special_teams = stats.special_teams
    special_teams = replace(special_teams, field_goal_snap_outcomes=tuple(
        event.field_goal_snap_result for event in team_fumbles if event.field_goal_snap_result))
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

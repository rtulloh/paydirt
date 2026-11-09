"""Explicit reviewed fitting scope, never corrections to historical source facts."""
from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pfr_play_by_play import ClassifiedGame, PfrGame

POLICY = "reviewed_historical_source_scope_v1"
_DIAGNOSTICS = {"unreconciled_fumble_box", "unreconciled_field_goal_box"}
_FIELDS = {"schema_version", "policy", "season", "historical_source_complete",
           "excluded_required_events", "reviewed_diagnostics", "known_partial_games"}


def validate_source_scope_disclosure(data: object) -> dict[str, int]:
    """Validate portable, explicitly incomplete scope and derive exact allowances."""
    if (not isinstance(data, dict) or set(data) not in (_FIELDS, _FIELDS | {"reviewed_sack_counts"})
            or type(data.get("schema_version")) is not int or data["schema_version"] != 1
            or data.get("policy") != POLICY
            or type(data.get("season")) is not int or data["season"] < 1920
            or data.get("historical_source_complete") is not False):
        raise ValueError("Reviewed scope requires explicit incomplete historical source disclosure")
    allowances: Counter[str] = Counter()
    schemas = {
        "excluded_required_events": {"game_id", "play_number", "team", "unit", "field",
                                     "raw_game_sha256", "raw_play_sha256", "reason", "scope"},
        "reviewed_diagnostics": {"game_id", "raw_game_sha256", "diagnostic", "count", "reason"},
        "known_partial_games": {"game_id", "raw_game_sha256", "reason"},
    }
    if "reviewed_sack_counts" in data:
        schemas["reviewed_sack_counts"] = {"game_id", "raw_game_sha256", "team", "pbp_sacks", "box_sacks", "reason"}
    total = 0
    for group, fields in schemas.items():
        records = data.get(group)
        if not isinstance(records, list):
            raise TypeError("Reviewed scope inventories must be lists")
        seen = set()
        for record in records:
            if (not isinstance(record, dict) or set(record) != fields
                    or not isinstance(record.get("game_id"), str) or not record["game_id"].strip()
                    or not isinstance(record.get("reason"), str) or not record["reason"].strip()
                    or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("raw_game_sha256")))):
                raise ValueError("Reviewed scope record lacks bound identity or a reason")
            key = (record["game_id"],)
            if group == "excluded_required_events":
                if (type(record["play_number"]) is not int or record["play_number"] < 1
                        or not isinstance(record["team"], str) or not record["team"]
                        or record["unit"] != "rushing" or record["field"] != "initial_gain"
                        or record["scope"] != "fitting_only"
                        or not re.fullmatch(r"[0-9a-f]{64}", str(record["raw_play_sha256"]))):
                    raise ValueError("Reviewed fitting scope supports only bound aborted-snap initial gains")
                key += (record["play_number"],)
                allowances["missing_required_gains"] += 1
            elif group == "reviewed_diagnostics":
                if (record["diagnostic"] not in _DIAGNOSTICS
                        or type(record["count"]) is not int or record["count"] <= 0):
                    raise ValueError("Reviewed scope diagnostic is not an authorized box discrepancy")
                key += (record["diagnostic"],)
                allowances[record["diagnostic"]] += record["count"]
            elif group == "reviewed_sack_counts":
                if (not isinstance(record["team"], str) or not record["team"]
                        or any(type(record[field]) is not int or record[field] < 0
                               for field in ("pbp_sacks", "box_sacks"))
                        or abs(record["pbp_sacks"] - record["box_sacks"]) != 1):
                    raise ValueError("Reviewed sack scope requires exact differing nonnegative counts")
                key += (record["team"],)
            if key in seen:
                raise ValueError(f"Duplicate reviewed scope record: {key}")
            seen.add(key)
            total += 1
    if not total:
        raise ValueError("Reviewed source scope cannot be empty")
    return dict(allowances)


class _SackBoxParser(HTMLParser):
    """Read only complete team sack-credit rows, never derive an absent play."""

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.row: dict[str, str] | None = None
        self.cell: str | None = None
        self.rows: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            self.in_table = attributes.get("id") == "team_stats"
        elif tag == "tr" and self.in_table:
            self.row = {}
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = attributes.get("data-stat")
            if self.cell:
                self.row[self.cell] = ""

    def handle_data(self, text: str) -> None:
        if self.row is not None and self.cell:
            self.row[self.cell] += text

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row.get("stat", "").strip() == "Sacked-Yards":
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.in_table = False


def _sack_box_counts(html: str | None, game: PfrGame) -> dict[str, int]:
    if html is None:
        raise ValueError("Reviewed sack scope requires source team box counts")
    parser = _SackBoxParser()
    parser.feed(re.sub(r"<!--(.*?)-->", lambda match: match.group(1) if "<table" in match.group(1) else "",
                       html, flags=re.DOTALL))
    if len(parser.rows) != 1:
        raise ValueError("Reviewed sack scope requires one complete source team box row")
    values = [parser.rows[0].get(key, "").strip() for key in ("vis_stat", "home_stat")]
    if any(re.fullmatch(r"[0-9]+-[0-9]+", value) is None for value in values):
        raise ValueError("Reviewed sack scope requires complete source sack/loss counts")
    return dict(zip((game.away_team, game.home_team), (int(value.split("-")[0]) for value in values)))


def reviewed_sack_deltas(data: dict) -> dict[str, int]:
    """Return disclosed PBP minus box credit, keeping both source counts intact."""
    validate_source_scope_disclosure(data)
    deltas: Counter[str] = Counter()
    for record in data.get("reviewed_sack_counts", []):
        deltas[record["team"]] += record["pbp_sacks"] - record["box_sacks"]
    return dict(deltas)


class ReviewedSourceScope:
    """Hash-bound decisions applied once without changing strict diagnostics."""

    def __init__(self, path: Path, data: dict) -> None:
        validate_source_scope_disclosure(data)
        self.path = path
        self.season = data["season"]
        self._data = deepcopy(data)
        self._applied: set[tuple[str, int]] = set()

    def review_game(
        self, game: PfrGame, classified: ClassifiedGame, *, raw_sha256: str, raw_html: str | None = None,
    ) -> ClassifiedGame:
        """Return fitting-only fields; caller must retain original strict classification."""
        from .pfr_event_reconciliation import play_fingerprint

        if classified.source_conflicts:
            raise ValueError("Reviewed scope cannot suppress source conflicts")
        excluded = set()
        selected = []
        identity_fields = ("game_id", "play_number", "team", "unit", "field")
        plays = {play.number: play for play in game.plays}
        for group in ("excluded_required_events", "reviewed_diagnostics", "known_partial_games", "reviewed_sack_counts"):
            for index, record in enumerate(self._data.get(group, [])):
                if record["game_id"] != game.game_id:
                    continue
                key = (group, index)
                if key in self._applied:
                    raise ValueError("Reviewed scope record already applied")
                if record["raw_game_sha256"] != raw_sha256:
                    raise ValueError("Reviewed source scope raw game identity differs")
                if group == "excluded_required_events":
                    play = plays.get(record["play_number"])
                    matching = [issue for issue in classified.unsupported_fields if all(
                        issue.get(field) == record[field]
                        for field in identity_fields)]
                    if (play is None or len(matching) != 1
                            or record["team"] not in {game.home_team, game.away_team}
                            or record["raw_play_sha256"] != play_fingerprint(play)
                            or "aborted snap" not in play.detail.casefold()
                            or any(term in play.detail.casefold() for term in
                                   ("fumble", "penalty", "no play", "field goal", "extra point"))
                            or any(event.play_number == play.number for event in classified.plays)):
                        raise ValueError("Reviewed fitting exclusion is not this unresolved aborted snap")
                    excluded.add(tuple(record[field] for field in identity_fields))
                elif group == "reviewed_diagnostics":
                    if classified.diagnostics.get(record["diagnostic"], 0) != record["count"]:
                        raise ValueError("Reviewed scope diagnostic count differs from strict classification")
                    if record["diagnostic"] == "unreconciled_field_goal_box":
                        # Actor-only disagreement cannot waive a missing/extra
                        # team attempt or make. Keep player attribution unknown.
                        if game.field_goal_box is None:
                            raise ValueError("Reviewed field-goal scope requires complete team box counts")
                        box_attempts: Counter[str] = Counter()
                        box_makes: Counter[str] = Counter()
                        for team, attempts, makes in game.field_goal_box.values():
                            box_attempts[team] += attempts
                            box_makes[team] += makes
                        attempts = Counter(attempt.team for attempt in classified.field_goals)
                        makes = Counter(attempt.team for attempt in classified.field_goals if attempt.made)
                        teams = {game.home_team, game.away_team}
                        if (any(team not in teams for team in set(box_attempts) | set(attempts))
                                or any(box_attempts[team] != attempts[team]
                                       or box_makes[team] != makes[team] for team in teams)):
                            raise ValueError("Reviewed field-goal actor scope cannot waive team count differences")
                elif group == "reviewed_sack_counts":
                    box = _sack_box_counts(raw_html, game)
                    if (record["team"] not in box
                            or box[record["team"]] != record["box_sacks"]
                            or classified.event_counts.get(record["team"], {}).get("sacks", 0)
                            != record["pbp_sacks"]):
                        raise ValueError("Reviewed sack scope differs from PBP or credited box counts")
                selected.append(key)
        self._applied.update(selected)
        return replace(classified, unsupported_fields=tuple(
            issue for issue in classified.unsupported_fields
            if tuple(issue.get(field) for field in identity_fields) not in excluded))

    def assert_all_applied(self) -> None:
        """Reject unused decisions, including excluded games/date cutoffs."""
        expected = {(group, index) for group in ("excluded_required_events", "reviewed_diagnostics",
                                                "known_partial_games", "reviewed_sack_counts")
                    for index in range(len(self._data.get(group, [])))}
        if expected != self._applied:
            raise ValueError("Unused reviewed source scope records")

    def disclosure(self) -> dict:
        """Return unchanged portable decisions only after all identities were checked."""
        self.assert_all_applied()
        return deepcopy(self._data)


def load_source_scope(path: Path) -> ReviewedSourceScope:
    """Load explicit reviewed modeled scope; strict generation never opts in implicitly."""
    return ReviewedSourceScope(path, json.loads(path.read_text(encoding="utf-8")))

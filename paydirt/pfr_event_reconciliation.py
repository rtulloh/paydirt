"""Bind reviewed primary-source facts to unchanged historical PFR events.

File identity and typed consistency are verified here. Reading a scan and
reviewing the facts remain external source-review work, not software attestation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from .pfr_play_by_play import PfrGame, PfrPlay


def play_fingerprint(play: PfrPlay) -> str:
    """Hash all parsed event fields, including original text and game context."""
    content = json.dumps(asdict(play), sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(content.encode()).hexdigest()


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class SourceEvidence:
    """One reviewed source document and its portable byte/page identity."""

    file: str
    sha256: str
    url: str
    pages: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the exact portable JSON evidence representation."""
        return {
            "file": self.file,
            "sha256": self.sha256,
            "url": self.url,
            "pages": list(self.pages),
        }


@dataclass(frozen=True)
class SackEventFact:
    """Credited sack loss and physical initial gain are independent facts."""

    game_id: str
    play_number: int
    raw_game_sha256: str
    raw_play_sha256: str
    credited_sack: bool
    credited_sack_loss: int | None
    initial_gain: int | None
    evidence: tuple[SourceEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        """Return reviewed input facts without inserting modeled severity."""
        return {
            "game_id": self.game_id,
            "play_number": self.play_number,
            "raw_game_sha256": self.raw_game_sha256,
            "raw_play_sha256": self.raw_play_sha256,
            "credited_sack": self.credited_sack,
            "credited_sack_loss": self.credited_sack_loss,
            "initial_gain": self.initial_gain,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class FumbleEventFact:
    """Reviewed ownership, credit, and separately reviewed physical movement."""

    game_id: str
    play_number: int
    raw_game_sha256: str
    raw_play_sha256: str
    evidence: tuple[SourceEvidence, ...]
    fumble_lost: bool
    out_of_bounds: bool
    initial_gain: int | None = None
    initial_gain_reviewed: bool = False
    credited_kind: str | None = None
    credited_yards: int | None = None
    loose_ball_yards: int | None = None
    recovery_advance_yards: int | None = None
    loose_ball_yards_reviewed: bool = False
    recovery_advance_yards_reviewed: bool = False
    originating_kind: str | None = None
    originating_player_id: str | None = None
    originating_team: str | None = None
    reported_primary_yards: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Keep absent movement review distinct from reviewed unknown movement."""
        record = {
            "kind": "fumble", **_identity_dict(self),
            "fumble_lost": self.fumble_lost, "out_of_bounds": self.out_of_bounds,
        }
        if self.initial_gain_reviewed:
            record["initial_gain"] = self.initial_gain
        if self.credited_kind is not None or self.originating_kind is not None:
            record.update(credited_kind=self.credited_kind, credited_yards=self.credited_yards)
        if self.originating_kind is not None:
            record["originating_kind"] = self.originating_kind
        if self.originating_player_id is not None:
            record.update(originating_player_id=self.originating_player_id,
                          originating_team=self.originating_team)
        if self.reported_primary_yards is not None:
            record["reported_primary_yards"] = self.reported_primary_yards
        for field in ("loose_ball_yards", "recovery_advance_yards"):
            if getattr(self, f"{field}_reviewed"):
                record[field] = getattr(self, field)
        return record


@dataclass(frozen=True)
class PrepassFumbleFact:
    """One own-recovered fumble followed by an incompletion on the same snap."""

    game_id: str
    play_number: int
    raw_game_sha256: str
    raw_play_sha256: str
    evidence: tuple[SourceEvidence, ...]
    continuation_play_number: int
    continuation_play_sha256: str

    def to_dict(self) -> dict[str, object]:
        """Retain identities of both raw rows rather than rewriting either."""
        return {
            "kind": "prepass_fumble", **_identity_dict(self),
            "continuation_play_number": self.continuation_play_number,
            "continuation_play_sha256": self.continuation_play_sha256,
        }


@dataclass(frozen=True)
class AbortedFieldGoalFact:
    """A reviewed no-kick snap, with actor, credit and movement kept separate."""

    game_id: str
    play_number: int
    raw_game_sha256: str
    raw_play_sha256: str
    evidence: tuple[SourceEvidence, ...]
    offense_team: str
    fumbling_player_id: str
    recovering_team: str | None
    individual_lost: bool | None
    credited_player_id: str | None
    credited_rushing_yards: int | None
    physical_initial_yards: int | None

    def to_dict(self) -> dict[str, object]:
        """Serialize nullable support without converting it into chart movement."""
        return {
            "kind": "aborted_field_goal", **_identity_dict(self),
            **{name: getattr(self, name) for name in (
                "offense_team", "fumbling_player_id", "recovering_team", "individual_lost",
                "credited_player_id", "credited_rushing_yards", "physical_initial_yards")},
        }


EventFact = SackEventFact | FumbleEventFact | PrepassFumbleFact | AbortedFieldGoalFact


def _identity_dict(fact: EventFact) -> dict[str, object]:
    return {
        "game_id": fact.game_id, "play_number": fact.play_number,
        "raw_game_sha256": fact.raw_game_sha256, "raw_play_sha256": fact.raw_play_sha256,
        "evidence": [item.to_dict() for item in fact.evidence],
    }


def _validate_fumble_context(game: PfrGame, play: PfrPlay, fact: FumbleEventFact) -> None:
    """Refuse incompatible claims; unresolved source conflicts need review."""
    from .pfr_play_by_play import _first_actor_team, _recovery_team, _yards

    lower = play.detail.casefold()
    if "fumble" not in lower or any(
        marker in lower for marker in (
            "punts", "kicks off", "field goal", "extra point", "incomplete", "(accepted)",
        )
    ):
        raise ValueError("Fumble facts require a retained offensive fumble")
    offense = _first_actor_team(game, play, None)
    if fact.originating_player_id is not None:
        from .pfr_fumble_source import _actor_prefix

        actor_detail = lower.removeprefix("returned by ") if fact.originating_kind in {
            "kickoff_return", "punt_return"} else lower
        _, actor, body = _actor_prefix(game, actor_detail)
        if body.startswith("pass complete to "):
            _, actor, _ = _actor_prefix(game, body.removeprefix("pass complete to "))
        if (actor != fact.originating_player_id or actor not in play.player_ids
                or fact.originating_team not in {game.home_team, game.away_team}
                or game.player_teams.get(actor) not in {None, fact.originating_team}):
            raise ValueError("Reviewed originating actor/team conflicts with source identity")
        offense = fact.originating_team
    recovery = _recovery_team(game, play, offense) if offense else None
    gain = _yards(play.detail)
    if (
        not offense
        or (recovery is not None and fact.fumble_lost != (recovery != offense))
        or (fact.initial_gain_reviewed and fact.initial_gain is not None
            and gain is not None and fact.initial_gain != gain)
        or ("out of bounds" in lower and not fact.out_of_bounds)
    ):
        raise ValueError("Reviewed fumble facts conflict with known source facts")
    if fact.originating_kind is not None:
        from .pfr_fumble_source import extract_reported_primary_gain

        if (("sacked by" in lower and fact.originating_kind != "sack")
                or ("pass complete" in lower and fact.originating_kind != "receiving")):
            raise ValueError("Reviewed originating class conflicts with source context")
        try:
            reported = extract_reported_primary_gain(game, play, offense)
        except ValueError:
            reported = None
        if reported is not None and reported.kind != fact.originating_kind:
            raise ValueError("Reviewed originating class conflicts with reported event class")
        if reported is None and fact.reported_primary_yards is not None:
            try:
                reported = extract_reported_primary_gain(
                    game, play, offense, reviewed_kind=fact.originating_kind,
                    reviewed_actor=fact.originating_player_id)
            except ValueError:
                pass  # Malformed/absent raw number is precisely this review's scope.
        if (reported is not None and fact.reported_primary_yards is not None
                and reported.yards != fact.reported_primary_yards):
            raise ValueError("Reviewed reported primary gain conflicts with supported raw reported gain")
    if fact.reported_primary_yards is not None:
        names = [name.casefold() for name, actor in game.player_names.items()
                 if actor == fact.originating_player_id]
        if (len(re.findall(r"\bfumbles?\b", lower)) != 1
                or not any(re.search(r"\b" + re.escape(name) + r" fumbles?\b", lower)
                           for name in names)
                or any(term in lower for term in ("lateral", "reverse", "intercept"))):
            raise ValueError("Reviewed reported gain requires one same-actor primary fumble")


def _validate_prepass_context(game: PfrGame, fact: PrepassFumbleFact) -> None:
    plays = {play.number: play for play in game.plays}
    first = plays[fact.play_number]
    following = plays.get(fact.continuation_play_number)
    index = game.plays.index(first)
    actor_names = {name.casefold() for name, player_id in game.player_names.items()
                   if first.player_ids and player_id == first.player_ids[0]}
    if (
        following is None
        or index + 1 >= len(game.plays)
        or game.plays[index + 1] != following
        or fact.continuation_play_sha256 != play_fingerprint(following)
        or following.game_id != game.game_id
        or not first.player_ids
        or not following.player_ids
        or first.player_ids[0] != following.player_ids[0]
        or any(getattr(first, field) is None for field in ("quarter", "down", "yards_to_go"))
        or not first.location
        or any(getattr(first, field) != getattr(following, field)
               for field in ("quarter", "time_remaining", "down", "yards_to_go", "location"))
        or first.detail.casefold().removesuffix(".") not in {f"{name} fumbles" for name in actor_names}
        or "pass incomplete" not in following.detail.casefold()
        or any(marker in following.detail.casefold()
               for marker in ("fumble", "no play", "offsetting", "(offset)", "penalty", "sacked"))
    ):
        raise ValueError("Prepass fumble requires two bound rows from one unambiguous snap")


def _validate_aborted_field_goal_context(
    game: PfrGame, play: PfrPlay, fact: AbortedFieldGoalFact,
) -> None:
    """Reject invented teams/actors and erasure of an independently credited kick."""
    from .pfr_play_by_play import _FIELD_GOAL, _first_actor_team

    match = _FIELD_GOAL.search(play.detail)
    if (match is None or match.group(2).casefold() != "no good"
            or fact.offense_team not in {game.home_team, game.away_team}
            or _first_actor_team(game, play, None) not in {None, fact.offense_team}
            or fact.fumbling_player_id not in play.player_ids
            or game.player_teams.get(fact.fumbling_player_id) not in {None, fact.offense_team}
            or fact.recovering_team not in {None, game.home_team, game.away_team}
            or (fact.credited_player_id is not None
                and game.player_teams.get(fact.credited_player_id) != fact.offense_team)
            or (game.field_goal_box is not None and any(
                game.field_goal_box.get(actor, (None, 0, 0))[1] > 0
                for actor in play.player_ids[:1]))):
        raise ValueError("Aborted field-goal facts conflict with source context or official attempt credit")


class EventReconciliations:
    """Validated input inventory, requiring every record to be used once."""

    def __init__(self, facts: tuple[EventFact, ...], input_paths: tuple[Path, ...],
                 schema_version: int = 1) -> None:
        self.facts = facts
        self.input_paths = input_paths
        self.schema_version = schema_version
        self._applied: set[tuple[str, int]] = set()

    def for_game(self, game: PfrGame, raw_sha256: str) -> dict[int, EventFact]:
        """Validate source identity/eligibility before returning this game's facts."""
        selected = [fact for fact in self.facts if fact.game_id == game.game_id]
        plays = {play.number: play for play in game.plays}
        if selected and len(plays) != len(game.plays):
            raise ValueError(f"Duplicate source play numbers in {game.game_id}")
        occupied: set[int] = set()
        for fact in selected:
            key = (fact.game_id, fact.play_number)
            if key in self._applied:
                raise ValueError(f"Event reconciliation already applied: {key}")
            play = plays.get(fact.play_number)
            if (
                fact.raw_game_sha256 != raw_sha256
                or play is None
                or play.game_id != game.game_id
                or fact.raw_play_sha256 != play_fingerprint(play)
            ):
                raise ValueError(f"Event reconciliation source identity differs: {key}")
            if any(marker in play.detail.casefold() for marker in ("no play", "offsetting", "(offset)")):
                raise ValueError(f"Event reconciliation cannot credit a nullified play: {key}")
            covered = {fact.play_number}
            if isinstance(fact, FumbleEventFact):
                _validate_fumble_context(game, play, fact)
            elif isinstance(fact, PrepassFumbleFact):
                _validate_prepass_context(game, fact)
                covered.add(fact.continuation_play_number)
            elif isinstance(fact, AbortedFieldGoalFact):
                _validate_aborted_field_goal_context(game, play, fact)
            if occupied & covered:
                raise ValueError(f"Overlapping event reconciliations: {key}")
            occupied.update(covered)
        self._applied.update((fact.game_id, fact.play_number) for fact in selected)
        return {fact.play_number: fact for fact in selected}

    def assert_all_applied(self) -> None:
        """Reject records outside the selected source inventory/date cutoff."""
        unused = {(fact.game_id, fact.play_number) for fact in self.facts} - self._applied
        if unused:
            raise ValueError(f"Unused event reconciliations: {sorted(unused)}")


def load_event_reconciliations(path: Path) -> EventReconciliations:
    """Load strictly typed reviewed facts and verify every evidence file's bytes.

    Args:
        path: JSON sidecar; evidence files use paths relative to its directory.

    Returns:
        A complete event/input inventory that must be applied before generation.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("kind") == "ordered_event_reconciliation_sources":
        from .pfr_reconciliation_replay import load_reconciliation_replay

        return load_reconciliation_replay(path)
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "events"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] not in {1, 2, 3, 4, 5}
        or not isinstance(data["events"], list)
        or not data["events"]
    ):
        raise ValueError("Expected nonempty schema-version-1-through-5 event reconciliations")
    facts = []
    input_paths = {path}
    keys = set()
    identity_fields = {
        "game_id",
        "play_number",
        "raw_game_sha256",
        "raw_play_sha256",
        "evidence",
    }
    for record in data["events"]:
        if not isinstance(record, dict) or not record:
            raise ValueError("Unexpected event reconciliation fields")
        kind = record.get("kind", "sack")
        fields = identity_fields | {"credited_sack", "credited_sack_loss", "initial_gain"}
        if kind == "fumble" and data["schema_version"] >= 2:
            fields = identity_fields | {"kind", "fumble_lost", "out_of_bounds"}
            if "initial_gain" in record:
                fields.add("initial_gain")
            if data["schema_version"] >= 3:
                fields |= {"credited_kind", "credited_yards"}
                fields |= {"loose_ball_yards", "recovery_advance_yards"} & record.keys()
            if data["schema_version"] >= 4:
                fields |= {"originating_kind"} & record.keys()
                fields |= {"originating_player_id", "originating_team"} & record.keys()
            if data["schema_version"] >= 5:
                fields |= {"reported_primary_yards"} & record.keys()
        elif kind == "prepass_fumble" and data["schema_version"] >= 2:
            fields = identity_fields | {"kind", "continuation_play_number", "continuation_play_sha256"}
        elif kind == "aborted_field_goal" and data["schema_version"] >= 4:
            fields = identity_fields | {
                "kind", "offense_team", "fumbling_player_id", "recovering_team", "individual_lost",
                "credited_player_id", "credited_rushing_yards", "physical_initial_yards",
            }
        elif kind != "sack":
            raise ValueError("Unsupported event reconciliation kind or schema")
        if set(record) != fields:
            raise ValueError("Unexpected event reconciliation fields")
        if (
            not isinstance(record["game_id"], str)
            or not record["game_id"].strip()
            or type(record["play_number"]) is not int
            or record["play_number"] < 1
            or not _hash(record["raw_game_sha256"])
            or not _hash(record["raw_play_sha256"])
        ):
            raise ValueError("Invalid event identity")
        initial = record.get("initial_gain")
        if initial is not None and type(initial) is not int:
            raise ValueError("Physical initial gain must be an integer or unknown")
        if kind == "sack":
            loss = record["credited_sack_loss"]
            if (record["credited_sack"] is not True
                or (loss is not None and (type(loss) is not int or loss < 0))
                or (initial is not None and initial > 0)):
                raise ValueError("Credited loss and physical initial gain require separate valid values")
        elif kind == "fumble":
            if (type(record["fumble_lost"]) is not bool
                or type(record["out_of_bounds"]) is not bool
                or (record["fumble_lost"] and record["out_of_bounds"])):
                raise ValueError("Fumble recovery and out-of-bounds facts conflict or have invalid types")
            if data["schema_version"] >= 3:
                class_only = (data["schema_version"] >= 4
                              and record.get("originating_kind") in {
                                  "rushing", "sack", "receiving", "kickoff_return", "punt_return"}
                              and record["credited_kind"] is None and record["credited_yards"] is None)
                if not class_only and (
                    record["credited_kind"] not in {"rushing", "sack", "receiving"}
                    or type(record["credited_yards"]) is not int
                    or record["credited_kind"] == "sack" and record["credited_yards"] > 0
                ):
                    raise ValueError("Reviewed credit requires a known class and valid integer yards")
                if "originating_kind" in record and (
                    record["originating_kind"] not in {
                        "rushing", "sack", "receiving", "kickoff_return", "punt_return"}
                    or record["credited_kind"] not in {None, record["originating_kind"]}
                ):
                    raise ValueError("Reviewed originating class is unsupported or conflicts with credit")
                if {"originating_player_id", "originating_team"} & record.keys() and (
                    any(not isinstance(record.get(name), str) or not record[name].strip()
                        for name in ("originating_player_id", "originating_team"))
                ):
                    raise ValueError("Reviewed originating actor and team require a complete typed pair")
                if record.get("originating_kind") in {"kickoff_return", "punt_return"} and (
                        not record.get("originating_player_id") or not record.get("originating_team")):
                    raise ValueError("Reviewed standalone return requires exact actor/team support")
                if "reported_primary_yards" in record and (
                    type(record["reported_primary_yards"]) is not int
                    or record.get("originating_kind") not in {"rushing", "sack", "receiving"}
                    or not record.get("originating_player_id") or not record.get("originating_team")
                    or (record["originating_kind"] == "sack" and record["reported_primary_yards"] > 0)
                ):
                    raise ValueError("Reviewed reported gain requires primary class, actor/team and signed integer")
            for field in ("loose_ball_yards", "recovery_advance_yards"):
                if record.get(field) is not None and type(record[field]) is not int:
                    raise ValueError("Reviewed fumble movement must be an integer or unknown")
        elif kind == "aborted_field_goal":
            if (any(not isinstance(record[name], str) or not record[name].strip()
                    for name in ("offense_team", "fumbling_player_id"))
                    or any(record[name] is not None and (
                        not isinstance(record[name], str) or not record[name].strip())
                           for name in ("recovering_team", "credited_player_id"))
                    or (record["individual_lost"] is not None
                        and type(record["individual_lost"]) is not bool)
                    or any(record[name] is not None and type(record[name]) is not int
                           for name in ("credited_rushing_yards", "physical_initial_yards"))
                    or ((record["credited_player_id"] is None)
                        != (record["credited_rushing_yards"] is None))
                    or (record["recovering_team"] is not None and record["individual_lost"] is not None
                        and record["individual_lost"] != (
                            record["recovering_team"] != record["offense_team"]))):
                raise ValueError("Invalid or contradictory aborted field-goal facts")
        elif (type(record["continuation_play_number"]) is not int
              or record["continuation_play_number"] < 1
              or record["continuation_play_number"] == record["play_number"]
              or not _hash(record["continuation_play_sha256"])):
            raise ValueError("Invalid prepass continuation identity")
        key = (record["game_id"], record["play_number"])
        if key in keys:
            raise ValueError(f"Duplicate event reconciliation: {key}")
        keys.add(key)
        if not isinstance(record["evidence"], list) or not record["evidence"]:
            raise ValueError("Every reconciliation requires reviewed source evidence")
        evidence = []
        for item in record["evidence"]:
            if not isinstance(item, dict) or set(item) != {"file", "sha256", "url", "pages"}:
                raise ValueError("Unexpected source evidence fields")
            name, url, pages = item["file"], item["url"], item["pages"]
            if (
                not isinstance(name, str)
                or not name
                or Path(name).is_absolute()
                or ".." in Path(name).parts
                or not _hash(item["sha256"])
                or not isinstance(url, str)
            ):
                raise ValueError("Evidence requires a relative file, SHA-256 and HTTPS source URL")
            parsed_url = urlsplit(url)
            if (
                parsed_url.scheme != "https"
                or not parsed_url.hostname
                or parsed_url.username
                or parsed_url.password
                or not isinstance(pages, list)
                or not pages
                or any(type(page) is not int or page < 1 for page in pages)
                or len(set(pages)) != len(pages)
            ):
                raise ValueError("Invalid evidence URL or reviewed page numbers")
            source_path = path.parent / name
            if (
                not source_path.is_file()
                or hashlib.sha256(source_path.read_bytes()).hexdigest() != item["sha256"]
            ):
                raise ValueError(f"Evidence bytes differ: {name}")
            input_paths.add(source_path)
            evidence.append(SourceEvidence(name, item["sha256"], url, tuple(pages)))
        if kind == "sack":
            fact = SackEventFact(
                record["game_id"],
                record["play_number"],
                record["raw_game_sha256"],
                record["raw_play_sha256"],
                True,
                loss,
                initial,
                tuple(evidence),
            )
        elif kind == "fumble":
            fact = FumbleEventFact(
                record["game_id"], record["play_number"], record["raw_game_sha256"],
                record["raw_play_sha256"], tuple(evidence), record["fumble_lost"],
                record["out_of_bounds"], initial, "initial_gain" in record,
                record.get("credited_kind"), record.get("credited_yards"),
                record.get("loose_ball_yards"), record.get("recovery_advance_yards"),
                "loose_ball_yards" in record, "recovery_advance_yards" in record,
                record.get("originating_kind"),
                record.get("originating_player_id"), record.get("originating_team"),
                record.get("reported_primary_yards"),
            )
        elif kind == "prepass_fumble":
            fact = PrepassFumbleFact(
                record["game_id"], record["play_number"], record["raw_game_sha256"],
                record["raw_play_sha256"], tuple(evidence), record["continuation_play_number"],
                record["continuation_play_sha256"],
            )
        else:
            fact = AbortedFieldGoalFact(
                record["game_id"], record["play_number"], record["raw_game_sha256"],
                record["raw_play_sha256"], tuple(evidence), record["offense_team"],
                record["fumbling_player_id"], record["recovering_team"], record["individual_lost"],
                record["credited_player_id"], record["credited_rushing_yards"],
                record["physical_initial_yards"],
            )
        facts.append(fact)
    return EventReconciliations(tuple(facts), tuple(sorted(input_paths)), data["schema_version"])

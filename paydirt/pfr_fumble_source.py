"""Strict reported primary-fumble grammar, separate from verified credit/physics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pfr_play_by_play import PfrGame, PfrPlay


@dataclass(frozen=True)
class ReportedPrimaryGain:
    """An actor-bound number from the complete primary clause before a fumble."""

    kind: str
    yards: int
    actor: str
    team: str
    clause: str


def extract_reported_return_gain(
    game: PfrGame, play: PfrPlay, offense: str, *, reviewed_kind: str,
    reviewed_actor: str,
) -> ReportedPrimaryGain:
    """Read one standalone named return; its kick family needs independent review."""
    detail = play.detail.casefold().strip()
    if (reviewed_kind not in {"kickoff_return", "punt_return"}
            or not detail.startswith("returned by ")
            or len(re.findall(r"\bfumbles?\b", detail)) != 1):
        raise ValueError("Reported return requires a reviewed kick family and one return fumble")
    name, actor, body = _actor_prefix(game, detail.removeprefix("returned by "))
    if (actor != reviewed_actor or actor not in play.player_ids
            or game.player_teams.get(actor) not in {None, offense}):
        raise ValueError("Reported return actor/team conflicts with reviewed identity")
    match = re.match(r"for (?P<yards>-?\d+) yards?\.\s+"
                     + re.escape(name) + r" fumbles\b", body)
    if match is None:
        raise ValueError("Reported return requires a scoped gain and the same fumbler")
    return ReportedPrimaryGain(reviewed_kind, int(match["yards"]), actor, offense,
                               play.detail[:detail.index(" fumbles")].strip())


def _actor_prefix(game: PfrGame, text: str) -> tuple[str, str, str]:
    for name, actor in sorted(game.player_names.items(), key=lambda item: (-len(item[0]), item[0])):
        if text.startswith(name.casefold() + " "):
            return name.casefold(), actor, text[len(name) + 1:]
    raise ValueError("Reported primary clause requires an identified actor")


def extract_reported_primary_gain(
    game: PfrGame, play: PfrPlay, offense: str, *, reviewed_kind: str | None = None,
    reviewed_actor: str | None = None,
) -> ReportedPrimaryGain:
    """Accept a complete run, reception or sack clause with the same fumbler.

    Numbers in return/recovery clauses, bare exchange prose, laterals, compound
    fumbles and malformed reordered descriptions remain unsupported. This
    extracts a reported number, not an official individual credit or contact spot.
    """
    detail = play.detail.casefold().strip()
    if len(re.findall(r"\bfumbles?\b", detail)) != 1 or any(
        term in detail for term in ("lateral", "reverse", "intercept", "punt", "kick", "no play")
    ):
        raise ValueError("Reported fumble gain requires one unambiguous offensive primary event")
    name, actor, body = _actor_prefix(game, detail)
    actor_team = game.player_teams.get(actor)
    if (actor not in play.player_ids or (actor_team != offense and not (
            actor == reviewed_actor and actor_team is None))):
        raise ValueError("Reported primary actor/team conflicts with original offense")
    if reviewed_kind not in {None, "rushing", "receiving", "sack"}:
        raise ValueError("Reported primary gain has an unsupported reviewed originating class")
    kind = "rushing"
    if reviewed_kind is not None and body.startswith("for "):
        # Independent class evidence fills only this field. The same strict
        # actor-bound clause must still supply the primary number and fumbler.
        kind = reviewed_kind
    elif body.startswith("pass complete to "):
        name, actor, body = _actor_prefix(game, body.removeprefix("pass complete to "))
        actor_team = game.player_teams.get(actor)
        if (actor not in play.player_ids or (actor_team != offense and not (
                actor == reviewed_actor and actor_team is None))):
            raise ValueError("Reported receiver/team conflicts with original offense")
        kind = "receiving"
    elif body.startswith("sacked by "):
        defenders, separator, body = body.removeprefix("sacked by ").partition(" for ")
        if not separator:
            raise ValueError("Reported sack loss requires a complete defender/loss clause")
        for defender in defenders.split(" and "):
            identity = game.player_names.get(defender)
            if identity is None or game.player_teams.get(identity) in (None, offense):
                raise ValueError("Reported sack defender association is ambiguous")
        body = "for " + body
        kind = "sack"
    else:
        direction = re.match(
            r"(?:left(?: (?:end|tackle|guard))?|right(?: (?:end|tackle|guard))?|"
            r"middle|up the middle|scrambles(?: (?:left|right|middle|up the middle))?) ", body)
        if direction is None:
            raise ValueError("Reported rushing class needs explicit run action/direction")
        body = body[direction.end():]
    if reviewed_kind is not None and kind != reviewed_kind:
        raise ValueError("Reported event class conflicts with independently reviewed class")
    gain = re.match(
        r"for (?P<yards>-?\d+) yards?(?:, touchdown)?\.\s+"
        + re.escape(name) + r" fumbles\b", body)
    zero = re.match(r"for no gain\.\s+" + re.escape(name) + r" fumbles\b", body)
    if gain is None and zero is None:
        raise ValueError("Reported primary gain/fumbler association is incomplete or ambiguous")
    yards = int(gain["yards"]) if gain is not None else 0
    if kind == "sack":
        yards = -abs(yards)
    boundary = re.search(re.escape(name) + r" fumbles\b", detail)
    assert boundary is not None
    return ReportedPrimaryGain(kind, yards, actor, offense, play.detail[:boundary.start()].strip())

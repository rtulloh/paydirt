"""Lossless ordered nflverse fumble evidence, independent of chart fitting."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace

from .fumble_source import source_record_hash, validate_fumble_gain_policy


@dataclass(frozen=True)
class SourceFumbleOccurrence:
    """One occurrence; possession change is separate from individual lost credit."""

    source_event_id: str
    ordinal: int
    fumbling_team: str | None
    fumbling_player_id: str | None
    fumbling_player_name: str | None
    recovering_team: str | None
    recovering_player_id: str | None
    recovering_player_name: str | None
    terminal: str
    possession_changed: bool | None
    individual_lost: bool | None
    identity_basis: str
    physical_initial_yards: int | None = None


@dataclass(frozen=True)
class SourceRecoverySegment:
    """A scoped advance, preserving provider recovery credit without equating it."""

    entry_reason: str
    after_event: int | None
    team: str | None
    player_id: str | None
    player_name: str | None
    reported_yards: int | None
    provider_recovery_yards: int | None
    ends_in_fumble: int | None
    detail: str


@dataclass(frozen=True)
class FumbleLossReview:
    """An individual loss correction bound to one raw event and evidence page."""

    raw_play_sha256: str
    ordinal: int
    fumbling_team: str
    fumbling_player_id: str
    lost: bool
    evidence_sha256: str
    evidence_page: int


@dataclass(frozen=True)
class FumbleSourceLedger:
    """One originating play plus ordered conditional events and nullable facts."""

    source_event_id: str
    raw_play_sha256: str
    raw_values: tuple[tuple[str, object], ...]
    raw_description: str
    final_description: str
    origin: str
    retained: bool
    statistical_kind: str | None
    statistical_yards: int | None
    row_lost: bool | None
    events: tuple[SourceFumbleOccurrence, ...]
    segments: tuple[SourceRecoverySegment, ...]
    muff_actions: int
    unsupported: tuple[str, ...]
    statistical_player_id: str | None = None
    statistical_player_name: str | None = None
    loss_reviews: tuple[FumbleLossReview, ...] = ()


def _text(row: Mapping[str, object], name: str) -> str:
    value = row.get(name)
    text = "" if value is None else str(value).strip()
    return "" if text.casefold() in {"na", "nan", "none"} else text


def _integer(row: Mapping[str, object], name: str) -> int | None:
    try:
        number = float(_text(row, name))
    except ValueError:
        return None
    return int(number) if math.isfinite(number) and number.is_integer() else None


def _boolean(row: Mapping[str, object], name: str) -> bool | None:
    text = _text(row, name).casefold()
    if text in {"true", "yes", "1", "1.0"}:
        return True
    if text in {"false", "no", "0", "0.0"}:
        return False
    return None


def _identity(row: Mapping[str, object], prefix: str) -> tuple[str | None, str | None, str | None]:
    return tuple(_text(row, f"{prefix}_{key}") or None for key in ("team", "player_id", "player_name"))


def _narrative_recovery(description: str) -> tuple[str, str] | None:
    match = re.search(
        r"(?i:\brecovered by)\s+([A-Z]{2,3})-(?:\d+-)?"
        r"([A-Z][\w'-]*(?:\.[A-Z][\w'-]*)*(?:\s+[A-Z][\w'-]*)*)",
        description,
    )
    return (match.group(1).upper(), match.group(2).rstrip(".")) if match else None


def _advance(description: str, name: str | None) -> int | None:
    """Read only a named actor's direct advance clause within this segment."""
    if not name:
        return None
    pattern = (
        rf"(?<![\w.])(?:\d+-)?{re.escape(name)}"
        r"(?:\s+to\s+(?:[A-Z]{2,3}\s+-?\d+|50))?\s+for\s+(-?\d+)\s+yards?\b"
    )
    values = re.findall(pattern, description, re.IGNORECASE)
    return int(values[0]) if len(values) == 1 else None


def _origin(row: Mapping[str, object], description: str) -> str:
    for flag, origin in (
        ("punt_blocked", "blocked_punt"), ("field_goal_blocked", "blocked_field_goal"),
        ("extra_point_blocked", "blocked_extra_point"),
    ):
        if _boolean(row, flag):
            return origin
    if _text(row, "field_goal_result").casefold() == "blocked":
        return "blocked_field_goal"
    if _text(row, "extra_point_result").casefold() == "blocked":
        return "blocked_extra_point"
    if "punt formation" in description.casefold() and "abort" in description.casefold():
        return "punt_snap"
    if _boolean(row, "interception"):
        return "interception"
    play_type = _text(row, "play_type").casefold()
    if play_type in {"kickoff", "punt"}:
        return "kickoff_return" if play_type == "kickoff" else "punt_return"
    for flag, origin in (
        ("sack", "sack"), ("incomplete_pass", "retained_incompletion"),
        ("complete_pass", "receiving"), ("rush_attempt", "rushing"),
    ):
        if _boolean(row, flag):
            return origin
    return "unknown"


def build_fumble_ledger(row: Mapping[str, object], fallback_number: int = 0) -> FumbleSourceLedger:
    """Preserve ordered source evidence without authorizing numeric projection.

    Args:
        row: One unmodified provider record.
        fallback_number: Stable caller position when the provider has no play ID.

    Returns:
        One diagnostic ledger, including unresolved facts and contradictions.
    """
    raw = _text(row, "desc")
    final = re.split(r"(?:and )?the play was REVERSED\.", raw, flags=re.IGNORECASE)[-1].strip()
    actions = tuple(re.finditer(r"\bfumbles\b", final, re.IGNORECASE))
    second = _identity(row, "fumbled_2")
    second_recovery = _identity(row, "fumble_recovery_2")
    count = max(len(actions), 2 if any(second) or any(second_recovery) else
                1 if _boolean(row, "fumble") else 0)
    play_number = _integer(row, "play_id")
    event_id = f"{_text(row, 'game_id')}:{fallback_number if play_number is None else play_number}"
    retained = bool(_boolean(row, "fumble")) and _text(row, "play_type") != "no_play" and not (
        _boolean(row, "penalty") and "offsetting" in final.casefold())
    row_lost = _boolean(row, "fumble_lost")
    origin = _origin(row, final)
    events: list[SourceFumbleOccurrence] = []
    segments: list[SourceRecoverySegment] = []
    unsupported: list[str] = []
    if len(actions) != count:
        unsupported.append("structured and final-narrative fumble counts differ")
    if not _text(row, "game_id"):
        unsupported.append("missing source game identity")
    if origin in {"interception", "kickoff_return", "punt_return",
                  "blocked_punt", "blocked_field_goal", "blocked_extra_point"}:
        first_identity = _identity(row, "fumbled_1")
        before = final[:actions[0].start()] if actions else final
        if not any(first_identity):
            recovery = _narrative_recovery(before)
            if recovery:
                first_identity = (recovery[0], None, recovery[1])
        segments.append(SourceRecoverySegment(
            origin, None, *first_identity, _advance(before, first_identity[2]), None,
            1 if actions else None, before))
    for index in range(count):
        ordinal = index + 1
        actor = _identity(row, f"fumbled_{ordinal}")
        basis = "provider_identity"
        before = final[actions[index - 1].end():actions[index].start()] if 0 < index < len(actions) else ""
        if index and not any(actor) and events:
            previous = events[-1]
            previous_actor = (previous.recovering_team, previous.recovering_player_id,
                              previous.recovering_player_name)
            if all(previous_actor) and _advance(before, previous_actor[2]) is not None:
                actor, basis = previous_actor, "explicit_recovery_advance"
        if not actor[0] or not actor[1]:
            unsupported.append(f"missing {'second fumbler' if ordinal == 2 else 'fumbler'} identity at {ordinal}")
        start = actions[index].end() if index < len(actions) else len(final)
        end = actions[index + 1].start() if index + 1 < len(actions) else len(final)
        detail = final[start:end]
        recovery = _identity(row, f"fumble_recovery_{ordinal}")
        narrative_recovery = _narrative_recovery(detail)
        recovery_conflict = False
        if narrative_recovery:
            team, name = narrative_recovery
            if recovery[0] and team != recovery[0]:
                recovery_conflict = True
                unsupported.append(f"recovery team conflicts with scoped narrative at {ordinal}")
            elif not recovery[0]:
                recovery = (team, recovery[1], recovery[2])
            if recovery[2] and name.casefold() != recovery[2].casefold():
                recovery_conflict = True
                unsupported.append(f"recovery actor conflicts with scoped narrative at {ordinal}")
            elif not recovery[2]:
                recovery = (recovery[0], recovery[1], name)
        out = "out of bounds" in detail.casefold()
        terminal = "out_of_bounds" if out else "recovered" if recovery[0] else "unknown"
        if terminal == "unknown":
            unsupported.append(f"unknown recovery disposition at {ordinal}")
        changed = recovery[0] != actor[0] if recovery[0] and actor[0] else None
        individual_lost = row_lost if count == 1 and retained else None
        if count == 1 and individual_lost is not None and changed is not None and individual_lost != changed:
            unsupported.append("row lost credit conflicts with recovery possession")
        events.append(SourceFumbleOccurrence(
            f"{event_id}:F{ordinal}", ordinal, *actor, *recovery, terminal, changed,
            individual_lost, basis))
        if recovery[0]:
            segments.append(SourceRecoverySegment(
                "fumble_recovery", ordinal, *recovery,
                None if recovery_conflict else _advance(detail, recovery[2]),
                _integer(row, f"fumble_recovery_{ordinal}_yards"),
                ordinal + 1 if ordinal < count else None, detail))
    kinds = [name for flag, name in (("sack", "sack"), ("complete_pass", "receiving"),
                                    ("rush_attempt", "rushing")) if _boolean(row, flag)]
    kind = kinds[0] if len(kinds) == 1 else None
    if len(kinds) > 1:
        unsupported.append("conflicting statistical class flags")
    credit_prefix = {"rushing": "rusher", "receiving": "receiver", "sack": "passer"}.get(kind)
    credit_player = _text(row, f"{credit_prefix}_player_id") if credit_prefix else ""
    credit_name = _text(row, f"{credit_prefix}_player_name") if credit_prefix else ""
    return FumbleSourceLedger(
        event_id, source_record_hash(row), tuple(row.items()), raw, final, origin, retained,
        kind, _integer(row, "yards_gained"), row_lost, tuple(events), tuple(segments),
        len(re.findall(r"\bmuffs\b", final, re.IGNORECASE)), tuple(unsupported),
        statistical_player_id=credit_player or None, statistical_player_name=credit_name or None)


def apply_fumble_loss_reviews(
    ledger: FumbleSourceLedger, reviews: Iterable[FumbleLossReview],
) -> FumbleSourceLedger:
    """Attach field-specific reviewed losses after checking raw/event/evidence bindings."""
    events = list(ledger.events)
    accepted = list(ledger.loss_reviews)
    seen = {review.ordinal for review in accepted}
    for review in reviews:
        if (not ledger.retained or review.raw_play_sha256 != ledger.raw_play_sha256
                or type(review.ordinal) is not int or not 1 <= review.ordinal <= len(events)
                or type(review.lost) is not bool or type(review.evidence_page) is not int
                or review.evidence_page <= 0
                or re.fullmatch(r"[0-9a-f]{64}", review.evidence_sha256) is None
                or review.ordinal in seen):
            raise ValueError("Invalid or duplicate fumble loss review binding")
        event = events[review.ordinal - 1]
        if (review.fumbling_team, review.fumbling_player_id) != (
                event.fumbling_team, event.fumbling_player_id):
            raise ValueError("Fumble loss review does not match the ordered actor")
        events[review.ordinal - 1] = replace(event, individual_lost=review.lost)
        accepted.append(review)
        seen.add(review.ordinal)
    return replace(ledger, events=tuple(events), loss_reviews=tuple(accepted))


@dataclass(frozen=True)
class DiagnosticFumbleProjection:
    """One modeled event, retaining its unique source and exposure population."""

    source_event_id: str
    team: str
    exposure: str
    modeled_initial_yards: int
    chart_result: str
    modeled_gain_basis: str
    lost: bool
    statistical_player_id: str | None


@dataclass(frozen=True)
class DiagnosticJointFumbleProjection:
    """A local projection receipt; completeness does not authorize chart fitting."""

    source_event_id: str
    origin: str
    policy: str
    expected_occurrences: int
    events: tuple[DiagnosticFumbleProjection, ...]
    unsupported: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Whether every retained occurrence has the required source support."""
        return not self.unsupported and len(self.events) == self.expected_occurrences


def project_fumble_ledger(
    ledger: FumbleSourceLedger, *, policy: str,
) -> DiagnosticJointFumbleProjection:
    """Project an origin and its conditional fumbles once, without fitting a chart.

    Statistical play credit supplies only the explicit primary gain proxy. A
    later fumble uses its actor's scoped advance, never provider recovery credit.
    The current shared-return exchangeability experiment still needs measured
    engine exposures, complete populations and independent residual review.
    """
    validate_fumble_gain_policy(policy)
    if policy is None:
        raise ValueError("Diagnostic fumble projection requires an explicit policy")
    errors = list(ledger.unsupported)
    raw = dict(ledger.raw_values)
    if (_boolean(raw, "two_point_attempt") or re.search(
            r"\btwo[- ]point (?:conversion )?attempt\b", ledger.final_description, re.IGNORECASE)):
        errors.append("conversion excluded from ordinary source projection")
    if ledger.origin not in {"rushing", "receiving", "sack", "punt_snap", "interception",
                             "kickoff_return", "punt_return", "blocked_punt", "blocked_field_goal"}:
        errors.append(f"unsupported ordinary projection origin: {ledger.origin}")
    projected: list[DiagnosticFumbleProjection] = []
    if not ledger.retained:
        errors.append("no retained fumble credit")
    if not errors:
        for event in ledger.events:
            if event.individual_lost is None:
                errors.append(f"{event.source_event_id}: unknown individual lost credit")
                continue
            primary = event.ordinal == 1 and ledger.origin in {
                "rushing", "receiving", "sack", "punt_snap"}
            exposure = "primary" if primary else (
                ledger.origin if event.ordinal == 1 and ledger.origin in {
                    "kickoff_return", "punt_return"} else "shared_return")
            gain = event.physical_initial_yards
            basis = "known_physical"
            if gain is None and policy != "known_physical_v1":
                if primary:
                    expected_kind = "rushing" if ledger.origin == "punt_snap" else ledger.origin
                    if (ledger.statistical_kind == expected_kind
                            and (ledger.origin != "punt_snap" or ledger.statistical_player_id)):
                        gain = ledger.statistical_yards
                        basis = "play_statistical_credit_proxy"
                elif policy == "source_reported_gain_proxy_v1":
                    matching = [segment for segment in ledger.segments
                                if segment.ends_in_fumble == event.ordinal
                                and segment.team == event.fumbling_team
                                and segment.player_id == event.fumbling_player_id]
                    if len(matching) == 1:
                        gain = matching[0].reported_yards
                        basis = "scoped_reported_advance_proxy"
            if type(gain) is not int:
                required = ("physical initial gain" if policy == "known_physical_v1" else
                            "primary statistical gain/class" if primary else "scoped advance gain")
                errors.append(f"{event.source_event_id}: unsupported {required}")
                continue
            token = "F" if gain == 0 else f"F {'+' if gain > 0 else '-'} {abs(gain)}"
            projected.append(DiagnosticFumbleProjection(
                event.source_event_id, event.fumbling_team, exposure, gain, token, basis,
                event.individual_lost, ledger.statistical_player_id if primary else None))
    return DiagnosticJointFumbleProjection(
        ledger.source_event_id, ledger.origin, policy, len(ledger.events),
        tuple(projected), tuple(errors))

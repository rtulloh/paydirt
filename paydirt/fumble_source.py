"""Explicit fumble gain models, retaining nullable source facts without inference."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass

FUMBLE_GAIN_POLICIES = (
    "known_physical_v1", "credited_fumble_proxy_v1", "source_reported_gain_proxy_v1",
    "historical_fumble_class_proxy_v1",
    "historical_fumble_class_proxy_v2",
)
RUN_CHARTS = ("line_plunge", "off_tackle", "end_run", "draw")


@dataclass(frozen=True)
class FumbleGainFacts:
    """One supported fumble's credit, physical movement and recovery facts."""

    source_event_id: str
    raw_event_sha256: str
    credited_kind: str | None
    credited_yards: int | None
    physical_initial_yards: int | None
    lost: bool | None
    loose_ball_yards: int | None = None
    recovery_advance_yards: int | None = None
    reported_kind: str | None = None
    reported_yards: int | None = None
    reported_scope: str | None = None
    reported_actor: str | None = None
    reported_team: str | None = None
    recovery_basis: str | None = None
    retained_incompletion: bool = False
    aborted_field_goal: bool = False


@dataclass(frozen=True)
class FumbleGainProjection:
    """A model gain and its basis, never a replacement for source facts."""

    source_facts: FumbleGainFacts
    modeled_initial_yards: int | None
    modeled_gain_basis: str
    policy: str
    modeled_originating_kind: str | None = None
    modeled_class_basis: str | None = None
    modeled_role: str | None = None

    @property
    def originating_kind(self) -> str:
        """Return the supported origin class without promoting reported credit."""
        return (self.source_facts.credited_kind or self.source_facts.reported_kind
                or self.modeled_originating_kind)

    @property
    def chart_result(self) -> str:
        """Return the existing F token syntax for the separate modeled gain."""
        if self.source_facts.retained_incompletion:
            return "F INC"
        if self.source_facts.aborted_field_goal:
            owner = "LOST" if self.source_facts.lost else "KEEP"
            return f"F SNAP {owner} 0"
        gain = self.modeled_initial_yards
        return "F" if gain == 0 else f"F {'+' if gain > 0 else '-'} {abs(gain)}"

    def to_dict(self) -> dict:
        """Retain every nullable fact and the explicit policy in JSON evidence."""
        record = asdict(self)
        for name in ("modeled_originating_kind", "modeled_class_basis", "modeled_role"):
            if record[name] is None:
                record.pop(name)
        return {"schema_version": 2 if self.modeled_class_basis else 1, **record}


def validate_fumble_gain_policy(policy: str | None) -> None:
    """Reject unknown policies; None retains the separately documented legacy path."""
    if policy is not None and policy not in FUMBLE_GAIN_POLICIES:
        raise ValueError(f"Unsupported fumble gain policy: {policy!r}")


def project_fumble_gain(facts: FumbleGainFacts, *, policy: str) -> FumbleGainProjection:
    """Project supported facts under an explicitly selected, versioned model.

    Args:
        facts: Nullable source facts bound to one unchanged event.
        policy: Known physical gain only, or the approved credited-yard proxy.

    Returns:
        Separate modeled gain and basis with the original facts retained.
    """
    if policy not in FUMBLE_GAIN_POLICIES:
        raise ValueError(f"Explicit supported fumble gain policy required: {policy!r}")
    if (not isinstance(facts.source_event_id, str) or not facts.source_event_id.strip()
            or not isinstance(facts.raw_event_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", facts.raw_event_sha256) is None):
        raise ValueError("Fumble projection requires a source event identity and raw SHA-256")
    if type(facts.retained_incompletion) is not bool:
        raise ValueError("Retained incompletion marker must be boolean")
    if type(facts.aborted_field_goal) is not bool:
        raise ValueError("Aborted field-goal marker must be boolean")
    if facts.aborted_field_goal and (
        facts.retained_incompletion or facts.credited_kind != "rushing"
        or type(facts.credited_yards) is not int or facts.credited_yards != 0
        or facts.physical_initial_yards is not None
        or facts.loose_ball_yards is not None or facts.recovery_advance_yards is not None
    ):
        raise ValueError("Aborted field-goal projection requires explicit zero rushing credit and unknown movement")
    if facts.retained_incompletion:
        if (facts.credited_kind != "incomplete" or type(facts.credited_yards) is not int
                or facts.credited_yards != 0 or facts.lost is not False
                or facts.physical_initial_yards is not None):
            raise ValueError("Retained fumble incompletion requires zero incomplete credit and own recovery")
        return FumbleGainProjection(facts, None, "retained_incompletion", policy)
    kinds = {"rushing", "sack", "receiving"}
    reported_kinds = kinds | {"kickoff_return", "punt_return"}
    reported_policy = policy in {"source_reported_gain_proxy_v1", "historical_fumble_class_proxy_v1", "historical_fumble_class_proxy_v2"}
    if not reported_policy and facts.credited_kind not in kinds:
        raise ValueError("Fumble projection requires a known credited statistical class")
    if type(facts.lost) is not bool:
        raise ValueError("Fumble projection requires known recovery")
    if (facts.credited_yards is not None and type(facts.credited_yards) is not int
            or not reported_policy and type(facts.credited_yards) is not int):
        raise ValueError("Fumble projection requires known integer credit")
    if facts.credited_kind is not None and facts.credited_kind not in kinds:
        raise ValueError("Fumble projection has unsupported credited class")
    if facts.credited_yards is not None and facts.credited_kind not in kinds:
        raise ValueError("Fumble credit requires its supported class")
    for value in (facts.physical_initial_yards, facts.loose_ball_yards,
                  facts.recovery_advance_yards, facts.reported_yards):
        if value is not None and type(value) is not int:
            raise ValueError("Fumble movement/reported gain must be integer yards or unknown")
    kind = facts.credited_kind or facts.reported_kind
    if kind not in (reported_kinds if reported_policy else kinds):
        raise ValueError("Fumble projection requires a supported originating class")
    if kind == "sack" and (
        facts.credited_yards is not None and facts.credited_yards > 0
        or facts.physical_initial_yards is not None and facts.physical_initial_yards > 0
    ):
        raise ValueError("A credited sack cannot have positive initial gain or credit")
    gain = facts.physical_initial_yards
    basis = "physical"
    if gain is None:
        if policy == "known_physical_v1":
            raise ValueError("Unknown physical initial gain requires an explicit proxy")
        if facts.credited_yards is not None:
            gain, basis = facts.credited_yards, "credited_proxy"
        elif (reported_policy and facts.reported_kind in reported_kinds
              and type(facts.reported_yards) is int
              and facts.reported_scope == (
                  "primary_before_fumble" if facts.reported_kind in kinds else "return_before_fumble")
              and isinstance(facts.reported_actor, str) and facts.reported_actor.strip()
              and isinstance(facts.reported_team, str) and facts.reported_team.strip()):
            gain, basis = facts.reported_yards, "source_reported_proxy"
        else:
            raise ValueError("Reported proxy requires supported primary scope, class, actor and gain")
    if kind == "sack" and gain > 0:
        raise ValueError("A modeled sack cannot have positive gain")
    return FumbleGainProjection(facts, gain, basis, policy)


def source_record_hash(record: Mapping[str, object]) -> str:
    """Bind all original parsed structured-source fields without changing them."""
    data = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    return hashlib.sha256(data.encode()).hexdigest()


def inferred_rushing_chart(source_event_id: str, seed: int) -> str:
    """Assign a stable explicitly inferred primary family without team-name effects."""
    digest = hashlib.sha256(f"fumble-run-v1:{seed}:{source_event_id}".encode()).digest()
    return RUN_CHARTS[int.from_bytes(digest[:8], "big") % len(RUN_CHARTS)]

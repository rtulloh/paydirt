"""User-authorized historical role assumptions, separate from observed facts."""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

from .fumble_source import FumbleGainFacts, FumbleGainProjection, project_fumble_gain
from .pfr_fumble_source import _actor_prefix

if TYPE_CHECKING:
    from .pfr_play_by_play import ClassifiedGame, FumbleEvent, PfrGame, PfrPlay

POLICY = "historical_fumble_class_proxy_v1"
POLICY_V2 = "historical_fumble_class_proxy_v2"
POLICIES = (POLICY, POLICY_V2)


def policy_metadata(policy: str | None, diagnostics: Mapping[str, int]) -> dict:
    """Bind the versioned assumptions and separate modeled counts in portable evidence."""
    if policy not in POLICIES:
        return {}
    return {"modeled_fumble_assumptions": {
        "contract_version": 1 if policy == POLICY else 2, "policy": policy,
        "modeled_events": diagnostics.get("modeled_fumble_classes", 0),
        "class_counts": {key.removeprefix("modeled_fumble_class_"): value
                         for key, value in sorted(diagnostics.items())
                         if key.startswith("modeled_fumble_class_")},
        "source_class_truth_verified": False, "physical_gain_truth_verified": False,
        "terminal_recovery_gain_proxy": False,
        "precedence": "reviewed and explicit source class before role assumptions; physical gain before credit before reported gain",
        "identified_qb": "[-1,1] snap; below -1 sack; " + ("above 1 rush" if policy == POLICY_V2 else "positive above 1 unsupported"),
        "unknown_role": "below -1 sack; [-1,1] snap; (1,5] running back; above 5 receiver",
        "known_non_qb_without_source_class": "RB/FB rush; C snap; WR/TE reception" if policy == POLICY_V2 else "unsupported",
        "statistical_categories": {"qb_snap": "rushing", "qb_sack": "sack",
                                   "running_back": "rushing", "receiver": "receiving"},
        "interpretation": "User-authorized modeled classifications; source credit, actor, recovery and movement facts remain separate",
    }}


def project_historical_fumble(
    game: PfrGame, play: PfrPlay, offense: str, facts: FumbleGainFacts,
    *, policy: str = POLICY,
) -> FumbleGainProjection:
    """Model an unknown class from an explicit actor-bound gain, never recovery movement."""
    detail = play.detail.casefold().strip()
    if (len(re.findall(r"\bfumbles?\b", detail)) != 1
            or any(term in detail for term in ("lateral", "reverse", "intercept", "punt", "kick", "no play"))):
        raise ValueError("Historical class proxy requires one uncomplicated primary fumble")
    name, actor, body = _actor_prefix(game, detail)
    if actor not in play.player_ids or game.player_teams.get(actor) != offense:
        raise ValueError("Historical class proxy requires an identified offensive actor")
    if policy == POLICY_V2 and body.startswith("sacked by"):
        losses = re.findall(r"\bfor (\d+) yards?\b", body)
        fumbler = re.search(re.escape(name) + r" fumbles\b", body)
        if (len(losses) != 1 or fumbler is None or "returned" in body
                or "pass complete" in body or "pass incomplete" in body):
            raise ValueError("Reordered sack requires one same-actor loss without return movement")
        from .pfr_event_reconciliation import play_fingerprint

        if (facts.source_event_id != f"{play.game_id}:{play.number}"
                or facts.raw_event_sha256 != play_fingerprint(play)):
            raise ValueError("Historical proxy source identity differs")
        facts = replace(facts, reported_kind="sack", reported_yards=-int(losses[0]),
                        reported_scope="primary_before_fumble", reported_actor=actor,
                        reported_team=offense)
        validated = project_fumble_gain(facts, policy=policy)
        return replace(validated, modeled_class_basis="reordered_source_sack",
                       modeled_role=game.player_positions.get(actor))
    match = re.match(r"for (?P<yards>-?\d+) yards?\.\s+" + re.escape(name) + r" fumbles\b", body)
    zero = re.match(r"for no gain\.\s+" + re.escape(name) + r" fumbles\b", body)
    if match is None and zero is None:
        raise ValueError("Historical class proxy requires an explicit same-actor primary gain")
    gain = int(match['yards']) if match is not None else 0
    class_gain = facts.physical_initial_yards if facts.physical_initial_yards is not None else gain
    position = game.player_positions.get(actor)
    if position == "QB":
        if -1 <= class_gain <= 1:
            kind, basis, role = "rushing", "assumed_qb_snap", "QB"
        elif class_gain < -1:
            kind, basis, role = "sack", "assumed_qb_sack", "QB"
        elif policy == POLICY_V2:
            kind, basis, role = "rushing", "assumed_qb_rush", "QB"
        else:
            raise ValueError("Historical QB proxy cannot model positive sack gain")
    elif policy == POLICY_V2 and position in {"RB", "FB"}:
        kind, basis, role = "rushing", "assumed_known_running_back", position
    elif policy == POLICY_V2 and position == "C":
        kind, basis, role = "rushing", "assumed_center_snap", position
    elif policy == POLICY_V2 and position in {"WR", "TE"}:
        kind, basis, role = "receiving", "assumed_known_receiver", position
    elif position:
        raise ValueError("Historical unknown-role assumption cannot override a known non-QB position")
    elif class_gain < -1:
        kind, basis, role = "sack", "assumed_unknown_role_qb_sack", "QB"
    elif class_gain <= 1:
        kind, basis, role = "rushing", "assumed_unknown_role_qb_snap", "QB"
    elif class_gain <= 5:
        kind, basis, role = "rushing", "assumed_unknown_role_running_back", "RB"
    else:
        kind, basis, role = "receiving", "assumed_unknown_role_receiver", "receiver"
    from .pfr_event_reconciliation import play_fingerprint

    if (facts.source_event_id != f"{play.game_id}:{play.number}"
            or facts.raw_event_sha256 != play_fingerprint(play)):
        raise ValueError("Historical proxy source identity differs")
    facts = replace(facts, reported_yards=gain, reported_scope="primary_before_fumble",
                    reported_actor=actor, reported_team=offense)
    # Validate the existing gain/recovery contract using a separate modeled class;
    # the persisted source facts retain the original unknown class and credit.
    validated = project_fumble_gain(replace(facts, reported_kind=kind), policy=policy)
    return replace(validated, source_facts=facts, modeled_originating_kind=kind,
                   modeled_class_basis=basis, modeled_role=role)


FITTING_POLICY = "historical_isolated_fumble_exclusions_v1"


def fitting_population(
    game: PfrGame, classified: ClassifiedGame, *, raw_sha256: str,
) -> tuple[tuple[FumbleEvent, ...], list[dict]]:
    """Exclude every unresolved fumble uniformly from fitting while retaining its evidence."""
    from .pfr_event_reconciliation import play_fingerprint

    if classified.source_conflicts:
        raise ValueError("Fitting exclusions cannot suppress source conflicts")
    by_number = {event.play_number: event for event in classified.fumbles}
    plays = {play.number: play for play in game.plays}
    excluded: dict[int, dict] = {}
    for issue in classified.unsupported_fields:
        number = issue.get("play_number")
        if (not isinstance(number, int)
                or issue.get("field") not in {"fumble_gain_projection", "aborted_field_goal_projection"}
                or number not in by_number or number not in plays):
            raise ValueError("Fitting exclusions cannot suppress unrelated required fields")
        event = by_number[number]
        excluded[number] = {
            "event_id": f"{game.game_id}:{number}", "team": event.team,
            "unit": event.unit, "lost": event.lost,
            "mechanism": str(issue["field"]), "reason": str(issue.get("reason", "unknown")),
            "raw_game_sha256": raw_sha256, "raw_play_sha256": play_fingerprint(plays[number]),
            "scope": "fitting_only",
        }
    return tuple(event for event in classified.fumbles if event.play_number not in excluded), list(excluded.values())


def fitting_metadata(
    policy: str | None, full: list[FumbleEvent], fitted: list[FumbleEvent], exclusions: list[dict],
) -> dict | None:
    """Disclose full and supported denominators and uniform omission effects."""
    from collections import Counter

    if policy is None:
        return None
    if policy != FITTING_POLICY:
        raise ValueError("Unsupported historical fitting policy")
    teams = sorted({event.team for event in full})
    return {
        "contract_version": 1, "policy": policy,
        "selection": "all unresolved fumble projections, independent of team or fit performance",
        "historical_source_complete": False, "modeled_scope_eligible": True,
        "terminal_recovery_gain_proxy": False,
        "full_events": len(full), "fitted_events": len(fitted), "excluded_events": len(exclusions),
        "full_lost": sum(event.lost is True for event in full),
        "fitted_lost": sum(event.lost is True for event in fitted),
        "full_unknown_ownership": sum(event.lost is None for event in full),
        "fitted_unknown_ownership": sum(event.lost is None for event in fitted),
        "excluded_by_mechanism": dict(sorted(Counter(record["mechanism"] for record in exclusions).items())),
        "teams": {team: {
            "full_events": sum(event.team == team for event in full),
            "fitted_events": sum(event.team == team for event in fitted),
            "full_lost": sum(event.team == team and event.lost is True for event in full),
            "fitted_lost": sum(event.team == team and event.lost is True for event in fitted),
            "excluded_events": sum(record["team"] == team for record in exclusions),
        } for team in teams},
        "exclusions": sorted(exclusions, key=lambda record: record["event_id"]),
        "rate_interpretation": "Fumble/lost-fumble fitting numerators omit exclusions; all source events remain in the ledger. No historical result is omitted.",
    }


def validate_fitting_metadata(disclosure: object) -> str:
    """Reject false truth claims, inconsistent populations, or unidentified exclusions."""
    if not isinstance(disclosure, dict) or disclosure.get("policy") != FITTING_POLICY:
        raise ValueError("Unsupported historical fitting disclosure")
    if (type(disclosure.get("contract_version")) is not int or disclosure["contract_version"] != 1
            or disclosure.get("historical_source_complete") is not False
            or disclosure.get("modeled_scope_eligible") is not True
            or disclosure.get("terminal_recovery_gain_proxy") is not False):
        raise ValueError("Historical fitting disclosure requires explicit modeled uncertainty")
    records, teams = disclosure.get("exclusions"), disclosure.get("teams")
    if not isinstance(records, list) or not isinstance(teams, dict):
        raise TypeError("Historical fitting disclosure requires event and team populations")
    for key in ("full_events", "fitted_events", "excluded_events", "full_lost", "fitted_lost",
                "full_unknown_ownership", "fitted_unknown_ownership"):
        if type(disclosure.get(key)) is not int or disclosure[key] < 0:
            raise ValueError("Historical fitting counts must be nonnegative integers")
    if (disclosure["full_events"] != disclosure["fitted_events"] + len(records)
            or disclosure["excluded_events"] != len(records)
            or len({record.get("event_id") for record in records}) != len(records)):
        raise ValueError("Historical fitting populations do not reconcile")
    for record in records:
        if (record.get("scope") != "fitting_only" or not record.get("reason")
                or record.get("mechanism") not in {"fumble_gain_projection", "aborted_field_goal_projection"}
                or record.get("team") not in teams
                or any(not re.fullmatch(r"[0-9a-f]{64}", str(record.get(key)))
                       for key in ("raw_game_sha256", "raw_play_sha256"))):
            raise ValueError("Historical fitting exclusion lacks bound source evidence")
    for key in ("full_events", "fitted_events", "excluded_events", "full_lost", "fitted_lost"):
        if any(type(team.get(key)) is not int or team[key] < 0 for team in teams.values()):
            raise ValueError("Historical fitting team counts must be nonnegative integers")
        if sum(team[key] for team in teams.values()) != disclosure[key]:
            raise ValueError("Historical fitting team totals differ")
    if (disclosure["full_lost"] - disclosure["fitted_lost"] != sum(record.get("lost") is True for record in records)
            or disclosure["full_unknown_ownership"] - disclosure["fitted_unknown_ownership"]
            != sum(record.get("lost") is None for record in records)):
        raise ValueError("Historical fitting ownership counts differ")
    from collections import Counter

    if disclosure.get("excluded_by_mechanism") != dict(Counter(record["mechanism"] for record in records)):
        raise ValueError("Historical fitting mechanism totals differ")
    for name, team in teams.items():
        excluded = [record for record in records if record["team"] == name]
        if (team["full_events"] != team["fitted_events"] + len(excluded)
                or team["excluded_events"] != len(excluded)
                or team["full_lost"] != team["fitted_lost"] + sum(record["lost"] is True for record in excluded)):
            raise ValueError("Historical fitting team attribution differs")
    return FITTING_POLICY

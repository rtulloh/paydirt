"""Classify nflverse play-by-play rows into empirical Paydirt outcomes."""

from __future__ import annotations

import csv
import gzip
import hashlib
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from .fumble_source import (
    FumbleGainFacts,
    FumbleGainProjection,
    inferred_rushing_chart,
    project_fumble_gain,
    source_record_hash,
    validate_fumble_gain_policy,
)
from .nflverse_fumble_ledger import (
    DiagnosticFumbleProjection,
    DiagnosticJointFumbleProjection,
    FumbleLossReview,
    FumbleSourceLedger,
    apply_fumble_loss_reviews,
    build_fumble_ledger,
    project_fumble_ledger,
)
from .pfr_play_by_play import (
    EmpiricalPlay,
    FieldGoalAttempt,
    FumbleEvent,
    normalized_penalty_result,
)

_PASS_CHARTS = ("screen", "short_pass", "medium_pass", "long_pass")
FUMBLE_PROJECTION_MODES = ("ordered_ledger_v1",)
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
    event_counts: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    excluded_conversions: tuple[Mapping[str, object], ...] = ()
    unsupported_fields: tuple[Mapping[str, object], ...] = ()
    fumble_gain_projections: tuple[FumbleGainProjection, ...] = ()
    fumble_ledgers: tuple[FumbleSourceLedger, ...] = ()
    joint_fumble_projections: tuple[DiagnosticJointFumbleProjection, ...] = ()
    shared_return_fumbles: tuple[DiagnosticFumbleProjection, ...] = ()
    interception_return_outcomes: Mapping[str, Mapping[str, str]] = field(default_factory=dict)


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
        value = float(text)
        return value if math.isfinite(value) else None
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


def _project_fumble(
    row: Mapping[str, object], lost: bool | None, fallback_number: int, policy: str,
) -> FumbleGainProjection:
    """Retain structured credit; the feed does not establish initial physical gain."""
    offense = _text(row, "posteam").upper()
    if not _text(row, "game_id"):
        raise ValueError("A source game identity is required")
    if not offense or _text(row, "fumbled_1_team").upper() != offense:
        raise ValueError("One explicitly identified original-offense fumbler is required")
    sack, rush, completion = (_flag(row, key) for key in ("sack", "rush_attempt", "complete_pass"))
    incomplete = _flag(row, "incomplete_pass")
    if incomplete:
        final_description = re.split(
            r"and the play was REVERSED\.", _text(row, "desc"), flags=re.IGNORECASE,
        )[-1]
        fumble_match = re.search(r"\bfumbles?\b", final_description, re.IGNORECASE)
        incomplete_match = re.search(r"\bpass incomplete\b", final_description, re.IGNORECASE)
        recovery = _text(row, "fumble_recovery_1_team").upper()
        if (sack or rush or completion or _flag(row, "interception")
                or not _flag(row, "pass_attempt") or lost is not False
                or recovery != offense or not _text(row, "fumbled_1_player_id")
                or _number(row, "yards_gained") != 0
                or fumble_match is None or incomplete_match is None
                or fumble_match.start() >= incomplete_match.start()):
            raise ValueError("Retained fumble incompletion requires supported original-offense continuation")
        return project_fumble_gain(FumbleGainFacts(
            f"{_text(row, 'game_id')}:{_play_number(row, fallback_number)}",
            source_record_hash(row), "incomplete", 0, None, False,
            recovery_basis="reported_identity", retained_incompletion=True,
        ), policy=policy)
    if sum((sack, rush, completion)) != 1 or rush and _flag(row, "pass_attempt"):
        raise ValueError("Exactly one supported credited sack/rushing/receiving class is required")
    recovery = _text(row, "fumble_recovery_1_team").upper()
    if recovery not in {"", "NA"} and lost is not None and (recovery != offense) != lost:
        raise ValueError("Credited lost flag conflicts with the explicit recovery team")
    credited = _number(row, "yards_gained")
    facts = FumbleGainFacts(
        f"{_text(row, 'game_id')}:{_play_number(row, fallback_number)}",
        source_record_hash(row),
        "sack" if sack else "rushing" if rush else "receiving",
        int(credited) if credited is not None and credited.is_integer() else None,
        None, lost,
    )
    return project_fumble_gain(facts, policy=policy)


def classify_nflverse_rows(
    rows: Iterable[Mapping[str, object]],
    seed: int = 8306,
    *, fumble_gain_policy: str | None = None,
    fumble_projection_mode: str | None = None,
    fumble_loss_reviews: Iterable[FumbleLossReview] = (),
) -> ClassifiedNflverseSeason:
    """Classify regular-season nflverse rows into empirical chart outcomes."""
    validate_fumble_gain_policy(fumble_gain_policy)
    if fumble_projection_mode not in (None, *FUMBLE_PROJECTION_MODES):
        raise ValueError("Unknown fumble projection mode")
    review_stream = tuple(fumble_loss_reviews)
    if review_stream and fumble_projection_mode is None:
        raise ValueError("Fumble loss reviews require an explicit projection mode")
    if fumble_projection_mode is not None and fumble_gain_policy != "source_reported_gain_proxy_v1":
        raise ValueError("Ordered ledger projection requires source_reported_gain_proxy_v1")
    if any(not isinstance(review, FumbleLossReview) for review in review_stream):
        raise ValueError("Fumble review stream requires typed FumbleLossReview values")
    reviews_by_hash: defaultdict[str, list[FumbleLossReview]] = defaultdict(list)
    for review in review_stream:
        reviews_by_hash[review.raw_play_sha256].append(review)
    used_reviews: set[str] = set()
    projections: list[FumbleGainProjection] = []
    plays: list[EmpiricalPlay] = []
    field_goals: list[FieldGoalAttempt] = []
    fumbles: list[FumbleEvent] = []
    diagnostics: Counter[str] = Counter()
    event_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    games: set[str] = set()
    source_rows = 0
    excluded_conversions: list[Mapping[str, object]] = []
    unsupported_fields: list[Mapping[str, object]] = []
    fumble_ledgers: list[FumbleSourceLedger] = []
    joint_projections: list[DiagnosticJointFumbleProjection] = []
    shared_fumbles: list[DiagnosticFumbleProjection] = []
    int_outcomes: defaultdict[str, dict[str, str]] = defaultdict(dict)
    projected_ids: set[str] = set()

    for fallback_number, row in enumerate(rows, 1):
        if _text(row, "season_type").upper() != "REG":
            continue
        source_rows += 1
        game_id = _text(row, "game_id")
        if game_id:
            games.add(game_id)
        play_type = _text(row, "play_type").casefold()
        description = _text(row, "desc")
        ledger: FumbleSourceLedger | None = None
        joint: DiagnosticJointFumbleProjection | None = None
        if (_flag(row, "fumble") or re.search(r"\bfumbles\b", description, re.IGNORECASE)
                or any(_flag(row, flag) for flag in (
                    "punt_blocked", "field_goal_blocked", "extra_point_blocked"))
                or any(_text(row, name).casefold() == "blocked" for name in (
                    "field_goal_result", "extra_point_result"))):
            ledger = build_fumble_ledger(row, fallback_number)
            if fumble_projection_mode is not None and ledger.raw_play_sha256 in reviews_by_hash:
                ledger = apply_fumble_loss_reviews(ledger, reviews_by_hash[ledger.raw_play_sha256])
                used_reviews.add(ledger.raw_play_sha256)
            fumble_ledgers.append(ledger)
        flag_text = _text(row, "two_point_attempt").casefold()
        known_conversion_flag = (_number(row, "two_point_attempt") in (0, 1)
                                 or flag_text in {"true", "false", "yes", "no"})
        explicit_conversion = re.search(
            r"\btwo[- ]point (?:conversion )?attempt\b", description, re.IGNORECASE,
        ) is not None
        scrimmage_context = (
            play_type in {"run", "pass"}
            or any(_flag(row, field) for field in ("pass_attempt", "rush_attempt", "sack"))
            or (play_type == "no_play" and _flag(row, "penalty"))
            or explicit_conversion
        )
        capability = ("structured_two_point_flags" if known_conversion_flag else
                      "missing_two_point_flags" if scrimmage_context else
                      "not_applicable_two_point_flags")
        diagnostics[capability] += 1
        structured_conversion = known_conversion_flag and _flag(row, "two_point_attempt")
        voided_conversion = (explicit_conversion and play_type == "no_play"
                             and _flag(row, "penalty")
                             and "no play" in description.casefold())
        defensive_conversion = (
            explicit_conversion and _flag(row, "extra_point_attempt")
            and re.search(r"\bdefensive two[- ]point", description, re.IGNORECASE) is not None
            and "block" in description.casefold()
        )
        if (explicit_conversion and known_conversion_flag and not structured_conversion
                and not voided_conversion and not defensive_conversion):
            diagnostics["conflicting_two_point_flags"] += 1
        if structured_conversion or explicit_conversion:
            # These procedures never supply ordinary chart samples. Source flags
            # distinguish credited offensive attempts from voided fouls/XP returns.
            diagnostics["excluded_conversion_rows"] += 1
            if structured_conversion:
                diagnostics["excluded_two_point_attempts"] += 1
            excluded_conversions.append({
                "game_id": game_id, "play_number": _play_number(row, fallback_number),
                "team": _text(row, "posteam").upper(),
                "opponent": _text(row, "defteam").upper(),
                "play_type": _text(row, "play_type"),
                "evidence": "structured_flag" if structured_conversion else "explicit_description",
                "procedure": ("defensive_return" if defensive_conversion else
                              "voided_offensive_attempt" if voided_conversion else "offensive_attempt"),
                "credited_offensive_attempt": structured_conversion if known_conversion_flag else None,
                **{name: _flag(row, name) for name in
                   ("penalty", "sack", "interception", "fumble", "fumble_lost")},
                "detail_sha256": hashlib.sha256(description.encode()).hexdigest(),
            })
            continue
        play_type = _text(row, "play_type").casefold()
        description = _text(row, "desc").casefold()
        offense = _text(row, "posteam").upper()
        defense = _text(row, "defteam").upper()

        # Official primary credit survives a retained end-enforcement foul.
        # Its empirical chart sample may still be only a penalty below.
        if (fumble_projection_mode is not None and ledger is not None and ledger.retained
                and (ledger.origin in {"rushing", "receiving", "sack", "punt_snap", "interception", "blocked_punt", "blocked_field_goal"}
                     or len(ledger.events) > 1)):
            returning_team = _text(row, "return_team").upper() or defense
            if ledger.origin == "interception" and (
                    len(ledger.events) != 1 or ledger.events[0].fumbling_team != returning_team
                    or returning_team != defense):
                unsupported_fields.append({"game_id": game_id, "play_number": _play_number(row, fallback_number),
                                           "field": "fumble_ownership", "reason": "conflicting interception-return fumbler"})
                continue
            assert fumble_gain_policy is not None
            joint = project_fumble_ledger(ledger, policy=fumble_gain_policy)
            if not joint.complete:
                unsupported_fields.append({
                    "game_id": game_id, "play_number": _play_number(row, fallback_number),
                    "field": "fumble_ownership", "reason": "; ".join(joint.unsupported),
                })
                diagnostics["unsupported_ordered_fumble_projections"] += 1
                continue
            if any(event.source_event_id in projected_ids for event in joint.events):
                raise ValueError("Duplicate ordered fumble source event")
            projected_ids.update(event.source_event_id for event in joint.events)
            joint_projections.append(joint)
            shared_fumbles.extend(event for event in joint.events if event.exposure == "shared_return")
            for event in joint.events:
                if event.exposure == "primary":
                    unit = "punt_snap" if ledger.origin == "punt_snap" else "rushing" if ledger.origin == "rushing" else "passing"
                    fumbles.append(FumbleEvent(event.team, unit, event.lost, game_id, _play_number(row, fallback_number)))
                    diagnostics["ordered_primary_fumble_credits"] += 1

        if fumble_projection_mode is not None and _flag(row, "interception") and play_type != "no_play":
            gain = _number(row, "return_yards")
            returning_team = _text(row, "return_team").upper() or defense
            if gain is None or not gain.is_integer() or not returning_team:
                unsupported_fields.append({"game_id": game_id, "play_number": _play_number(row, fallback_number),
                                           "field": "interception_return", "reason": "missing integer return gain/team"})
                continue
            event_id = f"{game_id}:{_play_number(row, fallback_number)}"
            if _flag(row, "fumble"):
                shared = [event for event in (joint.events if joint else ()) if event.exposure == "shared_return"]
                if len(shared) != 1:
                    unsupported_fields.append({"game_id": game_id, "play_number": _play_number(row, fallback_number),
                                               "field": "fumble_ownership", "reason": "unsupported INT-F shared subset"})
                    continue
                int_outcomes[returning_team][shared[0].source_event_id] = shared[0].chart_result
            else:
                if event_id in int_outcomes[returning_team]:
                    raise ValueError("Duplicate interception return source event")
                int_outcomes[returning_team][event_id] = str(int(gain))

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

        # Provider sack credit survives accepted end-enforcement fouls. The
        # modeled chart penalty sample below is distinct from this official
        # event count; a penalty-only sample must not erase source sack credit.
        credited_sack = _flag(row, "sack") and play_type != "no_play"
        if credited_sack:
            diagnostics["sacks"] += 1
            event_counts[offense]["sacks"] += 1

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
            if credited_sack:
                diagnostics["sacks_with_retained_penalty"] += 1
            chart = _scrimmage_chart(row, seed)
            if chart == "qb_time":
                # Structured qb_scramble establishes a dropback, but route
                # depth remains a declared heuristic when unrecorded.
                chart = _pass_chart(row)
                diagnostics["supplemental_penalties_as_primary"] += 1
                if _number(row, "air_yards") is None and not _text(row, "pass_length"):
                    diagnostics["heuristic_penalty_pass_family"] += 1
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

        if joint is not None and ledger is not None:
            primary = [event for event in joint.events if event.exposure == "primary"]
            if primary:
                event = primary[0]
                if ledger.origin == "punt_snap":
                    plays.append(_empirical_play(row, event.team, "special_teams", "punt", event.chart_result, fallback_number))
                else:
                    assert fumble_gain_policy is not None
                    projected = _project_fumble(row, event.lost, fallback_number, fumble_gain_policy)
                    projections.append(projected)
                    if ledger.origin == "sack":
                        plays.append(_empirical_play(row, offense, "offense", _pass_chart(row), "QT", fallback_number, defense))
                        chart = "qb_time"
                    elif ledger.origin == "receiving":
                        chart = _pass_chart(row)
                    else:
                        chart = _run_chart(row)
                        if chart not in {"line_plunge", "off_tackle", "end_run", "draw"}:
                            chart = inferred_rushing_chart(ledger.source_event_id, seed)
                            diagnostics["inferred_primary_rushing_fumble_family"] += 1
                    plays.append(_empirical_play(row, offense, "offense", chart, event.chart_result, fallback_number, defense))
                    diagnostics[f"fumble_gain_basis_{projected.modeled_gain_basis}"] += 1
                continue

        # Required outcome facts stay unknown rather than becoming zero/retained.
        retained_scrimmage = (play_type in {"run", "pass"}
                              or any(_flag(row, key) for key in ("sack", "pass_attempt", "rush_attempt")))
        if retained_scrimmage and _flag(row, "fumble"):
            text = _text(row, "fumble_lost").casefold()
            loss = _number(row, "fumble_lost")
            known_loss = loss in (0, 1) or text in {"true", "false", "yes", "no"}
            lost = _flag(row, "fumble_lost") if known_loss else None
            final_description = re.split(
                r"and the play was REVERSED\.", description, flags=re.IGNORECASE,
            )[-1]
            if (any(_text(row, key).casefold() not in {"", "na"} for key in (
                "fumbled_2_team", "fumbled_2_player_id", "fumbled_2_player_name",
                "fumble_recovery_2_team", "fumble_recovery_2_player_id",
            )) or len(re.findall(r"\bfumbles\b", final_description, re.IGNORECASE)) > 1):
                diagnostics["multiple_fumble_sequences"] += 1
                unsupported_fields.append({
                    "game_id": game_id, "play_number": _play_number(row, fallback_number),
                    "field": "fumble_ownership",
                    "reason": "multiple fumbles require separate ownership and credit events",
                })
                if fumble_gain_policy is not None:
                    continue
            elif _flag(row, "interception"):
                # The global flag can describe the interceptor's later fumble,
                # which is not an offensive passing-fumble calibration event.
                return_team = _text(row, "return_team").upper() or defense
                fumbling_teams = [
                    _text(row, key).upper() for key in ("fumbled_1_team", "fumbled_2_team")
                    if _text(row, key)
                ]
                if fumbling_teams == [return_team] and return_team == defense:
                    diagnostics["interception_return_fumbles"] += 1
                else:
                    diagnostics["unknown_interception_fumble_ownership"] += 1
                    unsupported_fields.append({
                        "game_id": game_id, "play_number": _play_number(row, fallback_number),
                        "field": "fumble_ownership",
                        "reason": "requires one explicitly identified interception-return fumbler",
                    })
            else:
                unit = "passing" if play_type == "pass" or _flag(row, "sack") or _flag(row, "pass_attempt") else "rushing"
                fumbles.append(FumbleEvent(offense, unit, lost, game_id, _play_number(row, fallback_number)))
                if fumble_gain_policy is not None:
                    try:
                        projected = _project_fumble(row, lost, fallback_number, fumble_gain_policy)
                    except ValueError as exc:
                        diagnostics["unsupported_fumble_gain_projections"] += 1
                        diagnostics["unknown_fumble_recoveries"] += int(lost is None)
                        unsupported_fields.append({
                            "game_id": game_id, "play_number": _play_number(row, fallback_number),
                            "field": "fumble_gain_projection", "reason": str(exc),
                        })
                        continue
                    projections.append(projected)
                    kind = projected.source_facts.credited_kind
                    fumbles[-1] = FumbleEvent(
                        offense, "rushing" if kind == "rushing" else "passing", lost,
                        game_id, _play_number(row, fallback_number),
                        retained_incompletion=projected.source_facts.retained_incompletion)
                    if kind == "sack":
                        chart = _pass_chart(row)
                        plays.append(_empirical_play(
                            row, offense, "offense", chart, "QT", fallback_number, defense))
                        chart = "qb_time"
                    elif kind in {"receiving", "incomplete"}:
                        chart = _pass_chart(row)
                    else:
                        chart = _run_chart(row)
                        if chart not in {"line_plunge", "off_tackle", "end_run", "draw"}:
                            chart = inferred_rushing_chart(projected.source_facts.source_event_id, seed)
                            diagnostics["inferred_primary_rushing_fumble_family"] += 1
                    plays.append(_empirical_play(
                        row, offense, "offense", chart, projected.chart_result, fallback_number, defense))
                    diagnostics[f"fumble_gain_basis_{projected.modeled_gain_basis}"] += 1
                    continue
            if not known_loss:
                diagnostics["unknown_fumble_recoveries"] += 1
                unsupported_fields.append({"game_id": game_id, "play_number": _play_number(row, fallback_number),
                                           "field": "fumble_lost", "reason": "unknown recovery ownership"})
        needs_gain = (retained_scrimmage and (_flag(row, "sack") or _flag(row, "complete_pass")
                      or play_type == "run" or _flag(row, "rush_attempt")))
        gain = _number(row, "yards_gained")
        if needs_gain and (gain is None or not gain.is_integer()):
            diagnostics["missing_required_gains"] += 1
            unsupported_fields.append({"game_id": game_id, "play_number": _play_number(row, fallback_number),
                                       "field": "yards_gained", "reason": "unknown integer initial/net gain"})
            continue

        if _flag(row, "sack"):
            chart = _pass_chart(row)
            yards = _integer(row, "yards_gained")
            plays.append(
                _empirical_play(row, offense, "offense", chart, "QT", fallback_number, defense)
            )
            qb_result = (_fumble_result(yards) if _flag(row, "fumble") else
                         "SACK 0" + ("*" if _flag(row, "out_of_bounds") else "") if yards == 0
                         else _marked_numeric(yards, _flag(row, "out_of_bounds")))
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
                        interception_return_penalty or (
                            int_outcomes[return_team].get(f"{game_id}:{_play_number(row, fallback_number)}:F1", _return_result(row))
                            if fumble_projection_mode is not None else _return_result(row)),
                        fallback_number,
                    )
                )
                if interception_return_penalty is not None:
                    diagnostics["special_teams_penalties"] += 1
                diagnostics["interceptions"] += 1
                event_counts[offense]["interceptions"] += 1
            elif _flag(row, "incomplete_pass"):
                result = "BLACK"
            elif _flag(row, "complete_pass"):
                yards = _integer(row, "yards_gained")
                if _flag(row, "fumble"):
                    result = _fumble_result(yards)
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
            else:
                result = _marked_numeric(yards, _flag(row, "out_of_bounds"))
            plays.append(
                _empirical_play(row, offense, "offense", chart, result, fallback_number, defense)
            )
            continue

        diagnostics["ignored_rows"] += 1

    for attempt in field_goals:
        event_counts[attempt.team]["field_goal_attempts"] += 1
    if set(reviews_by_hash) != used_reviews:
        raise ValueError("Unused or mismatched fumble loss review binding")
    return ClassifiedNflverseSeason(
        plays=tuple(plays),
        field_goals=tuple(field_goals),
        fumbles=tuple(fumbles),
        diagnostics=dict(diagnostics),
        source_rows=source_rows,
        games=len(games),
        event_counts={team: dict(counts) for team, counts in event_counts.items()},
        excluded_conversions=tuple(excluded_conversions),
        unsupported_fields=tuple(unsupported_fields),
        fumble_gain_projections=tuple(projections),
        fumble_ledgers=tuple(fumble_ledgers),
        joint_fumble_projections=tuple(joint_projections),
        shared_return_fumbles=tuple(shared_fumbles),
        interception_return_outcomes={team: dict(values) for team, values in int_outcomes.items()},
    )


def _open_csv(path: Path) -> TextIO:
    """Open plain or gzip-compressed nflverse CSV data as UTF-8 text."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open("r", newline="", encoding="utf-8")


def load_nflverse_play_by_play(
    path: str | Path,
    seed: int = 8306,
    *, fumble_gain_policy: str | None = None,
    fumble_projection_mode: str | None = None,
    fumble_loss_reviews: Iterable[FumbleLossReview] = (),
) -> ClassifiedNflverseSeason:
    """Read and classify regular-season rows from one nflverse CSV file."""
    source_path = Path(path)
    with _open_csv(source_path) as source:
        return classify_nflverse_rows(csv.DictReader(source), seed=seed,
                                      fumble_gain_policy=fumble_gain_policy,
                                      fumble_projection_mode=fumble_projection_mode,
                                      fumble_loss_reviews=fumble_loss_reviews)

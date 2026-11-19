"""Persistent season documents and authoritative team aggregates.

This module is transport/storage independent. Mutations validate and return copies,
so adapters can commit a complete new document atomically. Historical inputs supply
fixtures, never pre-filled results. Ranking is a declared game policy rather than
the official NFL tiebreak procedure. Only team statistics are supported.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from typing import Any
from uuid import uuid4

from .kicking_stats import FIELD_GOAL_FIELDS, validate_field_goal_stats
from .offense_stats import (
    OFFENSIVE_ATTEMPT_FIELDS,
    RATE_INPUTS,
    efficiency,
    validate_offensive_attempt_stats,
)
from .team_stats import (
    EXTENDED_TEAM_FIELDS,
    MAX_FIELDS,
    SIGNED_TEAM_FIELDS,
    validate_extended_team_stats,
)

EXTENDED_RATE_INPUTS = {
    "receiving_yards_per_reception": ("passing_yards", "passing_completions"),
    "third_down_conversion_percentage": ("third_down_conversions", "third_down_attempts"),
    "fourth_down_conversion_percentage": ("fourth_down_conversions", "fourth_down_attempts"),
    "extra_point_percentage": ("extra_points_made", "extra_points_attempted"),
    "gross_punt_average": ("punt_yards", "punts"),
    "net_punt_average": ("punt_yards", "punt_return_yards_allowed", "punt_touchbacks", "punts"),
    "kickoff_return_average": ("kickoff_return_yards", "kickoff_returns"),
    "punt_return_average": ("punt_return_yards", "punt_returns"),
    "punt_return_average_allowed": ("punt_return_yards_allowed", "punts_returned"),
}
ALL_RATE_INPUTS = {**RATE_INPUTS, **EXTENDED_RATE_INPUTS}


def _efficiency(rate: str, values: list[int]) -> float | None:
    """Use paired team totals; team punt attempts include blocked kicks.

    Net punt yards deduct return yards and twenty yards per touchback, using
    the same team-attempt denominator as gross average, never player averages.
    """
    if rate not in EXTENDED_RATE_INPUTS:
        return efficiency(rate, values)
    if rate == "net_punt_average":
        yards, returned, touchbacks, attempts = values
        return (yards - returned - 20 * touchbacks) / attempts if attempts else None
    numerator, attempts = values
    percentage = rate.endswith("_percentage")
    return numerator / attempts * (100 if percentage else 1) if attempts else None


SCHEMA_VERSION = 1
MAX_IMPORT_BYTES = 8 * 1024 * 1024
MAX_PARTICIPANTS = 128
MAX_FIXTURES = 20000
RANKING_POLICY = "Winning fraction, point differential, points scored, name and edition; not official NFL tiebreaking."
STAT_FIELDS = (
    "first_downs", "total_yards", "rushing_yards", "passing_yards", "sack_yards",
    "net_passing_yards", "turnovers", "penalties", "penalty_yards", "sacks",
    "interceptions_thrown", "fumbles_lost", *FIELD_GOAL_FIELDS, *OFFENSIVE_ATTEMPT_FIELDS,
    *EXTENDED_TEAM_FIELDS,
)
SIGNED_FIELDS = {"total_yards", "rushing_yards", "passing_yards", "net_passing_yards", *SIGNED_TEAM_FIELDS}


def _id() -> str:
    return str(uuid4())


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,119}", value) or value in {".", ".."}:
        raise ValueError(f"Invalid {label}")
    return value


def _year(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not re.fullmatch(r"[0-9]{4}", str(value)):
        raise ValueError("Invalid rules/chart season")
    return str(value)


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > 1_000_000_000:
        raise ValueError(f"Invalid {label}")
    return value


def _text(value: Any, label: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 120 or (not empty and not value.strip()) or any(ord(c) < 32 for c in value):
        raise ValueError(f"Invalid {label}")
    return value.strip()


def _stats(value: Any) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Invalid team statistics")  # noqa: TRY004 - user document validation
    output = {}
    for key in STAT_FIELDS:
        if key not in value or value[key] is None:
            continue
        output[key] = _integer(value[key], key, -1_000_000 if key in SIGNED_FIELDS else 0)
    validate_field_goal_stats({key: output[key] for key in FIELD_GOAL_FIELDS if key in output})
    validate_offensive_attempt_stats({key: output[key] for key in OFFENSIVE_ATTEMPT_FIELDS if key in output},
                                     interceptions=output.get("interceptions_thrown"))
    validate_extended_team_stats({key: output[key] for key in EXTENDED_TEAM_FIELDS if key in output})
    if "passing_yards" in output and "sack_yards" in output:
        net = output["passing_yards"] - output["sack_yards"]
        if "net_passing_yards" in output and output["net_passing_yards"] != net:
            raise ValueError("Net passing yards disagree with gross passing and sack yards")
        output["net_passing_yards"] = net
    return output


def _result(value: Any) -> dict:
    if not isinstance(value, dict) or value.get("final") is not True:
        raise ValueError("Only an authoritative final result may be recorded")
    source = value.get("source", "played")
    if not isinstance(source, str) or source not in {"played", "simulated", "manual"}:
        raise ValueError("Invalid result source")
    return {
        "game_id": _token(value.get("game_id"), "game ID"),
        "home_score": _integer(value.get("home_score"), "home score"),
        "away_score": _integer(value.get("away_score"), "away score"),
        "home_stats": _stats(value.get("home_stats")),
        "away_stats": _stats(value.get("away_stats")),
        "final": True, "source": source,
        "revision": _integer(value.get("revision", 1), "result revision", 1),
    }


def _definition(campaign: dict) -> str:
    shape = {"rules_season": campaign["rules_season"], "participants": campaign["participants"],
             "fixtures": [{k: f[k] for k in ("id", "week", "phase", "home_id", "away_id")}
                          for f in campaign["fixtures"] if f["phase"] == "REG"]}
    return hashlib.sha256(json.dumps(shape, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _lock(campaign: dict) -> None:
    campaign["locked_definition"] = _definition(campaign)


def _fixture(week: int, home_id: str, away_id: str, phase: str = "REG", **kwargs: Any) -> dict:
    return {"id": _id(), "week": week, "phase": phase, "home_id": home_id,
            "away_id": away_id, "status": "scheduled", "game_id": None,
            "result": None, "result_history": [], **kwargs}


def _round_robin(ids: list[str], double: bool) -> list[dict]:
    ring = list(ids)
    if len(ring) % 2:
        ring.append(None)
    games = []
    for round_index in range(len(ring) - 1):
        for i in range(len(ring) // 2):
            a, b = ring[i], ring[-1 - i]
            if a is not None and b is not None:
                home, away = (a, b) if (round_index + i) % 2 else (b, a)
                games.append(_fixture(round_index + 1, home, away))
        ring = [ring[0], ring[-1], *ring[1:-1]]
    if double:
        offset = len(ring) - 1
        games += [_fixture(f["week"] + offset, f["away_id"], f["home_id"]) for f in list(games)]
    return games


def create_campaign(
    name: str, participants: list[dict], rules_season: str, *,
    schedule: str = "double_round_robin", fixtures: list[dict] | None = None,
    historical: dict | None = None,
) -> dict:
    """Create an empty competition, using explicit editions and one rule year.

    Manual fixture sides use ``year/team_id`` keys; historical fixture sides use
    the supplied source's team IDs. Participants receive campaign-local UUIDs.
    """
    if not isinstance(participants, list) or not 2 <= len(participants) <= MAX_PARTICIPANTS:
        raise ValueError("Campaign requires 2..128 participants")
    members = []
    for value in participants:
        if not isinstance(value, dict):
            raise ValueError("Invalid participant")  # noqa: TRY004 - user document validation
        members.append({"id": _id(), "season": _year(value.get("season")),
                        "team_id": _token(value.get("team_id"), "team ID"),
                        "name": _text(value.get("name", value.get("team_id")), "team name"),
                        "conference": _text(value.get("conference", "League"), "conference"),
                        "division": _text(value.get("division", "Division"), "division")})
    c = {"schema_version": SCHEMA_VERSION, "id": _id(), "name": _text(name, "campaign name"),
         "rules_season": _year(rules_season), "kind": "custom", "participants": members,
         "fixtures": [], "locked_definition": None, "revision": 0,
         "archived": False, "postseason": None, "champion_id": None}
    refs = {f"{p['season']}/{p['team_id']}": p["id"] for p in members}
    if len(refs) != len(members):
        raise ValueError("Duplicate exact team edition")
    if historical is not None:
        _historical(c, historical)
    elif schedule in {"single_round_robin", "double_round_robin"}:
        c["fixtures"] = _round_robin([p["id"] for p in members], schedule == "double_round_robin")
    elif schedule == "manual":
        if not isinstance(fixtures, list) or not fixtures:
            raise ValueError("Manual schedule requires fixtures")
        for f in fixtures:
            if not isinstance(f, dict) or f.get("home") not in refs or f.get("away") not in refs:
                raise ValueError("Unknown manual fixture participant")
            c["fixtures"].append(_fixture(f.get("week"), refs[f["home"]], refs[f["away"]]))
    else:
        raise ValueError("Unsupported schedule type")
    return validate_campaign(c)


def duplicate_campaign(campaign: dict, name: str) -> dict:
    """Copy a competition's regular calendar into a fresh, unplayed season."""
    c = validate_campaign(campaign)
    identities = {p["id"]: _id() for p in c["participants"]}
    for participant in c["participants"]:
        participant["id"] = identities[participant["id"]]
    if c.get("followed_participant_id") is not None:
        c["followed_participant_id"] = identities[c["followed_participant_id"]]
    c["fixtures"] = [
        _fixture(f["week"], identities[f["home_id"]], identities[f["away_id"]],
                 **({"source_id": f["source_id"]} if "source_id" in f else {}))
        for f in c["fixtures"] if f["phase"] == "REG"
    ]
    c.update(id=_id(), name=_text(name, "campaign name"), revision=0, archived=False,
             locked_definition=None, postseason=None, champion_id=None)
    return validate_campaign(c)


def edit_schedule(campaign: dict, fixtures: list[dict]) -> dict:
    """Replace an unstarted calendar with reviewed campaign-local participant IDs.

    Editing a historical calendar explicitly turns it into a custom competition;
    it can no longer claim the original template's postseason structure.
    """
    c = validate_campaign(campaign)
    if c["locked_definition"] is not None:
        raise ValueError("Campaign definition is locked after play starts")
    if c["archived"]:
        raise ValueError("Archived campaign cannot edit its schedule")
    if not isinstance(fixtures, list) or not 1 <= len(fixtures) <= MAX_FIXTURES:
        raise ValueError("Schedule requires a bounded, nonempty fixture list")
    participants = {p["id"] for p in c["participants"]}
    rows = []
    for fixture in fixtures:
        if (not isinstance(fixture, dict) or fixture.get("home_id") not in participants
                or fixture.get("away_id") not in participants):
            raise ValueError("Unknown schedule participant")
        rows.append(_fixture(_integer(fixture.get("week"), "fixture week", 1),
                             fixture["home_id"], fixture["away_id"]))
    c["fixtures"] = rows
    c["kind"] = "custom"
    c.pop("template_season", None)
    c.pop("postseason_format", None)
    c["revision"] += 1
    return validate_campaign(c)


def _historical(campaign: dict, source: dict) -> None:
    try:
        season = _year(source["season"])
        weeks = _integer(source["regular_weeks"], "regular weeks", 1)
        games_per_team = _integer(source["games_per_team"], "games per team", 1)
        membership = {team: (conference, division)
                      for conference, divisions in source["divisions"].items()
                      for division, teams in divisions.items() for team in teams}
        all_members = [team for divisions in source["divisions"].values()
                       for teams in divisions.values() for team in teams]
        if (len(membership) != len(all_members) or set(membership) != {p["team_id"] for p in campaign["participants"]}
                or season != campaign["rules_season"] or any(p["season"] != season for p in campaign["participants"])):
            raise ValueError("Historical membership/season inventory is incomplete or mismatched")
        refs = {}
        for p in campaign["participants"]:
            p["conference"], p["division"] = membership[p["team_id"]]
            refs[p["team_id"]] = p["id"]
        counts: Counter = Counter()
        source_ids = set()
        for row in source["games"]:
            if row["phase"] != "REG":
                continue
            source_id = _token(row["game_id"], "source fixture ID")
            if source_id in source_ids or row["home"] not in refs or row["away"] not in refs:
                raise ValueError("Duplicate or unknown historical fixture")
            source_ids.add(source_id)
            week = _integer(row["week"], "historical week", 1)
            if week > weeks:
                raise ValueError("Historical week exceeds calendar")
            campaign["fixtures"].append(_fixture(week, refs[row["home"]], refs[row["away"]], source_id=source_id))
            counts.update((row["home"], row["away"]))
        if counts != Counter({t: games_per_team for t in refs}):
            raise ValueError("Historical regular fixture inventory is incomplete")
        campaign["kind"] = "historical"
        campaign["template_season"] = season
        campaign["postseason_format"] = source.get("postseason_format", "custom")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed historical schedule") from error


def validate_campaign(campaign: dict) -> dict:
    """Return a validated copy, reporting all malformed user documents as ValueError."""
    try:
        return _validate_campaign(campaign)
    except (KeyError, TypeError, AttributeError, RecursionError) as error:
        raise ValueError("Malformed campaign document") from error


def _validate_campaign(campaign: dict) -> dict:
    """Check document structure and dependent identities without storage side effects."""
    if not isinstance(campaign, dict) or type(campaign.get("schema_version")) is not int or campaign.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported campaign schema version")
    c = copy.deepcopy(campaign)
    c["id"] = _token(c.get("id"), "campaign ID")
    c["name"] = _text(c.get("name"), "campaign name")
    c["rules_season"] = _year(c.get("rules_season"))
    _integer(c.get("revision"), "campaign revision")
    if type(c.get("archived")) is not bool or c.get("kind") not in {"historical", "custom"}:
        raise ValueError("Invalid campaign metadata")
    members = c.get("participants")
    if not isinstance(members, list) or not 2 <= len(members) <= MAX_PARTICIPANTS:
        raise ValueError("Campaign requires 2..128 participants")
    ids, editions = set(), set()
    for p in members:
        if not isinstance(p, dict):
            raise ValueError("Invalid participant")  # noqa: TRY004 - user document validation
        pid = _token(p.get("id"), "participant ID")
        p["season"] = _year(p.get("season"))
        edition = (p["season"], _token(p.get("team_id"), "team ID"))
        for field in ("name", "conference", "division"):
            _text(p.get(field), field)
        if pid in ids or edition in editions:
            raise ValueError("Duplicate participant or exact team edition")
        ids.add(pid)
        editions.add(edition)
    followed = c.get("followed_participant_id")
    if followed is not None and (not isinstance(followed, str) or followed not in ids):
        raise ValueError("Unknown followed participant")
    fixtures = c.get("fixtures")
    if not isinstance(fixtures, list) or not 1 <= len(fixtures) <= MAX_FIXTURES:
        raise ValueError("Campaign requires a bounded, nonempty schedule")
    fixture_ids, busy, games = set(), set(), set()
    played = False
    for f in fixtures:
        if not isinstance(f, dict):
            raise ValueError("Invalid fixture")  # noqa: TRY004 - user document validation
        fid = _token(f.get("id"), "fixture ID")
        week = _integer(f.get("week"), "fixture week", 1)
        phase = f.get("phase")
        if not isinstance(phase, str) or not re.fullmatch(r"REG|PLAYOFF-[1-9][0-9]*|FINAL|WC|DIV|CON|SB", phase):
            raise ValueError("Invalid fixture phase")
        if fid in fixture_ids or f.get("home_id") not in ids or f.get("away_id") not in ids or f["home_id"] == f["away_id"]:
            raise ValueError("Duplicate, unknown, or self matchup")
        fixture_ids.add(fid)
        for side in ("home_id", "away_id"):
            slot = (week, f[side])
            if slot in busy:
                raise ValueError("Participant matchup appears more than once in a week")
            busy.add(slot)
        status = f.get("status")
        if status not in {"scheduled", "in_progress", "completed"}:
            raise ValueError("Invalid fixture status")
        if status == "scheduled":
            if f.get("game_id") is not None or f.get("result") is not None:
                raise ValueError("Scheduled fixture cannot contain game/result")
        else:
            played = True
            gid = _token(f.get("game_id"), "game ID")
            if gid in games:
                raise ValueError("Game already belongs to another fixture")
            games.add(gid)
            if status == "in_progress" and f.get("result") is not None:
                raise ValueError("In-progress fixture cannot contain a final")
            if status == "completed":
                f["result"] = _result(f.get("result"))
                if f["result"]["game_id"] != gid:
                    raise ValueError("Result game identity differs from fixture")
                if phase != "REG" and f["result"]["home_score"] == f["result"]["away_score"]:
                    raise ValueError("Postseason final cannot be a tie")
        history = f.get("result_history")
        if not isinstance(history, list) or len(history) > 1000:
            raise ValueError("Invalid result revision history")
        normalized = [_result(r) for r in history]
        if status != "completed" and normalized:
            raise ValueError("Uncompleted fixture cannot have result history")
        if status == "completed" and ([r["revision"] for r in normalized] != list(range(1, f["result"]["revision"]))
                                      or any(r["game_id"] != f["game_id"] for r in normalized)):
            raise ValueError("Result revision history is incomplete or mismatched")
        f["result_history"] = normalized
    if played and not c.get("locked_definition"):
        raise ValueError("Started campaign definition must be locked")
    if c.get("locked_definition") is not None and c["locked_definition"] != _definition(c):
        raise ValueError("Campaign definition is locked after play starts")
    champion = c.get("champion_id")
    if champion is not None and champion not in ids:
        raise ValueError("Unknown champion participant")
    _validate_postseason(c)

    return c


def _find(campaign: dict, fixture_id: str) -> dict:
    for fixture in campaign["fixtures"]:
        if fixture["id"] == fixture_id:
            return fixture
    raise ValueError("Unknown campaign fixture")


def start_fixture(campaign: dict, fixture_id: str, game_id: str) -> dict:
    """Bind one live game to a scheduled fixture; retries preserve that binding."""
    c = validate_campaign(campaign)
    if c["archived"]:
        raise ValueError("Archived campaign cannot start a fixture")
    game_id = _token(game_id, "game ID")
    f = _find(c, fixture_id)
    if f["status"] != "scheduled":
        if f["status"] == "in_progress" and f["game_id"] == game_id:
            return c
        raise ValueError("Fixture is completed or already in progress with another game")
    if any(other["game_id"] == game_id for other in c["fixtures"]):
        raise ValueError("Game already belongs to another fixture")
    f.update(status="in_progress", game_id=game_id)
    _lock(c)
    c["revision"] += 1
    return validate_campaign(c)


def resume_fixture(campaign: dict, fixture_id: str, old_game_id: str, new_game_id: str) -> dict:
    """CAS-rebind a live fixture after restoration allocated a new session ID.

    Restoring an already rebound checkpoint is idempotent. The old identity must
    match the persisted fixture, so a stale tab cannot replace a newer session.
    """
    c = validate_campaign(campaign)
    old_game_id = _token(old_game_id, "expected game ID")
    new_game_id = _token(new_game_id, "restored game ID")
    f = _find(c, fixture_id)
    if f["status"] != "in_progress":
        raise ValueError("Only an in-progress fixture can resume")
    if f["game_id"] == new_game_id:
        return c
    if f["game_id"] != old_game_id:
        raise ValueError("Stale resume: expected game identity has changed")
    if any(other["id"] != fixture_id and other["game_id"] == new_game_id for other in c["fixtures"]):
        raise ValueError("Restored game already belongs to another fixture")
    f["game_id"] = new_game_id
    c["revision"] += 1
    return validate_campaign(c)


def record_result(campaign: dict, fixture_id: str, result: dict, *, replace: bool = False) -> dict:
    """Accept a final once, or explicitly retain/revise a previously accepted final."""
    c = validate_campaign(campaign)
    final = _result(result)
    f = _find(c, fixture_id)
    if f["status"] == "completed":
        same = {k: v for k, v in final.items() if k != "revision"} == {k: v for k, v in f["result"].items() if k != "revision"}
        if same:
            return c
        if not replace:
            raise ValueError("Fixture completed; use explicit replace to correct its result")
        if c["postseason"] is not None:
            raise ValueError("Results are frozen after postseason seeding")
        if f["game_id"] != final["game_id"]:
            raise ValueError("Result correction must preserve game identity")
        f["result_history"].append(f["result"])
        final["revision"] = f["result"]["revision"] + 1
    else:
        final["revision"] = 1
        if c["archived"]:
            raise ValueError("Archived campaign cannot accept a new result")
        if f["game_id"] is not None and f["game_id"] != final["game_id"]:
            raise ValueError("Result does not match in-progress game")
    if any(other["id"] != fixture_id and other["game_id"] == final["game_id"] for other in c["fixtures"]):
        raise ValueError("Game already belongs to another fixture")
    if f["phase"] != "REG" and final["home_score"] == final["away_score"]:
        raise ValueError("Postseason final cannot be a tie")
    f.update(status="completed", game_id=final["game_id"], result=final)
    _lock(c)
    c["revision"] += 1
    return validate_campaign(c)


def _record(row: dict, scope: str, outcome: str) -> None:
    row[scope][outcome] += 1


def campaign_view(campaign: dict) -> dict:
    """Derive regular-season standings, supported team totals, rates and leaders."""
    c = validate_campaign(campaign)
    rows, stat_rows = {}, {}
    for p in c["participants"]:
        base = {"participant_id": p["id"], "name": p["name"], "season": p["season"],
                "team_id": p["team_id"], "conference": p["conference"], "division": p["division"]}
        rows[p["id"]] = {**base, "played": 0, "wins": 0, "losses": 0, "ties": 0,
                          "points_for": 0, "points_against": 0,
                          **{s: {k: 0 for k in ("wins", "losses", "ties")}
                             for s in ("home", "away", "division_record", "conference_record")}}
        stat_rows[p["id"]] = {**base, "stat_games": 0, "_turnover_pair": [0, 0, 0], "_fg_pairs": {"offense": [0, 0, 0], "defense": [0, 0, 0]},
                               "_rate_pairs": {side: {rate: [0] * (len(inputs) + 1) for rate, inputs in ALL_RATE_INPUTS.items()} for side in ("offense", "defense")},
                               "offense": {k: None for k in (*STAT_FIELDS, "points_scored")},
                               "defense": {k: None for k in (*STAT_FIELDS, "points_scored")},
                               "offense_games": {k: 0 for k in (*STAT_FIELDS, "points_scored")},
                               "defense_games": {k: 0 for k in (*STAT_FIELDS, "points_scored")}}
    members = {p["id"]: p for p in c["participants"]}
    for f in c["fixtures"]:
        if f["phase"] != "REG" or f["status"] != "completed":
            continue
        r = f["result"]
        for side, other in (("home", "away"), ("away", "home")):
            pid, opponent = f[side + "_id"], f[other + "_id"]
            row = rows[pid]
            score, allowed = r[side + "_score"], r[other + "_score"]
            outcome = "wins" if score > allowed else "losses" if score < allowed else "ties"
            row["played"] += 1
            row[outcome] += 1
            row["points_for"] += score
            row["points_against"] += allowed
            _record(row, side, outcome)
            if members[pid]["conference"] == members[opponent]["conference"]:
                _record(row, "conference_record", outcome)
                if members[pid]["division"] == members[opponent]["division"]:
                    _record(row, "division_record", outcome)
            stat = stat_rows[pid]
            own_box, opponent_box = r[side + "_stats"] or {}, r[other + "_stats"] or {}
            if "turnovers" in own_box and "turnovers" in opponent_box:
                stat["_turnover_pair"][0] += own_box["turnovers"]
                stat["_turnover_pair"][1] += opponent_box["turnovers"]
                stat["_turnover_pair"][2] += 1
            if r[side + "_stats"]:
                stat["stat_games"] += 1
            for category, box in (("offense", r[side + "_stats"]), ("defense", r[other + "_stats"])):
                scored = r[side + "_score"] if category == "offense" else r[other + "_score"]
                for field, value in {**(box or {}), "points_scored": scored}.items():
                    previous = stat[category][field]
                    stat[category][field] = max(previous or 0, value) if field in MAX_FIELDS else (previous or 0) + value
                    stat[category + "_games"][field] += 1
    for row in rows.values():
        row["win_pct"] = (row["wins"] + row["ties"] / 2) / row["played"] if row["played"] else 0.0
        row["point_diff"] = row["points_for"] - row["points_against"]
        for scope in ("home", "away", "division_record", "conference_record"):
            value = row[scope]
            row[scope + "_record" if scope in {"home", "away"} else scope] = "-".join(str(value[k]) for k in ("wins", "losses", "ties"))
        del row["home"], row["away"]
    # Percentages use only games that recorded both numerator and denominator.
    for fixture in c["fixtures"]:
        if fixture["phase"] != "REG" or fixture["status"] != "completed":
            continue
        for side, opponent in (("home", "away"), ("away", "home")):
            box = fixture["result"].get(side + "_stats") or {}
            for rate, inputs in ALL_RATE_INPUTS.items():
                if not all(key in box for key in inputs):
                    continue
                for pid, category in ((fixture[side + "_id"], "offense"), (fixture[opponent + "_id"], "defense")):
                    pair = stat_rows[pid]["_rate_pairs"][category][rate]
                    for index, key in enumerate(inputs):
                        pair[index] += box[key]
                    pair[-1] += 1
            if "field_goals_attempted" not in box or "field_goals_made" not in box:
                continue
            for pid, category in ((fixture[side + "_id"], "offense"), (fixture[opponent + "_id"], "defense")):
                pair = stat_rows[pid]["_fg_pairs"][category]
                pair[0] += box["field_goals_made"]
                pair[1] += box["field_goals_attempted"]
                pair[2] += 1
    for row in stat_rows.values():
        giveaways, takeaways, games = row.pop("_turnover_pair")
        row["turnover_summary"] = {"giveaways": giveaways if games else None,
                                   "takeaways": takeaways if games else None,
                                   "differential": takeaways - giveaways if games else None,
                                   "games": games}
        for category in ("offense", "defense"):
            row[category + "_per_game"] = {
                field: (total if field in MAX_FIELDS else total / row[category + "_games"][field]) if row[category + "_games"][field] else None
                for field, total in row[category].items()}
        for category, rates in row.pop("_rate_pairs").items():
            for rate, paired in rates.items():
                value = _efficiency(rate, paired[:-1])
                row[category][rate] = value
                row[category + "_per_game"][rate] = value
                row[category + "_games"][rate] = paired[-1]
        pairs = row.pop("_fg_pairs")
        for category, (made, attempted, games) in pairs.items():
            percentage = 100 * made / attempted if attempted else None
            row[category]["field_goal_percentage"] = percentage
            row[category + "_per_game"]["field_goal_percentage"] = percentage
            row[category + "_games"]["field_goal_percentage"] = games
    ordered = sorted(rows.values(), key=lambda r: (-r["win_pct"], -r["point_diff"], -r["points_for"], r["name"], r["season"], r["team_id"]))
    leaders = {}
    categories = {
        "scoring_offense": (None, "points_for", False),
        "scoring_defense": (None, "points_against", True),
        "total_offense": ("offense", "total_yards", False),
        "rushing_offense": ("offense", "rushing_yards", False),
        "passing_offense": ("offense", "net_passing_yards", False),
        "giveaways": ("offense", "turnovers", True),
        "total_defense": ("defense", "total_yards", True),
    }
    for name, (category, field, ascending) in categories.items():
        entries = []
        for pid, row in rows.items():
            n = row["played"] if category is None else stat_rows[pid][category + "_games"][field]
            if not n:
                continue
            total = row[field] if category is None else stat_rows[pid][category][field]
            entries.append({"participant_id": pid, "name": row["name"], "season": row["season"],
                            "team_id": row["team_id"], "value": total / n, "total": total, "games": n})
        entries.sort(key=lambda e: (e["value"] if ascending else -e["value"], e["name"], e["season"], e["team_id"]))
        for index, entry in enumerate(entries):
            entry["rank"] = entries[index - 1]["rank"] if index and entry["value"] == entries[index - 1]["value"] else index + 1
        leaders[name] = entries
    return {**c, "standings": ordered, "statistics": list(stat_rows.values()), "leaders": leaders,
            "ranking_policy": RANKING_POLICY}


def export_campaign(campaign: dict) -> str:
    """Serialize a validated portable campaign; chart bytes are never embedded."""
    return json.dumps(validate_campaign(campaign), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_object(pairs: list[tuple]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON field")
        value[key] = item
    return value


def import_campaign(text: str) -> dict:
    """Validate before assigning a new identity and rewriting all linked IDs."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise ValueError("Campaign import exceeds size limit")
    try:
        original = json.loads(text, object_pairs_hook=_unique_object,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON value")))
        c = validate_campaign(original)
    except (TypeError, KeyError, RecursionError) as error:
        raise ValueError("Malformed campaign import") from error
    participant_ids = {p["id"]: _id() for p in c["participants"]}
    game_ids = {f["game_id"]: _id() for f in c["fixtures"] if f["game_id"] is not None}
    c["id"] = _id()
    c["revision"] = 0
    for p in c["participants"]:
        p["id"] = participant_ids[p["id"]]
    if c.get("followed_participant_id") is not None:
        c["followed_participant_id"] = participant_ids[c["followed_participant_id"]]
    for f in c["fixtures"]:
        f["id"] = _id()
        f["home_id"] = participant_ids[f["home_id"]]
        f["away_id"] = participant_ids[f["away_id"]]
        if f["game_id"] is not None:
            f["game_id"] = game_ids[f["game_id"]]
        for r in [*f["result_history"], *([f["result"]] if f["result"] else [])]:
            r["game_id"] = game_ids[r["game_id"]]
    if c["postseason"]:
        c["postseason"]["seed_ids"] = [participant_ids[pid] for pid in c["postseason"]["seed_ids"]]
        if "conference_seeds" in c["postseason"]:
            c["postseason"]["conference_seeds"] = {
                conf: [participant_ids[pid] for pid in seeds]
                for conf, seeds in c["postseason"]["conference_seeds"].items()}
    if c["champion_id"]:
        c["champion_id"] = participant_ids[c["champion_id"]]
    if c["locked_definition"]:
        _lock(c)
    return validate_campaign(c)


HISTORICAL_FORMATS = {"eight_team": (3, 1), "ten_team": (3, 2), "fourteen_team": (4, 3)}


def _postseason_phases(postseason: dict) -> list[str]:
    if postseason["format"] == "generic_single_elimination":
        rounds = len(postseason["seed_ids"]).bit_length() - 1
        return [f"PLAYOFF-{i}" for i in range(1, rounds)] + ["FINAL"]
    return ["DIV", "CON", "SB"] if postseason["format"] == "eight_team" else ["WC", "DIV", "CON", "SB"]


def _winners(campaign: dict, phase: str, conference: str | None = None) -> list[str]:
    members = {p["id"]: p for p in campaign["participants"]}
    fixtures = [f for f in campaign["fixtures"] if f["phase"] == phase
                and (conference is None or members[f["home_id"]]["conference"] == conference)]
    if not fixtures or any(f["status"] != "completed" for f in fixtures):
        return []
    return [f["home_id"] if f["result"]["home_score"] > f["result"]["away_score"] else f["away_id"] for f in fixtures]


def _expected_round(campaign: dict, round_index: int) -> list[tuple[str, str]]:
    ps = campaign["postseason"]
    phases = _postseason_phases(ps)
    phase = phases[round_index - 1]
    if ps["format"] == "generic_single_elimination":
        alive = list(ps["seed_ids"]) if round_index == 1 else _winners(campaign, phases[round_index - 2])
        if len(alive) != len(ps["seed_ids"]) // 2 ** (round_index - 1):
            return []
        alive.sort(key=ps["seed_ids"].index)
        return [(alive[i], alive[-1 - i]) for i in range(len(alive) // 2)]
    if phase == "SB":
        alive = _winners(campaign, "CON")
        return [(alive[0], alive[1])] if len(alive) == 2 else []
    members = {p["id"]: p for p in campaign["participants"]}
    pairs = []
    modern = ps["format"] == "fourteen_team"
    for conference, seeds in ps["conference_seeds"].items():
        if phase == "WC":
            pairs.extend([(seeds[1], seeds[6]), (seeds[2], seeds[5]), (seeds[3], seeds[4])]
                         if modern else [(seeds[3], seeds[4])])
        elif phase == "DIV":
            if modern:
                wild = _winners(campaign, "WC", conference)
                if len(wild) != 3:
                    return []
                alive = sorted([seeds[0], *wild], key=seeds.index)
                pairs.extend([(alive[0], alive[3]), (alive[1], alive[2])])
            else:
                wilds = [seeds[3]] if ps["format"] == "eight_team" else _winners(campaign, "WC", conference)
                if len(wilds) != 1:
                    return []
                wildcard = wilds[0]
                same_division = members[wildcard]["division"] == members[seeds[0]]["division"]
                pairs.extend([(seeds[0], seeds[2]), (seeds[1], wildcard)] if same_division else
                             [(seeds[0], wildcard), (seeds[1], seeds[2])])
        else:
            alive = _winners(campaign, "DIV", conference)
            if len(alive) != 2:
                return []
            alive.sort(key=seeds.index)
            pairs.append((alive[0], alive[1]))
    return pairs


def _validate_postseason(campaign: dict) -> None:
    ps = campaign.get("postseason")
    playoff_fixtures = [f for f in campaign["fixtures"] if f["phase"] != "REG"]
    if ps is None:
        if playoff_fixtures or campaign.get("champion_id") is not None:
            raise ValueError("Postseason fixtures require postseason metadata")
        return
    if not isinstance(ps, dict) or ps.get("format") not in {"generic_single_elimination", *HISTORICAL_FORMATS}:
        raise ValueError("Invalid postseason format")
    seeds = ps.get("seed_ids")
    ids = {p["id"] for p in campaign["participants"]}
    if (not isinstance(seeds, list) or len(seeds) < 2 or any(not isinstance(pid, str) for pid in seeds)
            or len(seeds) != len(set(seeds)) or not set(seeds) <= ids):
        raise ValueError("Invalid postseason seed inventory")
    if ps["format"] == "generic_single_elimination":
        if len(seeds) & (len(seeds) - 1):
            raise ValueError("Generic postseason requires power-of-two seeds")
    else:
        confs = ps.get("conference_seeds")
        division_count, wildcards = HISTORICAL_FORMATS[ps["format"]]
        members = {p["id"]: p for p in campaign["participants"]}
        if not isinstance(confs, dict) or len(confs) != 2:
            raise ValueError("Historical postseason requires two conferences")
        flattened = []
        for conf, order in confs.items():
            if (not isinstance(order, list) or len(order) != division_count + wildcards
                    or any(pid not in ids or members[pid]["conference"] != conf for pid in order)
                    or len({members[pid]["division"] for pid in order[:division_count]}) != division_count):
                raise ValueError("Historical conference seed inventory differs from format")
            flattened.extend(order)
        if flattened != seeds:
            raise ValueError("Historical seed inventory is inconsistent")
    regular = [f for f in campaign["fixtures"] if f["phase"] == "REG"]
    if any(f["status"] != "completed" for f in regular):
        raise ValueError("Regular season must complete before postseason")
    phases = _postseason_phases(ps)
    round_index = _integer(ps.get("round"), "postseason round", 1)
    if round_index > len(phases):
        raise ValueError("Invalid postseason round")
    observed_phases = {f["phase"] for f in playoff_fixtures}
    if observed_phases != set(phases[:round_index]):
        raise ValueError("Missing or extra postseason round")
    start_week = max(f["week"] for f in regular)
    for index in range(1, round_index + 1):
        expected = _expected_round(campaign, index)
        actual = [(f["home_id"], f["away_id"]) for f in playoff_fixtures if f["phase"] == phases[index - 1]]
        if not expected or Counter(actual) != Counter(expected):
            raise ValueError("Postseason participants do not match seeds or preceding winners")
        if any(f["week"] != start_week + index for f in playoff_fixtures if f["phase"] == phases[index - 1]):
            raise ValueError("Postseason round is outside its calendar week")
    champion = campaign.get("champion_id")
    if champion is not None and (round_index != len(phases) or _winners(campaign, phases[-1]) != [champion]):
        raise ValueError("Champion must be the completed final winner")


def seed_postseason(campaign: dict, *, size: int = 4) -> dict:
    """Seed supported historical formats or a custom power-of-two bracket.

    Historical seasons use their format's conference/division slots. Both paths
    use the displayed practical ranking, never forced historical participants.
    """
    c = validate_campaign(campaign)
    if c["postseason"] is not None:
        raise ValueError("Postseason already seeded")
    if c["archived"]:
        raise ValueError("Archived campaign cannot seed postseason")
    if any(f["status"] != "completed" for f in c["fixtures"] if f["phase"] == "REG"):
        raise ValueError("Regular schedule must complete before postseason")
    ranked = campaign_view(c)["standings"]
    format_name = c.get("postseason_format") if c["kind"] == "historical" else None
    if format_name in HISTORICAL_FORMATS:
        division_count, wildcards = HISTORICAL_FORMATS[format_name]
        confs = sorted({p["conference"] for p in c["participants"]})
        conference_seeds = {}
        if len(confs) != 2:
            raise ValueError("Historical postseason requires two conferences")
        for conf in confs:
            teams = [r for r in ranked if r["conference"] == conf]
            divisions = {r["division"] for r in teams}
            if len(divisions) != division_count or len(teams) < division_count + wildcards:
                raise ValueError("Historical membership differs from postseason format")
            winners = {next(r["participant_id"] for r in teams if r["division"] == div) for div in divisions}
            order = [r["participant_id"] for r in teams if r["participant_id"] in winners]
            order += [r["participant_id"] for r in teams if r["participant_id"] not in winners][:wildcards]
            conference_seeds[conf] = order
        seeds = [pid for order in conference_seeds.values() for pid in order]
        c["postseason"] = {"seed_ids": seeds, "round": 1, "format": format_name,
                           "conference_seeds": conference_seeds}
    else:
        if type(size) is not int or size < 2 or size > len(c["participants"]) or size & (size - 1):
            raise ValueError("Postseason size must be an available power of two")
        seeds = [r["participant_id"] for r in ranked[:size]]
        c["postseason"] = {"seed_ids": seeds, "round": 1, "format": "generic_single_elimination"}
    week = max(f["week"] for f in c["fixtures"]) + 1
    phase = _postseason_phases(c["postseason"])[0]
    c["fixtures"] += [_fixture(week, home, away, phase) for home, away in _expected_round(c, 1)]
    c["revision"] += 1
    return validate_campaign(c)


def advance_postseason(campaign: dict) -> dict:
    """Advance only completed winners; preserve byes, reseeding and round identity."""
    c = validate_campaign(campaign)
    if c["postseason"] is None:
        raise ValueError("Postseason has not been seeded")
    if c["archived"]:
        raise ValueError("Archived campaign cannot advance postseason")
    ps = c["postseason"]
    phases = _postseason_phases(ps)
    current_phase = phases[ps["round"] - 1]
    current = [f for f in c["fixtures"] if f["phase"] == current_phase]
    if any(f["status"] != "completed" for f in current) or c["champion_id"] is not None:
        return c
    if current_phase == phases[-1]:
        c["champion_id"] = _winners(c, current_phase)[0]
    else:
        ps["round"] += 1
        phase = phases[ps["round"] - 1]
        week = max(f["week"] for f in c["fixtures"] if f["phase"] == "REG") + ps["round"]
        c["fixtures"] += [_fixture(week, home, away, phase, neutral=phase == "SB")
                          for home, away in _expected_round(c, ps["round"])]
    c["revision"] += 1
    return validate_campaign(c)

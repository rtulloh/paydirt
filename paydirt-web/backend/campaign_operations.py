"""Browser-owned campaign operations shared by HTTP and worker transports.

Campaign documents are client-owned. No unscoped server-global campaign database
is exposed. The pure Python domain validates every document before use.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from operations import OperationError, OperationRegistry
from pydantic import BaseModel, Field

from paydirt.campaigns import (
    advance_postseason,
    campaign_view,
    create_campaign,
    duplicate_campaign,
    edit_schedule,
    export_campaign,
    import_campaign,
    record_result,
    resume_fixture,
    seed_postseason,
    start_fixture,
    validate_campaign,
)
from paydirt.season_rules import load_season_rules


class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    participants: list[dict[str, Any]] = Field(default_factory=list, max_length=64)
    rules_season: str = "2026"
    schedule: str = "double_round_robin"
    fixtures: list[dict[str, Any]] | None = None
    template: str | None = None


class CampaignRequest(BaseModel):
    campaign: dict[str, Any]


class StartCampaignRequest(CampaignRequest):
    fixture_id: str
    human_is_home: bool = True
    difficulty: str = "medium"


class CompleteCampaignRequest(CampaignRequest):
    fixture_id: str
    game_id: str


class CorrectCampaignRequest(CompleteCampaignRequest):
    expected_result_revision: int = Field(ge=1)


class DuplicateCampaignRequest(CampaignRequest):
    name: str = Field(min_length=1, max_length=100)


class DefinitionCampaignRequest(CampaignRequest):
    fixtures: list[dict[str, Any]] = Field(min_length=1, max_length=20000)


class ResumeCampaignRequest(CampaignRequest):
    fixture_id: str
    old_game_id: str
    new_game_id: str


class PostseasonCampaignRequest(CampaignRequest):
    size: int = 4


class SimulateCampaignRequest(CampaignRequest):
    fixture_id: str


class CampaignBundleRequest(CampaignRequest):
    games: list[dict[str, Any]] = Field(default_factory=list, max_length=256)


MAX_BUNDLE_BYTES = 32 * 1024 * 1024


class ImportCampaignRequest(BaseModel):
    text: str = Field(max_length=MAX_BUNDLE_BYTES)


def _domain(function: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except (ValueError, KeyError, TypeError) as error:
        raise OperationError(422, str(error)) from error


def create_custom(request: CreateCampaignRequest) -> dict:
    """Create an empty custom competition; no historical outcomes are imported."""
    return _domain(create_campaign, request.name, request.participants, request.rules_season,
                   schedule=request.schedule, fixtures=request.fixtures)


def view_campaign(request: CampaignRequest) -> dict:
    """Compute standings and aggregates in Python from validated final results."""
    return _domain(campaign_view, request.campaign)


def _catalog(context: Any, participant: dict) -> tuple[Path, Path]:
    directory = context._find_season_dir(str(participant["season"]))
    team = context._team_directory(directory, participant["team_id"]) if directory else None
    if directory is None or team is None:
        raise OperationError(404, "A selected team edition is unavailable; no replacement was made")
    return directory, team


def load_template(year: str, context: Any) -> dict:
    """Load only explicitly supported complete historical calendars."""
    if year not in {"1983", "2024"}:
        raise OperationError(404, "Unknown historical template")
    # The path is fixed by the supported catalog, never supplied by an import.
    path = Path(__file__).resolve().parents[2] / "config" / "season-schedules" / f"{year}.json"
    if not path.is_file():
        raise OperationError(404, "Historical template is not installed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    participants = []
    for conference, divisions in spec["divisions"].items():
        for division, teams in divisions.items():
            for team_id in teams:
                directory, _ = _catalog(context, {"season": year, "team_id": team_id})
                info = context.load_team_info(directory, team_id)
                participants.append({"season": year, "team_id": team_id, "name": info.name,
                                     "conference": conference, "division": division})
    load_season_rules(context._find_season_dir(year))
    return {"season": year, "participants": participants, "spec": spec}


async def start_campaign(request: StartCampaignRequest, context: Any) -> dict:
    """Start a fixture once, binding its actual engine session to the campaign."""
    campaign = _domain(validate_campaign, request.campaign)
    if campaign["archived"]:
        raise OperationError(409, "Archived seasons cannot start games")
    fixture = next((f for f in campaign["fixtures"] if f["id"] == request.fixture_id), None)
    if not fixture or fixture["status"] != "scheduled":
        raise OperationError(409, "Fixture is not unplayed; resume its saved game instead")
    participants = {p["id"]: p for p in campaign["participants"]}
    home, away = participants[fixture["home_id"]], participants[fixture["away_id"]]
    _catalog(context, home)
    _catalog(context, away)
    rules_dir = context._find_season_dir(campaign["rules_season"])
    if rules_dir is None:
        raise OperationError(404, "Campaign rules year is unavailable")
    rules = load_season_rules(rules_dir)
    player, opponent = (home, away) if request.human_is_home else (away, home)
    result = await context.new_game(context.NewGameRequest(
        season=player["season"], player_season=player["season"], opponent_season=opponent["season"],
        player_team=player["team_id"], opponent_team=opponent["team_id"],
        play_as_home=request.human_is_home, difficulty=request.difficulty,
        player_end_zone_interception_policy="ask", opponent_end_zone_interception_policy="auto",
    ))
    game_id = result.game_id
    game = context.games[game_id]
    # The existing core owns the rule object and all decisions. Both CPU coaches
    # must use that same rulebook, not the years of their individual charts.
    game["engine"].season_rules = rules
    game["engine"].state.is_playoff = fixture["phase"] != "REG"
    for key in ("ai", "cpu_ai", "home_ai", "away_ai"):
        if game.get(key) is not None:
            game[key].ai_behavior = rules.ai_behavior
    game["campaign_id"] = campaign["id"]
    game["fixture_id"] = fixture["id"]
    game["rules_season"] = campaign["rules_season"]
    campaign = _domain(start_fixture, campaign, fixture["id"], game_id)
    return {"campaign": campaign, "game_id": game_id,
            "game_state": context.game_state_to_response(game), "play_history": [], "game_phase": "coinToss"}


def _final_team_stats(stats: Any) -> dict:
    """Keep unknown legacy turnover components distinct from measured zeroes."""
    box = asdict(stats)
    if getattr(stats, "_extended_team_stats", None) is not None:
        box.update(stats._extended_team_stats)
    if getattr(stats, "_offensive_attempt_stats", None) is not None:
        box.update(stats._offensive_attempt_stats)
    if getattr(stats, "_field_goal_stats", None) is not None:
        box.update(stats._field_goal_stats)
    if not getattr(stats, "_turnover_breakdown_complete", True):
        box["interceptions_thrown"] = None
        box["fumbles_lost"] = None
    return box


def complete_campaign(request: CompleteCampaignRequest, context: Any, *, correction: bool = False) -> dict:
    """Accept only the legal final from this fixture's linked session."""
    campaign = _domain(validate_campaign, request.campaign)
    game = _linked_game(context, campaign, request.fixture_id, request.game_id)
    engine = game["engine"]
    if (not engine.state.game_over or engine.has_untimed_down()
            or engine.pending_post_score_action()
            or getattr(engine, "has_pending_end_zone_interception", False)
            or getattr(getattr(engine, "_last_play_outcome", None), "pending_penalty_decision", False)):
        raise OperationError(409, "Game does not have a legal final yet")
    fixture = next(f for f in campaign["fixtures"] if f["id"] == request.fixture_id)
    result = {"game_id": fixture["game_id"] if correction else request.game_id, "home_score": engine.state.home_score,
              "away_score": engine.state.away_score, "home_stats": _final_team_stats(engine.state.home_stats),
              "away_stats": _final_team_stats(engine.state.away_stats), "source": "played", "final": True}
    return _domain(record_result, campaign, request.fixture_id, result, replace=correction)


def correct_campaign(request: CorrectCampaignRequest, context: Any) -> dict:
    """Explicitly revise a final from a linked engine, preserving ledger identity.

    Restoring a checkpoint allocates a new runtime session. Edition/rules/linkage
    still require validation; only its accepted fixture identity stays stable.
    No request-supplied score or statistics are accepted.
    """
    campaign = _domain(validate_campaign, request.campaign)
    fixture = next((f for f in campaign["fixtures"] if f["id"] == request.fixture_id), None)
    if fixture is None or fixture["status"] != "completed":
        raise OperationError(409, "Only a completed result can be corrected")
    if fixture["result"]["revision"] != request.expected_result_revision:
        raise OperationError(409, "Result revision changed; reopen it before correcting")
    return complete_campaign(request, context, correction=True)


def _catalog_campaign(context: Any, campaign: dict) -> None:
    for participant in campaign["participants"]:
        _catalog(context, participant)
    rules_dir = context._find_season_dir(campaign["rules_season"])
    if rules_dir is None:
        raise OperationError(404, "Campaign rules year is unavailable")
    try:
        load_season_rules(rules_dir)
    except (OSError, ValueError) as error:
        raise OperationError(404, "Campaign rules year is unavailable") from error


def _linked_game(context: Any, campaign: dict, fixture_id: str, game_id: str) -> dict:
    fixture = next((f for f in campaign["fixtures"] if f["id"] == fixture_id), None)
    game = context.games.get(game_id)
    if (fixture is None or game is None or game.get("campaign_id") != campaign["id"]
            or game.get("fixture_id") != fixture_id):
        raise OperationError(409, "Restored game is not linked to this campaign fixture")
    members = {p["id"]: p for p in campaign["participants"]}
    for side in ("home", "away"):
        member = members[fixture[side + "_id"]]
        team = game[side + "_team"]
        if str(team.season) != member["season"] or team.id != member["team_id"]:
            raise OperationError(409, "Restored game team edition differs from fixture")
    if (str(game["engine"].season_rules.season) != campaign["rules_season"]
            or bool(game["engine"].state.is_playoff) != (fixture["phase"] != "REG")):
        raise OperationError(409, "Restored game rules differ from fixture")
    return game


def simulate_campaign(request: SimulateCampaignRequest, context: Any) -> dict:
    """Run one unplayed fixture; persistence and cancellation happen between fixtures."""
    from uuid import uuid4

    from paydirt.campaign_simulation import simulate_game

    campaign = _domain(validate_campaign, request.campaign)
    if campaign["archived"]:
        raise OperationError(409, "Archived seasons cannot simulate games")
    fixture = next((f for f in campaign["fixtures"] if f["id"] == request.fixture_id), None)
    if fixture is None or fixture["status"] != "scheduled":
        raise OperationError(409, "Only an unplayed fixture can be simulated")
    _catalog_campaign(context, campaign)
    members = {p["id"]: p for p in campaign["participants"]}
    _, home = _catalog(context, members[fixture["home_id"]])
    _, away = _catalog(context, members[fixture["away_id"]])
    try:
        engine = simulate_game(home, away, context._find_season_dir(campaign["rules_season"]),
                               is_playoff=fixture["phase"] != "REG")
    except (ValueError, RuntimeError, OSError) as error:
        raise OperationError(422, f"Simulation did not complete: {error}") from error
    final = {"game_id": str(uuid4()), "home_score": engine.state.home_score,
             "away_score": engine.state.away_score, "home_stats": _final_team_stats(engine.state.home_stats),
             "away_stats": _final_team_stats(engine.state.away_stats), "source": "simulated", "final": True}
    return _domain(record_result, campaign, fixture["id"], final)


def _json_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate import field")
        result[key] = value
    return result


def _parse_bundle(text: str) -> tuple[dict, list[dict]]:
    if len(text.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise ValueError("Campaign bundle exceeds size limit")
    def reject_constant(_value: str) -> None:
        raise ValueError("Non-finite import value")
    data = json.loads(text, object_pairs_hook=_json_object, parse_constant=reject_constant)
    if isinstance(data, dict) and data.get("format") == "paydirt-campaign":
        if (type(data.get("version")) is not int or data["version"] != 1
                or set(data) != {"format", "version", "campaign", "games"}
                or not isinstance(data["games"], list) or len(data["games"]) > 256):
            raise ValueError("Invalid campaign bundle format")
        return validate_campaign(data["campaign"]), data["games"]
    return validate_campaign(data), []


async def import_bundle(request: ImportCampaignRequest, context: Any) -> dict:
    """Validate edition-bound checkpoints, then remap every imported relationship.

    Typed checkpoint validation constructs temporary trusted sessions without
    playing any actions. They are removed in finally; import never leaves active
    engines registered and never alters an existing game or campaign.
    """
    original, saved_games = _domain(_parse_bundle, request.text)
    _catalog_campaign(context, original)
    in_progress = {f["id"]: f for f in original["fixtures"] if f["status"] == "in_progress"}
    if len(saved_games) != len(in_progress):
        raise OperationError(422, "Every in-progress fixture requires exactly one saved checkpoint")
    # Domain import rejects invalid revisions/identities before remapping.
    imported = _domain(import_campaign, export_campaign(original))
    remapped = {old["id"]: new for old, new in zip(original["fixtures"], imported["fixtures"])}
    output, seen_fixtures, seen_saves = [], set(), set()
    for saved in saved_games:
        if not isinstance(saved, dict) or not isinstance(saved.get("metadata"), dict):
            raise OperationError(422, "Invalid saved checkpoint record")
        metadata = saved["metadata"]
        fixture_id = metadata.get("fixtureId")
        if (not isinstance(fixture_id, str) or fixture_id not in in_progress
                or fixture_id in seen_fixtures or not isinstance(saved.get("id"), str)
                or not saved["id"] or saved["id"] in seen_saves
                or metadata.get("campaignId") != original["id"]
                or metadata.get("gameId") != in_progress[fixture_id]["game_id"]
                or not isinstance(saved.get("checkpoint"), str)):
            raise OperationError(422, "Saved checkpoint does not match an in-progress fixture")
        phase = metadata.get("phase", "playing")
        if phase not in {"coinToss", "playing", "halftime", "gameOver"}:
            raise OperationError(422, "Invalid saved game phase")
        seen_fixtures.add(fixture_id)
        seen_saves.add(saved["id"])
        temporary_id = None
        try:
            restored = await context.restore_game_checkpoint(context.RestoreCheckpointRequest(checkpoint=saved["checkpoint"]))
            temporary_id = restored["game_id"]
            game = _linked_game(context, original, fixture_id, temporary_id)
            new_fixture = remapped[fixture_id]
            game["campaign_id"] = imported["id"]
            game["fixture_id"] = new_fixture["id"]
            checkpoint = await context.checkpoint_game(temporary_id)
            name = saved.get("name", imported["name"])
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                raise OperationError(422, "Invalid saved game name")
            home = game["home_team"]
            away = game["away_team"]
            output.append({"id": new_fixture["game_id"], "name": name, "checkpoint": checkpoint["checkpoint"],
                           "revision": 1, "savedAt": datetime.now(timezone.utc).isoformat(),
                           "metadata": {"campaignId": imported["id"], "fixtureId": new_fixture["id"],
                                        "gameId": new_fixture["game_id"], "phase": phase,
                                        "gameOver": bool(game["engine"].state.game_over),
                                        "homeTeam": home.model_dump(), "awayTeam": away.model_dump()}})
        finally:
            if temporary_id is not None:
                context.games.pop(temporary_id, None)
    return {"campaign": imported, "games": output}


def register_campaign_operations(registry: OperationRegistry, context: Any) -> None:
    """Register commands once, before the native router is built."""
    @registry.get("/api/campaign/templates")
    async def templates() -> dict:
        available = []
        for year in ("1983", "2024"):
            try:
                loaded = load_template(year, context)
                available.append({"season": year, "teams": len(loaded["participants"]),
                                  "weeks": loaded["spec"]["regular_weeks"]})
            except (OperationError, ValueError, OSError):
                continue
        return {"templates": available}

    @registry.post("/api/campaign/create")
    async def create(request: CreateCampaignRequest) -> dict:
        if request.template:
            loaded = load_template(request.template, context)
            return _domain(create_campaign, request.name, loaded["participants"], loaded["season"],
                           historical=loaded["spec"])
        campaign = create_custom(request)
        _catalog_campaign(context, campaign)
        return campaign

    @registry.post("/api/campaign/view")
    async def view(request: CampaignRequest) -> dict:
        return view_campaign(request)

    @registry.post("/api/campaign/duplicate")
    async def duplicate(request: DuplicateCampaignRequest) -> dict:
        campaign = _domain(duplicate_campaign, request.campaign, request.name)
        _catalog_campaign(context, campaign)
        return campaign

    @registry.post("/api/campaign/definition")
    async def definition(request: DefinitionCampaignRequest) -> dict:
        campaign = _domain(edit_schedule, request.campaign, request.fixtures)
        _catalog_campaign(context, campaign)
        return campaign

    @registry.post("/api/campaign/correct")
    async def correct(request: CorrectCampaignRequest) -> dict:
        return correct_campaign(request, context)

    @registry.post("/api/campaign/start")
    async def start(request: StartCampaignRequest) -> dict:
        return await start_campaign(request, context)

    @registry.post("/api/campaign/complete")
    async def complete(request: CompleteCampaignRequest) -> dict:
        return complete_campaign(request, context)

    @registry.post("/api/campaign/resume")
    async def resume(request: ResumeCampaignRequest) -> dict:
        campaign = _domain(validate_campaign, request.campaign)
        _linked_game(context, campaign, request.fixture_id, request.new_game_id)
        return _domain(resume_fixture, campaign, request.fixture_id, request.old_game_id, request.new_game_id)

    @registry.post("/api/campaign/postseason")
    async def postseason(request: PostseasonCampaignRequest) -> dict:
        if request.campaign.get("postseason") is not None:
            return _domain(advance_postseason, request.campaign)
        return _domain(seed_postseason, request.campaign, size=request.size)

    @registry.post("/api/campaign/simulate")
    async def simulate(request: SimulateCampaignRequest) -> dict:
        return simulate_campaign(request, context)

    @registry.post("/api/campaign/export")
    async def export_document(request: CampaignBundleRequest) -> dict:
        bundle = {"format": "paydirt-campaign", "version": 1,
                  "campaign": request.campaign, "games": request.games}
        text = json.dumps(bundle, allow_nan=False, separators=(",", ":"))
        # Validate the same portable artifact the importer consumes. Validation
        # temporary sessions are removed before the command returns.
        await import_bundle(ImportCampaignRequest(text=text), context)
        return {"text": text}

    @registry.post("/api/campaign/import")
    async def import_document(request: ImportCampaignRequest) -> dict:
        return await import_bundle(request, context)

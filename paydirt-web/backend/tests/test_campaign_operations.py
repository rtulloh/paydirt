"""Campaign operations record engine finals, never client-provided scores."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import SimpleNamespace

import pytest
import routes  # Initializes the application import path.
from operations import OperationError, OperationRegistry

ops = import_module("campaign_operations")

PARTICIPANTS = [
    {"season": "2026", "team_id": "Ironclads", "name": "Ironclads"},
    {"season": "2026", "team_id": "Thunderhawks", "name": "Thunderhawks"},
]


def create():
    return ops.create_custom(ops.CreateCampaignRequest(
        name="My season", participants=PARTICIPANTS, rules_season="2026"))


def test_duplicate_and_definition_commands_are_public_and_validate_before_play():
    original = create()
    duplicate = run(handler(routes, "/api/campaign/duplicate")(
        ops.DuplicateCampaignRequest(campaign=original, name="Fresh start")))
    assert duplicate["id"] != original["id"]
    fixture = duplicate["fixtures"][0]
    edited = run(handler(routes, "/api/campaign/definition")(
        ops.DefinitionCampaignRequest(campaign=duplicate, fixtures=[{
            "week": 8, "home_id": fixture["away_id"], "away_id": fixture["home_id"]}])))
    assert edited["fixtures"][0]["week"] == 8
    assert original["fixtures"][0]["week"] == 1


def test_explicit_correction_uses_engine_final_and_retains_prior_revision(isolated_games):
    original = create()
    fixture = original["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(
        campaign=original, fixture_id=fixture["id"]), routes))
    engine = routes.games[started["game_id"]]["engine"]
    engine.state.game_over = True
    engine.state.quarter = 4
    engine.state.time_remaining = 0
    engine.state.home_score, engine.state.away_score = 21, 14
    completed = ops.complete_campaign(ops.CompleteCampaignRequest(
        campaign=started["campaign"], fixture_id=fixture["id"], game_id=started["game_id"]), routes)
    # A restored/corrected authoritative engine receives a fresh runtime ID.
    restored = run(routes.restore_game_checkpoint(routes.RestoreCheckpointRequest(
        checkpoint=run(routes.checkpoint_game(started["game_id"]))["checkpoint"])))
    routes.games[restored["game_id"]]["engine"].state.home_score = 24
    corrected = run(handler(routes, "/api/campaign/correct")(
        ops.CorrectCampaignRequest(campaign=completed, fixture_id=fixture["id"],
            game_id=restored["game_id"], expected_result_revision=1)))
    accepted = corrected["fixtures"][0]
    assert accepted["game_id"] == started["game_id"]
    assert accepted["result"]["home_score"] == 24
    assert accepted["result"]["revision"] == 2
    assert accepted["result_history"][0]["home_score"] == 21
    assert next(row for row in ops.view_campaign(ops.CampaignRequest(campaign=corrected))["standings"]
                if row["participant_id"] == fixture["home_id"])["points_for"] == 24
    with pytest.raises(OperationError, match="revision"):
        run(handler(routes, "/api/campaign/correct")(
            ops.CorrectCampaignRequest(campaign=corrected, fixture_id=fixture["id"],
                game_id=restored["game_id"], expected_result_revision=1)))
    assert completed["fixtures"][0]["result"]["home_score"] == 21


def test_custom_create_and_view_have_no_invented_results():
    campaign = create()
    view = ops.view_campaign(ops.CampaignRequest(campaign=campaign))
    assert len(view["fixtures"]) == 2
    assert all(row["wins"] == 0 for row in view["standings"])
    assert not any(view["leaders"].values())


def test_unknown_template_never_generates_substitute_calendar():
    with pytest.raises(OperationError, match="template"):
        ops.load_template("not-a-year", SimpleNamespace())


def test_final_result_comes_only_from_linked_engine():
    @dataclass
    class Box:
        total_yards: int = 210
        rushing_yards: int = 80
        passing_yards: int = 140
        sack_yards: int = 10
        turnovers: int = 1

    campaign = create()
    fixture = campaign["fixtures"][0]
    from paydirt.campaigns import start_fixture
    campaign = start_fixture(campaign, fixture["id"], "game-1")
    state = SimpleNamespace(game_over=True, is_playoff=False, home_score=24, away_score=17,
                            home_stats=Box(), away_stats=Box())
    engine = SimpleNamespace(state=state, season_rules=SimpleNamespace(season=2026), pending_post_score_action=lambda: None,
                             has_untimed_down=lambda: False)
    context = SimpleNamespace(games={"game-1": {"engine": engine,
        "campaign_id": campaign["id"], "fixture_id": fixture["id"],
        **{side + "_team": SimpleNamespace(id=next(p["team_id"] for p in campaign["participants"] if p["id"] == fixture[side + "_id"]), season="2026") for side in ("home", "away")}}})
    request = ops.CompleteCampaignRequest(campaign=campaign, fixture_id=fixture["id"], game_id="game-1")
    result = ops.complete_campaign(request, context)
    assert result["fixtures"][0]["result"]["home_score"] == 24
    again = ops.complete_campaign(ops.CompleteCampaignRequest(
        campaign=result, fixture_id=fixture["id"], game_id="game-1"), context)
    assert again == result
    state.game_over = False
    with pytest.raises(OperationError, match="final"):
        ops.complete_campaign(request, context)


def test_game_from_another_campaign_cannot_be_recorded():
    campaign = create()
    request = ops.CompleteCampaignRequest(campaign=campaign, fixture_id=campaign["fixtures"][0]["id"], game_id="other")
    with pytest.raises(OperationError, match="linked"):
        ops.complete_campaign(request, SimpleNamespace(games={"other": {"campaign_id": "different"}}))


def test_registers_same_operations_for_both_transports():
    registry = OperationRegistry()
    ops.register_campaign_operations(registry, SimpleNamespace())
    paths = {item.path for item in registry.operations}
    assert {"/api/campaign/templates", "/api/campaign/create", "/api/campaign/view",
            "/api/campaign/start", "/api/campaign/complete", "/api/campaign/import"} <= paths


@pytest.fixture
def isolated_games():
    existing = dict(routes.games)
    yield routes
    routes.games.clear()
    routes.games.update(existing)


def run(awaitable):
    import asyncio
    return asyncio.run(awaitable)


def handler(context, path):
    registry = OperationRegistry()
    ops.register_campaign_operations(registry, context)
    return next(operation.handler for operation in registry.operations if operation.path == path)


@pytest.mark.parametrize("human_is_home", [True, False])
def test_start_uses_actual_coach_shared_rulebook_and_returns_setup_phase(isolated_games, human_is_home):
    c = create()
    data = run(ops.start_campaign(ops.StartCampaignRequest(
        campaign=c, fixture_id=c["fixtures"][0]["id"], human_is_home=human_is_home), routes))
    game = routes.games[data["game_id"]]
    assert game["ai"].ai_behavior is game["engine"].season_rules.ai_behavior
    assert game["human_is_home"] is human_is_home
    assert data["game_phase"] == "coinToss"
    assert data["campaign"]["fixtures"][0]["game_id"] == data["game_id"]
    assert data["campaign"]["fixtures"][0]["status"] == "in_progress"


def test_import_rejects_missing_catalog_edition():
    import json
    c = create(); c["participants"][0]["team_id"] = "DoesNotExist"
    with pytest.raises(OperationError, match="unavailable"):
        run(handler(routes, "/api/campaign/import")(ops.ImportCampaignRequest(text=json.dumps(c))))


def test_missing_pending_game_choice_prevents_final_acceptance():
    from paydirt.campaigns import start_fixture
    c = create(); fixture = c["fixtures"][0]
    c = start_fixture(c, fixture["id"], "g1")
    from paydirt.game_state import TeamStats
    engine = SimpleNamespace(season_rules=SimpleNamespace(season=2026), state=SimpleNamespace(game_over=True, is_playoff=False, home_score=24, away_score=17,
                             home_stats=TeamStats(), away_stats=TeamStats()), pending_post_score_action=lambda: None,
                             has_untimed_down=lambda: False,
                             _last_play_outcome=SimpleNamespace(pending_penalty_decision=True))
    context = SimpleNamespace(games={"g1": {"engine": engine, "campaign_id": c["id"], "fixture_id": fixture["id"],
        **{side + "_team": SimpleNamespace(id=next(p["team_id"] for p in c["participants"] if p["id"] == fixture[side + "_id"]), season="2026") for side in ("home", "away")}}})
    with pytest.raises(OperationError, match="final"):
        ops.complete_campaign(ops.CompleteCampaignRequest(campaign=c, fixture_id=fixture["id"], game_id="g1"), context)


def test_resume_operation_checks_new_session_and_rebinds(isolated_games):
    c = create(); fixture = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=fixture["id"]), routes))
    text = run(routes.checkpoint_game(started["game_id"]))["checkpoint"]
    restored = run(routes.restore_game_checkpoint(routes.RestoreCheckpointRequest(checkpoint=text)))
    request = ops.ResumeCampaignRequest(campaign=started["campaign"], fixture_id=fixture["id"],
                                        old_game_id=started["game_id"], new_game_id=restored["game_id"])
    resumed = run(handler(routes, "/api/campaign/resume")(request))
    assert resumed["fixtures"][0]["game_id"] == restored["game_id"]
    routes.games[restored["game_id"]]["campaign_id"] = "wrong"
    with pytest.raises(OperationError, match="linked"):
        run(handler(routes, "/api/campaign/resume")(request))


def test_postseason_command_seeds_and_waits_for_actual_finals():
    from paydirt.campaigns import record_result
    c = create()
    for i, fixture in enumerate(c["fixtures"]):
        c = record_result(c, fixture["id"], {"game_id": f"game-{i}", "home_score": 10,
            "away_score": 7, "final": True, "source": "simulated"})
    command = handler(routes, "/api/campaign/postseason")
    seeded = run(command(ops.PostseasonCampaignRequest(campaign=c, size=2)))
    assert len(seeded["fixtures"]) == 3
    assert seeded["fixtures"][-1]["phase"] == "FINAL"
    assert run(command(ops.PostseasonCampaignRequest(campaign=seeded, size=2))) == seeded


def test_campaign_bundle_import_remaps_active_checkpoint_and_leaves_no_runtime_session(isolated_games):
    import json
    import random
    c = create(); fixture = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=fixture["id"]), routes))
    text = run(routes.checkpoint_game(started["game_id"]))["checkpoint"]
    bundle = {"format": "paydirt-campaign", "version": 1, "campaign": started["campaign"],
              "games": [{"id": started["game_id"], "name": "Active", "checkpoint": text,
                         "metadata": {"campaignId": c["id"], "fixtureId": fixture["id"], "gameId": started["game_id"], "phase": "coinToss"},
                         "revision": 5, "savedAt": "2026-11-18T12:00:00Z"}]}
    before_games, before_rng = set(routes.games), random.getstate()
    imported = run(handler(routes, "/api/campaign/import")(ops.ImportCampaignRequest(text=json.dumps(bundle))))
    assert set(routes.games) == before_games
    assert random.getstate() == before_rng
    new_c, saved = imported["campaign"], imported["games"][0]
    assert new_c["id"] != c["id"]
    assert saved["id"] == new_c["fixtures"][0]["game_id"]
    assert saved["revision"] == 1
    assert saved["metadata"]["campaignId"] == new_c["id"]
    assert saved["metadata"]["fixtureId"] == new_c["fixtures"][0]["id"]
    assert saved["metadata"]["phase"] == "coinToss"
    restored = run(routes.restore_game_checkpoint(routes.RestoreCheckpointRequest(checkpoint=saved["checkpoint"])))
    session = routes.games[restored["game_id"]]
    assert session["campaign_id"] == new_c["id"]
    assert session["fixture_id"] == new_c["fixtures"][0]["id"]


def test_active_campaign_without_checkpoint_is_rejected(isolated_games):
    import json
    c = create(); fixture = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=fixture["id"]), routes))
    with pytest.raises(OperationError, match="checkpoint"):
        run(handler(routes, "/api/campaign/import")(ops.ImportCampaignRequest(text=json.dumps(started["campaign"]))))


@pytest.mark.parametrize("command", ["create", "view"])
def test_registered_create_and_view_use_catalog_and_domain(command):
    request = (ops.CreateCampaignRequest(name="Registered", participants=PARTICIPANTS, rules_season="2026")
               if command == "create" else ops.CampaignRequest(campaign=create()))
    data = run(handler(routes, "/api/campaign/" + command)(request))
    assert data["rules_season"] == "2026"
    assert len(data["participants"]) == 2


def test_export_plain_campaign_and_import_returns_separate_bundle():
    import json
    c = create()
    data = run(handler(routes, "/api/campaign/export")(ops.CampaignBundleRequest(campaign=c)))
    assert json.loads(data["text"])["format"] == "paydirt-campaign"
    imported = run(handler(routes, "/api/campaign/import")(ops.ImportCampaignRequest(text=data["text"])))
    assert imported["campaign"]["id"] != c["id"]
    assert imported["games"] == []


@pytest.mark.parametrize("text", ["{}", "[]", "not json", '{"schema_version":1,"schema_version":1}',
    '{"format":"paydirt-campaign","version":true,"campaign":{},"games":[]}',
    '{"format":"paydirt-campaign","version":1,"campaign":{},"games":null}'])
def test_malformed_bundle_is_rejected_without_new_sessions(isolated_games, text):
    before = set(routes.games)
    with pytest.raises(OperationError):
        run(handler(routes, "/api/campaign/import")(ops.ImportCampaignRequest(text=text)))
    assert set(routes.games) == before


def test_start_rejects_existing_fixture_and_missing_rules(isolated_games, monkeypatch):
    c = create(); fixture = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=fixture["id"]), routes))
    with pytest.raises(OperationError, match="unplayed"):
        run(ops.start_campaign(ops.StartCampaignRequest(campaign=started["campaign"], fixture_id=fixture["id"]), routes))
    c = create(); c["rules_season"] = "2099"
    with pytest.raises(OperationError, match="rules"):
        run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=c["fixtures"][0]["id"]), routes))


def test_simulation_operation_commits_one_authoritative_final_and_rejects_overwrite(monkeypatch):
    from paydirt import campaign_simulation
    from paydirt.game_state import TeamStats
    calls = []
    def fake_simulate(home, away, rules, **kwargs):
        calls.append((home, away, rules, kwargs))
        return SimpleNamespace(state=SimpleNamespace(home_score=20, away_score=17,
            home_stats=TeamStats(total_yards=250), away_stats=TeamStats(total_yards=210)))
    monkeypatch.setattr(campaign_simulation, "simulate_game", fake_simulate)
    c = create(); fixture = c["fixtures"][0]
    command = handler(routes, "/api/campaign/simulate")
    simulated = run(command(ops.SimulateCampaignRequest(campaign=c, fixture_id=fixture["id"])))
    assert len(calls) == 1
    assert simulated["fixtures"][0]["result"]["home_score"] == 20
    assert simulated["fixtures"][0]["result"]["source"] == "simulated"
    assert simulated["fixtures"][0]["status"] == "completed"
    assert c["fixtures"][0]["status"] == "scheduled"
    with pytest.raises(OperationError, match="unplayed"):
        run(command(ops.SimulateCampaignRequest(campaign=simulated, fixture_id=fixture["id"])))
    from paydirt.campaigns import start_fixture
    started = start_fixture(c, fixture["id"], "live")
    with pytest.raises(OperationError, match="unplayed"):
        run(command(ops.SimulateCampaignRequest(campaign=started, fixture_id=fixture["id"])))
    assert len(calls) == 1


def test_failed_simulation_retains_original_unplayed_fixture(monkeypatch):
    from paydirt import campaign_simulation
    def fail(*args, **kwargs):
        raise RuntimeError("action cap")
    monkeypatch.setattr(campaign_simulation, "simulate_game", fail)
    c = create()
    with pytest.raises(OperationError, match="action cap"):
        run(handler(routes, "/api/campaign/simulate")(ops.SimulateCampaignRequest(campaign=c, fixture_id=c["fixtures"][0]["id"])))
    assert all(f["status"] == "scheduled" for f in c["fixtures"])


def test_archived_start_has_no_runtime_side_effect(isolated_games):
    c = create(); c["archived"] = True
    before = set(routes.games)
    with pytest.raises(OperationError, match="Archived"):
        run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=c["fixtures"][0]["id"]), routes))
    assert set(routes.games) == before


def test_rejected_bundle_checkpoint_is_removed_and_live_game_unchanged(isolated_games):
    import json
    import random
    c = create(); fid = c["fixtures"][0]["id"]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=fid), routes))
    game = routes.games[started["game_id"]]
    # A well-formed real checkpoint with another campaign's link must fail after
    # codec validation without leaking the temporary validation session.
    game["campaign_id"] = "different"
    text = run(routes.checkpoint_game(started["game_id"]))["checkpoint"]
    before_ids, before_rng = set(routes.games), random.getstate()
    bundle = {"format": "paydirt-campaign", "version": 1, "campaign": started["campaign"],
              "games": [{"id": started["game_id"], "name": "Wrong campaign", "checkpoint": text,
                "metadata": {"campaignId": c["id"], "fixtureId": fid, "gameId": started["game_id"]}}]}
    with pytest.raises(OperationError, match="linked"):
        run(handler(routes, "/api/campaign/import")(ops.ImportCampaignRequest(text=json.dumps(bundle))))
    assert set(routes.games) == before_ids
    assert random.getstate() == before_rng
    assert routes.games[started["game_id"]] is game
    assert game["campaign_id"] == "different"


@pytest.mark.parametrize("mismatch", ["edition", "rules", "playoff"])
def test_final_rejects_engine_identity_mismatch_even_with_matching_link_tags(isolated_games, mismatch):
    c = create(); f = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=f["id"]), routes))
    game = routes.games[started["game_id"]]
    game["engine"].state.game_over = True
    if mismatch == "edition":
        game["home_team"] = SimpleNamespace(id="Different", season="2026")
    elif mismatch == "rules":
        game["engine"].season_rules.season = 2030
    else:
        game["engine"].state.is_playoff = True
    with pytest.raises(OperationError, match="differ"):
        ops.complete_campaign(ops.CompleteCampaignRequest(campaign=started["campaign"],
            fixture_id=f["id"], game_id=started["game_id"]), routes)


@pytest.mark.parametrize("source", ["played", "simulated"])
def test_incomplete_turnover_breakdown_remains_unknown_in_campaign_results(isolated_games, monkeypatch, source):
    from paydirt import campaign_simulation
    c = create(); f = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(campaign=c, fixture_id=f["id"]), routes))
    engine = routes.games[started["game_id"]]["engine"]
    engine.state.game_over = True
    engine.state.home_stats.turnovers = 3
    engine.state.home_stats._turnover_breakdown_complete = False
    # Real portable saves preserve the legacy marker; conversion to final boxes must too.
    checkpoint = run(routes.checkpoint_game(started["game_id"]))["checkpoint"]
    restored = run(routes.restore_game_checkpoint(routes.RestoreCheckpointRequest(checkpoint=checkpoint)))
    engine = routes.games[restored["game_id"]]["engine"]
    assert engine.state.home_stats._turnover_breakdown_complete is False
    if source == "played":
        from paydirt.campaigns import resume_fixture
        resumed = resume_fixture(started["campaign"], f["id"], started["game_id"], restored["game_id"])
        result = ops.complete_campaign(ops.CompleteCampaignRequest(campaign=resumed,
            fixture_id=f["id"], game_id=restored["game_id"]), routes)
    else:
        monkeypatch.setattr(campaign_simulation, "simulate_game", lambda *args, **kwargs: engine)
        result = ops.simulate_campaign(ops.SimulateCampaignRequest(campaign=c, fixture_id=f["id"]), routes)
    boxes = result["fixtures"][0]["result"]
    assert boxes["home_stats"]["turnovers"] == 3
    assert boxes["home_stats"].get("interceptions_thrown") is None
    assert boxes["home_stats"].get("fumbles_lost") is None
    assert boxes["away_stats"]["interceptions_thrown"] == 0
    assert boxes["away_stats"]["fumbles_lost"] == 0
    view = ops.view_campaign(ops.CampaignRequest(campaign=result))
    home = next(row for row in view["statistics"] if row["participant_id"] == f["home_id"])
    assert home["offense"]["interceptions_thrown"] is None
    assert home["offense_games"]["interceptions_thrown"] == 0
    assert home["offense"]["turnovers"] == 3


def test_expiring_touchdown_checkpoint_keeps_owed_try_before_campaign_final(isolated_games):
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from main import app

    from paydirt.campaigns import resume_fixture
    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType

    c = create(); fixture = c["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(
        campaign=c, fixture_id=fixture["id"], human_is_home=True), routes))
    game_id = started["game_id"]; game = routes.games[game_id]; engine = game["engine"]
    game["is_kickoff"] = False
    engine.state.is_home_possession = True
    engine.state.quarter, engine.state.time_remaining = 4, 10 / 60
    engine.state.two_minute_warning_called = True
    engine.state.home_score, engine.state.away_score = 21, 14
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 94, 2, 6
    with TestClient(app) as client:
        resolved = PlayResult(result_type=ResultType.YARDS, yards=9)
        with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(play_result=resolved)),
              patch("paydirt.game_engine.random.uniform", return_value=30)):
            played = client.post("/api/game/execute", json={
                "game_id": game_id, "player_play": "1", "cpu_play": "A"})
        assert played.status_code == 200, played.text
        assert played.json()["result"]["touchdown"] is True
        assert played.json()["game_state"]["game_over"] is True
        assert played.json()["game_state"]["pending_pat"] is True
        with pytest.raises(OperationError, match="legal final"):
            ops.complete_campaign(ops.CompleteCampaignRequest(campaign=started["campaign"],
                fixture_id=fixture["id"], game_id=game_id), routes)
        exported = client.post(f"/api/game/checkpoint/{game_id}")
        assert exported.status_code == 200, exported.text
        routes.games.pop(game_id)
        restored = client.post("/api/game/restore", json=exported.json())
        assert restored.status_code == 200, restored.text
        data = restored.json(); restored_id = data["game_id"]
        assert data["game_state"]["game_over"] is True
        assert data["game_state"]["pending_pat"] is True
        campaign = resume_fixture(started["campaign"], fixture["id"], game_id, restored_id)
        final_request = ops.CompleteCampaignRequest(campaign=campaign, fixture_id=fixture["id"], game_id=restored_id)
        with pytest.raises(OperationError, match="legal final"):
            ops.complete_campaign(final_request, routes)
        with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
            tried = client.post("/api/game/extra-point", json={"game_id": restored_id})
        assert tried.status_code == 200, tried.text
        assert tried.json()["game_state"]["pending_pat"] is False
        assert tried.json()["game_state"]["game_over"] is True
        final = ops.complete_campaign(final_request, routes)
        assert final["fixtures"][0]["status"] == "completed"
        assert final["fixtures"][0]["result"]["home_score"] == tried.json()["new_score_home"]
        checkpoint_after = client.post(f"/api/game/checkpoint/{restored_id}").json()["checkpoint"]
        duplicate = client.post("/api/game/extra-point", json={"game_id": restored_id})
        assert duplicate.status_code == 400
        assert client.post(f"/api/game/checkpoint/{restored_id}").json()["checkpoint"] == checkpoint_after
        assert ops.complete_campaign(ops.CompleteCampaignRequest(campaign=final,
            fixture_id=fixture["id"], game_id=restored_id), routes) == final


@pytest.mark.parametrize('human_decides', [False, True])
@pytest.mark.parametrize('accept_penalty', [False, True])
def test_resolved_penalty_cannot_block_campaign_final_or_reappear_on_restore(
        isolated_games, human_decides, accept_penalty):
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from main import app

    from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType
    campaign = create()
    fixture = campaign['fixtures'][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(
        campaign=campaign, fixture_id=fixture['id']), routes))
    game_id = started['game_id']
    engine = routes.games[game_id]['engine']
    engine.state.is_home_possession = not human_decides
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 1, 10
    choice = PenaltyChoice(play_result=PlayResult(result_type=ResultType.YARDS, yards=2),
                           penalty_options=[PenaltyOption('OFF','OFF 5',5,'Synthetic offensive foul')],
                           offended_team='defense')
    with TestClient(app) as client:
        with (patch('paydirt.game_engine.resolve_play_with_penalties',return_value=choice),
              patch('routes.cpu_should_accept_penalty',return_value=(not accept_penalty,0))):
            played = client.post('/api/game/execute',json={'game_id':game_id,
                'player_play':'A' if human_decides else '1','cpu_play':'1' if human_decides else 'A'})
        assert played.status_code == 200, played.text
        assert played.json()['result']['pending_penalty_decision'] is human_decides
        if human_decides:
            decision = client.post('/api/game/penalty-decision',json={
                'game_id':game_id,'accept_penalty':accept_penalty,'penalty_index':0})
            assert decision.status_code == 200, decision.text
        assert not engine._last_play_outcome.pending_penalty_decision
        duplicate = client.post('/api/game/penalty-decision',json={
            'game_id':game_id,'accept_penalty':accept_penalty,'penalty_index':0})
        assert duplicate.status_code == 400
        checkpoint = client.post(f'/api/game/checkpoint/{game_id}')
        restored = client.post('/api/game/restore',json=checkpoint.json())
        assert restored.status_code == 200, restored.text
        assert restored.json()['pending_result'] is None
        engine.state.quarter, engine.state.time_remaining = 4, 1 / 60
        engine.state.is_home_possession = True
        engine.state.home_score, engine.state.away_score = 21, 20
        final = client.post('/api/game/execute',json={'game_id':game_id,'player_play':'K','cpu_play':'A'})
        assert final.status_code == 200, final.text
        assert final.json()['game_state']['game_over'] is True
        completed = ops.complete_campaign(ops.CompleteCampaignRequest(
            campaign=started['campaign'],fixture_id=fixture['id'],game_id=game_id),routes)
        result = next(f for f in completed['fixtures'] if f['id']==fixture['id'])['result']
        assert (result['home_score'],result['away_score']) == (21,20)
        assert ops.complete_campaign(ops.CompleteCampaignRequest(
            campaign=completed,fixture_id=fixture['id'],game_id=game_id),routes) == completed



def test_final_box_exposes_measured_kicking_and_omits_unknown_legacy():
    from campaign_operations import _final_team_stats

    from paydirt.game_state import TeamStats
    from paydirt.kicking_stats import empty_field_goal_stats
    legacy = TeamStats()
    assert 'field_goals_attempted' not in _final_team_stats(legacy)
    measured = TeamStats()
    measured._field_goal_stats = empty_field_goal_stats()
    assert _final_team_stats(measured)['field_goals_attempted'] == 0


def test_final_box_includes_partial_extended_stats_without_inventing_legacy_zeroes():
    from campaign_operations import _final_team_stats

    from paydirt.game_state import TeamStats
    stats = TeamStats()
    assert "punts" not in _final_team_stats(stats)
    stats._extended_team_stats = {"punts": 2, "longest_punt": 54}
    box = _final_team_stats(stats)
    assert box["punts"] == 2
    assert box["longest_punt"] == 54
    assert "extra_points_made" not in box


def test_extended_stats_native_checkpoint_to_final_aggregate_parity(isolated_games, tmp_path):
    from native_library import NativeLibrary
    from native_library_operations import _validate_checkpoints

    campaign = create()
    fixture = campaign["fixtures"][0]
    started = run(ops.start_campaign(ops.StartCampaignRequest(
        campaign=campaign, fixture_id=fixture["id"]), routes))
    identity = started["game_id"]
    engine = routes.games[identity]["engine"]
    expected = {"punts": 3, "punts_blocked": 1, "punt_yards": 80,
                "punt_return_yards_allowed": 10, "punt_touchbacks": 1, "longest_punt": 45}
    engine.state.home_stats._extended_team_stats = expected
    checkpoint = run(routes.checkpoint_game(identity))["checkpoint"]
    saved = {"id": "save-public-2026", "name": "Synthetic saved season", "checkpoint": checkpoint,
             "metadata": {"campaignId": campaign["id"], "fixtureId": fixture["id"], "gameId": identity},
             "revision": 1, "savedAt": "2026-11-19T00:00:00Z"}
    command = {"store": "campaigns", "action": "put", "campaign": started["campaign"],
               "expectedRevision": 0, "gameRecord": saved, "expectedGameRevision": 0}
    run(_validate_checkpoints(command, routes))
    path = tmp_path / "isolated-library.sqlite3"
    NativeLibrary(path).command(command)
    persisted = NativeLibrary(path).command({"store": "games", "action": "get", "id": saved["id"]})
    routes.games.pop(identity)
    restored = run(routes.restore_game_checkpoint(routes.RestoreCheckpointRequest(checkpoint=persisted["checkpoint"])))
    engine = routes.games[restored["game_id"]]["engine"]
    assert engine.state.home_stats._extended_team_stats == expected
    engine.state.game_over = True
    engine.state.quarter = 4
    engine.state.time_remaining = 0
    engine.state.home_score, engine.state.away_score = 14, 7
    resumed_campaign = run(handler(routes, "/api/campaign/resume")(ops.ResumeCampaignRequest(
        campaign=started["campaign"], fixture_id=fixture["id"], old_game_id=identity,
        new_game_id=restored["game_id"])))
    completed = ops.complete_campaign(ops.CompleteCampaignRequest(campaign=resumed_campaign,
        fixture_id=fixture["id"], game_id=restored["game_id"]), routes)
    row = next(r for r in ops.view_campaign(ops.CampaignRequest(campaign=completed))["statistics"]
               if r["participant_id"] == fixture["home_id"])
    assert row["offense"]["longest_punt"] == 45
    assert row["offense"]["gross_punt_average"] == pytest.approx(80 / 3)
    assert row["offense"]["net_punt_average"] == pytest.approx(50 / 3)
    assert row["offense_games"]["net_punt_average"] == 1
    assert row["offense_games"]["extra_point_percentage"] == 0

"""Synthetic campaign domain regressions; no historical chart data is loaded."""
import copy
import importlib
import json
from collections import Counter

import pytest


@pytest.fixture
def api():
    return importlib.import_module("paydirt.campaigns")


@pytest.fixture
def participants():
    return [
        {"season": "2026", "team_id": f"team-{i}", "name": f"Team {i}",
         "conference": "A" if i < 2 else "B", "division": "East" if i % 2 else "West"}
        for i in range(4)
    ]


def campaign(api, participants, **kwargs):
    return api.create_campaign("My campaign", participants, "2026", **kwargs)


def result(game_id="game-1", **kwargs):
    return {"game_id": game_id, "home_score": 24, "away_score": 17, "final": True,
            "source": "played", "home_stats": stats(), "away_stats": stats(200), **kwargs}


def stats(yards=300):
    return {"total_yards": yards, "rushing_yards": 100, "passing_yards": yards - 90,
            "sack_yards": 10, "first_downs": 14, "turnovers": 2,
            "interceptions_thrown": 1, "fumbles_lost": 1, "sacks": 2,
            "penalties": 3, "penalty_yards": 20}


def test_duplicate_resets_progress_and_remaps_definition(api, participants):
    original = campaign(api, participants)
    fixture = original["fixtures"][0]
    original = api.record_result(original, fixture["id"], result())
    duplicate = api.duplicate_campaign(original, "Another attempt")
    assert duplicate["id"] != original["id"]
    assert duplicate["name"] == "Another attempt"
    assert duplicate["locked_definition"] is None
    assert duplicate["postseason"] is None and duplicate["champion_id"] is None
    assert {p["id"] for p in duplicate["participants"]}.isdisjoint(p["id"] for p in original["participants"])
    assert {f["id"] for f in duplicate["fixtures"]}.isdisjoint(f["id"] for f in original["fixtures"])
    assert all(f["status"] == "scheduled" and f["game_id"] is None and not f["result_history"] for f in duplicate["fixtures"])
    assert all(row["played"] == 0 for row in api.campaign_view(duplicate)["standings"])
    assert original["fixtures"][0]["result"]["home_score"] == 24


def test_generated_schedule_can_be_edited_only_before_play(api, participants):
    original = campaign(api, participants)
    fixture = original["fixtures"][0]
    fixtures = [{"week": 7, "home_id": fixture["away_id"], "away_id": fixture["home_id"]}]
    edited = api.edit_schedule(original, fixtures)
    assert edited["revision"] == original["revision"] + 1
    assert edited["fixtures"][0]["home_id"] == fixture["away_id"]
    assert edited["fixtures"][0]["week"] == 7
    assert original["fixtures"][0]["week"] == 1
    with pytest.raises(ValueError, match="locked"):
        api.edit_schedule(api.start_fixture(original, fixture["id"], "live"), fixtures)
    with pytest.raises(ValueError, match="once in a week"):
        api.edit_schedule(original, fixtures * 2)
    with pytest.raises(ValueError, match="Unknown"):
        api.edit_schedule(original, [{"week": 1, "home_id": "unknown", "away_id": fixture["home_id"]}])


def test_followed_team_survives_new_identities_and_is_not_a_definition_edit(api, participants):
    original = campaign(api, participants)
    original["followed_participant_id"] = original["participants"][0]["id"]
    imported = api.import_campaign(api.export_campaign(original))
    assert imported["followed_participant_id"] == imported["participants"][0]["id"]
    duplicate = api.duplicate_campaign(original, "Follow again")
    assert duplicate["followed_participant_id"] == duplicate["participants"][0]["id"]
    started = api.start_fixture(original, original["fixtures"][0]["id"], "live")
    started["followed_participant_id"] = started["participants"][1]["id"]
    assert api.validate_campaign(started)["followed_participant_id"] == started["participants"][1]["id"]
    started["followed_participant_id"] = "unknown"
    with pytest.raises(ValueError, match="followed"):
        api.validate_campaign(started)


def test_same_chart_year_campaigns_have_disjoint_identity(api, participants):
    a, b = campaign(api, participants), campaign(api, participants)
    assert a["id"] != b["id"]
    assert a["rules_season"] == "2026"
    assert a["name"] == "My campaign"
    assert a["schema_version"] == 1
    assert {p["id"] for p in a["participants"]}.isdisjoint(p["id"] for p in b["participants"])


def test_double_round_robin_covers_each_directed_pair_once(api, participants):
    c = campaign(api, participants)
    assert len(c["fixtures"]) == 12
    pairs = Counter((f["home_id"], f["away_id"]) for f in c["fixtures"])
    assert set(pairs.values()) == {1}
    for week in range(1, 7):
        games = [f for f in c["fixtures"] if f["week"] == week]
        ids = [f[s] for f in games for s in ("home_id", "away_id")]
        assert len(ids) == len(set(ids)) == 4


def test_odd_team_round_robin_preserves_byes(api, participants):
    c = campaign(api, participants[:3], schedule="single_round_robin")
    assert len(c["fixtures"]) == 3
    assert {f["week"] for f in c["fixtures"]} == {1, 2, 3}
    counts = Counter(f[s] for f in c["fixtures"] for s in ("home_id", "away_id"))
    assert set(counts.values()) == {2}


def test_same_franchise_in_different_years_is_distinct(api, participants):
    participants[1]["team_id"] = participants[0]["team_id"]
    participants[1]["season"] = "2025"
    c = campaign(api, participants)
    assert c["participants"][0]["team_id"] == c["participants"][1]["team_id"]
    assert c["participants"][0]["id"] != c["participants"][1]["id"]


@pytest.mark.parametrize("mutation", ["duplicate", "one-team", "path", "bad-name", "bad-rules"])
def test_invalid_creation_is_rejected(api, participants, mutation):
    kwargs = {}
    if mutation == "duplicate": participants[1] = participants[0]
    if mutation == "one-team": participants = participants[:1]
    if mutation == "path": participants[0]["team_id"] = "../secret"
    if mutation == "bad-name": kwargs["name"] = "  "
    if mutation == "bad-rules": kwargs["rules_season"] = "../2026"
    with pytest.raises(ValueError):
        api.create_campaign(kwargs.get("name", "test"), participants, kwargs.get("rules_season", "2026"))


def test_historical_adapter_keeps_regular_calendar_and_drops_actual_results(api, participants):
    spec = {"season": 2026, "regular_weeks": 1, "games_per_team": 1,
            "postseason_format": "custom", "divisions": {"A": {"East": [p["team_id"] for p in participants]}},
            "games": [{"game_id": "source-a", "phase": "REG", "week": 1,
                       "home": "team-0", "away": "team-1", "home_score": 99, "away_score": 0},
                      {"game_id": "source-b", "phase": "REG", "week": 1,
                       "home": "team-2", "away": "team-3", "home_score": 0, "away_score": 99},
                      {"game_id": "playoff", "phase": "SB", "week": 2,
                       "home": "team-0", "away": "team-1", "home_score": 99, "away_score": 0}]}
    c = campaign(api, participants, historical=spec)
    assert len(c["fixtures"]) == 2
    assert all(f["status"] == "scheduled" and f["result"] is None for f in c["fixtures"])
    assert all(r["wins"] == 0 for r in api.campaign_view(c)["standings"])
    assert c["participants"][0]["division"] == "East"
    duplicate = api.duplicate_campaign(c, "Historical restart")
    assert duplicate["kind"] == "historical" and duplicate["postseason_format"] == "custom"
    first = duplicate["fixtures"][0]
    edited = api.edit_schedule(duplicate, [{"week": 2, "home_id": first["home_id"], "away_id": first["away_id"]}])
    assert edited["kind"] == "custom" and "template_season" not in edited
    assert "postseason_format" not in edited
    assert c["kind"] == "historical"
    duplicate["archived"] = True
    with pytest.raises(ValueError, match="Archived"):
        api.edit_schedule(duplicate, [])
    with pytest.raises(ValueError, match="nonempty"):
        api.edit_schedule(c, [])
    broken = copy.deepcopy(spec); broken["games"].pop(1)
    with pytest.raises(ValueError, match="incomplete|inventory"):
        campaign(api, participants, historical=broken)


def test_manual_fixture_validation(api, participants):
    c = campaign(api, participants, schedule="manual", fixtures=[{"week": 1, "home": "2026/team-0", "away": "2026/team-1"}])
    assert len(c["fixtures"]) == 1
    for fixtures in [
        [{"week": 1, "home": "2026/team-0", "away": "2026/team-0"}],
        [{"week": 1, "home": "2026/team-0", "away": "2026/absent"}],
        [{"week": 0, "home": "2026/team-0", "away": "2026/team-1"}],
        [{"week": 1, "home": "2026/team-0", "away": "2026/team-1"},
         {"week": 1, "home": "2026/team-0", "away": "2026/team-2"}],
    ]:
        with pytest.raises(ValueError):
            campaign(api, participants, schedule="manual", fixtures=fixtures)


def test_start_fixture_is_functional_and_idempotent(api, participants):
    c = campaign(api, participants); before = copy.deepcopy(c); f = c["fixtures"][0]
    started = api.start_fixture(c, f["id"], "game-1")
    assert c == before
    assert started["fixtures"][0]["status"] == "in_progress"
    assert api.start_fixture(started, f["id"], "game-1") == started
    with pytest.raises(ValueError, match="progress|game"):
        api.start_fixture(started, f["id"], "different-game")


def test_only_final_results_count_and_retries_are_exactly_once(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    started = api.start_fixture(c, f["id"], "game-1")
    assert sum(r["played"] for r in api.campaign_view(started)["standings"]) == 0
    with pytest.raises(ValueError, match="final"):
        api.record_result(started, f["id"], result(final=False))
    completed = api.record_result(started, f["id"], result())
    assert api.record_result(completed, f["id"], result()) == completed
    rows = {r["participant_id"]: r for r in api.campaign_view(completed)["standings"]}
    assert rows[f["home_id"]]["wins"] == 1
    assert rows[f["away_id"]]["losses"] == 1
    assert sum(r["points_for"] for r in rows.values()) == 41
    with pytest.raises(ValueError, match="replace|completed"):
        api.record_result(completed, f["id"], result(home_score=30))


def test_replacement_recomputes_and_keeps_previous_revision(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    c = api.record_result(c, f["id"], result())
    revised = api.record_result(c, f["id"], result(home_score=10), replace=True)
    assert revised["fixtures"][0]["result"]["revision"] == 2
    assert len(revised["fixtures"][0]["result_history"]) == 1
    rows = {r["participant_id"]: r for r in api.campaign_view(revised)["standings"]}
    assert rows[f["home_id"]]["wins"] == 0
    assert rows[f["away_id"]]["wins"] == 1
    assert sum(r["points_for"] for r in rows.values()) == 27


def test_game_cannot_be_counted_in_two_fixtures(api, participants):
    c = campaign(api, participants)
    c = api.record_result(c, c["fixtures"][0]["id"], result())
    with pytest.raises(ValueError, match="already|another"):
        api.record_result(c, c["fixtures"][1]["id"], result())


@pytest.mark.parametrize("fields", [{"home_score": True}, {"away_score": -1}, {"source": "invented"},
                                     {"game_id": ""}, {"home_stats": {"total_yards": "300"}},
                                     {"home_stats": {"turnovers": -1}}])
def test_invalid_result_is_rejected_atomically(api, participants, fields):
    c = campaign(api, participants); before = copy.deepcopy(c)
    with pytest.raises(ValueError): api.record_result(c, c["fixtures"][0]["id"], result(**fields))
    assert c == before


def test_team_stats_and_defense_derive_from_opponent_boxes(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    c = api.record_result(c, f["id"], result())
    view = api.campaign_view(c); rows = {r["participant_id"]: r for r in view["statistics"]}
    home = rows[f["home_id"]]
    assert home["stat_games"] == 1
    assert home["offense"]["total_yards"] == 300
    assert home["offense"]["net_passing_yards"] == 200
    assert home["defense"]["total_yards"] == 200
    assert home["offense_per_game"]["rushing_yards"] == 100
    assert "total_offense" in view["leaders"]
    assert not any("player" in key for key in view["leaders"])
    assert "not official" in view["ranking_policy"].lower()


def test_unknown_stats_remain_unknown_and_denominator_is_explicit(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    c = api.record_result(c, f["id"], result(source="manual", home_stats=None, away_stats=None))
    v = api.campaign_view(c)
    assert sum(r["played"] for r in v["standings"]) == 2
    row = next(r for r in v["statistics"] if r["participant_id"] == f["home_id"])
    assert row["stat_games"] == 0
    assert row["offense"]["total_yards"] is None
    assert row["offense_per_game"]["total_yards"] is None
    assert v["leaders"]["total_offense"] == []
    assert v["leaders"]["scoring_offense"][0]["games"] == 1


def test_ties_and_scope_records(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    c = api.record_result(c, f["id"], result(home_score=17))
    rows = {r["participant_id"]: r for r in api.campaign_view(c)["standings"]}
    assert rows[f["home_id"]]["ties"] == 1
    assert rows[f["home_id"]]["win_pct"] == .5
    assert rows[f["home_id"]]["home_record"] == "0-0-1"
    assert rows[f["away_id"]]["away_record"] == "0-0-1"


def test_locked_definition_changes_fail_validation(api, participants):
    c = campaign(api, participants); c = api.start_fixture(c, c["fixtures"][0]["id"], "game-1")
    for change in ["rules", "membership", "fixture"]:
        mutated = copy.deepcopy(c)
        if change == "rules": mutated["rules_season"] = "2025"
        elif change == "membership": mutated["participants"][0]["team_id"] = "changed"
        else: mutated["fixtures"][0]["home_id"] = mutated["fixtures"][1]["home_id"]
        with pytest.raises(ValueError, match="locked|definition|matchup|self"):
            api.validate_campaign(mutated)


def test_export_import_roundtrip_is_a_separate_consistent_campaign(api, participants):
    c = campaign(api, participants); c = api.record_result(c, c["fixtures"][0]["id"], result())
    text = api.export_campaign(c); imported = api.import_campaign(text)
    assert imported["id"] != c["id"]
    assert imported["name"] == c["name"]
    assert {p["id"] for p in imported["participants"]}.isdisjoint(p["id"] for p in c["participants"])
    assert imported["fixtures"][0]["home_id"] in {p["id"] for p in imported["participants"]}
    assert imported["fixtures"][0]["result"]["game_id"] != "game-1"
    assert sum(r["played"] for r in api.campaign_view(imported)["standings"]) == 2
    assert api.validate_campaign(imported) == imported


@pytest.mark.parametrize("text", ['{}','[]','not json','{"schema_version":99}', '{"schema_version":1,"schema_version":2}'])
def test_invalid_import_never_becomes_campaign(api, text):
    with pytest.raises(ValueError): api.import_campaign(text)


def test_postseason_starts_only_after_regular_finals_and_excludes_regular_aggregates(api, participants):
    c = campaign(api, participants, schedule="single_round_robin")
    with pytest.raises(ValueError, match="complete"):
        api.seed_postseason(c, size=4)
    for i, f in enumerate(c["fixtures"]):
        c = api.record_result(c, f["id"], result(game_id=f"game-{i}"))
    seeded = api.seed_postseason(c, size=4)
    playoffs = [f for f in seeded["fixtures"] if f["phase"] != "REG"]
    assert len(playoffs) == 2
    fresh = api.duplicate_campaign(seeded, "New competition")
    assert fresh["postseason"] is None
    assert len(fresh["fixtures"]) == len(c["fixtures"])
    assert all(f["phase"] == "REG" and f["result"] is None for f in fresh["fixtures"])
    before = api.campaign_view(c)["standings"]
    f = playoffs[0]
    with pytest.raises(ValueError, match="tie"):
        api.record_result(seeded, f["id"], result("playoff-1", home_score=17))
    seeded = api.record_result(seeded, f["id"], result("playoff-1"))
    assert api.campaign_view(seeded)["standings"] == before
    with pytest.raises(ValueError, match="postseason|frozen"):
        api.record_result(seeded, c["fixtures"][0]["id"], result("game-0", home_score=50), replace=True)
    seeded = api.record_result(seeded, playoffs[1]["id"], result("playoff-2"))
    advanced = api.advance_postseason(seeded)
    finals = [f for f in advanced["fixtures"] if f["phase"] == "FINAL"]
    assert len(finals) == 1
    assert api.advance_postseason(advanced) == advanced
    complete = api.record_result(advanced, finals[0]["id"], result("final"))
    complete = api.advance_postseason(complete)
    assert complete["champion_id"] == finals[0]["home_id"]


def test_resume_fixture_rebinds_only_expected_live_game(api, participants):
    c = campaign(api, participants); fid = c["fixtures"][0]["id"]
    c = api.start_fixture(c, fid, "old-game")
    resumed = api.resume_fixture(c, fid, "old-game", "restored-game")
    assert resumed["fixtures"][0]["game_id"] == "restored-game"
    assert c["fixtures"][0]["game_id"] == "old-game"
    assert api.resume_fixture(resumed, fid, "old-game", "restored-game") == resumed
    with pytest.raises(ValueError, match="stale|expected"):
        api.resume_fixture(resumed, fid, "old-game", "another-game")
    completed = api.record_result(resumed, fid, result("restored-game"))
    with pytest.raises(ValueError, match="progress"):
        api.resume_fixture(completed, fid, "restored-game", "game-3")


def test_partial_stat_denominators_and_tied_leader_ranks(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    c = api.record_result(c, f["id"], result(home_score=17, home_stats={"rushing_yards": -3}, away_stats={"rushing_yards": -3}))
    view = api.campaign_view(c)
    assert view["leaders"]["total_offense"] == []
    assert [r["rank"] for r in view["leaders"]["rushing_offense"]] == [1, 1]
    assert all(r["value"] == -3 for r in view["leaders"]["rushing_offense"])


@pytest.mark.parametrize("change", ["schema-bool", "duplicate-pid", "duplicate-fid", "unknown-home", "bad-phase", "busy-week", "bad-status", "scheduled-result", "progress-result", "missing-lock", "wrong-history", "bad-champion", "missing-postseason"])
def test_corrupt_document_rejection(api, participants, change):
    c = campaign(api, participants)
    f = c["fixtures"][0]
    if change == "schema-bool": c["schema_version"] = True
    elif change == "duplicate-pid": c["participants"][1]["id"] = c["participants"][0]["id"]
    elif change == "duplicate-fid": c["fixtures"][1]["id"] = f["id"]
    elif change == "unknown-home": f["home_id"] = "missing"
    elif change == "bad-phase": f["phase"] = "random"
    elif change == "busy-week": c["fixtures"][2]["week"] = 1
    elif change == "bad-status": f["status"] = "bad"
    elif change == "scheduled-result": f["result"] = result()
    elif change == "progress-result":
        c = api.start_fixture(c, f["id"], "game-1"); c["fixtures"][0]["result"] = result()
    elif change == "missing-lock":
        c = api.start_fixture(c, f["id"], "game-1"); c["locked_definition"] = None
    elif change == "wrong-history": f["result_history"] = [result()]
    elif change == "bad-champion": c["champion_id"] = "missing"
    elif change == "missing-postseason": c["fixtures"][0]["phase"] = "FINAL"
    with pytest.raises(ValueError): api.validate_campaign(c)


def test_wrong_live_game_and_archived_actions_rejected(api, participants):
    c = campaign(api, participants); f = c["fixtures"][0]
    with pytest.raises(ValueError, match="Unknown"):
        api.start_fixture(c, "missing", "game")
    archived = copy.deepcopy(c); archived["archived"] = True
    with pytest.raises(ValueError, match="Archived"):
        api.start_fixture(archived, f["id"], "game")
    with pytest.raises(ValueError, match="Archived"):
        api.record_result(archived, f["id"], result())
    c = api.start_fixture(c, f["id"], "game")
    with pytest.raises(ValueError, match="match"):
        api.record_result(c, f["id"], result("different"))
    with pytest.raises(ValueError, match="already"):
        api.start_fixture(c, c["fixtures"][1]["id"], "game")


def test_result_revision_must_match_same_game(api, participants):
    c = campaign(api, participants); fid = c["fixtures"][0]["id"]
    c = api.record_result(c, fid, result())
    with pytest.raises(ValueError, match="identity"):
        api.record_result(c, fid, result("different", home_score=50), replace=True)
    bad = copy.deepcopy(c); bad["fixtures"][0]["result"]["revision"] = 2
    with pytest.raises(ValueError, match="history"):
        api.validate_campaign(bad)


def test_import_size_and_duplicate_keys_are_rejected(api):
    with pytest.raises(ValueError, match="size"):
        api.import_campaign(" " * (api.MAX_IMPORT_BYTES + 1))
    with pytest.raises(ValueError, match="Duplicate"):
        api.import_campaign('{"schema_version":1,"schema_version":1}')


def test_stats_inconsistent_net_and_boolean_are_rejected(api, participants):
    c = campaign(api, participants)
    for box in [{"net_passing_yards": 99, "passing_yards": 100, "sack_yards": 5}, {"turnovers": True}, []]:
        with pytest.raises(ValueError):
            api.record_result(c, c["fixtures"][0]["id"], result(home_stats=box))


def test_postseason_validation_and_two_team_champion_import(api, participants):
    c = campaign(api, participants[:2], schedule="single_round_robin")
    with pytest.raises(ValueError, match="seeded"):
        api.advance_postseason(c)
    c = api.record_result(c, c["fixtures"][0]["id"], result())
    for size in [1, 3, 8, True]:
        with pytest.raises(ValueError, match="size"):
            api.seed_postseason(c, size=size)
    c = api.seed_postseason(c, size=2)
    with pytest.raises(ValueError, match="already"):
        api.seed_postseason(c, size=2)
    c = api.record_result(c, c["fixtures"][-1]["id"], result("final"))
    c = api.advance_postseason(c)
    assert api.advance_postseason(c) == c
    imported = api.import_campaign(api.export_campaign(c))
    assert imported["champion_id"] == imported["fixtures"][-1]["home_id"]
    assert imported["postseason"]["seed_ids"] == [p["participant_id"] for p in api.campaign_view(imported)["standings"]]


@pytest.mark.parametrize("format_name,division_count,expected", [("ten_team", 3, 9), ("fourteen_team", 4, 13), ("eight_team", 3, 7)])
def test_historical_postseason_formats_use_campaign_qualifiers(api, format_name, division_count, expected):
    members, divisions, games = [], {}, []
    for conf in ["A", "B"]:
        divisions[conf] = {}
        for div in range(division_count):
            names = [f"{conf}-{div}-{j}" for j in range(2)]
            divisions[conf][f"D{div}"] = names
            for name in names:
                members.append({"season": "2026", "team_id": name, "name": name})
            games.append({"game_id": f"{conf}-{div}", "phase": "REG", "week": 1,
                          "home": names[0], "away": names[1]})
    source = {"season": 2026, "regular_weeks": 1, "games_per_team": 1,
              "postseason_format": format_name, "divisions": divisions, "games": games}
    c = api.create_campaign("Historical synthetic", members, "2026", historical=source)
    for i, f in enumerate(c["fixtures"]):
        c = api.record_result(c, f["id"], result(f"reg-{i}"))
    c = api.seed_postseason(c)
    assert c["postseason"]["format"] == format_name
    assert set(c["postseason"]["conference_seeds"]) == {"A", "B"}
    for _ in range(5):
        for f in list(c["fixtures"]):
            if f["phase"] != "REG" and f["status"] == "scheduled":
                c = api.record_result(c, f["id"], result("post-" + f["id"]))
        c = api.advance_postseason(c)
        if c["champion_id"]:
            break
    playoffs = [f for f in c["fixtures"] if f["phase"] != "REG"]
    assert len(playoffs) == expected
    assert c["champion_id"] is not None
    assert len([f for f in playoffs if f["phase"] == "SB"]) == 1
    assert all(f["status"] == "completed" for f in playoffs)
    if format_name != "fourteen_team":
        members = {p["id"]: p for p in c["participants"]}
        assert all(members[f["home_id"]]["division"] != members[f["away_id"]]["division"]
                   for f in playoffs if f["phase"] == "DIV")
    assert api.import_campaign(api.export_campaign(c))["champion_id"] is not None


@pytest.mark.parametrize("field,value", [("kind", []), ("champion_id", []), ("fixtures", [{}]), ("participants", [{}, {}])])
def test_malformed_import_document_reports_valueerror(api, participants, field, value):
    c = campaign(api, participants)
    c[field] = value
    with pytest.raises(ValueError): api.validate_campaign(c)
    with pytest.raises(ValueError): api.import_campaign(json.dumps(c))


def test_unhashable_result_source_is_rejected_as_invalid_document(api, participants):
    c = campaign(api, participants)
    with pytest.raises(ValueError):
        api.record_result(c, c["fixtures"][0]["id"], result(source=[]))


def test_postseason_rejects_forged_winner_missing_games_and_false_champion(api, participants):
    c = campaign(api, participants, schedule="single_round_robin")
    for i, f in enumerate(c["fixtures"]):
        c = api.record_result(c, f["id"], result(f"reg-{i}"))
    c = api.seed_postseason(c)
    for i, f in enumerate(c["fixtures"]):
        if f["phase"] != "REG": c = api.record_result(c, f["id"], result(f"post-{i}"))
    c = api.advance_postseason(c)
    mutations = []
    missing = copy.deepcopy(c); missing["fixtures"].pop(); mutations.append(missing)
    forged = copy.deepcopy(c)
    semifinals = [f for f in forged["fixtures"] if f["phase"] == "PLAYOFF-1"]
    forged["fixtures"][-1]["home_id"] = semifinals[0]["away_id"]
    mutations.append(forged)
    false_champion = copy.deepcopy(c); false_champion["champion_id"] = c["participants"][0]["id"]; mutations.append(false_champion)
    bad_week = copy.deepcopy(c); bad_week["fixtures"][-1]["week"] += 1; mutations.append(bad_week)
    for mutation in mutations:
        with pytest.raises(ValueError): api.validate_campaign(mutation)


def test_postseason_cannot_begin_or_advance_when_archived(api, participants):
    c = campaign(api, participants[:2], schedule="single_round_robin")
    c = api.record_result(c, c["fixtures"][0]["id"], result())
    archived = copy.deepcopy(c); archived["archived"] = True
    with pytest.raises(ValueError, match="Archived"): api.seed_postseason(archived, size=2)
    c = api.seed_postseason(c, size=2); c["archived"] = True
    with pytest.raises(ValueError, match="Archived"): api.advance_postseason(c)


@pytest.mark.parametrize("format_name,division_count", [("ten_team", 3), ("fourteen_team", 4)])
def test_historical_divisional_pairings_follow_upsets_and_reseed(api, format_name, division_count):
    members = [{"season": "2026", "team_id": f"{conf}-{div}-{i}", "name": f"{conf}-{div}-{i}",
                "conference": conf, "division": f"D{div}"}
               for conf in ("A", "B") for div in range(division_count) for i in range(2)]
    fixtures = [{"week": 1, "home": "2026/" + members[i]["team_id"],
                 "away": "2026/" + members[i + 1]["team_id"]} for i in range(0, len(members), 2)]
    c = api.create_campaign("Synthetic format", members, "2026", schedule="manual", fixtures=fixtures)
    c["kind"] = "historical"; c["postseason_format"] = format_name
    for i, f in enumerate(c["fixtures"]):
        c = api.record_result(c, f["id"], result(f"reg-{i}"))
    c = api.seed_postseason(c)
    seeds = c["postseason"]["conference_seeds"]
    for f in list(c["fixtures"]):
        if f["phase"] == "WC":
            c = api.record_result(c, f["id"], result("post-" + f["id"], home_score=10))
    c = api.advance_postseason(c)
    pairs = {(f["home_id"], f["away_id"]) for f in c["fixtures"] if f["phase"] == "DIV"}
    for order in seeds.values():
        if format_name == "fourteen_team":
            assert (order[0], order[6]) in pairs
            assert (order[4], order[5]) in pairs
        else:
            assert (order[0], order[4]) in pairs
            assert (order[1], order[2]) in pairs


def test_generic_eight_team_reseeds_winners_and_retains_losing_elimination(api):
    members = [{"season": "2026", "team_id": f"t{i}", "name": f"Team {i}"} for i in range(8)]
    fixtures = [{"week": 1, "home": f"2026/t{i}", "away": f"2026/t{i+1}"} for i in range(0, 8, 2)]
    c = api.create_campaign("Eight", members, "2026", schedule="manual", fixtures=fixtures)
    for i, f in enumerate(c["fixtures"]): c = api.record_result(c, f["id"], result(f"r-{i}"))
    c = api.seed_postseason(c, size=8)
    winners = []
    for f in list(c["fixtures"]):
        if f["phase"] == "PLAYOFF-1":
            c = api.record_result(c, f["id"], result("p-" + f["id"], home_score=10))
            winners.append(f["away_id"])
    c = api.advance_postseason(c)
    semifinals = [f for f in c["fixtures"] if f["phase"] == "PLAYOFF-2"]
    assert {f[side] for f in semifinals for side in ("home_id", "away_id")} == set(winners)



def test_field_goal_aggregation_weighted_rates_and_legacy_unknown(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c['fixtures'][0]['home_id']
    for index, fixture in enumerate(c['fixtures']):
        box = {'field_goals_attempted': 1 if index == 0 else 3,
               'field_goals_made': 1, 'field_goals_40_49_attempted': 1 if index == 0 else 3,
               'field_goals_40_49_made': 1}
        c = api.record_result(c, fixture['id'], result(f'fg-{index}',
            home_stats=box if fixture['home_id']==target else stats(),
            away_stats=box if fixture['away_id']==target else stats()))
    rows = {r['participant_id']:r for r in api.campaign_view(c)['statistics']}
    row = rows[target]
    assert row['offense']['field_goals_attempted'] == 4
    assert row['offense']['field_goals_made'] == 2
    assert row['offense']['field_goal_percentage'] == 50
    assert row['offense_per_game']['field_goal_percentage'] == 50
    assert row['offense_per_game']['field_goals_attempted'] == 2
    assert row['offense_games']['field_goal_percentage'] == 2
    other = next(r for pid,r in rows.items() if pid != target)
    assert other['offense']['field_goals_attempted'] is None
    assert other['offense']['field_goal_percentage'] is None
    assert other['defense']['field_goal_percentage'] == 50


def test_defensive_takeaways_and_sacks_follow_opponents_not_own_offense(api, participants):
    c = campaign(api, participants)
    fixture = c['fixtures'][0]
    c = api.record_result(c, fixture['id'], result(
        home_stats={**stats(), 'turnovers': 3, 'interceptions_thrown': 1, 'fumbles_lost': 2, 'sacks': 3},
        away_stats={**stats(), 'turnovers': 9, 'interceptions_thrown': 4, 'fumbles_lost': 5, 'sacks': 6}))
    rows = {row['participant_id']: row for row in api.campaign_view(c)['statistics']}
    for team, expected in ((fixture['home_id'], (4, 5, 6)), (fixture['away_id'], (1, 2, 3))):
        row = rows[team]
        for key, value in zip(('interceptions_thrown', 'fumbles_lost', 'sacks'), expected):
            assert row['defense'][key] == value
            assert row['defense_per_game'][key] == value
            assert row['defense_games'][key] == 1



def test_passing_efficiency_uses_same_complete_subset_and_weighted_inputs(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c['fixtures'][0]['home_id']
    boxes = [{"passing_attempts":10, "passing_completions":8, "passing_yards":120, "passing_touchdowns":2,
                  "interceptions_thrown":0, "rushing_attempts":4, "rushing_yards":20},
             {"passing_attempts":30, "passing_completions":12, "passing_yards":180, "passing_touchdowns":0,
                  "interceptions_thrown":2, "rushing_attempts":6, "rushing_yards":10}]
    for index, fixture in enumerate(c['fixtures']):
        c = api.record_result(c, fixture['id'], result(f'passing-{index}',
            home_stats=boxes[index] if fixture['home_id']==target else stats(),
            away_stats=boxes[index] if fixture['away_id']==target else stats()))
    row = next(r for r in api.campaign_view(c)['statistics'] if r['participant_id']==target)
    assert row['offense']['passing_attempts'] == 40
    assert row['offense']['completion_percentage'] == 50
    assert row['offense']['passing_yards_per_attempt'] == 7.5
    assert row['offense']['rushing_yards_per_attempt'] == 3
    assert row['offense']['passer_rating'] == pytest.approx(70.8333333333)
    assert row['offense_per_game']['passer_rating'] == row['offense']['passer_rating']
    assert row['offense_games']['passer_rating'] == 2



def test_efficiency_partial_boxes_use_complete_paired_game_subset(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c['fixtures'][0]['home_id']
    for i,f in enumerate(c['fixtures']):
        box = {"passing_attempts":10,"passing_completions":8,"passing_yards":120,"interceptions_thrown":0}
        if i == 0: box['passing_touchdowns']=2
        c = api.record_result(c,f['id'],result(f'partial-rate-{i}',
            home_stats=box if f['home_id']==target else stats(),
            away_stats=box if f['away_id']==target else stats()))
    row=next(r for r in api.campaign_view(c)['statistics'] if r['participant_id']==target)
    assert row['offense']['passer_rating']==pytest.approx(156.25)
    assert row['offense_games']['passer_rating']==1
    assert row['offense_games']['completion_percentage']==2
    assert row['offense']['completion_percentage']==80



def test_imported_offense_cannot_have_more_completions_and_interceptions_than_attempts(api, participants):
    c=campaign(api,participants[:2])
    with pytest.raises(ValueError,match='attempt'):
        api.record_result(c,c['fixtures'][0]['id'],result(home_stats={
            'passing_attempts':10,'passing_completions':10,'interceptions_thrown':1}))


def test_extended_stats_max_weighted_rates_and_score_coverage(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c["fixtures"][0]["home_id"]
    boxes = [{"longest_rush": 35, "rushing_touchdowns": 1, "third_down_attempts": 2, "third_down_conversions": 1,
                  "punts": 3, "punts_blocked": 1, "punt_yards": 80, "punt_return_yards_allowed": 10, "punt_touchbacks": 1,
                  "extra_points_attempted": 1, "extra_points_made": 1, "passing_completions": 2, "passing_yards": 30},
             {"longest_rush": 20, "rushing_touchdowns": 2, "third_down_attempts": 8, "third_down_conversions": 2,
                  "punts": 1, "punts_blocked": 0, "punt_yards": 50, "punt_return_yards_allowed": 0, "punt_touchbacks": 0,
                  "extra_points_attempted": 3, "extra_points_made": 2, "passing_completions": 8, "passing_yards": 70}]
    for index, fixture in enumerate(c["fixtures"]):
        c = api.record_result(c, fixture["id"], result(f"extended-{index}",
            home_stats=boxes[index] if fixture["home_id"] == target else stats(),
            away_stats=boxes[index] if fixture["away_id"] == target else stats()))
    row = next(r for r in api.campaign_view(c)["statistics"] if r["participant_id"] == target)
    assert row["offense"]["longest_rush"] == row["offense_per_game"]["longest_rush"] == 35
    assert row["offense"]["rushing_touchdowns"] == 3
    assert row["offense"]["third_down_conversion_percentage"] == 30
    assert row["offense"]["extra_point_percentage"] == 75
    assert row["offense"]["receiving_yards_per_reception"] == 10
    assert row["offense"]["gross_punt_average"] == 32.5
    assert row["offense"]["net_punt_average"] == 25
    assert row["offense_games"]["net_punt_average"] == 2
    assert row["offense_games"]["points_scored"] == 2
    assert row["offense_per_game"]["points_scored"] == row["offense"]["points_scored"] / 2


def test_extended_rates_partial_coverage_and_unknown_zero_denominator(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c["fixtures"][0]["home_id"]
    for i, fixture in enumerate(c["fixtures"]):
        box = {"punts": 0, "punt_yards": 0}
        if not i: box.update(punt_return_yards_allowed=0, punt_touchbacks=0)
        c = api.record_result(c, fixture["id"], result(f"extended-partial-{i}",
            home_stats=box if fixture["home_id"] == target else stats(),
            away_stats=box if fixture["away_id"] == target else stats()))
    row = next(r for r in api.campaign_view(c)["statistics"] if r["participant_id"] == target)
    assert row["offense"]["net_punt_average"] is None
    assert row["offense_games"]["net_punt_average"] == 1
    assert row["offense_games"]["gross_punt_average"] == 2
    assert row["offense"]["longest_rush"] is None
    assert row["offense_games"]["longest_rush"] == 0


@pytest.mark.parametrize("box", [
    {"third_down_attempts": 1, "third_down_conversions": 2},
    {"extra_points_attempted": 0, "extra_points_made": 1},
    {"rushing_fumbles": 0, "rushing_fumbles_lost": 1},
    {"punts": 1, "punts_blocked": 2},
])
def test_extended_result_rejects_impossible_counter_pairs(api, participants, box):
    c = campaign(api, participants[:2])
    with pytest.raises(ValueError):
        api.record_result(c, c["fixtures"][0]["id"], result(home_stats=box))


def test_all_extended_fields_survive_result_export_import_with_signed_returns(api, participants):
    from paydirt.team_stats import EXTENDED_TEAM_FIELDS
    c = campaign(api, participants[:2])
    box = dict.fromkeys(EXTENDED_TEAM_FIELDS, 0)
    box.update(kickoff_return_yards=-3, punt_return_yards=-2, punt_return_yards_allowed=-2)
    fixture = c["fixtures"][0]
    c = api.record_result(c, fixture["id"], result(home_stats=box))
    imported = api.import_campaign(api.export_campaign(c))
    assert imported["fixtures"][0]["result"]["home_stats"] == box
    row = next(r for r in api.campaign_view(c)["statistics"] if r["participant_id"] == fixture["home_id"])
    assert all(row["offense"][key] == value for key, value in box.items())


def test_return_and_fourth_down_rates_use_weighted_paired_inputs(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c["fixtures"][0]["home_id"]
    for i, fixture in enumerate(c["fixtures"]):
        box = {"kickoff_returns": 1 if i == 0 else 3, "kickoff_return_yards": 10 if i == 0 else 70,
                   "punt_returns": 1 if i == 0 else 3, "punt_return_yards": -2 if i == 0 else 22,
                   "fourth_down_attempts": 1 if i == 0 else 3, "fourth_down_conversions": 1}
        c = api.record_result(c, fixture["id"], result(f"returns-{i}",
            home_stats=box if fixture["home_id"] == target else stats(),
            away_stats=box if fixture["away_id"] == target else stats()))
    row = next(r for r in api.campaign_view(c)["statistics"] if r["participant_id"] == target)
    for rate, expected in (("kickoff_return_average", 20), ("punt_return_average", 5),
                           ("fourth_down_conversion_percentage", 50)):
        assert row["offense"][rate] == row["offense_per_game"][rate] == expected
        assert row["offense_games"][rate] == 2


def test_legacy_final_scores_have_coverage_without_optional_stat_boxes(api, participants):
    c = campaign(api, participants[:2])
    fixture = c["fixtures"][0]
    c = api.record_result(c, fixture["id"], result(home_score=17, away_score=10, home_stats=None, away_stats=None))
    row = next(r for r in api.campaign_view(c)["statistics"] if r["participant_id"] == fixture["home_id"])
    assert row["offense"]["points_scored"] == 17
    assert row["defense"]["points_scored"] == 10
    assert row["offense_games"]["points_scored"] == row["defense_games"]["points_scored"] == 1
    assert row["offense"]["punts"] is None


def test_allowed_punt_return_average_is_weighted_and_distinct_from_own_returns(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c["fixtures"][0]["home_id"]
    for i, fixture in enumerate(c["fixtures"]):
        box = {"punts_returned": 1 if i == 0 else 3, "punt_return_yards_allowed": 4 if i == 0 else 20,
               "punt_returns": 1, "punt_return_yards": 12}
        c = api.record_result(c, fixture["id"], result(f"allowed-returns-{i}",
            home_stats=box if fixture["home_id"] == target else stats(),
            away_stats=box if fixture["away_id"] == target else stats()))
    row = next(r for r in api.campaign_view(c)["statistics"] if r["participant_id"] == target)
    assert row["offense"]["punt_return_average_allowed"] == 6
    assert row["offense_per_game"]["punt_return_average_allowed"] == 6
    assert row["offense_games"]["punt_return_average_allowed"] == 2
    assert row["offense"]["punt_return_average"] == 12


def test_turnover_differential_pairs_opponent_and_own_boxes_not_independent_totals(api, participants):
    c = campaign(api, participants[:2], schedule="double_round_robin")
    target = c["fixtures"][0]["home_id"]
    for i, fixture in enumerate(c["fixtures"]):
        own, opponent = {"turnovers": 1 if i == 0 else 9}, {"turnovers": 4} if i == 0 else {}
        c = api.record_result(c, fixture["id"], result(f"differential-{i}",
            home_stats=own if fixture["home_id"] == target else opponent,
            away_stats=own if fixture["away_id"] == target else opponent))
    rows = {r["participant_id"]: r for r in api.campaign_view(c)["statistics"]}
    row = rows[target]
    assert row["turnover_summary"] == {"giveaways": 1, "takeaways": 4, "differential": 3, "games": 1}
    other = next(r for key, r in rows.items() if key != target)
    assert other["turnover_summary"] == {"giveaways": 4, "takeaways": 1, "differential": -3, "games": 1}

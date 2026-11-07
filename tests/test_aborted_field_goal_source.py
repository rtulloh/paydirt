"""Reviewed no-kick snaps retain events and unknown movement."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from paydirt.pfr_event_reconciliation import load_event_reconciliations, play_fingerprint
from paydirt.pfr_play_by_play import PfrGame, PfrPlay, classify_pfr_game


def game() -> PfrGame:
    """One actual kick and one misleading no-kick label, using synthetic data."""
    return PfrGame(
        "synthetic-2026-aborted-fg", "FOX", "OWL",
        {"center": "FOX", "holder": "FOX", "kicker": "FOX", "defender": "OWL"},
        {"center": "C", "holder": "QB", "kicker": "K", "defender": "DB"},
        {"alex center": "center", "pat holder": "holder", "lee kicker": "kicker",
         "sam defender": "defender"},
        (PfrPlay("synthetic-2026-aborted-fg", 7, 1, "9:00", 4, 6, "OWL 20", 0, 0,
                 "Alex Center 37 yard field goal no good", ("center",)),
         PfrPlay("synthetic-2026-aborted-fg", 20, 2, "8:00", 4, 4, "OWL 22", 0, 0,
                 "Lee Kicker 39 yard field goal good", ("kicker",))),
        field_goal_box={"kicker": ("FOX", 1, 1)},
    )


def sidecar(tmp_path: Path, **changes: object) -> tuple[Path, dict]:
    source = game()
    book = tmp_path / "synthetic-book.pdf"
    book.write_bytes(b"synthetic reviewed bad snap, no historical fixture")
    record = {
        "kind": "aborted_field_goal", "game_id": source.game_id, "play_number": 7,
        "raw_game_sha256": hashlib.sha256(b"synthetic raw input").hexdigest(),
        "raw_play_sha256": play_fingerprint(source.plays[0]),
        "offense_team": "FOX", "fumbling_player_id": "center",
        "recovering_team": "FOX", "individual_lost": None,
        "credited_player_id": "holder", "credited_rushing_yards": 0,
        "physical_initial_yards": None,
        "evidence": [{"file": book.name, "sha256": hashlib.sha256(book.read_bytes()).hexdigest(),
                      "url": "https://example.org/reviewed-book.pdf", "pages": [2, 5]}],
        **changes,
    }
    path = tmp_path / "reviewed.json"
    path.write_text(json.dumps({"schema_version": 4, "events": [record]}))
    return path, record


@pytest.mark.parametrize("policy", [None, "known_physical_v1", "credited_fumble_proxy_v1",
                                   "source_reported_gain_proxy_v1"])
def test_reviewed_nonattempt_keeps_one_snap_and_distinct_credit_actor(
    tmp_path: Path, policy: str | None,
) -> None:
    path, record = sidecar(tmp_path)
    inventory = load_event_reconciliations(path)
    facts = inventory.for_game(game(), record["raw_game_sha256"])
    result = classify_pfr_game(game(), event_facts=facts, fumble_gain_policy=policy)
    inventory.assert_all_applied()
    assert [(a.play_number, a.made) for a in result.field_goals] == [(20, True)]
    assert result.event_counts["FOX"]["field_goal_attempts"] == 1
    assert not result.source_conflicts
    assert result.diagnostics.get("box_reconciled_fumble_recoveries", 0) == 0
    assert len(result.fumbles) == 1
    assert (result.fumbles[0].unit, result.fumbles[0].lost) == ("field_goal_snap", None)
    assert not result.plays
    assert not result.fumble_gain_projections
    assert len(result.unsupported_fields) == 1
    assert result.unsupported_fields[0]["field"] == "aborted_field_goal_projection"
    receipt, = result.fumble_reconciliations
    assert receipt["fumbling_player_id"] == "center"
    assert receipt["credited_player_id"] == "holder"
    assert receipt["credited_rushing_yards"] == 0
    assert receipt["physical_initial_yards"] is None
    assert receipt["possession_changed"] is False
    assert receipt["individual_lost"] is None
    assert facts[7].to_dict() == record
    assert game().plays[0].detail == "Alex Center 37 yard field goal no good"


@pytest.mark.parametrize("changes", [
    {"recovering_team": "OWL", "individual_lost": True},
    {"recovering_team": None, "individual_lost": None},
    {"credited_player_id": None, "credited_rushing_yards": None},
])
def test_nullable_facts_do_not_invent_credit_or_movement(tmp_path: Path, changes: dict) -> None:
    path, record = sidecar(tmp_path, **changes)
    fact = load_event_reconciliations(path).for_game(game(), record["raw_game_sha256"])[7]
    result = classify_pfr_game(game(), event_facts={7: fact})
    assert result.fumbles[0].lost is changes.get("individual_lost")
    assert result.unsupported_fields
    assert fact.physical_initial_yards is None
    assert fact.credited_rushing_yards == changes.get("credited_rushing_yards", 0)


@pytest.mark.parametrize("changes", [
    {"offense_team": "OTHER"}, {"fumbling_player_id": "missing"},
    {"fumbling_player_id": "defender"}, {"recovering_team": "OTHER"},
    {"credited_player_id": "defender"},
    {"credited_player_id": None, "credited_rushing_yards": 0},
    {"credited_rushing_yards": True}, {"physical_initial_yards": False},
    {"individual_lost": "no"}, {"recovering_team": "FOX", "individual_lost": True},
    {"recovering_team": "OWL", "individual_lost": False},
])
def test_invalid_snap_facts_fail(tmp_path: Path, changes: dict) -> None:
    path, record = sidecar(tmp_path, **changes)
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(game(), record["raw_game_sha256"])


@pytest.mark.parametrize("detail", [
    "Alex Center left end for no gain", "Alex Center 37 yard field goal good",
    "Alex Center 37 yard field goal blocked", "Alex Center 37 yard field goal no good (no play)",
])
def test_review_cannot_hide_incompatible_source_play(tmp_path: Path, detail: str) -> None:
    changed = replace(game(), plays=(replace(game().plays[0], detail=detail), *game().plays[1:]))
    path, record = sidecar(tmp_path)
    record["raw_play_sha256"] = play_fingerprint(changed.plays[0])
    path.write_text(json.dumps({"schema_version": 4, "events": [record]}))
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(changed, record["raw_game_sha256"])


def test_unreviewed_label_still_exposes_conflict() -> None:
    result = classify_pfr_game(game())
    assert len(result.source_conflicts) == 1
    assert result.source_conflicts[0]["mechanism"] == "unknown"
    assert not result.fumbles
    assert len(result.field_goals) == 1


def test_review_cannot_erase_official_kicker_attempt(tmp_path: Path) -> None:
    changed = replace(game(), field_goal_box={"center": ("FOX", 1, 0), "kicker": ("FOX", 1, 1)})
    path, record = sidecar(tmp_path)
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(changed, record["raw_game_sha256"])


def test_reviewed_actor_team_can_fill_absent_secondary_metadata(tmp_path: Path) -> None:
    changed = replace(game(), player_teams={k: v for k, v in game().player_teams.items()
                                           if k != "center"})
    path, record = sidecar(tmp_path)
    fact = load_event_reconciliations(path).for_game(changed, record["raw_game_sha256"])[7]
    result = classify_pfr_game(changed, event_facts={7: fact})
    assert result.fumbles[0].team == "FOX"
    assert not result.source_conflicts
    assert len(result.field_goals) == 1

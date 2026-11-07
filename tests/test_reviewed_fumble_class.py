"""Independent class evidence does not promote reported gain to official credit."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from paydirt.pfr_event_reconciliation import load_event_reconciliations
from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_pfr_event_reconciliation import _fumble_sidecar
from tests.test_reported_fumble_gain import REPORTED, game_with


def load_class_fact(tmp_path: Path, kind: str, detail: str = "") -> tuple:
    """Bind a synthetic source's class, leaving credit and physical gain null."""
    game = game_with(detail or "Lee Runner for -2 yards. Lee Runner fumbles, recovered by Lee Runner")
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(originating_kind=kind, credited_kind=None, credited_yards=None,
                  out_of_bounds=False, initial_gain=None)
    path.write_text(json.dumps({"schema_version": 4, "events": [record]}))
    return game, load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])


@pytest.mark.parametrize("kind,expected,sacks", [
    ("rushing", ["F - 2"], 0), ("receiving", ["F - 2"], 0),
    ("sack", ["QT", "F - 2"], 1),
])
def test_reviewed_class_combines_only_with_scoped_actor_bound_reported_gain(
    tmp_path: Path, kind: str, expected: list[str], sacks: int,
) -> None:
    game, facts = load_class_fact(tmp_path, kind)
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    projection, = result.fumble_gain_projections
    assert not result.unsupported_fields
    assert projection.originating_kind == kind
    assert projection.modeled_gain_basis == "source_reported_proxy"
    assert projection.source_facts.credited_kind is None
    assert projection.source_facts.credited_yards is None
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.reported_actor == "lee"
    assert [p.result for p in result.plays] == expected
    assert result.event_counts.get("FOX", {}).get("sacks", 0) == sacks
    assert facts[7].to_dict()["originating_kind"] == kind


@pytest.mark.parametrize("policy", ["known_physical_v1", "credited_fumble_proxy_v1"])
def test_class_only_does_not_satisfy_stricter_gain_policies(tmp_path: Path, policy: str) -> None:
    game, facts = load_class_fact(tmp_path, "rushing")
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=policy)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


@pytest.mark.parametrize("kind,detail", [
    ("rushing", "Pat Passer sacked by Sam Defender for 2 yards. Pat Passer fumbles, recovered by Lee Runner"),
    ("sack", "Lee Runner left end for -2 yards. Lee Runner fumbles, recovered by Lee Runner"),
    ("receiving", "Lee Runner left end for 2 yards. Lee Runner fumbles, recovered by Lee Runner"),
    ("quarterback", "Lee Runner for 2 yards. Lee Runner fumbles, recovered by Lee Runner"),
])
def test_conflicting_or_untyped_class_review_fails(tmp_path: Path, kind: str, detail: str) -> None:
    with pytest.raises(ValueError):
        load_class_fact(tmp_path, kind, detail)


@pytest.mark.parametrize("detail", [
    "Lee Runner for -2 yards. Pat Passer fumbles, recovered by Lee Runner",
    "Lee Runner fumbles, recovered by Lee Runner and returned for 12 yards",
    "Lee Runner for -2 yards. Lee Runner fumbles. Pat Passer fumbles, recovered by Lee Runner",
])
def test_reviewed_class_cannot_supply_missing_or_unscoped_number(tmp_path: Path, detail: str) -> None:
    game, facts = load_class_fact(tmp_path, "rushing", detail)
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def test_bare_gain_without_class_review_stays_rejected() -> None:
    game = game_with("Lee Runner for -2 yards. Lee Runner fumbles, recovered by Lee Runner")
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def reviewed_actor_fact(tmp_path: Path, *, detail: str = "", **changes: object) -> tuple:
    game = game_with(detail or "Lee Runner for -2 yards. Lee Runner fumbles, recovered by Sam Defender")
    game = replace(game, player_teams={**game.player_teams, "lee": None})
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(originating_kind="rushing", originating_player_id="lee",
                  originating_team="FOX", credited_kind=None, credited_yards=None,
                  fumble_lost=True, out_of_bounds=False, initial_gain=None)
    record.update(changes)
    path.write_text(json.dumps({"schema_version": 4, "events": [record]}))
    return game, record, path


def test_reviewed_actor_team_fills_missing_metadata_without_using_recoverer(tmp_path: Path) -> None:
    game, record, path = reviewed_actor_fact(tmp_path)
    facts = load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    projection, = result.fumble_gain_projections
    assert not result.unsupported_fields
    assert projection.source_facts.reported_actor == "lee"
    assert projection.source_facts.reported_team == "FOX"
    assert projection.source_facts.lost is True
    assert result.plays[0].team == "FOX"
    assert facts[7].to_dict()["originating_player_id"] == "lee"
    assert facts[7].to_dict()["originating_team"] == "FOX"
    assert game.player_teams["lee"] is None
    assert projection.source_facts.credited_yards is None
    assert projection.source_facts.physical_initial_yards is None


@pytest.mark.parametrize("changes", [
    {"originating_player_id": "pat"}, {"originating_player_id": "unknown"},
    {"originating_team": "UNKNOWN"}, {"originating_team": None},
    {"originating_player_id": ""},
])
def test_reviewed_actor_team_requires_exact_primary_identity(tmp_path: Path, changes: dict) -> None:
    game, record, path = reviewed_actor_fact(tmp_path, **changes)
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])


def test_reviewed_actor_team_cannot_override_known_player_team(tmp_path: Path) -> None:
    game, record, path = reviewed_actor_fact(tmp_path)
    game = replace(game, player_teams={**game.player_teams, "lee": "OWL"})
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])


def test_missing_team_stays_rejected_without_an_independent_review(tmp_path: Path) -> None:
    game, _, _ = reviewed_actor_fact(tmp_path)
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def test_reviewed_receiver_team_is_bound_to_receiver_without_changing_passer(tmp_path: Path) -> None:
    game, record, path = reviewed_actor_fact(
        tmp_path, originating_kind="receiving",
        detail="Pat Passer pass complete to Lee Runner for 8 yards. "
               "Lee Runner fumbles, recovered by Sam Defender",
    )
    facts = load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    projection, = result.fumble_gain_projections
    assert not result.unsupported_fields
    assert projection.originating_kind == "receiving"
    assert projection.source_facts.reported_actor == "lee"
    assert projection.modeled_initial_yards == 8
    assert game.player_teams["lee"] is None
    assert game.player_teams["pat"] == "FOX"

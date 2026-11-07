"""Reviewed reported numbers remain distinct from statistical/physical credit."""

import json
from pathlib import Path

import pytest

from paydirt.pfr_event_reconciliation import load_event_reconciliations
from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_pfr_event_reconciliation import _fumble_sidecar
from tests.test_reported_fumble_gain import REPORTED, game_with


def reported_review(tmp_path: Path, **changes: object) -> tuple:
    game = game_with(
        "Pat Passer sacked by, recovered by Lee Runner at FOX14 "
        "Sam Defender for 6 yards. Pat Passer fumbles (forced by Sam Defender)"
    )
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(originating_kind="sack", originating_player_id="pat",
                  originating_team="FOX", credited_kind=None, credited_yards=None,
                  initial_gain=None, out_of_bounds=False, reported_primary_yards=-6)
    record.update(changes)
    path.write_text(json.dumps({"schema_version": 5, "events": [record]}))
    return game, path, record


def test_reviewed_reported_gain_repairs_malformed_number_without_promoting_credit(tmp_path: Path) -> None:
    game, path, record = reported_review(tmp_path)
    inventory = load_event_reconciliations(path)
    facts = inventory.for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    projection, = result.fumble_gain_projections
    assert not result.unsupported_fields
    assert [p.result for p in result.plays] == ["QT", "F - 6"]
    assert projection.modeled_gain_basis == "source_reported_proxy"
    assert projection.source_facts.reported_yards == -6
    assert projection.source_facts.reported_actor == "pat"
    assert projection.source_facts.reported_scope == "primary_before_fumble"
    assert projection.source_facts.credited_yards is None
    assert projection.source_facts.physical_initial_yards is None
    assert facts[7].to_dict()["reported_primary_yards"] == -6
    inventory.assert_all_applied()


@pytest.mark.parametrize("policy", ["known_physical_v1", "credited_fumble_proxy_v1"])
def test_reported_review_supplies_no_stricter_policy_credit(tmp_path: Path, policy: str) -> None:
    game, path, record = reported_review(tmp_path)
    facts = load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=policy)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


@pytest.mark.parametrize("changes", [
    {"reported_primary_yards": True}, {"reported_primary_yards": "-6"},
    {"reported_primary_yards": None}, {"reported_primary_yards": 6},
    {"originating_player_id": None}, {"originating_kind": None},
    {"originating_kind": "punt_return"},
])
def test_reported_review_requires_primary_class_actor_and_signed_integer(
    tmp_path: Path, changes: dict,
) -> None:
    game, path, record = reported_review(tmp_path, **changes)
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])


@pytest.mark.parametrize("action", ["left end ", ""])
def test_reported_review_cannot_hide_a_conflicting_supported_raw_gain(
    tmp_path: Path, action: str,
) -> None:
    game = game_with(f"Lee Runner {action}for 3 yards. Lee Runner fumbles, recovered by Lee Runner")
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(originating_kind="rushing", originating_player_id="lee",
                  originating_team="FOX", credited_kind=None, credited_yards=None,
                  initial_gain=None, out_of_bounds=False, reported_primary_yards=9)
    path.write_text(json.dumps({"schema_version": 5, "events": [record]}))
    with pytest.raises(ValueError, match="reported.*conflict|conflict.*reported"):
        load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])


def test_malformed_source_without_review_stays_unsupported(tmp_path: Path) -> None:
    game, _, _ = reported_review(tmp_path)
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


@pytest.mark.parametrize("detail", [
    "Pat Passer for 2 yards. Lee Runner fumbles, recovered by Lee Runner",
    "Pat Passer fumbles, recovered by Lee Runner. Lee Runner fumbles, recovered by Pat Passer",
    "Pat Passer laterals to Lee Runner. Pat Passer fumbles, recovered by Lee Runner",
])
def test_reported_review_cannot_bypass_occurrence_and_scope_guards(tmp_path: Path, detail: str) -> None:
    game = game_with(detail)
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(originating_kind="rushing", originating_player_id="pat",
                  originating_team="FOX", credited_kind=None, credited_yards=None,
                  initial_gain=None, out_of_bounds=False, reported_primary_yards=2)
    path.write_text(json.dumps({"schema_version": 5, "events": [record]}))
    with pytest.raises(ValueError):
        load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])

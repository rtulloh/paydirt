"""Reviewed standalone kick returns retain their special-team origin."""

import json
from pathlib import Path

import pytest

from paydirt.pfr_event_reconciliation import load_event_reconciliations
from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_pfr_event_reconciliation import _fumble_sidecar
from tests.test_reported_fumble_gain import REPORTED, game_with


def reviewed_return(tmp_path: Path, *, kind: str = "kickoff_return", detail: str = "") -> tuple:
    game = game_with(detail or "returned by Lee Runner for 26 yards. Lee Runner fumbles, "
                     "recovered by Lee Runner at FOX28")
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(originating_kind=kind, originating_player_id="lee", originating_team="FOX",
                  credited_kind=None, credited_yards=None, initial_gain=None,
                  fumble_lost=False, out_of_bounds=False)
    path.write_text(json.dumps({"schema_version": 4, "events": [record]}))
    return game, load_event_reconciliations(path).for_game(game, record["raw_game_sha256"])


@pytest.mark.parametrize("kind", ["kickoff_return", "punt_return"])
def test_reviewed_standalone_return_is_one_special_f_without_primary_rush(
    tmp_path: Path, kind: str,
) -> None:
    game, facts = reviewed_return(tmp_path, kind=kind)
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    assert not result.unsupported_fields
    assert [(p.team, p.unit, p.chart, p.result) for p in result.plays] == [
        ("FOX", "special_teams", kind, "F + 26")]
    event, = result.fumbles
    assert event.unit == kind and event.lost is False
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == kind
    assert projection.source_facts.reported_scope == "return_before_fumble"
    assert projection.source_facts.reported_yards == 26
    assert projection.source_facts.credited_yards is None
    assert projection.source_facts.physical_initial_yards is None
    assert result.event_counts.get("FOX", {}).get("sacks", 0) == 0


@pytest.mark.parametrize("policy", ["known_physical_v1", "credited_fumble_proxy_v1"])
def test_return_class_does_not_supply_stricter_gain_evidence(tmp_path: Path, policy: str) -> None:
    game, facts = reviewed_return(tmp_path)
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=policy)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


@pytest.mark.parametrize("detail", [
    ("returned by Lee Runner for unknown yards. Lee Runner fumbles, "
     "recovered by Lee Runner and returned for 26 yards"),
    "returned by Lee Runner for 26 yards. Pat Passer fumbles, recovered by Lee Runner",
])
def test_return_review_cannot_borrow_a_recovery_gain_or_different_actor(tmp_path: Path, detail: str) -> None:
    game, facts = reviewed_return(tmp_path, detail=detail)
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def test_standalone_return_without_review_does_not_invent_a_kick_origin() -> None:
    game = game_with("returned by Lee Runner for 26 yards. Lee Runner fumbles, recovered by Lee Runner")
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields

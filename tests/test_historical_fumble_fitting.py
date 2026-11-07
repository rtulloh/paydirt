"""Fitting exclusions retain evidence and never suppress unrelated errors."""
from dataclasses import replace

import pytest

from paydirt import historical_fumble_proxy as proxy
from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_reported_fumble_gain import game_with


def held():
    game = game_with("Pat Passer fumbles, recovered by Lee Runner at FOX35 and returned for 9 yards")
    return game, classify_pfr_game(game, fumble_gain_policy=proxy.POLICY_V2)


def test_exclusion_retains_original_and_records_identity() -> None:
    game, classified = held()
    original = classified
    fitted, records = proxy.fitting_population(game, classified, raw_sha256="a" * 64)
    assert fitted == () and len(records) == 1
    assert classified == original and len(classified.fumbles) == 1
    record, = records
    assert record["event_id"] == "synthetic-2026:7"
    assert record["raw_game_sha256"] == "a" * 64
    assert record["team"] == "FOX" and record["lost"] is False
    assert record["reason"] and record["raw_play_sha256"]
    assert record["scope"] == "fitting_only"


@pytest.mark.parametrize("changes", [
    {"source_conflicts": ({"reason": "conflict"},)},
    {"unsupported_fields": ({"game_id": "synthetic-2026", "play_number": 7,
                             "team": "FOX", "field": "other_required", "reason": "missing"},)},
])
def test_exclusion_cannot_hide_conflict_or_other_required_field(changes: dict) -> None:
    game, classified = held()
    with pytest.raises(ValueError):
        proxy.fitting_population(game, replace(classified, **changes), raw_sha256="a" * 64)


def test_supported_event_remains_fitted() -> None:
    game = game_with("Pat Passer scrambles for 3 yards. Pat Passer fumbles, recovered by Lee Runner at FOX43")
    classified = classify_pfr_game(game, fumble_gain_policy=proxy.POLICY_V2)
    fitted, records = proxy.fitting_population(game, classified, raw_sha256="a" * 64)
    assert fitted == classified.fumbles and records == []


@pytest.mark.parametrize("damage", ["team", "mechanism"])
def test_disclosure_rejects_wrong_event_attribution(damage: str) -> None:
    game, classified = held()
    fitted, records = proxy.fitting_population(game, classified, raw_sha256="a" * 64)
    disclosure = proxy.fitting_metadata(proxy.FITTING_POLICY, list(classified.fumbles), list(fitted), records)
    assert disclosure is not None
    if damage == "team":
        disclosure["teams"]["FOX"]["excluded_events"] = 0
        disclosure["teams"]["OWL"] = {"full_events": 0, "fitted_events": 0,
                                      "full_lost": 0, "fitted_lost": 0, "excluded_events": 1}
    else:
        disclosure["excluded_by_mechanism"] = {"aborted_field_goal_projection": 1}
    with pytest.raises(ValueError):
        proxy.validate_fitting_metadata(disclosure)

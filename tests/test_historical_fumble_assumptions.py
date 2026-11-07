"""Explicit modeled role assumptions preserve source facts and event accounting."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from paydirt.pfr_event_reconciliation import FumbleEventFact, play_fingerprint
from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_reported_fumble_gain import game_with

POLICY = "historical_fumble_class_proxy_v1"


@pytest.mark.parametrize("yards,kind,basis", [
    (-1, "rushing", "assumed_qb_snap"), (0, "rushing", "assumed_qb_snap"),
    (1, "rushing", "assumed_qb_snap"), (-2, "sack", "assumed_qb_sack"),
    (-5, "sack", "assumed_qb_sack"), (-6, "sack", "assumed_qb_sack"),
])
@pytest.mark.parametrize("lost", [False, True])
def test_explicit_qb_gain_has_separate_modeled_class(yards: int, kind: str, basis: str, lost: bool) -> None:
    recoverer = "Sam Defender" if lost else "Lee Runner"
    game = game_with(f"Pat Passer for {yards} yards. Pat Passer fumbles, recovered by {recoverer} at FOX39")
    original = game.plays[0]
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert not result.unsupported_fields
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == kind
    record = projection.to_dict()
    assert record["modeled_class_basis"] == basis
    assert record["modeled_role"] == "QB"
    assert projection.modeled_initial_yards == yards
    assert projection.modeled_gain_basis == "source_reported_proxy"
    assert projection.source_facts.credited_kind is None
    assert projection.source_facts.credited_yards is None
    assert projection.source_facts.reported_kind is None
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.lost is lost
    assert result.diagnostics["modeled_fumble_classes"] == 1
    assert result.diagnostics[f"modeled_fumble_class_{basis}"] == 1
    assert len(result.fumbles) == 1 and game.plays[0] == original
    assert [p.result for p in result.plays] == (["QT"] if kind == "sack" else []) + [projection.chart_result]


@pytest.mark.parametrize("yards,kind,role", [
    (-6, "sack", "QB"), (-5, "sack", "QB"), (-2, "sack", "QB"),
    (-1, "rushing", "QB"), (0, "rushing", "QB"), (1, "rushing", "QB"),
    (2, "rushing", "RB"), (5, "rushing", "RB"),
    (6, "receiving", "receiver"), (20, "receiving", "receiver"),
])
def test_unknown_role_uses_only_bounded_explicit_primary_gain(yards: int, kind: str, role: str) -> None:
    game = game_with(f"Lee Runner for {yards} yards. Lee Runner fumbles, recovered by Sam Defender at FOX45")
    game = replace(game, player_positions={k: v for k, v in game.player_positions.items() if k != "lee"})
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert not result.unsupported_fields
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == kind
    assert projection.to_dict()["modeled_role"] == role
    assert projection.to_dict()["modeled_class_basis"].startswith("assumed_unknown_role_")
    assert projection.source_facts.credited_kind is None
    assert projection.source_facts.reported_kind is None
    assert projection.source_facts.physical_initial_yards is None
    assert len(result.fumbles) == 1


@pytest.mark.parametrize("detail,positions", [
    ("Lee Runner for 3 yards. Lee Runner fumbles, recovered by Sam Defender at FOX43", None),
    ("Pat Passer fumbles, recovered by Lee Runner at FOX35 and returned for 9 yards", None),
    ("Pat Passer for -3 yards. Pat Passer fumbles", None),
    ("Pat Passer for 2 yards. Pat Passer fumbles, recovered by Sam Defender at FOX42", None),
])
def test_missing_gain_ownership_or_pending_branches_stay_held(detail: str, positions: dict | None) -> None:
    game = game_with(detail)
    if positions is not None:
        game = replace(game, player_positions=positions)
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert result.unsupported_fields and not result.fumble_gain_projections
    assert len(result.fumbles) == 1


def test_supported_explicit_run_precedes_qb_assumption() -> None:
    game = game_with("Pat Passer scrambles for -5 yards. Pat Passer fumbles, recovered by Lee Runner at FOX35")
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == "rushing"
    assert projection.source_facts.reported_kind == "rushing"
    assert projection.modeled_initial_yards == -5
    assert projection.to_dict().get("modeled_class_basis") is None


def test_old_strict_policy_keeps_ambiguous_qb_class_held() -> None:
    game = game_with("Pat Passer for 0 yards. Pat Passer fumbles, recovered by Lee Runner at FOX40")
    result = classify_pfr_game(game, fumble_gain_policy="source_reported_gain_proxy_v1")
    assert result.unsupported_fields and not result.fumble_gain_projections


def test_reviewed_physical_and_loose_ball_facts_survive_role_assumption() -> None:
    game = game_with("Pat Passer for -1 yards. Pat Passer fumbles, recovered by Lee Runner at FOX37")
    fact = FumbleEventFact(game.game_id, 7, "a" * 64, play_fingerprint(game.plays[0]), (),
                           False, False, initial_gain=-2, initial_gain_reviewed=True,
                           loose_ball_yards=-1, recovery_advance_yards=0,
                           loose_ball_yards_reviewed=True, recovery_advance_yards_reviewed=True)
    original = fact.to_dict()
    result = classify_pfr_game(game, event_facts={7: fact}, fumble_gain_policy=POLICY)
    projection, = result.fumble_gain_projections
    assert projection.modeled_initial_yards == -2
    assert projection.modeled_gain_basis == "physical"
    assert projection.originating_kind == "sack"
    assert projection.source_facts.physical_initial_yards == -2
    assert projection.source_facts.loose_ball_yards == -1
    assert projection.source_facts.recovery_advance_yards == 0
    assert projection.source_facts.reported_yards == -1
    assert fact.to_dict() == original


def test_assumption_cannot_hide_stale_reviewed_event_identity() -> None:
    game = game_with("Pat Passer for -3 yards. Pat Passer fumbles, recovered by Lee Runner at FOX37")
    fact = FumbleEventFact(game.game_id, 7, "a" * 64, "b" * 64, (), False, False)
    result = classify_pfr_game(game, event_facts={7: fact}, fumble_gain_policy=POLICY)
    assert result.unsupported_fields and not result.fumble_gain_projections


def test_official_rushing_credit_precedes_qb_sack_assumption() -> None:
    game = game_with("Pat Passer for -3 yards. Pat Passer fumbles, recovered by Lee Runner at FOX37")
    fact = FumbleEventFact(game.game_id, 7, "a" * 64, play_fingerprint(game.plays[0]), (),
                           False, False, credited_kind="rushing", credited_yards=-2)
    result = classify_pfr_game(game, event_facts={7: fact}, fumble_gain_policy=POLICY)
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == "rushing"
    assert projection.modeled_initial_yards == -2
    assert projection.source_facts.credited_yards == -2
    assert projection.to_dict().get("modeled_class_basis") is None


def test_portable_pfr_ledger_declares_versioned_unverified_assumptions(tmp_path: Path, monkeypatch) -> None:
    import generate_pfr_charts as command

    game = game_with("Pat Passer for 0 yards. Pat Passer fumbles, recovered by Lee Runner at FOX40")
    source = tmp_path / "source"
    source.mkdir()
    raw = source / "synthetic-2026.html"
    raw.write_bytes(b"synthetic source bytes")
    monkeypatch.setattr(command, "parse_pfr_boxscore", lambda *_args: game)
    ledger = tmp_path / "ledger.json"
    command._classify_directory(source, None, 8306, ledger, fumble_gain_policy=POLICY)
    record = json.loads(ledger.read_text())
    model = record["modeled_fumble_assumptions"]
    assert model["policy"] == POLICY and model["contract_version"] == 1
    assert model["modeled_events"] == 1
    assert model["source_class_truth_verified"] is False
    assert model["physical_gain_truth_verified"] is False
    assert model["terminal_recovery_gain_proxy"] is False
    assert model["statistical_categories"]["qb_snap"] == "rushing"
    assert record["games"][0]["raw_sha256"]

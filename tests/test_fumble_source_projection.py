"""Credited-fumble experiment: source facts remain separate from modeled gains."""
from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from paydirt.nflverse_play_by_play import classify_nflverse_rows
from paydirt.pfr_event_reconciliation import load_event_reconciliations, play_fingerprint
from paydirt.pfr_play_by_play import PfrGame, PfrPlay, classify_pfr_game

PROXY = "credited_fumble_proxy_v1"
PHYSICAL = "known_physical_v1"


def fact_values(**changes) -> dict:
    return {
        "source_event_id": "synthetic:7",
        "raw_event_sha256": hashlib.sha256(b"synthetic unchanged raw event").hexdigest(),
        "credited_kind": "rushing", "credited_yards": 0,
        "physical_initial_yards": None, "lost": False,
        "loose_ball_yards": -3, "recovery_advance_yards": None,
        **changes,
    }


def project(policy: str = PROXY, **changes):
    module = importlib.import_module("paydirt.fumble_source")
    fact = module.FumbleGainFacts(**fact_values(**changes))
    return fact, module.project_fumble_gain(fact, policy=policy)


@pytest.mark.parametrize("yards,result", [(0, "F"), (-3, "F - 3"), (7, "F + 7")])
@pytest.mark.parametrize("lost", [False, True])
def test_proxy_preserves_null_physical_gain_and_known_zero(yards: int, result: str, lost: bool) -> None:
    fact, projected = project(credited_yards=yards, lost=lost)
    assert fact.physical_initial_yards is None
    assert projected.modeled_initial_yards == yards
    assert projected.modeled_gain_basis == "credited_proxy"
    assert projected.chart_result == result
    record = projected.to_dict()
    assert record["source_facts"] == asdict(fact)
    assert record["source_facts"]["recovery_advance_yards"] is None
    assert record["source_facts"]["loose_ball_yards"] == -3
    assert record["policy"] == PROXY
    assert json.loads(json.dumps(record)) == record


@pytest.mark.parametrize("initial", [-4, 0, 9])
@pytest.mark.parametrize("policy", [PROXY, PHYSICAL])
def test_known_physical_gain_wins_without_rewriting_credit(initial: int, policy: str) -> None:
    fact, projected = project(policy, physical_initial_yards=initial, credited_yards=2)
    assert projected.modeled_initial_yards == initial
    assert projected.modeled_gain_basis == "physical"
    assert fact.credited_yards == 2
    assert fact.physical_initial_yards == initial


@pytest.mark.parametrize("changes", [
    {"credited_yards": None}, {"credited_kind": None}, {"lost": None},
    {"credited_kind": "quarterback"}, {"credited_kind": "rushing", "credited_yards": False},
    {"credited_yards": 1.5}, {"physical_initial_yards": True},
    {"lost": 0}, {"loose_ball_yards": float("nan")}, {"recovery_advance_yards": "2"},
    {"source_event_id": ""}, {"raw_event_sha256": "not-a-hash"},
    {"credited_kind": "sack", "credited_yards": 2},
    {"credited_kind": "sack", "credited_yards": -2, "physical_initial_yards": 1},
])
def test_proxy_rejects_unknown_or_incompatible_required_support(changes: dict) -> None:
    with pytest.raises(ValueError):
        project(**changes)


@pytest.mark.parametrize("policy", [PHYSICAL, "automatic", "", None])
def test_missing_physical_gain_needs_explicit_proxy(policy: str) -> None:
    with pytest.raises(ValueError):
        project(policy)


def nfl_row(**changes) -> dict:
    return {
        "season_type": "REG", "game_id": "synthetic-2026", "play_id": "7",
        "posteam": "FOX", "defteam": "OWL", "play_type": "run",
        "desc": "Pat Quarterback fumbles, recovered by Pat Quarterback",
        "fumble": "1", "fumble_lost": "0", "fumbled_1_team": "FOX",
        "sack": "0", "rush_attempt": "1", "pass_attempt": "0",
        "complete_pass": "0", "interception": "0", "yards_gained": "0",
        "qb_scramble": "0", "run_location": "middle",
        **changes,
    }


@pytest.mark.parametrize("kind,yards,changes,expected", [
    ("rushing", 0, {}, ["F"]),
    ("rushing", -3, {}, ["F - 3"]),
    ("rushing", 4, {}, ["F + 4"]),
    ("sack", 0, {"play_type": "pass", "sack": "1", "rush_attempt": "0", "pass_attempt": "1"}, ["QT", "F"]),
    ("sack", -6, {"play_type": "pass", "sack": "1", "rush_attempt": "0", "pass_attempt": "1"}, ["QT", "F - 6"]),
    ("receiving", 8, {"play_type": "pass", "rush_attempt": "0", "pass_attempt": "1", "complete_pass": "1"}, ["F + 8"]),
])
def test_nflverse_proxy_records_credited_facts_and_projects_once(
    kind: str, yards: int, changes: dict, expected: list[str],
) -> None:
    row = nfl_row(yards_gained=str(yards), **changes)
    before = deepcopy(row)
    result = classify_nflverse_rows([row], fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert [play.result for play in result.plays] == expected
    assert len(result.fumbles) == len(result.fumble_gain_projections) == 1
    record = result.fumble_gain_projections[0].to_dict()
    assert record["source_facts"]["physical_initial_yards"] is None
    assert record["source_facts"]["credited_kind"] == kind
    assert record["source_facts"]["credited_yards"] == yards
    assert record["modeled_initial_yards"] == yards
    assert record["modeled_gain_basis"] == "credited_proxy"
    assert row == before


@pytest.mark.parametrize("yards", ["0", "-3"])
def test_known_rushing_fumble_stays_primary_despite_qb_scramble_metadata(yards: str) -> None:
    row = nfl_row(yards_gained=yards, qb_scramble="1",
                  desc="Pat Quarterback scrambles and fumbles, recovered by Pat Quarterback")
    result = classify_nflverse_rows([row], fumble_gain_policy=PROXY)
    assert len(result.plays) == 1
    assert result.plays[0].chart in {"line_plunge", "off_tackle", "end_run", "draw"}
    assert result.fumbles[0].unit == "rushing"
    assert result.diagnostics["inferred_primary_rushing_fumble_family"] == 1


@pytest.mark.parametrize("changes,field", [
    ({"yards_gained": ""}, "fumble_gain_projection"),
    ({"fumble_lost": ""}, "fumble_gain_projection"),
    ({"rush_attempt": "0"}, "fumble_gain_projection"),
    ({"fumbled_1_team": ""}, "fumble_gain_projection"),
    ({"fumbled_1_team": "OWL"}, "fumble_gain_projection"),
    ({"sack": "1", "yards_gained": "2"}, "fumble_gain_projection"),
])
def test_nflverse_proxy_retains_explicit_unsupported_events(changes: dict, field: str) -> None:
    result = classify_nflverse_rows([nfl_row(**changes)], fumble_gain_policy=PROXY)
    assert any(item["field"] == field for item in result.unsupported_fields)
    assert not result.fumble_gain_projections


def test_compound_and_interception_return_ownership_guards_survive_proxy() -> None:
    compound = nfl_row(fumbled_2_team="FOX", fumbled_2_player_name="Second Player")
    interception = nfl_row(play_type="pass", rush_attempt="0", pass_attempt="1",
                           interception="1", fumbled_1_team="OWL", return_team="OWL")
    result = classify_nflverse_rows([compound, interception], fumble_gain_policy=PROXY)
    assert any(item["field"] == "fumble_ownership" for item in result.unsupported_fields)
    assert not result.fumble_gain_projections
    assert not result.fumbles
    assert result.diagnostics["interception_return_fumbles"] == 1


def pfr_game() -> PfrGame:
    return PfrGame(
        "synthetic-2026", "FOX", "OWL", {"pat": "FOX"}, {"pat": "QB"},
        {"pat quarterback": "pat"},
        (PfrPlay("synthetic-2026", 7, 1, "10:00", 1, 10, "FOX 40", 0, 0,
                 "Pat Quarterback fumbles, recovered by Pat Quarterback", ("pat",)),),
    )


def reviewed_credit(tmp_path: Path, *, physical=None, credit=0, lost=False) -> tuple[PfrGame, dict]:
    game = pfr_game()
    evidence = tmp_path / "official.txt"
    evidence.write_text("Synthetic primary evidence for credited rushing yards and recovery.")
    record = {
        "kind": "fumble", "game_id": game.game_id, "play_number": 7,
        "raw_game_sha256": hashlib.sha256(b"synthetic raw HTML").hexdigest(),
        "raw_play_sha256": play_fingerprint(game.plays[0]),
        "fumble_lost": lost, "out_of_bounds": False, "initial_gain": physical,
        "credited_kind": "rushing", "credited_yards": credit,
        "evidence": [{"file": evidence.name, "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                      "url": "https://example.org/official.txt", "pages": [1]}],
    }
    sidecar = tmp_path / "events.json"
    sidecar.write_text(json.dumps({"schema_version": 3, "events": [record]}))
    facts = load_event_reconciliations(sidecar).for_game(game, record["raw_game_sha256"])
    return game, facts


@pytest.mark.parametrize("physical,credit,basis,expected", [
    (None, 0, "credited_proxy", "F"),
    (None, -3, "credited_proxy", "F - 3"),
    (0, -3, "physical", "F"),
    (4, 0, "physical", "F + 4"),
])
def test_reviewed_pfr_credit_projects_without_qb_position_inference(
    tmp_path: Path, physical: int | None, credit: int, basis: str, expected: str,
) -> None:
    game, facts = reviewed_credit(tmp_path, physical=physical, credit=credit)
    before = play_fingerprint(game.plays[0])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert len(result.plays) == 1 and result.plays[0].result == expected
    assert result.plays[0].chart in {"line_plunge", "off_tackle", "end_run", "draw"}
    assert result.fumbles[0].unit == "rushing"
    gain = result.fumble_gain_projections[0]
    assert gain.modeled_gain_basis == basis
    assert gain.source_facts.physical_initial_yards == physical
    assert gain.source_facts.credited_yards == credit
    assert play_fingerprint(game.plays[0]) == before
    assert facts[7].to_dict()["credited_yards"] == credit


def test_reviewed_credit_is_bound_to_raw_event_bytes(tmp_path: Path) -> None:
    game, _facts = reviewed_credit(tmp_path)
    changed = replace(game, plays=(replace(game.plays[0], detail=game.plays[0].detail + "."),))
    sidecar = tmp_path / "events.json"
    with pytest.raises(ValueError, match="identity"):
        load_event_reconciliations(sidecar).for_game(changed, hashlib.sha256(b"synthetic raw HTML").hexdigest())


def test_default_nflverse_classification_is_a_passing_control() -> None:
    result = classify_nflverse_rows([nfl_row()])
    assert [play.result for play in result.plays] == ["F"]
    assert len(result.fumbles) == 1 and result.fumbles[0].lost is False


def test_default_pfr_unknown_gain_is_a_passing_control() -> None:
    result = classify_pfr_game(pfr_game())
    assert not result.plays
    assert len(result.fumbles) == 1 and result.fumbles[0].lost is False

@pytest.mark.parametrize("changes", [
    {"game_id": ""},
    {"fumble_recovery_1_team": "OWL", "fumble_lost": "0"},
    {"fumble_recovery_1_team": "FOX", "fumble_lost": "1"},
    {"pass_attempt": "1", "rush_attempt": "1"},
])
def test_proxy_rejects_contradictory_identity_credit_or_recovery(changes: dict) -> None:
    result = classify_nflverse_rows([nfl_row(**changes)], fumble_gain_policy=PROXY)
    assert any(item["field"] == "fumble_gain_projection" for item in result.unsupported_fields)
    assert not result.fumble_gain_projections


def test_structured_credit_class_controls_calibration_unit() -> None:
    row = nfl_row(play_type="pass", rush_attempt="1", pass_attempt="0")
    result = classify_nflverse_rows([row], fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert result.fumbles[0].unit == "rushing"
    assert result.fumble_gain_projections[0].source_facts.credited_kind == "rushing"


def test_pfr_proxy_requires_reviewed_credit_instead_of_interpreting_prose() -> None:
    game = pfr_game()
    play = replace(game.plays[0], detail="Pat Quarterback for no gain. Pat Quarterback fumbles, recovered by Pat Quarterback")
    result = classify_pfr_game(replace(game, plays=(play,)), fumble_gain_policy=PROXY)
    assert not result.plays and not result.fumble_gain_projections
    assert any(item["field"] == "fumble_gain_projection" for item in result.unsupported_fields)


@pytest.mark.parametrize("credit,kind", [(None, "rushing"), (True, "rushing"), (0, "QB"), (2, "sack")])
def test_reviewed_credit_fields_are_strictly_typed(tmp_path: Path, credit, kind: str) -> None:
    reviewed_credit(tmp_path)
    path = tmp_path / "events.json"
    data = json.loads(path.read_text())
    data["events"][0].update(credited_kind=kind, credited_yards=credit)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="credit"):
        load_event_reconciliations(path)


def test_renaming_team_does_not_change_projection_or_inferred_family() -> None:
    original = nfl_row(qb_scramble="1")
    renamed = {**original, "posteam": "NEW", "fumbled_1_team": "NEW", "defteam": "ALT"}
    left = classify_nflverse_rows([original], fumble_gain_policy=PROXY)
    right = classify_nflverse_rows([renamed], fumble_gain_policy=PROXY)
    assert [(p.chart, p.result) for p in left.plays] == [(p.chart, p.result) for p in right.plays]
    assert left.fumble_gain_projections[0].modeled_initial_yards == right.fumble_gain_projections[0].modeled_initial_yards


def test_proxy_unknown_recovery_remains_visible_in_source_census() -> None:
    result = classify_nflverse_rows([nfl_row(fumble_lost="")], fumble_gain_policy=PROXY)
    assert result.diagnostics["unknown_fumble_recoveries"] == 1
    assert result.fumbles[0].lost is None


def _reload_reviewed_fumble(
    tmp_path: Path, *, detail: str | None = None, **fields: object,
) -> tuple[PfrGame, dict]:
    game, _facts = reviewed_credit(tmp_path)
    if detail is not None:
        game = replace(game, plays=(replace(game.plays[0], detail=detail),))
    path = tmp_path / "events.json"
    data = json.loads(path.read_text())
    data["events"][0].update(raw_play_sha256=play_fingerprint(game.plays[0]), **fields)
    path.write_text(json.dumps(data))
    return game, load_event_reconciliations(path).for_game(
        game, data["events"][0]["raw_game_sha256"])


def test_reviewed_unknown_physical_gain_does_not_become_prose_yardage(tmp_path: Path) -> None:
    game, facts = _reload_reviewed_fumble(
        tmp_path, detail="Pat Quarterback for -3 yards. Pat Quarterback fumbles, recovered by Pat Quarterback",
        initial_gain=None, credited_yards=0)
    before = play_fingerprint(game.plays[0])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert facts[7].initial_gain_reviewed and facts[7].initial_gain is None
    assert facts[7].to_dict()["initial_gain"] is None
    assert [play.result for play in result.plays] == ["F"]
    projection = result.fumble_gain_projections[0]
    assert projection.modeled_gain_basis == "credited_proxy"
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.credited_yards == 0
    assert projection.modeled_initial_yards == 0
    assert play_fingerprint(game.plays[0]) == before


def test_known_physical_gain_still_rejects_conflicting_prose(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="conflict"):
        _reload_reviewed_fumble(
            tmp_path, detail="Pat Quarterback for -3 yards. Pat Quarterback fumbles, recovered by Pat Quarterback",
            initial_gain=-5, credited_yards=0)


@pytest.mark.parametrize("field", ["loose_ball_yards", "recovery_advance_yards"])
@pytest.mark.parametrize("value", [None, 0, -3, 4])
def test_reviewed_movement_is_retained_separately_from_proxy_gain(
    tmp_path: Path, field: str, value: int | None,
) -> None:
    game, facts = _reload_reviewed_fumble(tmp_path, **{field: value})
    assert facts[7].to_dict()[field] == value
    other = "recovery_advance_yards" if field == "loose_ball_yards" else "loose_ball_yards"
    assert other not in facts[7].to_dict()
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert [play.result for play in result.plays] == ["F"]
    projection = result.fumble_gain_projections[0]
    assert getattr(projection.source_facts, field) == value
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.credited_yards == projection.modeled_initial_yards == 0


@pytest.mark.parametrize("field", ["loose_ball_yards", "recovery_advance_yards"])
@pytest.mark.parametrize("value", [True, 1.5, "-3", []])
def test_reviewed_movement_requires_nullable_integer(
    tmp_path: Path, field: str, value: object,
) -> None:
    with pytest.raises(ValueError, match="movement"):
        _reload_reviewed_fumble(tmp_path, **{field: value})


def test_reviewed_zero_advance_is_retained_when_secondary_prose_reports_return(tmp_path: Path) -> None:
    game, facts = _reload_reviewed_fumble(
        tmp_path,
        detail="Pat Quarterback for 8 yards. Pat Quarterback fumbles, recovered by Pat Quarterback and returned for 8 yards",
        credited_yards=8, initial_gain=None, recovery_advance_yards=0)
    before = play_fingerprint(game.plays[0])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert [play.result for play in result.plays] == ["F + 8"]
    projection, = result.fumble_gain_projections
    assert projection.source_facts.recovery_advance_yards == 0
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.credited_yards == projection.modeled_initial_yards == 8
    assert play_fingerprint(game.plays[0]) == before

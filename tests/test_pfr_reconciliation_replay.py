"""Ordered review replay keeps factual schemas and rejects implicit overrides."""
import hashlib
import json
from pathlib import Path

import pytest

from paydirt.pfr_event_reconciliation import load_event_reconciliations
from tests.test_pfr_event_reconciliation import _fumble_sidecar, _game


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fact_sha(path: Path) -> str:
    fact, = load_event_reconciliations(path).facts
    return hashlib.sha256((json.dumps(fact.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()


def replay(tmp_path: Path, *, replacement: bool = False) -> tuple[Path, dict]:
    first, record = _fumble_sidecar(tmp_path, _game())
    first.rename(tmp_path / "recovery-v2.json")
    first = tmp_path / "recovery-v2.json"
    second = tmp_path / "class-v4.json"
    reviewed = {**record, "originating_kind": "rushing", "credited_kind": None,
                "credited_yards": None, "initial_gain": None}
    if not replacement:
        reviewed["play_number"] = 8
    second.write_text(json.dumps({"schema_version": 4, "events": [reviewed]}))
    data = {"schema_version": 1, "kind": "ordered_event_reconciliation_sources",
            "sources": [{"file": p.name, "sha256": sha(p)} for p in (first, second)],
            "replacements": []}
    if replacement:
        data["replacements"] = [{
            "game_id": record["game_id"], "play_number": record["play_number"],
            "previous_source_sha256": sha(first), "previous_fact_sha256": fact_sha(first),
            "replacement_source_sha256": sha(second), "replacement_fact_sha256": fact_sha(second),
            "reason": "Explicit synthetic class review supersedes recovery-only record",
        }]
    path = tmp_path / "ordered-reviews.json"
    path.write_text(json.dumps(data))
    return path, data


def test_heterogeneous_ordered_replay_preserves_schema2_nulls_and_schema4_class(tmp_path: Path) -> None:
    path, _ = replay(tmp_path)
    loaded = load_event_reconciliations(path)
    assert len(loaded.facts) == 2
    recovery, class_only = [fact.to_dict() for fact in loaded.facts]
    assert "credited_kind" not in recovery and "initial_gain" not in recovery
    assert class_only["credited_kind"] is None and class_only["credited_yards"] is None
    assert class_only["initial_gain"] is None and class_only["originating_kind"] == "rushing"
    assert path in loaded.input_paths
    assert loaded.source_schema_versions == (2, 4)


def test_exact_approved_replacement_uses_one_final_fact_and_binds_both_sources(tmp_path: Path) -> None:
    path, _ = replay(tmp_path, replacement=True)
    loaded = load_event_reconciliations(path)
    assert len(loaded.facts) == 1
    assert loaded.facts[0].to_dict()["originating_kind"] == "rushing"
    assert {p.name for p in loaded.input_paths} == {
        "ordered-reviews.json", "recovery-v2.json", "class-v4.json", "reviewed-gamebook.pdf"}


@pytest.mark.parametrize("damage", [
    "unapproved", "wrong_previous_source", "wrong_previous_fact", "wrong_replacement_source",
    "wrong_replacement_fact", "wrong_event", "unused", "reverse_order", "tampered_source",
    "missing_source", "duplicate_source", "external_source", "tampered_evidence", "nested_replay",
    "duplicate_json", "empty_sources", "boolean_version",
])
def test_replay_rejects_unbound_or_unused_authority(tmp_path: Path, damage: str) -> None:
    path, data = replay(tmp_path, replacement=True)
    relation = data["replacements"][0]
    if damage == "unapproved":
        data["replacements"] = []
    elif damage.startswith("wrong_") and damage != "wrong_event":
        field = damage.removeprefix("wrong_") + "_sha256"
        relation[field] = "0" * 64
    elif damage == "wrong_event":
        relation["play_number"] = 9
    elif damage == "unused":
        data["replacements"].append({**relation, "play_number": 9})
    elif damage == "reverse_order":
        data["sources"].reverse()
    elif damage == "tampered_source":
        (tmp_path / data["sources"][0]["file"]).write_text("{}")
    elif damage == "missing_source":
        (tmp_path / data["sources"][0]["file"]).unlink()
    elif damage == "duplicate_source":
        data["sources"].append(data["sources"][0])
    elif damage == "external_source":
        data["sources"][0]["file"] = "../outside.json"
    elif damage == "tampered_evidence":
        (tmp_path / "reviewed-gamebook.pdf").write_text("Changed")
    elif damage == "nested_replay":
        nested = tmp_path / "nested.json"
        nested.write_text(json.dumps(data))
        data["sources"][0] = {"file": nested.name, "sha256": sha(nested)}
    elif damage == "empty_sources":
        data["sources"] = []
    elif damage == "boolean_version":
        data["schema_version"] = True
    path.write_text(json.dumps(data))
    if damage == "duplicate_json":
        path.write_text(path.read_text().replace('"replacements":', '"schema_version": 1, "replacements":'))
    with pytest.raises((ValueError, OSError)):
        load_event_reconciliations(path)


@pytest.mark.parametrize("version", [2, 3, 4, 5])
def test_replay_keeps_each_existing_factual_schema_without_promotion(tmp_path: Path, version: int) -> None:
    path, record = _fumble_sidecar(tmp_path, _game())
    if version >= 3:
        record.update(credited_kind="rushing", credited_yards=-2)
    if version >= 4:
        record.update(originating_kind="rushing")
    if version >= 5:
        record.update(reported_primary_yards=-2, originating_player_id="passer", originating_team="FOX")
    path.write_text(json.dumps({"schema_version": version, "events": [record]}))
    expected, = load_event_reconciliations(path).facts
    collection = tmp_path / "replay.json"
    collection.write_text(json.dumps({"schema_version": 1, "kind": "ordered_event_reconciliation_sources",
        "sources": [{"file": path.name, "sha256": sha(path)}], "replacements": []}))
    actual = load_event_reconciliations(collection)
    assert actual.source_schema_versions == (version,)
    assert actual.facts[0].to_dict() == expected.to_dict()


def test_explicit_metadata_withdrawal_retains_recovery_without_inventing_a_gain(tmp_path: Path) -> None:
    path, data = replay(tmp_path, replacement=True)
    first = tmp_path / data["sources"][0]["file"]
    second = tmp_path / data["sources"][1]["file"]
    original = json.loads(first.read_text())
    original["events"][0]["initial_gain"] = -5
    first.write_text(json.dumps(original))
    withdrawn = json.loads(first.read_text())
    del withdrawn["events"][0]["initial_gain"]
    second.write_text(json.dumps(withdrawn))
    data["sources"] = [{"file": p.name, "sha256": sha(p)} for p in (first, second)]
    data["replacements"][0].update(previous_source_sha256=sha(first), previous_fact_sha256=fact_sha(first),
        replacement_source_sha256=sha(second), replacement_fact_sha256=fact_sha(second),
        reason="Explicit withdrawal of previously unreviewed movement metadata")
    path.write_text(json.dumps(data))
    fact, = load_event_reconciliations(path).facts
    assert "initial_gain" not in fact.to_dict()
    assert fact.to_dict()["fumble_lost"] is False


def test_approved_replacement_cannot_rebind_the_raw_event(tmp_path: Path) -> None:
    path, data = replay(tmp_path, replacement=True)
    second = tmp_path / data["sources"][1]["file"]
    changed = json.loads(second.read_text())
    changed["events"][0]["raw_play_sha256"] = "b" * 64
    second.write_text(json.dumps(changed))
    data["sources"][1]["sha256"] = sha(second)
    data["replacements"][0].update(replacement_source_sha256=sha(second), replacement_fact_sha256=fact_sha(second))
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="raw event identity"):
        load_event_reconciliations(path)

def test_single_schema2_sidecar_control_is_unchanged(tmp_path: Path) -> None:
    path, _ = _fumble_sidecar(tmp_path, _game())
    loaded = load_event_reconciliations(path)
    assert loaded.schema_version == 2 and len(loaded.facts) == 1
    assert {p.name for p in loaded.input_paths} == {"reconciliations.json", "reviewed-gamebook.pdf"}

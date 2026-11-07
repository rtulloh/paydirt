"""Replay existing factual schemas with explicit byte-bound replacement authority."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .pfr_event_reconciliation import EventFact, EventReconciliations, load_event_reconciliations


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fact_fingerprint(fact: EventFact) -> str:
    """Bind the complete typed fact, preserving absent and null quantities."""
    raw = json.dumps(fact.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(raw.encode()).hexdigest()


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


class ReconciliationReplay(EventReconciliations):
    """Ordered factual inventory; its replay version is distinct from fact schemas."""

    def __init__(self, facts: tuple[EventFact, ...], paths: tuple[Path, ...],
                 replay_path: Path, versions: tuple[int, ...]) -> None:
        super().__init__(facts, paths, max(versions))
        self.replay_path = replay_path
        self.source_schema_versions = versions


def load_reconciliation_replay(path: Path) -> ReconciliationReplay:
    """Reject implicit overrides, stale authority, nested inventories and unused approvals."""
    from .chart_release_gate import _strict_json_object

    path = Path(path).absolute()
    root = path.parent.resolve()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Replay must be a regular local file")
    data = _strict_json_object(path.read_bytes())
    if (set(data) != {"schema_version", "kind", "sources", "replacements"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["kind"] != "ordered_event_reconciliation_sources"
            or not isinstance(data["sources"], list) or not data["sources"]
            or not isinstance(data["replacements"], list)):
        raise ValueError("Requires a nonempty schema-1 ordered reconciliation replay")
    relation_fields = {"game_id", "play_number", "previous_source_sha256", "previous_fact_sha256",
                       "replacement_source_sha256", "replacement_fact_sha256", "reason"}
    approvals = {}
    for relation in data["replacements"]:
        if (not isinstance(relation, dict) or set(relation) != relation_fields
                or not isinstance(relation["game_id"], str) or not relation["game_id"]
                or type(relation["play_number"]) is not int or relation["play_number"] < 1
                or not isinstance(relation["reason"], str) or not relation["reason"].strip()
                or any(not _hash(relation[name]) for name in relation_fields if name.endswith("_sha256"))):
            raise ValueError("Invalid exact replacement authority")
        identity = tuple(relation[name] for name in sorted(relation_fields - {"reason"}))
        if identity in approvals:
            raise ValueError("Duplicate replacement authority")
        approvals[identity] = relation
    facts: dict[tuple[str, int], tuple[EventFact, str]] = {}
    paths = {path}
    seen_paths, seen_hashes, versions, consumed = set(), set(), [], set()
    for source in data["sources"]:
        if (not isinstance(source, dict) or set(source) != {"file", "sha256"}
                or not isinstance(source["file"], str) or not source["file"]
                or not _hash(source["sha256"])):
            raise ValueError("Invalid replay source binding")
        relative = Path(source["file"])
        if (relative.is_absolute() or ".." in relative.parts or "\\" in source["file"]
                or relative.as_posix() != source["file"] or source["file"] == "."):
            raise ValueError("Replay sources require canonical relative paths")
        source_path = root / relative
        if (source_path.is_symlink() or not source_path.is_file()
                or not source_path.resolve().is_relative_to(root)
                or any(parent.is_symlink() for parent in source_path.parents if parent != root)):
            raise ValueError("Missing or external replay source")
        if source_path in seen_paths or source["sha256"] in seen_hashes:
            raise ValueError("Duplicate replay source")
        seen_paths.add(source_path)
        seen_hashes.add(source["sha256"])
        if _sha(source_path) != source["sha256"]:
            raise ValueError("Replay source bytes differ from authority")
        factual = _strict_json_object(source_path.read_bytes())
        if set(factual) != {"schema_version", "events"}:
            raise ValueError("Replay sources must be factual sidecars, never nested replay inventories")
        inventory = load_event_reconciliations(source_path)
        versions.append(inventory.schema_version)
        for evidence in inventory.input_paths:
            if (evidence.is_symlink() or not evidence.is_file() or not evidence.resolve().is_relative_to(root)
                    or any(parent.is_symlink() for parent in evidence.parents if parent != root)):
                raise ValueError("Replay evidence must remain inside its source inventory")
            paths.add(evidence)
        for fact in inventory.facts:
            key = (fact.game_id, fact.play_number)
            if key in facts:
                previous, previous_source = facts[key]
                relation: dict[str, Any] = {
                    "game_id": fact.game_id, "play_number": fact.play_number,
                    "previous_source_sha256": previous_source, "previous_fact_sha256": fact_fingerprint(previous),
                    "replacement_source_sha256": source["sha256"], "replacement_fact_sha256": fact_fingerprint(fact),
                }
                identity = tuple(relation[name] for name in sorted(relation))
                if identity not in approvals or identity in consumed:
                    raise ValueError(f"Unapproved duplicate reconciliation: {key}")
                if (previous.raw_game_sha256, previous.raw_play_sha256) != (fact.raw_game_sha256, fact.raw_play_sha256):
                    raise ValueError("Replacement cannot change the raw event identity")
                consumed.add(identity)
            facts[key] = (fact, source["sha256"])
    if consumed != set(approvals):
        raise ValueError("Unused exact replacement authority")
    return ReconciliationReplay(tuple(fact for fact, _source in facts.values()),
                                tuple(sorted(paths)), path, tuple(versions))


def reconciliation_input_hashes(inventory: EventReconciliations) -> dict[str, str]:
    """Keep legacy labels; retain full relative paths for heterogeneous replay."""
    if isinstance(inventory, ReconciliationReplay):
        root = inventory.replay_path.parent
        return {"event_reconciliations/" + path.relative_to(root).as_posix(): _sha(path)
                for path in inventory.input_paths}
    from .generated_source_audit import generation_input_hashes

    return generation_input_hashes({"event_reconciliations": list(inventory.input_paths)})

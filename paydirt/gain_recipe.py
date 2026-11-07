"""Reproducible development training for source-driven gain normalization.

Training is rerun from the supplied sources on every generation. It establishes
a deterministic model allocation, never source truth or held-out acceptance.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .gain_normalization import GainBaseline, derive_gain_normalization

if TYPE_CHECKING:
    from .chart_generator import TeamSeasonStats

TRAINING_REPETITIONS = 16
TRAINING_SEED = 20261108
SOURCE_CONTRACT_FIELDS = {
    "season", "schedule", "targets", "teams", "games", "schema_version",
    "source_hashes", "attribution", "scope", "limitations",
}


def load_source_training_contract(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read source-only facts, rejecting missing fields and circular identities."""
    from .chart_release_gate import _strict_json_object

    content = Path(path).read_bytes()
    contract = _strict_json_object(content)
    if (not {"season", "schedule", "targets"} <= set(contract)
            or set(contract) - SOURCE_CONTRACT_FIELDS
            or not isinstance(contract.get("targets"), dict)):
        raise ValueError("Normalization requires source-only facts, without circular output identities")
    return contract, content


def _baseline_arguments(arguments: Sequence[str], destination: Path, audit: Path) -> list[str]:
    """Replace destinations and remove normalization to prevent recursive fitting."""
    removed = {"--output", "--audit-dir", "--gain-normalization-contract"}
    result: list[str] = []
    iterator = iter(arguments)
    for argument in iterator:
        if argument in removed:
            next(iterator)
        elif argument.split("=", 1)[0] not in removed:
            result.append(argument)
    return [*result, "--output", str(destination), "--audit-dir", str(audit)]


def prepare_gain_recipe(
    command: Callable[[Sequence[str]], int], arguments: Sequence[str], *,
    audit_dir: Path, contract_path: Path, stats: Mapping[str, TeamSeasonStats],
    workers: int = 4, source_games: int | None = None,
) -> dict[str, Any]:
    """Regenerate an unnormalized cohort, play fixed training and derive once.

    Args:
        command: Existing source generator, called with normalization removed.
        arguments: Original generator command arguments.
        audit_dir: Local evidence destination; existing training is preserved.
        contract_path: Source-only calendar/targets, without output identities.
        stats: Complete normalized official source totals, keyed by directory.
        workers: Parallel measurement workers; does not change seeded results.
        source_games: Source adapter's complete game count, when available.

    Returns:
        Hash-bound training evidence and the fixed complete-cohort derivation.

    Raises:
        ValueError: Source scope, training accounting or output identity is invalid.
    """
    from .chart_engine_audit import run_engine_audit, validate_engine_report
    from .chart_release_gate import _strict_json_object

    contract, contract_bytes = load_source_training_contract(contract_path)
    season = contract.get("season")
    schedule = contract.get("schedule")
    if (type(season) is not int or not stats
            or any(row.season != season or row.team_name != name for name, row in stats.items())
            or not isinstance(schedule, list) or not schedule):
        raise ValueError("Normalization requires complete same-season source scope")
    if any(not isinstance(pair, dict) or set(pair) != {"away", "home"}
           or any(not isinstance(name, str) or name not in stats for name in pair.values())
           or pair["away"] == pair["home"] for pair in schedule):
        raise ValueError("Source schedule contains an invalid fixture")
    if set(stats) != {name for pair in schedule for name in pair.values()}:
        raise ValueError("Normalization requires every source cohort member")
    if source_games is not None and len(schedule) != source_games:
        raise ValueError("Normalization schedule differs from the source game population")
    baseline_root = Path(audit_dir) / "gain-normalization-baseline"
    baseline = baseline_root / str(season)
    report_path = Path(audit_dir) / "gain-normalization-training.json"
    classified = Path(audit_dir) / "gain-normalization-classified"
    if any(path.exists() or path.is_symlink() for path in (baseline_root, classified, report_path)):
        raise ValueError("Preserve existing normalization training outputs; use a new audit directory")
    argv = _baseline_arguments(arguments, baseline, classified)
    if command(argv) != 0:
        raise ValueError("Unnormalized source generation failed")
    manifest_bytes = (baseline / "generation-manifest.json").read_bytes()
    manifest = _strict_json_object(manifest_bytes)
    if (manifest.get("season") != season or set(manifest.get("teams", {})) != set(stats)
            or manifest.get("gain_normalization")):
        raise ValueError("Training baseline must be the complete unnormalized source cohort")
    report = run_engine_audit(
        baseline, [(pair["away"], pair["home"]) for pair in schedule],
        repetitions=TRAINING_REPETITIONS, seed=TRAINING_SEED, policy="chart-focused",
        workers=workers, attempt_end_zone_interception_returns=True)
    validation = validate_engine_report(
        report, contract, baseline, minimum_team_games=1,
        minimum_repetitions=TRAINING_REPETITIONS, require_fit=False)
    if not validation["passed"]:
        raise ValueError("Invalid normalization training: " + "; ".join(validation["errors"]))
    metadata = report["metadata"]
    if metadata["repetitions"] != TRAINING_REPETITIONS or metadata["seed"] != TRAINING_SEED:
        raise ValueError("Normalization training must use the fixed development family")
    baselines: dict[str, dict[str, GainBaseline]] = {"passing": {}, "rushing": {}}
    for name, source in stats.items():
        if metadata["team_names"].get(name) != source.short_name:
            raise ValueError(f"Source and engine team identities differ: {name}")
        measured = report["teams"][source.short_name]
        for metric, attempts, yards in (("passing", "pass_attempts", "passing_yards"),
                                         ("rushing", "rushing_attempts", "rushing_yards")):
            official = getattr(source.offense, metric)
            baselines[metric][name] = GainBaseline(
                official.attempts, official.yards, measured[attempts], measured[yards], True)
    derivation = derive_gain_normalization(sorted(stats), baselines)
    if Path(contract_path).read_bytes() != contract_bytes:
        raise ValueError("Source contract changed during normalization training")
    if (baseline / "generation-manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("Source manifest changed during normalization training")
    report["validation"] = validation
    report["release_certified"] = False
    report_bytes = (json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("xb") as stream:
        stream.write(report_bytes)
    return {
        "schema_version": 1, "fit_accepted": False, "source_truth_verified": False,
        "derivation": derivation,
        "source_contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "baseline_input_hashes": manifest.get("input_hashes", {}),
        "training": {
            "repetitions": TRAINING_REPETITIONS, "seed": TRAINING_SEED,
            "games": report["league"]["games"], "policy": "chart-focused",
            "attempt_end_zone_interception_returns": True,
            "validation_passed": True,
            "chart_fingerprint": metadata["chart_fingerprint"],
            "engine_fingerprint": metadata["engine_fingerprint"],
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        },
    }

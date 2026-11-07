"""Typed source/flag bindings for the two existing chart generators."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .chart_release_gate import _strict_json_object
from .pfr_event_reconciliation import load_event_reconciliations
from .pfr_reconciliation_replay import reconciliation_input_hashes

MODERN_GROUPS = {"fumble_reviews", "fumble_review_evidence", "shared_exposures",
                 "shared_measurement", "projection_code"}


def normalization_source_binding(
    bundle: Path, groups: dict[str, list[str]], manifest: dict[str, Any],
    values: dict[str, str], contract: dict[str, Any],
) -> dict[str, str]:
    """Bind automatic training inputs; independent regeneration verifies results."""
    from .gain_recipe import TRAINING_REPETITIONS, TRAINING_SEED, load_source_training_contract

    names = groups.get("normalization_contract", [])
    model = manifest.get("gain_normalization")
    if not names:
        if model is not None or "--gain-normalization-contract" in values:
            raise ValueError("Normalization model requires its bound normalization source contract")
        return {}
    if len(names) != 1 or not isinstance(model, dict):
        raise ValueError("Requires one normalization source contract and normalization model")
    path = bundle / names[0]
    source, source_bytes = load_source_training_contract(path)
    if model.get("source_contract_sha256") != hashlib.sha256(source_bytes).hexdigest():
        raise ValueError("Candidate differs from normalization source contract bytes")
    if any(source[name] != contract.get(name) for name in
           ("season", "schedule", "targets", "teams", "games") if name in source):
        raise ValueError("Candidate normalization source facts differ from release source facts")
    training = model.get("training", {})
    derivation = model.get("derivation", {})
    if (not isinstance(training, dict) or not isinstance(derivation, dict)
            or type(model.get("schema_version")) is not int or model["schema_version"] != 1
            or model.get("fit_accepted") is not False
            or model.get("source_truth_verified") is not False
            or derivation.get("cohort") != sorted(contract["teams"])
            or training.get("repetitions") != TRAINING_REPETITIONS
            or training.get("seed") != TRAINING_SEED
            or training.get("policy") != "chart-focused"
            or training.get("attempt_end_zone_interception_returns") is not True
            or training.get("validation_passed") is not True):
        raise ValueError("Candidate differs from fixed normalization training procedure")
    return {"--gain-normalization-contract": names[0]}


def pfr_reconciliation_binding(bundle: Path, names: list[str], selected: str | None) -> str:
    """Require the complete factual/evidence closure of one selected sidecar or replay."""
    if selected not in names or not selected or not selected.endswith(".json"):
        raise ValueError("Requires one selected reviewed sidecar or ordered replay")
    loaded = load_event_reconciliations(bundle / selected)
    expected = {"inputs/" + name for name in reconciliation_input_hashes(loaded)}
    if set(names) != expected:
        raise ValueError("Reconciliation inputs differ from the exact reviewed source/evidence inventory")
    return selected


def modern_source_bindings(bundle: Path, project: Path, groups: dict[str, list[str]],
                           manifest: dict[str, Any], values: dict[str, str],
                           policy: str | None) -> dict[str, str]:
    """Use existing typed validators; hashes do not establish source completeness or fit."""
    import generate_nflverse_charts as generator

    model = manifest.get("ordered_fumble_projection", {})
    if not isinstance(model, dict):
        raise TypeError("Generation manifest requires an ordered projection object")
    mode = model.get("mode")
    supplied = set(groups) & MODERN_GROUPS
    if mode is None:
        if supplied or any(flag in values for flag in (
                "--fumble-projection-mode", "--fumble-loss-reviews", "--shared-return-exposures",
                "--fumble-range-policy")) or model.get("range_policy") is not None:
            raise ValueError("Review/exposure/code inputs and range policy require an explicit ordered projection mode")
        return {}
    if (mode != "ordered_ledger_v1" or policy != "source_reported_gain_proxy_v1"
            or model.get("fit_accepted") is not False):
        raise ValueError("Requires the existing unaccepted ordered-ledger diagnostic mode and gain policy")
    required = {"shared_exposures", "shared_measurement", "projection_code"}
    if not required <= supplied:
        raise ValueError("Ordered generation requires measured shared exposure and exact projection code inputs")
    range_policy = model.get("range_policy", "measured_diagnostic_v1")
    if (range_policy not in ("measured_diagnostic_v1", "source_primary_v1")
            or values.get("--fumble-range-policy", "measured_diagnostic_v1") != range_policy):
        raise ValueError("Generation range policy differs from the declared ordered candidate")
    expected = {"--fumble-projection-mode": mode}
    if "--fumble-range-policy" in values:
        expected["--fumble-range-policy"] = range_policy
    for group, flag in (("shared_exposures", "--shared-return-exposures"),
                        ("fumble_reviews", "--fumble-loss-reviews")):
        if group in groups:
            if len(groups[group]) != 1:
                raise ValueError(f"Requires one typed {group} input")
            expected[flag] = groups[group][0]
    if any(values.get(flag) != value for flag, value in expected.items()):
        raise ValueError("Ordered generation arguments differ from typed source bindings")
    code_paths = [project / "generate_nflverse_charts.py", *(project / "paydirt" / name for name in (
        "nflverse_play_by_play.py", "nflverse_fumble_ledger.py", "chart_generator.py", "fumble_source.py"))]
    actual_code = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in code_paths}
    bound_code = {Path(name).name: hashlib.sha256((bundle / name).read_bytes()).hexdigest()
                  for name in groups["projection_code"]}
    if actual_code != bound_code:
        raise ValueError("Projection code inventory/bytes differ from the current generator implementation")
    reviews, evidence = generator._load_fumble_reviews(
        bundle / groups["fumble_reviews"][0] if "fumble_reviews" in groups else None)
    if "fumble_reviews" in groups and not reviews:
        raise ValueError("A supplied fumble review inventory must be nonempty")
    _require_paths(bundle, groups.get("fumble_review_evidence", []), evidence, "fumble review evidence")
    mapping = _strict_json_object((bundle / groups["team_map"][0]).read_bytes())
    if (not mapping or any(not isinstance(key, str) or key != key.upper()
                           or not isinstance(value, str) for key, value in mapping.items())
            or set(mapping.values()) != set(manifest.get("teams", mapping.values()))):
        raise ValueError("Modern team map differs from the generation team scope")
    source = bundle / groups["play_by_play"][0]
    classified = generator.load_nflverse_play_by_play(
        source, seed=int(values["--seed"]), fumble_gain_policy=policy,
        fumble_projection_mode=mode, fumble_loss_reviews=reviews)
    if classified.unsupported_fields:
        raise ValueError(f"Unsupported typed source fields: {len(classified.unsupported_fields)}")
    if type(manifest.get("games")) is not int or manifest["games"] != classified.games:
        raise ValueError("Modern source game population differs from candidate")
    exposure = bundle / groups["shared_exposures"][0]
    _counts, measurements = generator._load_shared_exposures(
        exposure, source, set(mapping), expected_games=classified.games)
    generator._load_shared_ranges(exposure, set(mapping))
    _require_paths(bundle, groups["shared_measurement"], measurements, "shared exposure measurement")
    return expected


def _require_paths(bundle: Path, supplied: list[str], referenced: list[Path], label: str) -> None:
    expected = {bundle / name for name in supplied}
    if (expected != set(referenced) or any(path.is_symlink() or not path.is_file()
                                        or not path.resolve().is_relative_to(bundle) for path in referenced)):
        raise ValueError(f"Typed {label} differs from its exact bound input group")

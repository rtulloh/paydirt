"""Portable recipes must bind the versioned assumption contract without truth claims."""
import json
from pathlib import Path

import pytest

from paydirt.historical_fumble_proxy import POLICY, POLICY_V2, policy_metadata
from tests.test_chart_source_bundle import bundle_files, digest, inventory, prepare


@pytest.mark.parametrize("policy", [POLICY, POLICY_V2])
@pytest.mark.parametrize("damage", [None, "missing_contract", "version", "boolean_version", "truth", "counts", "class_total", "old_policy"])
def test_portable_assumption_contract_matches_manifest_and_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None, policy: str,
) -> None:
    files = bundle_files.__wrapped__(tmp_path)
    bundle, candidate, *_ = files
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    diagnostics = {"modeled_fumble_classes": 2, "modeled_fumble_class_assumed_qb_snap": 2}
    model = policy_metadata(policy, diagnostics)["modeled_fumble_assumptions"]
    manifest.update(fumble_gain_policy=policy, modeled_fumble_assumptions=model, diagnostics=diagnostics)
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract["modeled_fumble_assumptions"] = dict(model)
    if damage == "missing_contract":
        contract.pop("modeled_fumble_assumptions")
    elif damage == "version":
        manifest["modeled_fumble_assumptions"]["contract_version"] = 99
        contract["modeled_fumble_assumptions"]["contract_version"] = 99
    elif damage == "truth":
        manifest["modeled_fumble_assumptions"]["source_class_truth_verified"] = True
        contract["modeled_fumble_assumptions"]["source_class_truth_verified"] = True
    elif damage == "boolean_version":
        manifest["modeled_fumble_assumptions"]["contract_version"] = True
        contract["modeled_fumble_assumptions"]["contract_version"] = True
    elif damage == "counts":
        manifest["diagnostics"]["modeled_fumble_classes"] = 3
    elif damage == "class_total":
        manifest["diagnostics"]["modeled_fumble_classes"] = 3
        model = policy_metadata(policy, manifest["diagnostics"])["modeled_fumble_assumptions"]
        manifest["modeled_fumble_assumptions"] = model
        contract["modeled_fumble_assumptions"] = model
    elif damage == "old_policy":
        manifest["fumble_gain_policy"] = "source_reported_gain_proxy_v1"
    manifest_path.write_text(json.dumps(manifest))
    contract["generation_manifest_sha256"] = digest(manifest_path)
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["generator_script"] = "generate_pfr_charts.py"
    args = recipe["arguments"]
    index = args.index("--pbp")
    args[index:index + 2] = ["--html-dir", "inputs/play_by_play"]
    args += ["--fumble-gain-policy", manifest["fumble_gain_policy"]]
    recipe_path.write_text(json.dumps(recipe))
    inventory(bundle)
    result = prepare(files, monkeypatch)
    assert result["passed"] is (damage is None), result["errors"]
    if damage is not None:
        assert not files[-1]
    assert result["release_certified"] is False


@pytest.mark.parametrize("damage", [None, "missing_contract", "truth", "count", "wrong_policy"])
def test_portable_fitting_exclusion_binding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None) -> None:
    from paydirt.historical_fumble_proxy import FITTING_POLICY, fitting_metadata
    from paydirt.pfr_play_by_play import FumbleEvent

    files = bundle_files.__wrapped__(tmp_path)
    bundle, candidate, *_ = files
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    diagnostics = {"modeled_fumble_classes": 1, "modeled_fumble_class_assumed_qb_snap": 1}
    model = policy_metadata(POLICY_V2, diagnostics)["modeled_fumble_assumptions"]
    event = FumbleEvent("FOX", "rushing", False, "synthetic-2026", 7)
    record = {"event_id": "synthetic-2026:7", "team": "FOX", "unit": "rushing", "lost": False,
              "mechanism": "fumble_gain_projection", "reason": "missing primary gain",
              "raw_game_sha256": "a" * 64, "raw_play_sha256": "b" * 64, "scope": "fitting_only"}
    disclosure = fitting_metadata(FITTING_POLICY, [event], [], [record])
    manifest.update(fumble_gain_policy=POLICY_V2, modeled_fumble_assumptions=model,
                    diagnostics=diagnostics, fumble_fitting_policy=disclosure)
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract.update(modeled_fumble_assumptions=model, fumble_fitting_policy=disclosure)
    if damage == "missing_contract":
        contract.pop("fumble_fitting_policy")
    elif damage == "truth":
        disclosure["historical_source_complete"] = True
    elif damage == "count":
        disclosure["excluded_events"] = 0
    elif damage == "wrong_policy":
        disclosure["policy"] = "unknown"
    manifest_path.write_text(json.dumps(manifest))
    contract["generation_manifest_sha256"] = digest(manifest_path)
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["generator_script"] = "generate_pfr_charts.py"
    args = recipe["arguments"]
    index = args.index("--pbp")
    args[index:index + 2] = ["--html-dir", "inputs/play_by_play"]
    args += ["--fumble-gain-policy", POLICY_V2, "--fumble-exclusion-policy", FITTING_POLICY]
    recipe_path.write_text(json.dumps(recipe))
    inventory(bundle)
    result = prepare(files, monkeypatch)
    assert result["passed"] is (damage is None), result["errors"]

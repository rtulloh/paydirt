"""Portable recipes bind source-only training facts and the fixed procedure."""
import json

import pytest

from tests.test_chart_source_bundle import BundleFiles, bundle_files, digest, inventory, prepare


def add_normalization(files: BundleFiles) -> None:
    bundle, candidate, _output, _project, _calls = files
    source = bundle / "inputs/normalization_contract/source.json"
    source.parent.mkdir()
    source.write_text(json.dumps({"season": 2026, "schedule": [], "targets": {}}))
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["input_hashes"]["normalization_contract/source.json"] = digest(source)
    manifest["gain_normalization"] = {
        "schema_version": 1, "fit_accepted": False, "source_truth_verified": False,
        "source_contract_sha256": digest(source),
        "derivation": {"cohort": ["A"]},
        "training": {"repetitions": 16, "seed": 20261108, "policy": "chart-focused",
                     "attempt_end_zone_interception_returns": True, "validation_passed": True},
    }
    manifest_path.write_text(json.dumps(manifest))
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract.update(targets={}, input_hashes=manifest["input_hashes"],
                    generation_manifest_sha256=digest(manifest_path))
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["arguments"] += ["--gain-normalization-contract", "inputs/normalization_contract/source.json"]
    recipe["expected_input_hashes"] = manifest["input_hashes"]
    recipe_path.write_text(json.dumps(recipe))
    inventory(bundle)


def test_portable_normalization_preserves_bound_training_contract(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch,  # noqa: F811 - imported fixture
) -> None:
    add_normalization(bundle_files)
    result = prepare(bundle_files, monkeypatch)
    assert result["passed"], result["errors"]
    assert "normalization_contract/source.json" in result["source_paths"]["input_files"]
    command = bundle_files[-1][0][0]
    assert command[command.index("--gain-normalization-contract") + 1] == (
        "inputs/normalization_contract/source.json")


@pytest.mark.parametrize("mutation,expected", [
    ("hash", "normalization source contract"),
    ("facts", "normalization source facts"),
    ("repetitions", "fixed normalization training"),
    ("missing_model", "normalization model"),
])
def test_normalization_binding_rejects_inconsistent_receipts(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mutation: str, expected: str,  # noqa: F811
) -> None:
    add_normalization(bundle_files)
    bundle, candidate, _output, _project, calls = bundle_files
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if mutation == "hash":
        manifest["gain_normalization"]["source_contract_sha256"] = "0" * 64
    elif mutation == "facts":
        path = bundle / "inputs/normalization_contract/source.json"
        path.write_text(json.dumps({"season": 2025, "schedule": [], "targets": {}}))
        manifest["input_hashes"]["normalization_contract/source.json"] = digest(path)
        manifest["gain_normalization"]["source_contract_sha256"] = digest(path)
    elif mutation == "repetitions":
        manifest["gain_normalization"]["training"]["repetitions"] = 64
    else:
        del manifest["gain_normalization"]
    manifest_path.write_text(json.dumps(manifest))
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract.update(input_hashes=manifest["input_hashes"],
                    generation_manifest_sha256=digest(manifest_path))
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["expected_input_hashes"] = manifest["input_hashes"]
    recipe_path.write_text(json.dumps(recipe))
    inventory(bundle)
    result = prepare(bundle_files, monkeypatch)
    assert not result["passed"]
    assert expected in "; ".join(result["errors"])
    assert not calls

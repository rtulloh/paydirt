"""Local source preparation binds bytes before running either existing generator."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

BundleFiles = tuple[Path, Path, Path, Path, list]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(bundle: Path) -> None:
    files = {path.relative_to(bundle).as_posix(): digest(path) for path in bundle.rglob("*")
             if path.is_file() and path.name != "inventory.json"}
    (bundle / "inventory.json").write_text(json.dumps({"schema_version": 1, "files": files}))


@pytest.fixture
def bundle_files(tmp_path: Path) -> BundleFiles:
    bundle, candidate, output, project = (tmp_path / name for name in ("bundle", "2026-candidate", "2026-reproduced", "project"))
    project.mkdir()
    (project / "paydirt").mkdir()
    (project / "paydirt/source_adapter.py").write_text("# Synthetic public source adapter\n")
    for script in ("generate_nflverse_charts.py", "generate_pfr_charts.py"):
        (project / script).write_text("# Synthetic generator identity\n")
    sources = {
        "normalized_stats/A.json": '{"season":2026,"team_name":"A"}',
        "play_by_play/source.csv": "Synthetic public play-by-play\n",
        "team_map/map.json": '{"AAA":"A"}',
    }
    for name, data in sources.items():
        path = bundle / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    template = bundle / "template/2026/2026.yaml"
    template.parent.mkdir(parents=True)
    template.write_text("season: 2026\n")
    candidate.mkdir()
    (candidate / "2026.yaml").write_bytes(template.read_bytes())
    (candidate / "A").mkdir()
    for name in ("offense", "defense", "special"):
        (candidate / "A" / (name + ".csv")).write_text("Synthetic public chart " + name + "\n")
    input_hashes = {name: digest(bundle / "inputs" / name) for name in sources}
    chart_hashes = {path.relative_to(candidate).as_posix(): digest(path) for path in candidate.glob("*/*.csv")}
    manifest = {"season": 2026, "input_hashes": input_hashes, "seed": 8306,
                "calibration_profile": {}, "opponent_adjustment": {"shrinkage": 24.0}}
    (candidate / "generation-manifest.json").write_text(json.dumps(manifest))
    (bundle / "contract.json").write_text(json.dumps({
        "season": 2026, "teams": {"A": {}}, "schedule": [], "input_hashes": input_hashes,
        "chart_hashes": chart_hashes, "generation_profile": {},
        "generation_manifest_sha256": digest(candidate / "generation-manifest.json"),
    }))
    (bundle / "recipe.json").write_text(json.dumps({
        "schema_version": 1, "generator_script": "generate_nflverse_charts.py",
        "arguments": ["--stats-dir", "inputs/normalized_stats", "--template-season", "template/2026",
                      "--team-map", "inputs/team_map/map.json", "--seed", "8306",
                      "--opponent-shrinkage", "24.0", "--output", "{output}",
                      "--audit-dir", "{audit}", "--pbp", "inputs/play_by_play/source.csv"],
        "expected_input_hashes": input_hashes, "expected_csv_hashes": chart_hashes,
        "scope": "Synthetic public byte-binding fixture; no source-fidelity claim",
    }))
    inventory(bundle)
    return bundle, candidate, output, project, []


def prepare(files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mode: str = "normal") -> dict:
    assert importlib.util.find_spec("paydirt.chart_source_bundle") is not None, "Maintained source-bundle preparation is required"
    module = importlib.import_module("paydirt.chart_source_bundle")
    bundle, candidate, output, project, calls = files
    monkeypatch.setattr(module, "PROJECT_ROOT", project)
    def run(command: list[str], **options: object) -> subprocess.CompletedProcess:
        calls.append((command, options))
        stream = options["stdout"]
        stream.write("Synthetic generator execution\n")
        if mode == "failed": return subprocess.CompletedProcess(command, 2)
        generated = Path(command[command.index("--output") + 1])
        shutil.copytree(candidate, generated)
        if mode == "wrong-csv": (generated / "A/offense.csv").write_text("Wrong\n")
        elif mode == "wrong-manifest": (generated / "generation-manifest.json").write_text("{}")
        elif mode == "wrong-rules": (generated / "2026.yaml").write_text("season: 1\n")
        elif mode == "changed-source": (bundle / "inputs/play_by_play/source.csv").write_text("Changed\n")
        elif mode == "changed-candidate": (candidate / "A/offense.csv").write_text("Changed\n")
        elif mode == "changed-script": (project / "generate_nflverse_charts.py").write_text("Changed\n")
        elif mode == "changed-adapter": (project / "paydirt/source_adapter.py").write_text("Changed\n")
        elif mode == "added-adapter": (project / "paydirt/new_source_adapter.py").write_text("Added\n")
        elif mode == "removed-log": output.with_suffix(".log").unlink()
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(module.subprocess, "run", run)
    return module.prepare_chart_sources(bundle, candidate, output)


def test_source_preparation_runs_bound_recipe_and_returns_actual_paths(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle, _candidate, output, project, calls = bundle_files
    result = prepare(bundle_files, monkeypatch)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert result["execution"]["exit_code"] == 0
    assert result["source_paths"]["stats_dir"] == str(bundle / "inputs/normalized_stats")
    assert result["source_paths"]["reproduced_dir"] == str(output)
    assert set(result["source_paths"]["input_files"]) == {"normalized_stats/A.json", "play_by_play/source.csv", "team_map/map.json"}
    assert len(calls) == 1
    assert calls[0][0][1] == str(project / "generate_nflverse_charts.py")
    assert calls[0][1]["cwd"] == bundle
    assert "{output}" not in calls[0][0] and "{audit}" not in calls[0][0]


@pytest.mark.parametrize("mutation", [
    "missing-file", "changed-file", "extra-file", "bad-hash", "missing-inventory", "wrong-inventory-version",
    "duplicate-json", "nonfinite-json", "overflow-json", "wrong-script", "unknown-flag", "duplicate-flag",
    "output-override", "audit-override", "absolute-input", "traversing-input", "wrong-source-label",
    "changed-candidate", "changed-contract", "substituted-manifest", "omitted-source", "wrong-profile",
    "existing-output", "existing-log", "output-in-bundle", "output-in-candidate",
    "symlink-input", "missing-required-flag", "wrong-seed", "wrong-shrinkage", "invalid-number",
])
def test_invalid_source_bundle_fails_before_generator_execution(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    bundle, candidate, output, project, calls = bundle_files
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    rebind = False
    if mutation == "missing-file": (bundle / "inputs/play_by_play/source.csv").unlink()
    elif mutation == "changed-file": (bundle / "inputs/play_by_play/source.csv").write_text("Changed\n")
    elif mutation == "extra-file": (bundle / "extra.txt").write_text("Unexpected\n")
    elif mutation == "bad-hash":
        path = bundle / "inventory.json"; data = json.loads(path.read_text())
        data["files"]["recipe.json"] = "0" * 64; path.write_text(json.dumps(data))
    elif mutation == "missing-inventory": (bundle / "inventory.json").unlink()
    elif mutation == "wrong-inventory-version":
        path = bundle / "inventory.json"; data = json.loads(path.read_text())
        data["schema_version"] = True; path.write_text(json.dumps(data))
    elif mutation in {"duplicate-json", "nonfinite-json", "overflow-json"}:
        path = bundle / "inputs/normalized_stats/A.json"
        path.write_text({"duplicate-json": '{"a":1,"a":2}', "nonfinite-json": '{"a":NaN}', "overflow-json": '{"a":1e999}'}[mutation])
        # Keep all byte bindings consistent, isolating strict JSON validation.
        sha = digest(path)
        recipe["expected_input_hashes"]["normalized_stats/A.json"] = sha
        manifest_path = candidate / "generation-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["input_hashes"]["normalized_stats/A.json"] = sha
        manifest_path.write_text(json.dumps(manifest))
        contract_path = bundle / "contract.json"
        contract = json.loads(contract_path.read_text())
        contract["input_hashes"]["normalized_stats/A.json"] = sha
        contract["generation_manifest_sha256"] = digest(manifest_path)
        contract_path.write_text(json.dumps(contract))
        recipe_path.write_text(json.dumps(recipe))
        rebind = True
    elif mutation == "wrong-script": recipe["generator_script"] = "arbitrary.py"; rebind = True
    elif mutation == "unknown-flag": recipe["arguments"] += ["--unreviewed", "yes"]; rebind = True
    elif mutation == "duplicate-flag": recipe["arguments"] += ["--seed", "8306"]; rebind = True
    elif mutation == "output-override": recipe["arguments"][recipe["arguments"].index("{output}")] = str(candidate); rebind = True
    elif mutation == "audit-override": recipe["arguments"][recipe["arguments"].index("{audit}")] = str(bundle); rebind = True
    elif mutation == "absolute-input": recipe["arguments"][recipe["arguments"].index("inputs/play_by_play/source.csv")] = str(bundle / "inputs/play_by_play/source.csv"); rebind = True
    elif mutation == "traversing-input": recipe["arguments"][recipe["arguments"].index("inputs/play_by_play/source.csv")] = "../bundle/inputs/play_by_play/source.csv"; rebind = True
    elif mutation == "wrong-source-label": recipe["expected_input_hashes"]["wrong/source.csv"] = "0" * 64; rebind = True
    elif mutation == "changed-candidate": (candidate / "A/offense.csv").write_text("Changed\n")
    elif mutation == "changed-contract":
        path = bundle / "contract.json"; data = json.loads(path.read_text()); data["chart_hashes"] = {}
        path.write_text(json.dumps(data)); rebind = True
    elif mutation == "substituted-manifest":
        path = candidate / "generation-manifest.json"; data = json.loads(path.read_text()); data["season"] = 2025
        path.write_text(json.dumps(data))
        path = bundle / "contract.json"; data = json.loads(path.read_text())
        data["generation_manifest_sha256"] = digest(candidate / "generation-manifest.json")
        path.write_text(json.dumps(data)); rebind = True
    elif mutation == "omitted-source": recipe["expected_input_hashes"].pop("play_by_play/source.csv"); rebind = True
    elif mutation == "wrong-profile":
        path = bundle / "contract.json"; data = json.loads(path.read_text()); data["generation_profile"] = {"pass_yard_multiplier": 100}
        path.write_text(json.dumps(data)); rebind = True
    elif mutation == "existing-output": output.mkdir(); (output / "keep.txt").write_text("Preserve\n")
    elif mutation == "existing-log": output.with_suffix(".log").write_text("Preserve\n")
    elif mutation == "output-in-bundle": output = bundle / "2026-reproduced"
    elif mutation == "output-in-candidate": output = candidate / "2026-reproduced"
    elif mutation == "symlink-input":
        path = bundle / "inputs/play_by_play/source.csv"
        external = bundle.parent / "synthetic-external.csv"
        path.rename(external); path.symlink_to(external)
    elif mutation == "missing-required-flag":
        index = recipe["arguments"].index("--pbp"); del recipe["arguments"][index:index+2]; rebind = True
    elif mutation == "wrong-seed": recipe["arguments"][recipe["arguments"].index("--seed")+1] = "999"; rebind = True
    elif mutation == "wrong-shrinkage": recipe["arguments"][recipe["arguments"].index("--opponent-shrinkage")+1] = "999"; rebind = True
    elif mutation == "invalid-number": recipe["arguments"][recipe["arguments"].index("--seed")+1] = "NaN"; rebind = True
    if rebind:
        if mutation not in {"duplicate-json", "nonfinite-json", "overflow-json", "changed-contract", "wrong-profile"}:
            recipe_path.write_text(json.dumps(recipe))
        inventory(bundle)
    before = {path: path.read_bytes() for directory in (bundle, candidate) for path in directory.rglob("*") if path.is_file()}
    result = prepare((bundle, candidate, output, project, calls), monkeypatch)
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False
    assert not calls
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize("mode", ["failed", "wrong-csv", "wrong-manifest", "wrong-rules",
                                  "changed-source", "changed-candidate", "changed-script", "removed-log",
                                  "changed-adapter", "added-adapter"])
def test_executed_producer_cannot_hide_failed_or_changed_evidence(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    result = prepare(bundle_files, monkeypatch, mode)
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False
    if mode == "removed-log":
        assert result["execution"]["log_sha256"] is None
    else:
        assert result["execution"]["log_sha256"]


def cli_module(files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mode: str = "normal") -> object:
    assert importlib.util.find_spec("scripts.prepare_chart_sources") is not None, "Source preparation needs a maintained CLI"
    cli = importlib.import_module("scripts.prepare_chart_sources")
    def invoke(bundle: Path, candidate: Path, output: Path) -> dict:
        assert (bundle, candidate, output) == files[:3]
        return prepare(files, monkeypatch, mode)
    monkeypatch.setattr(cli, "prepare_chart_sources", invoke)
    return cli


@pytest.mark.parametrize("mode", ["normal", "failed"])
def test_preparation_cli_retains_receipt_and_emits_gate_inputs_only_on_success(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    bundle, candidate, output, _project, _calls = bundle_files
    cli = cli_module(bundle_files, monkeypatch, mode)
    receipt = bundle.parent / "preparation.json"
    assert cli.main(["--bundle", str(bundle), "--candidate-dir", str(candidate),
                     "--reproduced-dir", str(output), "--output", str(receipt)]) == (0 if mode == "normal" else 1)
    result = json.loads(receipt.read_text())
    assert result["passed"] is (mode == "normal")
    assert result["release_certified"] is False
    input_inventory = receipt.with_name("preparation-inputs.json")
    if mode == "normal":
        assert json.loads(input_inventory.read_text()) == result["source_paths"]["input_files"]
    else:
        assert not input_inventory.exists()


@pytest.mark.parametrize("target", ["receipt", "input-inventory", "bundle-input", "candidate-chart",
                                  "generator-log", "inside-output"])
def test_preparation_cli_preserves_all_existing_evidence_and_producer_destinations(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:
    bundle, candidate, output, _project, calls = bundle_files
    cli = cli_module(bundle_files, monkeypatch)
    receipt = bundle.parent / "preparation.json"
    if target == "receipt": receipt.write_text("Preserve receipt\n")
    elif target == "input-inventory": receipt.with_name("preparation-inputs.json").write_text("Preserve inputs\n")
    elif target == "bundle-input": receipt = bundle / "inventory.json"
    elif target == "candidate-chart": receipt = candidate / "A/offense.csv"
    elif target == "generator-log": receipt = output.with_suffix(".log")
    elif target == "inside-output": receipt = output / "receipt.json"
    before = {path: path.read_bytes() for path in bundle.parent.rglob("*") if path.is_file()}
    assert cli.main(["--bundle", str(bundle), "--candidate-dir", str(candidate),
                     "--reproduced-dir", str(output), "--output", str(receipt)]) == 1
    assert not calls
    assert all(path.read_bytes() == data for path, data in before.items())


def prepared_receipt(files: BundleFiles, monkeypatch: pytest.MonkeyPatch) -> tuple[object, Path]:
    cli = cli_module(files, monkeypatch)
    bundle, candidate, output, project, _calls = files
    receipt = project / ".ai-audits/chart-sources/2026/source.json"
    assert cli.main(["--bundle", str(bundle), "--candidate-dir", str(candidate),
                     "--reproduced-dir", str(output), "--output", str(receipt)]) == 0
    return importlib.import_module("paydirt.chart_source_bundle"), receipt


def test_prepared_receipt_returns_reverified_actual_gate_paths(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, receipt = prepared_receipt(bundle_files, monkeypatch)
    assert hasattr(module, "prepared_source_options"), "Prepared receipts must be independently revalidated"
    bundle, candidate, output, _project, _calls = bundle_files
    options = module.prepared_source_options(receipt, candidate, bundle / "contract.json")
    assert options == {"input_files": {name: Path(path) for name, path in
                                      json.loads(receipt.read_text())["source_paths"]["input_files"].items()},
                       "stats_dir": bundle / "inputs/normalized_stats", "reproduced_dir": output}


@pytest.mark.parametrize("mutation", [
    "failed", "contradictory-errors", "certified", "changed-log", "changed-source", "changed-candidate",
    "changed-reproduction", "changed-code", "added-code", "changed-inventory", "changed-contract",
    "changed-runtime", "substitute-inputs", "substitute-stats", "missing-binding", "duplicate-json",
    "bad-exit", "substitute-command", "substitute-cwd",
])
def test_prepared_receipt_cannot_reuse_failed_stale_or_substituted_evidence(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    module, receipt = prepared_receipt(bundle_files, monkeypatch)
    assert hasattr(module, "prepared_source_options"), "Prepared receipts must be independently revalidated"
    bundle, candidate, output, project, _calls = bundle_files
    data = json.loads(receipt.read_text())
    if mutation == "failed": data["passed"] = False
    elif mutation == "contradictory-errors": data["errors"] = ["Unresolved"]
    elif mutation == "certified": data["release_certified"] = True
    elif mutation == "changed-log": Path(data["execution"]["log_path"]).write_text("Changed\n")
    elif mutation == "changed-source": (bundle / "inputs/play_by_play/source.csv").write_text("Changed\n")
    elif mutation == "changed-candidate": (candidate / "A/offense.csv").write_text("Changed\n")
    elif mutation == "changed-reproduction": (output / "A/offense.csv").write_text("Changed\n")
    elif mutation == "changed-code": (project / "paydirt/source_adapter.py").write_text("Changed\n")
    elif mutation == "added-code": (project / "paydirt/added.py").write_text("Added\n")
    elif mutation == "changed-inventory": inventory(bundle); (bundle / "inventory.json").write_text("{}")
    elif mutation == "changed-contract":
        path = bundle.parent / "substituted-contract.json"; path.write_text("{}")
    elif mutation == "changed-runtime": data["binding"]["engine_fingerprint"] = "0" * 64
    elif mutation == "substitute-inputs":
        path = Path(data["gate_input_inventory"])
        path.write_text(json.dumps({"wrong/input.csv": str(bundle / "inputs/play_by_play/source.csv")}))
    elif mutation == "substitute-stats": data["source_paths"]["stats_dir"] = str(candidate)
    elif mutation == "missing-binding": data.pop("binding")
    elif mutation == "bad-exit": data["execution"]["exit_code"] = 1
    elif mutation == "substitute-command": data["execution"]["command"][1] = "/unrelated/producer.py"
    elif mutation == "substitute-cwd": data["execution"]["cwd"] = str(project)
    receipt.write_text(json.dumps(data) if mutation != "duplicate-json" else '{"passed":true,"passed":true}')
    with pytest.raises((ValueError, KeyError, TypeError, OSError, RuntimeError)):
        module.prepared_source_options(receipt, candidate, bundle.parent / "substituted-contract.json"
                                       if mutation == "changed-contract" else bundle / "contract.json")


def test_bare_cohort_cli_uses_actual_verified_preparation_before_starting_games(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _module, _receipt = prepared_receipt(bundle_files, monkeypatch)
    import paydirt.chart_release_gate as gate
    import scripts.audit_generated_charts as cli
    bundle, candidate, output, project, _calls = bundle_files
    contract_path = bundle / "contract.json"
    calls = []
    monkeypatch.setattr(cli, "ROOT", project)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *_a, **_k: calls.append("games") or {
        "metadata": {"attempt_end_zone_interception_returns": False}})
    def audit(_candidate: Path, _contract: dict, _report: dict, **options: object) -> dict:
        calls.append(options)
        return {"passed": True, "release_certified": False}
    monkeypatch.setattr(gate, "audit_release", audit)
    assert cli.main(["--season-dir", str(candidate), "--contract", str(contract_path),
                     "--output", str(project / "cohort.json")]) == 0
    assert calls[0] == "games"
    assert calls[1]["stats_dir"] == bundle / "inputs/normalized_stats"
    assert calls[1]["reproduced_dir"] == output


@pytest.mark.parametrize("target", ["receipt", "input-inventory", "source", "contract", "candidate", "reproduction", "log", "code"])
@pytest.mark.parametrize("invalid", [False, True])
def test_bare_cohort_cli_preserves_preparation_inputs_even_when_validation_fails(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, target: str, invalid: bool,
) -> None:
    _module, receipt = prepared_receipt(bundle_files, monkeypatch)
    import scripts.audit_generated_charts as cli
    bundle, candidate, reproduced, project, _calls = bundle_files
    data = json.loads(receipt.read_text())
    if invalid:
        data["passed"] = False
        receipt.write_text(json.dumps(data))
    targets = {"receipt": receipt, "input-inventory": Path(data["gate_input_inventory"]),
               "source": bundle / "inputs/play_by_play/source.csv", "contract": bundle / "contract.json",
               "candidate": candidate / "A/offense.csv", "reproduction": reproduced / "A/offense.csv",
               "log": reproduced.with_suffix(".log"), "code": project / "paydirt/source_adapter.py"}
    destination = targets[target]
    before = destination.read_bytes()
    monkeypatch.setattr(cli, "ROOT", project)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *_a, **_k: pytest.fail("Reject output collisions before games"))
    assert cli.main(["--season-dir", str(candidate), "--contract", str(bundle / "contract.json"),
                     "--output", str(destination)]) == 1
    assert destination.read_bytes() == before


def test_stale_preparation_is_rejected_before_games_and_partial_flags_cannot_use_discovery(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _module, receipt = prepared_receipt(bundle_files, monkeypatch)
    import scripts.audit_generated_charts as cli
    bundle, candidate, _reproduced, project, _calls = bundle_files
    monkeypatch.setattr(cli, "ROOT", project)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *_a, **_k: pytest.fail("Reject stale inputs before games"))
    arguments = ["--season-dir", str(candidate), "--contract", str(bundle / "contract.json"),
                 "--output", str(project / "failure.json")]
    assert cli.main(arguments + ["--source-inputs", str(receipt)]) == 1
    (bundle / "inputs/play_by_play/source.csv").write_text("Changed\n")
    assert cli.main(arguments) == 1


@pytest.mark.parametrize("name", ["paydirt/source_adapter.py", "scripts/stage_chart_sources.py", "config/validation.json", ".github/workflows/test.yml",
                                  "seasons/2026/A/offense.csv", ".git/config", ".gitignore"])
@pytest.mark.parametrize("campaign", [False, True])
def test_explicit_source_flags_cannot_overwrite_implementation_files(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch, name: str, campaign: bool,
) -> None:
    _module, receipt = prepared_receipt(bundle_files, monkeypatch)
    import scripts.audit_generated_charts as cli
    bundle, candidate, reproduced, project, _calls = bundle_files
    data = json.loads(receipt.read_text())
    receipt.unlink()  # Exercise explicit source evidence without discovery.
    destination = project / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("Preserve implementation\n")
    before = destination.read_bytes()
    monkeypatch.setattr(cli, "ROOT", project)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *_a, **_k: pytest.fail("Reject implementation output before games"))
    arguments = (["--campaign-bundle", str(project / "missing-campaign.json")] if campaign else [
        "--season-dir", str(candidate), "--contract", str(bundle / "contract.json"),
        "--source-inputs", data["gate_input_inventory"], "--source-stats-dir", str(bundle / "inputs/normalized_stats"),
        "--reproduced-dir", str(reproduced)])
    assert cli.main(arguments + ["--output", str(destination)]) == 1
    assert destination.read_bytes() == before


@pytest.mark.parametrize("generator", ["generate_nflverse_charts.py", "generate_pfr_charts.py"])
@pytest.mark.parametrize(("declared", "requested", "valid"), [
    ("credited_fumble_proxy_v1", "credited_fumble_proxy_v1", True),
    ("known_physical_v1", "known_physical_v1", True),
    ("credited_fumble_proxy_v1", None, False),
    (None, "credited_fumble_proxy_v1", False),
    ("credited_fumble_proxy_v1", "known_physical_v1", False),
    ("unreviewed_policy", "unreviewed_policy", False),
])
def test_source_recipe_binds_explicit_fumble_policy(
    bundle_files: BundleFiles, monkeypatch: pytest.MonkeyPatch,
    generator: str, declared: str | None, requested: str | None, valid: bool,
) -> None:
    bundle, candidate, _output, _project, calls = bundle_files
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["generator_script"] = generator
    if generator == "generate_pfr_charts.py":
        recipe["arguments"][recipe["arguments"].index("--pbp")] = "--html-dir"
        recipe["arguments"][-1] = "inputs/play_by_play"
        manifest["fumble_gain_policy"] = declared
    else:
        manifest["fumble_gain_model"] = {"policy": declared}
    if requested is not None:
        recipe["arguments"] += ["--fumble-gain-policy", requested]
    manifest_path.write_text(json.dumps(manifest))
    recipe_path.write_text(json.dumps(recipe))
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract["generation_manifest_sha256"] = digest(manifest_path)
    contract_path.write_text(json.dumps(contract))
    inventory(bundle)
    result = prepare(bundle_files, monkeypatch)
    assert result["passed"] is valid, result["errors"]
    assert len(calls) == int(valid)
    assert result["release_certified"] is False
    if valid:
        command = result["execution"]["command"]
        assert command[command.index("--fumble-gain-policy") + 1] == declared

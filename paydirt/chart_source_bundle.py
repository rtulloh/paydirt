"""Prepare actual source/reproduction paths for the existing chart gate.

This performs local byte-bound generation. It does not acquire remote sources,
establish upstream truth, start games or certify complete charter readiness.
"""
from __future__ import annotations

import gzip
import hashlib
import math
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

from .chart_engine_audit import chart_fingerprint, engine_fingerprint
from .chart_release_gate import _strict_json_object, _strict_json_value
from .chart_source_bindings import MODERN_GROUPS, modern_source_bindings, pfr_reconciliation_binding
from .fumble_source import validate_fumble_gain_policy

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generation_file_hashes() -> dict[str, str]:
    """Bind both generator entry points and all local Python source adapters."""
    paths = [PROJECT_ROOT / name for name in ("generate_pfr_charts.py", "generate_nflverse_charts.py")]
    package = PROJECT_ROOT / "paydirt"
    if not package.is_dir() or package.is_symlink():
        raise ValueError("Generation requires the local paydirt source package")
    paths.extend(package.rglob("*.py"))
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError("Generation code must consist of regular local files")
    return {path.relative_to(PROJECT_ROOT).as_posix(): _digest(path) for path in sorted(paths)}


def _relative(name: str) -> Path:
    if (not isinstance(name, str) or not name or "\\" in name
            or Path(name).is_absolute() or ".." in Path(name).parts
            or Path(name).as_posix() != name or name == "."):
        raise ValueError("Bundle paths must be canonical relative paths")
    return Path(name)


def _bundle_files(bundle: Path) -> dict[str, str]:
    """Verify the complete inventory, including strict supported JSON objects."""
    inventory_path = bundle / "inventory.json"
    if inventory_path.is_symlink():
        raise ValueError("Bundle inventories must be regular local files")
    inventory = _strict_json_object(inventory_path.read_bytes())
    if (set(inventory) != {"schema_version", "files"}
            or type(inventory["schema_version"]) is not int or inventory["schema_version"] != 1
            or not isinstance(inventory["files"], dict) or not inventory["files"]):
        raise ValueError("Requires a nonempty schema-1 source file inventory")
    paths = list(bundle.rglob("*"))
    if any(path.is_symlink() for path in paths):
        raise ValueError("Portable source bundles cannot contain symlinks")
    actual = {path.relative_to(bundle).as_posix(): path for path in paths
              if path.is_file() and path != inventory_path}
    if set(actual) != set(inventory["files"]):
        raise ValueError("Source bundle file inventory differs from actual files")
    hashes = {}
    for name, expected in inventory["files"].items():
        relative = _relative(name)
        if (relative.parts[0] not in {"inputs", "template"}
                and name not in {"recipe.json", "contract.json"}):
            raise ValueError(f"Unexpected source bundle file: {name}")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Invalid source file SHA-256: {name}")
        data = actual[name].read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Source bundle bytes changed: {name}")
        if relative.suffix == ".json":
            if relative.parts[:2] == ("inputs", "fumble_reviews"):
                if not isinstance(_strict_json_value(data), list):
                    raise ValueError("Typed fumble reviews require a JSON list")
            else:
                _strict_json_object(data)
        hashes[name] = expected
    hashes["inventory.json"] = _digest(inventory_path)
    return hashes


def prepare_chart_sources(bundle_dir: Path, candidate_dir: Path, reproduced_dir: Path) -> dict[str, Any]:
    """Run a verified local recipe and require complete candidate reproduction.

    Args:
        bundle_dir: Cohort directory containing inventory, recipe and public inputs.
        candidate_dir: Actual candidate whose contract and bytes must be reproduced.
        reproduced_dir: New year-prefixed output directory; existing evidence is preserved.

    Returns:
        Noncertifying preparation verdict, actual paths and execution/log bindings.
    """
    bundle, candidate, output = (Path(path).resolve() for path in (bundle_dir, candidate_dir, reproduced_dir))
    audit = output.with_name(output.name + "-classified")
    log = output.with_suffix(".log")
    errors: list[str] = []
    execution: dict[str, Any] = {"exit_code": None, "log_path": str(log), "log_sha256": None}
    source_paths: dict[str, Any] = {}
    before_files: dict[str, str] | None = None
    before_candidate: str | None = None
    before_engine: str | None = None
    script: Path | None = None
    before_script: str | None = None
    before_code: dict[str, str] | None = None
    log_created = False
    try:
        for destination in (output, audit, log):
            if destination.exists() or destination.is_symlink():
                raise ValueError(f"Preparation preserves existing output/log paths: {destination}")
            if destination.is_relative_to(bundle) or destination.is_relative_to(candidate):
                raise ValueError("Preparation outputs must be outside source inputs and candidate")
        before_files = _bundle_files(bundle)
        recipe = _strict_json_object((bundle / "recipe.json").read_bytes())
        contract = _strict_json_object((bundle / "contract.json").read_bytes())
        manifest = _strict_json_object((candidate / "generation-manifest.json").read_bytes())
        if (set(recipe) != {"schema_version", "generator_script", "arguments", "expected_input_hashes",
                           "expected_csv_hashes", "scope"}
                or type(recipe["schema_version"]) is not int or recipe["schema_version"] != 1
                or recipe["generator_script"] not in {"generate_pfr_charts.py", "generate_nflverse_charts.py"}):
            raise ValueError("Requires a schema-1 recipe for one of the two existing generators")
        season = contract.get("season")
        if (type(season) is not int or season <= 0 or manifest.get("season") != season
                or contract.get("generation_manifest_sha256") != _digest(candidate / "generation-manifest.json")
                or contract.get("generation_profile") != manifest.get("calibration_profile")):
            raise ValueError("Candidate manifest, source season or declared profile differs from contract")
        if output.name != str(season) and not output.name.startswith(f"{season}-"):
            raise ValueError("Reproduction directory must begin with its source year")
        inputs = {name.removeprefix("inputs/"): sha for name, sha in before_files.items()
                  if name.startswith("inputs/")}
        if (not inputs or inputs != recipe["expected_input_hashes"] or inputs != contract.get("input_hashes")
                or inputs != manifest.get("input_hashes")):
            raise ValueError("Actual source labels/hashes differ from recipe, contract or generation manifest")
        csvs = {path.relative_to(candidate).as_posix(): _digest(path) for path in candidate.glob("*/*.csv")}
        if not csvs or csvs != recipe["expected_csv_hashes"] or csvs != contract.get("chart_hashes"):
            raise ValueError("Actual candidate CSV inventory differs from bound contract/recipe")
        groups: dict[str, list[str]] = {}
        pfr = recipe["generator_script"] == "generate_pfr_charts.py"
        for name in inputs:
            relative = _relative(name)
            if len(relative.parts) != 2 and not (pfr and len(relative.parts) > 2
                                                and relative.parts[0] == "event_reconciliations"):
                raise ValueError("Generation inputs require group/filename labels, or nested replay evidence")
            groups.setdefault(relative.parts[0], []).append("inputs/" + name)
        common_groups = {"normalized_stats", "play_by_play", "team_map"}
        allowed_groups = common_groups | {"profile"} | ({"event_reconciliations"} if pfr else MODERN_GROUPS)
        if not common_groups <= set(groups) or set(groups) - allowed_groups or len(groups["team_map"]) != 1:
            raise ValueError("Incomplete or unsupported source input groups")
        if (not isinstance(contract.get("teams"), dict)
                or {Path(name).stem for name in groups["normalized_stats"]} != set(contract["teams"])
                or any(Path(name).suffix != ".json" for name in groups["normalized_stats"])):
            raise ValueError("Normalized statistics do not match the complete contract team inventory")
        arguments = recipe["arguments"]
        if (not isinstance(arguments, list) or len(arguments) % 2
                or any(not isinstance(part, str) or not part for part in arguments)):
            raise ValueError("Recipe arguments require explicit flag/value pairs")
        flags = arguments[::2]
        if len(set(flags)) != len(flags):
            raise ValueError("Duplicate generation argument")
        values = dict(zip(flags, arguments[1::2]))
        expected = {"--stats-dir": "inputs/normalized_stats", "--template-season": f"template/{season}",
                    "--team-map": groups["team_map"][0], "--output": "{output}", "--audit-dir": "{audit}"}
        if pfr:
            expected["--html-dir"] = "inputs/play_by_play"
            if "event_reconciliations" in groups:
                expected["--event-reconciliations"] = pfr_reconciliation_binding(
                    bundle, groups["event_reconciliations"], values.get("--event-reconciliations"))
            if manifest.get("through_date") is not None:
                expected["--through-date"] = str(manifest["through_date"])
        else:
            if len(groups["play_by_play"]) != 1:
                raise ValueError("nflverse generation requires one bound play-by-play file")
            expected["--pbp"] = groups["play_by_play"][0]
        if "profile" in groups:
            if len(groups["profile"]) != 1:
                raise ValueError("Requires one bound calibration profile")
            expected["--calibration-profile"] = groups["profile"][0]
        model = manifest.get("fumble_gain_model", {})
        if not pfr and not isinstance(model, dict):
            raise ValueError("Generation manifest requires a fumble gain model object")
        policy = manifest.get("fumble_gain_policy") if pfr else model.get("policy")
        validate_fumble_gain_policy(policy)
        if policy is not None:
            expected["--fumble-gain-policy"] = policy
        if not pfr:
            expected.update(modern_source_bindings(bundle, PROJECT_ROOT, groups, manifest, values, policy))
        if set(values) != set(expected) | {"--seed", "--opponent-shrinkage"}:
            raise ValueError("Unknown or missing generation arguments")
        for flag, value in expected.items():
            if values[flag] != value:
                raise ValueError(f"Generation argument differs from bound inputs: {flag}")
        seed, shrinkage = int(values["--seed"]), float(values["--opponent-shrinkage"])
        if (seed != manifest.get("seed") or not math.isfinite(shrinkage) or shrinkage < 0
                or shrinkage != manifest.get("opponent_adjustment", {}).get("shrinkage")):
            raise ValueError("Generation seed or shrinkage differs from bound candidate")
        for flag, value in expected.items():
            if flag in {"--output", "--audit-dir", "--through-date", "--fumble-gain-policy",
                        "--fumble-projection-mode", "--fumble-range-policy"}:
                continue
            path = bundle / _relative(value)
            if not path.exists() or not path.resolve().is_relative_to(bundle):
                raise ValueError(f"Missing or external generation input: {flag}")
        source_paths = {"input_files": {name: str(bundle / "inputs" / name) for name in inputs},
                        "stats_dir": str(bundle / "inputs/normalized_stats"), "reproduced_dir": str(output)}
        before_candidate, before_engine = chart_fingerprint(candidate), engine_fingerprint()
        script = PROJECT_ROOT / recipe["generator_script"]
        before_script = _digest(script)
        before_code = generation_file_hashes()
        command = [sys.executable, str(script), *[str(output) if part == "{output}" else
                   str(audit) if part == "{audit}" else part for part in arguments]]
        execution.update(command=command, cwd=str(bundle), script_sha256=before_script)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("x") as stream:
            log_created = True
            completed = subprocess.run(command, check=False, cwd=bundle, stdout=stream, stderr=subprocess.STDOUT)
        execution["exit_code"] = completed.returncode
        if completed.returncode != 0:
            errors.append(f"Generator exited with status {completed.returncode}; inspect the retained log")
        elif chart_fingerprint(output) != before_candidate:
            errors.append("Generated charts, manifest, rules or metadata differ from candidate")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    if log_created:
        try:
            execution["log_sha256"] = _digest(log)
        except OSError as error:
            errors.append(f"Cannot retain generator log: {error}")
    try:
        if before_files is not None and _bundle_files(bundle) != before_files:
            errors.append("Source bundle changed during generation")
        if before_candidate is not None and chart_fingerprint(candidate) != before_candidate:
            errors.append("Candidate changed during generation")
        if before_engine is not None and engine_fingerprint() != before_engine:
            errors.append("Loaded runtime changed during generation")
        if script is not None and _digest(script) != before_script:
            errors.append("Generator script changed during generation")
        if before_code is not None and generation_file_hashes() != before_code:
            errors.append("Generation source code changed during generation")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    return {"passed": not errors, "release_certified": False, "errors": errors,
            "source_paths": source_paths, "execution": execution,
            "binding": {"bundle_dir": str(bundle), "inventory_sha256": (before_files or {}).get("inventory.json"),
                        "candidate_dir": str(candidate), "chart_fingerprint": before_candidate,
                        "engine_fingerprint": before_engine, "generation_files": before_code},
            "scope": "Actual local source/generation consistency only; upstream truth, source quality, "
                     "campaigns and complete charter readiness remain separate checks."}


def prepared_source_options(receipt_path: Path, candidate_dir: Path, contract_path: Path) -> dict[str, Any]:
    """Revalidate prepared evidence before supplying paths to the existing gate.

    A receipt records trusted local execution, not upstream truth or readiness.
    Source facts and mechanics still require the independent component checks.
    """
    receipt = _strict_json_object(Path(receipt_path).read_bytes())
    if receipt.get("passed") is not True or receipt.get("errors") != [] or receipt.get("release_certified") is not False:
        raise ValueError("Source preparation is failed, contradictory or incorrectly certified")
    binding, execution, paths = (receipt[name] for name in ("binding", "execution", "source_paths"))
    bundle, candidate = Path(binding["bundle_dir"]).resolve(), Path(candidate_dir).resolve()
    code = generation_file_hashes()
    runtime, fingerprint = engine_fingerprint(), chart_fingerprint(candidate)
    files = _bundle_files(bundle)
    if (binding["generation_files"] != code or binding["engine_fingerprint"] != runtime
            or binding["chart_fingerprint"] != fingerprint
            or binding["inventory_sha256"] != files["inventory.json"]):
        raise ValueError("Prepared source bytes, code, runtime or candidate are stale")
    if _digest(Path(contract_path)) != files["contract.json"]:
        raise ValueError("Prepared sources belong to a different contract")
    recipe = _strict_json_object((bundle / "recipe.json").read_bytes())
    script = PROJECT_ROOT / recipe["generator_script"]
    if recipe["generator_script"] not in {"generate_pfr_charts.py", "generate_nflverse_charts.py"}:
        raise ValueError("Prepared generator is unsupported")
    output = Path(paths["reproduced_dir"]).resolve()
    audit = output.with_name(output.name + "-classified")
    expected_command = [sys.executable, str(script), *[str(output) if part == "{output}" else
                        str(audit) if part == "{audit}" else part for part in recipe["arguments"]]]
    log = output.with_suffix(".log")
    if (type(execution["exit_code"]) is not int or execution["exit_code"] != 0
            or execution["command"] != expected_command or execution["cwd"] != str(bundle)
            or execution["script_sha256"] != _digest(script)
            or execution["log_path"] != str(log) or execution["log_sha256"] != _digest(log)
            or chart_fingerprint(output) != fingerprint):
        raise ValueError("Prepared generator execution, log or reproduction differs from actual evidence")
    inputs = {name.removeprefix("inputs/"): str(bundle / name) for name in files if name.startswith("inputs/")}
    if (paths["input_files"] != inputs or paths["stats_dir"] != str(bundle / "inputs/normalized_stats")
            or _strict_json_object(Path(receipt["gate_input_inventory"]).read_bytes()) != inputs):
        raise ValueError("Prepared gate paths differ from actual source inventory")
    if (generation_file_hashes() != code or engine_fingerprint() != runtime
            or chart_fingerprint(candidate) != fingerprint or _bundle_files(bundle) != files):
        raise ValueError("Prepared evidence changed during validation")
    return {"input_files": {name: Path(path) for name, path in inputs.items()},
            "stats_dir": bundle / "inputs/normalized_stats", "reproduced_dir": output}


def pack_chart_sources(bundle_dir: Path, archive_path: Path) -> dict[str, Any]:
    """Package verified local source bytes deterministically without publishing."""
    bundle, archive = Path(bundle_dir).resolve(), Path(archive_path)
    if archive.exists() or archive.is_symlink() or archive.resolve().is_relative_to(bundle):
        raise ValueError("Source archives require a new path outside their input bundle")
    files = _bundle_files(bundle)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with (archive.open("xb") as raw,
          gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed,
          tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as stream):
        for name in sorted(files):
            path = bundle / name
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = path.stat().st_size, 0o644, 0
            with path.open("rb") as source:
                stream.addfile(member, source)
    if _bundle_files(bundle) != files:
        raise ValueError("Source bundle changed while packaging")
    return {"passed": True, "release_certified": False, "archive": str(archive.resolve()),
            "sha256": _digest(archive), "file_count": len(files), "inventory_sha256": files["inventory.json"]}


def unpack_chart_sources(archive_path: Path, expected_sha256: str, destination_dir: Path) -> dict[str, Any]:
    """Stage a pinned local archive using regular files and canonical paths only.

    Existing destinations are preserved. Failed new staging directories remain
    available for diagnosis and cannot be reused as a successful preparation.
    """
    archive, destination = Path(archive_path), Path(destination_dir)
    if (not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
            or _digest(archive) != expected_sha256):
        raise ValueError("Source archive does not match its pinned SHA-256")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Source staging preserves existing destinations")
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        names: set[str] = set()
        for member in members:
            _relative(member.name)
            if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE} or member.name in names:
                raise ValueError("Source archives require unique regular-file members")
            names.add(member.name)
        if "inventory.json" not in names:
            raise ValueError("Source archive is missing its inventory")
        for name in names:
            if any(parent.as_posix() in names for parent in Path(name).parents if parent != Path(".")):
                raise ValueError("Source archive has conflicting file and parent paths")
        destination.mkdir(parents=True)
        for member in members:
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = stream.extractfile(member)
            if source is None:
                raise ValueError("Source archive contains an unreadable member")
            with source, target.open("xb") as output:
                while data := source.read(1024 * 1024):
                    output.write(data)
    files = _bundle_files(destination)
    if _digest(archive) != expected_sha256:
        raise ValueError("Source archive changed during staging")
    return {"passed": True, "release_certified": False, "bundle_dir": str(destination),
            "archive_sha256": expected_sha256, "file_count": len(files),
            "inventory_sha256": files["inventory.json"]}

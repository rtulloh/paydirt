"""Combine chart checks without treating missing evidence as success."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import struct
import subprocess
import sys
import zlib
from collections import ChainMap
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .chart_allocation_gate import audit_allocations
from .chart_audit import audit_season
from .chart_engine_audit import (
    audit_observer_conformance,
    chart_fingerprint,
    engine_fingerprint,
    validate_engine_report,
)
from .chart_generator import EmpiricalPassCalibration
from .chart_loader import parse_defense_csv
from .chart_runtime_identity import loaded_runtime_identity
from .chart_tactics_audit import (
    audit_defense_tactics,
    audit_engine_controls,
    audit_generated_offense_risk_order,
    audit_generated_strength_order,
    audit_priority_resolution,
)
from .generated_source_audit import audit_generated_source

# Stable audit cohort IDs map to the public numeric season directories.
PUBLIC_SEASON_DIRECTORIES = {"1983-generated": "1983", "2024": "2024"}


def readiness_file_inventory(root: Path) -> dict[str, str]:
    """Discover implementation/validation bytes without scanning local season data.

    Dependencies and caches are excluded. Required anchors distinguish an
    intended public checkout from an empty directory or partial file selection.
    """
    root = Path(root).resolve()
    required = {
        "AGENTS.md", "pyproject.toml", "generate_nflverse_charts.py", "generate_pfr_charts.py",
        "tune_charts.py", "paydirt/game_engine.py", "paydirt/chart_engine_audit.py",
        "paydirt/chart_runtime_identity.py", "paydirt/chart_release_gate.py",
        "paydirt/chart_generator.py", "paydirt/auto_game.py", "scripts/audit_generated_charts.py",
        "paydirt-web/backend/main.py", "paydirt-web/backend/requirements.txt",
        "paydirt-web/frontend/package.json", "paydirt-web/frontend/package-lock.json",
        "paydirt-web/frontend/vite.config.js", "paydirt-web/frontend/playwright.config.js",
        ".github/workflows/test.yml", ".github/workflows/release.yml",
        "config/chart-validation/1983.json", "config/chart-validation/2024.json",
        "docs/dev-notes/chart-confidence-agent-charter.md",
        "docs/dev-notes/chart-reference-comparison-protocol.md",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise ValueError(f"Missing readiness implementation anchors: {', '.join(missing)}")
    files = {root / name for name in required}
    patterns = (
        (".", "*.py"), (".", "*.spec"), ("paydirt", "**/*"),
        ("tests", "**/*.py"), ("scripts", "**/*.py"),
        ("paydirt-web/backend", "*.py"), ("paydirt-web/backend/tests", "**/*.py"),
        ("paydirt-web/backend", "requirements*.txt"),
        ("paydirt-web/frontend/src", "**/*"), ("paydirt-web/frontend/e2e", "**/*"),
        ("paydirt-web/frontend", "*.js"), ("paydirt-web/frontend", "*.mjs"),
        ("paydirt-web/frontend", "*.cjs"), ("paydirt-web/frontend", "*.json"),
        ("paydirt-web/frontend", "*.html"), (".github/workflows", "*.yml"),
        (".github/workflows", "*.yaml"), ("config/chart-validation", "**/*.json"),
    )
    for directory, pattern in patterns:
        files.update(path for path in (root / directory).glob(pattern)
                     if path.is_file() and "__pycache__" not in path.parts)
    result = {}
    for path in sorted(files):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Readiness implementation must use local regular files: {path}")
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _strict_json_value(data: bytes) -> Any:
    """Decode finite JSON with unique object keys, including typed list inputs."""
    def unique_object(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise ValueError(f"Nonfinite JSON constant: {value}")

    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Nonfinite JSON number: {value}")
        return number

    result = json.loads(data, object_pairs_hook=unique_object,
                        parse_constant=reject_constant, parse_float=finite_float)
    return result


def _strict_json_object(data: bytes) -> dict:
    result = _strict_json_value(data)
    if not isinstance(result, dict):
        raise TypeError("Expected a JSON object")
    return result


def audit_readiness_freeze(root: Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    """Check frozen implementation, candidates and generation inputs against bytes.

    Reserved-family registration is a declaration, not proof of non-observation.
    The full readiness bundle must additionally bind the parent's announcement,
    seed-use history and every independent acceptance component.
    """
    root = Path(root).resolve()
    errors: list[str] = []
    cohorts: dict[str, dict] = {}
    directories: dict[str, tuple[Path, str]] = {}
    bound_inputs: dict[Path, str] = {}
    before_engine: str | None = None
    try:
        before_engine = engine_fingerprint()
    except (ValueError, TypeError, OSError, RuntimeError) as error:
        errors.append(f"Cannot verify loaded runtime: {error}")
    before_files: dict[str, str] | None = None

    def artifact(reference: Any) -> bytes:
        if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
                or not isinstance(reference["path"], str) or not reference["path"]
                or not isinstance(reference["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])):
            raise ValueError("Requires an explicit path and SHA-256 binding")
        path = (root / reference["path"]).resolve()
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != reference["sha256"]:
            raise ValueError("Frozen input bytes differ from declared SHA-256")
        bound_inputs[path] = reference["sha256"]
        return data

    try:
        if (not isinstance(freeze, Mapping) or set(freeze) != {
                "schema_version", "engine_fingerprint", "files", "cohorts", "reserved_families",
        } or type(freeze.get("schema_version")) is not int or freeze["schema_version"] != 1):
            raise ValueError("Requires schema-1 frozen implementation/input inventory")
        before_files = readiness_file_inventory(root)
        if freeze["files"] != before_files:
            errors.append("Frozen implementation inventory differs from current files")
        if before_engine is not None and freeze["engine_fingerprint"] != before_engine:
            errors.append("Frozen loaded-runtime fingerprint differs from current engine")
        expected_seeds = {
            "held_out": {"master": 20361108, "opened": False},
            "reference": {"master": 20461108, "opened": False},
            "transfer": {"master": 20561108, "opened": False},
        }
        if (freeze["reserved_families"] != expected_seeds
                or any(type(entry.get("master")) is not int or entry.get("opened") is not False
                       for entry in freeze["reserved_families"].values())):
            errors.append("Freeze must register the three unopened charter master families")
        expected = {"1983-generated": (1983, 28), "2024": (2024, 32)}
        if not isinstance(freeze["cohorts"], dict) or set(freeze["cohorts"]) != set(expected):
            errors.append("Freeze requires exactly the two complete source cohorts")
        entries = freeze["cohorts"] if isinstance(freeze["cohorts"], dict) else {}
        for name, (season, count) in expected.items():
            reasons: list[str] = []
            cohorts[name] = {"passed": False, "errors": reasons}
            try:
                entry = entries.get(name)
                if (not isinstance(entry, dict) or set(entry) != {
                        "season_dir", "chart_fingerprint", "contract", "source_inputs",
                } or not isinstance(entry["season_dir"], str) or not entry["season_dir"]
                        or not isinstance(entry["chart_fingerprint"], str)
                        or not re.fullmatch(r"[0-9a-f]{64}", entry["chart_fingerprint"])):
                    raise ValueError("Missing candidate, contract or generation-input binding")
                directory = (root / entry["season_dir"]).resolve()
                current = chart_fingerprint(directory)
                directories[name] = (directory, current)
                if current != entry["chart_fingerprint"]:
                    reasons.append("Frozen candidate chart/profile/rule bytes changed")
                contract = _strict_json_object(artifact(entry["contract"]))
                if (contract.get("season") != season or not isinstance(contract.get("teams"), dict)
                        or len(contract["teams"]) != count):
                    reasons.append("Incomplete or substituted frozen source contract")
                manifest = _strict_json_object((directory / "generation-manifest.json").read_bytes())
                if manifest.get("season") != season:
                    reasons.append("Frozen generation manifest substitutes another source season")
                inputs, declared = entry["source_inputs"], manifest.get("input_hashes")
                if (not isinstance(inputs, dict) or not inputs or not isinstance(declared, dict)
                        or set(inputs) != set(declared)):
                    raise ValueError("Frozen source labels differ from generation-manifest inputs")
                for label, reference in inputs.items():
                    try:
                        artifact(reference)
                        if reference["sha256"] != declared[label]:
                            reasons.append(f"{label}: source hash differs from generation manifest")
                    except (ValueError, TypeError, OSError) as error:
                        reasons.append(f"{label}: {error}")
            except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
                reasons.append(str(error))
            cohorts[name]["passed"] = not reasons
            errors.extend(f"{name}: {reason}" for reason in reasons)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    try:
        if before_files is not None and readiness_file_inventory(root) != before_files:
            errors.append("Implementation files changed during freeze validation")
        if engine_fingerprint() != before_engine:
            errors.append("Loaded runtime changed during freeze validation")
        for name, (directory, before) in directories.items():
            if chart_fingerprint(directory) != before:
                errors.append(f"{name}: candidate changed during freeze validation")
        for path, expected in bound_inputs.items():
            try:
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    errors.append(f"Frozen input changed during freeze validation: {path}")
            except OSError as error:
                errors.append(f"Frozen input changed during freeze validation: {path}: {error}")
    except (ValueError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    return {
        "passed": not errors, "release_certified": False, "errors": errors, "cohorts": cohorts,
        "scope": "Frozen-byte consistency only; source truth, non-observation, campaigns, "
                 "benchmark/transfer, regression, visual packet and independent review remain required.",
    }


def required_regression_commands(*, released_charts: bool = False) -> dict[str, tuple[str, list[str]]]:
    """Return strict candidate commands, or the explicit unchanged-release checklist.

    Frozen candidate collection/output validation deliberately remains strict.
    released_charts=True is the AGENTS route for immutable published inputs only.
    """
    python = sys.executable
    commands = {
        "core": (".", [python, "-m", "pytest", "tests/", "-q", "-o", "addopts=", "--tb=short", "-rs", "--cov=paydirt", "--cov-report=term"]),
        "backend": ("paydirt-web/backend", [python, "-m", "pytest", "tests/", "-q", "-o", "addopts=", "--tb=short"]),
        "frontend": ("paydirt-web/frontend", ["npm", "test", "--", "--run"]),
        "build": ("paydirt-web/frontend", ["npm", "run", "build"]),
        "browser": ("paydirt-web/frontend", ["npm", "run", "test:e2e"]),
        "lint": (".", ["ruff", "check", "paydirt/", "tests/", "paydirt-web/backend/"]),
        "all_games": (".", [python, "tests/run_all_games.py"]),
        "full_season": (".", [python, "tests/run_full_season.py"]),
    }
    for name, season in (("public_ai", "2026"), ("local_ai", "1983")):
        label = "public" if name == "public_ai" else "local"
        command = [python, "tests/run_ai_audit.py", "--season", season, "--weeks", "16", "--seed", "8306",
                   "--compare-balanced", "--output", f".ai-audits/{label}-season.json"]
        if name == "local_ai":
            command += ["--csv", ".ai-audits/local-season.csv"]
        commands[name] = (".", command)
    for season, directory in (("1983", "1983"), ("2024", "2024")):
        if released_charts:
            commands[f"chart_{season}"] = (".", [
                python, "-m", "paydirt.released_chart_regression_audit", "--season", season,
                "--output", f".ai-audits/chart-quality-{season}.json",
            ])
        else:
            commands[f"chart_{season}"] = (".", [
                python, "scripts/audit_generated_charts.py", "--season-dir", f"seasons/{directory}",
                "--contract", f"config/chart-validation/{season}.json", "--output", f".ai-audits/chart-quality-{season}.json",
                "--repetitions", "64", "--workers", "4",
            ])
    return commands


def readiness_freeze_fingerprint(freeze: Mapping[str, Any]) -> str:
    """Identify canonical freeze contents independently of JSON formatting."""
    return hashlib.sha256(json.dumps(freeze, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _audit_execution_log(
    root: Path, reference: object, cwd: Path, argv: list[str], logs: dict[Path, str],
    *, pythonpath: Path | None = None,
) -> dict[str, Any]:
    """Validate one bound execution record and retain its bytes for the final recheck."""
    errors: list[str] = []
    diagnostics: list[str] = []
    try:
        if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
                or not isinstance(reference["path"], str) or not reference["path"]
                or not isinstance(reference["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])):
            raise ValueError("Missing execution-log path/SHA-256 binding")
        path = (root / reference["path"]).resolve()
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != reference["sha256"]:
            raise ValueError("Execution log differs from bound SHA-256")
        logs[path] = reference["sha256"]
        execution = _strict_json_object(data)
        fields = {"argv", "cwd", "returncode", "stdout", "stderr"}
        if pythonpath is not None:
            fields.add("pythonpath")
        if set(execution) != fields:
            raise ValueError("Execution log must retain command, location, status and output with the required isolation fields")
        if (execution["argv"] != argv or execution["cwd"] != str(cwd.resolve())
                or (pythonpath is not None and execution["pythonpath"] != str(pythonpath))):
            errors.append("Execution command, working directory or isolation differs from the required command")
        if type(execution["returncode"]) is not int or execution["returncode"] != 0:
            errors.append("Required execution failed or lacks a valid exit status")
        if not isinstance(execution["stdout"], str) or not isinstance(execution["stderr"], str):
            raise TypeError("Execution stdout/stderr must retain actual text")
        output = execution["stdout"] + "\n" + execution["stderr"]
        if not output.strip():
            errors.append("Required execution has no output evidence")
        diagnostics = [line for line in output.splitlines()
                       if re.search(r"\b(skip(?:ped|s)?|warn(?:ings?)?|vulnerabilit(?:y|ies))\b", line, re.IGNORECASE)]
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    return {"passed": not errors, "errors": errors, "diagnostics": diagnostics}


def audit_regression_evidence(root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Check complete bound execution logs against an unchanged frozen candidate.

    Logs contain argv, cwd, returncode, stdout and stderr captured by a trusted
    local runner. This validates evidence consistency, not hostile-host execution
    attestation. Clean snapshot, review and other readiness components are separate.
    """
    root = Path(root).resolve()
    errors: list[str] = []
    commands: dict[str, dict] = {}
    logs: dict[Path, str] = {}
    before = audit_readiness_freeze(root, freeze)
    if not before["passed"]:
        errors.extend(f"Initial freeze: {error}" for error in before["errors"])
    try:
        if (not isinstance(evidence, Mapping) or set(evidence) != {"schema_version", "freeze_sha256", "commands"}
                or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1):
            raise ValueError("Requires schema-1 complete regression evidence")
        expected_freeze = readiness_freeze_fingerprint(freeze)
        if evidence["freeze_sha256"] != expected_freeze:
            errors.append("Regression evidence belongs to a different frozen candidate")
        expected = required_regression_commands()
        entries = evidence["commands"]
        if not isinstance(entries, dict) or set(entries) != set(expected):
            errors.append("Regression requires every AGENTS command exactly once")
        for name, (cwd, argv) in expected.items():
            reference = entries.get(name) if isinstance(entries, dict) else None
            command = _audit_execution_log(root, reference, root / cwd, argv, logs)
            commands[name] = command
            errors.extend(f"{name}: {reason}" for reason in command["errors"])
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    after = audit_readiness_freeze(root, freeze)
    if not after["passed"]:
        errors.extend(f"Final freeze: {error}" for error in after["errors"])
    for path, expected_sha in logs.items():
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
                errors.append(f"Execution log changed during validation: {path}")
        except OSError as error:
            errors.append(f"Cannot retain execution log: {error}")
    return {"passed": not errors, "release_certified": False, "errors": errors, "commands": commands,
            "scope": "Frozen-candidate regression-log consistency only; clean public snapshot, source/campaigns, "
                     "reference/transfer, visual packet and independent review remain separate requirements."}


def regression_ai_input_fingerprints(root: Path) -> dict[str, str]:
    """Bind the public/local AI checklist inputs without exporting chart bytes."""
    fingerprints = {}
    for name, season in (("public_ai", "2026"), ("local_ai", "1983")):
        directory = Path(root).resolve() / "seasons" / season
        teams = sorted(directory.glob("*/team.yaml"))
        if (directory.is_symlink() or len(teams) < 2 or len(teams) % 2
                or season == "1983" and len(teams) != 28
                or any(path.is_symlink() or path.parent.is_symlink() for path in teams)):
            raise ValueError(f"Incomplete or nonlocal {name} chart inventory")
        fingerprints[name] = chart_fingerprint(directory)
    return fingerprints


def audit_regression_outputs(root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Independently check the five actual checklist outputs against frozen inputs.

    AI receipts retain calls and legal final-state flags, not full box scores or
    loaded runtime identity. Actual execution logs and deterministic engine
    controls remain required. This starts no games and certifies no release.
    """
    from tests.ai_audit import SITUATION_CSV_FIELDS, validate_report

    from .chart_source_bundle import prepared_source_options

    root = Path(root).resolve()
    errors: list[str] = []
    bound: dict[Path, str] = {}
    checked_sources: list[tuple[Path, Path, Path]] = []
    ai_inputs: dict[str, str] | None = None
    local_csv_rows: list[dict] | None = None
    expected = {}
    for name, (_cwd, command) in required_regression_commands().items():
        for flag, suffix in (("--output", "json"), ("--csv", "csv")):
            if flag in command:
                expected[f"{name}_{suffix}"] = root / command[command.index(flag) + 1]
    artifacts: dict[str, dict] = {name: {"passed": False, "errors": []} for name in expected}

    def read(reference: object, original: Path | None = None) -> bytes:
        fields = {"path", "sha256"} | ({"original_path"} if original is not None else set())
        if (not isinstance(reference, dict) or set(reference) != fields
                or not isinstance(reference["path"], str) or not reference["path"]
                or not isinstance(reference["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])):
            raise ValueError("Requires an explicit output/receipt path and SHA-256 binding")
        if original is not None and reference["original_path"] != str(original):
            raise ValueError("Captured output substitutes a different command destination")
        path = (root / reference["path"]).resolve()
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != reference["sha256"]:
            raise ValueError("Output/receipt bytes differ from the bound SHA-256")
        bound[path] = reference["sha256"]
        return data

    before = audit_readiness_freeze(root, freeze)
    errors.extend(f"Initial freeze: {reason}" for reason in before["errors"])
    try:
        if (not isinstance(evidence, Mapping) or set(evidence) != {
                "schema_version", "freeze_sha256", "artifacts", "ai_inputs", "source_receipts",
        } or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1):
            raise ValueError("Requires schema-1 complete regression outputs")
        if evidence["freeze_sha256"] != readiness_freeze_fingerprint(freeze):
            errors.append("Regression outputs belong to a different frozen candidate")
        if not isinstance(evidence["artifacts"], dict) or set(evidence["artifacts"]) != set(expected):
            errors.append("Regression requires all five produced outputs exactly once")
        if not isinstance(evidence["source_receipts"], dict) or set(evidence["source_receipts"]) != {"1983", "2024"}:
            errors.append("Regression outputs require both actual source-preparation receipts")
        source_entries = evidence["source_receipts"] if isinstance(evidence["source_receipts"], dict) else {}
        try:
            ai_inputs = regression_ai_input_fingerprints(root)
            if evidence["ai_inputs"] != ai_inputs:
                errors.append("AI input fingerprints differ from the collected public/local charts")
        except (ValueError, TypeError, OSError, RuntimeError) as error:
            errors.append(f"AI inputs: {error}")
        entries = evidence["artifacts"] if isinstance(evidence["artifacts"], dict) else {}
        for label, original in expected.items():
            reasons = artifacts[label]["errors"]
            try:
                data = read(entries.get(label), original)
                if label == "local_ai_csv":
                    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
                    if reader.fieldnames != list(SITUATION_CSV_FIELDS) or list(reader) != local_csv_rows:
                        raise ValueError("Local AI CSV does not reconcile with every JSON situation row")
                elif label in {"public_ai_json", "local_ai_json"}:
                    report = _strict_json_object(data)
                    season = "2026" if label == "public_ai_json" else "1983"
                    teams = sorted(f"{season}/{path.parent.name}" for path in (root / "seasons" / season).glob("*/team.yaml"))
                    result = validate_report(report, teams)
                    artifacts[label].update(result)
                    reasons = artifacts[label]["errors"]
                    if label == "local_ai_json":
                        local_csv_rows = [{key: json.dumps(group[key], sort_keys=True) if isinstance(group[key], dict)
                                           else str(group[key]) for key in SITUATION_CSV_FIELDS}
                                          for group in report["summary"]["situations"]]
                else:
                    year = "1983" if label == "chart_1983_json" else "2024"
                    name = "1983-generated" if year == "1983" else "2024"
                    entry = freeze["cohorts"][name]
                    candidate = root / "seasons" / year
                    if chart_fingerprint(candidate) != entry["chart_fingerprint"]:
                        raise ValueError("Canonical candidate differs from the frozen charts")
                    contract_path = (root / entry["contract"]["path"]).resolve()
                    contract_data = read(entry["contract"])
                    if (root / f"config/chart-validation/{year}.json").read_bytes() != contract_data:
                        raise ValueError("Command's canonical contract differs from the frozen contract")
                    reference = source_entries.get(year)
                    receipt = root / f".ai-audits/chart-sources/{year}/source.json"
                    read(reference)
                    if (root / reference["path"]).resolve() != receipt:
                        raise ValueError("Source preparation substitutes the command's required receipt")
                    options = prepared_source_options(receipt, candidate, contract_path)
                    checked_sources.append((receipt, candidate, contract_path))
                    stored = _strict_json_object(data)
                    engine = stored["engine_evidence"]
                    if not isinstance(engine, dict) or not isinstance(engine.get("metadata"), dict):
                        raise ValueError("Chart output lacks engine policy/seed metadata")
                    metadata = engine["metadata"]
                    if (metadata.get("policy") != "chart-focused" or type(metadata.get("seed")) is not int
                            or metadata["seed"] != 20261108):
                        raise ValueError("Chart output substitutes a different policy or master seed")
                    checked = audit_release(candidate, _strict_json_object(contract_data), engine, **options)
                    if stored.get("release_certified") is not False:
                        reasons.append("Stored component report incorrectly claims certification")
                    for field in ("passed", "errors", "components"):
                        stored_json = json.dumps(stored.get(field), sort_keys=True, allow_nan=False)
                        checked_json = json.dumps(checked.get(field), sort_keys=True, allow_nan=False)
                        if stored_json != checked_json:
                            reasons.append(f"Stored {field} differs from independent component validation")
                    if checked.get("passed") is not True or checked.get("errors"):
                        reasons.extend(checked.get("errors") or ["Independent chart component validation failed"])
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, csv.Error) as error:
                reasons.append(str(error))
            artifacts[label]["passed"] = not reasons
            errors.extend(f"{label}: {reason}" for reason in reasons)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    after = audit_readiness_freeze(root, freeze)
    errors.extend(f"Final freeze: {reason}" for reason in after["errors"])
    for path, digest in bound.items():
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append(f"Regression output/receipt changed during validation: {path}")
        except OSError as error:
            errors.append(f"Regression output/receipt changed during validation: {error}")
    try:
        if ai_inputs is not None and regression_ai_input_fingerprints(root) != ai_inputs:
            errors.append("AI input charts changed during output validation")
        for receipt, candidate, contract_path in checked_sources:
            prepared_source_options(receipt, candidate, contract_path)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(f"Source/input recheck: {error}")
    return {"passed": not errors, "release_certified": False, "errors": errors, "artifacts": artifacts,
            "scope": "Actual regression-output consistency and independent AI/source/chart checks only; "
                     "execution logs, clean snapshot and complete charter acceptance remain required."}


def public_source_file_inventory(root: Path) -> dict[str, str]:
    """Discover tracked and new unignored working-tree bytes without exporting them."""
    root = Path(root).resolve()
    repository = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()
    if Path(repository).resolve() != root:
        raise ValueError("Public snapshot discovery requires the actual repository root")
    names = subprocess.check_output([
        "git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z",
    ]).decode().split("\0")
    files = {}
    for name in names:
        if not name:
            continue
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or relative.as_posix() != name:
            raise ValueError("Public inventory requires canonical repository-relative paths")
        if len(relative.parts) > 2 and relative.parts[0] == "seasons" and relative.parts[1] not in {"1983", "2024", "2026"}:
            raise ValueError("Public inventory contains an undeclared historical season")
        path = root / relative
        if path.is_symlink():
            raise ValueError("Public source inventory cannot contain symlinks")
        if not path.exists():
            continue  # A tracked working-tree deletion is part of the intended candidate.
        if not path.is_file():
            raise ValueError("Public source inventory requires regular files")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not files:
        raise ValueError("Public source inventory is empty")
    return files


def public_snapshot_file_inventory(directory: Path) -> dict[str, str]:
    """Inspect every snapshot source file, regardless of ignore rules.

    Test caches, coverage output and installed npm dependencies are generated
    artifacts. Other extra bytes and even empty nonpublic season directories fail.
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError("Public snapshot source directory is missing")
    files = {}

    def fail(error: OSError) -> None:
        raise error

    for current, directories, names in os.walk(directory, onerror=fail):
        parent = Path(current)
        for name in list(directories):
            path = parent / name
            relative = path.relative_to(directory)
            if path.is_symlink():
                raise ValueError("Public snapshot source cannot contain symlinks")
            if relative.parts[0] == "seasons" and len(relative.parts) >= 2 and relative.parts[1] not in {"1983", "2024", "2026"}:
                raise ValueError("Public snapshot contains a nonpublic season directory")
            if name in {"__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}:
                directories.remove(name)
        for name in names:
            path = parent / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Public snapshot source requires regular local files")
            if name == ".coverage" or name.startswith(".coverage."):
                continue
            files[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def audit_public_snapshot(root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Bind clean public source and complete unit logs to the frozen implementation."""
    root = Path(root).resolve()
    errors: list[str] = []
    commands: dict[str, dict] = {}
    logs: dict[Path, str] = {}
    before_files: dict[str, str] | None = None
    snapshot: Path | None = None
    before = audit_readiness_freeze(root, freeze)
    if not before["passed"]:
        errors.extend(f"Initial freeze: {error}" for error in before["errors"])
    try:
        if (not isinstance(evidence, Mapping) or set(evidence) != {
                "schema_version", "freeze_sha256", "snapshot_dir", "files", "commands",
        } or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1):
            raise ValueError("Requires schema-1 complete public snapshot evidence")
        expected_freeze = readiness_freeze_fingerprint(freeze)
        if evidence["freeze_sha256"] != expected_freeze:
            errors.append("Public snapshot belongs to a different freeze")
        raw_snapshot = root / evidence["snapshot_dir"]
        snapshot = raw_snapshot.resolve()
        if raw_snapshot.is_symlink() or not snapshot.is_relative_to(root / ".ai-audits"):
            raise ValueError("Public snapshot requires a local directory under ignored .ai-audits/")
        before_files = public_source_file_inventory(root)
        if evidence["files"] != before_files or public_snapshot_file_inventory(snapshot) != before_files:
            errors.append("Public snapshot/manifest differs from the complete intended working-tree bytes")
        if readiness_file_inventory(snapshot) != freeze["files"]:
            errors.append("Public snapshot implementation differs from the frozen code")
        for name, entry in freeze["cohorts"].items():
            if chart_fingerprint(snapshot / "seasons" / PUBLIC_SEASON_DIRECTORIES[name]) != entry["chart_fingerprint"]:
                errors.append(f"{name}: public snapshot uses a different chart candidate")
        required = {name: value for name, value in required_regression_commands().items() if name in {"core", "backend", "frontend"}}
        required["setup"] = ("paydirt-web/frontend", ["npm", "ci"])
        entries = evidence["commands"]
        if not isinstance(entries, dict) or set(entries) != set(required):
            errors.append("Public snapshot requires dependency setup and all three complete unit suites")
        for name, (cwd, argv) in required.items():
            reference = entries.get(name) if isinstance(entries, dict) else None
            command = _audit_execution_log(root, reference, snapshot / cwd, argv, logs, pythonpath=snapshot)
            commands[name] = command
            errors.extend(f"{name}: {reason}" for reason in command["errors"])
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        errors.append(str(error))
    try:
        if before_files is not None and public_source_file_inventory(root) != before_files:
            errors.append("Public working-tree files changed during validation")
        if before_files is not None and snapshot is not None and public_snapshot_file_inventory(snapshot) != before_files:
            errors.append("Public snapshot changed during validation")
        for path, sha in logs.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                errors.append("Clean execution log changed during validation")
    except (ValueError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        errors.append(str(error))
    after = audit_readiness_freeze(root, freeze)
    if not after["passed"]:
        errors.extend(f"Final freeze: {error}" for error in after["errors"])
    return {"passed": not errors, "release_certified": False, "errors": errors, "commands": commands,
            "file_count": len(before_files or {}),
            "scope": "Public working-tree/snapshot/unit-log consistency only; full regression, source/campaigns, "
                     "reference/transfer, visual packet and independent review remain required."}


def _components(
    season_dir: Path, contract: dict, engine_report: dict, *,
    stats_dir: Path | None = None, reproduced_dir: Path | None = None,
    input_files: Mapping[str, Path] | None = None,
) -> dict:
    def engine_evidence() -> dict:
        validation = validate_engine_report(engine_report, contract, season_dir, minimum_repetitions=64)
        conformance = audit_observer_conformance()
        errors = validation.get("errors", []) + conformance["errors"]
        return {**validation, "passed": validation["passed"] and conformance["passed"],
                "errors": errors, "measurement": conformance}

    def tactics() -> dict:
        errors, teams = [], {}
        global_controls = {}
        for name, check in (("priority", audit_priority_resolution),
                            ("strength", audit_generated_strength_order)):
            control = check()
            reasons = [finding.message for finding in control.findings]
            errors.extend(f"{name}: {reason}" for reason in reasons)
            global_controls[name] = {"passed": control.passed, "errors": reasons,
                                     "contrasts": control.contrasts}
        profile = contract.get("generation_profile", {})
        risk = audit_generated_offense_risk_order(EmpiricalPassCalibration(
            completion_rate_adjustment=profile.get("pass_completion_adjustment", 0),
            interception_rate_adjustment=profile.get("pass_interception_adjustment", 0),
            pressure_rate_adjustment=profile.get("pass_pressure_adjustment", 0),
            resolved_yard_multiplier=profile.get("pass_yard_multiplier", 1),
        ))
        risk_errors = [finding.message for finding in risk.findings]
        errors.extend(risk_errors)
        global_controls["offense_risk"] = {"passed": risk.passed, "errors": risk_errors,
                                           "contracts": risk.contracts}
        paths = sorted(season_dir.glob("*/defense.csv"))
        if not paths:
            errors.append("No defensive charts found")
        for path in paths:
            defense = parse_defense_csv(str(path))
            tactical = audit_defense_tactics(defense)
            engine = audit_engine_controls(defense)
            findings = tactical.findings + engine.findings
            errors.extend(f"{path.parent.name}: {finding.message}" for finding in findings)
            teams[path.parent.name] = {
                "passed": not findings, "contrasts": tactical.contrasts,
                "contracts": tactical.contracts,
                "diagnostics": [finding.message for finding in tactical.diagnostics],
                "engine_controls_passed": engine.passed,
            }
        mechanics = audit_season(season_dir)
        errors.extend(mechanics["errors"])
        exact = mechanics.get("exact_mechanics", {})
        if set(exact) != set(teams):
            errors.append("Incomplete exact mechanics team inventory")
        for team, evidence in exact.items():
            if len(evidence.get("plays", {})) != 54:
                errors.append(f"{team}: incomplete exact primary call inventory")
            for call, distribution in evidence.get("plays", {}).items():
                if distribution.get("exact_total_mass") != [1, 1]:
                    errors.append(f"{team} {call}: exact probability mass does not conserve")
        return {"passed": not errors, "errors": errors, "teams": teams,
                "global_controls": global_controls, "exact_mechanics": exact,
                "mechanics_warnings": mechanics["warnings"]}

    checks = {
        "source": lambda: audit_generated_source(
            season_dir, validation_contract=contract, stats_dir=stats_dir,
            reproduced_dir=reproduced_dir, input_files=input_files,
        ),
        "tactics": tactics,
        "allocation": audit_allocations,
        "engine": engine_evidence,
    }
    results = {}
    for name, check in checks.items():
        try:
            results[name] = check()
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
            results[name] = {"passed": False, "errors": [str(error)]}
    return results


def audit_release(
    season_dir: Path, contract: dict, engine_report: dict, *,
    stats_dir: Path | None = None, reproduced_dir: Path | None = None,
    input_files: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Require independently checked source inputs and all implemented components.

    This component gate does not certify the charter's complete readiness bundle.
    """
    source_options = {"stats_dir": stats_dir, "reproduced_dir": reproduced_dir,
                      "input_files": input_files}
    components = _components(Path(season_dir), contract, engine_report, **(
        source_options if any(value is not None for value in source_options.values()) else {}
    ))
    errors = []
    for name in ("source", "tactics", "allocation", "engine"):
        component = components.get(name)
        if (not isinstance(component, dict) or component.get("passed") is not True
                or component.get("errors")):
            reasons = component.get("errors", []) if isinstance(component, dict) else []
            errors.extend(f"{name}: {reason}" for reason in (reasons or ["Missing or failed evidence"]))
    source = components.get("source", {})
    checks = source.get("checks", {}) if isinstance(source, dict) else {}
    for required in ("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"):
        if not isinstance(checks, dict) or checks.get(required) is not True:
            errors.append(f"source: {required} must be independently verified")
    return {"passed": not errors, "release_certified": False,
            "errors": errors, "components": components,
            "engine_evidence": engine_report,
            "scope": "Component gate: source consistency, exact tactical controls, event allocation and "
                     "current-engine source-schedule calibration; historical tactical "
                     "accuracy and the full charter readiness bundle are not established by these controls."}


STATISTICAL_RELEASE_POLICY: dict[str, str] | None = {
    "commit": "5281b4fb6cdc3585be6aeb270ace7a1b2a5c1dc7",
    "path": "config/chart-validation/1977-release-exception.json",
    "sha256": "cf38dad7ae2b33b33c270076dee02834ad655109e74a0cef07859e919d4f9e36",
}

STATISTICAL_RELEASE_AUTHORIZATION = {
    "season": 1977,
    "commit": "e0b6bb6cd92344dbe490b103206809c26a8de632",
    "path": "docs/dev-notes/1977-calibration-release-goal.md",
    "sha256": "82289652789e82e07e23817e3a6f9c0e81b9bf53a6fdf5208bb1067b4e7df1ab",
}


def _exception_inventory(folder: Path) -> dict[str, str]:
    """Bind complete candidate bytes; reject redirected inputs."""
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Exception inputs require an actual directory")
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Exception inputs cannot contain symlinks")
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _exception_file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _statistical_failures(engine: dict) -> tuple[list[dict], list[str]]:
    """Extract only computed finite metric misses, preserving their exact bounds."""
    failures, messages = [], []
    groups = [("team", team, metrics) for team, metrics in engine["team_metrics"].items()]
    groups.append(("league", None, engine["metrics"]))
    for scope, team, metrics in groups:
        for name, metric in metrics.items():
            if metric["passed"] is True:
                continue
            observed, target, tolerance = (metric[key] for key in ("observed", "target", "tolerance"))
            if (not all(type(value) in (float, int) and math.isfinite(value)
                        for value in (observed, target, tolerance)) or tolerance <= 0):
                raise ValueError("Nonfinite or invalid fit metrics cannot receive an exception")
            failure = {"scope": scope, "metric": name, "observed": observed,
                       "target": target, "tolerance": tolerance}
            if team is not None:
                failure["team"] = team
            failures.append(failure)
            prefix = f"{team} {name}" if team is not None else name
            messages.append(f"{prefix}: {observed:.6f} differs from {target:.6f} by more than {tolerance}")
    return sorted(failures, key=lambda item: (item["scope"], item.get("team", ""), item["metric"])), messages


VERSION_ONLY_1977_RUNTIME = {
    "season": 1977,
    "commit": "a35153c26c8efbd07cd87d012e812520082e21e1",
    "report_fingerprint": "eb769742173e7a78a8ddfbff9218a178dd8943c15e6d76fd57ecd12e8ca4968f",
    "actual_fingerprint": "da5c7599f7c164a4697b6edabb57f14b3369021ac83383844a2236ed5ed7a7f3",
    "files": {
        "__init__.py": (
            "555dd9d5b9767366c0e7788c55a3abc0582dc6b74e869e246718caa9c5ec530f",
            "bbdbfd9d96853dfe7cdd44ae610ea5891db93ae9030dfc7cd1905de6aa2f3ffd",
        ),
        "__main__.py": (
            "c665cd4153432b45ec87102592c349cbe3582c1d5f43e292036be79cc632be40",
            "4e1d640bf22e5e0b4c666089c461e036682daacf413fd86bd0a440c041ca7f5e",
        ),
    },
}


def _version_only_1977_validation_view(
    root: Path, report: dict, season: int,
) -> tuple[dict, dict | None]:
    """Derive an explicit validation view after the caller pins raw report bytes.

    Only the reviewed 1.10.4 -> 1.10.5 metadata bytes may differ. This does not
    alter the original report, generic engine identity or any gameplay check.
    """
    actual = engine_fingerprint()
    metadata = report["metadata"]
    original = metadata.get("engine_fingerprint")
    if original == actual or original is None:
        return report, None  # Ordinary validation still rejects missing identity.
    pin = VERSION_ONLY_1977_RUNTIME
    if (season != pin["season"] or root != Path(__file__).resolve().parents[1]
            or original != pin["report_fingerprint"] or actual != pin["actual_fingerprint"]):
        raise ValueError("Runtime differs from exact reviewed 1977 version-only identities")
    runtime = loaded_runtime_identity()
    if (metadata.get("runtime_identity") != runtime
            or metadata.get("worker_runtime_identities") != [runtime] * metadata.get("repetitions", 0)):
        raise ValueError("Version-only allowance requires identical loaded runtime and workers")
    def git(*args: str) -> bytes:
        try:
            return subprocess.check_output(
                ["git", "--no-replace-objects", "-C", str(root), *args], stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("Missing immutable version-only runtime baseline") from exc
    def included(name: str) -> bool:
        path = Path(name)
        return path.suffix == ".py" and (
            not any(word in path.stem for word in ("audit", "gate")) or name == "chart_engine_audit.py"
        )
    names = {Path(name).name for name in git("ls-tree", "--name-only", pin["commit"] + ":paydirt").decode().splitlines()
             if included(name)}
    package = root / "paydirt"
    current = {path.name for path in package.glob("*.py") if included(path.name)}
    if current != names:
        raise ValueError("Version-only runtime source inventory differs")
    baseline_digest, actual_digest = hashlib.sha256(), hashlib.sha256()
    accepted = []
    for name in sorted(names):
        path = package / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Version-only runtime source must be a regular file")
        old = git("show", f"{pin['commit']}:paydirt/{name}")
        new = path.read_bytes()
        old_hash, new_hash = hashlib.sha256(old).hexdigest(), hashlib.sha256(new).hexdigest()
        for digest, data in ((baseline_digest, old), (actual_digest, new)):
            digest.update(name.encode() + b"\0" + data + b"\0")
        if name in pin["files"]:
            if (old_hash, new_hash) != pin["files"][name]:
                raise ValueError("Version-only metadata bytes differ from reviewed full-file hashes")
            accepted.append({"path": "paydirt/" + name, "baseline_sha256": old_hash, "actual_sha256": new_hash})
        elif old != new:
            raise ValueError("Unreviewed engine source change outside version metadata")
    if (baseline_digest.hexdigest() != original or actual_digest.hexdigest() != actual
            or set(pin["files"]) != {item["path"].split("/")[-1] for item in accepted}):
        raise ValueError("Version-only source proof contradicts complete engine fingerprints")
    receipt = {
        "scope": "Owner-approved exact 1.10.4 to 1.10.5 version metadata only; no gameplay waiver",
        "baseline_commit": pin["commit"], "report_engine_fingerprint": original,
        "actual_engine_fingerprint": actual, "loaded_runtime_identity": runtime,
        "source_files_verified": len(names), "unchanged_source_files": len(names) - len(accepted),
        "accepted_version_files": accepted,
        "validation_view": "Only metadata.engine_fingerprint derives from the verified actual source; raw report remains unchanged",
    }
    return {**report, "metadata": {**metadata, "engine_fingerprint": actual}}, receipt


def audit_statistical_release_exception(
    root: Path, season_dir: Path, contract_path: Path, engine_report_path: Path,
    policy_path: Path, *, public_dir: Path, stats_dir: Path,
    reproduced_dir: Path, input_files: Mapping[str, Path],
) -> dict[str, Any]:
    """Accept only the owner's exact, committed 1977 statistical release exception.

    Source, reproduction, mechanics, allocation, observer conformance, runtime,
    accounting and minimum samples are independently checked. Failed statistical
    bounds stay failed; this component never certifies a complete release.
    """
    import gzip

    errors: list[str] = []
    result: dict[str, Any] = {
        "passed": False, "strict_fit_passed": False, "release_certified": False,
        "release_accepted_with_statistical_exceptions": False,
        "accepted_failures": [], "errors": errors,
        "scope": "Exact owner-authorized statistical acceptance; no source, gameplay or native-install waiver",
    }
    root = Path(root).resolve()
    try:
        authority = STATISTICAL_RELEASE_AUTHORIZATION
        policy_bytes = Path(policy_path).read_bytes()
        relative = Path(policy_path).resolve().relative_to(root).as_posix()
        def git_object(reference: str) -> bytes:
            return subprocess.check_output(
                ["git", "--no-replace-objects", "-C", str(root), "show", reference],
                stderr=subprocess.PIPE,
            )
        trusted_policy = STATISTICAL_RELEASE_POLICY
        if (not trusted_policy or relative != trusted_policy["path"]
                or hashlib.sha256(policy_bytes).hexdigest() != trusted_policy["sha256"]
                or git_object(f"{trusted_policy['commit']}:{trusted_policy['path']}") != policy_bytes):
            raise ValueError("Statistical exception policy must match the immutable reviewed policy pin")
        authorization = git_object(f"{authority['commit']}:{authority['path']}")
        if hashlib.sha256(authorization).hexdigest() != authority["sha256"]:
            raise ValueError("Immutable owner authorization differs from the trusted record")
        policy = _strict_json_object(policy_bytes)
        if (type(policy.get("schema_version")) is not int or policy["schema_version"] != 1
                or type(policy.get("season")) is not int or policy["season"] != authority["season"]
                or policy.get("authorization_commit") != authority["commit"]
                or policy.get("authorization_sha256") != authority["sha256"]
                or not isinstance(policy.get("reason"), str) or not policy["reason"].strip()):
            raise ValueError("Policy does not match the specific owner-authorized season and reason")
        contract_bytes = Path(contract_path).read_bytes()
        report_file_digest = _exception_file_digest(Path(engine_report_path))
        raw_report = (gzip.decompress(Path(engine_report_path).read_bytes())
                      if Path(engine_report_path).suffix == ".gz" else Path(engine_report_path).read_bytes())
        if (hashlib.sha256(contract_bytes).hexdigest() != policy["contract_sha256"]
                or hashlib.sha256(raw_report).hexdigest() != policy["engine_report_sha256"]):
            raise ValueError("Contract or raw execution report differs from the accepted identity")
        contract, report = _strict_json_object(contract_bytes), _strict_json_object(raw_report)
        validation_report, version_receipt = _version_only_1977_validation_view(root, report, contract.get("season"))
        if version_receipt is not None:
            result["runtime_version_equivalence"] = version_receipt
        del raw_report
        if contract.get("season") != authority["season"] or report["metadata"].get("policy") != "chart-focused":
            raise ValueError("Exception requires the exact source season and chart-focused measurement")
        before_stats = _exception_inventory(Path(stats_dir))
        before_reproduced = _exception_inventory(Path(reproduced_dir))
        before_inputs = {name: _exception_file_digest(Path(path)) for name, path in input_files.items()}
        before_canonical = _exception_inventory(Path(season_dir))
        before_public = _exception_inventory(Path(public_dir))
        if before_canonical != policy["canonical_files"] or before_public != policy["public_files"]:
            raise ValueError("Canonical or published inventory differs from the accepted bytes")
        canonical_manifest = Path(season_dir) / "generation-manifest.json"
        published = _strict_json_object((Path(public_dir) / "generation-manifest.json").read_bytes())
        manifest = _strict_json_object(canonical_manifest.read_bytes())
        public_keys = {
            "accuracy_bounds_passed", "calibration_profile", "chart_hashes", "empirical_outcomes",
            "field_goal_attempts", "fumble_fitting_summary", "fumble_gain_policy", "fumbles", "games",
            "gain_normalization_summary", "historical_source_complete", "known_accuracy_exceptions",
            "diagnostic_limitations", "local_source_reproduction", "modeled_fumble_assumptions",
            "opponent_adjustment", "original_generation_manifest_sha256", "post_generation_transforms",
            "public_manifest_schema_version", "reviewed_source_summary", "scope", "season", "seed",
            "source", "source_feature_coverage", "source_rows", "teams",
        }
        if set(published) - public_keys:
            raise ValueError("Public manifest contains unapproved/private provenance fields")
        public_team_keys = {
            "empirical_outcomes", "fallback_columns", "field_goal_attempts", "fumbles",
            "generated_empirical_outcomes", "opponent_adjusted_outcomes", "pfr_team",
            "source_event_counts",
        }
        public_teams = published.get("teams", {})
        if not isinstance(public_teams, dict):
            raise TypeError("Public team inventory must be an object")
        canonical_teams = manifest.get("teams", {})
        if not isinstance(canonical_teams, dict) or any(not isinstance(team, dict) for team in canonical_teams.values()):
            raise TypeError("Canonical team inventory must contain objects")
        canonical_public_teams = {
            name: {key: value for key, value in team.items() if key in public_team_keys}
            for name, team in canonical_teams.items()
        }
        if public_teams != canonical_public_teams:
            raise ValueError("Public team source counts differ from the canonical manifest")
        for key in ("empirical_outcomes", "field_goal_attempts", "fumble_gain_policy", "fumbles",
                    "games", "modeled_fumble_assumptions", "opponent_adjustment", "seed", "source",
                    "source_feature_coverage", "source_rows"):
            if published.get(key) != manifest.get(key):
                raise ValueError(f"Public source summary differs from canonical generation: {key}")
        for team in public_teams.values():
            if not isinstance(team, dict) or set(team) - public_team_keys:
                raise ValueError("Public team metadata contains unapproved/private provenance fields")
            for key, value in team.items():
                if key == "pfr_team":
                    if not isinstance(value, str) or not value.isalpha() or len(value) > 4:
                        raise ValueError("Public source team identifier is invalid")
                elif key == "source_event_counts":
                    if (not isinstance(value, dict)
                            or set(value) - {"field_goal_attempts", "interceptions", "sacks"}
                            or any(type(count) is not int or count < 0 for count in value.values())):
                        raise ValueError("Public source event counts are invalid")
                elif type(value) is not int or value < 0:
                    raise ValueError("Public team aggregate must be a nonnegative integer")
        if (published.get("original_generation_manifest_sha256") != hashlib.sha256(canonical_manifest.read_bytes()).hexdigest()
                or published.get("calibration_profile") != manifest.get("calibration_profile")
                or published.get("season") != authority["season"]
                or published.get("public_manifest_schema_version") != 1):
            raise ValueError("Sanitized public provenance does not bind the exact canonical manifest/profile")
        actual_chart_hashes = {name: digest for name, digest in before_public.items()
                               if len(Path(name).parts) == 2 and name.endswith(".csv")}
        if published.get("chart_hashes") != actual_chart_hashes:
            raise ValueError("Public chart hash provenance differs from actual published CSV bytes")
        required_public = set(before_canonical) - {"generation-manifest.json", "NOTES.md", "chart-audit.json"}
        if not required_public <= set(before_public):
            raise ValueError("Published season omits canonical gameplay files")
        for name, digest in before_public.items():
            if name in ("generation-manifest.json", "NOTES.md"):
                continue
            parts = Path(name).parts
            allowed = name in (f"{authority['season']}.yaml", "ai_behavior.yaml") or (
                len(parts) == 2 and parts[1] in {"offense.csv", "defense.csv", "special.csv", "team.yaml", "roster.json"}
            )
            if not allowed:
                raise ValueError(f"Unexpected published source artifact: {name}")
            if before_canonical.get(name) != digest:
                raise ValueError(f"Published chart or metadata differs from canonical generation: {name}")
        component = audit_release(Path(season_dir), contract, validation_report, stats_dir=stats_dir,
                                  reproduced_dir=reproduced_dir, input_files=input_files)["components"]
        for name in ("source", "tactics", "allocation"):
            if component[name].get("passed") is not True or component[name].get("errors"):
                errors.append(f"Nonstatistical {name} requirement failed")
        for check in ("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"):
            if component["source"].get("checks", {}).get(check) is not True:
                errors.append(f"Source {check} is not independently verified")
        nonfit = validate_engine_report(validation_report, contract, Path(season_dir), minimum_team_games=1000,
                                        minimum_repetitions=72, require_fit=False)
        if nonfit.get("passed") is not True or nonfit.get("errors"):
            errors.extend(nonfit.get("errors") or ["Nonstatistical engine validation failed"])
        engine = component["engine"]
        measurement = engine.get("measurement", {})
        if measurement.get("passed") is not True or measurement.get("errors"):
            errors.append("Observer conformance failed")
        failures, expected_errors = _statistical_failures(engine)
        if engine.get("passed") is not (not expected_errors):
            errors.append("Strict engine summary contradicts its measured failures")
        if sorted(engine["errors"]) != sorted(expected_errors):
            errors.append("Strict engine errors include unaccepted nonstatistical failures")
        accepted = sorted(policy["accepted_failures"], key=lambda item: (item["scope"], item.get("team", ""), item["metric"]))
        if failures != accepted:
            errors.append("Accepted statistical misses do not exactly match independently measured failures")
        if (published.get("accuracy_bounds_passed") is not engine["passed"]
                or published.get("known_accuracy_exceptions") != failures):
            errors.append("Published accuracy disclosure contradicts independently measured failures")
        if (_exception_inventory(Path(stats_dir)) != before_stats
                or _exception_inventory(Path(reproduced_dir)) != before_reproduced
                or {name: _exception_file_digest(Path(path)) for name, path in input_files.items()} != before_inputs
                or _exception_inventory(Path(season_dir)) != before_canonical
                or _exception_inventory(Path(public_dir)) != before_public
                or Path(policy_path).read_bytes() != policy_bytes
                or Path(contract_path).read_bytes() != contract_bytes
                or _exception_file_digest(Path(engine_report_path)) != report_file_digest):
            errors.append("Bound inputs changed during acceptance")
        if version_receipt is not None:
            _, final_version_receipt = _version_only_1977_validation_view(root, report, contract.get("season"))
            if final_version_receipt != version_receipt:
                errors.append("Version-only source proof changed during acceptance")
        result.update(strict_fit_passed=engine["passed"], accepted_failures=failures,
                      statistical_validation={key: engine[key] for key in ("errors", "metrics", "team_metrics")},
                      authorization_commit=authority["commit"], policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
                      components={name: {"passed": component[name]["passed"], "errors": component[name]["errors"]}
                                  for name in ("source", "tactics", "allocation")})
        result["passed"] = not errors
        result["release_accepted_with_statistical_exceptions"] = not errors and bool(failures)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        errors.append(str(exc))
    return result


def audit_campaign_bundle(cohorts: Mapping[str, Any]) -> dict[str, Any]:
    """Require every charter campaign, with its own phase, policy and exposure.

    Source, exact mechanics, frozen artifact inventory, reference/transfer,
    regression and independent review remain separate readiness requirements.
    This validates supplied reports; it never opens a reserved seed campaign.
    """
    errors: list[str] = []
    results: dict[str, dict[str, Any]] = {}
    expected = {"1983-generated": (1983, 28), "2024": (2024, 32)}
    families = {
        "training": ("chart-focused", 20261108, 64, 1000, True),
        "held_out": ("chart-focused", 20361108, 64, 1000, True),
        "hard": ("hard", 20261108, 8, 128, False),
        "balanced": ("balanced", 20261108, 8, 128, False),
        "run-heavy": ("run-heavy", 20261108, 1, 16, False),
        "pass-heavy": ("pass-heavy", 20261108, 1, 16, False),
    }
    for policy in (
        "repeat-line-plunge", "repeat-off-tackle", "repeat-end-run", "repeat-draw",
        "repeat-screen", "repeat-short-pass", "repeat-medium-pass", "repeat-long-pass",
        "repeat-te-short-long",
    ):
        families[policy] = (policy, 20261108, 1, 16, False)
    if not isinstance(cohorts, Mapping):
        return {"passed": False, "release_certified": False, "cohorts": {},
                "errors": ["Missing campaign cohort inventory"]}
    for name in set(cohorts) - set(expected):
        errors.append(f"Unexpected campaign cohort: {name}")
    for name, (season, count) in expected.items():
        data = cohorts.get(name)
        if not isinstance(data, Mapping):
            errors.append(f"{name}: missing campaign cohort")
            continue
        results[name] = {}
        contract = data.get("contract")
        if (not isinstance(contract, dict) or contract.get("season") != season
                or not isinstance(contract.get("teams"), dict)
                or len(contract["teams"]) != count):
            errors.append(f"{name}: incomplete or substituted source cohort")
            continue
        directory = data.get("season_dir")
        if not isinstance(directory, (str, Path)) or not str(directory):
            errors.append(f"{name}: missing candidate directory")
            continue
        policies = data.get("policies", {})
        for family, (policy, seed, repetitions, team_games, fit) in families.items():
            report = (data.get(family) if family in {"training", "held_out"}
                      else policies.get(family) if isinstance(policies, Mapping) else None)
            metadata = report.get("metadata") if isinstance(report, dict) else None
            if (not isinstance(metadata, dict) or metadata.get("policy") != policy
                    or type(metadata.get("seed")) is not int or metadata["seed"] != seed):
                validation = {"passed": False, "errors": [
                    f"Missing or substituted campaign; requires {policy}, master {seed}",
                ]}
            else:
                try:
                    validation = validate_engine_report(
                        report, contract, Path(directory), minimum_repetitions=repetitions,
                        minimum_team_games=team_games, require_fit=fit,
                    )
                except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
                    validation = {"passed": False, "errors": [str(error)]}
            if not isinstance(validation, dict):
                validation = {"passed": False, "errors": ["Invalid validation result"]}
            reasons = validation.get("errors")
            if not isinstance(reasons, list):
                reasons = ["Missing validation error inventory"]
            if validation.get("passed") is not True or reasons:
                errors.extend(f"{name} {family}: {reason}" for reason in (
                    reasons or ["Missing or failed campaign evidence"]
                ))
            results[name][family] = validation
    return {
        "passed": not errors, "release_certified": False, "errors": errors,
        "cohorts": results,
        "scope": "Campaign census only: training, held-out and policy exposure/accounting/fit. "
                 "Source, exact mechanics, freeze, reference/transfer, regression, visual packet "
                 "and independent review still determine full charter readiness.",
    }


class _BoundReports(Mapping[str, Any]):
    """Load one campaign at a time instead of retaining all thirty large reports."""

    def __init__(
        self, references: Mapping[str, Any], loader: Callable[[Any, str], Any], prefix: str,
    ) -> None:
        self.references, self.loader, self.prefix = references, loader, prefix

    def __getitem__(self, key: str) -> Any:
        return self.loader(self.references[key], f"{self.prefix} {key}")

    def __iter__(self) -> Iterator[str]:
        return iter(self.references)

    def __len__(self) -> int:
        return len(self.references)

    def __contains__(self, key: object) -> bool:
        return key in self.references


def audit_campaign_bundle_file(bundle_path: Path) -> dict[str, Any]:
    """Verify actual campaign artifacts, then delegate their semantics to the census.

    This component neither starts campaigns nor certifies complete charter readiness.
    """
    errors: list[str] = []
    verified = 0
    path = Path(bundle_path).resolve()
    before_engine: str | None = None
    try:
        before_engine = engine_fingerprint()
    except (ValueError, TypeError, OSError, RuntimeError) as error:
        errors.append(f"Cannot verify loaded runtime: {error}")
    directories: dict[str, tuple[Path, str]] = {}
    input_paths: set[str] = set()
    candidate_paths: set[str] = set()

    def note_reference(reference: Any) -> None:
        if isinstance(reference, dict) and isinstance(reference.get("path"), str) and reference["path"]:
            input_paths.add(str((path.parent / reference["path"]).resolve()))

    def load(reference: Any, label: str) -> dict | None:
        nonlocal verified
        try:
            if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
                    or not isinstance(reference["path"], str) or not reference["path"]
                    or not isinstance(reference["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])):
                raise ValueError("Requires an explicit path and SHA-256 binding")
            data = (path.parent / reference["path"]).resolve().read_bytes()
            if hashlib.sha256(data).hexdigest() != reference["sha256"]:
                raise ValueError("Artifact bytes differ from declared SHA-256")
            result = _strict_json_object(data)
            verified += 1
            return result
        except (ValueError, TypeError, OSError) as error:
            errors.append(f"{label}: {error}")
            return None

    cohorts: dict[str, Any] = {}
    try:
        bundle = _strict_json_object(path.read_bytes())
        if (set(bundle) != {"schema_version", "cohorts"}
                or type(bundle.get("schema_version")) is not int
                or bundle["schema_version"] != 1
                or not isinstance(bundle.get("cohorts"), dict)):
            raise ValueError("Requires schema-1 campaign cohort inventory")
        expected = {"1983-generated", "2024"}
        if set(bundle["cohorts"]) != expected:
            errors.append("Campaign file requires exactly the two declared source cohorts")
        # Preserve named inputs even when a cohort entry later fails its schema.
        for entry in bundle["cohorts"].values():
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("season_dir"), str) and entry["season_dir"]:
                candidate_paths.add(str((path.parent / entry["season_dir"]).resolve()))
            for key in ("contract", "training", "held_out"):
                note_reference(entry.get(key))
            if isinstance(entry.get("policies"), dict):
                for reference in entry["policies"].values():
                    note_reference(reference)
        policies = {"hard", "balanced", "run-heavy", "pass-heavy", "repeat-line-plunge",
                    "repeat-off-tackle", "repeat-end-run", "repeat-draw", "repeat-screen",
                    "repeat-short-pass", "repeat-medium-pass", "repeat-long-pass", "repeat-te-short-long"}
        for name in sorted(expected & set(bundle["cohorts"])):
            entry = bundle["cohorts"][name]
            if (not isinstance(entry, dict) or set(entry) != {
                    "season_dir", "chart_fingerprint", "contract", "training", "held_out", "policies",
            } or not isinstance(entry.get("season_dir"), str) or not entry["season_dir"]
                    or not isinstance(entry.get("policies"), dict)):
                errors.append(f"{name}: incomplete or unexpected campaign entry")
                continue
            directory = (path.parent / entry["season_dir"]).resolve()
            fingerprint = chart_fingerprint(directory) if directory.is_dir() else None
            if fingerprint is None or fingerprint != entry["chart_fingerprint"]:
                errors.append(f"{name}: candidate chart fingerprint differs or directory is missing")
            else:
                directories[name] = directory, fingerprint
            if set(entry["policies"]) != policies:
                errors.append(f"{name}: incomplete or unexpected policy inventory")
            cohorts[name] = ChainMap(
                _BoundReports({key: entry[key] for key in ("training", "held_out")}, load, name),
                {"season_dir": directory, "contract": load(entry["contract"], f"{name} contract"),
                 "policies": _BoundReports(entry["policies"], load, name)},
            )
    except (ValueError, TypeError, OSError) as error:
        errors.append(f"Campaign bundle: {error}")
    census = audit_campaign_bundle(cohorts)
    try:
        if before_engine != engine_fingerprint():
            errors.append("Engine changed during campaign bundle validation")
        for name, (directory, fingerprint) in directories.items():
            if chart_fingerprint(directory) != fingerprint:
                errors.append(f"{name}: candidate changed during campaign bundle validation")
    except (ValueError, TypeError, OSError, RuntimeError) as error:
        errors.append(f"Cannot verify final campaign identities: {error}")
    binding_errors = list(errors)
    errors.extend(census["errors"])
    return {"passed": not errors, "release_certified": False, "errors": errors,
            "binding": {"passed": not binding_errors, "errors": binding_errors,
                        "artifacts_verified": verified, "input_paths": sorted(input_paths),
                        "candidate_paths": sorted(candidate_paths)}, "census": census,
            "scope": "Bound campaign census only; full charter readiness is not established."}


def _visual_artifact(root: Path, reference: object, artifacts: dict[Path, str]) -> bytes:
    """Read a bound local capture artifact and retain its digest for rechecking."""
    if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
            or not isinstance(reference["path"], str)
            or not isinstance(reference["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])):
        raise ValueError("Visual artifact requires an exact path/SHA-256 binding")
    relative = Path(reference["path"])
    if (relative.is_absolute() or ".." in relative.parts or "\\" in reference["path"]
            or relative.as_posix() != reference["path"] or relative.parts[:1] != (".ai-audits",)):
        raise ValueError("Visual artifacts require canonical local paths under ignored .ai-audits/")
    path = root / relative
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root):
        raise ValueError(f"Visual artifact cannot use symlinks: {relative}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != reference["sha256"]:
        raise ValueError(f"Visual artifact differs from bound SHA-256: {relative}")
    if path in artifacts and artifacts[path] != digest:
        raise ValueError(f"Visual artifact has contradictory bindings: {relative}")
    artifacts[path] = digest
    return data


def _visual_png(data: bytes, width: int, height: int) -> None:
    """Check complete, noninterlaced RGB/RGBA browser PNG dimensions and scanlines."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Screenshot is not a PNG")
    position = 8
    compressed = bytearray()
    channels = 0
    ended = False
    while position + 12 <= len(data):
        size = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        end = position + 12 + size
        if end > len(data):
            raise ValueError("Screenshot has a truncated PNG chunk")
        payload = data[position + 8:end - 4]
        checksum = struct.unpack(">I", data[end - 4:end])[0]
        if zlib.crc32(kind + payload) != checksum:
            raise ValueError("Screenshot has an invalid PNG checksum")
        if position == 8:
            if kind != b"IHDR" or size != 13:
                raise ValueError("Screenshot lacks the PNG image header")
            actual_width, actual_height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if ((actual_width, actual_height) != (width, height) or depth != 8
                    or color not in {2, 6} or (compression, filtering, interlace) != (0, 0, 0)):
                raise ValueError("Screenshot dimensions or encoding differ from the browser viewport")
            channels = 3 if color == 2 else 4
        elif kind == b"IHDR":
            raise ValueError("Screenshot has a duplicate PNG image header")
        if kind == b"IDAT":
            compressed.extend(payload)
        if kind == b"IEND":
            if size or end != len(data):
                raise ValueError("Screenshot has invalid PNG termination")
            ended = True
            break
        position = end
    if not ended or not compressed:
        raise ValueError("Screenshot lacks complete PNG image data")
    stride = 1 + width * channels
    expected = stride * height
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(bytes(compressed), expected + 1)
    if (len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or any(pixels[offset] > 4 for offset in range(0, expected, stride))):
        raise ValueError("Screenshot PNG scanlines are incomplete or invalid")


def _visual_table(table: object, name: str, viewport: Mapping[str, int]) -> None:
    """Check ordered row coverage and browser-reported visible table geometry."""
    fields = {"row_keys", "left", "top", "right", "bottom",
              "scroll_width", "client_width", "scroll_height", "client_height"}
    if not isinstance(table, dict) or set(table) != fields:
        raise ValueError(f"{name}: requires complete table layout measurements")
    expected = ([f"{letter}{sub}" for letter in "ABCDEF" for sub in range(1, 6)]
                if name == "defense" else [str(roll) for roll in range(10, 40)])
    if table["row_keys"] != expected:
        raise ValueError(f"{name}: requires all thirty ordered chart rows")
    for field in fields - {"row_keys"}:
        value = table[field]
        if type(value) not in {int, float} or not math.isfinite(value):
            raise ValueError(f"{name}: layout measurements must be finite numbers")
    if (not 0 <= table["left"] < table["right"] <= viewport["width"]
            or not 0 <= table["top"] < table["bottom"] <= viewport["height"]
            or not 0 < table["scroll_width"] <= table["client_width"]
            or not 0 < table["scroll_height"] <= table["client_height"]):
        raise ValueError(f"{name}: chart rows are clipped or require internal scrolling")


def audit_visual_capture_evidence(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate trusted local captures, without certifying selection or chart contents.

    Receipts record browser observations; hashes and PNG validation establish local
    consistency, not hostile-host attestation. Candidate/API/DOM cell comparisons,
    the charter's selection criteria and independent visual review remain separate.
    """
    root = Path(root).resolve()
    errors: list[str] = []
    artifacts: dict[Path, str] = {}
    contexts: list[object] = []
    sections_checked = 0
    before = audit_readiness_freeze(root, freeze)
    errors.extend(f"Initial freeze: {error}" for error in before["errors"])
    try:
        if (not isinstance(evidence, Mapping)
                or set(evidence) != {"schema_version", "freeze_sha256", "contexts"}
                or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1):
            raise ValueError("Requires schema-1 complete visual-capture evidence")
        freeze_sha = readiness_freeze_fingerprint(freeze)
        if evidence["freeze_sha256"] != freeze_sha:
            errors.append("Visual captures belong to a different freeze")
        contexts = evidence["contexts"]
        if not isinstance(contexts, list) or not contexts:
            raise ValueError("Visual captures require selected contexts from both public cohorts")
        seen: set[tuple[str, str]] = set()
        cohorts: set[str] = set()
        for index, context in enumerate(contexts):
            try:
                if not isinstance(context, dict) or set(context) != {"cohort", "team", "capture"}:
                    raise ValueError("Requires exact cohort/team/capture context")
                cohort, team = context["cohort"], context["team"]
                if not isinstance(cohort, str) or not isinstance(team, str) or cohort not in freeze["cohorts"]:
                    raise ValueError("Visual context has an unknown cohort or invalid team")
                identity = (cohort, team)
                if identity in seen:
                    raise ValueError("Duplicate visual context")
                seen.add(identity)
                cohorts.add(cohort)
                entry = freeze["cohorts"][cohort]
                contract = _strict_json_object((root / entry["contract"]["path"]).read_bytes())
                if team not in contract["teams"]:
                    raise ValueError("Visual team is absent from the frozen public contract")
                receipt = _strict_json_object(_visual_artifact(root, context["capture"], artifacts))
                fields = {"schema_version", "freeze_sha256", "engine_fingerprint", "cohort", "team",
                          "chart_fingerprint", "viewport", "browser_errors", "state_before", "state_after", "sections"}
                if (set(receipt) != fields or type(receipt["schema_version"]) is not int
                        or receipt["schema_version"] != 1):
                    raise ValueError("Requires schema-1 complete browser capture receipt")
                if (receipt["freeze_sha256"] != freeze_sha or receipt["engine_fingerprint"] != freeze["engine_fingerprint"]
                        or receipt["chart_fingerprint"] != entry["chart_fingerprint"]
                        or (receipt["cohort"], receipt["team"]) != identity):
                    raise ValueError("Browser receipt identity, runtime or candidate differs from the freeze")
                viewport = receipt["viewport"]
                if (not isinstance(viewport, dict) or set(viewport) != {"width", "height"}
                        or any(type(value) is not int or value <= 0 for value in viewport.values())):
                    raise ValueError("Browser viewport requires positive integer dimensions")
                if receipt["browser_errors"] != []:
                    raise ValueError("Browser capture has errors or lacks the error record")
                state_before = _strict_json_object(_visual_artifact(root, receipt["state_before"], artifacts))
                state_after = _strict_json_object(_visual_artifact(root, receipt["state_after"], artifacts))
                if not state_before or state_before != state_after:
                    raise ValueError("Chart browsing changed game state or lacks state evidence")
                sections = receipt["sections"]
                if not isinstance(sections, dict) or set(sections) != {"offense", "defense", "special_teams"}:
                    raise ValueError("Browser capture requires every chart view exactly once")
                location = None
                for view, section in sections.items():
                    if not isinstance(section, dict) or set(section) != {"url", "http_status", "screenshot", "tables"}:
                        raise ValueError(f"{view}: requires complete screenshot and browser observations")
                    if type(section["http_status"]) is not int or section["http_status"] != 200:
                        raise ValueError(f"{view}: preview did not return HTTP 200")
                    if not isinstance(section["url"], str):
                        raise TypeError(f"{view}: preview URL must be text")
                    parsed = urlsplit(section["url"])
                    query = parse_qs(parsed.query, keep_blank_values=True)
                    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                            or parsed.username or parsed.password or parsed.fragment or parsed.path != "/"
                            or set(query) != {"charts", "side", "view"}
                            or any(len(values) != 1 for values in query.values())
                            or not query["charts"][0] or query["side"][0] not in {"home", "away"}
                            or query["view"] != [view]):
                        raise ValueError(f"{view}: requires a local chart-preview URL with the correct view")
                    current = (parsed.netloc, query["charts"][0], query["side"][0])
                    if location is not None and current != location:
                        raise ValueError("Chart views refer to different games, sides or preview services")
                    location = current
                    names = {view, "special_plays"} if view == "offense" else {view}
                    tables = section["tables"]
                    if not isinstance(tables, dict) or set(tables) != names:
                        raise ValueError(f"{view}: capture omits a required table or adds an unrelated table")
                    for name, table in tables.items():
                        _visual_table(table, name, viewport)
                    if view == "offense":
                        main, auxiliary = tables["offense"], tables["special_plays"]
                        if (max(main["left"], auxiliary["left"]) < min(main["right"], auxiliary["right"])
                                and max(main["top"], auxiliary["top"]) < min(main["bottom"], auxiliary["bottom"])):
                            raise ValueError("Offense and auxiliary chart tables overlap")
                    _visual_png(_visual_artifact(root, section["screenshot"], artifacts), viewport["width"], viewport["height"])
                    sections_checked += 1
                selected_team = state_before.get(location[2] + "_team")
                if (state_before.get("game_id") != location[1] or not isinstance(selected_team, dict)
                        or selected_team.get("id") != team):
                    raise ValueError("State evidence belongs to a different game, side or team")
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, struct.error, zlib.error) as error:
                errors.append(f"Context {index}: {error}")
        if cohorts != set(freeze["cohorts"]):
            errors.append("Visual captures must cover both complete public-cohort identities")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    for path, digest in artifacts.items():
        try:
            reference = {"path": path.relative_to(root).as_posix(), "sha256": digest}
            _visual_artifact(root, reference, {})
        except (ValueError, TypeError, OSError, RuntimeError) as error:
            errors.append(f"Final capture artifact: {error}")
    after = audit_readiness_freeze(root, freeze)
    errors.extend(f"Final freeze: {error}" for error in after["errors"])
    return {"passed": not errors, "release_certified": False, "errors": errors,
            "context_count": len(contexts) if isinstance(contexts, list) else 0, "section_count": sections_checked,
            "selection_validated": False, "candidate_content_validated": False,
            "scope": "Trusted local capture consistency only; candidate/API/DOM cell comparison, charter team selection, "
                     "independent visual review and full readiness remain required."}


def audit_visual_content_evidence(
    root: Path, freeze: Mapping[str, Any], captures: Mapping[str, Any], evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind candidate/API/DOM correspondence to complete captures at the same freeze."""
    from .chart_loader import load_team_chart
    from .chart_preview_audit import compare_preview_book, compare_preview_dom

    root = Path(root).resolve()
    errors: list[str] = []
    artifacts: dict[Path, str] = {}
    tables_checked = cells_checked = 0
    initial = audit_visual_capture_evidence(root, freeze, captures)
    errors.extend(f"Initial capture: {reason}" for reason in initial["errors"])
    try:
        if (not isinstance(evidence, Mapping) or set(evidence) != {
                "schema_version", "freeze_sha256", "captures_sha256", "contexts",
        } or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1):
            raise ValueError("Requires schema-1 complete visual-content evidence")
        if (evidence["freeze_sha256"] != readiness_freeze_fingerprint(freeze)
                or evidence["captures_sha256"] != readiness_freeze_fingerprint(captures)):
            errors.append("Visual content belongs to a different freeze or capture manifest")
        contexts = evidence["contexts"]
        if not isinstance(contexts, list) or not contexts:
            raise ValueError("Visual content requires every selected capture context")
        capture_contexts = {(entry["cohort"], entry["team"]): entry for entry in captures["contexts"]}
        seen: set[tuple[str, str]] = set()
        for index, context in enumerate(contexts):
            try:
                if not isinstance(context, dict) or set(context) != {"cohort", "team", "api_book", "views"}:
                    raise ValueError("Requires exact cohort/team/API/DOM content context")
                cohort, team_id = context["cohort"], context["team"]
                if not isinstance(cohort, str) or not isinstance(team_id, str):
                    raise TypeError("Content context identities must be text")
                identity = (cohort, team_id)
                if identity in seen or identity not in capture_contexts:
                    raise ValueError("Duplicate or unselected visual-content context")
                seen.add(identity)
                capture = capture_contexts[identity]
                receipt = _strict_json_object(_visual_artifact(root, capture["capture"], artifacts))
                state = _strict_json_object(_visual_artifact(root, receipt["state_before"], artifacts))
                query = parse_qs(urlsplit(receipt["sections"]["offense"]["url"]).query)
                selected = state[query["side"][0] + "_team"]
                entry = freeze["cohorts"][cohort]
                contract = _strict_json_object((root / entry["contract"]["path"]).read_bytes())
                chart = load_team_chart(str(root / entry["season_dir"] / team_id))
                book = _strict_json_object(_visual_artifact(root, context["api_book"], artifacts))
                expected = compare_preview_book(chart, book, selected, contract["season"])
                views = context["views"]
                if not isinstance(views, dict) or set(views) != {"offense", "defense", "special_teams"}:
                    raise ValueError("Visual content requires all three observed DOM views")
                heading = f"{contract['season']} {selected['name']}"
                for view, reference in views.items():
                    names = (view, "special_plays") if view == "offense" else (view,)
                    observation = _strict_json_object(_visual_artifact(root, reference, artifacts))
                    cells_checked += compare_preview_dom(
                        observation, receipt["sections"][view]["url"], heading, {name: expected[name] for name in names},
                    )
                    tables_checked += len(names)
            except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
                errors.append(f"Content context {index}: {error}")
        if seen != set(capture_contexts):
            errors.append("Visual content omits a selected capture context")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        errors.append(str(error))
    for path, digest in artifacts.items():
        try:
            _visual_artifact(root, {"path": path.relative_to(root).as_posix(), "sha256": digest}, {})
        except (ValueError, TypeError, OSError, RuntimeError) as error:
            errors.append(f"Final content artifact: {error}")
    final = audit_visual_capture_evidence(root, freeze, captures)
    errors.extend(f"Final capture: {reason}" for reason in final["errors"])
    return {"passed": not errors, "release_certified": False, "errors": errors,
            "capture": final, "tables_checked": tables_checked, "cells_checked": cells_checked,
            "candidate_content_validated": not errors, "selection_validated": False,
            "scope": "Selected candidate/API/DOM value and palette correspondence with bound captures only; "
                     "charter selection, pixel appearance, independent visual review and full readiness remain required."}


def audit_visual_selection_evidence(
    root: Path, freeze: Mapping[str, Any], captures: Mapping[str, Any],
    content: Mapping[str, Any], evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Check charter preview coverage against actual complete frozen campaigns.

    This validates trusted local selection/content consistency. It neither opens
    seed families nor certifies source reconciliation, owner approval or release.
    """
    from .chart_preview_selection_audit import preview_selection_roles

    root = Path(root).resolve()
    errors: list[str] = []
    artifacts: dict[Path, str] = {}
    cohorts: dict[str, Any] = {}
    content_check: dict[str, Any] = {}
    inputs = {"freeze": freeze, "captures": captures, "content": content, "selection": evidence}
    before: dict[str, str] = {}
    try:
        before = {name: readiness_freeze_fingerprint(value) for name, value in inputs.items()}
        content_check = audit_visual_content_evidence(root, freeze, captures, content)
        if content_check.get("passed") is not True or content_check.get("errors"):
            errors.extend(["Visual content: " + str(error) for error in content_check.get("errors", [])]
                          or ["Visual content validation failed"])
        if (not isinstance(evidence, Mapping) or set(evidence) != {
                "schema_version", "freeze_sha256", "captures_sha256", "content_sha256", "cohorts",
        } or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1):
            raise ValueError("Requires schema-1 bound preview-selection evidence")
        for name in ("freeze", "captures", "content"):
            if evidence[name + "_sha256"] != before[name]:
                raise ValueError(f"Preview selection differs from the bound {name} manifest")
        if not isinstance(evidence["cohorts"], dict) or set(evidence["cohorts"]) != {"1983-generated", "2024"}:
            raise ValueError("Preview selection requires exactly both complete cohorts")
        selected = {(entry["cohort"], entry["team"]) for entry in captures["contexts"]}
        for cohort in ("1983-generated", "2024"):
            details: dict[str, Any] = {"campaigns": {}}
            cohorts[cohort] = details
            try:
                entry = evidence["cohorts"][cohort]
                if not isinstance(entry, dict) or set(entry) != {"training", "held_out"}:
                    raise ValueError("Selection requires exactly training and held-out report bindings")
                candidate = freeze["cohorts"][cohort]
                contract = _strict_json_object((root / candidate["contract"]["path"]).read_bytes())
                reports = {}
                for phase, seed in (("training", 20261108), ("held_out", 20361108)):
                    try:
                        report = _strict_json_object(_visual_artifact(root, entry[phase], artifacts))
                        reports[phase] = report
                        metadata = report.get("metadata")
                        if (not isinstance(metadata, dict) or type(metadata.get("seed")) is not int
                                or metadata["seed"] != seed or metadata.get("policy") != "chart-focused"):
                            errors.append(f"{cohort} {phase}: wrong charter seed or reference policy")
                        validation = validate_engine_report(
                            report, contract, root / candidate["season_dir"],
                            minimum_repetitions=64, minimum_team_games=1000, require_fit=True,
                        )
                        if (not isinstance(validation, dict) or not isinstance(validation.get("errors"), list)
                                or type(validation.get("passed")) is not bool):
                            raise ValueError("Malformed nested campaign validation result")
                        details["campaigns"][phase] = validation
                        if validation["passed"] is not True or validation["errors"]:
                            errors.extend([f"{cohort} {phase}: {error}" for error in validation["errors"]]
                                          or [f"{cohort} {phase}: campaign validation failed"])
                    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                        errors.append(f"{cohort} {phase}: {error}")
                        details["campaigns"][phase] = {"passed": False, "errors": [str(error)]}
                roles = preview_selection_roles(contract, reports)
                details.update(roles)
                details["owner_required"] = ["Dolphins"] if cohort == "1983-generated" else []
                required = {roles[key]["team"] for key in ("worst_outlier", "strong_source_offense", "weak_source_offense")}
                required.update(details["owner_required"])
                details["required_teams"] = sorted(required)
                for team in sorted(required):
                    if team not in contract["teams"] or (cohort, team) not in selected:
                        errors.append(f"{cohort}: missing required preview team {team}")
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                errors.append(f"{cohort} selection: {error}")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(f"Preview selection: {error}")
    try:
        if before != {name: readiness_freeze_fingerprint(value) for name, value in inputs.items()}:
            errors.append("Selection inputs changed during validation")
        for path, digest in artifacts.items():
            _visual_artifact(root, {"path": path.relative_to(root).as_posix(), "sha256": digest}, {})
        final_content = audit_visual_content_evidence(root, freeze, captures, content)
        if final_content.get("passed") is not True or final_content.get("errors"):
            errors.extend(["Final visual content: " + str(error) for error in final_content.get("errors", [])]
                          or ["Final visual content validation failed"])
        content_check = final_content
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(f"Final preview-selection recheck: {error}")
    return {"passed": not errors, "errors": errors, "release_certified": False,
            "ready_for_owner_review": False, "source_accepted": False,
            "selection_validated": not errors, "candidate_content_validated": not errors,
            "cohorts": cohorts, "content": content_check, "campaign_artifacts_verified": len(artifacts),
            "scope": "Bound representative selection and visual correspondence only; full charter readiness and source acceptance remain separate."}



def audit_reference_corpus_evidence(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Check stable dependencies before reading any declared private corpus bytes.

    This is a trusted local census, not the weighted/crossed/paired benchmark,
    proof of non-observation, source acceptance or final readiness.
    """
    from .chart_reference_audit import audit_reference_corpus, reference_corpus_inventory
    from .chart_source_bundle import prepared_source_options

    root = Path(root).resolve()
    errors: list[str] = []
    dependencies: dict[str, Any] = {}
    corpus: dict[str, Any] = {}
    artifacts: dict[Path, str] = {}
    reference_read = False
    before: dict[str, str] = {}

    def checked(result: Any, label: str) -> dict[str, Any]:
        if (not isinstance(result, dict) or type(result.get("passed")) is not bool
                or not isinstance(result.get("errors"), list)):
            raise ValueError(f"Malformed {label} validation result")
        if result["passed"] is not True or result["errors"]:
            raise ValueError(f"{label}: " + "; ".join(map(str, result["errors"] or ["Failed evidence"])))
        return result

    def validate_dependencies() -> dict[str, Any]:
        results = {}
        for name in ("1983-generated", "2024"):
            reasons: list[str] = []
            details: dict[str, Any] = {"passed": False, "errors": reasons}
            results[name] = details
            options = report = contract = candidate = None
            try:
                entry = freeze["cohorts"][name]
                candidate = root / entry["season_dir"]
                contract_path = root / entry["contract"]["path"]
                contract = _strict_json_object(contract_path.read_bytes())
                source_ref = evidence["source_receipts"][name]
                _strict_json_object(_visual_artifact(root, source_ref, artifacts))
                options = prepared_source_options(root / source_ref["path"], candidate, contract_path)
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                reasons.append(f"Prepared sources: {error}")
            try:
                report = _strict_json_object(_visual_artifact(root, evidence["training"][name], artifacts))
                metadata = report.get("metadata")
                if (not isinstance(metadata, dict) or type(metadata.get("seed")) is not int
                        or metadata["seed"] != 20261108 or metadata.get("policy") != "chart-focused"):
                    raise ValueError("Reference preflight requires training master 20261108 and chart-focused policy")
                details["training"] = checked(validate_engine_report(
                    report, contract, candidate, minimum_repetitions=64, minimum_team_games=1000, require_fit=True,
                ), "training")
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                reasons.append(f"Training: {error}")
            if report is not None and contract is not None and candidate is not None and options is not None:
                try:
                    component = checked(audit_release(candidate, contract, report, **options), "component")
                    details["component"] = {key: value for key, value in component.items() if key != "engine_evidence"}
                except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                    reasons.append(f"Source/mechanics: {error}")
            details["passed"] = not reasons
        return results

    try:
        before = {"freeze": readiness_freeze_fingerprint(freeze), "evidence": readiness_freeze_fingerprint(evidence)}
        checked(audit_readiness_freeze(root, freeze), "freeze")
        if (not isinstance(evidence, Mapping) or set(evidence) != {
                "schema_version", "freeze_sha256", "source_receipts", "training", "corpus",
        } or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1
                or evidence["freeze_sha256"] != before["freeze"]):
            raise ValueError("Requires schema-1 reference evidence bound to the current freeze")
        for field in ("source_receipts", "training"):
            if not isinstance(evidence[field], dict) or set(evidence[field]) != {"1983-generated", "2024"}:
                raise ValueError(f"Reference {field} must bind exactly both complete source cohorts")
        dependencies = validate_dependencies()
        errors.extend(f"{name}: {reason}" for name, result in dependencies.items() for reason in result["errors"])
        if not errors:
            reference_read = True
            candidate = freeze["cohorts"]["1983-generated"]
            contract = _strict_json_object((root / candidate["contract"]["path"]).read_bytes())
            corpus = audit_reference_corpus(root, freeze, evidence["corpus"], contract)
            checked(corpus, "reference corpus")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(str(error))
    try:
        if reference_read:
            final = validate_dependencies()
            errors.extend(f"Final {name}: {reason}" for name, result in final.items() for reason in result["errors"])
        checked(audit_readiness_freeze(root, freeze), "final freeze")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(f"Final reference dependencies: {error}")
    try:
        if before != {"freeze": readiness_freeze_fingerprint(freeze), "evidence": readiness_freeze_fingerprint(evidence)}:
            errors.append("Reference declaration or freeze changed during validation")
        for path, digest in artifacts.items():
            _visual_artifact(root, {"path": path.relative_to(root).as_posix(), "sha256": digest}, {})
        if (reference_read and "files" in corpus
                and reference_corpus_inventory(root / evidence["corpus"]["directory"]) != (corpus["files"], corpus["directories"])):
            errors.append("Reference corpus changed after dependency revalidation")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(f"Final reference artifacts: {error}")
    return {"passed": not errors, "errors": errors, "corpus_validated": not errors,
            "reference_bytes_read": reference_read, "dependencies": dependencies, "corpus": corpus,
            "release_certified": False, "ready_for_owner_review": False, "source_accepted": False,
            "benchmark_complete": False, "dependency_artifacts_verified": len(artifacts),
            "scope": "Declared local normalized-corpus/decoder consistency only; weighted/crossed behavior, paired reference campaigns, transfer and independent review remain required."}


def _audit_reference_comparison_evidence(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any], kind: str,
) -> dict[str, Any]:
    """Guard computed reference diagnostics with the same stable dependencies."""
    from . import chart_reference_audit as reference

    root = Path(root).resolve()
    errors: list[str] = []
    preflights: dict[str, Any] = {}
    measured_result: dict[str, Any] = {}
    flag = "weighted_validated" if kind == "weighted" else "contexts_validated"
    reference_read = False
    before = {}
    entered = False

    def check_preflight(label: str) -> dict[str, Any]:
        checked = audit_reference_corpus_evidence(root, freeze, evidence)
        preflights[label] = checked
        if (not isinstance(checked, dict) or type(checked.get("passed")) is not bool
                or not isinstance(checked.get("errors"), list)):
            raise ValueError(f"{label}: malformed reference preflight")
        if not checked["passed"] or checked["errors"] or checked.get("corpus_validated") is not True:
            raise ValueError(f"{label}: " + "; ".join(map(str, checked["errors"] or ["Reference preflight failed"])))
        return checked

    try:
        before = {"freeze": readiness_freeze_fingerprint(freeze), "evidence": readiness_freeze_fingerprint(evidence)}
        initial = check_preflight("before")
        reference_read = initial["reference_bytes_read"]
        entered = True
        generated, originals = reference._load_matched_reference_charts(root, freeze, evidence)
        compare = reference.compare_reference_weighted if kind == "weighted" else reference.compare_reference_contexts
        measured = compare(generated, originals)
        if (not isinstance(measured, dict) or type(measured.get("passed")) is not bool
                or not isinstance(measured.get("errors"), list)):
            raise ValueError(f"Malformed {kind} reference result")
        measured_result = measured
        if (measured["passed"] is not True or measured["errors"]
                or measured.get(flag) is not True):
            raise ValueError(f"Reference {kind}: " + "; ".join(map(str, measured["errors"] or ["Failed evidence"])))
        if kind == "weighted":
            if (not isinstance(measured.get("teams"), dict) or set(measured["teams"]) != set(generated)
                    or any(details.get("passed") is not True or details.get("errors")
                           or set(details.get("scenarios", {})) != {"rr", "gr", "rg", "gg"}
                           or len(details.get("plays", {})) != 54 for details in measured["teams"].values())):
                raise ValueError("Weighted reference result omits complete matched-team evidence")
        else:
            from .chart_reference_context_audit import validate_context_collection
            validate_context_collection(measured, set(generated))
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(str(error))
    if entered:
        try:
            check_preflight("after")
        except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError, OverflowError) as error:
            errors.append(str(error))
    try:
        if before != {"freeze": readiness_freeze_fingerprint(freeze), "evidence": readiness_freeze_fingerprint(evidence)}:
            errors.append(f"Reference declaration or freeze changed during {kind} comparison")
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        errors.append(f"Final {kind} declarations: {error}")
    reference_read = reference_read or any(
        isinstance(value, dict) and value.get("reference_bytes_read") is True for value in preflights.values())
    return {
        "passed": not errors, "errors": errors, "preflights": preflights, kind: measured_result,
        "reference_bytes_read": reference_read, "corpus_validated": not errors, flag: not errors,
        "stateful_crossed_complete": False, "benchmark_complete": False,
        "source_accepted": False, "ready_for_owner_review": False, "release_certified": False,
        "scope": f"Computed {kind} diagnostics only; full source fit, stateful outlier/exploit review, "
                 "paired campaigns, prospective transfer and independent review remain required.",
    }


def audit_reference_weighted_evidence(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind exact weighted diagnostics to complete before/after corpus preflights."""
    return _audit_reference_comparison_evidence(root, freeze, evidence, "weighted")


def audit_reference_context_evidence(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind complete matched engine contexts to stable dependencies and private output."""
    return _audit_reference_comparison_evidence(root, freeze, evidence, "contexts")


def audit_reference_paired_evidence(
    root: Path, freeze: Mapping[str, Any], evidence: Mapping[str, Any], paired: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind full paired campaign files after stable source/training/corpus checks."""
    from .chart_reference_audit import compare_reference_campaigns
    from .chart_reference_pair_audit import validate_paired_summary

    root = Path(root).resolve()
    errors: list[str] = []
    preflights: dict[str, Any] = {}
    artifacts: dict[Path, str] = {}
    measured: dict[str, Any] = {}
    reference_read = paired_read = entered = False
    before = {}

    def declarations() -> dict[str, str]:
        return {name: readiness_freeze_fingerprint(value) for name, value in (
            ("freeze", freeze), ("reference", evidence), ("paired", paired))}

    def preflight(label: str) -> dict[str, Any]:
        checked = audit_reference_corpus_evidence(root, freeze, evidence)
        preflights[label] = checked
        if (not isinstance(checked, dict) or checked.get("passed") is not True or checked.get("errors") != []
                or checked.get("corpus_validated") is not True):
            reasons = checked.get("errors", []) if isinstance(checked, dict) else []
            raise ValueError(f"{label}: " + "; ".join(map(str, reasons or ["Failed reference preflight"])))
        return checked

    try:
        before = declarations()
        initial = preflight("before")
        reference_read = initial["reference_bytes_read"]
        entered = True
        if (not isinstance(paired, Mapping) or set(paired) != {
                "schema_version", "freeze_sha256", "reference_declaration_sha256", "generated", "reference"}
                or type(paired["schema_version"]) is not int or paired["schema_version"] != 1
                or paired["freeze_sha256"] != before["freeze"]
                or paired["reference_declaration_sha256"] != before["reference"]):
            raise ValueError("Requires strict schema-1 paired evidence bound to this freeze and reference declaration")
        reports = {}
        for side in ("generated", "reference"):
            try:
                binding = paired[side]
                if (not isinstance(binding, dict) or not isinstance(binding.get("path"), str)
                        or Path(binding["path"]).parts[:2] != (".ai-audits", "chart-reference-comparison")):
                    raise ValueError("Paired reports must remain under ignored .ai-audits/chart-reference-comparison/")
                paired_read = True
                reports[side] = _strict_json_object(_visual_artifact(root, binding, artifacts))
            except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
                errors.append(f"{side} paired report: {error}")
        if not errors:
            candidate = freeze["cohorts"]["1983-generated"]
            contract = _strict_json_object((root / candidate["contract"]["path"]).read_bytes())
            mapping = {name: details["reference_folder"] for name, details in evidence["corpus"]["teams"].items()}
            measured = compare_reference_campaigns(
                reports["generated"], reports["reference"], contract, root / candidate["season_dir"],
                root / evidence["corpus"]["directory"], mapping)
            validate_paired_summary(measured, contract, mapping)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(str(error))
    if entered:
        try:
            preflight("after")
        except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError, OverflowError) as error:
            errors.append(str(error))
    try:
        if before != declarations():
            errors.append("Reference, paired declaration or freeze changed during paired validation")
        for path, digest in artifacts.items():
            _visual_artifact(root, {"path": path.relative_to(root).as_posix(), "sha256": digest}, {})
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, OverflowError) as error:
        errors.append(f"Final paired artifacts: {error}")
    reference_read = reference_read or any(isinstance(value, dict) and value.get("reference_bytes_read") is True
                                          for value in preflights.values())
    return {"passed": not errors, "errors": errors, "preflights": preflights, "paired": measured,
            "reference_bytes_read": reference_read, "paired_artifacts_read": paired_read,
            "paired_artifacts_verified": len(artifacts), "corpus_validated": not errors, "paired_validated": not errors,
            "benchmark_complete": False, "source_accepted": False, "ready_for_owner_review": False, "release_certified": False,
            "scope": "Bound complete paired campaign diagnostics only; source-fit/outlier verdict, transfer, "
                     "seed-use/announcement history, independent review and full readiness remain required."}

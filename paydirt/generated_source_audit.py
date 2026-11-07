"""Audit generated-source declarations and output consistency, not historical fit."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .chart_audit import audit_chart_decoder, audit_season


def generation_input_hashes(groups: Mapping[str, list[Path]]) -> dict[str, str]:
    """Bind generation to source bytes using portable, nonabsolute labels."""
    hashes = {}
    for group, paths in sorted(groups.items()):
        for path in sorted(paths):
            key = f"{group}/{path.name}"
            if key in hashes:
                raise ValueError(f"Duplicate generation input label: {key}")
            hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _read_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
    """Read evidence without treating malformed input as a passing check."""
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        errors.append(f"{path.name}: cannot read evidence: {error}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path.name}: evidence must be a JSON object")
        return None
    return value


def _is_count(value: Any) -> bool:
    """Return whether a value is a nonnegative integer count."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_stats(data: dict[str, Any], name: str, season: Any, errors: list[str]) -> None:
    """Validate normalized identities and counting-stat denominators."""
    if data.get("team_name") != name or data.get("season") != season:
        errors.append(f"{name}: normalized source identity/season mismatch")
    for side in ("offense", "defense", "special_teams"):
        units = data.get(side, {})
        if not isinstance(units, dict):
            errors.append(f"{name}: {side} source must be an object")
            continue
        for unit, line in units.items():
            if not isinstance(line, dict):
                continue
            label = f"{name} {side}.{unit}"
            for field, value in line.items():
                if field == "yards":
                    if not isinstance(value, (int, float)) or not math.isfinite(value):
                        errors.append(f"{label}.{field}: invalid yards")
                elif not _is_count(value):
                    errors.append(f"{label}.{field}: invalid nonnegative count")
            attempts = line.get("attempts")
            if _is_count(attempts):
                for field in ("completions", "interceptions", "made", "blocked"):
                    value = line.get(field)
                    if _is_count(value) and value > attempts:
                        errors.append(f"{label}.{field}: exceeds attempts denominator")
                completed = line.get("completions", 0)
                intercepted = line.get("interceptions", 0)
                if (
                    _is_count(completed)
                    and _is_count(intercepted)
                    and completed + intercepted > attempts
                ):
                    errors.append(f"{label}: completions plus interceptions exceed attempts")
            lost, fumbles = line.get("fumbles_lost"), line.get("fumbles")
            if _is_count(lost) and _is_count(fumbles) and lost > fumbles:
                errors.append(f"{label}: lost fumbles exceed fumbles")


def _source_rates(counts: Mapping[str, Any]) -> dict[str, float]:
    """Recompute rate targets from their statistical denominators."""
    return {
        "completion_rate": counts["completions"] / counts["pass_attempts"],
        "interception_rate": counts["interceptions"] / counts["pass_attempts"],
        "sack_rate": counts["sacks"] / (counts["pass_attempts"] + counts["sacks"]),
        "yards_per_pass_attempt": counts["passing_yards"] / counts["pass_attempts"],
        "rushing_yards_per_attempt": counts["rushing_yards"] / counts["rushing_attempts"],
    }


def _normalized_counts(data: Mapping[str, Any]) -> dict[str, int]:
    """Extract the public counting facts retained in a reviewed contract."""
    passing = data.get("offense", {}).get("passing", {})
    rushing = data.get("offense", {}).get("rushing", {})
    field_goal = data.get("special_teams", {}).get("field_goal", {})
    return {
        "pass_attempts": passing.get("attempts", 0),
        "completions": passing.get("completions", 0),
        "interceptions": passing.get("interceptions", 0),
        "sacks": passing.get("sacks", 0),
        "passing_yards": passing.get("yards", 0),
        "rushing_attempts": rushing.get("attempts", 0),
        "rushing_yards": rushing.get("yards", 0),
        "field_goal_attempts": field_goal.get("attempts", 0),
        "field_goals_made": field_goal.get("made", 0),
    }


def _audit_contract(
    season_dir: Path,
    manifest: dict[str, Any],
    contract: Mapping[str, Any],
    errors: list[str],
    findings: list[dict[str, Any]],
) -> None:
    """Check reviewed source facts without requiring ignored raw input files."""
    try:
        if contract.get("schema_version") != 1:
            errors.append("contract: unsupported schema version")
        manifest_hash = contract.get("generation_manifest_sha256")
        if (
            manifest_hash is not None
            and hashlib.sha256((season_dir / "generation-manifest.json").read_bytes()).hexdigest()
            != manifest_hash
        ):
            errors.append("contract: generation manifest hash differs from reviewed metadata")
        if not manifest.get("input_hashes") or manifest["input_hashes"] != contract.get("input_hashes"):
            errors.append("contract: declared input hashes differ from reviewed inventory")
        if contract["season"] != manifest["season"] or contract["games"] != manifest["games"]:
            errors.append("contract: season/game count differs from manifest")
        if contract["attribution"] != manifest["source"]:
            errors.append("contract: source attribution differs from manifest")
        if contract["generation_profile"] != manifest["calibration_profile"]:
            errors.append("contract: generation profile differs from selected profile")
        if set(contract["teams"]) != set(manifest["teams"]):
            errors.append("contract: team inventory differs from manifest")
        appearances: Counter[str] = Counter()
        schedule = contract["schedule"]
        if len(schedule) != contract["games"]:
            errors.append("contract: schedule length differs from game count")
        for game in schedule:
            if game["away"] == game["home"]:
                errors.append("contract: schedule contains self-matchup")
            for side in ("away", "home"):
                if game[side] not in contract["teams"]:
                    errors.append("contract: schedule names unknown team")
                appearances[game[side]] += 1
        totals: Counter[str] = Counter()
        for name, team in contract["teams"].items():
            if team["games"] != appearances[name]:
                errors.append(f"contract {name}: team game count does not reconcile schedule")
            if not all(_is_count(value) for value in team["counts"].values()):
                errors.append(f"contract {name}: invalid source counts")
            counts = team["counts"]
            if counts["completions"] + counts["interceptions"] > counts["pass_attempts"]:
                errors.append(f"contract {name}: completed/intercepted passes exceed attempts")
            if counts["field_goals_made"] > counts["field_goal_attempts"]:
                errors.append(f"contract {name}: field goals made exceed attempts")
            totals.update(team["counts"])
            for metric, expected in _source_rates(team["counts"]).items():
                if not math.isclose(team["rates"][metric], expected, abs_tol=1e-12, rel_tol=1e-12):
                    errors.append(f"contract {name}: {metric} does not reconcile source counts")
            for metric in ("interceptions", "sacks", "field_goal_attempts"):
                observed = manifest["teams"][name].get("source_event_counts", {}).get(metric)
                if not _is_count(observed) or observed != counts[metric]:
                    errors.append(f"contract source {name}: classified {metric} differs from official")
                    findings.append({"code": "classified-source-count-mismatch", "team": name,
                                     "metric": metric, "classified": observed,
                                     "official": counts[metric], "severity": "error"})
            classified_fga = manifest["teams"][name]["field_goal_attempts"]
            official_fga = team["counts"]["field_goal_attempts"]
            if classified_fga != official_fga:
                errors.append(
                    f"contract source {name}: classified field_goal_attempts differs from official"
                )
                findings.append(
                    {
                        "code": "classified-source-count-mismatch",
                        "team": name,
                        "metric": "field_goal_attempts",
                        "classified": classified_fga,
                        "official": official_fga,
                        "severity": "error",
                    }
                )
        if dict(totals) != contract["league"]["counts"]:
            errors.append("contract: league count summary does not reconcile teams")
        rates = _source_rates(contract["league"]["counts"])
        if set(contract["targets"]) != set(rates):
            errors.append("contract: target metric inventory differs from required source rates")
        for metric, expected in rates.items():
            if not math.isclose(
                contract["league"]["rates"][metric], expected, abs_tol=1e-12, rel_tol=1e-12
            ):
                errors.append(f"contract: league {metric} does not reconcile source counts")
            target = contract["targets"][metric]
            if not math.isclose(target["value"], expected, abs_tol=1e-12, rel_tol=1e-12):
                errors.append(f"contract: target {metric} does not reconcile source counts")
            if not math.isfinite(target["tolerance"]) or target["tolerance"] < 0:
                errors.append(f"contract: invalid {metric} tolerance")
        paths = {str(path.relative_to(season_dir)): path for path in season_dir.glob("*/*.csv")}
        if set(paths) != set(contract["chart_hashes"]):
            errors.append("contract: chart hash file inventory differs from generated output")
        for name, path in paths.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != contract["chart_hashes"].get(name):
                errors.append(f"contract: chart hash mismatch: {name}")
        official = contract["league"]["counts"]
        diagnostics = manifest.get("diagnostics", {})
        classified = {
            key: diagnostics[key] for key in ("interceptions", "sacks") if key in diagnostics
        }
        classified["field_goal_attempts"] = manifest["field_goal_attempts"]
        for key, observed in classified.items():
            if observed == official[key]:
                continue
            finding = {
                "code": "classified-source-count-mismatch",
                "metric": key,
                "classified": observed,
                "official": official[key],
                "severity": "error",
            }
            # An approval label and prose do not reconcile event evidence.
            # Definition differences belong in source normalization, preserving
            # raw provenance and separately credited official occurrences.
            errors.append(
                f"contract source {key}: classified {observed} differs from official {official[key]}"
            )
            findings.append(finding)
    except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError, OSError) as error:
        errors.append(f"contract: malformed or unreadable evidence: {error}")


def audit_generated_source(
    season_dir: Path,
    *,
    stats_dir: Path | None = None,
    reproduced_dir: Path | None = None,
    expected_profile: Mapping[str, float] | None = None,
    validation_contract: Mapping[str, Any] | None = None,
    input_files: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Check manifest arithmetic, source identities, structure and reproduction.

    Optional evidence not supplied is disclosed as unverified. A passing report
    establishes consistency only for the checks explicitly marked true.
    """
    season_dir = Path(season_dir)
    errors: list[str] = []
    warnings: list[str] = []
    findings: list[dict[str, Any]] = []
    checks: dict[str, Any] = {
        "structural": False,
        "decoder": False,
        "normalized_stats": False,
        "source_hashes": False,
        "reproduction": False,
        "raw_inputs": False,
    }
    decoder: dict[str, dict[str, Any]] = {}
    manifest = _read_object(season_dir / "generation-manifest.json", errors)
    if manifest is None:
        return {
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
            "findings": findings,
            "decoder": decoder,
        }
    declared_inputs = manifest.get("input_hashes", {})
    if input_files is None:
        warnings.append("Raw generation inputs not supplied; declared hashes not independently rechecked")
    else:
        before = len(errors)
        if not declared_inputs or set(input_files) != set(declared_inputs):
            errors.append("input hash inventory differs from supplied source files")
        for label, path in input_files.items():
            try:
                if hashlib.sha256(Path(path).read_bytes()).hexdigest() != declared_inputs.get(label):
                    errors.append(f"input hash mismatch: {label}")
            except OSError as error:
                errors.append(f"input hash {label}: {error}")
        checks["raw_inputs"] = len(errors) == before
    for key in ("season", "seed", "games", "source_rows"):
        if not _is_count(manifest.get(key)):
            errors.append(f"manifest {key}: missing or invalid nonnegative integer")
    if not isinstance(manifest.get("source"), str) or not manifest["source"].strip():
        errors.append("manifest source: missing provenance declaration")
    if str(manifest.get("source", "")).startswith("nflverse"):
        before = len(errors)
        capability = manifest.get("required_source_fields")
        empty_ledger_hash = hashlib.sha256(b"[]\n").hexdigest()
        if not isinstance(capability, dict):
            errors.append("required source fields: missing coverage declaration")
        elif (type(capability.get("unsupported_count")) is not int
              or capability["unsupported_count"] != 0
              or capability.get("ledger_sha256") != empty_ledger_hash):
            errors.append("required source fields: unsupported population or nonempty/unverified ledger")
        checks["required_source_fields"] = len(errors) == before
        before = len(errors)
        population = manifest.get("conversion_population")
        if not isinstance(population, dict):
            errors.append("conversion population: missing coverage declaration")
        else:
            known = population.get("structured_flag_rows")
            unknown = population.get("unknown_flag_rows")
            not_applicable = population.get("not_applicable_flag_rows")
            excluded = population.get("excluded_count")
            credited = population.get("credited_offensive_attempts")
            if not all(_is_count(value) for value in
                       (known, unknown, not_applicable, excluded, credited)):
                errors.append("conversion population: invalid coverage counts")
            elif (unknown or known + unknown + not_applicable != manifest.get("source_rows")
                  or excluded > known + unknown or credited > excluded or credited > known
                  or excluded != manifest.get("diagnostics", {}).get("excluded_conversion_rows", 0)
                  or credited != manifest.get("diagnostics", {}).get("excluded_two_point_attempts", 0)):
                errors.append("conversion population: incomplete or unreconciled coverage")
            ledger_hash = population.get("exclusion_ledger_sha256")
            if (not isinstance(ledger_hash, str) or len(ledger_hash) != 64
                    or any(char not in "0123456789abcdef" for char in ledger_hash)):
                errors.append("conversion population: missing exclusion ledger fingerprint")
            if manifest.get("diagnostics", {}).get("conflicting_two_point_flags", 0):
                errors.append("conversion population: conflicting source markers")
        checks["conversion_population"] = len(errors) == before
    modeled_allowances: dict[str, int] = {}
    disclosure = manifest.get("fumble_fitting_policy")
    if disclosure is not None:
        before = len(errors)
        try:
            from .fumble_source import source_record_hash
            from .historical_fumble_proxy import (
                POLICY_V2,
                policy_metadata,
                validate_fitting_metadata,
            )

            validate_fitting_metadata(disclosure)
            if (manifest.get("fumble_gain_policy") != POLICY_V2
                    or validation_contract is None
                    or source_record_hash(validation_contract.get("fumble_fitting_policy")) != source_record_hash(disclosure)
                    or source_record_hash(manifest.get("modeled_fumble_assumptions")) != source_record_hash(
                        policy_metadata(POLICY_V2, manifest.get("diagnostics", {}))["modeled_fumble_assumptions"])
                    or source_record_hash(validation_contract.get("modeled_fumble_assumptions")) != source_record_hash(
                        manifest.get("modeled_fumble_assumptions"))
                    or disclosure["fitted_unknown_ownership"] != 0
                    or manifest.get("fumbles") != disclosure["fitted_events"]
                    or manifest.get("diagnostics", {}).get("active_unsupported_required_fields", 0)):
                raise ValueError("Modeled fitting population requires exact contract opt-in and complete supported ownership")
            for name, team in manifest.get("teams", {}).items():
                source_team = team.get("pfr_team", name)
                if team.get("fumbles") != disclosure["teams"].get(source_team, {}).get("fitted_events"):
                    raise ValueError("Modeled fitting team population differs from manifest")
            modeled_allowances = {
                "missing_required_gains": disclosure["excluded_by_mechanism"].get("fumble_gain_projection", 0),
                "unknown_fumble_recoveries": disclosure["full_unknown_ownership"],
            }
        except (ValueError, TypeError, KeyError) as error:
            errors.append(f"modeled fitting eligibility: {error}")
        checks["modeled_fitting_scope"] = len(errors) == before
        checks["historical_source_complete"] = False
    for diagnostic in ("unverified_field_goal_box", "unreconciled_field_goal_box",
                       "missing_required_gains", "unknown_fumble_recoveries", "unreconciled_fumble_box"):
        count = manifest.get("diagnostics", {}).get(diagnostic, 0)
        if not _is_count(count) or count != modeled_allowances.get(diagnostic, 0):
            errors.append(f"source event eligibility: {diagnostic}={count}")
    teams = manifest.get("teams")
    if not isinstance(teams, dict) or not teams:
        errors.append("manifest team inventory: missing or empty object")
        teams = {}
    folders = {
        p.name
        for p in season_dir.iterdir()
        if p.is_dir()
        and any((p / file).exists() for file in ("offense.csv", "defense.csv", "special.csv"))
    }
    if folders != set(teams):
        errors.append("manifest team inventory does not match generated chart folders")
    for key in ("empirical_outcomes", "field_goal_attempts", "fumbles"):
        counts = [team.get(key) if isinstance(team, dict) else None for team in teams.values()]
        if not _is_count(manifest.get(key)) or not all(_is_count(n) for n in counts):
            errors.append(f"manifest {key}: missing or invalid aggregate/team counts")
        elif sum(counts) != manifest[key]:
            errors.append(f"manifest {key}: aggregate does not reconcile team counts")
    for name, team in teams.items():
        if not isinstance(team, dict):
            errors.append(f"{name}: invalid manifest team object")
            continue
        for key in (
            "generated_empirical_outcomes",
            "opponent_adjusted_outcomes",
            "fallback_columns",
        ):
            if not _is_count(team.get(key)):
                errors.append(f"{name}: missing or invalid {key}")
        supplied = team.get("empirical_outcomes")
        adjusted = team.get("opponent_adjusted_outcomes")
        generated = team.get("generated_empirical_outcomes")
        if _is_count(supplied) and _is_count(adjusted) and supplied != adjusted:
            errors.append(f"{name}: opponent-adjusted outcome counts do not reconcile")
        if _is_count(generated) and _is_count(adjusted) and generated > adjusted:
            errors.append(f"{name}: generated empirical outcomes exceed supplied outcomes")
    profile = manifest.get("calibration_profile")
    if not isinstance(profile, dict) or not profile:
        errors.append("manifest calibration profile: missing or invalid object")
        profile = {}
    for name, value in profile.items():
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            errors.append(f"profile {name}: must be finite numeric")
        elif name.endswith("multiplier") and value <= 0:
            errors.append(f"profile {name}: multiplier must be positive")
    opponent = manifest.get("opponent_adjustment", {})
    if not isinstance(opponent, dict):
        errors.append("manifest opponent profile: invalid object")
        opponent = {}
    for name, value in profile.items():
        if opponent.get(name) != value:
            errors.append(f"profile {name}: calibration and opponent profile disagree")
    for name, value in (expected_profile or {}).items():
        if profile.get(name) != value:
            errors.append(f"profile {name}: differs from selected expected profile")
    if stats_dir is None:
        warnings.append(
            "Normalized source statistics not supplied; identities and denominators unverified"
        )
    else:
        stats_dir = Path(stats_dir)
        before = len(errors)
        for name in teams:
            data = _read_object(stats_dir / f"{name}.json", errors)
            if data is not None:
                _validate_stats(data, name, manifest.get("season"), errors)
        checks["normalized_stats"] = len(errors) == before
    hashes = manifest.get("source_hashes")
    if not hashes and declared_inputs:
        checks["source_hashes"] = checks["raw_inputs"]
    elif not hashes:
        warnings.append(
            "Manifest has no source hashes; raw-input identity not cryptographically established"
        )
    elif not isinstance(hashes, dict) or stats_dir is None:
        errors.append("source hashes: expected mapping and source directory are required")
    else:
        before = len(errors)
        for name, expected in hashes.items():
            path = (stats_dir / name).resolve()
            if not path.is_relative_to(stats_dir.resolve()):
                errors.append(f"source hash {name}: path escapes source directory")
                continue
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as error:
                errors.append(f"source hash {name}: cannot read: {error}")
                continue
            if actual != expected:
                errors.append(f"source hash {name}: SHA-256 mismatch")
        checks["source_hashes"] = len(errors) == before
    try:
        structure = audit_season(season_dir)
        errors.extend(f"chart structure: {error}" for error in structure["errors"])
        warnings.extend(f"chart coverage: {warning}" for warning in structure["warnings"])
        checks["structural"] = not structure["errors"]
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        errors.append(f"chart structure: cannot audit: {error}")
    before = len(errors)
    if not folders:
        errors.append("chart decoder: no generated chart folders")
    for name in sorted(folders):
        census = audit_chart_decoder(season_dir / name)
        decoder[name] = census
        errors.extend(f"chart decoder {name}: {error}" for error in census["errors"])
        errors.extend(f"chart decoder {name}: {limitation}" for limitation in census["limitations"])
    checks["decoder"] = len(errors) == before
    if reproduced_dir is None:
        warnings.append("Independent regeneration not supplied; output reproducibility unverified")
    else:
        reproduced_dir = Path(reproduced_dir)
        before = len(errors)
        originals = {p.relative_to(season_dir): p for p in season_dir.glob("*/*.csv")}
        reproduced = {p.relative_to(reproduced_dir): p for p in reproduced_dir.glob("*/*.csv")}
        if set(originals) != set(reproduced):
            errors.append("reproduction: chart file inventories differ")
        for name in sorted(originals.keys() & reproduced.keys()):
            if originals[name].read_bytes() != reproduced[name].read_bytes():
                errors.append(f"reproduction: chart bytes differ: {name}")
        checks["reproduction"] = len(errors) == before
        checks["compared_chart_files"] = len(originals.keys() & reproduced.keys())
    coverage = manifest.get("source_feature_coverage", {})
    if isinstance(coverage, dict) and coverage.get("modeled_missing_features"):
        warnings.append(
            "Modeled source omissions: " + ", ".join(coverage["modeled_missing_features"])
        )
    if validation_contract is not None:
        before = len(errors)
        _audit_contract(season_dir, manifest, validation_contract, errors, findings)
        contract_teams = validation_contract.get("teams")
        if stats_dir is not None and isinstance(contract_teams, dict):
            for name, team in contract_teams.items():
                data = _read_object(stats_dir / f"{name}.json", errors)
                if data is not None:
                    try:
                        if _normalized_counts(data) != team.get("counts"):
                            errors.append(
                                f"contract normalized {name}: current source counts differ from reviewed facts"
                            )
                    except (AttributeError, KeyError, TypeError, ValueError) as error:
                        errors.append(f"contract normalized {name}: malformed evidence: {error}")
        checks["validation_contract"] = len(errors) == before
        checks["reviewed_source_facts"] = True
    else:
        checks["validation_contract"] = False
        checks["reviewed_source_facts"] = False
    checks["teams"] = len(teams)
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "findings": findings,
        "decoder": decoder,
    }

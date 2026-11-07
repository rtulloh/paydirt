"""Source/output consistency regressions using public fictional fixtures only."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
from contextlib import nullcontext
from pathlib import Path

import pytest

from paydirt.chart_audit import audit_season


@pytest.fixture
def generated_source(tmp_path: Path) -> tuple[Path, Path]:
    season = tmp_path / "generated"
    source = Path(__file__).resolve().parents[1] / "seasons" / "2026"
    shutil.copytree(source, season)
    stats = tmp_path / "stats"
    stats.mkdir()
    names = ("Ironclads", "Thunderhawks")
    for name in names:
        (stats / f"{name}.json").write_text(
            json.dumps(
                {
                    "season": 2026,
                    "team_name": name,
                    "offense": {
                        "passing": {
                            "attempts": 100,
                            "completions": 60,
                            "yards": 700,
                            "interceptions": 2,
                            "sacks": 0,
                        },
                        "rushing": {"attempts": 50, "yards": 200},
                    },
                    "defense": {
                        "passing": {
                            "attempts": 100,
                            "completions": 60,
                            "yards": 700,
                            "interceptions": 2,
                        }
                    },
                    "special_teams": {"field_goal": {"attempts": 2, "made": 1}},
                }
            )
        )
    profile = {
        "pass_completion_adjustment": 0.0,
        "pass_interception_adjustment": 0.0,
        "pass_pressure_adjustment": 0.0,
        "pass_yard_multiplier": 1.0,
        "run_yard_multiplier": 1.0,
    }
    manifest = {
        "season": 2026,
        "seed": 8306,
        "source": "Synthetic public-fixture audit",
        "games": 1,
        "source_rows": 12,
        "empirical_outcomes": 10,
        "field_goal_attempts": 4,
        "fumbles": 2,
        "input_hashes": {f"normalized_stats/{name}.json": hashlib.sha256((stats / f"{name}.json").read_bytes()).hexdigest()
                         for name in names},
        "calibration_profile": profile,
        "opponent_adjustment": dict(profile),
        "teams": {
            name: {
                "empirical_outcomes": 5,
                "generated_empirical_outcomes": 4,
                "opponent_adjusted_outcomes": 5,
                "fallback_columns": 1,
                "field_goal_attempts": 2,
                "source_event_counts": {"interceptions": 2, "sacks": 0, "field_goal_attempts": 2},
                "fumbles": 1,
            }
            for name in names
        },
    }
    (season / "generation-manifest.json").write_text(json.dumps(manifest))
    return season, stats


def _audit(season: Path, **kwargs: object) -> dict:
    # Before the source-aware audit exists, the current structural gate is the
    # behavior under test: it accepts source/profile mismatches. Keeping this
    # fallback also makes deleting the new validator fail these regressions.
    if importlib.util.find_spec("paydirt.generated_source_audit") is None:
        report = audit_season(season)
        return {**report, "passed": not report["errors"]}
    from paydirt.generated_source_audit import audit_generated_source

    return audit_generated_source(season, **kwargs)


def _change_manifest(season: Path, change: object) -> None:
    path = season / "generation-manifest.json"
    manifest = json.loads(path.read_text())
    change(manifest)
    path.write_text(json.dumps(manifest))


def test_consistent_public_fixture_passes_with_explicit_hash_limitation(
    generated_source: tuple[Path, Path],
) -> None:
    season, stats = generated_source
    report = _audit(season, stats_dir=stats)
    assert report["passed"]


def test_source_evidence_includes_decoder_census_for_every_team(generated_source) -> None:
    season, stats = generated_source
    report = _audit(season, stats_dir=stats)
    assert report["passed"], report["errors"]
    assert report["checks"].get("decoder") is True
    assert set(report["decoder"]) == {"Ironclads", "Thunderhawks"}
    for name, decoder in report["decoder"].items():
        assert decoder["passed"] and decoder["fully_supported"]
        assert len(decoder["columns"]) == 73
        assert decoder["files"] == {
            filename: hashlib.sha256((season / name / filename).read_bytes()).hexdigest()
            for filename in ("offense.csv", "defense.csv", "special.csv")
        }


@pytest.mark.parametrize("filename,column,token", [
    ("special.csv", 1, "+65"),
    ("special.csv", 5, "OFF R"),
    ("offense.csv", 11, "OFF 5"),
])
def test_source_gate_rejects_unsupported_consumers_and_known_fallbacks(
    generated_source, filename: str, column: int, token: str,
) -> None:
    season, stats = generated_source
    path = season / "Ironclads" / filename
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    rows[1][column] = token
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    expected_warning = pytest.warns(UserWarning, match="unreadable cell 'OFF R'") if token == "OFF R" else nullcontext()
    with expected_warning:
        report = _audit(season, stats_dir=stats)
    assert not report["passed"]
    assert report["checks"].get("decoder") is False
    assert any("decoder" in error and "Ironclads" in error for error in report["errors"])


@pytest.mark.parametrize("diagnostic", ["unverified_field_goal_box", "unreconciled_field_goal_box"])
def test_unverified_or_conflicting_event_credit_cannot_certify_source(
    generated_source: tuple[Path, Path], diagnostic: str,
) -> None:
    season, stats = generated_source
    _change_manifest(season, lambda manifest: manifest.__setitem__("diagnostics", {diagnostic: 1}))
    report = _audit(season, stats_dir=stats)
    assert not report["passed"]
    assert any(diagnostic in error for error in report["errors"])


@pytest.mark.parametrize("field", ["empirical_outcomes", "field_goal_attempts", "fumbles"])
def test_manifest_aggregate_must_reconcile_team_counts(
    generated_source: tuple[Path, Path], field: str
) -> None:
    season, stats = generated_source
    _change_manifest(season, lambda manifest: manifest.__setitem__(field, 999))
    report = _audit(season, stats_dir=stats)
    assert not report["passed"]
    assert any(field in error for error in report["errors"])


def test_manifest_team_inventory_must_match_outputs(generated_source: tuple[Path, Path]) -> None:
    season, _ = generated_source
    _change_manifest(season, lambda manifest: manifest["teams"].pop("Ironclads"))
    report = _audit(season)
    assert not report["passed"]
    assert any("team inventory" in error for error in report["errors"])


def test_opponent_profile_drift_fails(generated_source: tuple[Path, Path]) -> None:
    season, _ = generated_source
    _change_manifest(
        season,
        lambda manifest: manifest["opponent_adjustment"].__setitem__("pass_yard_multiplier", 2.0),
    )
    report = _audit(season)
    assert not report["passed"]
    assert any("profile" in error for error in report["errors"])


def test_expected_profile_drift_fails(generated_source: tuple[Path, Path]) -> None:
    season, _ = generated_source
    report = _audit(season, expected_profile={"pass_yard_multiplier": 2.0})
    assert not report["passed"]
    assert any("profile" in error for error in report["errors"])


@pytest.mark.parametrize("mutation", ["identity", "negative", "denominator"])
def test_invalid_normalized_stats_fail(generated_source: tuple[Path, Path], mutation: str) -> None:
    season, stats = generated_source
    path = stats / "Ironclads.json"
    data = json.loads(path.read_text())
    if mutation == "identity":
        data["season"] = 1999
    elif mutation == "negative":
        data["offense"]["passing"]["attempts"] = -1
    else:
        data["offense"]["passing"]["completions"] = 101
    path.write_text(json.dumps(data))
    report = _audit(season, stats_dir=stats)
    assert not report["passed"]
    assert any("Ironclads" in error for error in report["errors"])


def test_recorded_source_hash_mismatch_fails(generated_source: tuple[Path, Path]) -> None:
    season, stats = generated_source
    _change_manifest(
        season, lambda manifest: manifest.__setitem__("source_hashes", {"Ironclads.json": "0" * 64})
    )
    report = _audit(season, stats_dir=stats)
    assert not report["passed"]
    assert any("hash" in error for error in report["errors"])


def test_regenerated_chart_difference_fails(
    generated_source: tuple[Path, Path], tmp_path: Path
) -> None:
    season, _ = generated_source
    reproduced = tmp_path / "reproduced"
    shutil.copytree(season, reproduced)
    path = reproduced / "Ironclads" / "defense.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    report = _audit(season, reproduced_dir=reproduced)
    assert not report["passed"]
    assert any("reproduction" in error for error in report["errors"])


def test_matching_regeneration_passes(generated_source: tuple[Path, Path], tmp_path: Path) -> None:
    season, _ = generated_source
    reproduced = tmp_path / "reproduced"
    shutil.copytree(season, reproduced)
    assert _audit(season, reproduced_dir=reproduced)["passed"]


def test_structurally_invalid_chart_fails(generated_source: tuple[Path, Path]) -> None:
    season, _ = generated_source
    path = season / "Ironclads" / "offense.csv"
    path.write_text(path.read_text().replace("10,", "999,", 1))
    assert not _audit(season)["passed"]


def _contract(season: Path) -> dict:
    manifest = json.loads((season / "generation-manifest.json").read_text())
    counts = {
        "pass_attempts": 100,
        "completions": 60,
        "interceptions": 2,
        "sacks": 0,
        "passing_yards": 700,
        "rushing_attempts": 50,
        "rushing_yards": 200,
        "field_goal_attempts": 2,
        "field_goals_made": 1,
    }
    rates = {
        "completion_rate": 0.6,
        "interception_rate": 0.02,
        "sack_rate": 0.0,
        "yards_per_pass_attempt": 7.0,
        "rushing_yards_per_attempt": 4.0,
    }
    return {
        "schema_version": 1,
        "season": 2026,
        "games": 1,
        "attribution": manifest["source"],
        "generation_profile": manifest["calibration_profile"],
        "input_hashes": dict(manifest["input_hashes"]),
        "schedule": [{"away": "Ironclads", "home": "Thunderhawks"}],
        "teams": {
            name: {"games": 1, "counts": dict(counts), "rates": dict(rates)}
            for name in manifest["teams"]
        },
        "league": {
            "counts": {key: value * 2 for key, value in counts.items()},
            "rates": dict(rates),
        },
        "targets": {key: {"value": value, "tolerance": 0.1} for key, value in rates.items()},
        "chart_hashes": {
            str(path.relative_to(season)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in season.glob("*/*.csv")
        },
    }


def test_consistent_reviewed_contract_passes_without_raw_inputs(
    generated_source: tuple[Path, Path],
) -> None:
    season, _ = generated_source
    assert _audit(season, validation_contract=_contract(season))["passed"]


@pytest.mark.parametrize(
    "mutation",
    [
        "profile",
        "hash",
        "inventory",
        "season",
        "summary",
        "rate",
        "target",
        "schedule",
        "team_games",
    ],
)
def test_reviewed_contract_mutants_fail(generated_source: tuple[Path, Path], mutation: str) -> None:
    season, _ = generated_source
    contract = _contract(season)
    if mutation == "profile":
        contract["generation_profile"]["pass_yard_multiplier"] = 2.0
    elif mutation == "hash":
        contract["chart_hashes"]["Ironclads/defense.csv"] = "0" * 64
    elif mutation == "inventory":
        contract["chart_hashes"].pop("Ironclads/defense.csv")
    elif mutation == "season":
        contract["season"] = 1983
    elif mutation == "summary":
        contract["league"]["counts"]["completions"] += 1
    elif mutation == "rate":
        contract["teams"]["Ironclads"]["rates"]["completion_rate"] = 0.9
    elif mutation == "target":
        contract["targets"]["completion_rate"]["value"] = 0.9
    elif mutation == "schedule":
        contract["schedule"][0]["away"] = "Unknown"
    else:
        contract["teams"]["Ironclads"]["games"] = 99
    report = _audit(season, validation_contract=contract)
    assert not report["passed"]
    assert any("contract" in error for error in report["errors"])


def test_unreconciled_classified_source_count_fails(generated_source: tuple[Path, Path]) -> None:
    season, _ = generated_source
    _change_manifest(
        season,
        lambda manifest: manifest.__setitem__("diagnostics", {"interceptions": 5, "sacks": 0}),
    )
    report = _audit(season, validation_contract=_contract(season))
    assert not report["passed"]
    assert report["findings"][0]["code"] == "classified-source-count-mismatch"


def test_text_only_review_allowlist_cannot_reconcile_source_events(
    generated_source: tuple[Path, Path],
) -> None:
    season, _ = generated_source
    _change_manifest(
        season,
        lambda manifest: manifest.__setitem__("diagnostics", {"interceptions": 5, "sacks": 0}),
    )
    contract = _contract(season)
    contract["source_reconciliations"] = {
        "interceptions": {
            "classified": 5,
            "official": 4,
            "reviewed": True,
            "reason": "Synthetic nullified-play evidence",
        }
    }
    report = _audit(season, validation_contract=contract)
    assert not report["passed"]
    assert report["findings"][0]["severity"] == "error"


def test_team_source_discrepancies_cannot_cancel_at_league_level(
    generated_source: tuple[Path, Path],
) -> None:
    season, _ = generated_source
    _change_manifest(
        season,
        lambda manifest: (
            manifest["teams"]["Ironclads"].__setitem__("field_goal_attempts", 3),
            manifest["teams"]["Thunderhawks"].__setitem__("field_goal_attempts", 1),
        ),
    )
    report = _audit(season, validation_contract=_contract(season))
    assert not report["passed"]
    assert any(finding.get("team") == "Ironclads" for finding in report["findings"])


def test_current_normalized_inputs_must_match_reviewed_counts(
    generated_source: tuple[Path, Path],
) -> None:
    season, stats = generated_source
    contract = _contract(season)
    path = stats / "Ironclads.json"
    data = json.loads(path.read_text())
    data["offense"]["passing"]["yards"] = 800
    path.write_text(json.dumps(data))
    report = _audit(season, stats_dir=stats, validation_contract=contract)
    assert not report["passed"]
    assert any("normalized" in error and "contract" in error for error in report["errors"])


def test_reviewed_manifest_hash_detects_other_metadata_drift(
    generated_source: tuple[Path, Path],
) -> None:
    season, _ = generated_source
    contract = _contract(season)
    contract["generation_manifest_sha256"] = hashlib.sha256(
        (season / "generation-manifest.json").read_bytes()
    ).hexdigest()
    _change_manifest(season, lambda manifest: manifest.__setitem__("seed", 999))
    report = _audit(season, validation_contract=contract)
    assert not report["passed"]
    assert any("manifest hash" in error for error in report["errors"])


def test_contract_field_goal_makes_cannot_exceed_attempts(
    generated_source: tuple[Path, Path],
) -> None:
    season, _ = generated_source
    contract = _contract(season)
    contract["teams"]["Ironclads"]["counts"]["field_goals_made"] = 3
    contract["league"]["counts"]["field_goals_made"] = 4
    report = _audit(season, validation_contract=contract)
    assert not report["passed"]


def test_malformed_contract_with_raw_stats_returns_failing_report(
    generated_source: tuple[Path, Path],
) -> None:
    season, stats = generated_source
    contract = _contract(season)
    contract["teams"] = None
    report = _audit(season, stats_dir=stats, validation_contract=contract)
    assert not report["passed"]


def test_team_interception_mismatches_cannot_cancel_in_league_counts(generated_source):
    season, _ = generated_source
    def change(manifest):
        manifest["teams"]["Ironclads"]["source_event_counts"]["interceptions"] = 3
        manifest["teams"]["Thunderhawks"]["source_event_counts"]["interceptions"] = 1
    _change_manifest(season, change)
    result = _audit(season, validation_contract=_contract(season))
    assert not result["passed"]
    assert any("Ironclads" in error and "interceptions" in error for error in result["errors"])


def test_raw_input_hashes_are_checked_independently_of_count_identity(generated_source):
    season, stats = generated_source
    files = {f"normalized_stats/{p.name}": p for p in stats.glob("*.json")}
    contract = _contract(season)
    control = _audit(season, input_files=files, validation_contract=contract)
    assert control["passed"] and control["checks"]["raw_inputs"]
    assert control["checks"]["source_hashes"]
    assert not any("not cryptographically" in warning for warning in control["warnings"])
    path = stats / "Ironclads.json"
    path.write_text(path.read_text() + " ")  # Same parsed facts, different declared raw bytes.
    result = _audit(season, input_files=files, validation_contract=contract)
    assert not result["passed"]
    assert any("input hash" in error for error in result["errors"])


@pytest.mark.parametrize("mutation", [None, "not_applicable", "missing", "unknown", "inventory", "exclusions", "ledger", "credit"])
def test_nflverse_conversion_population_requires_complete_declared_coverage(
    generated_source: tuple[Path, Path], mutation: str | None,
) -> None:
    season, stats = generated_source
    def change(manifest: dict) -> None:
        manifest["source"] = "nflverse regular-season play-by-play"
        manifest["required_source_fields"] = {
            "unsupported_count": 0, "ledger_sha256": hashlib.sha256(b"[]\n").hexdigest(),
        }
        manifest["diagnostics"] = {"excluded_two_point_attempts": 2, "excluded_conversion_rows": 2}
        population = {"structured_flag_rows": 12, "unknown_flag_rows": 0,
                      "not_applicable_flag_rows": 0, "credited_offensive_attempts": 2,
                      "excluded_count": 2, "exclusion_ledger_sha256": "a" * 64}
        manifest["conversion_population"] = population
        if mutation == "not_applicable":
            population.update(structured_flag_rows=10, not_applicable_flag_rows=2)
        elif mutation == "credit":
            population["credited_offensive_attempts"] = 3
        elif mutation == "missing":
            manifest.pop("conversion_population")
        elif mutation == "unknown":
            population.update(structured_flag_rows=11, unknown_flag_rows=1)
        elif mutation == "inventory":
            population["structured_flag_rows"] = 13
        elif mutation == "exclusions":
            population["excluded_count"] = 0
        elif mutation == "ledger":
            population.pop("exclusion_ledger_sha256")
    _change_manifest(season, change)
    result = _audit(season, stats_dir=stats)
    assert result["passed"] is (mutation in (None, "not_applicable"))
    if mutation not in (None, "not_applicable"):
        assert any("conversion population" in error for error in result["errors"])


@pytest.mark.parametrize("field", ["missing_required_gains", "unknown_fumble_recoveries", "unreconciled_fumble_box"])
def test_source_with_unsupported_required_fields_cannot_certify(generated_source, field: str) -> None:
    season, stats = generated_source
    _change_manifest(season, lambda manifest: manifest.setdefault("diagnostics", {}).update({field: 1}))
    result = _audit(season, stats_dir=stats)
    assert not result["passed"]
    assert any(field in error for error in result["errors"])


@pytest.mark.parametrize("mutation", [None, "missing", "unknown_count", "nonzero_count", "missing_hash", "wrong_hash"])
def test_nflverse_required_source_capability_declaration_is_mandatory(generated_source, mutation):
    season, stats = generated_source

    def change(manifest):
        manifest["source"] = "nflverse regular-season play-by-play"
        manifest["conversion_population"] = {
            "structured_flag_rows": 12, "unknown_flag_rows": 0, "not_applicable_flag_rows": 0,
            "excluded_count": 0, "credited_offensive_attempts": 0, "exclusion_ledger_sha256": "a" * 64,
        }
        capability = {"unsupported_count": 0, "ledger_sha256": hashlib.sha256(b"[]\n").hexdigest()}
        manifest["required_source_fields"] = capability
        if mutation == "missing":
            manifest.pop("required_source_fields")
        elif mutation == "unknown_count":
            capability["unsupported_count"] = None
        elif mutation == "nonzero_count":
            capability["unsupported_count"] = 1
        elif mutation == "missing_hash":
            capability.pop("ledger_sha256")
        elif mutation == "wrong_hash":
            capability["ledger_sha256"] = hashlib.sha256(b'[{"field": "yards_gained"}]\n').hexdigest()

    _change_manifest(season, change)
    result = _audit(season, stats_dir=stats)
    assert result["passed"] is (mutation is None)
    if mutation is not None:
        assert any("required source fields" in error.lower() for error in result["errors"])

"""Synthetic modern preparation checks typed authority, exposure and code scope."""
import csv
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.test_chart_source_bundle import bundle_files, digest, inventory, prepare
from tests.test_nflverse_joint_adapter import MODE, POLICY, compound, losses, reviews


def bind(files: tuple) -> None:
    bundle, candidate, *_ = files
    inputs = {p.relative_to(bundle / "inputs").as_posix(): digest(p)
              for p in (bundle / "inputs").rglob("*") if p.is_file()}
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["input_hashes"] = inputs
    manifest_path.write_text(json.dumps(manifest))
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract.update(input_hashes=inputs, generation_manifest_sha256=digest(manifest_path))
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["expected_input_hashes"] = inputs
    recipe_path.write_text(json.dumps(recipe))
    inventory(bundle)


@pytest.fixture
def modern_bundle(tmp_path: Path) -> tuple:
    files = bundle_files.__wrapped__(tmp_path)
    bundle, candidate, _output, project, _calls = files
    raw = bundle / "inputs/play_by_play/source.csv"
    row = compound()
    with raw.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    with raw.open() as stream:
        serialized = next(csv.DictReader(stream))
    paths = {
        "fumble_review_evidence/evidence.pdf": b"%PDF-1.7\n<< /Type /Pages /Count 2 >>\n%%EOF",
        "team_map/map.json": json.dumps({"AAA": "A", "BBB": "B"}).encode(),
        "normalized_stats/B.json": b'{"season":2026,"team_name":"B"}',
    }
    for name, data in paths.items():
        path = bundle / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    pdf = bundle / "inputs/fumble_review_evidence/evidence.pdf"
    loss_path = bundle / "inputs/fumble_reviews/reviews.json"
    loss_path.parent.mkdir()
    loss_path.write_text(json.dumps([{**asdict(r), "evidence_file": "../fumble_review_evidence/evidence.pdf",
                                     "evidence_sha256": digest(pdf)}
                                    for r in reviews(serialized, losses("own_sack"))]))
    measurement = bundle / "inputs/shared_measurement/measurement.json"
    measurement.parent.mkdir()
    measurement.write_text(json.dumps({"shared_final_retention_pending": 0, "source_schedules_completed": 1,
        "games_completed": 1, "by_team_consumer": {
            f"{team}:interception": {"retained_terminal_segments": 10, "current_range": [10, 24]}
            for team in ("AAA", "BBB")}}))
    exposure = bundle / "inputs/shared_exposures/exposure.json"
    exposure.parent.mkdir()
    exposure.write_text(json.dumps({"source_sha256": digest(raw),
        "measurement_file": "../shared_measurement/measurement.json", "measurement_sha256": digest(measurement),
        "terminal_exposures_by_team": {"AAA": 10, "BBB": 10},
        "fumble_ranges_by_team": {team: [[10, 24], [25, 39]] for team in ("AAA", "BBB")}}))
    for name in ("generate_nflverse_charts.py", "nflverse_play_by_play.py", "nflverse_fumble_ledger.py",
                 "chart_generator.py", "fumble_source.py"):
        actual = project / name if name.startswith("generate_") else project / "paydirt" / name
        if not actual.exists():
            actual.write_text("# Synthetic bound projection code " + name)
        supplied = bundle / "inputs/projection_code" / name
        supplied.parent.mkdir(exist_ok=True)
        supplied.write_bytes(actual.read_bytes())
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(games=1, fumble_gain_model={"policy": POLICY},
                    ordered_fumble_projection={"mode": MODE, "fit_accepted": False})
    manifest_path.write_text(json.dumps(manifest))
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract["teams"]["B"] = {}
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["arguments"] += ["--fumble-gain-policy", POLICY, "--fumble-projection-mode", MODE,
        "--fumble-loss-reviews", "inputs/fumble_reviews/reviews.json",
        "--shared-return-exposures", "inputs/shared_exposures/exposure.json"]
    recipe_path.write_text(json.dumps(recipe))
    bind(files)
    return files


def test_typed_modern_recipe_passes_with_complete_scoped_bindings(modern_bundle: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    result = prepare(modern_bundle, monkeypatch)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert len(modern_bundle[-1]) == 1


@pytest.mark.parametrize("damage", [
    "missing_authority", "tampered_authority", "wrong_authority_scope", "unused_authority",
    "missing_measurement", "tampered_measurement", "wrong_exposure_source", "wrong_exposure_teams",
    "wrong_exposure_games", "pending_exposure", "wrong_ranges", "missing_code", "tampered_code",
    "unknown_code", "missing_mode", "wrong_mode", "missing_exposure_flag", "unknown_group",
    "duplicate_review_json",
])
def test_typed_modern_inputs_fail_before_execution_even_if_outer_hashes_rebound(
    modern_bundle: tuple, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    bundle, candidate, *_ = modern_bundle
    review = bundle / "inputs/fumble_reviews/reviews.json"
    measurement = bundle / "inputs/shared_measurement/measurement.json"
    exposure = bundle / "inputs/shared_exposures/exposure.json"
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    if damage == "missing_authority":
        (bundle / "inputs/fumble_review_evidence/evidence.pdf").unlink()
    elif damage == "tampered_authority":
        with (bundle / "inputs/fumble_review_evidence/evidence.pdf").open("ab") as stream:
            stream.write(b"Changed")
    elif damage in {"wrong_authority_scope", "unused_authority"}:
        data = json.loads(review.read_text())
        data[0]["raw_play_sha256" if damage == "unused_authority" else "fumbling_player_id"] = "0" * 64
        review.write_text(json.dumps(data))
    elif damage == "missing_measurement":
        measurement.unlink()
    elif damage == "tampered_measurement":
        measurement.write_text("{}")
    elif damage.startswith("wrong_exposure") or damage == "wrong_ranges":
        data = json.loads(exposure.read_text())
        if damage == "wrong_exposure_source": data["source_sha256"] = "0" * 64
        elif damage == "wrong_exposure_teams": data["terminal_exposures_by_team"] = {"AAA": 10}
        elif damage == "wrong_exposure_games":
            manifest_path = candidate / "generation-manifest.json"
            manifest = json.loads(manifest_path.read_text()); manifest["games"] = 2
            manifest_path.write_text(json.dumps(manifest))
        else: data["fumble_ranges_by_team"]["AAA"] = [[10, 25], [26, 39]]
        exposure.write_text(json.dumps(data))
    elif damage == "pending_exposure":
        data = json.loads(measurement.read_text()); data["shared_final_retention_pending"] = 1
        measurement.write_text(json.dumps(data))
        data = json.loads(exposure.read_text()); data["measurement_sha256"] = digest(measurement)
        exposure.write_text(json.dumps(data))
    elif damage in {"missing_code", "tampered_code", "unknown_code"}:
        path = bundle / "inputs/projection_code/fumble_source.py"
        if damage == "missing_code": path.unlink()
        elif damage == "tampered_code": path.write_text("# Unrelated rebound code")
        else: path.rename(path.with_name("unknown.py"))
    elif damage in {"missing_mode", "wrong_mode", "missing_exposure_flag"}:
        flag = "--shared-return-exposures" if damage == "missing_exposure_flag" else "--fumble-projection-mode"
        index = recipe["arguments"].index(flag)
        if damage == "wrong_mode": recipe["arguments"][index + 1] = "unreviewed_mode"
        else: del recipe["arguments"][index:index + 2]
    elif damage == "unknown_group":
        path = bundle / "inputs/unreviewed/other.json"; path.parent.mkdir(); path.write_text("{}")
    elif damage == "duplicate_review_json":
        review.write_text(review.read_text().replace('"ordinal":', '"ordinal": 1, "ordinal":', 1))
    recipe_path.write_text(json.dumps(recipe))
    bind(modern_bundle)
    result = prepare(modern_bundle, monkeypatch)
    assert result["passed"] is False and result["errors"]
    assert modern_bundle[-1] == []


def test_legacy_modern_single_source_recipe_control(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    files = bundle_files.__wrapped__(tmp_path)
    assert prepare(files, monkeypatch)["passed"]


@pytest.mark.parametrize("declared,selected", [
    (None, None), ("measured_diagnostic_v1", None),
    (None, "measured_diagnostic_v1"), ("measured_diagnostic_v1", "measured_diagnostic_v1"),
    ("source_primary_v1", "source_primary_v1"),
])
def test_typed_range_policy_binds_scalar_mode_without_treating_it_as_path(
    modern_bundle: tuple, monkeypatch: pytest.MonkeyPatch, declared: str | None, selected: str | None,
) -> None:
    bundle, candidate, *_ = modern_bundle
    path = candidate / "generation-manifest.json"
    data = json.loads(path.read_text())
    if declared is not None:
        data["ordered_fumble_projection"]["range_policy"] = declared
    path.write_text(json.dumps(data))
    path = bundle / "recipe.json"
    data = json.loads(path.read_text())
    if selected is not None:
        data["arguments"] += ["--fumble-range-policy", selected]
    path.write_text(json.dumps(data))
    bind(modern_bundle)
    result = prepare(modern_bundle, monkeypatch)
    assert result["passed"], result["errors"]
    assert len(modern_bundle[-1]) == 1


@pytest.mark.parametrize("declared,selected", [
    ("source_primary_v1", None), ("source_primary_v1", "measured_diagnostic_v1"),
    ("measured_diagnostic_v1", "source_primary_v1"), (None, "source_primary_v1"),
    ("unknown", None), ("source_primary_v1", "unknown"),
])
def test_typed_range_policy_mismatch_fails_before_generation(
    modern_bundle: tuple, monkeypatch: pytest.MonkeyPatch, declared: str | None, selected: str | None,
) -> None:
    bundle, candidate, *_ = modern_bundle
    path = candidate / "generation-manifest.json"
    data = json.loads(path.read_text())
    if declared is not None:
        data["ordered_fumble_projection"]["range_policy"] = declared
    path.write_text(json.dumps(data))
    path = bundle / "recipe.json"
    data = json.loads(path.read_text())
    if selected is not None:
        data["arguments"] += ["--fumble-range-policy", selected]
    path.write_text(json.dumps(data))
    bind(modern_bundle)
    result = prepare(modern_bundle, monkeypatch)
    assert not result["passed"]
    assert modern_bundle[-1] == []


@pytest.mark.parametrize("damage", ["wrong_source", "wrong_range", "pending", "missing_code", "tampered_authority"])
def test_typed_source_range_policy_preserves_complete_source_guards(
    modern_bundle: tuple, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    bundle, candidate, *_ = modern_bundle
    path = candidate / "generation-manifest.json"
    data = json.loads(path.read_text())
    data["ordered_fumble_projection"]["range_policy"] = "source_primary_v1"
    path.write_text(json.dumps(data))
    path = bundle / "recipe.json"
    data = json.loads(path.read_text())
    data["arguments"] += ["--fumble-range-policy", "source_primary_v1"]
    path.write_text(json.dumps(data))
    exposure = bundle / "inputs/shared_exposures/exposure.json"
    data = json.loads(exposure.read_text())
    if damage == "wrong_source":
        data["source_sha256"] = "0" * 64
    elif damage == "wrong_range":
        data["fumble_ranges_by_team"]["AAA"] = [[10, 25], [26, 39]]
    elif damage == "pending":
        path = bundle / "inputs/shared_measurement/measurement.json"
        report = json.loads(path.read_text())
        report["shared_final_retention_pending"] = 1
        path.write_text(json.dumps(report))
        data["measurement_sha256"] = digest(path)
    elif damage == "missing_code":
        (bundle / "inputs/projection_code/fumble_source.py").unlink()
    else:
        (bundle / "inputs/fumble_review_evidence/evidence.pdf").write_bytes(b"Changed authority")
    exposure.write_text(json.dumps(data))
    bind(modern_bundle)
    result = prepare(modern_bundle, monkeypatch)
    assert not result["passed"]
    assert modern_bundle[-1] == []

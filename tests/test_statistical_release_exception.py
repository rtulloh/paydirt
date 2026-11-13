"""Synthetic statistical acceptance cannot hide source or runtime failures."""

import hashlib
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from paydirt import chart_release_gate as gate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path
    shutil.copytree(Path(__file__).resolve().parents[1] / "seasons/2026", root / "canonical")
    shutil.copytree(root / "canonical", root / "public")
    shutil.copytree(root / "canonical", root / "reproduced")
    (root / "stats").mkdir()
    (root / "stats/Sample.json").write_text("{}")
    (root / "raw.html").write_text("Synthetic raw source")
    for name, value in {
        "AUTH.md": "Synthetic owner authorization",
        "contract.json": json.dumps({"season": 2026}),
        "engine.json": json.dumps({"metadata": {"policy": "chart-focused"}}),
    }.items():
        (root / name).write_text(value)
    manifest = root / "canonical/generation-manifest.json"
    manifest.write_text(
        json.dumps({"season": 2026, "calibration_profile": {"pass_interception_adjustment": 0.004}})
    )
    (root / "public/generation-manifest.json").write_text(
        json.dumps(
            {
                "season": 2026,
                "public_manifest_schema_version": 1,
                "original_generation_manifest_sha256": digest(manifest),
                "calibration_profile": {"pass_interception_adjustment": 0.004},
            }
        )
    )

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    def commit():
        git("add", ".")
        git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "reviewed synthetic evidence",
        )

    git("init", "-q")
    commit()
    authority = {
        "season": 2026,
        "commit": git("rev-parse", "HEAD"),
        "path": "AUTH.md",
        "sha256": digest(root / "AUTH.md"),
    }
    monkeypatch.setattr(gate, "STATISTICAL_RELEASE_AUTHORIZATION", authority, raising=False)
    failure = {
        "scope": "team",
        "team": "Sample",
        "metric": "interception_rate",
        "observed": 0.055,
        "target": 0.04,
        "tolerance": 0.01,
    }
    engine = {
        "passed": False,
        "errors": ["Sample interception_rate: 0.055000 differs from 0.040000 by more than 0.01"],
        "metrics": {},
        "team_metrics": {
            "Sample": {
                "interception_rate": {
                    **{k: failure[k] for k in ("observed", "target", "tolerance")},
                    "passed": False,
                }
            }
        },
        "measurement": {"passed": True, "errors": []},
    }
    components = {
        name: {"passed": True, "errors": []} for name in ("source", "tactics", "allocation")
    }
    components["source"]["checks"] = {
        name: True
        for name in ("raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder")
    }
    components["engine"] = engine
    monkeypatch.setattr(
        gate, "audit_release", lambda *args, **kwargs: {"components": deepcopy(components)}
    )
    nonfit = {"passed": True, "errors": []}

    def validate(*args, **kwargs):
        assert kwargs == {
            "minimum_team_games": 1000,
            "minimum_repetitions": 72,
            "require_fit": False,
        }
        return deepcopy(nonfit)

    monkeypatch.setattr(gate, "validate_engine_report", validate)
    def inventory(folder):
        return {str(p.relative_to(folder)): digest(p) for p in folder.rglob("*") if p.is_file()}
    policy = {
        "schema_version": 1,
        "season": 2026,
        "authorization_commit": authority["commit"],
        "authorization_sha256": authority["sha256"],
        "contract_sha256": digest(root / "contract.json"),
        "engine_report_sha256": digest(root / "engine.json"),
        "canonical_files": inventory(root / "canonical"),
        "public_files": inventory(root / "public"),
        "accepted_failures": [failure],
        "reason": "Synthetic disclosed exception only",
    }
    public_manifest = root / "public/generation-manifest.json"
    public_data = json.loads(public_manifest.read_text())
    public_data.update(
        accuracy_bounds_passed=False,
        known_accuracy_exceptions=[failure],
        chart_hashes={
            str(p.relative_to(root / "public")): digest(p)
            for p in (root / "public").glob("*/*.csv")
        },
    )
    public_manifest.write_text(json.dumps(public_data))
    policy["public_files"] = inventory(root / "public")

    def save(repin=True):
        (root / "policy.json").write_text(json.dumps(policy))
        commit()
        if repin:
            monkeypatch.setattr(
                gate,
                "STATISTICAL_RELEASE_POLICY",
                {
                    "commit": git("rev-parse", "HEAD"),
                    "path": "policy.json",
                    "sha256": digest(root / "policy.json"),
                },
                raising=False,
            )

    save()
    return root, policy, components, nonfit, save


def audit(case):
    root = case[0]
    function = getattr(gate, "audit_statistical_release_exception", None)
    assert callable(function), "Explicit hash-bound statistical acceptance is not implemented"
    return function(
        root,
        root / "canonical",
        root / "contract.json",
        root / "engine.json",
        root / "policy.json",
        public_dir=root / "public",
        stats_dir=root / "stats",
        reproduced_dir=root / "reproduced",
        input_files={"raw": root / "raw.html"},
    )


def test_exact_exception_accepts_without_relabeling_strict_fit(case):
    result = audit(case)
    assert result["passed"]
    assert result["strict_fit_passed"] is False
    assert result["release_accepted_with_statistical_exceptions"] is True
    assert result["release_certified"] is False


def test_derived_view_is_disclosed_and_used_by_both_validations(case, monkeypatch):
    calls = []
    view = {"metadata": {"policy": "chart-focused", "engine_fingerprint": "derived"}}
    receipt = {"report_engine_fingerprint": "original", "actual_engine_fingerprint": "derived"}

    def derive(root, report, season):
        assert "engine_fingerprint" not in report["metadata"]
        return view, receipt

    def strict(*args, **kwargs):
        calls.append(args[2])
        return {"components": deepcopy(case[2])}

    def nonfit(*args, **kwargs):
        calls.append(args[0])
        return deepcopy(case[3])

    monkeypatch.setattr(gate, "_version_only_1977_validation_view", derive, raising=False)
    monkeypatch.setattr(gate, "audit_release", strict)
    monkeypatch.setattr(gate, "validate_engine_report", nonfit)
    result = audit(case)
    assert result["passed"]
    assert calls == [view, view]
    assert result["runtime_version_equivalence"] == receipt
    assert "engine_fingerprint" not in json.loads((case[0] / "engine.json").read_text())["metadata"]


@pytest.mark.parametrize("component", ["source", "tactics", "allocation"])
def test_other_component_failure_is_never_excepted(case, component):
    case[2][component].update(passed=False, errors=["Nonstatistical defect"])
    assert not audit(case)["passed"]


@pytest.mark.parametrize(
    "check", ["raw_inputs", "normalized_stats", "source_hashes", "reproduction", "decoder"]
)
def test_source_summary_cannot_hide_unverified_check(case, check):
    case[2]["source"]["checks"][check] = False
    assert not audit(case)["passed"]


def test_insufficient_sample_or_runtime_mismatch_is_not_excepted(case):
    case[3].update(passed=False, errors=["Stale runtime or insufficient sample"])
    assert not audit(case)["passed"]


def test_observer_failure_is_not_excepted(case):
    case[2]["engine"]["measurement"].update(passed=False, errors=["Observer mismatch"])
    assert not audit(case)["passed"]


@pytest.mark.parametrize(
    "mutation",
    [
        "omitted",
        "target",
        "other_error",
        "canonical",
        "public",
        "engine",
        "season",
        "uncommitted",
        "authority",
    ],
)
def test_binding_and_exception_list_are_exact(case, mutation):
    root, policy, components, _, save = case
    if mutation == "omitted":
        policy["accepted_failures"] = []
    elif mutation == "target":
        policy["accepted_failures"][0]["target"] = 0.05
    elif mutation == "other_error":
        components["engine"]["errors"].append("Other nonstatistical failure")
    elif mutation in ("canonical", "public"):
        next((root / mutation).glob("*/offense.csv")).write_text("changed")
    elif mutation == "engine":
        (root / "engine.json").write_text("{}")
    elif mutation == "season":
        policy["season"] = 1977
    elif mutation == "authority":
        policy["authorization_commit"] = "0" * 40
    if mutation == "uncommitted":
        (root / "policy.json").write_text(json.dumps({**policy, "reason": "Unreviewed"}))
    else:
        save()
    assert not audit(case)["passed"]


def test_public_manifest_cannot_export_private_inventory(case):
    root, policy, _, _, save = case
    path = root / "public/generation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["input_hashes"] = {"private_source_game.html": "a" * 64}
    path.write_text(json.dumps(manifest))
    policy["public_files"]["generation-manifest.json"] = digest(path)
    save()
    assert not audit(case)["passed"]


def test_execution_report_cannot_change_during_acceptance(case, monkeypatch):
    def changed(*args, **kwargs):
        (case[0] / "engine.json").write_text("{}")
        return {"components": deepcopy(case[2])}

    monkeypatch.setattr(gate, "audit_release", changed)
    assert not audit(case)["passed"]


def test_new_commit_cannot_self_authorize_replacement_policy(case):
    case[1]["reason"] = "Replacement committed without trusted review pin"
    case[4](repin=False)
    assert not audit(case)["passed"]


def test_false_strict_summary_without_a_metric_failure_is_rejected(case):
    engine = case[2]["engine"]
    engine["errors"] = []
    engine["team_metrics"]["Sample"]["interception_rate"]["passed"] = True
    case[1]["accepted_failures"] = []
    case[4]()
    assert not audit(case)["passed"]


def test_public_team_metadata_cannot_export_private_inventory(case):
    root, policy, _, _, save = case
    path = root / "public/generation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["teams"] = {"Sample": {"private_input_hashes": {"private.html": "a" * 64}}}
    path.write_text(json.dumps(manifest))
    policy["public_files"]["generation-manifest.json"] = digest(path)
    save()
    assert not audit(case)["passed"]


@pytest.mark.parametrize("missing", ["offense.csv", "2026.yaml"])
def test_public_season_must_retain_all_gameplay_files(case, missing):
    root, policy, _, _, save = case
    next((root / "public").rglob(missing)).unlink()
    policy["public_files"] = {
        str(p.relative_to(root / "public")): digest(p)
        for p in (root / "public").rglob("*")
        if p.is_file()
    }
    save()
    assert not audit(case)["passed"]


@pytest.mark.parametrize(
    "field,value", [("accuracy_bounds_passed", True), ("known_accuracy_exceptions", [])]
)
def test_public_accuracy_disclosure_must_match_computed_failures(case, field, value):
    root, policy, _, _, save = case
    path = root / "public/generation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    policy["public_files"]["generation-manifest.json"] = digest(path)
    save()
    assert not audit(case)["passed"]


@pytest.mark.parametrize("changed", ["raw.html", "stats/Sample.json", "reproduced/2026.yaml"])
def test_source_evidence_cannot_change_during_acceptance(case, monkeypatch, changed):
    def mutate(*args, **kwargs):
        (case[0] / changed).write_text("changed after source validation")
        return {"components": deepcopy(case[2])}

    monkeypatch.setattr(gate, "audit_release", mutate)
    assert not audit(case)["passed"]


def test_local_generation_diagnostic_is_not_a_published_gameplay_file(case):
    root, policy, _, _, save = case
    path = root / "canonical/chart-audit.json"
    path.write_text("{}")
    policy["canonical_files"]["chart-audit.json"] = digest(path)
    save()
    assert audit(case)["passed"]


def test_public_chart_hash_provenance_matches_actual_csv_bytes(case):
    root, policy, _, _, save = case
    path = root / "public/generation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["chart_hashes"][next(iter(manifest["chart_hashes"]))] = "0" * 64
    path.write_text(json.dumps(manifest))
    policy["public_files"]["generation-manifest.json"] = digest(path)
    save()
    assert not audit(case)["passed"]


@pytest.mark.parametrize("public_count,expected", [(1, True), (2, False)])
def test_public_team_source_counts_match_canonical_manifest(case, public_count, expected):
    root, policy, _, _, save = case
    canonical = root / "canonical/generation-manifest.json"
    data = json.loads(canonical.read_text())
    data["teams"] = {"Sample": {"fumbles": 1}}
    canonical.write_text(json.dumps(data))
    policy["canonical_files"]["generation-manifest.json"] = digest(canonical)
    public = root / "public/generation-manifest.json"
    data = json.loads(public.read_text())
    data.update(
        teams={"Sample": {"fumbles": public_count}},
        original_generation_manifest_sha256=digest(canonical),
    )
    public.write_text(json.dumps(data))
    policy["public_files"]["generation-manifest.json"] = digest(public)
    save()
    assert audit(case)["passed"] is expected

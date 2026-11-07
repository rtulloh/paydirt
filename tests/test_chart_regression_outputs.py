"""Regression success requires actual, current, independently checked outputs."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
import paydirt.chart_source_bundle as sources
from tests import test_chart_readiness_freeze as freeze_support
from tests.test_ai_audit_report_validation import synthetic_report

freeze_files = freeze_support.freeze_files


def bind(path: Path, **extra: str) -> dict:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **extra}


def install_output_fixtures(root: Path, freeze: dict, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Only substitute the already-tested source/component evaluators."""
    contents = {}
    for name, entry in freeze["cohorts"].items():
        canonical = root / "seasons" / name
        if not canonical.exists():
            import shutil
            shutil.copytree(root / entry["season_dir"], canonical)
        year = 1983 if name == "1983-generated" else 2024
        (root / f"config/chart-validation/{year}.json").write_bytes((root / entry["contract"]["path"]).read_bytes())
        receipt = root / ".ai-audits/chart-sources" / str(1983 if name == "1983-generated" else 2024) / "source.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text('{"synthetic_source_receipt": true}\n')
    for name, season, count in (("public_ai", "2026", 2), ("local_ai", "1983", 28)):
        teams = [f"{season}/Synthetic{i:02d}" for i in range(count)]
        for team in teams:
            directory = root / "seasons" / team
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "team.yaml").write_text("Synthetic team\n")
            (directory / "offense.csv").write_text("Synthetic chart\n")
        report = synthetic_report(teams)
        contents[name + "_json"] = json.dumps(report)
        if name == "local_ai":
            stream = io.StringIO()
            fields = ("team", "difficulty", "mode", "down", "distance_band", "calls", "largest_share",
                      "distinct_plays", "longest_streak", "small_sample", "play_counts", "primary_play_shares")
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
                              for key, value in group.items()} for group in report["summary"]["situations"])
            contents["local_ai_csv"] = stream.getvalue()
    for year in (1983, 2024):
        contents[f"chart_{year}_json"] = json.dumps({
            "passed": True, "release_certified": False, "errors": [],
            "components": {name: {"passed": True, "errors": []} for name in ("source", "tactics", "allocation", "engine")},
            "engine_evidence": {"synthetic_season": year, "metadata": {"policy": "chart-focused", "seed": 20261108}},
            "scope": "Synthetic controls",
        })

    def prepared(receipt: Path, candidate: Path, contract: Path) -> dict:
        year = 1983 if candidate.name == "1983-generated" else 2024
        assert receipt == root / f".ai-audits/chart-sources/{year}/source.json"
        assert contract == (root / freeze["cohorts"][candidate.name]["contract"]["path"]).resolve()
        return {"stats_dir": receipt.parent / "stats", "reproduced_dir": receipt.parent / "reproduced",
                "input_files": {"synthetic": receipt}}

    def components(candidate: Path, contract: dict, report: dict, **options: object) -> dict:
        assert set(options) == {"stats_dir", "reproduced_dir", "input_files"}
        year = 1983 if candidate.name == "1983-generated" else 2024
        assert contract["season"] == year
        result = json.loads(contents[f"chart_{year}_json"])
        if report != result["engine_evidence"]:
            result.update(passed=False, errors=["Synthetic engine evidence fails independent validation"])
        return result

    monkeypatch.setattr(sources, "prepared_source_options", prepared)
    monkeypatch.setattr(gate, "audit_release", components)
    freeze["files"] = gate.readiness_file_inventory(root)
    return contents


@pytest.fixture
def output_files(freeze_files: tuple, monkeypatch: pytest.MonkeyPatch) -> tuple:
    root, freeze = freeze_files
    contents = install_output_fixtures(root, freeze, monkeypatch)
    artifacts = {}
    for label, content in contents.items():
        path = root / ".ai-audits/captured" / (label + (".csv" if label.endswith("_csv") else ".json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        command = gate.required_regression_commands()[label.rsplit("_", 1)[0]][1]
        original = root / command[command.index("--csv" if label.endswith("_csv") else "--output") + 1]
        artifacts[label] = bind(path, original_path=str(original))
    return root, freeze, {
        "schema_version": 1, "freeze_sha256": gate.readiness_freeze_fingerprint(freeze), "artifacts": artifacts,
        "ai_inputs": {name: gate.chart_fingerprint(root / "seasons" / year)
                      for name, year in (("public_ai", "2026"), ("local_ai", "1983"))},
        "source_receipts": {str(year): bind(root / f".ai-audits/chart-sources/{year}/source.json") for year in (1983, 2024)},
    }


def audit(files: tuple) -> dict:
    function = getattr(gate, "audit_regression_outputs", None)
    assert callable(function), "The gate must validate actual AI/CSV/chart outputs, not only exit logs"
    return function(*files)


def test_complete_regression_outputs_are_independently_checked_and_noncertifying(output_files: tuple) -> None:
    result = audit(output_files)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert set(result["artifacts"]) == set(output_files[2]["artifacts"])
    assert result["artifacts"]["local_ai_json"]["games"] == 448


def test_missing_ai_inputs_do_not_suppress_independent_chart_output_checks(output_files: tuple) -> None:
    root, freeze, data = output_files
    (root / "seasons/2026/Synthetic00/team.yaml").unlink()
    result = audit((root, freeze, data))
    assert not result["passed"] and result["errors"]
    assert result["artifacts"]["chart_1983_json"]["passed"]
    assert result["artifacts"]["chart_2024_json"]["passed"]
    assert result["artifacts"]["local_ai_json"]["passed"]


@pytest.mark.parametrize("mutation", [
    "wrong-version", "wrong-freeze", "self-declared-pass", "omitted-artifact", "extra-artifact",
    "bare-path", "bad-digest", "missing-file", "changed-bytes", "wrong-origin", "duplicate-json", "nonfinite-json",
    "empty-ai", "truncated-ai", "forged-ai-summary", "wrong-ai-input", "missing-ai-input", "changed-ai-chart",
    "missing-source-receipt", "changed-source-receipt", "substituted-source-receipt", "failed-source-recheck",
    "empty-csv", "csv-header", "csv-row", "csv-extra-row", "missing-engine", "wrong-engine",
    "stored-failure", "ignored-component-failure", "contradictory-errors", "wrong-promoted", "changed-code",
    "wrong-chart-policy", "wrong-chart-seed", "wrong-canonical-contract",
    "invalid-source-container", "invalid-artifact-container", "invalid-engine-metadata",
    "integer-pass-flag",
])
def test_failed_incomplete_or_stale_outputs_cannot_pass(output_files: tuple, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    root, freeze, original = output_files
    data = deepcopy(original)
    label = "local_ai_json"
    reference = data["artifacts"][label]
    path = Path(reference["path"])
    report = json.loads(path.read_text())
    rewrite = False
    if mutation == "wrong-version": data["schema_version"] = True
    elif mutation == "wrong-freeze": data["freeze_sha256"] = "0" * 64
    elif mutation == "self-declared-pass": data["passed"] = True
    elif mutation == "omitted-artifact": data["artifacts"].pop("chart_1983_json")
    elif mutation == "extra-artifact": data["artifacts"]["other"] = deepcopy(reference)
    elif mutation == "invalid-source-container": data["source_receipts"] = []
    elif mutation == "invalid-artifact-container": data["artifacts"] = []
    elif mutation == "bare-path": data["artifacts"][label] = reference["path"]
    elif mutation == "bad-digest": reference["sha256"] = "no"
    elif mutation == "missing-file": path.unlink()
    elif mutation == "changed-bytes": path.write_text("{}")
    elif mutation == "wrong-origin": reference["original_path"] = str(root / ".ai-audits/other.json")
    elif mutation == "duplicate-json": path.write_text('{"summary":{},"summary":{}}'); reference["sha256"] = bind(path)["sha256"]
    elif mutation == "nonfinite-json": path.write_text('{"summary":NaN}'); reference["sha256"] = bind(path)["sha256"]
    elif mutation == "empty-ai": report = {}; rewrite = True
    elif mutation == "truncated-ai": report["games"].pop(); rewrite = True
    elif mutation == "forged-ai-summary": report["summary"]["calls"] += 1; rewrite = True
    elif mutation == "wrong-ai-input": data["ai_inputs"]["public_ai"] = "0" * 64
    elif mutation == "missing-ai-input": data["ai_inputs"].pop("public_ai")
    elif mutation == "changed-ai-chart": (root / "seasons/2026/Synthetic00/offense.csv").write_text("Changed\n")
    elif mutation == "missing-source-receipt": data["source_receipts"].pop("2024")
    elif mutation == "changed-source-receipt": Path(data["source_receipts"]["2024"]["path"]).write_text("Changed\n")
    elif mutation == "substituted-source-receipt": data["source_receipts"]["2024"] = deepcopy(data["source_receipts"]["1983"])
    elif mutation == "failed-source-recheck":
        def fail(*args: object) -> dict:
            raise ValueError("Synthetic source preparation is stale")
        monkeypatch.setattr(sources, "prepared_source_options", fail)
    elif mutation.startswith("csv-") or mutation == "empty-csv":
        reference = data["artifacts"]["local_ai_csv"]; path = Path(reference["path"])
        text = path.read_text()
        if mutation == "empty-csv": text = ""
        elif mutation == "csv-header": text = text.replace("team,", "other,", 1)
        elif mutation == "csv-row": text = text.replace("1983/Synthetic00", "1983/Substituted", 1)
        else: text += text.splitlines(keepends=True)[1]
        path.write_text(text); reference["sha256"] = bind(path)["sha256"]
    elif mutation in {"missing-engine", "wrong-engine", "stored-failure", "ignored-component-failure", "contradictory-errors", "wrong-chart-policy", "wrong-chart-seed", "invalid-engine-metadata", "integer-pass-flag"}:
        reference = data["artifacts"]["chart_2024_json"]; path = Path(reference["path"])
        report = json.loads(path.read_text()); rewrite = True
        if mutation == "missing-engine": report.pop("engine_evidence")
        elif mutation == "wrong-engine": report["engine_evidence"]["synthetic_season"] = 1983
        elif mutation == "stored-failure": report["passed"] = False
        elif mutation == "ignored-component-failure": report["components"]["allocation"]["passed"] = False
        elif mutation == "wrong-chart-policy": report["engine_evidence"]["metadata"]["policy"] = "balanced"
        elif mutation == "wrong-chart-seed": report["engine_evidence"]["metadata"]["seed"] = 1
        elif mutation == "invalid-engine-metadata": report["engine_evidence"]["metadata"] = None
        elif mutation == "integer-pass-flag": report["components"]["allocation"]["passed"] = 1
        else: report["errors"] = ["Synthetic failure hidden by PASS"]
    elif mutation == "wrong-promoted": (root / "seasons/2024/offense.csv").write_text("Changed\n")
    elif mutation == "changed-code": (root / "paydirt/game_engine.py").write_text("Changed\n")
    elif mutation == "wrong-canonical-contract":
        path = root / "config/chart-validation/2024.json"
        path.write_text('{"season":2024,"teams":{}}')
        freeze = deepcopy(freeze)
        freeze["files"] = gate.readiness_file_inventory(root)
        data["freeze_sha256"] = gate.readiness_freeze_fingerprint(freeze)
    if rewrite:
        path.write_text(json.dumps(report)); reference["sha256"] = bind(path)["sha256"]
    result = audit((root, freeze, data))
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False
    assert set(result["artifacts"]) == set(original["artifacts"])


@pytest.mark.parametrize("target", ["artifact", "ai-input", "source-receipt"])
def test_outputs_changed_during_validation_are_rejected(output_files: tuple, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    root, freeze, data = output_files
    original = gate.audit_release
    def change(*args: object, **kwargs: object) -> dict:
        result = original(*args, **kwargs)
        if target == "artifact": path = Path(data["artifacts"]["public_ai_json"]["path"])
        elif target == "source-receipt": path = Path(data["source_receipts"]["1983"]["path"])
        else: path = root / "seasons/2026/Synthetic00/offense.csv"
        path.write_text("Changed after first read\n")
        return result
    monkeypatch.setattr(gate, "audit_release", change)
    result = audit((root, freeze, data))
    assert not result["passed"] and any("changed" in error.lower() for error in result["errors"])

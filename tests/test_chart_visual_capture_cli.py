"""The existing gate CLI validates saved preview evidence without starting games."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import audit_generated_charts as cli
from tests import test_chart_visual_capture as capture_support

capture_files = capture_support.capture_files
freeze_files = capture_support.freeze_files


def inputs(files: tuple, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    root, freeze, evidence = files
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *args, **kwargs: pytest.fail("Saved capture validation must not start games"))
    folder = root / ".ai-audits" / "visual-inputs"
    folder.mkdir()
    freeze_path, evidence_path = folder / "freeze.json", folder / "evidence.json"
    freeze_path.write_text(json.dumps(freeze))
    evidence_path.write_text(json.dumps(evidence))
    return freeze_path, evidence_path, root / ".ai-audits" / "visual-result.json"


@pytest.mark.parametrize("valid", [True, False])
def test_visual_cli_validates_saved_captures(capture_files: tuple, monkeypatch: pytest.MonkeyPatch, valid: bool) -> None:
    freeze, evidence, output = inputs(capture_files, monkeypatch)
    if not valid:
        data = json.loads(evidence.read_text())
        data["contexts"][0]["capture"]["sha256"] = "0" * 64
        evidence.write_text(json.dumps(data))
    assert cli.main(["--visual-capture", str(evidence), "--freeze", str(freeze), "--output", str(output)]) == (0 if valid else 1)
    result = json.loads(output.read_text())
    assert result["passed"] is valid
    assert result["release_certified"] is False
    assert result["selection_validated"] is False


@pytest.mark.parametrize("extra", [["--engine-only"], ["--season-dir", "other"], ["--contract", "other"],
                                  ["--campaign-bundle", "other"], ["--policy", "hard"], ["--seed", "1"],
                                  ["--repetitions", "1"], ["--workers", "1"]])
def test_visual_cli_rejects_execution_options(capture_files: tuple, monkeypatch: pytest.MonkeyPatch, extra: list[str]) -> None:
    freeze, evidence, output = inputs(capture_files, monkeypatch)
    assert cli.main(["--visual-capture", str(evidence), "--freeze", str(freeze), "--output", str(output), *extra]) == 1


@pytest.mark.parametrize("target", ["freeze", "evidence", "receipt", "image", "chart", "new-chart", "implementation"])
def test_visual_cli_preserves_inputs_and_candidates(capture_files: tuple, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    root, freeze_data, data = capture_files
    freeze, evidence, _output = inputs(capture_files, monkeypatch)
    receipt = root / data["contexts"][0]["capture"]["path"]
    image = root / json.loads(receipt.read_text())["sections"]["offense"]["screenshot"]["path"]
    candidate = root / freeze_data["cohorts"]["2024"]["season_dir"]
    outputs = {"freeze": freeze, "evidence": evidence, "receipt": receipt, "image": image,
               "chart": candidate / "offense.csv", "new-chart": candidate / "extra.json",
               "implementation": root / "paydirt" / "new.py"}
    output = outputs[target]
    before = output.read_bytes() if output.exists() else None
    assert cli.main(["--visual-capture", str(evidence), "--freeze", str(freeze), "--output", str(output)]) == 1
    assert (output.read_bytes() if output.exists() else None) == before


@pytest.mark.parametrize("missing", ["freeze", "evidence"])
def test_visual_cli_requires_both_inputs(capture_files: tuple, monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    freeze, evidence, output = inputs(capture_files, monkeypatch)
    args = ["--output", str(output)]
    args.extend(["--freeze", str(freeze)] if missing == "evidence" else ["--visual-capture", str(evidence)])
    assert cli.main(args) == 1


@pytest.mark.parametrize("bad_freeze", [{"cohorts": []}, {"cohorts": {"2024": {"source_inputs": []}}}])
def test_visual_cli_records_malformed_freezes_without_crashing(
    capture_files: tuple, monkeypatch: pytest.MonkeyPatch, bad_freeze: dict,
) -> None:
    freeze, evidence, output = inputs(capture_files, monkeypatch)
    freeze.write_text(json.dumps(bad_freeze))
    assert cli.main(["--visual-capture", str(evidence), "--freeze", str(freeze), "--output", str(output)]) == 1
    assert not output.exists()


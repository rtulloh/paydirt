"""Weighted reference integration uses synthetic corpora and public sample teams."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_reference_audit as reference
import paydirt.chart_release_gate as gate
from tests import test_chart_reference_corpus as support

bind = support.bind
freeze_files = support.freeze_files
reference_files = support.reference_files
rebind = support.rebind


def weighted(data: tuple) -> dict:
    function = getattr(gate, "audit_reference_weighted_evidence", None)
    assert callable(function), "Existing gate must bind exact weighted diagnostics to the private preflight"
    return function(*data[:3])


def test_complete_weighted_gate_is_bound_and_never_certifies(reference_files: tuple) -> None:
    result = weighted(reference_files)
    assert result["passed"], result["errors"]
    assert result["corpus_validated"] and result["weighted_validated"]
    assert result["reference_bytes_read"] and result["weighted"]["behavior_matches_reference"]
    assert len(result["weighted"]["teams"]) == 28
    assert set(result["preflights"]) == {"before", "after"}
    assert not result["stateful_crossed_complete"] and not result["benchmark_complete"]
    assert not result["source_accepted"] and not result["ready_for_owner_review"] and not result["release_certified"]
    assert all(len(values) == 8 for values in reference_files[-1].values())


@pytest.mark.parametrize("mutation", ["source", "training", "freeze", "decoder"])
def test_failed_preflight_never_starts_weighted_comparison(
    reference_files: tuple, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    root, freeze, evidence, corpus, reports, _calls = reference_files
    if mutation == "source":
        bind(root, root / evidence["source_receipts"]["2024"]["path"], {"valid": False})
    elif mutation == "training":
        reports["2024"]["valid"] = False
        rebind(reference_files, "2024")
    elif mutation == "freeze":
        freeze["schema_version"] = 0
    else:
        path = corpus / "RefSynthetic0/offense.csv"
        path.write_text(path.read_text().replace(",B,", ",UNSUPPORTED,", 1))
    def forbidden(*args: object) -> dict:
        pytest.fail("Invalid preflight must not start weighted reference inspection")
    monkeypatch.setattr(reference, "compare_reference_weighted", forbidden)
    result = weighted(reference_files)
    assert not result["passed"] and result["errors"] and not result["weighted_validated"]
    assert not result["benchmark_complete"] and not result["release_certified"]


@pytest.mark.parametrize("mutation", [
    "candidate", "corpus", "source", "training", "code", "freeze", "declaration",
    "exception", "malformed", "failed", "incomplete", "load-failed",
])
def test_weighted_gate_rechecks_dependencies_and_retains_failure(
    reference_files: tuple, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    root, freeze, evidence, corpus, _reports, _calls = reference_files
    original = reference.compare_reference_weighted
    load = reference.load_team_chart if hasattr(reference, "load_team_chart") else None
    def changed(generated: dict, originals: dict) -> dict:
        if mutation == "exception":
            raise RuntimeError("Synthetic weighted failure")
        result = original(generated, originals)
        if mutation == "malformed":
            return []
        if mutation == "failed":
            result["passed"] = False
            result["errors"].append("Synthetic weighted discrepancy")
        elif mutation == "incomplete":
            result["teams"].pop("Synthetic0")
        elif mutation == "candidate":
            path = root / freeze["cohorts"]["1983-generated"]["season_dir"] / "Synthetic0/offense.csv"
            path.write_text(path.read_text() + "\n")
        elif mutation == "corpus":
            (corpus / "new-empty-directory").mkdir()
        elif mutation == "source":
            path = root / evidence["source_receipts"]["2024"]["path"]
            path.write_text(path.read_text() + "\n")
        elif mutation == "training":
            path = root / evidence["training"]["2024"]["path"]
            path.write_text(path.read_text() + "\n")
        elif mutation == "code":
            (root / "paydirt/game_engine.py").write_text("# changed\n")
        elif mutation == "freeze":
            freeze["protocol_sha256"] = "0" * 64
        elif mutation == "declaration":
            evidence["corpus"]["teams"]["Synthetic0"]["prior_use"] = "changed during comparison"
        return result
    if mutation == "load-failed":
        assert callable(load), "Reference gate needs the core chart loader"
        def broken(directory: str) -> object:
            if Path(directory).name == "RefSynthetic0":
                raise ValueError("Synthetic chart load failure")
            return load(directory)
        monkeypatch.setattr(reference, "load_team_chart", broken)
    monkeypatch.setattr(reference, "compare_reference_weighted", changed)
    result = weighted(reference_files)
    assert not result["passed"] and result["errors"]
    assert not result["weighted_validated"] and not result["corpus_validated"]
    assert not result["benchmark_complete"] and not result["release_certified"]
    assert "after" in result["preflights"], "Weighted failures still require final dependency revalidation"


@pytest.mark.parametrize("mutation", ["none", "no-corpus", "no-freeze", "public-output", "overwrite", "changed-declaration"])
def test_cli_routes_weighted_reference_through_private_output_and_final_binding(
    reference_files: tuple, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    from scripts import audit_generated_charts as cli
    root, freeze, evidence, _corpus, _reports, _calls = reference_files
    monkeypatch.setattr(cli, "ROOT", root)
    freeze_path, evidence_path = root / ".ai-audits/freeze.json", root / ".ai-audits/reference.json"
    bind(root, freeze_path, freeze)
    bind(root, evidence_path, evidence)
    output = root / ".ai-audits/chart-reference-comparison/weighted.json"
    if mutation == "public-output":
        output = root / "weighted-public.json"
    elif mutation == "overwrite":
        output.parent.mkdir(parents=True)
        output.write_text("owner sentinel")
    function = getattr(gate, "audit_reference_weighted_evidence", None)
    assert callable(function), "Weighted CLI requires the maintained gate API"
    def checked(*args: object) -> dict:
        result = function(*args)
        if mutation == "changed-declaration":
            evidence_path.write_text(evidence_path.read_text() + "\n")
        return result
    monkeypatch.setattr(gate, "audit_reference_weighted_evidence", checked)
    arguments = ["--reference-weighted", "--output", str(output)]
    if mutation != "no-corpus":
        arguments += ["--reference-corpus", str(evidence_path)]
    if mutation != "no-freeze":
        arguments += ["--freeze", str(freeze_path)]
    before = deepcopy(freeze), deepcopy(evidence)
    status = cli.main(arguments)
    assert status == (0 if mutation == "none" else 1)
    if mutation in {"none", "changed-declaration"}:
        result = json.loads(output.read_text())
        assert result["weighted_validated"] is (mutation == "none")
        assert not result["benchmark_complete"] and not result["release_certified"]
    elif mutation == "overwrite":
        assert output.read_text() == "owner sentinel"
    else:
        assert not output.exists()
    assert (freeze, evidence) == before

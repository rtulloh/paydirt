"""Boundary integration stubs use public synthetic reports, never private charts."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

import paydirt.chart_reference_audit as reference
import paydirt.chart_reference_context_audit as contexts
import paydirt.chart_release_gate as gate
from tests import test_chart_reference_corpus as support
from tests.test_chart_reference_weighted import team

bind = support.bind
freeze_files = support.freeze_files
reference_files = support.reference_files
rebind = support.rebind


@pytest.fixture(scope="session")
def real_context_report() -> dict:
    originals = {name: team(name) for name in ("Alpha", "Beta")}
    result = reference.compare_reference_contexts(deepcopy(originals), originals)
    assert result["passed"], result["errors"]
    return result


def validate(report: dict, names: set[str]) -> None:
    function = getattr(contexts, "validate_context_collection", None)
    assert callable(function), (
        "Context gate must independently reconcile its complete collection census"
    )
    function(report, names)


@pytest.fixture
def context_evidence(
    reference_files: tuple, real_context_report: dict, monkeypatch: pytest.MonkeyPatch
) -> tuple:
    """Scale a public stub for boundary tests; this is not 28-team play evidence."""
    source = deepcopy(real_context_report["teams"]["Alpha"])
    for scenario in source["scenarios"].values():
        for bucket in scenario.values():
            for field in ("attempted", "trials", "selected_calls", "penalty_decisions"):
                bucket[field] *= 27
            for field in (
                "official",
                "home_stats",
                "away_stats",
                "counts",
                "result_counts",
                "terminations",
                "sequence_lengths",
                "totals",
            ):
                bucket[field] = {key: value * 27 for key, value in bucket[field].items()}

    def collect(generated: dict, originals: dict) -> dict:
        assert set(generated) == set(originals) and len(generated) == 28
        result = {
            key: deepcopy(value) for key, value in real_context_report.items() if key != "teams"
        }
        result.update(
            expected_trials=28 * 27 * 54 * 6 * 4,
            attempted_trials=28 * 27 * 54 * 6 * 4,
            completed_trials=28 * 27 * 54 * 6 * 4,
            teams={name: source for name in sorted(generated)},
            rankings={label: sorted(generated) for label in ("rr", "gr", "rg", "gg")},
        )
        return result

    monkeypatch.setattr(reference, "compare_reference_contexts", collect)
    return (*reference_files, collect)


def audit(data: tuple) -> dict:
    function = getattr(gate, "audit_reference_context_evidence", None)
    assert callable(function), "Existing gate must guard complete stateful reference collection"
    return function(*data[:3])


def test_real_public_collection_census_validates_without_acceptance(
    real_context_report: dict,
) -> None:
    validate(real_context_report, {"Alpha", "Beta"})
    assert (
        not real_context_report["stateful_crossed_complete"]
        and not real_context_report["benchmark_complete"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "master",
        "contexts",
        "team",
        "scenario",
        "bucket",
        "short",
        "failed",
        "bool",
        "ratio",
        "sequence",
        "official",
        "digest",
        "contrasts",
        "formations",
        "ranking",
    ],
)
def test_collection_census_rejects_incomplete_or_inconsistent_report(
    real_context_report: dict, mutation: str
) -> None:
    result = deepcopy(real_context_report)
    details = result["teams"]["Alpha"]
    scenario = details["scenarios"]["rr"]
    key = next(iter(scenario))
    bucket = scenario[key]
    if mutation == "schema":
        result["passed"] = "yes"
    elif mutation == "master":
        result["metadata"]["master"] = 20461108
    elif mutation == "contexts":
        result["context_grid"].pop()
    elif mutation == "team":
        result["teams"].pop("Beta")
    elif mutation == "scenario":
        details["scenarios"].pop("gg")
    elif mutation == "bucket":
        scenario.pop(key)
    elif mutation == "short":
        bucket["trials"] = 0
    elif mutation == "failed":
        result["failed_trials"] = 1
    elif mutation == "bool":
        bucket["selected_calls"] = True
    elif mutation == "ratio":
        bucket["per_trial"]["net_offensive_yards"] = [999, 1]
    elif mutation == "sequence":
        bucket["sequence_lengths"] = {"4": 3}
    elif mutation == "official":
        bucket["official"]["offensive_plays"] += 1
    elif mutation == "digest":
        bucket["receipt_sha256"] = "missing"
    elif mutation == "contrasts":
        details["contrasts"].pop(key)
    elif mutation == "formations":
        details["formation_contrasts"]["rr"].pop(key)
    else:
        result["rankings"]["gg"] = ["Alpha"]
    with pytest.raises((ValueError, TypeError, KeyError)):
        validate(result, {"Alpha", "Beta"})


def test_complete_stateful_gate_revalidates_preflight_and_remains_noncertifying(
    context_evidence: tuple,
) -> None:
    result = audit(context_evidence)
    assert result["passed"], result["errors"]
    assert (
        result["contexts_validated"]
        and result["corpus_validated"]
        and result["reference_bytes_read"]
    )
    assert set(result["preflights"]) == {"before", "after"}
    assert len(result["contexts"]["teams"]) == 28
    assert not result["stateful_crossed_complete"] and not result["benchmark_complete"]
    assert (
        not result["source_accepted"]
        and not result["ready_for_owner_review"]
        and not result["release_certified"]
    )
    assert all(len(values) == 8 for values in context_evidence[-2].values())


@pytest.mark.parametrize("mutation", ["source", "training", "freeze", "corpus"])
def test_failed_dependencies_prevent_stateful_collection(
    context_evidence: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root, freeze, evidence, corpus, reports, _calls, _collect = context_evidence
    if mutation == "source":
        bind(root, root / evidence["source_receipts"]["2024"]["path"], {"valid": False})
    elif mutation == "training":
        reports["2024"]["valid"] = False
        rebind(context_evidence[:6], "2024")
    elif mutation == "freeze":
        freeze["schema_version"] = 0
    else:
        (corpus / "extra-directory").mkdir()

    def forbidden(*args: object) -> dict:
        pytest.fail("Failed preflight must not start stateful collection")

    monkeypatch.setattr(reference, "compare_reference_contexts", forbidden)
    result = audit(context_evidence)
    assert not result["passed"] and result["errors"] and not result["contexts_validated"]
    assert not result["benchmark_complete"] and not result["release_certified"]


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "corpus",
        "source",
        "training",
        "code",
        "declaration",
        "exception",
        "malformed",
        "failed",
        "incomplete",
        "short",
    ],
)
def test_stateful_gate_rechecks_after_collection_failure_or_late_change(
    context_evidence: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root, freeze, evidence, corpus, _reports, _calls, collect = context_evidence

    def changed(*args: object) -> dict:
        if mutation == "exception":
            raise RuntimeError("Synthetic context collection failure")
        result = collect(*args)
        if mutation == "malformed":
            return []
        if mutation == "failed":
            result["errors"].append("Synthetic context failure")
        elif mutation == "incomplete":
            result["teams"].pop("Synthetic0")
        elif mutation == "short":
            result["completed_trials"] -= 1
        elif mutation == "candidate":
            path = (
                root / freeze["cohorts"]["1983-generated"]["season_dir"] / "Synthetic0/offense.csv"
            )
            path.write_text(path.read_text() + "\n")
        elif mutation == "corpus":
            (corpus / "new-directory").mkdir()
        elif mutation == "source":
            path = root / evidence["source_receipts"]["2024"]["path"]
            path.write_text(path.read_text() + "\n")
        elif mutation == "training":
            path = root / evidence["training"]["2024"]["path"]
            path.write_text(path.read_text() + "\n")
        elif mutation == "code":
            (root / "paydirt/game_engine.py").write_text("# changed\n")
        else:
            evidence["corpus"]["teams"]["Synthetic0"]["prior_use"] = "changed"
        return result

    monkeypatch.setattr(reference, "compare_reference_contexts", changed)
    result = audit(context_evidence)
    assert not result["passed"] and result["errors"] and not result["contexts_validated"]
    assert (
        not result["corpus_validated"]
        and not result["benchmark_complete"]
        and not result["release_certified"]
    )
    assert "after" in result["preflights"]


@pytest.mark.parametrize(
    "mutation",
    ["none", "no-corpus", "no-freeze", "both", "public-output", "overwrite", "changed-declaration"],
)
def test_context_cli_obeys_private_output_and_final_binding(
    context_evidence: tuple,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    from scripts import audit_generated_charts as cli

    root, freeze, evidence, _corpus, _reports, _calls, _collect = context_evidence
    monkeypatch.setattr(cli, "ROOT", root)
    freeze_path, declaration_path = (
        root / ".ai-audits/freeze.json",
        root / ".ai-audits/declaration.json",
    )
    bind(root, freeze_path, freeze)
    bind(root, declaration_path, evidence)
    output = root / ".ai-audits/chart-reference-comparison/contexts.json"
    if mutation == "public-output":
        output = root / "contexts-public.json"
    elif mutation == "overwrite":
        output.parent.mkdir(parents=True)
        output.write_text("owner sentinel")
    function = getattr(gate, "audit_reference_context_evidence", None)
    assert callable(function), "Context CLI requires the maintained gate"

    def checked(*args: object) -> dict:
        result = function(*args)
        if mutation == "changed-declaration":
            declaration_path.write_text(declaration_path.read_text() + "\n")
        return result

    monkeypatch.setattr(gate, "audit_reference_context_evidence", checked)
    args = ["--reference-contexts", "--output", str(output)]
    if mutation != "no-corpus":
        args += ["--reference-corpus", str(declaration_path)]
    if mutation != "no-freeze":
        args += ["--freeze", str(freeze_path)]
    if mutation == "both":
        args += ["--reference-weighted"]
    status = cli.main(args)
    assert status == (0 if mutation == "none" else 1)
    if mutation in {"none", "changed-declaration"}:
        result = json.loads(output.read_text())
        assert result["contexts_validated"] is (mutation == "none")
        assert not result["benchmark_complete"] and not result["release_certified"]
    elif mutation == "overwrite":
        assert output.read_text() == "owner sentinel"
    else:
        assert not output.exists()

"""A campaign inventory must reject absent or substituted charter evidence."""

from copy import deepcopy
from pathlib import Path

import pytest

from paydirt import chart_release_gate as gate


def _report(policy: str, seed: int) -> dict:
    return {"metadata": {"policy": policy, "seed": seed}}


def _cohorts() -> dict:
    return {
        name: {
            "season_dir": Path("synthetic") / name,
            "contract": {"season": year, "teams": {
                f"Synthetic {index}": {} for index in range(count)
            }},
            "training": _report("chart-focused", 20261108),
            "held_out": _report("chart-focused", 20361108),
            "policies": {policy: _report(policy, 20261108) for policy in (
                "hard", "balanced", "run-heavy", "pass-heavy",
                "repeat-line-plunge", "repeat-off-tackle", "repeat-end-run", "repeat-draw",
                "repeat-screen", "repeat-short-pass", "repeat-medium-pass",
                "repeat-long-pass", "repeat-te-short-long",
            )},
        }
        for name, year, count in (("1983-generated", 1983, 28), ("2024", 2024, 32))
    }


@pytest.fixture
def validated_reports(monkeypatch):
    calls = []

    def validate(report, contract, directory, **kwargs):
        calls.append((report, contract, directory, kwargs))
        return {"passed": True, "errors": []}

    monkeypatch.setattr(gate, "validate_engine_report", validate)
    return calls


def test_campaign_bundle_requires_actual_exposure_per_family(validated_reports) -> None:
    report = gate.audit_campaign_bundle(_cohorts())
    assert report["passed"]
    assert report["release_certified"] is False
    assert len(validated_reports) == 30
    for source, _, _, requirements in validated_reports:
        policy = source["metadata"]["policy"]
        assert requirements == {
            "minimum_team_games": 1000 if policy == "chart-focused" else (
                128 if policy in {"hard", "balanced"} else 16
            ),
            "minimum_repetitions": 64 if policy == "chart-focused" else (
                8 if policy in {"hard", "balanced"} else 1
            ),
            "require_fit": policy == "chart-focused",
        }


@pytest.mark.parametrize("cohort", ["1983-generated", "2024"])
@pytest.mark.parametrize("missing", ["cohort", "training", "held_out", "hard", "balanced",
                                     "run-heavy", "pass-heavy", "repeat-line-plunge",
                                     "repeat-off-tackle", "repeat-end-run", "repeat-draw",
                                     "repeat-screen", "repeat-short-pass", "repeat-medium-pass",
                                     "repeat-long-pass", "repeat-te-short-long"])
def test_every_cohort_and_campaign_family_is_mandatory(validated_reports, cohort, missing) -> None:
    cohorts = _cohorts()
    if missing == "cohort":
        del cohorts[cohort]
    elif missing in {"training", "held_out"}:
        del cohorts[cohort][missing]
    else:
        del cohorts[cohort]["policies"][missing]
    result = gate.audit_campaign_bundle(cohorts)
    assert not result["passed"]
    assert any(cohort in error for error in result["errors"])


@pytest.mark.parametrize("mutation", ["heldout_seed", "training_seed", "heldout_policy",
                                      "policy_label", "policy_reserved_seed", "missing_team", "season"])
def test_substituted_population_or_policy_is_rejected(validated_reports, mutation) -> None:
    cohorts = _cohorts()
    cohort = cohorts["2024"]
    if mutation == "heldout_seed":
        cohort["held_out"]["metadata"]["seed"] = 20261108
    elif mutation == "training_seed":
        cohort["training"]["metadata"]["seed"] = 20361108
    elif mutation == "heldout_policy":
        cohort["held_out"]["metadata"]["policy"] = "hard"
    elif mutation == "policy_label":
        cohort["policies"]["hard"]["metadata"]["policy"] = "balanced"
    elif mutation == "policy_reserved_seed":
        cohort["policies"]["hard"]["metadata"]["seed"] = 20361108
    elif mutation == "missing_team":
        cohort["contract"]["teams"].pop("Synthetic 0")
    else:
        cohort["contract"]["season"] = 2023
    assert not gate.audit_campaign_bundle(cohorts)["passed"]


@pytest.mark.parametrize("bad_result", [{"passed": False, "errors": []},
                                       {"passed": True, "errors": ["bad individual team"]},
                                       {}, {"passed": "yes", "errors": []}])
def test_nested_validation_failure_cannot_hide_in_bundle(monkeypatch, bad_result) -> None:
    def validate(report, *_args, **_kwargs):
        if report["metadata"]["policy"] == "hard":
            return deepcopy(bad_result)
        return {"passed": True, "errors": []}

    monkeypatch.setattr(gate, "validate_engine_report", validate)
    result = gate.audit_campaign_bundle(_cohorts())
    assert not result["passed"]
    assert any("hard" in error for error in result["errors"])


def test_validator_exception_preserves_other_campaign_results(monkeypatch) -> None:
    def validate(report, *_args, **_kwargs):
        if report["metadata"]["policy"] == "hard":
            raise ValueError("unreadable evidence")
        return {"passed": True, "errors": []}

    monkeypatch.setattr(gate, "validate_engine_report", validate)
    result = gate.audit_campaign_bundle(_cohorts())
    assert not result["passed"]
    assert "held_out" in result["cohorts"]["2024"]
    assert any("unreadable evidence" in error for error in result["errors"])

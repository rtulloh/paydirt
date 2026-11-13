"""Paired reference campaign controls use only public sample charts."""

from __future__ import annotations

import csv
import math
import shutil
import statistics
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_reference_audit as reference
from paydirt.chart_engine_audit import REQUIRED_METRICS, run_engine_audit, validate_engine_report

PUBLIC = Path(__file__).resolve().parents[1] / "seasons/2026"
METRICS = (
    *REQUIRED_METRICS,
    "points_per_team_game",
    "plays_per_team_game",
    "fumble_loss_rate_per_play",
    "field_goal_rate",
)


@pytest.fixture(scope="module")
def paired_reports(tmp_path_factory: pytest.TempPathFactory) -> tuple:
    root = tmp_path_factory.mktemp("paired-public")
    generated, originals = root / "2026-generated", root / "2026-reference"
    mapping = {"Ironclads": "ReferenceIron", "Thunderhawks": "ReferenceThunder"}
    for directory in (generated, originals):
        directory.mkdir()
        shutil.copy2(PUBLIC / "2026.yaml", directory / "2026.yaml")
    for name, other in mapping.items():
        shutil.copytree(PUBLIC / name, generated / name)
        shutil.copytree(PUBLIC / name, originals / other)
    # Change synthetic copied gains, not public files or source target facts.
    offense = generated / "Ironclads/offense.csv"
    rows = list(csv.reader(offense.read_text().splitlines()))
    for row in rows[1:]:
        for column in range(1, 10):
            if row[column].lstrip("-").isdigit():
                row[column] = str(int(row[column]) + 2)
    with offense.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    schedule = [("Ironclads", "Thunderhawks"), ("Thunderhawks", "Ironclads")]
    mapped = [(mapping[away], mapping[home]) for away, home in schedule]
    # These real games are explicitly training diagnostics, never reserved outcomes.
    reports = (
        run_engine_audit(generated, schedule, repetitions=2, seed=20261108),
        run_engine_audit(originals, mapped, repetitions=2, seed=20261108),
    )
    original = reports[1]
    contract = {
        "schedule": schedule,
        "targets": {
            key: {"value": original["league"][key], "tolerance": 0.01} for key in REQUIRED_METRICS
        },
        "teams": {
            name: {
                "rates": {
                    key: original["teams"][original["metadata"]["team_names"][other]][key]
                    for key in REQUIRED_METRICS
                }
            }
            for name, other in mapping.items()
        },
    }
    return *reports, contract, generated, originals, mapping


def compare(data: tuple, **options: object) -> dict:
    function = getattr(reference, "compare_reference_campaigns", None)
    assert callable(function), (
        "Paired reference comparison must reconcile actual full-engine reports"
    )
    return function(*data, master=20261108, **options)


def test_public_fixture_reports_are_valid_complete_engine_controls(paired_reports: tuple) -> None:
    generated, original, contract, directory, other, mapping = paired_reports
    mapped = deepcopy(contract)
    mapped["schedule"] = [(mapping[away], mapping[home]) for away, home in contract["schedule"]]
    mapped["teams"] = {mapping[name]: target for name, target in contract["teams"].items()}
    for report, source, path in ((generated, contract, directory), (original, mapped, other)):
        result = validate_engine_report(
            report, source, path, minimum_repetitions=1, minimum_team_games=1, require_fit=False
        )
        assert result["passed"], result["errors"]
        assert len(report["game_receipts"]) == 4
    assert validate_engine_report(original, mapped, other, minimum_team_games=1)["passed"]


def test_complete_training_pairs_preserve_inputs_mapping_and_source_fit_failures(
    paired_reports: tuple,
) -> None:
    before = deepcopy(paired_reports[:3])
    result = compare(paired_reports)
    assert result["passed"], result["errors"]
    assert result["paired_validated"] and not result["exposure_complete"]
    assert not result["benchmark_complete"] and not result["source_accepted"]
    assert not result["ready_for_owner_review"] and not result["release_certified"]
    assert result["coverage"]["paired_games"] == result["coverage"]["games_per_set"] == 4
    assert result["coverage"]["repetitions"] == 2
    assert result["coverage"]["team_games"] == {"Ironclads": 4, "Thunderhawks": 4}
    assert (
        result["sets"]["generated"]["mechanics"]["passed"]
        and result["sets"]["reference"]["mechanics"]["passed"]
    )
    assert not result["sets"]["generated"]["source_fit"]["passed"]
    assert result["sets"]["reference"]["source_fit"]["passed"]
    assert set(result["teams"]) == set(paired_reports[-1])
    assert len(result["game_pairs"]) == 4
    assert paired_reports[:3] == before


def test_pairing_uses_mapped_matchups_and_initial_seed_without_assuming_equal_paths(
    paired_reports: tuple,
) -> None:
    result = compare(paired_reports)
    generated, original, contract, _directory, _other, mapping = paired_reports
    assert result["passed"], result["errors"]
    for index, pair in enumerate(result["game_pairs"]):
        away, home = contract["schedule"][index % 2]
        assert (pair["away"], pair["home"]) == (away, home)
        assert (pair["reference_away"], pair["reference_home"]) == (mapping[away], mapping[home])
        assert pair["seed"] == 20261108 + (index // 2) * 1000003 + (index % 2) * 1009
        assert pair["score_delta"] == {
            side: generated["game_receipts"][index][side + "_score"]
            - original["game_receipts"][index][side + "_score"]
            for side in ("away", "home")
        }
    assert any(
        pair["score_delta"]["away"] or pair["score_delta"]["home"] for pair in result["game_pairs"]
    )
    assert "diverge" in result["interpretation"]


def test_uncertainty_uses_paired_repetition_differences_and_keeps_aggregate_delta_separate(
    paired_reports: tuple,
) -> None:
    result = compare(paired_reports)
    generated, original, _contract, _directory, _other, mapping = paired_reports
    assert result["passed"], result["errors"]
    for label in ("league", *mapping):
        for metric in METRICS:

            def values(
                report: dict,
                index: int,
                reference_side: bool = False,
                label: str = label,
                metric: str = metric,
            ) -> float:
                replication = report["replications"][index]
                if label == "league":
                    return replication["league"][metric]
                folder = mapping[label] if reference_side else label
                return replication["teams"][report["metadata"]["team_names"][folder]][metric]

            differences = [
                values(generated, index) - values(original, index, True) for index in range(2)
            ]
            summary = result["paired"][label][metric]
            assert summary["replications"] == 2
            assert summary["mean_repetition_delta"] == pytest.approx(statistics.mean(differences))
            assert summary["between_repetition_standard_error"] == pytest.approx(
                statistics.stdev(differences) / math.sqrt(2)
            )
            assert summary["minimum"] == min(differences) and summary["maximum"] == max(differences)
    assert any(result["league"][metric]["delta"] for metric in METRICS)


def test_call_and_tail_summaries_keep_mapped_identifiers_and_denominators(
    paired_reports: tuple,
) -> None:
    result = compare(paired_reports)
    assert result["passed"], result["errors"]
    for label, report in zip(("generated", "reference"), paired_reports[:2]):
        diagnostics = result["sets"][label]["diagnostics"]
        assert sum(row["count"] for row in diagnostics["call_mix"]) == sum(
            len(game["decision_results"]) for game in report["game_receipts"]
        )
        assert {row["situation"][0] for row in diagnostics["call_mix"]} <= set(paired_reports[-1])
        assert set(diagnostics["primary_tails"]) == set(paired_reports[-1])
        for tails in diagnostics["primary_tails"].values():
            assert (
                0
                <= tails["explosive_40"]
                <= tails["explosive_20"]
                <= tails["retained_primary_calls"]
            )
            assert tails["losses"] + tails["zero_gains"] <= tails["retained_primary_calls"]
    assert all(
        set(names) == set(paired_reports[-1]) for names in result["rankings"]["generated"].values()
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "seed",
        "policy",
        "repetitions-bool",
        "unequal-repetitions",
        "missing-game",
        "pending",
        "decision",
        "count",
        "derived",
        "runtime",
        "replications",
        "score",
    ],
)
def test_invalid_raw_campaign_is_rejected_without_discarding_the_other_set(
    paired_reports: tuple, mutation: str
) -> None:
    data = list(deepcopy(paired_reports))
    report = data[0]
    if mutation == "seed":
        report["metadata"]["seed"] += 1
    elif mutation == "policy":
        report["metadata"]["policy"] = "hard"
    elif mutation == "repetitions-bool":
        report["metadata"]["repetitions"] = True
    elif mutation == "unequal-repetitions":
        report["metadata"]["repetitions"] = 3
    elif mutation == "missing-game":
        report["game_receipts"].pop()
    elif mutation == "pending":
        report["game_receipts"][0]["untimed_down"] = True
    elif mutation == "decision":
        report["game_receipts"][0]["decision_results"].pop()
    elif mutation == "count":
        next(iter(report["teams"].values()))["offensive_plays"] += 1
    elif mutation == "derived":
        report["league"]["completion_rate"] = float("nan")
    elif mutation == "runtime":
        report["metadata"]["runtime_identity"] = {}
    elif mutation == "replications":
        report["replications"].pop()
    else:
        report["game_receipts"][0]["home_score"] = True
    result = compare(tuple(data))
    assert not result["passed"] and result["errors"] and not result["paired_validated"]
    assert not result["benchmark_complete"] and not result["source_accepted"]
    assert not result["sets"]["generated"]["mechanics"]["passed"]
    assert result["sets"]["reference"]["mechanics"]["passed"]


def test_both_raw_failures_are_retained(paired_reports: tuple) -> None:
    data = list(deepcopy(paired_reports))
    data[0]["game_receipts"].pop()
    data[1]["game_receipts"].pop()
    result = compare(tuple(data))
    assert not result["passed"] and len(result["errors"]) >= 2
    assert all(
        not result["sets"][label]["mechanics"]["passed"] for label in ("generated", "reference")
    )


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "duplicate", "escape", "targets", "schedule"]
)
def test_incomplete_mapping_or_source_schedule_cannot_yield_partial_pairs(
    paired_reports: tuple, mutation: str
) -> None:
    data = list(deepcopy(paired_reports))
    if mutation == "missing":
        data[-1].pop("Ironclads")
    elif mutation == "extra":
        data[-1]["Other"] = "Other"
    elif mutation == "duplicate":
        data[-1]["Ironclads"] = data[-1]["Thunderhawks"]
    elif mutation == "escape":
        data[-1]["Ironclads"] = "../ReferenceIron"
    elif mutation == "targets":
        data[2]["teams"].pop("Ironclads")
    else:
        data[2]["schedule"][0] = ("Other", "Ironclads")
    result = compare(tuple(data))
    assert not result["passed"] and result["errors"] and not result["paired_validated"]
    assert not result["exposure_complete"] and not result["release_certified"]


def test_default_protocol_rejects_training_seed_even_if_otherwise_valid(
    paired_reports: tuple,
) -> None:
    function = getattr(reference, "compare_reference_campaigns", None)
    assert callable(function), "Default paired protocol must use its reserved comparison master"
    result = function(*paired_reports)
    assert not result["passed"] and result["errors"] and not result["exposure_complete"]


def test_single_training_repetition_has_no_sampling_standard_error(paired_reports: tuple) -> None:
    _generated, _original, contract, directory, other, mapping = paired_reports
    mapped = [(mapping[away], mapping[home]) for away, home in contract["schedule"]]
    generated = run_engine_audit(directory, contract["schedule"], repetitions=1, seed=20261108)
    original = run_engine_audit(other, mapped, repetitions=1, seed=20261108)
    result = compare((generated, original, contract, directory, other, mapping))
    assert result["passed"] and not result["exposure_complete"]
    assert all(
        value["replications"] == 1 and value["between_repetition_standard_error"] is None
        for values in result["paired"].values()
        for value in values.values()
    )


@pytest.mark.parametrize("master", [True, -1, "20261108"])
def test_invalid_declared_master_is_rejected(paired_reports: tuple, master: object) -> None:
    function = getattr(reference, "compare_reference_campaigns", None)
    assert callable(function), "Paired master must be a nonnegative integer"
    result = function(*paired_reports, master=master)
    assert not result["passed"] and result["errors"] and not result["paired_validated"]


@pytest.mark.parametrize(
    "metric",
    ["points_per_team_game", "plays_per_team_game", "fumble_loss_rate_per_play", "field_goal_rate"],
)
def test_all_displayed_derived_rates_are_reconciled_with_raw_counts(
    paired_reports: tuple, metric: str
) -> None:
    data = list(deepcopy(paired_reports))
    data[0]["league"][metric] += 1
    result = compare(tuple(data))
    assert not result["passed"] and result["errors"] and not result["paired_validated"]
    assert not result["sets"]["generated"]["mechanics"]["passed"]
    assert result["sets"]["reference"]["mechanics"]["passed"]

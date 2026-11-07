"""Release evidence must be fresh, complete and accurate, not merely playable."""
from copy import deepcopy
from pathlib import Path

import pytest

from paydirt.chart_engine_audit import (
    audit_observer_conformance,
    run_engine_audit,
    validate_engine_report,
)

PUBLIC = Path(__file__).resolve().parents[1] / "seasons" / "2026"
METRICS = (
    "completion_rate", "interception_rate", "sack_rate",
    "yards_per_pass_attempt", "rushing_yards_per_attempt",
)


@pytest.fixture(scope="module")
def engine_evidence() -> tuple[dict, dict]:
    schedule = [("Ironclads", "Thunderhawks"), ("Thunderhawks", "Ironclads")]
    report = run_engine_audit(PUBLIC, schedule, repetitions=1, seed=20261106)
    contract = {
        "schedule": schedule,
        "targets": {name: {"value": report["league"][name], "tolerance": 0.01}
                    for name in METRICS},
    }
    return report, contract


def test_current_complete_real_engine_evidence_passes(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = engine_evidence
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert result["passed"], result["errors"]
    assert report["league"]["games"] == 2
    assert all(team["team_games"] == 2 for team in report["teams"].values())
    assert report["metadata"]["policy"] == "chart-focused"


@pytest.mark.parametrize("policy,play", [
    ("repeat-line-plunge", "LINE_PLUNGE"), ("repeat-off-tackle", "OFF_TACKLE"),
    ("repeat-end-run", "END_RUN"), ("repeat-draw", "DRAW"),
    ("repeat-screen", "SCREEN"), ("repeat-short-pass", "SHORT_PASS"),
    ("repeat-medium-pass", "MEDIUM_PASS"), ("repeat-long-pass", "LONG_PASS"),
    ("repeat-te-short-long", "TE_SHORT_LONG"),
])
def test_single_call_stress_uses_declared_call_and_finishes_legally(policy, play) -> None:
    schedule = [("Ironclads", "Thunderhawks")]
    report = run_engine_audit(PUBLIC, schedule, repetitions=1, seed=20261108, policy=policy)
    normal = [call for game in report["game_receipts"] for call in game["decision_results"]
              if call["situation"][5] == "normal"]
    assert normal
    assert {call["situation"][1] for call in normal} == {play}
    assert report["league"]["games"] == 1
    assert all(game["game_over"] and not game["untimed_down"] for game in report["game_receipts"])
    contract = {"schedule": schedule, "targets": {metric: {"value": 100, "tolerance": .01}
                                                for metric in METRICS}}
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=1,
                                    minimum_repetitions=1, require_fit=False)
    assert result["passed"], result["errors"]


def _with_team_targets(report: dict, contract: dict) -> dict:
    """Use public-fixture counts as synthetic targets, independent of local seasons."""
    contract["teams"] = {
        folder: {"rates": {metric: report["teams"][name][metric] for metric in METRICS}}
        for folder, name in report["metadata"]["team_names"].items()
    }
    return contract


@pytest.mark.parametrize("metric,drift", [
    ("completion_rate", .031), ("interception_rate", .011), ("sack_rate", .016),
    ("yards_per_pass_attempt", .751), ("rushing_yards_per_attempt", .401),
])
def test_individual_team_failure_cannot_hide_behind_passing_league(
    engine_evidence: tuple[dict, dict], metric: str, drift: float,
) -> None:
    report, contract = deepcopy(engine_evidence)
    _with_team_targets(report, contract)
    folder = next(iter(contract["teams"]))
    contract["teams"][folder]["rates"][metric] += drift
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert result["metrics"][metric]["passed"]  # League is deliberately unchanged.
    assert any(folder in error and metric in error for error in result["errors"])


def test_team_targets_within_fixed_bounds_pass(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = deepcopy(engine_evidence)
    _with_team_targets(report, contract)
    for team in contract["teams"].values():
        team["rates"]["completion_rate"] += .029
        team["rates"]["yards_per_pass_attempt"] += .749
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert result["passed"], result["errors"]
    assert result["team_metrics"]
    assert result["maximum_team_errors"]["completion_rate"] == pytest.approx(.029)


def test_team_derived_metric_corruption_is_rejected(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = deepcopy(engine_evidence)
    _with_team_targets(report, contract)
    name = next(iter(report["teams"]))
    report["teams"][name]["completion_rate"] += .01
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("derived metric" in error for error in result["errors"])


def test_missing_team_target_is_rejected(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = deepcopy(engine_evidence)
    _with_team_targets(report, contract)
    contract["teams"].pop(next(iter(contract["teams"])))
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("team target" in error.casefold() for error in result["errors"])


@pytest.mark.parametrize("metric", METRICS)
def test_source_metric_drift_blocks_release(engine_evidence: tuple[dict, dict], metric: str) -> None:
    report, contract = deepcopy(engine_evidence)
    contract["targets"][metric]["value"] += 0.1
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any(metric in error for error in result["errors"])


@pytest.mark.parametrize("fingerprint", ("engine_fingerprint", "chart_fingerprint"))
def test_stale_engine_or_chart_evidence_blocks_release(engine_evidence: tuple[dict, dict], fingerprint: str) -> None:
    report, contract = deepcopy(engine_evidence)
    report["metadata"][fingerprint] = "stale"
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any(fingerprint in error for error in result["errors"])


def test_incomplete_team_sample_blocks_release(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = engine_evidence
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=1000)
    assert not result["passed"]
    assert any("sample" in error for error in result["errors"])


def test_changed_schedule_and_missing_team_block_release(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = deepcopy(engine_evidence)
    report["teams"].pop(next(iter(report["teams"])))
    contract["schedule"].append(("Ironclads", "Thunderhawks"))
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=1)
    assert not result["passed"]
    assert any("schedule" in error or "teams" in error for error in result["errors"])


@pytest.mark.parametrize("mutation", ("nonfinite", "missing", "totals", "policy"))
def test_invalid_or_mislabeled_evidence_cannot_pass(engine_evidence: tuple[dict, dict], mutation: str) -> None:
    report, contract = deepcopy(engine_evidence)
    if mutation == "nonfinite":
        report["league"]["completion_rate"] = float("nan")
    elif mutation == "missing":
        del contract["targets"]["completion_rate"]
    elif mutation == "totals":
        report["league"]["pass_attempts"] += 1
    else:
        report["metadata"]["policy"] = "unknown"
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]


def test_schedule_cannot_escape_the_candidate_directory() -> None:
    with pytest.raises(ValueError, match="team"):
        run_engine_audit(PUBLIC, [("../1983", "Ironclads")], repetitions=1, seed=1)


def test_measurement_gate_rejects_double_counted_qt_fumbles(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_calibration import EngineCalibrationObserver
    original = EngineCalibrationObserver.on_result

    def broken(self: EngineCalibrationObserver, game: object, outcome: object) -> None:
        original(self, game, outcome)
        totals = self.team_totals("SYN")
        totals.pass_attempts += 1
        totals.completions += 1

    monkeypatch.setattr(EngineCalibrationObserver, "on_result", broken)
    result = audit_observer_conformance()
    assert not result["passed"]
    assert any("observer" in error for error in result["errors"])


def test_corrected_observer_matches_real_engine_denominators() -> None:
    result = audit_observer_conformance()
    assert result["passed"], result["errors"]
    assert len(result["checks"]) == 34
    assert {case["case"] for case in result["checks"]} >= {"QT/0", "QT/F"}


def test_measurement_gate_rejects_counted_offsetting_plays(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_calibration import EngineCalibrationObserver
    original = EngineCalibrationObserver.on_result

    def broken(self: EngineCalibrationObserver, game: object, outcome: object) -> None:
        choice = outcome.penalty_choice
        if choice is not None and choice.offsetting:
            outcome.penalty_choice = None
        try:
            original(self, game, outcome)
        finally:
            outcome.penalty_choice = choice

    monkeypatch.setattr(EngineCalibrationObserver, "on_result", broken)
    result = audit_observer_conformance()
    assert not result["passed"]
    assert any("offsetting" in error for error in result["errors"])


def test_internally_impossible_play_denominators_block_release(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = deepcopy(engine_evidence)
    report["league"]["offensive_plays"] += 1
    next(iter(report["teams"].values()))["offensive_plays"] += 1
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("denominator" in error for error in result["errors"])


def test_engine_evidence_preserves_each_game_and_independent_replication(engine_evidence):
    report, contract = engine_evidence
    receipts = report.get("game_receipts", [])
    assert len(receipts) == report["league"]["games"] == 2
    assert [item["seed"] for item in receipts] == [20261106, 20261106 + 1009]
    assert [(item["away"], item["home"]) for item in receipts] == contract["schedule"]
    assert all(item["game_over"] and not item["untimed_down"] for item in receipts)
    assert report["replications"][0]["league"]["games"] == 2
    for values in report["uncertainty"]["league"].values():
        assert values["replications"] == 1
        assert values["between_repetition_standard_error"] is None


@pytest.mark.parametrize("mutation", ["missing", "seed", "score", "denominator", "yards"])
def test_invalid_individual_game_cannot_hide_in_aggregate(engine_evidence, mutation):
    report, contract = deepcopy(engine_evidence)
    receipts = report.setdefault("game_receipts", [{"seed": 20261106, "teams": {}}])
    if mutation == "missing":
        receipts.pop()
    elif mutation == "seed":
        receipts[0]["seed"] += 1
    elif mutation == "score":
        receipts[0]["game_over"] = False
    else:
        # Baseline has no receipts. Supply a corrupt record so failure must be
        # attributable to validation rather than a missing fixture key.
        values = next(iter(receipts[0]["teams"].values()), {})
        if mutation == "denominator":
            values["offensive_plays"] = values.get("offensive_plays", 0) + 1
        else:
            values["total_yards"] = values.get("total_yards", 0) + 1
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("game" in reason.casefold() for reason in result["errors"])


@pytest.mark.parametrize("policy", ["hard", "balanced", "run-heavy", "pass-heavy"])
def test_policy_sensitivity_requires_mechanics_without_reference_fit(policy):
    report = run_engine_audit(PUBLIC, [("Ironclads", "Thunderhawks")],
                              repetitions=1, seed=20261108, policy=policy)
    contract = {"schedule": [("Ironclads", "Thunderhawks")]}
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=1,
                                    require_fit=False)
    assert result["passed"], result["errors"]
    assert result["fit_required"] is False
    assert report["metadata"]["policy"] == policy
    assert report["call_mix"]
    assert report["game_receipts"][0]["game_over"]


@pytest.mark.parametrize("mutation", ["final_score", "replication", "uncertainty"])
def test_game_scores_and_sampling_evidence_reconcile_with_receipts(engine_evidence, mutation):
    report, contract = deepcopy(engine_evidence)
    if mutation == "final_score":
        report["game_receipts"][0]["home_score"] += 1
    elif mutation == "replication":
        report["replications"][0]["league"]["completions"] += 1
    else:
        report["uncertainty"]["league"]["completion_rate"]["minimum"] += .1
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any(mutation.replace("final_", "") in error.casefold()
               for error in result["errors"])



def test_modified_loaded_observer_cannot_receive_source_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_calibration import EngineCalibrationObserver

    original = EngineCalibrationObserver.on_result
    def broken(self, game, outcome):
        original(self, game, outcome)
        for totals in self._teams.values():
            totals.field_goal_attempts = totals.field_goals_made = 0
    monkeypatch.setattr(EngineCalibrationObserver, "on_result", broken)
    with pytest.raises(RuntimeError, match="loaded runtime"):
        run_engine_audit(PUBLIC, [("Ironclads", "Thunderhawks"), ("Thunderhawks", "Ironclads")],
                         repetitions=1, seed=20261106)


def test_changed_loaded_code_origin_cannot_receive_source_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_calibration import EngineCalibrationObserver

    function = EngineCalibrationObserver.on_result
    monkeypatch.setattr(function, "__code__", function.__code__.replace(co_filename="/tmp/another-checkout/chart_calibration.py"))
    with pytest.raises(RuntimeError, match="loaded runtime"):
        run_engine_audit(PUBLIC, [("Ironclads", "Thunderhawks")], repetitions=1, seed=20261106)


def test_missing_loaded_runtime_identity_is_rejected(engine_evidence: tuple[dict, dict]) -> None:
    report, contract = deepcopy(engine_evidence)
    report["metadata"].pop("runtime_identity", None)
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("runtime" in error for error in result["errors"])


@pytest.mark.parametrize("mutation", ["alias", "policy", "repeat_policy", "origin"])
def test_loaded_runtime_alias_policy_and_module_origin_match_sources(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    import paydirt.chart_calibration as calibration
    import paydirt.chart_engine_audit as audit

    if mutation == "alias":
        original = audit.run_auto_game
        monkeypatch.setattr(audit, "run_auto_game", lambda *a, **kw: original(*a, **kw))
    elif mutation == "policy":
        monkeypatch.setattr(audit, "_OFFENSE_WEIGHTS", (1,) * 9)
    elif mutation == "repeat_policy":
        monkeypatch.setitem(audit._POLICY_WEIGHTS, "repeat-screen", (1,) * 9)
    else:
        monkeypatch.setattr(calibration, "__file__", "/tmp/another-checkout/chart_calibration.py")
    with pytest.raises(RuntimeError, match="loaded runtime"):
        run_engine_audit(PUBLIC, [("Ironclads", "Thunderhawks")], repetitions=1, seed=20261106)


def test_observer_conformance_exercises_field_goals_and_zero_sack() -> None:
    result = audit_observer_conformance()
    assert result["passed"], result["errors"]
    assert {case["case"] for case in result["checks"]} >= {"FG/made", "FG/missed", "QT/SACK 0"}



def test_observer_conformance_rejects_erased_field_goal_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_calibration import EngineCalibrationObserver

    original = EngineCalibrationObserver.on_result
    def broken(self, game, outcome):
        original(self, game, outcome)
        for totals in self._teams.values():
            totals.field_goal_attempts = totals.field_goals_made = 0
    monkeypatch.setattr(EngineCalibrationObserver, "on_result", broken)
    result = audit_observer_conformance()
    assert not result["passed"]
    assert any("field goal" in error.lower() for error in result["errors"])



def test_spawned_workers_bind_the_same_loaded_execution_identity() -> None:
    schedule = [("Ironclads", "Thunderhawks")]
    report = run_engine_audit(PUBLIC, schedule, repetitions=2, seed=20261106, workers=2)
    metadata = report["metadata"]
    assert metadata["worker_runtime_identities"] == [metadata["runtime_identity"]] * 2
    result = validate_engine_report(report, {"schedule": schedule}, PUBLIC,
                                    minimum_team_games=2, require_fit=False)
    assert result["passed"], result["errors"]


@pytest.mark.parametrize("mutation", [
    "missing_calls", "missing_outcomes", "offense_policy", "defense_policy",
    "call_count", "outcome_count", "missing_decisions", "missing_repetition",
])
def test_policy_and_call_evidence_cannot_be_deleted_or_changed(engine_evidence, mutation):
    report, contract = deepcopy(engine_evidence)
    if mutation == "missing_calls":
        report.pop("call_mix", None)
    elif mutation == "missing_outcomes":
        report.pop("outcome_distributions", None)
    elif mutation == "offense_policy":
        report["metadata"]["normal_offense_weights"] = [1] * 9
    elif mutation == "defense_policy":
        report["metadata"]["normal_defense_weights"] = [1] * 6
    elif mutation == "call_count":
        report["call_mix"][0]["count"] += 1
    elif mutation == "outcome_count":
        report["outcome_distributions"][0]["count"] += 1
    elif mutation == "missing_decisions":
        for receipt in report["game_receipts"]:
            receipt.pop("decision_results", None)
    else:
        report.pop("comparable_situations", None)
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any(word in " ".join(result["errors"]).lower()
               for word in ("policy", "call", "decision", "situation"))


def test_each_call_records_selected_defense_and_ordered_result(engine_evidence):
    report, _ = engine_evidence
    from paydirt.play_resolver import DefenseType, PlayType, ResultType

    for receipt in report["game_receipts"]:
        decisions = receipt.get("decision_results", [])
        assert decisions
        for call in decisions:
            team, play, defense, down, distance, mode = call["situation"]
            assert team in receipt["teams"]
            assert play in PlayType.__members__
            assert defense in DefenseType.__members__
            assert down in (1, 2, 3, 4)
            assert distance in ("short", "medium", "long")
            assert isinstance(mode, str) and mode
            assert call["result"] in ResultType.__members__
            assert type(call["yards"]) is int
            assert type(call["retained"]) is bool
    assert sum(item["count"] for item in report["call_mix"]) == sum(
        len(receipt["decision_results"]) for receipt in report["game_receipts"]
    )


def test_comparable_repetition_keeps_call_order_and_resets_between_games():
    from paydirt import chart_engine_audit as audit

    def call(play, defense="STANDARD"):
        return {"situation": ["Home", play, defense, 1, "long", "normal"],
                "result": "YARDS", "yards": 4, "retained": True}

    receipts = [
        {"decision_results": [call("SCREEN"), call("SCREEN", "BLITZ"),
                              call("SHORT_PASS"), call("SCREEN")]},
        {"decision_results": [call("SCREEN"), call("SCREEN")]},
    ]
    summarize = getattr(audit, "_decision_evidence", None)
    assert callable(summarize), "Audit must reconstruct selection evidence from ordered calls"
    evidence = summarize(receipts)
    assert len(evidence["comparable_situations"]) == 1
    group = evidence["comparable_situations"][0]
    assert group["calls"] == 6
    assert group["play_counts"] == {"SCREEN": 5, "SHORT_PASS": 1}
    assert group["distinct_plays"] == 2
    assert group["longest_streak"] == 2
    assert group["largest_share"] == pytest.approx(5 / 6)


@pytest.mark.parametrize("mutation", ["team", "defense", "down", "result", "retained"])
def test_invalid_ordered_decisions_are_rejected(engine_evidence, mutation):
    report, contract = deepcopy(engine_evidence)
    calls = report["game_receipts"][0].get("decision_results", [])
    assert calls, "Real-engine evidence must preserve its ordered decisions"
    call = calls[0]
    if mutation in ("team", "defense", "down"):
        call["situation"][{"team": 0, "defense": 2, "down": 3}[mutation]] = {
            "team": "outside schedule", "defense": "invented", "down": 5,
        }[mutation]
    else:
        call[mutation] = "invented" if mutation == "result" else 1
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("decision" in error.lower() for error in result["errors"])


@pytest.mark.parametrize("category", ["field_goal", "scrimmage"])
def test_deleting_a_call_cannot_be_hidden_by_rebuilding_its_summaries(engine_evidence, category):
    from paydirt import chart_engine_audit as audit

    report, contract = deepcopy(engine_evidence)
    removed = False
    for receipt in report["game_receipts"]:
        for index, call in enumerate(receipt["decision_results"]):
            play = call["situation"][1]
            matching = play == "FIELD_GOAL" if category == "field_goal" else play == "LINE_PLUNGE"
            if call["retained"] and matching:
                receipt["decision_results"].pop(index)
                removed = True
                break
        if removed:
            break
    assert removed, "The public games must exercise the selected denominator"
    report.update(audit._decision_evidence(report["game_receipts"]))
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any("call totals" in error.lower() for error in result["errors"])


def test_saved_json_decision_and_runtime_evidence_passes(engine_evidence):
    import json

    report, contract = engine_evidence
    result = validate_engine_report(json.loads(json.dumps(report)), contract, PUBLIC, minimum_team_games=2)
    assert result["passed"], result["errors"]


@pytest.mark.parametrize("kind", ["keyword", "positional"])
def test_modified_loaded_defaults_cannot_receive_source_identity(monkeypatch: pytest.MonkeyPatch, kind):
    import paydirt.chart_engine_audit as audit

    if kind == "keyword":
        changed = dict(audit.run_engine_audit.__kwdefaults__)
        changed["policy"] = "pass-heavy"
        monkeypatch.setattr(audit.run_engine_audit, "__kwdefaults__", changed)
    else:
        from paydirt.save_game import save_game
        monkeypatch.setattr(save_game, "__defaults__", ("another-default.json",))
    with pytest.raises(RuntimeError, match="loaded runtime"):
        audit.run_engine_audit(PUBLIC, [("Ironclads", "Thunderhawks")],
                               repetitions=1, seed=20261106)


@pytest.mark.parametrize("required,passed", [(1, True), (2, False)])
def test_independent_schedule_minimum_is_separate_from_team_game_minimum(engine_evidence, required, passed):
    import inspect

    report, contract = engine_evidence
    # Exercise the old acceptance behavior before the new argument exists.
    extra = ({"minimum_repetitions": required}
             if "minimum_repetitions" in inspect.signature(validate_engine_report).parameters else {})
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2, **extra)
    assert result["passed"] is passed
    if not passed:
        assert any("independent schedule" in error.lower() for error in result["errors"])


@pytest.mark.parametrize("flag", ["COMPACT_MODE", "AI_HELPER_ENABLED"])
def test_legitimate_display_state_is_separate_from_loaded_policy_identity(monkeypatch, flag):
    import paydirt.interactive_game as interactive

    monkeypatch.setattr(interactive, flag, True)
    schedule = [("Ironclads", "Thunderhawks")]
    report = run_engine_audit(PUBLIC, schedule, repetitions=1, seed=20261106)
    result = validate_engine_report(report, {"schedule": schedule}, PUBLIC,
                                    minimum_team_games=1, require_fit=False)
    assert result["passed"], result["errors"]


@pytest.mark.parametrize("metric", ["points_per_team_game", "plays_per_team_game", "fumble_loss_rate_per_play", "field_goal_rate"])
@pytest.mark.parametrize("scope", ["league", "team"])
def test_all_derived_engine_rates_match_authoritative_raw_totals(engine_evidence: tuple, metric: str, scope: str) -> None:
    report, contract = deepcopy(engine_evidence)
    values = report["league"] if scope == "league" else next(iter(report["teams"].values()))
    values[metric] += 1
    result = validate_engine_report(report, contract, PUBLIC, minimum_team_games=2)
    assert not result["passed"]
    assert any(metric in error for error in result["errors"])

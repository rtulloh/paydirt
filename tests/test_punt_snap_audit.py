"""Punt snap fumbles must survive both execution and saved-report checks."""
import csv
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from paydirt import chart_engine_audit as audit
from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import PlayType

PUBLIC = Path(__file__).resolve().parents[1] / "seasons" / "2026"


def test_gate_controls_include_punt_snap_fumble_and_real_punt() -> None:
    result = audit.audit_observer_conformance()
    assert result["passed"], result["errors"]
    assert {case["case"] for case in result["checks"]} >= {"PUNT/F - 10", "PUNT/40*"}


def test_gate_controls_include_accepted_and_declined_punt_snap_rerolls() -> None:
    result = audit.audit_observer_conformance()
    assert result["passed"], result["errors"]
    assert {case["case"] for case in result["checks"]} >= {
        f"PUNT/{foul}->F - 10/{decision}"
        for foul in ("OFF 5", "DEF 5") for decision in ("accept", "decline")
    }


def test_gate_rejects_discarded_fumble_only_after_a_punt_foul(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.game_engine import PaydirtGameEngine

    original = PaydirtGameEngine._handle_punt

    def broken(self: PaydirtGameEngine, *args: object, **kwargs: object) -> PlayOutcome:
        chart = self.state.possession_team.special_teams
        cells = chart.punt
        if cells.get(10, "").startswith(("OFF", "DEF")):
            chart.punt = {roll: "40*" if value.startswith("F") else value for roll, value in cells.items()}
        try:
            return original(self, *args, **kwargs)
        finally:
            chart.punt = cells

    monkeypatch.setattr(PaydirtGameEngine, "_handle_punt", broken)
    result = audit.audit_observer_conformance()
    assert not result["passed"]
    assert any("->F" in error for error in result["errors"])


def test_gate_rejects_erased_aborted_punt_count(monkeypatch: pytest.MonkeyPatch) -> None:
    original = EngineCalibrationObserver.on_result

    def broken(self: EngineCalibrationObserver, game: object, outcome: PlayOutcome) -> None:
        original(self, game, outcome)
        if outcome.result.punt_snap_fumble:
            for totals in self._teams.values():
                totals.offensive_plays -= 1
                totals.rushing_attempts -= 1

    monkeypatch.setattr(EngineCalibrationObserver, "on_result", broken)
    result = audit.audit_observer_conformance()
    assert not result["passed"]
    assert any("PUNT/F" in error for error in result["errors"])


def test_gate_rejects_reintroduced_forty_yard_snap_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.game_engine import PaydirtGameEngine

    original = PaydirtGameEngine._handle_punt

    def broken(self: PaydirtGameEngine, *args: object, **kwargs: object) -> PlayOutcome:
        chart = self.state.possession_team.special_teams
        cells = chart.punt
        chart.punt = {roll: "40*" if value.startswith("F") else value for roll, value in cells.items()}
        try:
            return original(self, *args, **kwargs)
        finally:
            chart.punt = cells

    monkeypatch.setattr(PaydirtGameEngine, "_handle_punt", broken)
    result = audit.audit_observer_conformance()
    assert not result["passed"]
    assert any("PUNT/F" in error for error in result["errors"])


@pytest.fixture(scope="module")
def punt_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    directory = tmp_path_factory.mktemp("punt-audit") / "2026"
    shutil.copytree(PUBLIC, directory)
    for file in directory.glob("*/special.csv"):
        with file.open(newline="") as stream:
            rows = list(csv.reader(stream))
        column = rows[0].index("Punt")
        for row in rows[1:]:
            if row and row[0].isdigit():
                row[column] = "F - 10"
        with file.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
    return audit._run_season((str(directory), [("Ironclads", "Thunderhawks")],
                              20261108, "chart-focused", False))


def test_decision_receipts_reconcile_aborted_punts(punt_report: dict) -> None:
    receipt = punt_report["game_receipts"][0]
    snaps = [call for call in receipt["decision_results"] if call["situation"][1] == "PUNT"]
    assert snaps
    assert all(call["punt_snap_fumble"] for call in snaps)
    assert not audit._decision_count_errors(receipt)
    assert not audit._decision_errors(receipt, set(receipt["teams"]))


@pytest.mark.parametrize("mutation", ["missing", "nonboolean", "erased", "wrong_play"])
def test_saved_receipt_rejects_missing_or_false_snap_fact(punt_report: dict, mutation: str) -> None:
    receipt = deepcopy(punt_report["game_receipts"][0])
    call = next(call for call in receipt["decision_results"] if call["situation"][1] == "PUNT")
    if mutation == "missing":
        call.pop("punt_snap_fumble", None)
    elif mutation == "nonboolean":
        call["punt_snap_fumble"] = 1
    elif mutation == "erased":
        call["punt_snap_fumble"] = False
    else:
        call["situation"][1] = PlayType.KICKOFF.name
    errors = audit._decision_errors(receipt, set(receipt["teams"]))
    if not errors:
        errors = audit._decision_count_errors(receipt)
    assert errors

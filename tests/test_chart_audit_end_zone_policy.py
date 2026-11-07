"""Declared coaching policy must survive collection and saved-report reuse."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from paydirt import chart_engine_audit as audit
from paydirt.chart_loader import load_team_chart
from paydirt.game_engine import PaydirtGameEngine
from scripts import audit_generated_charts as cli

PUBLIC = Path(__file__).resolve().parents[1] / "seasons" / "2026"
SCHEDULE = [("Ironclads", "Thunderhawks")]


@pytest.mark.parametrize("policy", audit.supported_audit_policies())
@pytest.mark.parametrize("attempt", [False, True])
def test_factory_configures_both_physical_teams(policy: str, attempt: bool) -> None:
    game = PaydirtGameEngine(load_team_chart(PUBLIC / "Thunderhawks"), load_team_chart(PUBLIC / "Ironclads"))
    factory = audit._factory(policy, attempt_end_zone_interception_returns=attempt)
    factory(game, False)
    assert game.away_end_zone_interception_return is attempt
    factory(game, True)
    assert game.home_end_zone_interception_return is attempt


def test_existing_factory_default_remains_automatic_touchback() -> None:
    game = PaydirtGameEngine(load_team_chart(PUBLIC / "Thunderhawks"), load_team_chart(PUBLIC / "Ironclads"))
    factory = audit._factory("chart-focused")
    factory(game, False)
    factory(game, True)
    assert game.home_end_zone_interception_return is False
    assert game.away_end_zone_interception_return is False


@pytest.fixture(scope="module")
def policy_reports() -> dict[bool, dict]:
    """Synthetic policy declarations on otherwise complete public-game accounting."""
    base = audit.run_engine_audit(PUBLIC, SCHEDULE, repetitions=1, seed=20261108)
    reports = {}
    for attempt in (False, True):
        report = deepcopy(base)
        report["metadata"]["attempt_end_zone_interception_returns"] = attempt
        for receipt in report["game_receipts"]:
            receipt["home_end_zone_interception_return"] = attempt
            receipt["away_end_zone_interception_return"] = attempt
        reports[attempt] = report
    return reports


@pytest.mark.parametrize("workers", [1, 2])
@pytest.mark.parametrize("attempt", [False, True])
def test_collection_and_validation_bind_the_policy(attempt: bool, workers: int) -> None:
    report = audit.run_engine_audit(PUBLIC, SCHEDULE, repetitions=1, seed=20261108, workers=workers,
                                    attempt_end_zone_interception_returns=attempt)
    assert report["metadata"]["attempt_end_zone_interception_returns"] is attempt
    for receipt in report["game_receipts"]:
        assert receipt["home_end_zone_interception_return"] is attempt
        assert receipt["away_end_zone_interception_return"] is attempt
    result = audit.validate_engine_report(report, {"schedule": SCHEDULE}, PUBLIC,
                                          minimum_team_games=1, require_fit=False)
    assert result["passed"], result["errors"]


@pytest.mark.parametrize("damage", ["missing_metadata", "untyped_metadata", "home", "away", "missing_home"])
def test_inconsistent_policy_cannot_validate(policy_reports: dict, damage: str) -> None:
    report = deepcopy(policy_reports[True])
    if damage == "missing_metadata":
        report["metadata"].pop("attempt_end_zone_interception_returns")
    elif damage == "untyped_metadata":
        report["metadata"]["attempt_end_zone_interception_returns"] = 1
    elif damage == "missing_home":
        report["game_receipts"][0].pop("home_end_zone_interception_return")
    else:
        report["game_receipts"][0][f"{damage}_end_zone_interception_return"] = False
    result = audit.validate_engine_report(report, {"schedule": SCHEDULE}, PUBLIC,
                                          minimum_team_games=1, require_fit=False)
    assert not result["passed"]
    assert any("interception return" in e.lower() for e in result["errors"])


@pytest.mark.parametrize("attempt", [False, True])
def test_cli_passes_declared_mode_to_collection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                               policy_reports: dict, attempt: bool) -> None:
    calls = []
    def collect(*args, **kwargs):
        calls.append(kwargs)
        return deepcopy(policy_reports[attempt])
    monkeypatch.setattr(cli, "run_engine_audit", collect)
    monkeypatch.setattr(cli, "validate_engine_report", lambda *a, **k: {"passed": True})
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"schedule": [{"away": a,"home": h} for a,h in SCHEDULE]}))
    output = tmp_path / "report.json"
    argv = ["--season-dir",str(PUBLIC),"--contract",str(contract),"--output",str(output),"--engine-only"]
    if attempt:
        argv.append("--attempt-end-zone-interception-returns")
    assert cli.main(argv) == 0
    assert calls[0]["attempt_end_zone_interception_returns"] is attempt
    assert json.loads(output.read_text())["metadata"]["attempt_end_zone_interception_returns"] is attempt


@pytest.mark.parametrize("saved,requested", [(False,False),(True,True),(False,True),(True,False)])
def test_saved_report_requires_same_declared_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                policy_reports: dict, saved: bool, requested: bool) -> None:
    monkeypatch.setattr(cli,"run_engine_audit",lambda *a,**k: pytest.fail("Saved report must not start games"))
    monkeypatch.setattr(cli,"validate_engine_report",lambda *a,**k:{"passed":True})
    contract, cache, output = (tmp_path / name for name in ("contract.json","cache.json","output.json"))
    contract.write_text(json.dumps({"schedule":[{"away":a,"home":h} for a,h in SCHEDULE]}))
    cache.write_text(json.dumps(policy_reports[saved]))
    before = cache.read_bytes()
    argv = ["--season-dir",str(PUBLIC),"--contract",str(contract),"--engine-only",
            "--engine-report",str(cache),"--output",str(output)]
    if requested:
        argv.append("--attempt-end-zone-interception-returns")
    assert cli.main(argv) == (0 if saved == requested else 1)
    assert cache.read_bytes() == before
    if saved != requested:
        assert any("interception return" in e.lower() for e in json.loads(output.read_text())["errors"])


@pytest.mark.parametrize("value", [None,1,"true"])
def test_untyped_option_fails_before_collection(monkeypatch: pytest.MonkeyPatch, value: object) -> None:
    monkeypatch.setattr(audit,"_run_season",lambda *a:pytest.fail("Invalid policy must fail before workers"))
    with pytest.raises(ValueError,match="boolean"):
        audit.run_engine_audit(PUBLIC,SCHEDULE,repetitions=1,seed=1,attempt_end_zone_interception_returns=value)

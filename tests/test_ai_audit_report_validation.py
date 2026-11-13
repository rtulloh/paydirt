"""Saved AI evidence must reconcile with the complete requested schedule."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from paydirt.play_resolver import PlayType
from tests import ai_audit
from tests.semantic_audit import SemanticAudit


def synthetic_report(teams: list[str]) -> dict:
    """Build complete synthetic receipts without loading historical chart data."""
    specs = ai_audit.generated_schedule(teams, 16, 8306)
    specs += [
        replace(spec, away_difficulty="balanced", home_difficulty="balanced") for spec in specs
    ]
    games = []
    for spec in specs:
        calls = []
        for home in (False, True):
            calls.append(
                {
                    "before": {
                        "team": spec.home if home else spec.away,
                        "is_home": home,
                        "difficulty": spec.home_difficulty if home else spec.away_difficulty,
                        "quarter": 1,
                        "minutes_remaining": 15,
                        "overtime_period": 0,
                        "down": 1,
                        "distance": 10,
                        "ball_position": 20,
                        "score_differential": 0,
                        "mode": "ordinary",
                        "play": PlayType.LINE_PLUNGE.value,
                        "probabilities": {},
                    },
                    "result": {
                        "play": PlayType.LINE_PLUNGE.value,
                        "yards": 2,
                        **{
                            name: False
                            for name in (
                                "first_down",
                                "turnover",
                                "turnover_on_downs",
                                "touchdown",
                                "safety",
                                "field_goal_made",
                                "penalty_applied",
                                "pending_penalty_decision",
                                "spike_used",
                                "timeout_used",
                            )
                        },
                    },
                }
            )
        games.append(
            {
                "config": asdict(spec),
                "status": "passed",
                "calls": calls,
                "final": {
                    "home_score": 7,
                    "away_score": 7,
                    "overtime_periods": 1,
                    "game_over": True,
                    "untimed_down_pending": False,
                },
                "semantics": SemanticAudit().report(),
            }
        )
    report = ai_audit.make_report(games)
    report["run"] = {
        "master_seed": 8306,
        "comparison": True,
        "schedule": "generated regular season",
    }
    return report


def validate(report: dict, teams: list[str]) -> dict:
    function = getattr(ai_audit, "validate_report", None)
    assert callable(function), (
        "Saved AI reports require independent schedule and summary validation"
    )
    return function(report, teams)


@pytest.fixture
def teams() -> list[str]:
    return ["2026/SyntheticAlpha", "2026/SyntheticBeta"]


def test_complete_synthetic_ai_evidence_reconciles(teams: list[str]) -> None:
    result = validate(synthetic_report(teams), teams)
    assert result["passed"], result["errors"]
    assert result["games"] == 32 and result["calls"] == 64


@pytest.mark.parametrize(
    "mutation",
    [
        "empty-report",
        "wrong-version",
        "wrong-run",
        "omitted-game",
        "duplicated-game",
        "wrong-seed",
        "wrong-week",
        "substituted-team",
        "wrong-difficulty",
        "playoff",
        "failed-game",
        "contradictory-error",
        "empty-calls",
        "missing-result",
        "pending-result",
        "wrong-call-team",
        "wrong-call-difficulty",
        "different-result-play",
        "invalid-probabilities",
        "wrong-game-over",
        "untimed-down",
        "bool-score",
        "invalid-semantic-count",
        "missing-semantics",
        "coverage-summary",
        "summary-count",
        "summary-groups",
        "hidden-concentration-warning",
        "wrong-python",
        "bool-summary-count",
    ],
)
def test_ai_report_mutants_fail_even_after_rebuilding_their_own_summary(
    teams: list[str], mutation: str
) -> None:
    report = synthetic_report(teams)
    game = report["games"][0]
    call = game["calls"][0]
    if mutation == "empty-report":
        report = {}
    elif mutation == "wrong-version":
        report["schema_version"] = True
    elif mutation == "wrong-run":
        report["run"]["master_seed"] = 1
    elif mutation == "omitted-game":
        report["games"].pop()
    elif mutation == "duplicated-game":
        report["games"][1] = deepcopy(game)
    elif mutation == "wrong-seed":
        game["config"]["seed"] += 1
    elif mutation == "wrong-week":
        game["config"]["week"] = True
    elif mutation == "substituted-team":
        game["config"]["away"] = "2026/Other"
    elif mutation == "wrong-difficulty":
        game["config"]["away_difficulty"] = "easy"
    elif mutation == "playoff":
        game["config"]["is_playoff"] = True
    elif mutation == "failed-game":
        game["status"] = "failed"
    elif mutation == "contradictory-error":
        game["error"] = "Synthetic failure retained"
    elif mutation == "empty-calls":
        game["calls"] = []
    elif mutation == "missing-result":
        call.pop("result")
    elif mutation == "pending-result":
        call["result"]["pending_penalty_decision"] = True
    elif mutation == "wrong-call-team":
        call["before"]["team"] = "2026/Other"
    elif mutation == "wrong-call-difficulty":
        call["before"]["difficulty"] = "easy"
    elif mutation == "different-result-play":
        call["result"]["play"] = PlayType.SCREEN.value
    elif mutation == "invalid-probabilities":
        call["before"]["probabilities"] = {call["before"]["play"]: 0.2}
    elif mutation == "wrong-game-over":
        game["final"]["game_over"] = False
    elif mutation == "untimed-down":
        game["final"]["untimed_down_pending"] = True
    elif mutation == "bool-score":
        game["final"]["home_score"] = True
    elif mutation == "invalid-semantic-count":
        game["semantics"]["covered"]["incomplete"] = -1
    elif mutation == "missing-semantics":
        game.pop("semantics")
    elif mutation == "wrong-python":
        report["python"] = "0.0.0"
    if mutation not in {"empty-report", "wrong-version", "wrong-run"}:
        rebuilt = ai_audit.make_report(report["games"])
        report.update(summary=rebuilt["summary"], semantic_coverage=rebuilt["semantic_coverage"])
    if mutation == "coverage-summary":
        report["semantic_coverage"]["incomplete"] += 1
    elif mutation == "summary-count":
        report["summary"]["calls"] += 1
    elif mutation == "summary-groups":
        report["summary"]["situations"][0]["longest_streak"] += 1
    elif mutation == "bool-summary-count":
        report["summary"]["failed"] = False
    elif mutation == "hidden-concentration-warning":
        game["calls"] = [deepcopy(call) for _ in range(30)]
        rebuilt = ai_audit.make_report(report["games"])
        report.update(summary=rebuilt["summary"], semantic_coverage=rebuilt["semantic_coverage"])
        assert report["summary"]["warnings"]
        report["summary"]["warnings"] = []
    result = validate(report, teams)
    assert not result["passed"] and result["errors"]


def test_concentration_is_retained_as_advisory_evidence(teams: list[str]) -> None:
    report = synthetic_report(teams)
    game = report["games"][0]
    game["calls"] = [deepcopy(game["calls"][0]) for _ in range(30)]
    report.update(
        {
            key: value
            for key, value in ai_audit.make_report(report["games"]).items()
            if key != "games"
        }
    )
    result = validate(report, teams)
    assert result["passed"], result["errors"]
    assert result["warnings"] == report["summary"]["warnings"]


def test_real_public_games_are_accepted_without_rewriting_their_evidence() -> None:
    teams = ["2026/Ironclads", "2026/Thunderhawks"]
    specs = ai_audit.generated_schedule(teams, 16, 8306)
    first = ai_audit.audit_game(specs[0])
    assert first["status"] == "passed", first.get("error")
    report = synthetic_report(teams)
    report["games"][0] = first
    report.update(
        {
            key: value
            for key, value in ai_audit.make_report(report["games"]).items()
            if key != "games"
        }
    )
    before = deepcopy(report)
    result = validate(report, teams)
    assert result["passed"], result["errors"]
    assert report == before

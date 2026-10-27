"""Audit harness contracts, public real-engine games, and synthetic reporting."""

import contextlib
import importlib
import io
import json
import random
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.auto_game import run_auto_game
from paydirt.computer_ai import create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType

AWAY = "2026/Ironclads"
HOME = "2026/Thunderhawks"


@pytest.mark.parametrize("home_level,away_level", [("hard", "hard"), ("medium", "hard"), ("hard", "easy")])
def test_auto_game_allows_observation_without_changing_default_flow(
    home_level: str, away_level: str,
) -> None:
    ais = {}
    calls, outcomes = [], []

    def factory(game: PaydirtGameEngine, is_home: bool):
        ai = create_computer_ai(home_level if is_home else away_level, game, is_home)
        ais[is_home] = ai
        return ai

    def decision(game, ai, play, defense):
        calls.append((game.state.is_home_possession, play))
        assert not game.state.game_over

    def result(game, outcome):
        assert not outcome.pending_penalty_decision
        outcomes.append(outcome.play_type)

    state = random.getstate()
    try:
        random.seed(731)
        with contextlib.redirect_stdout(io.StringIO()):
            game = run_auto_game(AWAY, HOME, ai_factory=factory,
                                 on_decision=decision, on_result=result)
    finally:
        random.setstate(state)
    assert game.state.game_over and not game.has_untimed_down()
    assert [play for _, play in calls] == outcomes
    assert ais[True].use_analysis is (home_level == "hard")
    assert ais[False].use_analysis is (away_level == "hard")
    assert ais[True].team_analyzer is None or ais[True].team_analyzer.team_chart is game.state.home_chart
    assert ais[False].team_analyzer is None or ais[False].team_analyzer.team_chart is game.state.away_chart


def audit_module():
    return importlib.import_module("tests.ai_audit")


def spec(**overrides):
    values = {"away": AWAY, "home": HOME, "seed": 731, "away_difficulty": "hard", "home_difficulty": "hard"}
    values.update(overrides)
    return audit_module().GameSpec(**values)


def test_seeded_audits_are_reproducible_and_restore_caller_rng() -> None:
    audit = audit_module()
    before = random.getstate()
    first = audit.audit_game(spec())
    second = audit.audit_game(spec())
    assert first == second
    assert random.getstate() == before
    assert first["status"] == "passed", first.get("error")
    other = audit.audit_game(spec(seed=732))
    assert first["calls"] != other["calls"]
    assert first["calls"] and all("before" in call and "result" in call for call in first["calls"])
    assert any(call["before"]["probabilities"] for call in first["calls"])
    for call in first["calls"]:
        probs = call["before"]["probabilities"]
        if probs:
            assert sum(probs.values()) == pytest.approx(1)
            assert call["before"]["play"] in probs
        assert call["result"]["pending_penalty_decision"] is False


def test_audit_limit_is_failure_not_a_successful_partial_game() -> None:
    audit = audit_module()
    before = random.getstate()
    game = audit.audit_game(spec(), play_limit=1)
    assert game["status"] == "failed"
    assert "limit" in game["error"].lower()
    assert random.getstate() == before
    assert len(game["calls"]) == 1


def test_observation_is_read_only_and_default_auto_remains_balanced() -> None:
    audit = audit_module()
    called = []
    real_factory = create_computer_ai

    def factory(difficulty, game, cpu_is_home):
        called.append(difficulty)
        return real_factory(difficulty, game, cpu_is_home)

    with patch("tests.ai_audit.create_computer_ai", side_effect=factory):
        result = audit.audit_game(spec(home_difficulty="medium", away_difficulty="easy"))
    assert result["status"] == "passed"
    assert called == ["easy", "medium"]
    assert all(not call["before"]["probabilities"] for call in result["calls"]
               if call["before"]["mode"] == "ordinary")
    baseline, observed = [], []
    for observer in (None, lambda game, ai, play, defense: observed.append(play.value)):
        state = random.getstate()
        try:
            random.seed(100)
            with contextlib.redirect_stdout(io.StringIO()):
                game = run_auto_game(AWAY, HOME, on_decision=observer)
            baseline.append((game.state.home_score, game.state.away_score,
                             [(p.play_type, p.yards_gained) for p in game.play_log]))
        finally:
            random.setstate(state)
    assert baseline[0] == baseline[1]
    assert observed


def test_generated_season_and_independent_stable_seeds() -> None:
    audit = audit_module()
    teams = ["2026/Alpha", "2026/Beta", "2026/Gamma", "2026/Delta"]
    schedule = audit.generated_schedule(teams, weeks=3, seed=731)
    assert len(schedule) == 6
    for week in range(1, 4):
        games = [game for game in schedule if game.week == week]
        assert sorted([team for game in games for team in (game.home, game.away)]) == sorted(teams)
    assert len({game.seed for game in schedule}) == 6
    assert schedule == audit.generated_schedule(list(reversed(teams)), weeks=3, seed=731)
    assert schedule != audit.generated_schedule(teams, weeks=3, seed=732)
    assert audit.game_seed(731, "game-A") == audit.game_seed(731, "game-A")
    assert audit.game_seed(731, "game-A") != audit.game_seed(731, "game-B")


@pytest.mark.parametrize("teams,weeks", [([], 1), ([AWAY], 1), ([AWAY, AWAY], 1), ([AWAY, HOME], 0)])
def test_invalid_schedules_are_not_silently_partial(teams: list, weeks: int) -> None:
    with pytest.raises(ValueError):
        audit_module().generated_schedule(teams, weeks=weeks, seed=731)


def test_summary_reconciles_and_does_not_export_charts_or_descriptions() -> None:
    audit = audit_module()
    games = [audit.audit_game(spec(seed=seed)) for seed in (731, 732)]
    report = audit.make_report(games)
    summary = report["summary"]
    assert summary["games"] == summary["passed"] == 2
    assert summary["failed"] == 0
    assert summary["calls"] == sum(len(game["calls"]) for game in games)
    assert sum(group["calls"] for group in summary["situations"]) == summary["calls"]
    for group in summary["situations"]:
        assert sum(group["play_counts"].values()) == group["calls"]
        assert group["largest_share"] == max(group["play_counts"].values()) / group["calls"]
        assert group["distinct_plays"] == len(group["play_counts"])
    encoded = json.dumps(report)
    for forbidden in ("raw_result", "description", "team_dir", "offense.csv", "roster", "_score_cache"):
        assert forbidden not in encoded


def test_batch_reports_failures_and_never_persists_standings(tmp_path: Path) -> None:
    audit = audit_module()
    with patch("paydirt.standings.StandingsManager.save_season", side_effect=AssertionError("saved standings")):
        games = audit.run_games([spec(), spec(seed=732)], play_limit=1)
    assert len(games) == 2
    assert audit.make_report(games)["summary"]["failed"] == 2
    assert list(tmp_path.iterdir()) == []


def test_repeated_call_warnings_disclose_small_samples_without_global_caps() -> None:
    audit = audit_module()
    sample = {"status": "passed", "config": {"away": AWAY, "home": HOME}, "calls": [
        {"before": {"team": AWAY, "difficulty": "hard", "mode": "ordinary",
                    "down": 1, "distance": 10, "play": PlayType.SCREEN.value}} for _ in range(30)]}
    summary = audit.make_report([sample])["summary"]
    assert summary["situations"][0]["largest_share"] == 1
    assert summary["situations"][0]["longest_streak"] == 30
    assert summary["warnings"]
    assert summary["failed"] == 0  # Concentration is evidence to inspect, not an illegal play.


def test_cli_writes_json_and_csv_and_balanced_comparison(tmp_path: Path, capsys) -> None:
    cli = importlib.import_module("tests.run_ai_audit")
    output, csv_output = tmp_path / "report.json", tmp_path / "groups.csv"
    status = cli.main([AWAY, HOME, "--games", "2", "--seed", "731",
                       "--compare-balanced", "--output", str(output), "--csv", str(csv_output)])
    assert status == 0
    report = json.loads(output.read_text())
    assert report["summary"]["games"] == report["summary"]["passed"] == 4
    assert [game["config"]["seed"] for game in report["games"][:2]] == [
        game["config"]["seed"] for game in report["games"][2:]]
    assert {game["config"]["away_difficulty"] for game in report["games"]} == {"hard", "balanced"}
    assert csv_output.read_text().startswith("team,difficulty,mode,down,distance_band,calls,")
    assert "4/4" in capsys.readouterr().out


def test_cli_season_uses_complete_schedule_without_private_dependencies(tmp_path: Path) -> None:
    cli = importlib.import_module("tests.run_ai_audit")
    output = tmp_path / "report.json"
    assert cli.main(["--season", "2026", "--weeks", "3", "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["summary"]["games"] == report["summary"]["passed"] == 3
    assert {game["config"]["week"] for game in report["games"]} == {1, 2, 3}


def test_cli_failure_is_nonzero_and_report_retains_every_matchup(tmp_path: Path) -> None:
    cli = importlib.import_module("tests.run_ai_audit")
    output = tmp_path / "report.json"
    assert cli.main([AWAY, HOME, "--games", "2", "--play-limit", "1", "--output", str(output)]) == 1
    report = json.loads(output.read_text())
    assert report["summary"]["games"] == report["summary"]["failed"] == 2
    assert report["summary"]["balance_calls"] == 0
    assert report["summary"]["situations"] == []


@pytest.mark.parametrize("args", [["--season", "missing"], [AWAY], [AWAY, HOME, "--games", "0"],
    [AWAY, HOME, "--season", "2026"], ["--season", "2026", "--weeks", "0"],
    [AWAY, HOME, "--play-limit", "0"]])
def test_cli_rejects_invalid_run_configuration(args: list[str], tmp_path: Path) -> None:
    cli = importlib.import_module("tests.run_ai_audit")
    with pytest.raises(SystemExit) as error:
        cli.main([*args, "--output", str(tmp_path / "report.json")])
    assert error.value.code == 2
    assert not (tmp_path / "report.json").exists()


def test_audit_errors_never_export_private_exception_text() -> None:
    audit = audit_module()
    with patch.object(audit, "run_auto_game", side_effect=ValueError("private offense.csv cell at /secret/data")):
        report = audit.audit_game(spec())
    assert report["status"] == "failed"
    assert "private" not in json.dumps(report)
    assert "secret" not in json.dumps(report)


def test_failed_partial_games_are_not_silently_mixed_into_balance() -> None:
    audit = audit_module()
    games = [audit.audit_game(spec()), audit.audit_game(spec(seed=733), play_limit=1)]
    report = audit.make_report(games)
    assert report["summary"]["failed"] == 1
    assert report["summary"]["balance_calls"] == len(games[0]["calls"])
    assert report["summary"]["calls"] == len(games[0]["calls"]) + 1


def test_console_prioritizes_supported_groups_over_tiny_samples(tmp_path: Path, capsys) -> None:
    cli = importlib.import_module("tests.run_ai_audit")
    groups = [{"team": "Team", "difficulty": "hard", "mode": "ordinary",
               "down": 1, "distance_band": "7-10", "calls": 100,
               "largest_share": .2, "distinct_plays": 9, "longest_streak": 2,
               "small_sample": False}]
    groups.extend({**groups[0], "team": str(i), "calls": 1, "largest_share": 1,
                   "small_sample": True} for i in range(8))
    fake_report = {"games": [], "summary": {"games": 0, "passed": 0, "failed": 0,
                   "calls": 0, "warnings": [], "situations": groups}}
    with patch.object(cli, "run_games", return_value=[]), patch.object(cli, "make_report", return_value=fake_report):
        assert cli.main([AWAY, HOME, "--output", str(tmp_path / "report.json")]) == 0
    assert "n=100 largest=20.0%" in capsys.readouterr().out


def test_observers_get_one_finalized_penalty_call_not_kickoff_chains() -> None:
    from paydirt.auto_game import _complete_auto_outcome
    from paydirt.game_state import PlayOutcome
    from paydirt.play_resolver import DefenseType, PlayResult, ResultType
    from tests.game_fixtures import make_sample_game

    game = make_sample_game()
    ai = create_computer_ai("hard", game, True)
    pending = PlayOutcome(PlayType.SCREEN, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
                          pending_penalty_decision=True)
    finalized = PlayOutcome(PlayType.SCREEN, DefenseType.STANDARD, PlayResult(ResultType.YARDS), touchdown=True)
    kickoff = PlayOutcome(PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS))
    observed = []
    with patch("paydirt.auto_game._resolve_auto_penalties", side_effect=[finalized, kickoff]), (
        patch.object(game, "attempt_extra_point", return_value=(True, "PAT"))
    ), patch.object(game, "can_attempt_conversion_after_touchdown", return_value=True), (
        patch.object(game, "can_kickoff_after_play", return_value=True)
    ), patch.object(game, "kickoff", return_value=kickoff), contextlib.redirect_stdout(io.StringIO()):
        _complete_auto_outcome(game, pending, True, 1, ai, ai, lambda engine, result: observed.append(result))
    assert observed == [finalized]
    assert observed[0].pending_penalty_decision is False


def test_pending_penalty_result_cannot_pass_evidence_validation() -> None:
    audit = audit_module()
    original = audit.run_auto_game

    def unfinished(*args, **kwargs):
        observe = kwargs["on_result"]

        def pending(game, outcome):
            old = outcome.pending_penalty_decision
            outcome.pending_penalty_decision = True
            try:
                observe(game, outcome)
            finally:
                outcome.pending_penalty_decision = old

        kwargs["on_result"] = pending
        return original(*args, **kwargs)

    with patch.object(audit, "run_auto_game", side_effect=unfinished):
        report = audit.audit_game(spec())
    assert report["status"] == "failed"


def test_unrelated_runtime_failure_is_not_mislabeled_as_action_limit() -> None:
    audit = audit_module()
    with patch.object(audit, "run_auto_game", side_effect=RuntimeError("private chart read failure")):
        report = audit.audit_game(spec())
    assert report["status"] == "failed"
    assert "limit" not in report["error"]


def test_balanced_baseline_observation_has_same_seeded_results_as_plain_auto() -> None:
    audit = audit_module()
    before = random.getstate()
    try:
        random.seed(731)
        with contextlib.redirect_stdout(io.StringIO()):
            plain = run_auto_game(AWAY, HOME)
    finally:
        random.setstate(before)
    recorded = audit.audit_game(spec(away_difficulty="balanced", home_difficulty="balanced"))
    assert recorded["status"] == "passed"
    assert (plain.state.home_score, plain.state.away_score) == (
        recorded["final"]["home_score"], recorded["final"]["away_score"])


@pytest.mark.parametrize("difficulty", ["hard", "medium", "easy", "balanced"])
def test_hurry_up_audit_includes_actual_selection_probabilities(difficulty: str) -> None:
    from paydirt.play_resolver import CHART_PLAY_TYPES

    result = audit_module().audit_game(spec(home_difficulty=difficulty, away_difficulty=difficulty))
    assert result["status"] == "passed", result.get("error")
    calls = [call["before"] for call in result["calls"]
             if call["before"]["mode"] in ("Two-Minute Drill", "Play + Spike")
             and call["before"]["play"] in {play.value for play in CHART_PLAY_TYPES}]
    assert calls
    for call in calls:
        assert call["play"] in call["probabilities"]
        assert sum(call["probabilities"].values()) == pytest.approx(1)

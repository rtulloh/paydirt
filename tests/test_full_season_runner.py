"""Tests for the standalone full-season regression runner."""

from types import SimpleNamespace

import pytest

from tests import run_full_season as runner


def finished_game() -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            game_over=True, home_score=3, away_score=0, ot_period=0,
            scoring_plays=[SimpleNamespace(points=3, is_home_team=True)],
        ),
        has_untimed_down=lambda: False,
        get_period_scores=lambda: [{"home": 3, "away": 0}],
    )


def test_generated_schedule_is_complete_and_deterministic() -> None:
    teams = [f"Team{number:02d}" for number in range(28)]
    schedule = runner.build_schedule(teams)
    assert schedule == runner.build_schedule(list(reversed(teams)))
    assert len(schedule) == 224
    assert len({game[4] for game in schedule}) == 224
    for week in range(1, 17):
        games = [game for game in schedule if game[0] == week]
        assert len(games) == 14
        assert sorted(team for game in games for team in game[2:4]) == teams
        assert all(game[4] == 19830000 + week * 100 + game[1] for game in games)


@pytest.mark.parametrize("teams", [[], ["team"] * 28, [str(n) for n in range(27)]])
def test_schedule_rejects_missing_or_duplicate_teams(teams: list[str]) -> None:
    with pytest.raises(ValueError, match="28 distinct"):
        runner.build_schedule(teams)


def test_valid_game_passes() -> None:
    runner.validate_game(finished_game(), "FINAL")


@pytest.mark.parametrize("problem", ["game_over", "untimed", "final", "periods", "scoring"])
def test_validation_rejects_bad_game(problem: str) -> None:
    game = finished_game()
    output = "FINAL"
    if problem == "game_over":
        game.state.game_over = False
    elif problem == "untimed":
        game.has_untimed_down = lambda: True
    elif problem == "final":
        output = ""
    elif problem == "periods":
        game.get_period_scores = lambda: [{"home": 0, "away": 0}]
    else:
        game.state.scoring_plays = []
    with pytest.raises(ValueError):
        runner.validate_game(game, output)


@pytest.mark.parametrize("fails", [False, True])
def test_runner_completes_all_games_and_returns_failure_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fails: bool,
) -> None:
    calls = []

    def simulate(context, away: str, home: str, seed: int) -> SimpleNamespace:
        calls.append(seed)
        print("FINAL")
        if fails and len(calls) == 1:
            raise RuntimeError("injected failure")
        return finished_game()

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    # Isolate regular-season failure accounting; postseason has its own full-flow tests.
    monkeypatch.setattr(runner, "run_playoffs", lambda season: 0)
    status = runner.run_full_season([str(n) for n in range(28)])
    output = capsys.readouterr()
    assert len(calls) == 224
    assert status == int(fails)
    assert ("223/224" if fails else "224/224") in output.out
    if fails:
        assert "seed=19830101" in output.err
        assert "injected failure" in output.err


def test_main_fails_when_season_data_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(runner, "SEASON_DIR", tmp_path / "missing")
    assert runner.main() == 1


@pytest.mark.parametrize("problem", [None, "exception", "missing-untimed"])
def test_historical_runner_keeps_all_reproductions_local(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], problem: str,
) -> None:
    calls = []

    def simulate(context, away: str, home: str, seed: int) -> SimpleNamespace:
        calls.append((away, home, seed))
        print("FINAL")
        if problem == "exception" and len(calls) == 1:
            raise RuntimeError("injected failure")
        if problem != "missing-untimed":
            print("UNTIMED DOWN")
        return finished_game()

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_historical_reproductions() == int(problem is not None)
    assert len(calls) == 9
    assert all(away.startswith("1983/") and home.startswith("1983/") for away, home, _ in calls)
    output = capsys.readouterr()
    assert ("9/9" if problem is None else "8/9" if problem == "exception" else "7/9") in output.out
    if problem == "exception":
        assert "seed=19831104" in output.err
    elif problem == "missing-untimed":
        assert "seed=19831107" in output.err
        assert "seed=19831624" in output.err


@pytest.mark.parametrize("missing_supplemental", [False, True])
@pytest.mark.parametrize("supplemental_seed", [19831107, 19831624])
def test_seed_drift_retains_original_and_requires_supplemental_untimed_flow(
    monkeypatch: pytest.MonkeyPatch, missing_supplemental: bool, supplemental_seed: int,
) -> None:
    calls = []

    def simulate(context, away: str, home: str, seed: int) -> SimpleNamespace:
        calls.append(seed)
        print("FINAL")
        # Synthetic output only: no historical charts are loaded by this test.
        if seed in (19831107, 19831624) and not (seed == supplemental_seed and missing_supplemental):
            print("UNTIMED DOWN")
        return finished_game()

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_historical_reproductions() == int(missing_supplemental)
    assert {19831104, 19831107, 19831603, 19831607, 19831621, 19831623,
            19831624, 19830601, 19830914} == set(calls)

@pytest.mark.parametrize("reproduction_status,season_status", [(0, 0), (1, 0), (0, 1), (1, 1)])
def test_main_requires_both_integration_checks_to_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path, reproduction_status: int, season_status: int,
) -> None:
    calls = []
    monkeypatch.setattr(runner, "SEASON_DIR", tmp_path)
    monkeypatch.setattr(runner, "build_schedule", lambda teams: [])
    monkeypatch.setattr(runner, "run_historical_reproductions", lambda: reproduction_status)

    def season(teams: list[str]) -> int:
        calls.append(teams)
        return season_status

    monkeypatch.setattr(runner, "run_full_season", season)
    assert runner.main() == (reproduction_status or season_status)
    assert calls == [[]]


def test_historical_driver_plays_on_but_does_not_change_live_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep late-penalty flow reachable using legal calls, not altered dice/rules."""
    from paydirt.computer_ai import ComputerAI
    from paydirt.play_resolver import PlayType
    from tests.game_fixtures import make_sample_game

    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.home_score, game.state.away_score = 7, 0
    game.state.quarter, game.state.time_remaining = 4, 6 / 60
    game.state.ball_position = 80
    ai = ComputerAI()
    decisions = []

    def simulate(context: pytest.MonkeyPatch, away: str, home: str, seed: int) -> SimpleNamespace:
        decisions.append(ai.select_offense(game))
        print("FINAL\nUNTIMED DOWN")
        return finished_game()

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_historical_reproductions() == 0
    assert len(decisions) == 9
    assert all(play != PlayType.QB_KNEEL for play in decisions)
    assert ai.select_offense(game) == PlayType.QB_KNEEL

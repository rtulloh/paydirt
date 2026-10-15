"""Clock-saving modifiers may reopen a game only when they preserve time."""

from unittest.mock import patch

import pytest

from tests.game_fixtures import make_sample_game
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from tests.test_untimed_down_flow import run_seeded_cli_game


@pytest.fixture(params=[True, False], ids=["home-offense", "away-offense"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.quarter = 4
    engine.state.home_score = 24
    engine.state.away_score = 17
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 40
    return engine


@pytest.mark.parametrize("modifier,cost", [("timeout", 0.167), ("spike", 0.333)])
@pytest.mark.parametrize("seconds", [5, 10, 10.2, 15.8, 20, 20.2, 30])
def test_clock_adjustment_keeps_game_end_consistent(
    game: PaydirtGameEngine, modifier: str, cost: float, seconds: float,
) -> None:
    before = seconds / 60
    game.state.time_remaining = before
    game._use_time(40)
    assert game.state.game_over
    getattr(game, f"_apply_{modifier}")(before, 4)
    expected = max(0, before - cost)
    if expected < 0.0167:
        expected = 0
    assert game.state.time_remaining == pytest.approx(expected)
    assert game.state.game_over is (expected == 0)
    assert not game.has_untimed_down()
    assert game.state.quarter == 4


@pytest.mark.parametrize("modifier,cost", [("timeout", 0.167), ("spike", 0.333)])
@pytest.mark.parametrize("seconds", [5, 10, 10.2, 15.8, 20, 20.2, 30])
def test_play_with_clock_modifier_finishes_or_preserves_game(
    game: PaydirtGameEngine, modifier: str, cost: float, seconds: float,
) -> None:
    game.state.time_remaining = seconds / 60
    choice = PenaltyChoice(PlayResult(ResultType.YARDS, yards=4))
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice), patch(
        "paydirt.game_engine.random.uniform", return_value=40,
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD,
            call_timeout=modifier == "timeout", call_spike=modifier == "spike",
        )
    expected = max(0, seconds / 60 - cost)
    if expected < 0.0167:
        expected = 0
    assert game.state.time_remaining == pytest.approx(expected)
    assert game.state.game_over is (expected == 0)
    assert not game.has_untimed_down()
    assert not outcome.turnover
    assert game.state.ball_position == 44
    assert len(game.play_log) == 1


@pytest.mark.parametrize("away,home,seed", [
    ("Ironclads", "Thunderhawks", 19830601),
    ("Thunderhawks", "Ironclads", 19830914),
])
def test_sample_game_clock_modifier_flow(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    away: str, home: str, seed: int,
) -> None:
    engine = run_seeded_cli_game(monkeypatch, away, home, seed)
    output = capsys.readouterr().out
    assert "FINAL" in output
    assert engine.state.time_remaining == 0
    assert not engine.has_untimed_down()
    assert engine.state.game_over
    assert sum(p["home"] for p in engine.get_period_scores()) == engine.state.home_score
    assert sum(p["away"] for p in engine.get_period_scores()) == engine.state.away_score

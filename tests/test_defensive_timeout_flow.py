"""Public-fixture regressions for defensive CPU timeouts and clock modifiers."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.computer_ai import ComputerAI
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


class ReachedDisplay(Exception):
    """Stop the CLI after its play and timeout decisions."""


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("human_home", [False, True])
@pytest.mark.parametrize("trailing", [False, True])
def test_cli_cpu_defense_spends_its_own_timeout(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, human_home: bool, trailing: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = human_home
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    game.state.two_minute_warning_called = True
    game.state.home_score = 19 if human_home else 3
    game.state.away_score = 3 if human_home else 19
    if not trailing:
        game.state.home_score, game.state.away_score = game.state.away_score, game.state.home_score
    ai = Mock(use_analysis=False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout_on_defense.side_effect = ComputerAI().should_call_timeout_on_defense
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_game_status", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.LINE_PLUNGE, False, False, False, False, False))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "_complete_touchdown_sequence", lambda game, outcome, *args: outcome)
    monkeypatch.setattr("builtins.input", lambda prompt="": (
        "A" if prompt == "\nYour choice: " and not human_home else ""))
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    monkeypatch.setattr(game, "kickoff", lambda **kwargs: SimpleNamespace(
        pending_penalty_decision=False, description="Synthetic kickoff"))
    charts = [game.state.home_chart, game.state.away_chart] if human_home else [
        game.state.away_chart, game.state.home_chart]
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=charts))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME", "away_score": 0,
        "home_score": 0, "quarter": 4, "time_remaining": 1})
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, not human_home, human_home, None))

    def play(*args, **kwargs):
        game.state.time_remaining = 0.4  # A 36-second, running-clock play.
        from paydirt.game_state import PlayOutcome
        return PlayOutcome(
            play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
            result=PlayResult(ResultType.YARDS, yards=3), yards_gained=3,
        )

    monkeypatch.setattr(game, "run_play_with_penalty_procedure", play)
    monkeypatch.setattr(cli, "display_play_result", Mock(side_effect=ReachedDisplay))
    with pytest.raises(ReachedDisplay):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()

    defense_timeouts = game.state.away_timeouts if human_home else game.state.home_timeouts
    offense_timeouts = game.state.home_timeouts if human_home else game.state.away_timeouts
    assert defense_timeouts == (2 if trailing else 3)
    assert offense_timeouts == 3
    expected_time = 50 / 60 if trailing else 0.4
    assert game.state.time_remaining == pytest.approx(expected_time, abs=0.001)


@pytest.mark.parametrize("no_huddle", [False, True])
@pytest.mark.parametrize("sideline", [False, True])
def test_defensive_timeout_interacts_with_no_huddle_and_sideline(
    no_huddle: bool, sideline: bool,
) -> None:
    game = make_sample_game()
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    game.state.two_minute_warning_called = True
    game.state.is_home_possession = True
    game.state.ball_position = 40
    result = PlayResult(ResultType.YARDS, yards=12, raw_result="12")
    choice = SimpleNamespace(penalty_options=[], offsetting=False, play_result=result)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice), patch(
        "paydirt.game_engine.random.uniform", side_effect=lambda low, high: (low + high) / 2
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.LINE_PLUNGE, DefenseType.STANDARD,
            no_huddle=no_huddle, out_of_bounds_designation=sideline,
        )
    expected_seconds = 10 if sideline else (20 if no_huddle else 35)
    assert (1.0 - game.state.time_remaining) * 60 == pytest.approx(expected_seconds)
    assert outcome.yards_gained == (7 if sideline else 12)
    used = game.apply_defensive_timeout(
        outcome, time_before_play=1.0, quarter_before_play=4,
        offense_was_home=True, two_minute_warning_before=True,
    )
    assert used is (not sideline)
    assert game.state.home_timeouts == 3
    assert game.state.away_timeouts == (3 if sideline else 2)
    assert game.state.time_remaining == pytest.approx(50 / 60, abs=0.001)
    # A second caller cannot charge the same play twice.
    assert not game.apply_defensive_timeout(
        outcome, time_before_play=1.0, quarter_before_play=4,
        offense_was_home=True, two_minute_warning_before=True,
    )


@pytest.mark.parametrize("reason", [
    "incomplete", "oob", "turnover", "downs", "touchdown", "safety",
    "penalty", "pending", "warning", "no-timeouts", "short-play", "already-used",
])
def test_defensive_timeout_preserves_timeouts_when_not_useful(reason: str) -> None:
    game = make_sample_game()
    game.state.quarter = 4
    game.state.time_remaining = 0.4
    game.state.two_minute_warning_called = True
    game.state.is_home_possession = True
    result = PlayResult(ResultType.YARDS, yards=3)
    outcome = PlayOutcome(
        play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD, result=result)
    if reason == "incomplete":
        result.result_type = ResultType.INCOMPLETE
    elif reason == "oob":
        result.out_of_bounds = True
    elif reason in ("turnover", "touchdown", "safety"):
        setattr(outcome, reason, True)
    elif reason == "downs":
        game.state.is_home_possession = False
    elif reason == "penalty":
        outcome.penalty_applied = True
    elif reason == "pending":
        outcome.pending_penalty_decision = True
    elif reason == "no-timeouts":
        game.state.away_timeouts = 0
    elif reason == "short-play":
        game.state.time_remaining = 50 / 60
    elif reason == "already-used":
        outcome.timeout_used = True
    before_time = game.state.time_remaining
    before_timeouts = game.state.away_timeouts
    assert not game.apply_defensive_timeout(
        outcome, time_before_play=1.0, quarter_before_play=4,
        offense_was_home=True, two_minute_warning_before=reason != "warning",
    )
    assert game.state.time_remaining == before_time
    assert game.state.away_timeouts == before_timeouts


def test_defensive_timeout_can_save_the_last_running_clock_play() -> None:
    game = make_sample_game()
    game.state.quarter = 4
    game.state.time_remaining = 0
    game.state.game_over = True
    game.state.two_minute_warning_called = True
    game.state.is_home_possession = True
    outcome = PlayOutcome(
        play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
        result=PlayResult(ResultType.YARDS, yards=3))
    assert game.apply_defensive_timeout(
        outcome, time_before_play=0.5, quarter_before_play=4,
        offense_was_home=True, two_minute_warning_before=True,
    )
    assert game.state.time_remaining == pytest.approx(20 / 60, abs=0.001)
    assert not game.state.game_over
    assert game.state.away_timeouts == 2


@pytest.mark.parametrize("remaining", [0, 1])
def test_halftime_rewind_uses_first_half_timeout_budget(remaining: int) -> None:
    game = make_sample_game()
    game.state.quarter = 2
    game.state.time_remaining = 0.5
    game.state.is_home_possession = True
    game.state.two_minute_warning_called = True
    game.state.home_timeouts = 1
    game.state.away_timeouts = remaining
    game._use_time(35)
    assert game.state.quarter == 3
    outcome = PlayOutcome(
        play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
        result=PlayResult(ResultType.YARDS, yards=3))
    used = game.apply_defensive_timeout(
        outcome, time_before_play=0.5, quarter_before_play=2,
        offense_was_home=True, two_minute_warning_before=True,
        timeouts_before_play=(1, remaining),
    )
    assert used is bool(remaining)
    if remaining:
        assert game.state.quarter == 2
        assert game.state.time_remaining == pytest.approx(20 / 60, abs=0.001)
        assert (game.state.home_timeouts, game.state.away_timeouts) == (1, 0)
        assert game.state.two_minute_warning_called
    else:
        assert game.state.quarter == 3
        assert (game.state.home_timeouts, game.state.away_timeouts) == (3, 3)


@pytest.mark.parametrize("remaining", [0, 2])
def test_offensive_timeout_charges_the_offense_and_requires_a_timeout(remaining: int) -> None:
    game = make_sample_game()
    game.state.quarter = 4
    game.state.time_remaining = 1.0
    game.state.two_minute_warning_called = True
    game.state.is_home_possession = True
    game.state.home_timeouts = remaining
    result = PlayResult(ResultType.YARDS, yards=3)
    choice = SimpleNamespace(penalty_options=[], offsetting=False, play_result=result)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice), patch(
        "paydirt.game_engine.random.uniform", return_value=35
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.LINE_PLUNGE, DefenseType.STANDARD, call_timeout=True)
    assert outcome.timeout_used is bool(remaining)
    assert game.state.home_timeouts == max(0, remaining - 1)
    assert game.state.away_timeouts == 3
    expected_seconds = 10 if remaining else 35
    assert (1.0 - game.state.time_remaining) * 60 == pytest.approx(expected_seconds, abs=0.03)

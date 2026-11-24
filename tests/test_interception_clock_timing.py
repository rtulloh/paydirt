"""Clean scrimmage interceptions use the shortest change-of-possession time."""

from unittest.mock import Mock

import pytest

from paydirt import interactive_game as cli
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


def interception_result() -> PlayResult:
    """Build a completed interception whose return time is deterministic."""
    return PlayResult(
        ResultType.INTERCEPTION,
        yards=3,
        turnover=True,
        raw_result="INT 3",
        dice_roll=24,
        int_return_yards=6,
        int_return_dice=30,
    )


def pick_six_result() -> PlayResult:
    """Build an interception whose return reaches the end zone."""
    return PlayResult(
        ResultType.INTERCEPTION,
        yards=3,
        turnover=True,
        raw_result="INT 3",
        dice_roll=24,
        int_return_yards=97,
        int_return_dice=30,
    )


def prepare_game():
    """Create the reported Q2 0:41 scrimmage situation with public charts."""
    game = make_sample_game()
    game.state.quarter = 2
    game.state.time_remaining = 41 / 60
    game.state.two_minute_warning_called = True
    game.state.ball_position = 11
    game.state.down, game.state.yards_to_go = 1, 10
    return game


@pytest.mark.parametrize("direct", [False, True], ids=["procedure", "direct"])
@pytest.mark.parametrize("call_timeout", [False, True], ids=["no-timeout", "timeout"])
def test_scrimmage_interception_uses_ten_seconds_and_conserves_timeout(
    monkeypatch: pytest.MonkeyPatch, direct: bool, call_timeout: bool,
) -> None:
    """A Q2 0:41 interception leaves 0:31; T is not needed or charged."""
    game = prepare_game()
    result = interception_result()
    timing = Mock(return_value=41)
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(result),
    )
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)

    if direct:
        outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    else:
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS,
            DefenseType.STANDARD,
            call_timeout=call_timeout,
        )

    assert outcome.turnover is True
    assert outcome.timeout_used is False
    assert game.state.quarter == 2
    assert game.state.time_remaining * 60 == pytest.approx(31)
    assert outcome.clock_trace is not None
    assert outcome.clock_trace.requested_seconds == 10
    assert outcome.clock_trace.charged_seconds == pytest.approx(10)
    assert not outcome.clock_trace.period_ended
    assert game.state.home_timeouts == game.state.away_timeouts == 3
    timing.assert_not_called()


def test_timeout_skip_message_explains_the_change_of_possession() -> None:
    """A requested T after an interception reports why no timeout was spent."""
    game = prepare_game()
    outcome = PlayOutcome(
        PlayType.MEDIUM_PASS,
        DefenseType.STANDARD,
        PlayResult(ResultType.INTERCEPTION),
        turnover=True,
    )

    should_apply, message = game._should_apply_timeout_after_play(
        outcome, play_seconds=10, quarter_before_play=2,
    )

    assert should_apply is False
    assert "change of possession" in message


@pytest.mark.parametrize("direct", [False, True], ids=["procedure", "direct"])
def test_ordinary_completion_still_uses_the_scrimmage_timing_sample(
    monkeypatch: pytest.MonkeyPatch, direct: bool,
) -> None:
    """The interception rule must not shorten ordinary completed passes."""
    game = prepare_game()
    result = PlayResult(ResultType.YARDS, yards=7)
    timing = Mock(return_value=41)
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(result),
    )
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)

    if direct:
        outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    else:
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS,
            DefenseType.STANDARD,
        )

    assert outcome.turnover is False
    assert game.state.quarter == 3
    assert game.state.time_remaining == 15
    assert outcome.clock_trace is not None
    assert outcome.clock_trace.requested_seconds == 41
    assert outcome.clock_trace.charged_seconds == pytest.approx(41)
    timing.assert_called_once()


@pytest.mark.parametrize("direct", [False, True], ids=["procedure", "direct"])
def test_pick_six_uses_the_shortest_interception_time(
    monkeypatch: pytest.MonkeyPatch, direct: bool,
) -> None:
    """A scoring change of possession still uses the ten-second play row."""
    game = prepare_game()
    game.state.defense_team.special_teams.interception_return = {30: "TD"}
    result = pick_six_result()
    timing = Mock(return_value=41)
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(result),
    )
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (30, "TD"))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)

    if direct:
        outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    else:
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS,
            DefenseType.STANDARD,
        )

    assert outcome.turnover is True
    assert outcome.touchdown is True
    assert game.state.quarter == 2
    assert game.state.time_remaining * 60 == pytest.approx(31)
    assert outcome.clock_trace is not None
    assert outcome.clock_trace.requested_seconds == 10
    assert outcome.clock_trace.charged_seconds == pytest.approx(10)
    timing.assert_not_called()


@pytest.mark.parametrize("direct", [False, True], ids=["procedure", "direct"])
def test_immediate_end_zone_touchback_uses_ten_seconds(
    monkeypatch: pytest.MonkeyPatch, direct: bool,
) -> None:
    """A no-return end-zone interception still uses change-of-possession time."""
    game = prepare_game()
    game.state.ball_position = 95
    game.state.defense_team.special_teams.interception_return = {}
    result = PlayResult(
        ResultType.INTERCEPTION,
        yards=5,
        turnover=True,
        raw_result="INT 5",
        dice_roll=24,
        end_zone_return_choice=False,
    )
    timing = Mock(return_value=41)
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(result),
    )
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", timing)

    if direct:
        outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    else:
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS,
            DefenseType.STANDARD,
        )

    assert outcome.turnover is True
    assert game.state.ball_position == 20
    assert game.state.quarter == 2
    assert game.state.time_remaining * 60 == pytest.approx(31)
    assert outcome.clock_trace is not None
    assert outcome.clock_trace.requested_seconds == 10
    assert outcome.clock_trace.charged_seconds == pytest.approx(10)
    timing.assert_not_called()


def test_resumed_cli_explains_timeout_skipped_after_interception(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """The player sees why T did not stop an already-stopped clock."""
    game = prepare_game()
    game.state.is_home_possession = True
    ai = Mock(use_analysis=False)
    ai.select_defense.return_value = DefenseType.STANDARD
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_game_status", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.MEDIUM_PASS, False, False, False, True, False))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME",
        "away_score": 0, "home_score": 0, "quarter": 2,
        "time_remaining": 41 / 60,
    })
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, False, True, None))
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: (
        PenaltyChoice(interception_result())
    ))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", Mock(return_value=41))
    class ReachedNextAction(Exception):
        pass

    def stop_at_next_defense_prompt(*args: object) -> None:
        raise ReachedNextAction

    monkeypatch.setattr(cli, "display_play_result", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_defense_play", stop_at_next_defense_prompt)

    with pytest.raises(ReachedNextAction):
        cli.resume_game("synthetic.save")

    assert "change of possession" in capsys.readouterr().out

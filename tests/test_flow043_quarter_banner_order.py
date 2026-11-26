"""FLOW-043: announce a Q1/Q3 period end before its untimed try and kickoff.

A touchdown that expires the clock in Q1 or Q3 still owes its try and its
kickoff, and the kickoff is taken in the new period. The banner therefore has
to print with the score, not on the next loop iteration - otherwise the period
end is announced after the next period has already run. Halftime is the
deliberate exception: it waits for the second-half kickoff.
"""

from unittest.mock import Mock

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import ClockTrace, PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


class ReachedNextPeriod(Exception):
    """Stop the loop once the scoring chain and its banner have printed."""


def prepare_game(quarter: int, seconds: float) -> PaydirtGameEngine:
    """Public sample teams, synthetic score-at-the-wire situation."""
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = seconds / 60
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 95, 1, 5
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.special_teams.kickoff = dict.fromkeys(range(10, 40), "65")
        chart.special_teams.kickoff_return = dict.fromkeys(range(10, 40), "0")
        chart.special_teams.extra_point_no_good = []
    return game


def run_resumed(
    monkeypatch: pytest.MonkeyPatch,
    game: PaydirtGameEngine,
    stop_quarter: int,
    stop_prompt: str | None = None,
    expect_stop: bool = True,
) -> None:
    """Drive the resumed CLI loop through one touchdown, then stop."""
    ai = Mock(use_analysis=False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout_on_defense.return_value = False
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, False, True, None))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME",
        "away_score": 0, "home_score": 0, "quarter": game.state.quarter,
        "time_remaining": game.state.time_remaining})

    def user_input(prompt: str = "") -> str:
        if stop_prompt and stop_prompt in prompt:
            raise ReachedNextPeriod
        return ""

    monkeypatch.setattr("builtins.input", user_input)
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play_with_penalties",
        lambda *args: PenaltyChoice(
            PlayResult(ResultType.YARDS, yards=5, description="Synthetic touchdown run")
        ),
    )
    monkeypatch.setattr(
        "paydirt.game_engine.resolve_play",
        lambda *args: PlayResult(ResultType.YARDS, yards=5, description="Synthetic touchdown run"),
    )
    # The touchdown must consume the remaining clock; the kickoff fits in Q4.
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: high)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (24, "Synthetic roll"))

    def offense(*args: object) -> tuple:
        return PlayType.MEDIUM_PASS, False, False, False, False, False

    def status(*args: object) -> None:
        if game.state.quarter == stop_quarter:
            raise ReachedNextPeriod

    monkeypatch.setattr(cli, "get_human_offense_play", offense)
    monkeypatch.setattr(cli, "display_game_status", status)
    if expect_stop:
        with pytest.raises(ReachedNextPeriod):
            cli.resume_game("synthetic.save")
    else:
        # A return score can end the game before the stop condition is reached.
        cli.resume_game("synthetic.save")


def test_q3_expiring_touchdown_announces_before_the_untimed_try(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    game = prepare_game(quarter=3, seconds=7)
    run_resumed(monkeypatch, game, stop_quarter=4)
    output = capsys.readouterr().out

    assert "END OF QUARTER 3" in output
    assert output.index("END OF QUARTER 3") < output.index("Extra point GOOD!")

    # Reordering must not move the points or the period attribution.
    assert game.state.home_score == 7
    periods = {p["quarter"]: (p["home"], p["away"]) for p in game.get_period_scores()}
    assert periods[3] == (7, 0)
    assert periods[4] == (0, 0)


def test_q3_expiring_touchdown_banner_precedes_the_kickoff(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    game = prepare_game(quarter=3, seconds=7)
    run_resumed(monkeypatch, game, stop_quarter=4)
    output = capsys.readouterr().out

    assert "END OF QUARTER 3" in output
    assert output.index("END OF QUARTER 3") < output.index("kicks off")


def test_halftime_still_waits_for_the_second_half_kickoff(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    game = prepare_game(quarter=2, seconds=7)
    run_resumed(monkeypatch, game, stop_quarter=3, stop_prompt="2nd half kickoff")
    output = capsys.readouterr().out

    # The try still precedes the halftime announcement, as before this fix.
    assert "END OF QUARTER 2" in output
    assert output.index("Extra point GOOD!") < output.index("END OF QUARTER 2")
    assert "HALFTIME" in output


def test_banner_prints_exactly_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """The loop's own transition handler must not repeat the announcement."""
    game = prepare_game(quarter=3, seconds=7)
    run_resumed(monkeypatch, game, stop_quarter=4)
    output = capsys.readouterr().out
    assert output.count("END OF QUARTER 3") == 1


def test_q3_touchdown_then_q4_kickoff_return_td_announces_each_period_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A period-ending return TD must not repeat the Q3 banner.

    The return score is handled by a different in-loop branch than the
    scrimmage touchdown, so both need to register the announced period.
    """
    game = prepare_game(quarter=3, seconds=7)
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.special_teams.kickoff_return = dict.fromkeys(range(10, 40), "TD")
    run_resumed(monkeypatch, game, stop_quarter=4, expect_stop=False)
    output = capsys.readouterr().out
    assert output.count("END OF QUARTER 3") == 1


class TestPeriodEndedByScore:
    """The predicate is deliberately narrow: Q1/Q3 only, one period forward."""

    @pytest.mark.parametrize("before,after", [(1, 2), (3, 4)])
    def test_returns_the_period_a_q1_or_q3_score_ended(self, before: int, after: int) -> None:
        game = prepare_game(quarter=before, seconds=7)
        game.state.quarter = after
        assert cli._period_ended_by_score(game, before) == before

    @pytest.mark.parametrize("before,after", [(2, 3), (4, 4), (1, 3)])
    def test_returns_none_for_halftime_q4_and_a_stale_quarter(
        self, before: int, after: int,
    ) -> None:
        game = prepare_game(quarter=before, seconds=7)
        game.state.quarter = after
        assert cli._period_ended_by_score(game, before) is None


def test_touchdown_without_a_clock_trace_or_callback_still_runs_the_try(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Legacy/restored outcomes may lack a trace and may not pass a callback."""
    game = prepare_game(quarter=3, seconds=7)
    game.state.quarter = 4
    outcome = PlayOutcome(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD,
        PlayResult(ResultType.YARDS, yards=5, description="Synthetic touchdown"),
        touchdown=True, clock_trace=None,
    )
    monkeypatch.setattr(cli, "_run_try_and_kickoff", lambda *args: None)
    result = cli._complete_touchdown_sequence(game, outcome, human_is_home=True)
    output = capsys.readouterr().out
    assert result is outcome
    assert "END OF QUARTER" not in output


def test_period_announcement_without_a_callback_skips_only_the_notification(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A caller that passes no callback still gets the banner, not a crash."""
    game = prepare_game(quarter=3, seconds=7)
    game.state.quarter = 4
    trace = ClockTrace(
        start_quarter=3, start_seconds=7, end_quarter=4, end_seconds=900,
        requested_seconds=7, charged_seconds=7, period_ended=True,
    )
    outcome = PlayOutcome(
        PlayType.MEDIUM_PASS, DefenseType.STANDARD,
        PlayResult(ResultType.YARDS, yards=5, description="Synthetic touchdown"),
        touchdown=True, clock_trace=trace,
    )
    monkeypatch.setattr(cli, "_run_try_and_kickoff", lambda *args: None)
    cli._complete_touchdown_sequence(game, outcome, human_is_home=True)
    assert "END OF QUARTER 3" in capsys.readouterr().out

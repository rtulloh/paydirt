"""TRACE-009: prove the actual TD/try/kickoff clock sequence without invented rolls."""

from unittest.mock import Mock

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def prepare_game(home: bool = True) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 2, 45 / 60
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 95, 1, 5
    game.state.two_minute_warning_called = True
    kicking = game.state.home_chart if home else game.state.away_chart
    receiving = game.state.away_chart if home else game.state.home_chart
    kicking.special_teams.kickoff[24] = "58"
    kicking.special_teams.extra_point_no_good = []
    receiving.special_teams.kickoff_return[24] = "F+0"
    receiving.peripheral.fumble_recovered_range = (10, 19)
    return game


def touchdown(
    game: PaydirtGameEngine, monkeypatch: pytest.MonkeyPatch, seconds: float, direct: bool = False,
) -> PlayOutcome:
    result = PlayResult(ResultType.YARDS, yards=5, description="Synthetic five-yard completion")
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(result))
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: result)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: seconds)
    run = game.run_play if direct else game.run_play_with_penalty_procedure
    return run(PlayType.MEDIUM_PASS, DefenseType.STANDARD)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("play_seconds,kick_seconds", [(25, 5), (35, 10), (40, 15)])
def test_td_try_kickoff_trace_explains_remaining_snap_or_halftime(
    monkeypatch: pytest.MonkeyPatch, home: bool, direct: bool,
    play_seconds: int, kick_seconds: int,
) -> None:
    game = prepare_game(home)
    out = touchdown(game, monkeypatch, play_seconds, direct)
    assert out.touchdown
    assert getattr(out, "clock_trace", None) is not None, "Touchdown needs engine-owned clock evidence"
    td_trace = out.clock_trace
    assert td_trace.start_seconds == 45
    assert td_trace.end_seconds == pytest.approx(45 - play_seconds)
    assert td_trace.requested_seconds == td_trace.charged_seconds == play_seconds
    assert not td_trace.period_ended
    assert game.can_kickoff_after_play()
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (24, "Synthetic roll"))
    before = game.state.time_remaining
    success, description = game.attempt_extra_point()
    assert success and game.state.time_remaining == before
    pat_trace = game.last_clock_trace
    assert pat_trace.requested_seconds == pat_trace.charged_seconds == 0
    assert pat_trace.start_seconds == pat_trace.end_seconds == pytest.approx(before * 60)
    assert "untimed PAT" in description
    rolls = Mock(side_effect=[(24, "Kick"), (24, "Return"), (30, "Lost fumble")])
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", rolls)
    monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda *args: kick_seconds)
    kick = game.kickoff(kicking_home=home)
    assert kick.turnover and game.state.is_home_possession is home
    assert game.state.ball_position == 93  # Recovery at the receiving team's seven.
    assert rolls.call_count == 3
    trace = kick.clock_trace
    assert trace.start_seconds == pytest.approx(45 - play_seconds)
    assert trace.requested_seconds == kick_seconds
    assert trace.charged_seconds == pytest.approx(min(kick_seconds, 45 - play_seconds))
    expired = play_seconds + kick_seconds >= 45
    assert trace.period_ended is expired
    assert game.halftime_pending() is expired
    assert game.state.quarter == (3 if expired else 2)
    assert game.state.time_remaining * 60 == pytest.approx(900 if expired else 45 - play_seconds - kick_seconds)
    assert out.clock_trace is td_trace  # Later try/kickoff cannot overwrite the TD's evidence.
    if not expired:
        next_play = touchdown(game, monkeypatch, 5)
        assert not next_play.touchdown  # Five yards from the opponent's seven.
        assert game.state.quarter == 2
        assert game.state.time_remaining * 60 == pytest.approx(10)


@pytest.mark.parametrize("requested", [45, 50])
def test_td_that_expires_half_records_cap_and_does_not_require_another_kick(
    monkeypatch: pytest.MonkeyPatch, requested: int,
) -> None:
    game = prepare_game()
    out = touchdown(game, monkeypatch, requested)
    trace = getattr(out, "clock_trace", None)
    assert trace is not None
    assert trace.requested_seconds == requested and trace.charged_seconds == 45
    assert trace.period_ended
    assert trace.end_quarter == 3 and trace.end_seconds == 900
    assert "period ended" in trace.description and "Q3 15:00" in trace.description
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (24, "Try"))
    game.attempt_extra_point()
    assert game.state.quarter == 3 and game.state.time_remaining == 15
    assert not game.can_kickoff_after_play()
    assert game.last_clock_trace.charged_seconds == 0


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("play_seconds,kick_seconds", [(25, 5), (35, 10)])
def test_new_and_resumed_cli_expose_each_clock_record_and_preserve_next_action(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    resumed: bool, play_seconds: int, kick_seconds: int,
) -> None:
    game = prepare_game()
    ai = Mock(use_analysis=False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout_on_defense.return_value = False
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    def user_input(prompt: str = "") -> str:
        if "2nd half kickoff" in prompt:
            raise ReachedNextAction
        return ""

    monkeypatch.setattr("builtins.input", user_input)
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=[game.state.home_chart, game.state.away_chart]))
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, False, True, None))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME",
        "away_score": 0, "home_score": 0, "quarter": 2, "time_remaining": .75})
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=5, description="Synthetic completion")))
    monkeypatch.setattr("paydirt.game_engine.random.uniform", Mock(side_effect=[play_seconds, kick_seconds]))
    # New-game initialization performs an opening kickoff; retain the prepared Q2 scenario.
    real_kickoff = game.kickoff
    calls = 0

    def kickoff(**kwargs: bool) -> PlayOutcome:
        nonlocal calls
        calls += 1
        if not resumed and calls == 1:
            return PlayOutcome(
                PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
                description="Synthetic opening kickoff",
            )
        return real_kickoff(**kwargs)

    monkeypatch.setattr(game, "kickoff", kickoff)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", Mock(side_effect=[
        (24, "PAT"), (24, "Kick"), (24, "Return"), (30, "Lost fumble")]))

    class ReachedNextAction(Exception):
        pass

    actions = 0

    def offense(*args: object) -> tuple:
        nonlocal actions
        actions += 1
        if actions > 1:
            raise ReachedNextAction
        return PlayType.MEDIUM_PASS, False, False, False, False, False

    def status(*args: object) -> None:
        if game.state.quarter == 3:
            raise ReachedNextAction

    monkeypatch.setattr(cli, "get_human_offense_play", offense)
    monkeypatch.setattr(cli, "display_game_status", status)
    with pytest.raises(ReachedNextAction):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()
    output = capsys.readouterr().out
    assert output.count("Clock:") == 3
    assert "requested 0.000s; charged 0.000s" in output
    assert "untimed PAT" in output
    if play_seconds + kick_seconds == 45:
        assert "HALFTIME" in output
    else:
        assert "HALFTIME" not in output
        assert game.state.quarter == 2 and game.state.time_remaining == pytest.approx(.25)


@pytest.mark.parametrize("quarter,seconds,duration,oob,charged", [
    (2, 125, 35, False, 5), (2, 45, 35, True, 10), (2, 5, 15, False, 5),
])
def test_clock_evidence_reports_warning_oob_and_expiry_caps(
    quarter: int, seconds: int, duration: int, oob: bool, charged: int,
) -> None:
    game = prepare_game()
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    game.state.two_minute_warning_called = False
    game._use_time(duration, out_of_bounds=oob)
    trace = game.last_clock_trace
    assert trace.requested_seconds == duration
    assert trace.charged_seconds == pytest.approx(charged)
    if seconds == 125:
        assert trace.end_seconds == 120
        assert "two-minute warning" in trace.description


@pytest.mark.parametrize("pending_extension", [False, True])
def test_clock_expiry_held_for_foul_or_untimed_down_is_not_a_period_end(pending_extension: bool) -> None:
    game = prepare_game()
    game.state.time_remaining = 5 / 60
    game.state.untimed_down_pending = pending_extension
    game._use_time(10, defensive_penalty=not pending_extension)
    trace = game.last_clock_trace
    assert trace.charged_seconds == pytest.approx(5)
    assert trace.end_quarter == 2 and trace.end_seconds == 0
    assert not trace.period_ended
    assert "period held" in trace.description


@pytest.mark.parametrize("good", [False, True])
def test_pat_success_or_failure_is_zero_time_evidence(
    monkeypatch: pytest.MonkeyPatch, good: bool,
) -> None:
    game = prepare_game()
    game.state.home_chart.special_teams.extra_point_no_good = [] if good else [24]
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (24, "Try"))
    success, description = game.attempt_extra_point()
    assert success is good
    trace = game.last_clock_trace
    assert trace.start_quarter == trace.end_quarter == 2
    assert trace.start_seconds == trace.end_seconds == 45
    assert trace.requested_seconds == trace.charged_seconds == 0
    assert trace.description in description

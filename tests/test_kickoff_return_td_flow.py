"""Reproduce missing PAT/kickoff after a kickoff-return touchdown in the CLI."""

from unittest.mock import patch

import pytest

from paydirt import interactive_game
from paydirt.chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType


class NextScrimmage(Exception):
    """Stop the real CLI loop when it tries to resume ordinary play."""


def make_chart(short_name: str) -> TeamChart:
    return TeamChart(
        peripheral=PeripheralData(
            year=1983, team_name=short_name, team_nickname="Test", short_name=short_name,
            power_rating=50,
        ),
        offense=OffenseChart(short_pass={16: "22"}),
        defense=DefenseChart(),
        special_teams=SpecialTeamsChart(
            kickoff={28: "50", 10: "60"},
            kickoff_return={28: "85", 10: "10"},
            punt={}, punt_return={}, interception_return={}, field_goal={}, extra_point_no_good=[],
        ),
        team_dir="",
    )


@pytest.mark.parametrize("initial_scoring_is_home", [False, True])
def test_cli_return_td_requires_pat_and_another_kickoff(
    monkeypatch, capsys, initial_scoring_is_home: bool,
) -> None:
    """CIN TD/PAT -> kickoff -> BAL return TD must lead to BAL PAT and kickoff."""
    game = PaydirtGameEngine(make_chart("BAL '83"), make_chart("CIN '83"))
    game.state.quarter = 3
    game.state.time_remaining = 6 + 35 / 60
    game.state.home_score = 10 if not initial_scoring_is_home else 3
    game.state.away_score = 3 if not initial_scoring_is_home else 10
    game.state.is_home_possession = initial_scoring_is_home
    game.state.ball_position = 92
    game.state.down = 1
    game.state.yards_to_go = 8
    initial_score = (game.state.home_score, game.state.away_score)

    # Mock only startup/terminal interaction and decisions; scoring and kicks use the engine.
    monkeypatch.setattr(interactive_game, "COMPACT_MODE", True)
    monkeypatch.setattr(interactive_game, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(interactive_game, "get_save_info", lambda _: {
        "saved_at": "test", "away_team": "CIN", "home_team": "BAL",
        "away_score": game.state.away_score, "home_score": game.state.home_score,
        "quarter": 3, "time_remaining": game.state.time_remaining,
    })
    monkeypatch.setattr(interactive_game, "load_game", lambda _: (game, False, True, None))
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(interactive_game, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(interactive_game, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, False))
    monkeypatch.setattr(interactive_game, "get_human_offense_play", lambda *args: (
        PlayType.SHORT_PASS, False, False, False, False, False,
    ))
    monkeypatch.setattr(interactive_game, "computer_select_defense", lambda *args: DefenseType.STANDARD)
    monkeypatch.setattr(interactive_game.ComputerAI, "select_offense_with_clock_management", lambda *args: (
        PlayType.SHORT_PASS, False, False, False, 0, False,
    ))
    status_calls = []

    def stop_before_next_scrimmage(*args) -> None:
        status_calls.append(game.state.ball_position)
        if len(status_calls) > 1:
            raise NextScrimmage

    monkeypatch.setattr(interactive_game, "display_game_status", stop_before_next_scrimmage)
    with patch('paydirt.play_resolver.roll_chart_dice', return_value=(16, 'B1+W2+W3=16')), patch('paydirt.play_resolver.roll_white_dice', return_value=(2, 'R2+G0=2')), patch('paydirt.game_engine.roll_chart_dice', side_effect=[(37, 'PAT=37'), (28, 'KO=28'), (28, 'RT=28'), (37, 'PAT=37'), (10, 'KO=10'), (10, 'RT=10')]), patch.object(game, 'attempt_extra_point', wraps=game.attempt_extra_point) as pat, patch.object(game, 'kickoff', wraps=game.kickoff) as kickoff, pytest.raises(NextScrimmage):
        interactive_game.resume_game("test-save.json", compact=True)

    output = capsys.readouterr().out
    assert "RETURNED FOR A TOUCHDOWN!" in output, output
    # Both real touchdowns must have been credited before diagnosing missing follow-up.
    assert sum(play.points == 6 for play in game.state.scoring_plays) == 2
    assert pat.call_count == 2, (
        f"Both touchdowns require a PAT before another scrimmage; got {pat.call_count}. "
        f"Score={game.state.home_score}-{game.state.away_score}, "
        f"ball_position={game.state.ball_position}.\n{output}"
    )
    assert [call.kwargs["kicking_home"] for call in kickoff.call_args_list] == [
        initial_scoring_is_home, not initial_scoring_is_home,
    ]
    assert (game.state.home_score, game.state.away_score) == (initial_score[0] + 7, initial_score[1] + 7)
    assert game.state.is_home_possession == initial_scoring_is_home
    assert game.state.ball_position == 15


@pytest.mark.parametrize("initial_scoring_is_home", [False, True])
def test_new_game_loop_handles_return_td_before_next_scrimmage(
    monkeypatch, initial_scoring_is_home: bool,
) -> None:
    """Exercise the new-game entry point, not just the saved-game loop."""
    from paydirt.game_engine import PlayOutcome
    from paydirt.play_resolver import PlayResult, ResultType

    home, away = make_chart("BAL '83"), make_chart("CIN '83")
    game = PaydirtGameEngine(home, away)
    game.state.quarter = 3
    game.state.time_remaining = 6.5
    game.state.home_score = 10 if not initial_scoring_is_home else 3
    game.state.away_score = 3 if not initial_scoring_is_home else 10
    initial_score = (game.state.home_score, game.state.away_score)
    monkeypatch.setattr(interactive_game, "COMPACT_MODE", True)
    monkeypatch.setattr(interactive_game, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(interactive_game, "clear_screen", lambda: None)
    charts = iter([home, away])
    monkeypatch.setattr(interactive_game, "select_team", lambda *args, **kwargs: next(charts))
    monkeypatch.setattr(interactive_game, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(interactive_game.random, "choice", lambda choices: choices[0])
    monkeypatch.setattr(interactive_game, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(interactive_game, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, False))
    monkeypatch.setattr(interactive_game, "get_human_offense_play", lambda *args: (
        PlayType.SHORT_PASS, False, False, False, False, False,
    ))
    monkeypatch.setattr(interactive_game, "computer_select_defense", lambda *args: DefenseType.STANDARD)
    monkeypatch.setattr(interactive_game.ComputerAI, "select_offense_with_clock_management", lambda *args: (
        PlayType.SHORT_PASS, False, False, False, 0, False,
    ))
    status_calls = []

    def stop_before_next_scrimmage(*args) -> None:
        status_calls.append(game.state.ball_position)
        if len(status_calls) > 1:
            raise NextScrimmage

    monkeypatch.setattr(interactive_game, "display_game_status", stop_before_next_scrimmage)
    real_kickoff = game.kickoff
    kickers = []

    def kickoff_from_scenario(kicking_home: bool) -> PlayOutcome:
        kickers.append(kicking_home)
        if len(kickers) == 1:
            # Skip only the unrelated opening kickoff to start at the reported drive.
            game.state.is_home_possession = initial_scoring_is_home
            game.state.ball_position = 92
            game.state.down = 1
            game.state.yards_to_go = 8
            return PlayOutcome(
                play_type=PlayType.KICKOFF, defense_type=DefenseType.STANDARD,
                result=PlayResult(ResultType.YARDS), description="Opening kickoff complete",
            )
        return real_kickoff(kicking_home=kicking_home)

    monkeypatch.setattr(game, "kickoff", kickoff_from_scenario)
    with patch('paydirt.play_resolver.roll_chart_dice', return_value=(16, 'B1+W2+W3=16')), patch('paydirt.play_resolver.roll_white_dice', return_value=(2, 'R2+G0=2')), patch('paydirt.game_engine.roll_chart_dice', side_effect=[(37, 'PAT=37'), (28, 'KO=28'), (28, 'RT=28'), (37, 'PAT=37'), (10, 'KO=10'), (10, 'RT=10')]), patch.object(game, 'attempt_extra_point', wraps=game.attempt_extra_point) as pat, pytest.raises(NextScrimmage):
        interactive_game.run_interactive_game(compact=True)
    assert pat.call_count == 2
    assert kickers[1:] == [initial_scoring_is_home, not initial_scoring_is_home]
    assert (game.state.home_score, game.state.away_score) == (initial_score[0] + 7, initial_score[1] + 7)
    assert game.state.is_home_possession == initial_scoring_is_home
    assert game.state.ball_position == 15


def test_consecutive_return_touchdowns_each_get_pat_and_kickoff(monkeypatch) -> None:
    """Keep processing if the kickoff after a return TD is also returned for a TD."""
    game = PaydirtGameEngine(make_chart("BAL '83"), make_chart("CIN '83"))
    game.state.quarter = 3
    game.state.time_remaining = 6.5
    monkeypatch.setattr(interactive_game, "get_kickoff_choice", lambda *args: False)
    with (
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (28, "KO=28"), (28, "RT=28"), (37, "PAT=37"), (28, "KO=28"), (28, "RT=28"),
            (37, "PAT=37"), (10, "KO=10"), (10, "RT=10"),
        ]),
        patch.object(game, "attempt_extra_point", wraps=game.attempt_extra_point) as pat,
        patch.object(game, "kickoff", wraps=game.kickoff) as kickoff,
    ):
        outcome = game.kickoff(kicking_home=False)
        outcome = interactive_game._complete_touchdown_sequence(game, outcome, human_is_home=True)
    assert pat.call_count == 2
    assert [call.kwargs["kicking_home"] for call in kickoff.call_args_list] == [False, True, False]
    assert (game.state.home_score, game.state.away_score) == (7, 7)
    assert game.state.is_home_possession is True
    assert game.state.ball_position == 15
    assert not outcome.touchdown


def test_game_ending_return_td_does_not_attempt_pat_or_kickoff(monkeypatch) -> None:
    """Respect the engine decision when a return TD ends sudden-death overtime."""
    game = PaydirtGameEngine(make_chart("BAL '83"), make_chart("CIN '83"))
    game.state.is_overtime = True
    game.state.ot_period = 1
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(28, "KO=28")):
        outcome = game.kickoff(kicking_home=False)
    assert outcome.touchdown
    assert game.state.game_over
    with (
        patch.object(game, "attempt_extra_point") as pat,
        patch.object(game, "kickoff") as kickoff,
    ):
        assert interactive_game._complete_touchdown_sequence(game, outcome, True) is outcome
    pat.assert_not_called()
    kickoff.assert_not_called()

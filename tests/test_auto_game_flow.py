"""Deterministic auto-mode orchestration using real engine rules and public charts."""

from itertools import chain, repeat
from typing import Callable
from unittest.mock import Mock, create_autospec

import pytest

from paydirt import auto_game
from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


class StopScenario(Exception):
    """Stop just before the next scripted call, without pretending the game ended."""


@pytest.fixture
def run_scenario(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> Callable:
    def run(setup: Callable = lambda game: None, plays: tuple = (),
            after_opening: Callable = lambda game: None, accept_play: bool = True,
            engine_rolls: tuple = (16,), offense_rolls: tuple = (16,)) -> dict:
        game = make_sample_game()
        for chart in (game.state.home_chart, game.state.away_chart):
            chart.offense.line_plunge = dict.fromkeys(range(10, 40), "1")
            chart.offense.medium_pass = dict.fromkeys(range(10, 40), "0")
            chart.defense.modifiers.clear()
            chart.special_teams.kickoff = dict.fromkeys(range(10, 40), "65")
            chart.special_teams.kickoff_return = dict.fromkeys(range(10, 40), "0")
            chart.special_teams.field_goal = dict.fromkeys(range(10, 40), "100")
            chart.special_teams.punt = dict.fromkeys(range(10, 40), "40*")
            chart.special_teams.punt_return = dict.fromkeys(range(10, 40), "0")
            chart.special_teams.interception_return = dict.fromkeys(range(10, 40), "0")
            chart.special_teams.extra_point_no_good = []
        setup(game)
        calls = iter(plays)
        ais = [ComputerAI(), ComputerAI()]  # Away, then home, matching auto mode.
        for ai in ais:
            ai.should_accept_penalty = create_autospec(
                ai.should_accept_penalty, return_value=(accept_play, 0))
            ai.select_defense = lambda game: DefenseType.STANDARD

            def choose(game: PaydirtGameEngine) -> tuple:
                try:
                    play = next(calls)
                except StopIteration:
                    raise StopScenario from None
                return (play, False, False, False, 0, False)

            ai.select_offense_with_clock_management = choose
        monkeypatch.setattr(auto_game, "ComputerAI", Mock(side_effect=ais))
        monkeypatch.setattr(auto_game, "find_team_charts", lambda path: [("2026", "sample", "sample")])
        monkeypatch.setattr(auto_game, "resolve_team_path", lambda spec, charts, root: spec)
        monkeypatch.setattr(auto_game, "load_team_chart", lambda path: (
            game.state.away_chart if path == "away" else game.state.home_chart))
        monkeypatch.setattr(auto_game, "PaydirtGameEngine", lambda home, away: game)
        monkeypatch.setattr(auto_game.time, "sleep", lambda delay: None)
        monkeypatch.setattr("paydirt.game_engine.random.uniform", lambda low, high: low)
        monkeypatch.setattr("paydirt.play_resolver.random.choice", lambda choices: choices[0])
        erolls = iter(chain(engine_rolls, repeat(engine_rolls[-1])))
        orolls = iter(chain(offense_rolls, repeat(offense_rolls[-1])))
        monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (next(erolls), "synthetic"))
        monkeypatch.setattr("paydirt.play_resolver.roll_chart_dice", lambda: (next(orolls), "synthetic"))
        kickoff = game.kickoff
        kicks = []

        def kick(kicking_home: bool = True, kickoff_spot: int = 35):
            kicks.append((game.state.game_over, game.state.quarter,
                          game.state.time_remaining, kicking_home,
                          game.state.home_score, game.state.away_score))
            outcome = kickoff(kicking_home=kicking_home, kickoff_spot=kickoff_spot)
            if len(kicks) == 1:
                after_opening(game)
            return outcome

        monkeypatch.setattr(game, "kickoff", kick)
        finished = True
        try:
            auto_game.run_auto_game("away", "home")
        except StopScenario:
            finished = False
        return {"game": game, "ais": ais, "kicks": kicks, "finished": finished,
                "output": capsys.readouterr().out}
    return run


def set_scrimmage(game: PaydirtGameEngine, home: bool, position: int = 50,
                   seconds: float = 60, quarter: int = 1) -> None:
    game.state.is_home_possession = home
    game.state.ball_position = position
    game.state.time_remaining = seconds / 60
    game.state.quarter = quarter
    game.state.down, game.state.yards_to_go = 1, 10


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("accept_play", [False, True])
def test_scrimmage_penalty_is_resolved_before_next_call(run_scenario: Callable,
                                                       home: bool, accept_play: bool) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        for chart in (game.state.home_chart, game.state.away_chart):
            chart.offense.medium_pass.update({16: "OFF 5", 17: "INT 10"})
    result = run_scenario(setup, (PlayType.MEDIUM_PASS,),
                          lambda game: set_scrimmage(game, home), accept_play,
                          offense_rolls=(16, 17))
    state = result["game"].state
    assert state.is_home_possession is (not home if accept_play else home)
    assert state.ball_position == (40 if accept_play else 45)
    offense_stats = state.home_stats if home else state.away_stats
    assert offense_stats.interceptions_thrown == int(accept_play)
    assert offense_stats.penalties == int(not accept_play)
    assert state.time_remaining < 1
    deciding_ai = result["ais"][0 if home else 1]
    deciding_ai.should_accept_penalty.assert_called_once()
    assert all(not outcome.pending_penalty_decision for outcome in result["game"].play_log)
    assert ("INTERCEPTION" in result["output"]) is accept_play


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("accept_play", [False, True])
def test_field_goal_decision_precedes_scoring_and_kickoff(run_scenario: Callable,
                                                         home: bool, accept_play: bool) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        for chart in (game.state.home_chart, game.state.away_chart):
            chart.special_teams.field_goal[16] = "OFF 5"
    result = run_scenario(setup, (PlayType.FIELD_GOAL,),
                          lambda game: set_scrimmage(game, home, 90), accept_play,
                          offense_rolls=(16, 17))
    state = result["game"].state
    assert state.home_score == (3 if home and accept_play else 0)
    assert state.away_score == (3 if not home and accept_play else 0)
    assert len(result["kicks"]) == (2 if accept_play else 1)
    if accept_play:
        assert result["kicks"][1][3] is home
        assert state.is_home_possession is not home
    else:
        assert state.is_home_possession is home
        assert state.ball_position == 85
        assert "FIELD GOAL" not in result["output"]
    assert all(not outcome.pending_penalty_decision for outcome in result["game"].play_log)
    result["ais"][0 if home else 1].should_accept_penalty.assert_called_once()


@pytest.mark.parametrize("accept_play", [False, True])
def test_opening_kickoff_penalty_resolved_before_scrimmage(run_scenario: Callable,
                                                         accept_play: bool) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        game.state.home_chart.special_teams.kickoff[16] = "DEF 5"
    result = run_scenario(setup, accept_play=accept_play, engine_rolls=(16, 17))
    assert not hasattr(result["game"], "_pending_kickoff_penalty_state")
    assert not result["game"].state.is_home_possession
    assert len(result["kicks"]) == (1 if accept_play else 2)
    assert sum(ai.should_accept_penalty.call_count for ai in result["ais"]) == 1


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("accept_play", [False, True])
def test_punt_penalty_resolved_once(run_scenario: Callable, home: bool, accept_play: bool) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        for chart in (game.state.home_chart, game.state.away_chart):
            chart.special_teams.punt[16] = "DEF 5"
    def position(game: PaydirtGameEngine) -> None:
        set_scrimmage(game, home)
        game.state.down, game.state.yards_to_go = 4, 8
    result = run_scenario(setup, (PlayType.PUNT,), position, accept_play,
                          engine_rolls=(16, 16, 16, 17))  # kick, return, punt (DEF 5), reroll
    state = result["game"].state
    assert not hasattr(result["game"], "_pending_punt_state")
    assert state.is_home_possession is (not home if accept_play else home)
    if not accept_play:
        assert (state.ball_position, state.down, state.yards_to_go) == (55, 4, 3)
    result["ais"][1 if home else 0].should_accept_penalty.assert_called_once()


@pytest.mark.parametrize("play,position,lead", [(PlayType.FIELD_GOAL, 90, 0),
                                              (PlayType.LINE_PLUNGE, 99, 7),
                                              (PlayType.MEDIUM_PASS, 1, -7)])
@pytest.mark.parametrize("home", [False, True])
def test_game_ending_score_does_not_kick_again(run_scenario: Callable, play: PlayType,
                                             position: int, lead: int, home: bool) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        for chart in (game.state.home_chart, game.state.away_chart):
            chart.offense.medium_pass[16] = "-2"
    def ending(game: PaydirtGameEngine) -> None:
        set_scrimmage(game, home, position, 1, 4)
        game.state.home_score = 14 + (lead if home else 0)
        game.state.away_score = 14 + (lead if not home else 0)
    result = run_scenario(setup, (play,), ending)
    assert result["finished"]
    assert result["game"].state.game_over
    assert len(result["kicks"]) == 1
    assert "receives kickoff" not in result["output"]
    assert "receives safety kick" not in result["output"]


def test_consecutive_opening_return_touchdowns_complete_before_scrimmage(run_scenario: Callable) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        game.state.away_chart.special_teams.kickoff_return[16] = "TD"
        game.state.home_chart.special_teams.kickoff_return[17] = "TD"
    # Kick, return (TD), PAT, kick, return (TD), PAT, kick, return.
    result = run_scenario(setup, engine_rolls=(16, 16, 18, 17, 17, 19, 20))
    state = result["game"].state
    assert state.home_score == state.away_score == 7
    assert len(result["kicks"]) == 3
    assert result["output"].count("Extra point GOOD") == 2


def test_tied_regulation_starts_real_overtime(run_scenario: Callable) -> None:
    result = run_scenario(plays=(PlayType.FIELD_GOAL,),
                          after_opening=lambda game: set_scrimmage(game, True, 90, 0, 4))
    state = result["game"].state
    assert result["finished"] and state.game_over and state.is_overtime
    assert state.quarter == 5 and state.ot_period == 1
    assert "OVERTIME" in result["output"]
    assert "Q4 0:00" not in result["output"]
    assert len(result["kicks"]) == 2  # Opening and OT; none after the winning FG.
    assert sum(score.points for score in state.scoring_plays) == 3
    assert result["game"].get_period_scores()[-1]["home"] + result["game"].get_period_scores()[-1]["away"] == 3


def test_no_overtime_season_ends_tied(run_scenario: Callable) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        game.season_rules.overtime.enabled = False
    result = run_scenario(setup, (PlayType.LINE_PLUNGE,),
                          lambda game: set_scrimmage(game, False, 50, 1, 4))
    state = result["game"].state
    assert result["finished"] and state.game_over
    assert not state.is_overtime
    assert state.home_score == state.away_score == 0
    assert len(result["kicks"]) == 1


def test_untimed_down_remains_visible_until_engine_consumes_it(run_scenario: Callable) -> None:
    def ending(game: PaydirtGameEngine) -> None:
        set_scrimmage(game, True, 50, 0, 4)
        game.state.home_score = 7
        game.state.untimed_down_pending = True
    result = run_scenario(plays=(PlayType.LINE_PLUNGE,), after_opening=ending)
    assert "UNTIMED DOWN" in result["output"]
    assert result["finished"] and result["game"].state.game_over
    assert not result["game"].has_untimed_down()


@pytest.mark.parametrize("quarter,seconds,game_over,expected", [
    (1, 30, False, True), (2, 30, False, True), (2, 0, False, False),
    (4, 0, False, False), (4, 30, True, False), (5, 30, True, False),
])
def test_engine_controls_post_score_kickoff(quarter: int, seconds: float,
                                           game_over: bool, expected: bool) -> None:
    game = make_sample_game()
    game.state.quarter = quarter
    game.state.time_remaining = seconds / 60
    game.state.game_over = game_over
    assert game.can_kickoff_after_play(quarter) is expected


def test_engine_suppresses_post_score_kick_before_halftime() -> None:
    game = make_sample_game()
    game.state.quarter = 3
    game.state.time_remaining = 15
    assert not game.can_kickoff_after_play(2)
    assert game.can_kickoff_after_play(3)


def test_play_limit_is_a_failure_not_a_final_score(run_scenario: Callable) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        game._use_time = lambda seconds, **kwargs: False
    with pytest.raises(RuntimeError, match="play limit"):
        run_scenario(setup, tuple(repeat(PlayType.LINE_PLUNGE, 502)))


@pytest.mark.parametrize("home", [False, True])
def test_normal_scrimmage_control(run_scenario: Callable, home: bool) -> None:
    result = run_scenario(plays=(PlayType.LINE_PLUNGE,),
                          after_opening=lambda game: set_scrimmage(game, home))
    state = result["game"].state
    assert state.is_home_possession is home
    assert (state.ball_position, state.down, state.yards_to_go) == (51, 2, 9)
    assert state.time_remaining < 1
    assert len(result["kicks"]) == 1


def test_halftime_kickoff_control(run_scenario: Callable) -> None:
    result = run_scenario(plays=(PlayType.LINE_PLUNGE,),
                          after_opening=lambda game: set_scrimmage(game, False, 50, 1, 2))
    assert result["game"].state.quarter == 3
    assert result["game"].state.is_home_possession
    assert len(result["kicks"]) == 2
    assert result["kicks"][1][3] is False


def test_overtime_does_not_preempt_an_untimed_down() -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = 4, 0
    game.state.untimed_down_pending = True
    assert not game.needs_overtime()


@pytest.mark.parametrize("quarter,expected_kicks", [(1, 2), (2, 2)])
def test_touchdown_at_period_boundary_has_only_the_required_kick(
    run_scenario: Callable, quarter: int, expected_kicks: int,
) -> None:
    result = run_scenario(plays=(PlayType.LINE_PLUNGE,),
                          after_opening=lambda game: set_scrimmage(game, True, 99, 1, quarter))
    assert result["game"].state.home_score == 7
    assert result["game"].state.quarter == quarter + 1
    assert len(result["kicks"]) == expected_kicks


def test_modified_overtime_first_field_goal_allows_response(run_scenario: Callable) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        game.season_rules.overtime.format = "modified_sudden_death"
    result = run_scenario(setup, (PlayType.FIELD_GOAL,),
                          lambda game: set_scrimmage(game, True, 90, 0, 4))
    state = result["game"].state
    assert state.is_overtime and not state.game_over
    assert state.home_score + state.away_score == 3
    assert len(result["kicks"]) == 3
    assert not any(kick[0] for kick in result["kicks"])


def test_regular_overtime_can_expire_tied(run_scenario: Callable) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        game.season_rules.overtime.period_length_minutes = 1 / 60
    result = run_scenario(setup, after_opening=lambda game: set_scrimmage(game, True, 90, 0, 4))
    state = result["game"].state
    assert result["finished"] and state.game_over and state.is_overtime
    assert state.home_score == state.away_score == 0
    assert len(result["kicks"]) == 2


def test_repeated_defensive_penalties_keep_the_untimed_down(run_scenario: Callable) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        for chart in (game.state.home_chart, game.state.away_chart):
            chart.offense.medium_pass.update({16: "DEF 5", 17: "0"})
    def ending(game: PaydirtGameEngine) -> None:
        set_scrimmage(game, True, 50, 0, 4)
        game.state.home_score = 7
        game.state.untimed_down_pending = True
    result = run_scenario(setup, (PlayType.MEDIUM_PASS, PlayType.MEDIUM_PASS, PlayType.LINE_PLUNGE),
                          ending, False, offense_rolls=(16, 17, 16, 17, 18))
    state = result["game"].state
    assert result["finished"] and state.game_over
    assert not result["game"].has_untimed_down()
    assert state.away_stats.penalties == 2
    assert result["output"].count("UNTIMED DOWN -") == 3
    assert len(result["kicks"]) == 1


@pytest.mark.parametrize("seed", [17, 29, 103, 2026])
def test_seeded_public_game_finishes_with_consistent_totals(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, seed: int,
) -> None:
    import random

    game = make_sample_game()
    monkeypatch.setattr(auto_game, "find_team_charts", lambda path: [("2026", "sample", "sample")])
    monkeypatch.setattr(auto_game, "resolve_team_path", lambda spec, charts, root: spec)
    monkeypatch.setattr(auto_game, "load_team_chart", lambda path: (
        game.state.away_chart if path == "away" else game.state.home_chart))
    monkeypatch.setattr(auto_game, "PaydirtGameEngine", lambda home, away: game)
    monkeypatch.setattr(auto_game.time, "sleep", lambda delay: None)
    kickoff = game.kickoff
    kicks = []

    def kick(kicking_home: bool = True, kickoff_spot: int = 35):
        assert not game.state.game_over, "Kickoff after game end"
        kicks.append(game.state.quarter)
        return kickoff(kicking_home=kicking_home, kickoff_spot=kickoff_spot)

    monkeypatch.setattr(game, "kickoff", kick)
    run_play = game.run_play_with_penalty_procedure

    def play(*args, **kwargs):
        assert game.state.time_remaining > 0 or game.has_untimed_down(), "Expired-clock play"
        return run_play(*args, **kwargs)

    monkeypatch.setattr(game, "run_play_with_penalty_procedure", play)
    random_state = random.getstate()
    try:
        random.seed(seed)
        auto_game.run_auto_game("away", "home")
    finally:
        random.setstate(random_state)
    state = game.state
    assert state.game_over and not game.has_untimed_down()
    assert all(not outcome.pending_penalty_decision for outcome in game.play_log)
    periods = game.get_period_scores()
    assert sum(period["home"] for period in periods) == state.home_score
    assert sum(period["away"] for period in periods) == state.away_score
    assert sum(score.points for score in state.scoring_plays if score.is_home_team) == state.home_score
    assert sum(score.points for score in state.scoring_plays if not score.is_home_team) == state.away_score
    for stats in (state.home_stats, state.away_stats):
        assert stats.net_passing_yards == stats.passing_yards - stats.sack_yards
        assert stats.total_yards == stats.rushing_yards + stats.net_passing_yards
    assert kicks
    assert "FINAL STATISTICS" in capsys.readouterr().out


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("deficit", [6, 7])
@pytest.mark.parametrize("pat_good", [False, True])
def test_final_touchdown_completes_conversion_before_end_or_overtime(
    run_scenario: Callable, home: bool, deficit: int, pat_good: bool,
) -> None:
    def setup(game: PaydirtGameEngine) -> None:
        if not pat_good:
            for chart in (game.state.home_chart, game.state.away_chart):
                chart.special_teams.extra_point_no_good = list(range(10, 40))

    def ending(game: PaydirtGameEngine) -> None:
        set_scrimmage(game, home, 99, 1, 4)
        game.state.home_score = 7 if not home else 7 - deficit
        game.state.away_score = 7 if home else 7 - deficit

    result = run_scenario(setup, (PlayType.LINE_PLUNGE,), ending)
    state = result["game"].state
    offense_score = state.home_score if home else state.away_score
    assert offense_score == 13 - deficit + int(pat_good)
    tied = offense_score == 7
    assert state.is_overtime is tied
    assert state.game_over is not tied
    assert result["finished"] is not tied
    assert len(result["kicks"]) == (2 if tied else 1)
    assert f"Extra point {'GOOD' if pat_good else 'NO GOOD'}" in result["output"]


@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.FIELD_GOAL])
def test_sudden_death_score_never_attempts_conversion(run_scenario: Callable, play: PlayType) -> None:
    def ending(game: PaydirtGameEngine) -> None:
        game.start_overtime(coin_toss_winner_is_home=True)
        set_scrimmage(game, True, 99, 60, 5)
    result = run_scenario(plays=(play,), after_opening=ending)
    assert result["finished"] and result["game"].state.game_over
    assert result["game"].state.home_score == (6 if play == PlayType.LINE_PLUNGE else 3)
    assert "Extra point" not in result["output"]
    assert len(result["kicks"]) == 1


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("pat_good", [False, True])
def test_interactive_conversion_respects_engine_terminal_kick_query(
    monkeypatch: pytest.MonkeyPatch, home: bool, pat_good: bool,
) -> None:
    # The shared engine's finalized PAT must not make the existing CLI kick
    # after game end (or before overtime when the final PAT misses).
    from paydirt import interactive_game

    game = make_sample_game()
    game.season_rules.two_point_conversion = False
    set_scrimmage(game, home, 99, 1, 4)
    game.state.home_score = 6 if not home else 0
    game.state.away_score = 6 if home else 0
    game.state.possession_team.offense.line_plunge[16] = "1"
    game.state.defense_team.defense.modifiers.clear()
    if not pat_good:
        game.state.possession_team.special_teams.extra_point_no_good = [16]
    else:
        game.state.possession_team.special_teams.extra_point_no_good = []
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (16, "synthetic"))
    monkeypatch.setattr("paydirt.play_resolver.roll_chart_dice", lambda: (16, "synthetic"))
    outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert outcome.touchdown and not game.state.game_over
    assert game.state.time_remaining == 0
    choice = Mock(return_value=False)
    kick = Mock(wraps=game.kickoff)
    monkeypatch.setattr(interactive_game, "get_kickoff_choice", choice)
    monkeypatch.setattr(game, "kickoff", kick)
    interactive_game._complete_touchdown_sequence(game, outcome, human_is_home=not home)
    assert game.state.game_over is pat_good
    assert game.needs_overtime() is not pat_good
    choice.assert_not_called()
    kick.assert_not_called()
